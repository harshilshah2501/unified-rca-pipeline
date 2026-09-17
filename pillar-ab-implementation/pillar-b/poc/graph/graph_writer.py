from __future__ import annotations

from typing import Any

from ab_shared.dest import Dest
from ab_shared.identity_gate import ResolvedOnlyGate
from ab_shared.ingest_source import IngestSource
from graph.graph_builder import GraphState, apply_topo_stream, load_estate_bootstrap_state
from graph.maintain import maintain_graph_validity
from graph.snapshot import build_snapshot, publish_snapshot


class GraphWriter:
    """Sole map write orchestrator: estate bootstrap → write_topo_stream → publish_map → optional maintain_map."""

    def __init__(self, tenant: str = "default", gate: ResolvedOnlyGate | None = None) -> None:
        self.tenant = tenant
        self.gate = gate or ResolvedOnlyGate()
        self.state: GraphState | None = None

    def load_estate_bootstrap(self, path_or_dict: Any, *, tenant: str | None = None) -> None:
        """Load optional declared starting estate into memory. Not E7 CaseSeed."""
        self.state = load_estate_bootstrap_state(path_or_dict, tenant=tenant or self.tenant)

    @property
    def rejects(self) -> list[tuple[dict, str]]:
        if self.state is None:
            return []
        return self.state.rejects

    def write_topo_stream(self, source: IngestSource) -> None:
        """Write admitted topo_update lines into GraphState (NOOP / WRITE / DROP / phased).

        Does not publish to Dest — call publish_map next.
        """
        if self.state is None:
            self.state = GraphState(tenant=self.tenant)
        apply_topo_stream(self.state, source, self.gate)

    def publish_map(self, dest: Dest, *, version: str = "1") -> dict[str, Any]:
        """Validate GraphState and publish graph_snapshot.v1 (+ nodes/edges JSONL) to Dest map/."""
        if self.state is None:
            self.state = GraphState(tenant=self.tenant)
        snapshot = build_snapshot(self.state, version=version)
        publish_snapshot(dest, snapshot)
        return snapshot

    def maintain_map(
        self,
        as_of: str,
        *,
        corroborating_max_age_seconds: int = 3600,
        soft_stale_days: int | None = None,
        hard_downgrade_days: int | None = None,
    ) -> dict[str, int]:
        """E5: expire / drop stale corroborating / mark declared soft·hard — does not create edges."""
        if self.state is None:
            return {
                "expired_edges": 0,
                "stale_corroborating": 0,
                "declared_soft_stale": 0,
                "declared_hard_downgraded": 0,
            }
        kwargs: dict[str, Any] = {
            "corroborating_max_age_seconds": corroborating_max_age_seconds,
        }
        if soft_stale_days is not None:
            kwargs["soft_stale_days"] = soft_stale_days
        if hard_downgrade_days is not None:
            kwargs["hard_downgrade_days"] = hard_downgrade_days
        return maintain_graph_validity(self.state, as_of, **kwargs)
