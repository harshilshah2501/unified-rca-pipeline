"""Read helpers: walk a published ``graph_snapshot.v1``.

Used by tests and (product intent) Scope / Diagnose over Dest ``map/``.
Does not call GraphWriter write APIs.

Part B of the PoC (walk-through) lives here — Part A (build/maintain) writes the snapshot.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Iterable, Literal

Direction = Literal["out", "in", "both"]

# Align with maintain.py — hard-downgraded edges leave confidence-bearing walks.
_MAINTAIN_HARD = "hard_downgraded"


def _index_edges(
    snapshot: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    by_src: dict[str, list[dict[str, Any]]] = {}
    by_dst: dict[str, list[dict[str, Any]]] = {}
    for e in snapshot.get("edges") or []:
        by_src.setdefault(e["src_ci_id"], []).append(e)
        by_dst.setdefault(e["dst_ci_id"], []).append(e)
    return by_src, by_dst


def _edge_ok(
    edge: dict[str, Any],
    *,
    relation: str | None,
    relations: Iterable[str] | None,
    confidence_bearing_only: bool,
) -> bool:
    if relation and edge.get("relation") != relation:
        return False
    if relations is not None and edge.get("relation") not in set(relations):
        return False
    if confidence_bearing_only and edge.get("maintain_status") == _MAINTAIN_HARD:
        return False
    return True


def _adjacent(
    edge: dict[str, Any],
    current: str,
    *,
    direction: Direction,
) -> str | None:
    """Return the other endpoint when traversing ``direction`` from ``current``."""
    src, dst = edge["src_ci_id"], edge["dst_ci_id"]
    if direction == "out" and src == current:
        return dst
    if direction == "in" and dst == current:
        return src
    if direction == "both":
        if src == current:
            return dst
        if dst == current:
            return src
    return None


def neighbors(
    snapshot: dict[str, Any],
    ci_id: str,
    *,
    relation: str | None = None,
    relations: Iterable[str] | None = None,
    hops: int = 1,
    direction: Direction = "out",
    confidence_bearing_only: bool = False,
) -> list[dict[str, Any]]:
    """Return edges reachable within ``hops`` from ``ci_id``.

    * ``direction="out"`` — follow ``src → dst`` (default, estate dependency walk).
    * ``direction="in"`` — follow reverse (who points at this CI).
    * ``direction="both"`` — undirected hop budget.

    When ``confidence_bearing_only`` is true, edges with
    ``maintain_status=hard_downgraded`` are skipped (E5 hard mark).
    """
    if hops < 1:
        return []
    by_src, by_dst = _index_edges(snapshot)
    node_ids = {n.get("ci_id") for n in snapshot.get("nodes") or []}
    if ci_id not in node_ids and ci_id not in by_src and ci_id not in by_dst:
        return []

    results: list[dict[str, Any]] = []
    seen_edge_ids: set[str] = set()
    seen_nodes = {ci_id}
    q: deque[tuple[str, int]] = deque([(ci_id, 0)])

    while q:
        node, depth = q.popleft()
        if depth >= hops:
            continue
        candidates: list[dict[str, Any]] = []
        if direction in ("out", "both"):
            candidates.extend(by_src.get(node, []))
        if direction in ("in", "both"):
            candidates.extend(by_dst.get(node, []))
        for e in candidates:
            eid = e.get("edge_id") or id(e)
            if eid in seen_edge_ids:
                continue
            if not _edge_ok(
                e,
                relation=relation,
                relations=relations,
                confidence_bearing_only=confidence_bearing_only,
            ):
                continue
            nxt = _adjacent(e, node, direction=direction)
            if nxt is None:
                continue
            seen_edge_ids.add(str(eid))
            results.append(e)
            if nxt not in seen_nodes:
                seen_nodes.add(nxt)
                q.append((nxt, depth + 1))
    return results


def neighbor_ids(snapshot: dict[str, Any], ci_id: str, **kwargs: Any) -> list[str]:
    """Unique other-endpoint ``ci_id``s from ``neighbors`` (not including the seed)."""
    direction: Direction = kwargs.get("direction", "out")
    ids: set[str] = set()
    for e in neighbors(snapshot, ci_id, **kwargs):
        if direction == "out":
            ids.add(e["dst_ci_id"])
        elif direction == "in":
            ids.add(e["src_ci_id"])
        else:
            ids.add(e["src_ci_id"])
            ids.add(e["dst_ci_id"])
    ids.discard(ci_id)
    return sorted(ids)


def reachable_ci_ids(
    snapshot: dict[str, Any],
    seed_ci: str,
    *,
    hops: int = 2,
    direction: Direction = "out",
    relation: str | None = None,
    relations: Iterable[str] | None = None,
    confidence_bearing_only: bool = False,
    include_seed: bool = True,
) -> list[str]:
    """WorkingSet-lite: CI ids reachable from a symptom/seed within ``hops``.

    Includes the seed when ``include_seed`` and the seed exists on the snapshot.
    """
    node_ids = {n.get("ci_id") for n in snapshot.get("nodes") or []}
    if seed_ci not in node_ids:
        return []
    reached = {seed_ci} if include_seed else set()
    for e in neighbors(
        snapshot,
        seed_ci,
        hops=hops,
        direction=direction,
        relation=relation,
        relations=relations,
        confidence_bearing_only=confidence_bearing_only,
    ):
        reached.add(e["src_ci_id"])
        reached.add(e["dst_ci_id"])
    if not include_seed:
        reached.discard(seed_ci)
    return sorted(reached)


def find_paths(
    snapshot: dict[str, Any],
    seed_ci: str,
    *,
    target_ci: str | None = None,
    target_ci_types: Iterable[str] | None = None,
    max_hops: int = 4,
    direction: Direction = "out",
    relation: str | None = None,
    relations: Iterable[str] | None = None,
    confidence_bearing_only: bool = False,
    max_paths: int = 20,
) -> list[list[str]]:
    """Directed/undirected simple paths from seed to a target CI or CI type.

    Each path is a list of ``ci_id`` including seed and leaf. Empty if seed missing
    or no path within ``max_hops``. Caps at ``max_paths`` for test determinism.
    """
    nodes_by_id = {n["ci_id"]: n for n in snapshot.get("nodes") or [] if n.get("ci_id")}
    if seed_ci not in nodes_by_id:
        return []
    type_set = set(target_ci_types) if target_ci_types is not None else None
    by_src, by_dst = _index_edges(snapshot)

    paths: list[list[str]] = []
    # (node, path_ci_ids, path_edge_ids)
    q: deque[tuple[str, list[str], set[str]]] = deque([(seed_ci, [seed_ci], set())])

    def _is_target(cid: str) -> bool:
        if target_ci is not None and cid == target_ci:
            return True
        if type_set is not None:
            n = nodes_by_id.get(cid) or {}
            if n.get("ci_type") in type_set:
                return True
        return False

    while q and len(paths) < max_paths:
        node, path, used = q.popleft()
        depth = len(path) - 1
        if depth > 0 and _is_target(node):
            paths.append(path)
            continue
        if depth >= max_hops:
            continue
        candidates: list[dict[str, Any]] = []
        if direction in ("out", "both"):
            candidates.extend(by_src.get(node, []))
        if direction in ("in", "both"):
            candidates.extend(by_dst.get(node, []))
        for e in candidates:
            eid = str(e.get("edge_id") or id(e))
            if eid in used:
                continue
            if not _edge_ok(
                e,
                relation=relation,
                relations=relations,
                confidence_bearing_only=confidence_bearing_only,
            ):
                continue
            nxt = _adjacent(e, node, direction=direction)
            if nxt is None or nxt in path:
                continue
            q.append((nxt, path + [nxt], used | {eid}))
    return paths
