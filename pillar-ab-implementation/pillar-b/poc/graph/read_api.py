"""Thin read API wrappers over ``neighbors`` for callers that prefer get_* names."""

from __future__ import annotations

from typing import Any

from graph.neighbors import neighbor_ids, neighbors


def get_neighbors(snapshot: dict[str, Any], ci_id: str, **kwargs: Any) -> list[str]:
    return neighbor_ids(snapshot, ci_id, **kwargs)


def get_neighbor_edges(snapshot: dict[str, Any], ci_id: str, **kwargs: Any) -> list[dict]:
    return neighbors(snapshot, ci_id, **kwargs)
