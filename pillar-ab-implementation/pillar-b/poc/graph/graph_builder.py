"""Write core: in-memory estate (GraphState) + admit triage for topo lines.

``GraphWriter`` owns the public verbs; this module mutates ``GraphState``:

* ``load_estate_bootstrap_state`` — optional declared seed (lab JSON / future CMDB sync)
* ``apply_topo_stream`` — per-line NOOP / WRITE / DROP / phased skip

CI type eligibility → ``ci_qualify``; relation names → ``edge_catalog``;
endpoint pairing → ``edge_triplets`` (``EDGE_TRIPLET_ALLOWLIST.md``).
Node/edge shapes are Motadata-aligned (no tenant / discovered_via on rows).
Edge upsert identity is ``(source_id, edge_type, target_id)``; ``edge_id`` is a
snowflake allocated once per logical key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ab_shared.identity_gate import ResolvedOnlyGate
from ab_shared.ingest_source import IngestSource
from graph.ci_qualify import may_emit_vertex, to_storage_type
from graph.edge_catalog import classify_relation, to_edge_type
from graph.edge_triplets import check_edge_triplet, storage_type_or_none
from graph.snowflake import next_snowflake

# Motadata storage → ingest PascalCase for first-time node upsert when only map type is known.
_STORAGE_TO_INGEST = {
    "service": "Service",
    "host": "Host",
    "process": "Runtime",
    "db": "Database",
    "business_service": "BusinessService",
    "queue": "Queue",
    "pod": "Pod",
    "container": "Container",
    "endpoint": "Endpoint",
    "node": "Node",
    "namespace": "Namespace",
    "volume": "Volume",
    "network": "Network",
    "k8s_deployment": "Deployment",
    "customer": "Customer",
}


def logical_edge_key(source_id: str, edge_type: str, target_id: str) -> str:
    """Stable GraphState dict key — not the Motadata snowflake ``edge_id``."""
    return f"{source_id}|{edge_type}|{target_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _metadata_json(extra: dict[str, Any] | None = None) -> str:
    base: dict[str, Any] = {"env": "rca-lab"}
    if extra:
        base.update(extra)
    return json.dumps(base, separators=(",", ":"), sort_keys=True)


@dataclass
class GraphState:
    """Working estate before / between Dest publishes.

    ``nodes`` keyed by ``entity_id``. ``edges`` keyed by
    ``logical_edge_key(source_id, edge_type, target_id)``. ``rejects`` is the DROP
    tape for the current run (not persisted unless a caller chooses to).
    ``tenant`` scopes the Dest path / snapshot envelope only — not copied onto rows.
    """

    tenant: str = "default"
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[str, dict[str, Any]] = field(default_factory=dict)
    rejects: list[tuple[dict, str]] = field(default_factory=list)


def _resolve_endpoint_storage_type(
    state: GraphState,
    ci_id: str,
    declared_ci_type: str | None,
) -> str | None:
    """Prefer type already on the map; else map declared ingest type. Never invent Service."""
    existing = state.nodes.get(ci_id)
    if existing and existing.get("type"):
        return str(existing["type"])
    return storage_type_or_none(declared_ci_type)


def _make_node(
    n: dict,
    *,
    last_seen: str | None = None,
    version: int = 1,
    valid_from: str | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Motadata ``graph_node.v1`` dict; raises if CI type is never allowed."""
    ci_type = n["type"]
    ok, reason = may_emit_vertex(ci_type)
    if not ok:
        raise ValueError(reason)
    seen = last_seen or _now_iso()
    return {
        "schema_version": "graph_node.v1",
        "entity_id": n["id"],
        "type": to_storage_type(ci_type),
        "name": n.get("name", n["id"]),
        "metadata": _metadata_json(metadata_extra),
        "last_seen": seen,
        "valid_from": valid_from,
        "valid_to": None,
        "version": version,
    }


def _upsert_node(state: GraphState, n: dict, *, last_seen: str | None = None) -> None:
    eid = n["id"]
    seen = last_seen or _now_iso()
    if eid in state.nodes:
        prev = state.nodes[eid]
        prev["last_seen"] = seen
        prev["version"] = int(prev.get("version") or 1) + 1
        if n.get("name") and n["name"] != eid:
            prev["name"] = n["name"]
        # Keep Motadata type from first write — stream lines often omit dst_ci_type
        # and would otherwise clobber Host/Database with a Service default.
        return
    state.nodes[eid] = _make_node(n, last_seen=seen, version=1)


def _make_edge(
    *,
    source_id: str,
    target_id: str,
    edge_type: str,
    edge_id: int,
    evidence_event_id: int,
    valid_from: str | None,
    origin: str,
    telemetry_source: str | None = None,
) -> dict[str, Any]:
    """Build a Motadata ``graph_edge.v1`` dict.

    ``origin`` / ``telemetry_source`` are PoC maintain helpers (additionalProperties),
    not Motadata table columns — used so E5 can distinguish declared vs stream edges
    without ``discovered_via``.
    """
    row: dict[str, Any] = {
        "schema_version": "graph_edge.v1",
        "edge_id": edge_id,
        "source_id": source_id,
        "target_id": target_id,
        "edge_type": edge_type,
        "valid_from": valid_from,
        "valid_to": None,
        "evidence_event_id": evidence_event_id,
        "origin": origin,
    }
    if telemetry_source:
        row["telemetry_source"] = telemetry_source
    return row


def _upsert_edge(
    state: GraphState,
    *,
    source_id: str,
    target_id: str,
    relation: str,
    valid_from: str | None,
    origin: str,
    telemetry_source: str | None = None,
    evidence_event_id: int | None = None,
) -> None:
    edge_type = to_edge_type(relation)
    key = logical_edge_key(source_id, edge_type, target_id)
    ev_id = evidence_event_id if evidence_event_id is not None else next_snowflake()
    if key in state.edges:
        prev = state.edges[key]
        prev["valid_from"] = valid_from
        prev["evidence_event_id"] = ev_id
        prev["origin"] = origin
        if telemetry_source:
            prev["telemetry_source"] = telemetry_source
        prev.pop("maintain_status", None)
        return
    state.edges[key] = _make_edge(
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        edge_id=next_snowflake(),
        evidence_event_id=ev_id,
        valid_from=valid_from,
        origin=origin,
        telemetry_source=telemetry_source,
    )


def load_estate_bootstrap_state(path_or_dict: Any, tenant: str = "default") -> GraphState:
    """Load declared estate bootstrap (lab file or CMDB-style starting map).

    Product intent: first fill / occasional declared reconcile — not every stream event.
    """
    if hasattr(path_or_dict, "read_text"):
        data = json.loads(path_or_dict.read_text(encoding="utf-8"))
    elif isinstance(path_or_dict, (str, bytes)):
        from pathlib import Path

        data = json.loads(Path(path_or_dict).read_text(encoding="utf-8"))
    else:
        data = path_or_dict
    state = GraphState(tenant=tenant)
    bootstrap_seen = "2026-08-20T00:00:00Z"
    for n in data.get("nodes", []):
        ok, reason = may_emit_vertex(n["type"])
        if not ok:
            state.rejects.append((n, reason or "never_ci_vertex"))
            continue
        _upsert_node(
            state,
            n,
            last_seen=bootstrap_seen,
        )
        state.nodes[n["id"]]["valid_from"] = bootstrap_seen
    for e in data.get("edges", []):
        action, reason = classify_relation(e["relation"])
        if action == "reject":
            state.rejects.append((e, reason or "unknown_relation"))
            continue
        if action == "skip":
            continue
        src, dst = e["from"], e["to"]
        if src not in state.nodes or dst not in state.nodes:
            continue
        src_type = state.nodes[src].get("type")
        dst_type = state.nodes[dst].get("type")
        trip, trip_reason = check_edge_triplet(e["relation"], src_type, dst_type)
        if trip != "ok":
            state.rejects.append((e, trip_reason or "illegal_edge_triplet"))
            continue
        _upsert_edge(
            state,
            source_id=src,
            target_id=dst,
            relation=e["relation"],
            valid_from=bootstrap_seen,
            origin="declared",
            telemetry_source="topology.bootstrap",
        )
    return state


def apply_topo_stream(state: GraphState, source: IngestSource, gate: ResolvedOnlyGate | None = None) -> GraphState:
    """Apply post-E2 ingest lines that are Topology's job.

    Admit mapping (hub walkthrough NOOP / WRITE / DROP):
      - fact_kind != topo_update → NOOP (silent continue; metric/event/trace/anomaly)
      - gate or catalog fail → DROP (append rejects)
      - classify_relation skip → phased map-NOOP
      - illegal / missing endpoint types → DROP (triplet allowlist)
      - classify_relation emit → WRITE (upsert nodes + edge)
    """
    gate = gate or ResolvedOnlyGate()
    for rec in source.records():
        if rec.get("fact_kind") != "topo_update":
            continue
        result = gate.admit(rec)
        if not result.accepted:
            state.rejects.append((rec, result.reason or "identity_unresolved"))
            continue
        ci_type = rec.get("ci_type", "Service")
        ok, reason = may_emit_vertex(ci_type)
        if not ok:
            state.rejects.append((rec, reason or "never_ci_vertex"))
            continue
        relation = rec.get("relation")
        if not relation:
            continue
        action, reason = classify_relation(relation)
        if action == "reject":
            state.rejects.append((rec, reason or "unknown_relation"))
            continue
        if action == "skip":
            continue
        src = rec.get("src_ci_id") or rec["ci_id"]
        dst = rec.get("dst_ci_id")
        if not dst:
            continue
        src_declared = rec.get("src_ci_type") or ci_type
        dst_declared = rec.get("dst_ci_type")  # no Service default — see EDGE_TRIPLET_ALLOWLIST
        src_storage = _resolve_endpoint_storage_type(state, src, src_declared)
        dst_storage = _resolve_endpoint_storage_type(state, dst, dst_declared)
        trip, trip_reason = check_edge_triplet(relation, src_storage, dst_storage)
        if trip != "ok":
            state.rejects.append((rec, trip_reason or "illegal_edge_triplet"))
            continue
        ts = rec.get("ts") or _now_iso()
        src_emit = src_declared
        dst_emit = dst_declared or _STORAGE_TO_INGEST.get(str(dst_storage), "")
        for cid, emit_type, cname in (
            (src, src_emit, src),
            (dst, dst_emit, dst),
        ):
            if not emit_type:
                continue
            ok2, _reason2 = may_emit_vertex(emit_type)
            if not ok2:
                continue
            _upsert_node(state, {"id": cid, "type": emit_type, "name": cname}, last_seen=ts)
        bind = rec.get("identity", {}).get("bind_source", "topo_update")
        _upsert_edge(
            state,
            source_id=src,
            target_id=dst,
            relation=relation,
            valid_from=ts,
            origin="stream",
            telemetry_source=bind,
        )
    return state
