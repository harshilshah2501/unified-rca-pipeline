"""E5 Maintain (Pillar B side) — graph validity from map state.

Independent of Pillar A seasonal baselines. Not a package merge with sketches.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from graph.graph_builder import GraphState


def _parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromisoformat(ts)


def expire_edges(state: GraphState, as_of: str) -> int:
    """Drop edges whose valid_to is set and <= as_of. Returns count removed."""
    removed = 0
    doomed: list[str] = []
    for eid, edge in state.edges.items():
        valid_to = edge.get("valid_to")
        if valid_to and valid_to <= as_of:
            doomed.append(eid)
    for eid in doomed:
        del state.edges[eid]
        removed += 1
    return removed


def drop_stale_corroborating(
    state: GraphState,
    as_of: str,
    *,
    max_age_seconds: int = 3600,
) -> int:
    """Drop corroborating edges older than max_age relative to as_of (no valid_to set)."""
    cutoff = _parse_ts(as_of) - timedelta(seconds=max_age_seconds)
    removed = 0
    doomed: list[str] = []
    for eid, edge in state.edges.items():
        if edge.get("valid_to"):
            continue
        discovered = edge.get("discovered_via", {})
        if discovered.get("evidence_type") != "corroborating":
            continue
        valid_from = edge.get("valid_from")
        if not valid_from:
            continue
        if _parse_ts(valid_from) <= cutoff:
            doomed.append(eid)
    for eid in doomed:
        del state.edges[eid]
        removed += 1
    return removed


def maintain_graph_validity(
    state: GraphState,
    as_of: str,
    *,
    corroborating_max_age_seconds: int = 3600,
) -> dict[str, int]:
    """E5 stub: expire time-bounded edges and drop stale corroborating links."""
    expired = expire_edges(state, as_of)
    stale = drop_stale_corroborating(
        state,
        as_of,
        max_age_seconds=corroborating_max_age_seconds,
    )
    return {"expired_edges": expired, "stale_corroborating": stale}
