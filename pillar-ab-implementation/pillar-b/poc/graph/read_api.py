"""Thin read API wrappers over ``neighbors`` for callers that prefer get_* names."""

from __future__ import annotations

from typing import Any

from graph.neighbors import find_paths, neighbor_ids, neighbors, reachable_ci_ids


def get_neighbors(snapshot: dict[str, Any], ci_id: str, **kwargs: Any) -> list[str]:
    return neighbor_ids(snapshot, ci_id, **kwargs)


def get_neighbor_edges(snapshot: dict[str, Any], ci_id: str, **kwargs: Any) -> list[dict]:
    return neighbors(snapshot, ci_id, **kwargs)


def get_reachable(snapshot: dict[str, Any], seed_ci: str, **kwargs: Any) -> list[str]:
    """WorkingSet-lite CI set from a seed (map-only)."""
    return reachable_ci_ids(snapshot, seed_ci, **kwargs)


def get_paths(snapshot: dict[str, Any], seed_ci: str, **kwargs: Any) -> list[list[str]]:
    return find_paths(snapshot, seed_ci, **kwargs)
