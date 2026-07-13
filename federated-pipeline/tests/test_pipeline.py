"""PoC pipeline tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from poc.adapters.nezha import rank_patterns
from poc.adapters.panorama import PanoramaAdapter
from poc.adapters.panorama_majority import ObserverReport, Status, infer_panorama
from poc.scenarios.crawler import run_crawler_scenario
from poc.scenarios.hipster import (
    INCIDENT_TIME,
    build_hipster_detection_flag,
    build_hipster_orchestrator,
    build_hipster_observer_reports,
)


def test_nezha_pattern_scoring():
    ranked = rank_patterns(
        normal_counts={"a→b": 100, "a→c": 200},
        abnormal_counts={"a→b": 10, "a→d": 90},
        min_score=0.5,
    )
    assert ranked[0].actual_pattern == "d"
    assert ranked[0].score == pytest.approx(90 / 90, rel=1e-3)


def test_panorama_majority_flags_unhealthy_subject():
    inference = infer_panorama("checkoutservice", build_hipster_observer_reports())
    assert inference is not None
    primary = inference.primary_metric
    assert primary is not None
    assert primary[1].status == Status.UNHEALTHY
    assert len(inference.observers) >= 4

    flag = PanoramaAdapter().detect_from_reports(
        "checkoutservice", build_hipster_observer_reports()
    )
    assert flag is not None
    assert flag.entity == "checkoutservice"
    assert flag.status == "UNHEALTHY"
    assert flag.observer_count >= 4
    assert flag.evidence_score >= 0.5


def test_panorama_majority_ignores_healthy_consensus():
    reports = [
        ObserverReport("a", "svc", "latency", Status.HEALTHY, 5.0, ts=1.0),
        ObserverReport("b", "svc", "latency", Status.HEALTHY, 4.0, ts=1.0),
        ObserverReport("c", "svc", "latency", Status.HEALTHY, 6.0, ts=1.0),
    ]
    flag = PanoramaAdapter().detect_from_reports("svc", reports)
    assert flag is None


def test_crawler_pipeline_end_to_end():
    verdict = run_crawler_scenario()
    assert verdict.root_cause_entity == "crawler_vm"
    assert verdict.confidence > 0.5
    assert "crawler_vm" in verdict.evidence["murphy"]["distribution"]
    assert verdict.evidence["murphy"]["distribution"]["crawler_vm"] > 0.3
    assert verdict.root_cause_pattern
    assert verdict.evidence["panorama"]["status"] == "UNHEALTHY"


def test_hipster_pipeline_end_to_end():
    orchestrator = build_hipster_orchestrator()
    orchestrator.nezha.prefer_dataset = False
    flag = build_hipster_detection_flag()
    assert flag.entity == "checkoutservice"
    assert flag.status == "UNHEALTHY"

    verdict = orchestrator.run_pipeline(flag, incident_time=INCIDENT_TIME)
    assert verdict.root_cause_entity == "checkoutservice"
    assert verdict.confidence > 0.5
    assert "checkoutservice" in verdict.evidence["murphy"]["distribution"]
    assert verdict.evidence["panorama"]["status"] == "UNHEALTHY"
    assert verdict.root_cause_pattern
