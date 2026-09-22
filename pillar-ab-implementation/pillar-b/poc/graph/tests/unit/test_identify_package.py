"""Increment 3 — LeafClaim → EvidenceBundle → VerdictCard."""

from __future__ import annotations

import json

from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from graph.case_path import (
    build_evidence_bundle,
    build_working_set,
    curate_storm,
    load_signal_storm,
    localize_leaf,
    package_verdict,
)
from graph.graph_writer import GraphWriter

I2 = SAMPLE_ESTATE / "cases" / "increment2"
I3 = SAMPLE_ESTATE / "cases" / "increment3"


def _pipeline_to_claim():
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    snap = writer.publish_map(MemoryDest())
    seed = curate_storm(
        load_signal_storm(I2 / "signal_storm.json"),
        case_id="case-checkout-1",
        prefer_seed_ci="checkout-api",
    )
    ws = build_working_set(snap, seed, hops=2, confidence_bearing_only=False)
    claim = localize_leaf(snap, ws)
    return snap, seed, ws, claim


def test_i3_evidence_bundle_from_leaf_claim():
    expected = json.loads((I3 / "expected_verdict.json").read_text(encoding="utf-8"))
    _, _, ws, claim = _pipeline_to_claim()
    assert claim.claim_ci_id == expected["root_ci_id"]
    bundle = build_evidence_bundle(claim, ws)
    assert bundle.leaf_ci_id == expected["root_ci_id"]
    assert bundle.case_id == expected["case_id"]
    assert list(bundle.path_from_seed) == expected["path_spine"]
    for kind in expected["must_have_evidence_kinds"]:
        assert len(getattr(bundle, kind)) >= 1, kind
    assert len(bundle.changes) == 0  # honest lab gap
    assert bundle.confidence_tier == expected["confidence_tier"]
    assert bundle.weakest_evidence_type == expected["weakest_evidence_type"]


def test_i3_evidence_provider_override():
    _, _, ws, claim = _pipeline_to_claim()

    def provider(c, _ws):
        return {
            "metrics": [{"kind": "custom", "ci_id": c.claim_ci_id, "summary": "custom metric"}],
            "logs": [],
            "traces": [],
            "changes": [{"kind": "deploy", "ci_id": c.claim_ci_id, "summary": "rollout"}],
            "topology": [{"kind": "walk_path", "path": list(c.path_from_seed)}],
        }

    bundle = build_evidence_bundle(claim, ws, evidence_provider=provider)
    assert bundle.metrics[0]["summary"] == "custom metric"
    assert len(bundle.changes) == 1
    assert bundle.confidence_tier in (1, 2, 3)


def test_i3_package_verdict_card():
    expected = json.loads((I3 / "expected_verdict.json").read_text(encoding="utf-8"))
    _, _, ws, claim = _pipeline_to_claim()
    bundle = build_evidence_bundle(claim, ws)
    card = package_verdict(bundle)
    assert card.root_ci_id == expected["root_ci_id"]
    assert card.root_ci_type == expected["root_ci_type"]
    assert card.detect_class == expected["detect_class"]
    assert card.confidence_tier == expected["confidence_tier"]
    assert card.confidence_label == "medium"
    for cid in expected["blast_must_include"]:
        assert cid in card.blast_radius
    assert card.narrative
    assert len(card.recommended_actions) >= 2
    assert card.serviceops_handoff["ci_id"] == "payments-db"
    assert card.evidence_counts["changes"] == 0


def test_i3_package_can_omit_narrative():
    _, _, ws, claim = _pipeline_to_claim()
    card = package_verdict(build_evidence_bundle(claim, ws), include_narrative=False)
    assert card.narrative is None
    assert card.summary  # D4 required card body still present


def test_i3_full_diagnose_close():
    """Increment 1 map + Increment 2 case path + Increment 3 Identify/Package."""
    expected = json.loads((I3 / "expected_verdict.json").read_text(encoding="utf-8"))
    _snap, seed, ws, claim = _pipeline_to_claim()
    bundle = build_evidence_bundle(claim, ws)
    card = package_verdict(bundle)
    assert seed.case_id == ws.case_id == claim.case_id == bundle.case_id == card.case_id
    assert card.root_ci_id == "payments-db"
    d = card.to_dict()
    assert "summary" in d and "blast_radius" in d
    # Closed diagnose path — still not a live ServiceOps ticket API
    assert "ticket_id" not in d["serviceops_handoff"]
