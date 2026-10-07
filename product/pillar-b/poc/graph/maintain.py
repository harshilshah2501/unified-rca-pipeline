"""E5 Maintain (Pillar B side) — graph validity from map state.

Independent of Pillar A seasonal baselines. Not a package merge with sketches.

Runs on existing edges only (expire, drop stale stream edges, declared soft/hard).
Does not invent new topology. After maintain, callers typically ``publish_map``
again so Dest reflects the marks.

Uses Motadata ``valid_to`` / node ``last_seen`` + ``version`` (epoch ms) — not
``discovered_via.evidence_type`` tiers. Declared vs stream is the PoC
``origin`` additional property set at write time.

``map/`` is the **present** topology surface. Maintain refreshes validity on that
present map; it does not append a history/ sketch room or keep an event log of
past estates (cold snapshot versions are checkpoints of present state, not Pillar A history).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from graph.graph_builder import GraphState
from graph.timeutil import epoch_ms_to_datetime, to_epoch_ms

DECLARED_SOFT_STALE_DAYS = 7
DECLARED_HARD_DOWNGRADE_DAYS = 30

MAINTAIN_SOFT_STALE = "soft_stale"
MAINTAIN_HARD_DOWNGRADED = "hard_downgraded"


def expire_edges(state: GraphState, as_of: str | int) -> int:
    """Drop edges whose valid_to is set and <= as_of. Returns count removed."""
    as_of_ms = to_epoch_ms(as_of)
    removed = 0
    doomed: list[str] = []
    for eid, edge in state.edges.items():
        valid_to = edge.get("valid_to")
        if valid_to is None:
            continue
        if to_epoch_ms(valid_to) <= as_of_ms:
            doomed.append(eid)
    for eid in doomed:
        del state.edges[eid]
        removed += 1
    return removed


def drop_stale_stream_edges(
    state: GraphState,
    as_of: str | int,
    *,
    max_age_seconds: int = 3600,
) -> int:
    """Drop stream-origin edges older than max_age relative to as_of (no valid_to)."""
    as_of_ms = to_epoch_ms(as_of)
    cutoff_ms = as_of_ms - (max_age_seconds * 1000)
    removed = 0
    doomed: list[str] = []
    for eid, edge in state.edges.items():
        if edge.get("valid_to") is not None:
            continue
        if edge.get("origin") != "stream":
            continue
        valid_from = edge.get("valid_from")
        if valid_from is None:
            continue
        if to_epoch_ms(valid_from) <= cutoff_ms:
            doomed.append(eid)
    for eid in doomed:
        del state.edges[eid]
        removed += 1
    return removed


# Back-compat alias for callers / tests that still use the old name
def drop_stale_corroborating(
    state: GraphState,
    as_of: str | int,
    *,
    max_age_seconds: int = 3600,
) -> int:
    return drop_stale_stream_edges(state, as_of, max_age_seconds=max_age_seconds)


def touch_nodes(state: GraphState, as_of: str | int) -> int:
    """Refresh ``last_seen`` and bump ``version`` on every node (Motadata maintain)."""
    as_of_ms = to_epoch_ms(as_of)
    touched = 0
    for node in state.nodes.values():
        node["last_seen"] = as_of_ms
        node["version"] = int(node.get("version") or 1) + 1
        touched += 1
    return touched


def apply_declared_freshness(
    state: GraphState,
    as_of: str | int,
    *,
    soft_stale_days: int = DECLARED_SOFT_STALE_DAYS,
    hard_downgrade_days: int = DECLARED_HARD_DOWNGRADE_DAYS,
) -> dict[str, int]:
    """Mark declared-origin edges by age without creating or deleting them.

    - Soft (default 7d): ``maintain_status=soft_stale`` — still on the map.
    - Hard (default 30d): ``maintain_status=hard_downgraded`` (exclude from
      confidence-bearing localization paths; still published).

    Age clock starts from ``valid_from`` when set, else leaves the edge untouched.
    Edges with an explicit ``valid_to`` are handled by ``expire_edges``, not here.
    """
    now = epoch_ms_to_datetime(to_epoch_ms(as_of))
    soft_count = 0
    hard_count = 0
    for edge in state.edges.values():
        if edge.get("valid_to") is not None:
            continue
        if edge.get("origin") != "declared":
            continue
        valid_from = edge.get("valid_from")
        if valid_from is None:
            continue
        age = now - epoch_ms_to_datetime(to_epoch_ms(valid_from))
        if age >= timedelta(days=hard_downgrade_days):
            edge["maintain_status"] = MAINTAIN_HARD_DOWNGRADED
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
    as_of: str | int,
    *,
    corroborating_max_age_seconds: int = 3600,
    soft_stale_days: int = DECLARED_SOFT_STALE_DAYS,
    hard_downgrade_days: int = DECLARED_HARD_DOWNGRADE_DAYS,
    touch_node_versions: bool = False,
) -> dict[str, int]:
    """E5 map maintain: expire, drop stale stream edges, apply declared freshness."""
    expired = expire_edges(state, as_of)
    stale = drop_stale_stream_edges(
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
    touched = touch_nodes(state, as_of) if touch_node_versions else 0
    return {
        "expired_edges": expired,
        "stale_corroborating": stale,
        "nodes_touched": touched,
        **declared,
    }
