"""E9 Localize — WorkingSet → LeafClaim (teaching heuristics).

Identify (E10) and Package (E11) continue from this LeafClaim in Increment 3.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from graph.case_path.scope import WorkingSet

# Prefer deeper dependency leaves for ERROR / AVAILABILITY teaching stories.
_LEAF_TYPE_PREF = ("Database", "Host", "Runtime", "Service")


@dataclass(frozen=True)
class LeafClaim:
    """E9 output: where to look next — not a final operator verdict."""

    case_id: str
    tenant: str
    claim_ci_id: str
    claim_ci_type: str
    detect_class: str
    path_from_seed: tuple[str, ...]
    rationale: str
    confidence: str = "medium"
    alternatives: tuple[str, ...] = ()
    labels: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path_from_seed"] = list(self.path_from_seed)
        d["alternatives"] = list(self.alternatives)
        return d


def localize_leaf(
    snapshot: dict[str, Any],
    working_set: WorkingSet,
    *,
    prefer_ci: str | None = None,
) -> LeafClaim:
    """Pick a leaf claim from the WorkingSet.

    Teaching rules (fabric film 2 / ERROR path):
    1. If ``prefer_ci`` is in the WorkingSet, claim it (lab goldens).
    2. Else prefer deepest path ending at Database, then Host.
    3. Else fall back to seed CI (thin graph).
    """
    nodes = {n["ci_id"]: n for n in snapshot.get("nodes") or []}
    seed = working_set.seed_ci_id
    detect = working_set.detect_class

    if prefer_ci and prefer_ci in working_set.ci_ids:
        path = _path_covering(working_set, prefer_ci) or [seed, prefer_ci]
        n = nodes.get(prefer_ci) or {}
        return LeafClaim(
            case_id=working_set.case_id,
            tenant=working_set.tenant,
            claim_ci_id=prefer_ci,
            claim_ci_type=str(n.get("ci_type") or "Unknown"),
            detect_class=detect,
            path_from_seed=tuple(path),
            rationale=f"lab prefer_ci={prefer_ci} present on WorkingSet",
            confidence="high",
            alternatives=_alt_leaves(working_set, prefer_ci),
        )

    # Deepest Database path
    db_paths = sorted(working_set.paths_to_databases, key=len, reverse=True)
    if db_paths:
        path = db_paths[0]
        leaf = path[-1]
        n = nodes.get(leaf) or {}
        return LeafClaim(
            case_id=working_set.case_id,
            tenant=working_set.tenant,
            claim_ci_id=leaf,
            claim_ci_type=str(n.get("ci_type") or "Database"),
            detect_class=detect,
            path_from_seed=tuple(path),
            rationale=(
                f"deepest Database leaf on WorkingSet "
                f"({len(path) - 1} hops from {seed}); detect_class={detect}"
            ),
            confidence="medium",
            alternatives=_alt_leaves(working_set, leaf),
        )

    host_paths = sorted(working_set.paths_to_hosts, key=len, reverse=True)
    if host_paths:
        path = host_paths[0]
        leaf = path[-1]
        n = nodes.get(leaf) or {}
        return LeafClaim(
            case_id=working_set.case_id,
            tenant=working_set.tenant,
            claim_ci_id=leaf,
            claim_ci_type=str(n.get("ci_type") or "Host"),
            detect_class=detect,
            path_from_seed=tuple(path),
            rationale=f"deepest Host leaf on WorkingSet from {seed}",
            confidence="medium",
            alternatives=_alt_leaves(working_set, leaf),
        )

    # Thin fallback
    n = nodes.get(seed) or {}
    return LeafClaim(
        case_id=working_set.case_id,
        tenant=working_set.tenant,
        claim_ci_id=seed,
        claim_ci_type=str(n.get("ci_type") or working_set.detect_class),
        detect_class=detect,
        path_from_seed=(seed,),
        rationale="no Database/Host path in WorkingSet; claim remains on seed",
        confidence="low",
        alternatives=(),
    )


def _path_covering(ws: WorkingSet, ci: str) -> list[str] | None:
    for bucket in (ws.paths_to_databases, ws.paths_to_hosts):
        for p in bucket:
            if ci in p:
                # Truncate at claim
                i = p.index(ci)
                return p[: i + 1]
    if ci == ws.seed_ci_id:
        return [ci]
    if ci in ws.neighbor_ids:
        return [ws.seed_ci_id, ci]
    return None


def _alt_leaves(ws: WorkingSet, chosen: str) -> tuple[str, ...]:
    alts: list[str] = []
    for p in ws.paths_to_databases + ws.paths_to_hosts:
        leaf = p[-1]
        if leaf != chosen and leaf not in alts:
            alts.append(leaf)
    return tuple(alts[:5])
