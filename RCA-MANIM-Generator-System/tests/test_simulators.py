"""Tests for simulation engines."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from rca_spec_parser import parse_input, spec_from_dict
from simulation_engine import get_simulator

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def test_murphy_sim_produces_frames():
    spec = spec_from_dict(parse_input(SCENARIOS / "murphy_crawler.md"))
    spec.simulation.outer_samples = 200
    frames = get_simulator("murphy").run(spec)
    assert len(frames) > 3
    final = frames[-1]
    assert "D1" in final.distributions
    assert "D2" in final.distributions
    assert final.metadata.get("d1_mean") is not None
    assert final.metadata["d1_mean"] < final.metadata["d2_mean"]


def test_murphy_deterministic():
    spec = spec_from_dict(parse_input(SCENARIOS / "murphy_crawler.md"))
    spec.simulation.outer_samples = 100
    a = get_simulator("murphy").run(spec)
    b = get_simulator("murphy").run(spec)
    assert a[-1].metadata["d1_mean"] == b[-1].metadata["d1_mean"]


def test_nezha_sim_drift():
    spec = spec_from_dict(parse_input(SCENARIOS / "nezha_checkout_drift.md"))
    frames = get_simulator("nezha").run(spec)
    assert len(frames) > 0
    drift_frames = [f for f in frames if f.metadata.get("drift_index", -1) >= 0]
    assert drift_frames


def test_panorama_sim_voting():
    spec = spec_from_dict(parse_input(SCENARIOS / "panorama_zk_partition.md"))
    frames = get_simulator("panorama").run(spec)
    assert len(frames) >= 3
    assert frames[-1].metadata.get("pano")


def test_panorama_consensus_eventually():
    spec = spec_from_dict(parse_input(SCENARIOS / "panorama_zk_partition.md"))
    frames = get_simulator("panorama").run(spec)
    locked = any(f.metadata.get("consensus_locked") for f in frames)
    assert locked or frames[-1].metadata.get("pano")
