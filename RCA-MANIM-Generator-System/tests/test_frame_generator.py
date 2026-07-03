"""Tests for frame generator."""

from __future__ import annotations

from pathlib import Path

from frame_generator import generate_frames
from rca_spec_parser import parse_input, spec_from_dict
from simulation_engine import get_simulator

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def test_murphy_animation_frames():
    spec = spec_from_dict(parse_input(SCENARIOS / "murphy_crawler.md"))
    spec.simulation.outer_samples = 100
    sim = get_simulator("murphy").run(spec)
    frames = generate_frames(spec, sim)
    assert frames[0].frame_id == 0
    assert frames[0].graph_state.nodes
    assert frames[-1].overlays.charts or frames[-1].metadata.get("phase") == "result"


def test_nezha_drift_highlight():
    spec = spec_from_dict(parse_input(SCENARIOS / "nezha_checkout_drift.md"))
    sim = get_simulator("nezha").run(spec)
    frames = generate_frames(spec, sim)
    drift_frames = [f for f in frames if f.graph_state.highlights or f.overlays.text]
    assert drift_frames


def test_panorama_vote_charts():
    spec = spec_from_dict(parse_input(SCENARIOS / "panorama_zk_partition.md"))
    sim = get_simulator("panorama").run(spec)
    frames = generate_frames(spec, sim)
    assert any(f.overlays.charts or f.metadata.get("vote_bars") for f in frames)
