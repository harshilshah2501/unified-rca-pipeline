"""E5 Maintain (Pillar B side) — graph validity from map state.

Independent of Pillar A seasonal baselines. Not a package merge with sketches.

Runs on existing edges only (expire, stale corroborating, declared soft/hard).
Does not invent new topology. After maintain, callers typically ``publish_map``
again so Dest reflects the marks.

Declared-edge clocks (7d soft / 30d hard) are Design-numeric product defaults from
the operational graph — injectable for lab clocks; not yet vendor-lab validated.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from graph.graph_builder import GraphState

# Design-numeric — operational graph decision log / LLD-E5 §3
DECLARED_SOFT_STALE_DAYS = 7
DECLARED_HARD_DOWNGRADE_DAYS = 30

MAINTAIN_SOFT_STALE = "soft_stale"
MAINTAIN_HARD_DOWNGRADED = "hard_downgraded"


def _parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.fromisoformat(ts)


def _as_of_dt(as_of: str) -> datetime:
    return _parse_ts(as_of).astimezone(timezone.utc)


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


def apply_declared_freshness(
    state: GraphState,
    as_of: str,
    *,
    soft_stale_days: int = DECLARED_SOFT_STALE_DAYS,
    hard_downgrade_days: int = DECLARED_HARD_DOWNGRADE_DAYS,
) -> dict[str, int]:
    """Mark declared edges by age without creating or deleting them.

    - Soft (default 7d): ``maintain_status=soft_stale`` — still on the map.
    - Hard (default 30d): ``maintain_status=hard_downgraded`` + confidence ``n/a``
      (exclude from confidence-bearing localization paths; still published).

    Age clock starts from ``valid_from`` when set, else leaves the edge untouched.
    Edges with an explicit ``valid_to`` are handled by ``expire_edges``, not here.
    """
    now = _as_of_dt(as_of)
    soft_count = 0
    hard_count = 0
    for edge in state.edges.values():
        if edge.get("valid_to"):
            continue
        discovered = edge.get("discovered_via") or {}
        if discovered.get("evidence_type") != "declared":
            continue
        valid_from = edge.get("valid_from")
        if not valid_from:
            continue
        age = now - _parse_ts(valid_from).astimezone(timezone.utc)
        if age >= timedelta(days=hard_downgrade_days):
            edge["maintain_status"] = MAINTAIN_HARD_DOWNGRADED
            discovered = dict(discovered)
            discovered["confidence"] = "n/a"
            edge["discovered_via"] = discovered
            hard_count += 1
        elif age >= timedelta(days=soft_stale_days):
            edge["maintain_status"] = MAINTAIN_SOFT_STALE
            soft_count += 1
        else:
            edge.pop("maintain_status", None)
    return {"declared_soft_stale": soft_count, "declared_hard_downgraded": hard_count}


def confidence_bearing_edges(state: GraphState) -> list[dict[str, Any]]:
    """Edges eligible for confidence-bearing localization (excludes hard-downgraded)."""
    return [
        e
        for e in state.edges.values()
        if e.get("maintain_status") != MAINTAIN_HARD_DOWNGRADED
    ]


def maintain_graph_validity(
    state: GraphState,
    as_of: str,
    *,
    corroborating_max_age_seconds: int = 3600,
    soft_stale_days: int = DECLARED_SOFT_STALE_DAYS,
    hard_downgrade_days: int = DECLARED_HARD_DOWNGRADE_DAYS,
) -> dict[str, int]:
    """E5 map maintain: expire, drop stale corroborating, apply declared freshness."""
    expired = expire_edges(state, as_of)
    stale = drop_stale_corroborating(
        state,
        as_of,
        max_age_seconds=corroborating_max_age_seconds,
    )
    declared = apply_declared_freshness(
        state,
        as_of,
        soft_stale_days=soft_stale_days,
        hard_downgrade_days=hard_downgrade_days,
    )
    return {
        "expired_edges": expired,
        "stale_corroborating": stale,
        **declared,
    }
