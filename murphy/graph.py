"""Relationship graph for Murphy — cyclic directed infrastructure topology."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import networkx as nx

from murphy.types import Entity

if TYPE_CHECKING:
    from murphy.store import MetricStore

_MAX_GRAPH_ENTITIES = 10_000


class RelationshipGraph:
    """Cyclic directed graph over infrastructure entities."""

    def __init__(self, max_hops: int = 5) -> None:
        self._graph = nx.DiGraph()
        self._entities: dict[str, Entity] = {}
        self.max_hops = max_hops

    @property
    def entity_ids(self) -> set[str]:
        return set(self._entities.keys())

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.id] = entity
        self._graph.add_node(entity.id)

    def add_edge(self, src_id: str, dst_id: str, bidirectional: bool = True) -> None:
        self._graph.add_edge(src_id, dst_id)
        if bidirectional:
            self._graph.add_edge(dst_id, src_id)

    def neighbors(self, entity_id: str) -> list[str]:
        if entity_id not in self._graph:
            return []
        return list(self._graph.successors(entity_id))

    def in_neighbors(self, entity_id: str) -> list[str]:
        if entity_id not in self._graph:
            return []
        return list(self._graph.predecessors(entity_id))

    def bfs_from(self, start_id: str, max_hops: int | None = None) -> set[str]:
        hops = max_hops if max_hops is not None else self.max_hops
        if start_id not in self._graph:
            return {start_id}
        visited: set[str] = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        while queue:
            node, depth = queue.popleft()
            if depth >= hops:
                continue
            for neighbor in self.neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return visited

    def shortest_path_subgraph(self, src_id: str, dst_id: str) -> list[str]:
        """
        Return entities on all shortest paths from src to dst,
        ordered by increasing distance from src.
        """
        if src_id not in self._graph or dst_id not in self._graph:
            return []
        if src_id == dst_id:
            return [src_id]
        try:
            shortest_len = nx.shortest_path_length(self._graph, src_id, dst_id)
        except nx.NetworkXNoPath:
            return []

        on_path: set[str] = set()
        lengths_from_src = nx.single_source_shortest_path_length(
            self._graph, src_id, cutoff=shortest_len
        )
        lengths_to_dst = nx.single_source_shortest_path_length(
            self._graph.reverse(copy=False), dst_id, cutoff=shortest_len
        )

        for node, dist_from_src in lengths_from_src.items():
            dist_to_dst = lengths_to_dst.get(node)
            if dist_to_dst is not None and dist_from_src + dist_to_dst == shortest_len:
                on_path.add(node)

        return sorted(on_path, key=lambda n: lengths_from_src[n])

    def build_from_monitoring_db(self, app_id: str, monitoring_db: MetricStore) -> None:
        """Build graph from monitoring DB entities and type-based neighborhood rules."""
        entities = monitoring_db.get_entity_metadata(app_id)
        if not entities:
            return

        for entity in entities:
            self.add_entity(entity)

        entity_by_id = {e.id: e for e in entities}
        self._wire_explicit_edges(entities)
        self._wire_type_based_edges(entities, entity_by_id)

        seed_ids = {e.id for e in entities}
        expanded = set(seed_ids)
        frontier = set(seed_ids)
        for _ in range(self.max_hops):
            if len(expanded) >= _MAX_GRAPH_ENTITIES:
                break
            next_frontier: set[str] = set()
            for entity_id in frontier:
                for neighbor_id in self._metadata_neighbors(entity_by_id.get(entity_id)):
                    if neighbor_id in entity_by_id and neighbor_id not in expanded:
                        entity = entity_by_id[neighbor_id]
                        self.add_entity(entity)
                        expanded.add(neighbor_id)
                        next_frontier.add(neighbor_id)
            for entity_id in frontier:
                for neighbor_id in self.neighbors(entity_id):
                    if neighbor_id not in expanded and neighbor_id in entity_by_id:
                        expanded.add(neighbor_id)
                        next_frontier.add(neighbor_id)
            frontier = next_frontier
            if not frontier:
                break

    def prune_candidates(
        self,
        symptom_entity: str,
        current_metrics: dict[str, dict[str, float]],
        historical_stats: dict[str, dict[str, tuple[float, float]]],
        threshold_stdevs: float = 1.0,
    ) -> set[str]:
        """
        BFS from symptom entity; keep entities with any metric exceeding
        conservative threshold (threshold_stdevs std from historical mean).
        """
        reachable = self.bfs_from(symptom_entity, self.max_hops)
        candidates: set[str] = set()
        for entity_id in reachable:
            metrics = current_metrics.get(entity_id, {})
            stats = historical_stats.get(entity_id, {})
            if not metrics or not stats:
                continue
            for metric_name, value in metrics.items():
                if metric_name not in stats:
                    continue
                mean, std = stats[metric_name]
                if value > mean + threshold_stdevs * std:
                    candidates.add(entity_id)
                    break
                if value < mean - threshold_stdevs * std:
                    candidates.add(entity_id)
                    break
        if symptom_entity in reachable:
            candidates.add(symptom_entity)
        return candidates

    def _wire_explicit_edges(self, entities: list[Entity]) -> None:
        for entity in entities:
            meta = entity.metadata or {}
            for neighbor_id in meta.get("neighbors", []):
                bidirectional = meta.get("bidirectional", True)
                self.add_edge(entity.id, neighbor_id, bidirectional=bidirectional)
            for edge in meta.get("directed_edges", []):
                if len(edge) == 2:
                    self.add_edge(edge[0], edge[1], bidirectional=False)

    def _wire_type_based_edges(
        self,
        entities: list[Entity],
        entity_by_id: dict[str, Entity],
    ) -> None:
        by_type: dict[str, list[Entity]] = {}
        for entity in entities:
            by_type.setdefault(entity.entity_type, []).append(entity)

        for entity in entities:
            self._add_default_edges(entity, entity_by_id, by_type)

    def _add_default_edges(
        self,
        entity: Entity,
        entity_by_id: dict[str, Entity],
        by_type: dict[str, list[Entity]],
    ) -> None:
        meta = entity.metadata or {}
        etype = entity.entity_type

        def connect(target_id: str, bidirectional: bool = True) -> None:
            if target_id in entity_by_id:
                self.add_edge(entity.id, target_id, bidirectional=bidirectional)

        if etype == "flow":
            src = meta.get("source_vm")
            dst = meta.get("destination_vm")
            if src:
                connect(src)
            if dst:
                connect(dst)

        elif etype == "vm":
            host_id = meta.get("host_id")
            if host_id:
                connect(host_id)
            for nic_id in meta.get("nic_ids", []):
                connect(nic_id)
            for container_id in meta.get("container_ids", []):
                connect(container_id)

        elif etype == "microservice":
            for container_id in meta.get("container_ids", []):
                connect(container_id)
            for upstream in meta.get("upstream", []):
                causal = meta.get("causal_direction") == "caller_to_callee"
                connect(upstream, bidirectional=not causal)
            for downstream in meta.get("downstream", []):
                causal = meta.get("causal_direction") == "caller_to_callee"
                connect(downstream, bidirectional=not causal)

        elif etype == "host":
            for vm in by_type.get("vm", []):
                if vm.metadata.get("host_id") == entity.id:
                    connect(vm.id)
            tor_id = meta.get("tor_switch_id")
            if tor_id:
                connect(tor_id)

        elif etype == "nic":
            vm_id = meta.get("vm_id")
            if vm_id:
                connect(vm_id)
            for flow_id in meta.get("flow_ids", []):
                connect(flow_id)

        elif etype == "container":
            vm_id = meta.get("vm_id")
            if vm_id:
                connect(vm_id)
            ms_id = meta.get("microservice_id")
            if ms_id:
                connect(ms_id)

    def _metadata_neighbors(self, entity: Entity | None) -> list[str]:
        if entity is None:
            return []
        meta = entity.metadata or {}
        neighbors: list[str] = list(meta.get("neighbors", []))
        neighbors.extend(meta.get("upstream", []))
        neighbors.extend(meta.get("downstream", []))
        neighbors.extend(meta.get("container_ids", []))
        if meta.get("host_id"):
            neighbors.append(meta["host_id"])
        if meta.get("vm_id"):
            neighbors.append(meta["vm_id"])
        if meta.get("source_vm"):
            neighbors.append(meta["source_vm"])
        if meta.get("destination_vm"):
            neighbors.append(meta["destination_vm"])
        return neighbors

    def shortest_path_hops(self, src_id: str, dst_id: str) -> list[str]:
        """Single shortest path (for explanation chain walking)."""
        if src_id not in self._graph or dst_id not in self._graph:
            return []
        try:
            return nx.shortest_path(self._graph, src_id, dst_id)
        except nx.NetworkXNoPath:
            return []
