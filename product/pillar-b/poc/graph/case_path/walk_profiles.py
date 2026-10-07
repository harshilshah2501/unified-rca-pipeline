"""E8 Scope detect-class walk profiles (MAP_SCOPE_WALK_POLICY §4).

Maps CaseSeed ``detect_class`` → relation set, hop budget, and walk direction.
Storage still holds all fifteen Motadata relations; Scope filters which ones
participate in the WorkingSet BFS / path search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

Direction = Literal["out", "in", "both"]

# ERROR / AVAILABILITY / SLOWDOWN — service + dependency map (G5 / policy §4.1–4.2).
_APP_FAULT_RELATIONS = frozenset(
    {
        "depends_on",
        "communicates_with",
        "uses",
        "part_of",
        "runs_on",
    }
)
_CLUSTER_OPTIONAL = frozenset({"member_of", "clustered_with"})

# SATURATION — hosting / shared-box context (§4.3).
_SATURATION_RELATIONS = frozenset(
    {
        "runs_on",
        "hosted_on",
        "part_of",
        "member_of",
        "clustered_with",
        "depends_on",
    }
)

# MONITORING_UNAVAILABLE / infrastructure (§4.4).
_MONITORING_RELATIONS = frozenset(
    {
        "monitored_by",
        "runs_on",
        "hosted_on",
        "connects_to",
        "mounts",
        "routes_through",
    }
)

# ANOMALY — minimal neighborhood (§4.5).
_ANOMALY_RELATIONS = frozenset({"depends_on", "runs_on"})


@dataclass(frozen=True)
class WalkProfile:
    """Resolved Scope walk knobs for one CaseSeed detect class."""

    name: str
    detect_class: str
    relations: frozenset[str]
    direction: Direction
    hops: int
    path_target_types: tuple[str, ...]


def _wants_cluster(labels: Mapping[str, Any] | None) -> bool:
    if not labels:
        return False
    if labels.get("include_cluster") is True:
        return True
    for key in ("cluster_id", "cluster", "cluster_name"):
        if labels.get(key):
            return True
    return False


def resolve_walk_profile(
    detect_class: str,
    *,
    labels: Mapping[str, Any] | None = None,
) -> WalkProfile:
    """Return the Scope walk profile for a CaseSeed detect class.

    Unknown classes fall back to the minimal ANOMALY profile so Scope does not
    open the full fifteen-relation catalog by accident.
    """
    raw = (detect_class or "").strip().upper() or "ANOMALY"
    cluster = _wants_cluster(labels)

    if raw in ("ERROR", "AVAILABILITY"):
        rels = set(_APP_FAULT_RELATIONS)
        if cluster:
            rels |= _CLUSTER_OPTIONAL
        return WalkProfile(
            name="error_availability",
            detect_class=raw,
            relations=frozenset(rels),
            direction="out",
            hops=2,
            path_target_types=("Database", "Host", "Runtime", "Middleware"),
        )

    if raw == "SLOWDOWN":
        rels = set(_APP_FAULT_RELATIONS)
        if cluster:
            rels |= _CLUSTER_OPTIONAL
        return WalkProfile(
            name="slowdown",
            detect_class=raw,
            relations=frozenset(rels),
            direction="out",
            hops=2,
            path_target_types=("Database", "Queue", "Host"),
        )

    if raw == "SATURATION":
        return WalkProfile(
            name="saturation",
            detect_class=raw,
            relations=_SATURATION_RELATIONS,
            direction="both",
            hops=2,
            path_target_types=("Host", "HypervisorHost", "Database"),
        )

    if raw in ("MONITORING_UNAVAILABLE", "INFRA", "INFRASTRUCTURE"):
        return WalkProfile(
            name="monitoring_unavailable",
            detect_class=raw,
            relations=_MONITORING_RELATIONS,
            direction="both",
            hops=2,
            path_target_types=("Host", "NetworkPort", "Datastore"),
        )

    # ANOMALY and anything unrecognized
    return WalkProfile(
        name="anomaly",
        detect_class=raw,
        relations=_ANOMALY_RELATIONS,
        direction="out",
        hops=1,
        path_target_types=(),
    )
