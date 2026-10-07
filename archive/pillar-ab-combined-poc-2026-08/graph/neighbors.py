from __future__ import annotations

from collections import deque
from typing import Any


def neighbors(
    snapshot: dict[str, Any],
    ci_id: str,
    *,
    relation: str | None = None,
    hops: int = 1,
) -> list[dict[str, Any]]:
    """Return directed outbound edges (and destinations) within hops."""
    by_src: dict[str, list[dict]] = {}
    for e in snapshot.get("edges", []):
        by_src.setdefault(e["src_ci_id"], []).append(e)

    seen_nodes = {ci_id}
    results: list[dict[str, Any]] = []
    q: deque[tuple[str, int]] = deque([(ci_id, 0)])
    while q:
        node, depth = q.popleft()
        if depth >= hops:
            continue
        for e in by_src.get(node, []):
            if relation and e["relation"] != relation:
                continue
            results.append(e)
            dst = e["dst_ci_id"]
            if dst not in seen_nodes:
                seen_nodes.add(dst)
                q.append((dst, depth + 1))
    return results


def neighbor_ids(snapshot: dict[str, Any], ci_id: str, **kwargs: Any) -> list[str]:
    return sorted({e["dst_ci_id"] for e in neighbors(snapshot, ci_id, **kwargs)})
