"""Compare GraphWriter actual snapshot to case expected spine (stable keys only)."""

from __future__ import annotations

from typing import Any


def snapshot_spine(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Reduce graph_snapshot.v1 to comparable node/edge identity fields."""
    nodes = sorted(
        [
            {
                "ci_id": n["ci_id"],
                "ci_type": n["ci_type"],
                "identity_status": n["identity_status"],
            }
            for n in snapshot["nodes"]
        ],
        key=lambda row: row["ci_id"],
    )
    edges = sorted(
        [
            {
                "edge_id": e["edge_id"],
                "src_ci_id": e["src_ci_id"],
                "relation": e["relation"],
                "dst_ci_id": e["dst_ci_id"],
            }
            for e in snapshot["edges"]
        ],
        key=lambda row: row["edge_id"],
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
