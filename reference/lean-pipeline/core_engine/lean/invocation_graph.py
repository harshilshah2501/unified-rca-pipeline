"""Typed invocation graph — effect→cause upstream walk."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InvocationGraph:
    """Directed graph: edge from effect to cause (symptom walks upstream)."""

    upstream: dict[str, list[str]] = field(default_factory=dict)
    node_types: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_topology(cls, topology: dict) -> InvocationGraph:
        upstream: dict[str, list[str]] = {n["id"]: [] for n in topology["nodes"]}
        node_types = {n["id"]: n["type"] for n in topology["nodes"]}
        for edge in topology["edges"]:
            upstream.setdefault(edge["from"], []).append(edge["to"])
        return cls(upstream=upstream, node_types=node_types)

    def upstream_of(self, node_id: str) -> list[str]:
        return list(self.upstream.get(node_id, []))

    def collect_upstream(self, start: str) -> list[str]:
        """BFS upstream from start; returns candidates in discovery order."""
        queue = [start]
        visited: set[str] = set()
        candidates: list[str] = []
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for up in self.upstream_of(node):
                if up not in visited:
                    candidates.append(up)
                    queue.append(up)
        return candidates
