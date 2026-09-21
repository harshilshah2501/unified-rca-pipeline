"""Write core: in-memory estate (GraphState) + admit triage for topo lines.

``GraphWriter`` owns the public verbs; this module mutates ``GraphState``:

* ``load_estate_bootstrap_state`` — optional declared seed (lab JSON / future CMDB sync)
* ``apply_topo_stream`` — per-line NOOP / WRITE / DROP / phased skip

CI type eligibility → ``ci_qualify``; relation names → ``edge_catalog``;
``discovered_via`` stamps → ``provenance``. No cycle detection in P1.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ab_shared.identity_gate import ResolvedOnlyGate
from ab_shared.ingest_source import IngestSource
from graph.ci_qualify import may_emit_vertex
from graph.edge_catalog import classify_relation
from graph.provenance import build_discovered_via, evidence_for_source


@dataclass
class GraphState:
    """Working estate before / between Dest publishes.

    ``nodes`` / ``edges`` keyed by ``ci_id`` / ``edge_id``. ``rejects`` is the DROP
    tape for the current run (not persisted unless a caller chooses to).
    """

    tenant: str = "default"
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[str, dict[str, Any]] = field(default_factory=dict)
    rejects: list[tuple[dict, str]] = field(default_factory=list)


def _make_node(tenant: str, n: dict) -> dict[str, Any]:
    """Build a ``graph_node.v1`` dict; raises if CI type is never allowed on map/.

    Expects input keys ``id``, ``type``, and optional ``name`` (estate bootstrap
    JSON shape). Also used when the stream creates missing endpoints.
    """
    ci_type = n["type"]
    ok, reason = may_emit_vertex(ci_type)
    if not ok:
        raise ValueError(reason)
    return {
        "schema_version": "graph_node.v1",
        "tenant": tenant,
        "ci_id": n["id"],
        "ci_type": ci_type,
        "ci_name": n.get("name", n["id"]),
        "instance_scope": "single",
        "identity_status": "resolved",
        "monitored_via": [],
        "aliases": [],
        "labels": {"env": "rca-lab"},
        "valid_from": None,
        "valid_to": None,
    }


def _make_edge(
    tenant: str,
    src: str,
    dst: str,
    relation: str,
    *,
    discovered_via: dict[str, Any],
    valid_from: str | None,
) -> dict[str, Any]:
    """Build a ``graph_edge.v1`` dict with a stable ``edge_id`` for upserts.

    Callers decide admit (``classify_relation``) and provenance; this only shapes
    the object — same role as ``_make_node`` for vertices.
    """
    return {
        "schema_version": "graph_edge.v1",
        "tenant": tenant,
        "edge_id": f"e_{src}_{relation}_{dst}",
        "src_ci_id": src,
        "dst_ci_id": dst,
        "relation": relation,
        "discovered_via": discovered_via,
        "valid_from": valid_from,
        "valid_to": None,
    }


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
    for n in data.get("nodes", []):
        ok, reason = may_emit_vertex(n["type"])
        if not ok:
            state.rejects.append((n, reason or "never_ci_vertex"))
            continue
        node = _node_from_bootstrap(tenant, n)
        state.nodes[node["ci_id"]] = node
    for e in data.get("edges", []):
        action, reason = classify_relation(e["relation"])
        if action == "reject":
            state.rejects.append((e, reason or "unknown_relation"))
            continue
        if action == "skip":
            # Catalog relation, not wave-1 yet — leave map unchanged.
            continue
        src, dst = e["from"], e["to"]
        if src not in state.nodes or dst not in state.nodes:
            continue
        edge = _make_edge(
            tenant,
            src,
            dst,
            e["relation"],
            discovered_via=build_discovered_via(
                "declared",
                confidence="medium",
                telemetry_source="topology.bootstrap",
                direction_inference=f"{src} -> {dst}",
            ),
            valid_from="2026-08-20T00:00:00Z",
        )
        state.edges[edge["edge_id"]] = edge
    return state


def apply_topo_stream(state: GraphState, source: IngestSource, gate: ResolvedOnlyGate | None = None) -> GraphState:
    """Apply post-E2 ingest lines that are Topology's job.

    Admit mapping (hub walkthrough NOOP / WRITE / DROP):
      - signal_class != topo_update → NOOP (silent continue; metric/event/trace/anomaly)
      - gate or catalog fail → DROP (append rejects)
      - classify_relation skip → phased map-NOOP
      - classify_relation emit → WRITE (upsert nodes + edge)
    """
    gate = gate or ResolvedOnlyGate()
    for rec in source.records():
        # NOOP — not Topology's signal_class (Pillar A / other stores own those lines).
        if rec.get("signal_class") != "topo_update":
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
        # Ensure both endpoints exist as vertices before writing the edge.
        for cid, ctype, cname in (
            (src, ci_type, src),
            (dst, rec.get("dst_ci_type", "Service"), dst),
        ):
            if cid not in state.nodes:
                ok2, reason2 = may_emit_vertex(ctype)
                if not ok2:
                    continue
                state.nodes[cid] = _node_from_bootstrap(
                    state.tenant, {"id": cid, "type": ctype, "name": cname}
                )
        bind = rec.get("identity", {}).get("bind_source", "topo_update")
        # Upsert: same edge_id refreshes the fact (valid_from / provenance) in place.
        edge = _make_edge(
            state.tenant,
            src,
            dst,
            relation,
            discovered_via=build_discovered_via(
                evidence_for_source(bind),
                confidence="high" if "inventory" in bind else "medium",
                telemetry_source=bind,
                direction_inference=f"{src} -> {dst}",
            ),
            valid_from=rec.get("ts"),
        )
        state.edges[edge["edge_id"]] = edge
    return state
