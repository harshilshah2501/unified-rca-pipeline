"""Validate GraphState and publish / load the Dest ``map/`` room.

``publish_map`` on GraphWriter ends here: schema-validate nodes, edges, and the
packaged ``graph_snapshot.v1``, then ``Dest.put`` under room ``map/``.

PoC encoding is Gate B ``files.v1`` (JSON / JSONL). Product keeps the same
logical keys; Vortex/S3 are later temperature encodings — not a second schema.
See ``contracts/MAP_WRITE_READ_RECORD.md``.
"""

from __future__ import annotations

import json
from typing import Any

from ab_shared.dest import Dest
from ab_shared.schema import validate
from graph.graph_builder import GraphState


def build_snapshot(state: GraphState, *, version: str = "1") -> dict[str, Any]:
    """Assemble and schema-validate a ``graph_snapshot.v1`` from in-memory state."""
    nodes = list(state.nodes.values())
    edges = list(state.edges.values())
    for n in nodes:
        validate("graph_node_v1.schema.json", n)
    for e in edges:
        validate("graph_edge_v1.schema.json", e)
    snapshot = {
        "schema_version": "graph_snapshot.v1",
        "tenant": state.tenant,
        "version": version,
        "nodes": nodes,
        "edges": edges,
    }
    validate("graph_snapshot_v1.schema.json", snapshot)
    return snapshot


def publish_snapshot(dest: Dest, snapshot: dict[str, Any]) -> None:
    """Write map room keys per MAP_WRITE_READ_RECORD / files.v1."""
    validate("graph_snapshot_v1.schema.json", snapshot)
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
    """Read packaged snapshot from Dest ``map/`` (Scope / Diagnose / tests)."""
    raw = dest.get("map", "graph_snapshot.json")
    if raw is None:
        return None
    snapshot = json.loads(raw.decode("utf-8"))
    validate("graph_snapshot_v1.schema.json", snapshot)
    return snapshot
