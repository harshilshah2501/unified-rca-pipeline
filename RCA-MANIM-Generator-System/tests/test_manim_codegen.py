"""Tests for Manim scene codegen."""

from __future__ import annotations

import ast
from pathlib import Path

from frame_generator import generate_frames
from manim_generator import generate_scene
from rca_spec_parser import parse_input, spec_from_dict
from simulation_engine import get_simulator

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def test_codegen_parses_for_all_systems():
    for name in ("murphy_crawler.md", "nezha_checkout_drift.md", "panorama_zk_partition.md"):
        spec = spec_from_dict(parse_input(SCENARIOS / name))
        if spec.system == "murphy":
            spec.simulation.outer_samples = 50
        sim = get_simulator(spec.system).run(spec)
        anim = generate_frames(spec, sim)
        code = generate_scene(anim, spec)
        ast.parse(code)
        assert "class RCAScene" in code


def test_codegen_contains_helpers():
    spec = spec_from_dict(parse_input(SCENARIOS / "murphy_crawler.md"))
    spec.simulation.outer_samples = 50
    sim = get_simulator("murphy").run(spec)
    anim = generate_frames(spec, sim)
    code = generate_scene(anim, spec)
    assert "build_graph" in code
    assert "show_distribution_plot" in code
