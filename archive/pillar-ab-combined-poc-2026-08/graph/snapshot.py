from __future__ import annotations

import json
from typing import Any

from ab_shared.dest import Dest
from ab_shared.schema import validate
from graph.graph_builder import GraphState


def build_snapshot(state: GraphState, *, version: str = "1") -> dict[str, Any]:
    nodes = list(state.nodes.values())
    edges = list(state.edges.values())
    for n in nodes:
        validate("graph_node_v1.schema.json", n)
    for e in edges:
        validate("graph_edge_v1.schema.json", e)
    return {
        "schema_version": "graph_snapshot.v1",
        "tenant": state.tenant,
        "version": version,
        "nodes": nodes,
        "edges": edges,
    }


def publish_snapshot(dest: Dest, snapshot: dict[str, Any]) -> None:
    dest.put("map", "graph_snapshot.json", json.dumps(snapshot, indent=2).encode("utf-8"))
    dest.put(
        "map",
        "nodes.jsonl",
        ("\n".join(json.dumps(n) for n in snapshot["nodes"]) + "\n").encode("utf-8"),
    )
    dest.put(
        "map",
        "edges.jsonl",
        ("\n".join(json.dumps(e) for e in snapshot["edges"]) + "\n").encode("utf-8"),
    )


def load_snapshot(dest: Dest) -> dict[str, Any] | None:
    raw = dest.get("map", "graph_snapshot.json")
    if raw is None:
        return None
    return json.loads(raw.decode("utf-8"))
