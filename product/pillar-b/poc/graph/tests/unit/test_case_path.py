"""stub case-path harness — Signal storm → CaseSeed → WorkingSet → LeafClaim."""

from __future__ import annotations

import json

from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from graph.case_path import (
    CaseSeed,
    build_working_set,
    curate_storm,
    load_signal_storm,
    localize_leaf,
    resolve_walk_profile,
)
from graph.graph_writer import GraphWriter
from graph.maintain import MAINTAIN_HARD_DOWNGRADED, apply_declared_freshness
from graph.snapshot import build_snapshot
from graph.graph_builder import load_estate_bootstrap_state

I2 = SAMPLE_ESTATE / "cases" / "stub_case_path"


def _published_checkout_map():
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    return writer.publish_map(MemoryDest())


def test_i2_curate_one_seed_from_storm():
    expected = json.loads((I2 / "expected_case_path.json").read_text(encoding="utf-8"))
    storm = load_signal_storm(I2 / "signal_storm.json")
    assert len(storm) == 4
    seed = curate_storm(
        storm,
        case_id=expected["case_id"],
        prefer_seed_ci=expected["seed_ci_id"],
    )
    assert seed.seed_ci_id == "checkout-api"
    assert seed.detect_class == "ERROR"
    assert seed.first_down_ts == expected["first_down_ts"]
    assert set(seed.merged_signal_ids) == set(expected["merged_signal_ids"])
    # CaseSeed must not look like a map write API
    assert not hasattr(seed, "publish_map")


def test_i2_curate_picks_highest_class_without_prefer():
    storm = load_signal_storm(I2 / "signal_storm.json")
    seed = curate_storm(storm, case_id="auto")
    # ERROR on checkout-api outranks SLOWDOWN/SATURATION tips
    assert seed.seed_ci_id == "checkout-api"
    assert seed.detect_class == "ERROR"


def test_i2_working_set_from_case_seed():
    expected = json.loads((I2 / "expected_case_path.json").read_text(encoding="utf-8"))
    snap = _published_checkout_map()
    seed = curate_storm(
        load_signal_storm(I2 / "signal_storm.json"),
        case_id=expected["case_id"],
        prefer_seed_ci="checkout-api",
    )
    ws = build_working_set(snap, seed, hops=2, confidence_bearing_only=False)
    assert ws.seed_ci_id == "checkout-api"
    for cid in expected["working_set_must_include"]:
        assert cid in ws.ci_ids, f"missing {cid} in {ws.ci_ids}"
    assert "payments-db" in ws.neighbor_ids
    assert any(p[-1] == "payments-db" for p in ws.paths_to_databases)
    assert ws.sketch_refs == []  # map-only unless provider injected
    assert ws.evidence_budget["max_hops"] == 2


def test_i2_working_set_accepts_sketch_provider_hook():
    snap = _published_checkout_map()
    seed = curate_storm(
        load_signal_storm(I2 / "signal_storm.json"),
        prefer_seed_ci="checkout-api",
    )

    def provider(_seed, ci_ids):
        return [
            {"entity_id": cid, "metric_id": "request.latency_ms", "room": "history"}
            for cid in ci_ids
            if cid == "checkout-api"
        ]

    ws = build_working_set(snap, seed, hops=1, sketch_provider=provider)
    assert len(ws.sketch_refs) == 1
    assert ws.sketch_refs[0]["entity_id"] == "checkout-api"


def test_i2_localize_deepest_database_leaf():
    expected = json.loads((I2 / "expected_case_path.json").read_text(encoding="utf-8"))
    snap = _published_checkout_map()
    seed = curate_storm(
        load_signal_storm(I2 / "signal_storm.json"),
        case_id=expected["case_id"],
        prefer_seed_ci="checkout-api",
    )
    ws = build_working_set(snap, seed, hops=2, confidence_bearing_only=False)
    claim = localize_leaf(snap, ws)
    assert claim.claim_ci_id == expected["leaf_claim_ci_id"]
    assert claim.claim_ci_type == "Database"
    assert list(claim.path_from_seed) == expected["path_spine"]
    assert claim.detect_class == "ERROR"


def test_i2_localize_prefer_ci_override():
    snap = _published_checkout_map()
    seed = curate_storm(
        load_signal_storm(I2 / "signal_storm.json"),
        prefer_seed_ci="checkout-api",
    )
    ws = build_working_set(snap, seed, hops=2, confidence_bearing_only=False)
    claim = localize_leaf(snap, ws, prefer_ci="linux-server-app-01")
    assert claim.claim_ci_id == "linux-server-app-01"
    assert claim.confidence == "high"


def test_i2_end_to_end_case_path_pipeline():
    """Storm → seed → WorkingSet → LeafClaim on a live published map."""
    expected = json.loads((I2 / "expected_case_path.json").read_text(encoding="utf-8"))
    snap = _published_checkout_map()
    seed = curate_storm(
        load_signal_storm(I2 / "signal_storm.json"),
        case_id=expected["case_id"],
        prefer_seed_ci="checkout-api",
    )
    ws = build_working_set(snap, seed, hops=2, confidence_bearing_only=False)
    claim = localize_leaf(snap, ws)
    assert claim.case_id == seed.case_id == ws.case_id
    assert claim.claim_ci_id == "payments-db"
    assert "payments-db" in ws.ci_ids
    # Still not Identify / Package
    assert "evidence_bundle" not in claim.to_dict()
    assert "verdict" not in claim.to_dict()


def test_i2_confidence_bearing_can_block_database_path():
    """Hard-downgrade every edge into payments-db → no Database path under filter."""
    state = load_estate_bootstrap_state(SAMPLE_ESTATE / "topology.bootstrap.json")
    for e in state.edges.values():
        if e["target_id"] == "payments-db":
            e["valid_from"] = "2025-01-01T00:00:00Z"
    apply_declared_freshness(state, "2026-08-20T00:00:00Z", hard_downgrade_days=30)
    for e in state.edges.values():
        if e["target_id"] == "payments-db":
            assert e["maintain_status"] == MAINTAIN_HARD_DOWNGRADED
    snap = build_snapshot(state)
    seed = curate_storm(
        load_signal_storm(I2 / "signal_storm.json"),
        prefer_seed_ci="checkout-api",
    )
    ws = build_working_set(snap, seed, hops=2, confidence_bearing_only=True)
    assert ws.paths_to_databases == []
    claim = localize_leaf(snap, ws)
    # Falls back to deepest Host (runs_on still bearing)
    assert claim.claim_ci_type == "Host"
    assert claim.claim_ci_id == "linux-server-app-01"


def _error_vs_monitor_snap() -> dict:
    """Minimal fixture: app depends_on + monitored_by collector on the same seed."""
    return {
        "version": "1",
        "nodes": [
            {"entity_id": "checkout-api", "type": "service", "name": "checkout-api"},
            {"entity_id": "payments-db", "type": "db", "name": "payments-db"},
            {
                "entity_id": "otel-collector",
                "type": "service",
                "name": "otel-collector",
            },
        ],
        "edges": [
            {
                "edge_id": "e-depends",
                "source_id": "checkout-api",
                "target_id": "payments-db",
                "edge_type": "DEPENDS_ON",
            },
            {
                "edge_id": "e-monitor",
                "source_id": "checkout-api",
                "target_id": "otel-collector",
                "edge_type": "MONITORED_BY",
            },
        ],
    }


def test_error_profile_excludes_monitored_by_from_working_set():
    """ERROR Scope profile must not pull monitor collectors into the WorkingSet."""
    snap = _error_vs_monitor_snap()
    seed = CaseSeed(
        case_id="case-error-profile",
        tenant="default",
        seed_ci_id="checkout-api",
        seed_ci_type="Service",
        detect_class="ERROR",
        first_down_ts="2026-03-20T09:00:00Z",
        merged_signal_ids=("sig-1",),
        merge_rationale="fixture",
    )
    profile = resolve_walk_profile("ERROR")
    assert "monitored_by" not in profile.relations
    assert "depends_on" in profile.relations

    ws = build_working_set(snap, seed)
    assert ws.walk_profile == "error_availability"
    assert "monitored_by" not in ws.relations
    assert "payments-db" in ws.ci_ids
    assert "otel-collector" not in ws.ci_ids
    assert "otel-collector" not in ws.neighbor_ids
    edge_types = {e["edge_type"] for e in ws.edges}
    assert "DEPENDS_ON" in edge_types
    assert "MONITORED_BY" not in edge_types
    assert any(p[-1] == "payments-db" for p in ws.paths_to_databases)


def test_monitoring_profile_includes_monitored_by():
    """MONITORING_UNAVAILABLE Scope profile keeps the collector edge."""
    snap = _error_vs_monitor_snap()
    seed = CaseSeed(
        case_id="case-mon-profile",
        tenant="default",
        seed_ci_id="checkout-api",
        seed_ci_type="Service",
        detect_class="MONITORING_UNAVAILABLE",
        first_down_ts="2026-03-20T09:00:00Z",
        merged_signal_ids=("sig-1",),
        merge_rationale="fixture",
    )
    ws = build_working_set(snap, seed)
    assert ws.walk_profile == "monitoring_unavailable"
    assert "monitored_by" in ws.relations
    assert "otel-collector" in ws.ci_ids
    assert any(e["edge_type"] == "MONITORED_BY" for e in ws.edges)


def test_anomaly_profile_defaults_to_one_hop():
    profile = resolve_walk_profile("ANOMALY")
    assert profile.hops == 1
    assert profile.relations == frozenset({"depends_on", "runs_on"})
