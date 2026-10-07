"""Compare GraphWriter actual snapshot to case expected spine (stable keys only).

Full node/edge objects carry snowflake ids and maintain marks that may grow;
SAMPLE_IO goldens assert on Motadata identity fields instead.
Tests only — not a product read API.
"""

from __future__ import annotations

from typing import Any


def snapshot_spine(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Reduce graph_snapshot.v1 to comparable Motadata identity fields."""
    nodes = sorted(
        [
            {
                "entity_id": n["entity_id"],
                "type": n["type"],
            }
            for n in snapshot["nodes"]
        ],
        key=lambda row: row["entity_id"],
    )
    edges = sorted(
        [
            {
                "source_id": e["source_id"],
                "edge_type": e["edge_type"],
                "target_id": e["target_id"],
            }
            for e in snapshot["edges"]
        ],
        key=lambda row: (row["source_id"], row["edge_type"], row["target_id"]),
    )
    return {
        "tenant": snapshot["tenant"],
        "version": snapshot["version"],
        "nodes": nodes,
        "edges": edges,
    }


def compare_spine(expected: dict[str, Any], actual_snapshot: dict[str, Any]) -> list[str]:
    """Return human-readable diffs (empty list means match)."""
    actual = snapshot_spine(actual_snapshot)
    diffs: list[str] = []
    for key in ("tenant", "version"):
        if expected.get(key) != actual.get(key):
            diffs.append(f"{key}: expected {expected.get(key)!r} actual {actual.get(key)!r}")
    if expected.get("nodes") != actual["nodes"]:
        diffs.append(
            "nodes mismatch:\n"
            f"  expected={expected.get('nodes')!r}\n"
            f"  actual  ={actual['nodes']!r}"
        )
    if expected.get("edges") != actual["edges"]:
        diffs.append(
            "edges mismatch:\n"
            f"  expected={expected.get('edges')!r}\n"
            f"  actual  ={actual['edges']!r}"
        )
    return diffs
