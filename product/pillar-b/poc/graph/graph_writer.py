"""Public orchestrator for Motadata Pillar B map writes.

``GraphWriter`` is the only library surface other code should call to mutate and
publish ``map/``. In the PoC, ``cli_publish_map`` (and unit tests) call it; in
product intent a Topology writer service would call the same verbs on a
continuous post-E2 stream.

Admit (dual): Motadata SoT is ``writer_stream.v1`` with a ``topology`` block
(presence predicate — no ``fact_kind``). Lab fixtures may still send legacy
``ingest.v1`` with ``fact_kind=topo_update``. See ``WRITER_REGULATOR.md``.

Internal modules (builder, catalog, qualify, snapshot, maintain) are for this
class and focused unit tests — not for Diagnose.
"""

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
        # Same resolved-only identity policy as Pillar A sketches.
        self.gate = gate or ResolvedOnlyGate()
        # None until bootstrap or first write_topo_stream; holds in-memory estate.
        self.state: GraphState | None = None

    def load_estate_bootstrap(self, path_or_dict: Any, *, tenant: str | None = None) -> None:
        """Load optional declared starting estate into memory (first fill / CMDB-style seed)."""
        self.state = load_estate_bootstrap_state(path_or_dict, tenant=tenant or self.tenant)

    @property
    def rejects(self) -> list[tuple[dict, str]]:
        """DROP tape for this run: ``(record, reason_code)`` pairs."""
        if self.state is None:
            return []
        return self.state.rejects

    def write_topo_stream(self, source: IngestSource) -> None:
        """Admit-triage topology claims into GraphState (NOOP / WRITE / DROP).

        Accepts ``writer_stream.v1`` ``topology`` blocks or legacy ``fact_kind=topo_update``.
        Does not publish to Dest — call ``publish_map`` next. Only upserts in-memory GraphState.
        """
        if self.state is None:
            self.state = GraphState(tenant=self.tenant)
        apply_topo_stream(self.state, source, self.gate)

    def publish_map(
        self,
        dest: Dest,
        *,
        version: str = "1",
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Validate GraphState and cold-publish present ``map/``.

        ``profile``: ``files.v1`` (default / MemoryDest) or ``vortex_s3.v1`` (FileDest Motadata SoT).
        Override default with env ``POC_MAP_DEST_PROFILE``.
        """
        if self.state is None:
            self.state = GraphState(tenant=self.tenant)
        snapshot = build_snapshot(self.state, version=version)
        publish_snapshot(dest, snapshot, profile=profile)
        return snapshot

    def maintain_map(
        self,
        as_of: str,
        *,
        corroborating_max_age_seconds: int = 3600,
        soft_stale_days: int | None = None,
        hard_downgrade_days: int | None = None,
    ) -> dict[str, int]:
        """E5: expire / drop stale stream edges / mark declared soft·hard — does not create edges.

        Call ``publish_map`` again afterward if Dest should reflect maintain marks.
        Uses Motadata ``valid_to`` / ``origin`` — not ``discovered_via`` tiers.
        """
        if self.state is None:
            return {
                "expired_edges": 0,
                "stale_corroborating": 0,
                "declared_soft_stale": 0,
                "declared_hard_downgraded": 0,
                "nodes_touched": 0,
            }
        kwargs: dict[str, Any] = {
            "corroborating_max_age_seconds": corroborating_max_age_seconds,
        }
        if soft_stale_days is not None:
            kwargs["soft_stale_days"] = soft_stale_days
        if hard_downgrade_days is not None:
            kwargs["hard_downgrade_days"] = hard_downgrade_days
        return maintain_graph_validity(self.state, as_of, **kwargs)
