from __future__ import annotations

from typing import Any

from ab_shared.dest import Dest
from ab_shared.identity_gate import ResolvedOnlyGate
from ab_shared.ingest_source import IngestSource
from graph.graph_builder import GraphState, apply_topo_updates, load_seed_topology
from graph.maintain import maintain_graph_validity
from graph.snapshot import build_snapshot, publish_snapshot


class GraphWriter:
    """Single orchestrator: seed → topo ingest → map flush (+ optional E5 maintain)."""

    def __init__(self, tenant: str = "default", gate: ResolvedOnlyGate | None = None) -> None:
        self.tenant = tenant
        self.gate = gate or ResolvedOnlyGate()
        self.state: GraphState | None = None

    def load_seed(self, path_or_dict: Any, *, tenant: str | None = None) -> None:
        self.state = load_seed_topology(path_or_dict, tenant=tenant or self.tenant)

    @property
    def rejects(self) -> list[tuple[dict, str]]:
        if self.state is None:
            return []
        return self.state.rejects

    def ingest(self, source: IngestSource) -> None:
        if self.state is None:
            self.state = GraphState(tenant=self.tenant)
        apply_topo_updates(self.state, source, self.gate)

    def flush(self, dest: Dest, *, version: str = "1") -> dict[str, Any]:
        if self.state is None:
            self.state = GraphState(tenant=self.tenant)
        snapshot = build_snapshot(self.state, version=version)
        publish_snapshot(dest, snapshot)
        return snapshot

    def maintain_validity(
        self,
        as_of: str,
        *,
        corroborating_max_age_seconds: int = 3600,
    ) -> dict[str, int]:
        if self.state is None:
            return {"expired_edges": 0, "stale_corroborating": 0}
        return maintain_graph_validity(
            self.state,
            as_of,
            corroborating_max_age_seconds=corroborating_max_age_seconds,
        )
