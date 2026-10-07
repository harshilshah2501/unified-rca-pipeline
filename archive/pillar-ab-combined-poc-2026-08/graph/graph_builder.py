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
    tenant: str = "default"
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[str, dict[str, Any]] = field(default_factory=dict)
    rejects: list[tuple[dict, str]] = field(default_factory=list)


def _node_from_seed(tenant: str, n: dict) -> dict[str, Any]:
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


def load_seed_topology(path_or_dict: Any, tenant: str = "default") -> GraphState:
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
        node = _node_from_seed(tenant, n)
        state.nodes[node["ci_id"]] = node
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
        edge_id = f"e_{src}_{e['relation']}_{dst}"
        state.edges[edge_id] = {
            "schema_version": "graph_edge.v1",
            "tenant": tenant,
            "edge_id": edge_id,
            "src_ci_id": src,
            "dst_ci_id": dst,
            "relation": e["relation"],
            "discovered_via": build_discovered_via(
                "declared",
                confidence="medium",
                telemetry_source="topology.seed",
                direction_inference=f"{src} -> {dst}",
            ),
            "valid_from": "2026-08-20T00:00:00Z",
            "valid_to": None,
        }
    return state


def apply_topo_updates(state: GraphState, source: IngestSource, gate: ResolvedOnlyGate | None = None) -> GraphState:
    gate = gate or ResolvedOnlyGate()
    for rec in source.records():
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
        for cid, ctype, cname in (
            (src, ci_type, src),
            (dst, rec.get("dst_ci_type", "Service"), dst),
        ):
            if cid not in state.nodes:
                ok2, reason2 = may_emit_vertex(ctype)
                if not ok2:
                    continue
                state.nodes[cid] = _node_from_seed(state.tenant, {"id": cid, "type": ctype, "name": cname})
        bind = rec.get("identity", {}).get("bind_source", "topo_update")
        edge_id = f"e_{src}_{relation}_{dst}"
        state.edges[edge_id] = {
            "schema_version": "graph_edge.v1",
            "tenant": state.tenant,
            "edge_id": edge_id,
            "src_ci_id": src,
            "dst_ci_id": dst,
            "relation": relation,
            "discovered_via": build_discovered_via(
                evidence_for_source(bind),
                confidence="high" if "inventory" in bind else "medium",
                telemetry_source=bind,
                direction_inference=f"{src} -> {dst}",
            ),
            "valid_from": rec.get("ts"),
            "valid_to": None,
        }
    return state
