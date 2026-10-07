"""Smoke tests — lean RCA root_ci vs ground truth for UC-1..UC-5 + UC-3b."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "lean-pipeline"))

from core_engine.observeops.engine import diagnose  # noqa: E402

CORPUS = REPO / "datasets" / "observeops"
PRIMARY_UCS = [f"UC-{i}" for i in range(1, 6)]
ALL_UCS = PRIMARY_UCS + ["UC-3b"]


@pytest.mark.parametrize("uc_id", ALL_UCS)
def test_root_ci_matches_ground_truth(uc_id: str) -> None:
    verdict = diagnose(uc_id, CORPUS)
    gt = json.loads((CORPUS / uc_id / "ground_truth.json").read_text())
    assert verdict["root_ci"] == gt["root_ci"], (
        f"{uc_id}: expected {gt['root_ci']}, got {verdict['root_ci']}"
    )


@pytest.mark.parametrize("uc_id", ALL_UCS)
def test_signature_and_contributors(uc_id: str) -> None:
    verdict = diagnose(uc_id, CORPUS)
    gt = json.loads((CORPUS / uc_id / "ground_truth.json").read_text())
    assert verdict["signature"] == gt["signature"]
    assert set(gt.get("contributor_cis") or []) <= set(verdict.get("contributor_cis") or [])
    assert verdict["engine"] == "lean"


@pytest.mark.parametrize("uc_id", ALL_UCS)
def test_verdict_has_tier_fields(uc_id: str) -> None:
    verdict = diagnose(uc_id, CORPUS)
    assert verdict["evidentiary_tier"] in (1, 2, 3)
    assert isinstance(verdict["fallback_fired"], bool)
    if verdict["fallback_fired"]:
        assert isinstance(verdict["causal_verified"], bool)
        assert isinstance(verdict["causal_log"], list)
    else:
        assert verdict["causal_verified"] is None
        assert verdict["causal_log"] is None
    assert isinstance(verdict["obs_to_convergence"], int)
    assert isinstance(verdict["naive_bfs_expansions"], int)
    assert isinstance(verdict["efficiency_ratio"], float)
    assert verdict["naive_bfs_expansions"] >= verdict["obs_to_convergence"]


def test_care_can_produce_tier_3_on_ambiguous_corpus_case() -> None:
    verdicts = [diagnose(uc_id, CORPUS) for uc_id in PRIMARY_UCS]
    assert any(
        verdict["fallback_fired"] and verdict["evidentiary_tier"] == 3
        for verdict in verdicts
    )


@pytest.mark.parametrize("uc_id", ["UC-2", "UC-4"])
def test_events_appear_in_evidence(uc_id: str) -> None:
    verdict = diagnose(uc_id, CORPUS)
    events = json.loads((CORPUS / uc_id / "events.json").read_text())["events"]
    assert events
    event_types = {e["event_type"] for e in events}
    cited = {
        item["signal"]
        for item in verdict["evidence"]
        if item.get("source") == "event" or item.get("message")
    }
    assert event_types & cited


def test_uc3b_does_not_blame_early_switch() -> None:
    verdict = diagnose("UC-3b", CORPUS)
    assert verdict["root_ci"] == "datastore-01"
    assert verdict["root_ci"] != "switch-core-01:GigE0/2"
    assert "vm-neighbor-01" in verdict["contributor_cis"]
    assert any(
        item.get("signal") == "utilization_pct" and item["ci"].startswith("switch-")
        for item in verdict["evidence"]
        if item.get("source") == "anomaly"
    )
