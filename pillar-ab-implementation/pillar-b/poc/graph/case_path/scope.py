"""E8 Scope — CaseSeed + published map/ → bounded WorkingSet (map side).

Sketch / history snippets are optional via ``sketch_refs`` injection so Pillar B
stays unit-testable without importing Pillar A. Full A∥B join remains in
``integration/``.

Walk knobs (relations, hops, direction) default from the CaseSeed detect-class
profile in ``walk_profiles`` / contracts ``MAP_SCOPE_WALK_POLICY.md`` §4.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

from graph.case_path.curate import CaseSeed
from graph.case_path.walk_profiles import WalkProfile, resolve_walk_profile
from graph.neighbors import find_paths, neighbor_ids, neighbors, reachable_ci_ids

SketchProvider = Callable[[CaseSeed, list[str]], list[dict[str, Any]]]


@dataclass
class WorkingSet:
    """E8 output: bounded suspects + neighborhood for Localize."""

    case_id: str
    tenant: str
    seed_ci_id: str
    detect_class: str
    hops: int
    direction: str
    ci_ids: list[str]
    neighbor_ids: list[str]
    edges: list[dict[str, Any]]
    paths_to_hosts: list[list[str]]
    paths_to_databases: list[list[str]]
    sketch_refs: list[dict[str, Any]] = field(default_factory=list)
    evidence_budget: dict[str, Any] = field(default_factory=dict)
    confidence_bearing_only: bool = True
    walk_profile: str = ""
    relations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_working_set(
    snapshot: dict[str, Any],
    seed: CaseSeed,
    *,
    hops: int | None = None,
    direction: str | None = None,
    relations: Iterable[str] | None = None,
    profile: WalkProfile | None = None,
    confidence_bearing_only: bool = True,
    sketch_provider: SketchProvider | None = None,
    max_paths: int = 10,
) -> WorkingSet:
    """Read-join Scope: walk ``map/`` from the CaseSeed tip into a WorkingSet.

    Does not mutate GraphState or Dest. ``sketch_provider``, when set, may attach
    history refs keyed by the same ``ci_id`` strings (entity_id ≡ ci_id).

    Defaults for hops / direction / relations come from the detect-class walk
    profile (``MAP_SCOPE_WALK_POLICY`` §4). Explicit kwargs override the profile.
    """
    resolved = profile or resolve_walk_profile(seed.detect_class, labels=seed.labels)
    walk_hops = resolved.hops if hops is None else hops
    walk_direction = resolved.direction if direction is None else direction
    if relations is None:
        rel_set = resolved.relations
    else:
        rel_set = frozenset(relations)
    rel_list = sorted(rel_set)

    walk_kw: dict[str, Any] = {
        "hops": walk_hops,
        "direction": walk_direction,
        "relations": rel_set,
        "confidence_bearing_only": confidence_bearing_only,
    }

    ci_ids = reachable_ci_ids(
        snapshot,
        seed.seed_ci_id,
        include_seed=True,
        **walk_kw,
    )
    n_ids = neighbor_ids(snapshot, seed.seed_ci_id, **walk_kw)
    edge_rows = neighbors(snapshot, seed.seed_ci_id, **walk_kw)

    path_kw: dict[str, Any] = {
        "max_hops": walk_hops + 1,
        "direction": walk_direction,
        "relations": rel_set,
        "confidence_bearing_only": confidence_bearing_only,
        "max_paths": max_paths,
    }
    paths_host = find_paths(
        snapshot,
        seed.seed_ci_id,
        target_ci_types=["Host"],
        **path_kw,
    )
    paths_db = find_paths(
        snapshot,
        seed.seed_ci_id,
        target_ci_types=["Database"],
        **path_kw,
    )

    sketches: list[dict[str, Any]] = []
    if sketch_provider is not None:
        sketches = list(sketch_provider(seed, ci_ids))

    return WorkingSet(
        case_id=seed.case_id,
        tenant=seed.tenant,
        seed_ci_id=seed.seed_ci_id,
        detect_class=seed.detect_class,
        hops=walk_hops,
        direction=walk_direction,
        ci_ids=ci_ids,
        neighbor_ids=n_ids,
        edges=edge_rows,
        paths_to_hosts=paths_host,
        paths_to_databases=paths_db,
        sketch_refs=sketches,
        evidence_budget={
            "max_hops": walk_hops,
            "max_cis": len(ci_ids),
            "max_edges": len(edge_rows),
            "max_sketch_refs": len(sketches),
            "confidence_bearing_only": confidence_bearing_only,
            "walk_profile": resolved.name,
            "relations": rel_list,
        },
        confidence_bearing_only=confidence_bearing_only,
        walk_profile=resolved.name,
        relations=rel_list,
    )
