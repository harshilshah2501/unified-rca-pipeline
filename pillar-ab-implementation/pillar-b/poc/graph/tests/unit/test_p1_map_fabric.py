"""Increment 1 — P1 map fabric eval (E1–E5 map lens).

See pillar-b/docs/MAP_P1_FABRIC_EVAL.md for the stage matrix and terminology lock.
"""

from __future__ import annotations

from ab_shared.dest import MemoryDest
from ab_shared.identity_gate import ResolvedOnlyGate
from ab_shared.ingest_source import JsonlIngestSource, ListIngestSource
from ab_shared.paths import FIXTURES
from ab_shared.schema import is_valid
from graph.graph_writer import GraphWriter
from graph.maintain import (
    DECLARED_HARD_DOWNGRADE_DAYS,
    DECLARED_SOFT_STALE_DAYS,
    MAINTAIN_HARD_DOWNGRADED,
    MAINTAIN_SOFT_STALE,
    apply_declared_freshness,
    confidence_bearing_edges,
)
from graph.neighbors import neighbor_ids
from graph.provenance import build_discovered_via
from graph.snapshot import load_snapshot

# ---------------------------------------------------------------------------
# E1 Collect boundary — Pillar B simulates post-E2; Collect rejects ≠ DROPs
# ---------------------------------------------------------------------------


def test_e1_fixture_lines_carry_ingest_v1_spine():
    """Wire admit shape: lab fixtures look like Collect-admitted ingest.v1."""
    for name in ("stream.resolved.jsonl", "stream.reject.jsonl"):
        for rec in JsonlIngestSource(FIXTURES / name).records():
            assert rec.get("schema_version") == "ingest.v1"
            assert "signal_class" in rec
            assert "ts" in rec and "tenant" in rec and "ci_id" in rec
            assert is_valid("ingest_v1.schema.json", rec)


def test_e1_unknown_signal_class_is_graphwriter_noop_not_drop():
    """Collect would reject unknown classes; GraphWriter NOOPs non-topo_update."""
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    before_nodes = len(writer.state.nodes)
    before_edges = len(writer.state.edges)
    writer.apply_stream(
        ListIngestSource(
            [
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T03:30:00Z",
                    "tenant": "default",
                    "ci_id": "checkout-api",
                    "ci_type": "Service",
                    "signal_class": "not_a_real_class",
                    "identity": {"status": "resolved"},
                }
            ]
        )
    )
    assert writer.rejects == []
    assert len(writer.state.nodes) == before_nodes
    assert len(writer.state.edges) == before_edges


# ---------------------------------------------------------------------------
# E2 Identity — ResolvedOnlyGate is the hard door into GraphWriter
# ---------------------------------------------------------------------------


def test_e2_gate_rejects_unresolved_and_synthesized():
    gate = ResolvedOnlyGate()
    assert gate.admit({"identity": {"status": "resolved"}}).accepted
    assert not gate.admit({"identity": {"status": "unattributed"}}).accepted
    assert not gate.admit({"identity": {"status": "synthesized"}}).accepted
    assert not gate.admit({}).accepted


def test_e2_unresolved_topo_never_silent_map_write():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    edge_count = len(writer.state.edges)
    writer.apply_stream(
        ListIngestSource(
            [
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T03:30:00Z",
                    "tenant": "default",
                    "ci_id": "ghost-svc",
                    "ci_type": "Service",
                    "signal_class": "topo_update",
                    "relation": "depends_on",
                    "src_ci_id": "ghost-svc",
                    "dst_ci_id": "payments-db",
                    "identity": {"status": "unattributed"},
                }
            ]
        )
    )
    reasons = {r for _, r in writer.rejects}
    assert "identity_unresolved" in reasons
    assert "ghost-svc" not in writer.state.nodes
    assert len(writer.state.edges) == edge_count


def test_e2_telemetry_key_index_is_design_stub_documented():
    """PoC does not ship telemetry_key_index; guide names it as Design."""
    guide = (FIXTURES.parents[2] / "docs" / "MAP_P1_FABRIC_EVAL.md").read_text(encoding="utf-8")
    assert "telemetry_key_index" in guide
    assert "Design" in guide


# ---------------------------------------------------------------------------
# E3 Topology — NOOP / WRITE / DROP / phased / idempotency
# ---------------------------------------------------------------------------


def test_e3_noop_non_topo_classes():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    n0, e0 = len(writer.state.nodes), len(writer.state.edges)
    lines = []
    for signal_class in ("metric_sample", "event", "trace_span", "anomaly"):
        lines.append(
            {
                "schema_version": "ingest.v1",
                "ts": "2026-08-20T03:30:00Z",
                "tenant": "default",
                "ci_id": "checkout-api",
                "ci_type": "Service",
                "signal_class": signal_class,
                "name": "probe",
                "value": 1.0,
                "identity": {"status": "resolved"},
            }
        )
    writer.apply_stream(ListIngestSource(lines))
    assert writer.rejects == []
    assert len(writer.state.nodes) == n0
    assert len(writer.state.edges) == e0


def test_e3_write_wave1_happy_path():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    assert writer.rejects == []
    snap = writer.publish_map(MemoryDest())
    assert any(e["relation"] == "depends_on" for e in snap["edges"])
    assert "payments-db" in neighbor_ids(snap, "checkout-api")


def test_e3_drop_reject_tape_codes():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.reject.jsonl"))
    reasons = {r for _, r in writer.rejects}
    assert reasons >= {
        "identity_unresolved",
        "identity_synthesized",
        "never_ci_vertex",
        "unknown_relation",
    }
    snap = writer.publish_map(MemoryDest())
    present = {n["ci_id"] for n in snap["nodes"]}
    assert "alert-1" not in present
    assert "chg-1" not in present


def test_e3_phased_map_noop_catalog_not_wave1():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    n0, e0 = len(writer.state.nodes), len(writer.state.edges)
    writer.apply_stream(
        ListIngestSource(
            [
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T03:30:00Z",
                    "tenant": "default",
                    "ci_id": "checkout-api",
                    "ci_type": "Service",
                    "signal_class": "topo_update",
                    "relation": "mounts",
                    "src_ci_id": "checkout-api",
                    "dst_ci_id": "linux-server-app-01",
                    "identity": {"status": "resolved"},
                }
            ]
        )
    )
    assert writer.rejects == []
    assert len(writer.state.edges) == e0
    assert not any(e["relation"] == "mounts" for e in writer.state.edges.values())
    assert len(writer.state.nodes) == n0


def test_e3_upsert_idempotency_replay():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    src = JsonlIngestSource(FIXTURES / "stream.resolved.jsonl")
    writer.apply_stream(src)
    after_first = len(writer.state.edges)
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    assert len(writer.state.edges) == after_first
    edge_ids = list(writer.state.edges.keys())
    assert len(edge_ids) == len(set(edge_ids))


def test_e3_bootstrap_provenance_not_caseseed():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    for edge in writer.state.edges.values():
        dv = edge["discovered_via"]
        assert dv["evidence_type"] == "declared"
        assert dv["telemetry_source"] == "topology.bootstrap"


# ---------------------------------------------------------------------------
# E4 orthogonality — non-topo never mutates map spine
# ---------------------------------------------------------------------------


def test_e4_mixed_tape_map_spine_unchanged_by_non_topo():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    spine_edges = sorted(writer.state.edges.keys())
    spine_nodes = sorted(writer.state.nodes.keys())
    writer.apply_stream(
        ListIngestSource(
            [
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T04:00:00Z",
                    "tenant": "default",
                    "ci_id": "checkout-api",
                    "ci_type": "Service",
                    "signal_class": sc,
                    "name": "noise",
                    "value": 9.0,
                    "identity": {"status": "resolved"},
                }
                for sc in ("metric_sample", "event", "trace_span", "anomaly")
            ]
        )
    )
    assert sorted(writer.state.edges.keys()) == spine_edges
    assert sorted(writer.state.nodes.keys()) == spine_nodes
    assert writer.rejects == []


# ---------------------------------------------------------------------------
# E5 Maintain — declared soft/hard + versioned re-flush
# ---------------------------------------------------------------------------


def test_e5_declared_soft_and_hard_with_fixture_clock():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    # Bootstrap edges use valid_from=2026-08-20; move clock past soft then hard.
    soft_as_of = "2026-08-28T00:00:00Z"  # 8 days later → soft
    stats_soft = writer.maintain_map(
        soft_as_of,
        soft_stale_days=DECLARED_SOFT_STALE_DAYS,
        hard_downgrade_days=DECLARED_HARD_DOWNGRADE_DAYS,
    )
    assert stats_soft["declared_soft_stale"] >= 1
    assert stats_soft["declared_hard_downgraded"] == 0
    soft_edges = [
        e for e in writer.state.edges.values() if e.get("maintain_status") == MAINTAIN_SOFT_STALE
    ]
    assert soft_edges

    hard_as_of = "2026-09-25T00:00:00Z"  # >30 days
    stats_hard = writer.maintain_map(
        hard_as_of,
        soft_stale_days=DECLARED_SOFT_STALE_DAYS,
        hard_downgrade_days=DECLARED_HARD_DOWNGRADE_DAYS,
    )
    assert stats_hard["declared_hard_downgraded"] >= 1
    hard_edges = [
        e
        for e in writer.state.edges.values()
        if e.get("maintain_status") == MAINTAIN_HARD_DOWNGRADED
    ]
    assert hard_edges
    assert all(e["discovered_via"]["confidence"] == "n/a" for e in hard_edges)
    bearing = confidence_bearing_edges(writer.state)
    assert all(e.get("maintain_status") != MAINTAIN_HARD_DOWNGRADED for e in bearing)
    # Soft/hard mark — do not delete declared edges from the published map.
    assert len(writer.state.edges) >= len(hard_edges)


def test_e5_maintain_does_not_create_edges():
    from graph.graph_builder import GraphState

    state = GraphState()
    state.edges["e_decl"] = {
        "schema_version": "graph_edge.v1",
        "tenant": "default",
        "edge_id": "e_decl",
        "src_ci_id": "a",
        "dst_ci_id": "b",
        "relation": "depends_on",
        "discovered_via": build_discovered_via("declared"),
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_to": None,
    }
    before = set(state.edges.keys())
    apply_declared_freshness(state, "2026-03-01T00:00:00Z")
    assert set(state.edges.keys()) == before


def test_e5_version_bump_reflush_still_walkable():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    dest = MemoryDest()
    before = writer.publish_map(dest, version="1")
    for edge in writer.state.edges.values():
        if edge.get("discovered_via", {}).get("telemetry_source") == "apm":
            edge["valid_to"] = "2026-08-20T03:00:00Z"
            break
    stats = writer.maintain_map("2026-08-20T04:00:00Z")
    assert stats["expired_edges"] >= 1
    after = writer.publish_map(dest, version="2")
    assert after["version"] == "2"
    assert len(after["edges"]) < len(before["edges"])
    loaded = load_snapshot(dest)
    assert loaded is not None
    assert neighbor_ids(loaded, "checkout-api")  # still walkable after maintain
