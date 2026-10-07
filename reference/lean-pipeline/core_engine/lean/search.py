"""Best-first search over BFS frontier (PRD §2.2)."""

from __future__ import annotations

import heapq
from collections import deque
from typing import Callable

from core_engine.lean.invocation_graph import InvocationGraph


def best_first_walk(
    graph: InvocationGraph,
    start: str,
    score_fn: Callable[[str], float],
    max_expansions: int = 50,
) -> tuple[list[tuple[str, float]], list[str]]:
    """
    Expand upstream nodes by highest info-gain score first.
    Returns the score-ranked candidates and the actual expansion order.
    The latter lets callers report how many observations were needed to
    select a particular root.
    """
    frontier: list[tuple[float, int, str]] = []
    counter = 0
    visited: set[str] = set()
    results: list[tuple[str, float]] = []

    for up in graph.upstream_of(start):
        s = score_fn(up)
        heapq.heappush(frontier, (-s, counter, up))
        counter += 1

    expansions = 0
    while frontier and expansions < max_expansions:
        neg_score, _, node = heapq.heappop(frontier)
        if node in visited:
            continue
        visited.add(node)
        score = -neg_score
        results.append((node, score))
        expansions += 1
        for up in graph.upstream_of(node):
            if up not in visited and up not in {n for n, _ in results}:
                s = score_fn(up)
                heapq.heappush(frontier, (-s, counter, up))
                counter += 1

    expansion_order = [node for node, _ in results]
    results.sort(key=lambda x: x[1], reverse=True)
    return results, expansion_order


def expansions_to_target(expansion_order: list[str], start: str, target: str) -> int:
    """Return best-first nodes selected until ``target`` is selected."""
    if target == start:
        return 1
    try:
        return expansion_order.index(target) + 1
    except ValueError:
        # The caller selected a rule-derived candidate outside the walk.
        # Report all observed candidates, rather than inventing a hit.
        return len(expansion_order)


def naive_bfs_expansions(
    graph: InvocationGraph,
    start: str,
    target: str,
    max_expansions: int = 50,
) -> int:
    """Return FIFO upstream nodes visited before selecting ``target``."""
    queue: deque[str] = deque([start])
    visited: set[str] = set()
    expansions = 0

    while queue and expansions < max_expansions:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        if node != start:
            expansions += 1
        if node == target:
            return 1 if target == start else expansions
        queue.extend(up for up in graph.upstream_of(node) if up not in visited)

    return 1 if target == start else expansions
