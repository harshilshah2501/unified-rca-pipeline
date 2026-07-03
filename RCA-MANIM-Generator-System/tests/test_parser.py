"""Tests for RCA-SPEC parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from rca_spec_parser import parse_input, spec_from_dict

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def test_parse_murphy_markdown():
    spec = parse_input(SCENARIOS / "murphy_crawler.md")
    assert spec["system"] == "murphy"
    assert len(spec["nodes"]) >= 3
    assert spec["fault"]["target"] == "crawler_vm"


def test_parse_nezha_markdown():
    spec = parse_input(SCENARIOS / "nezha_checkout_drift.md")
    assert spec["system"] == "nezha"
    assert spec["visualization"]["show_drift"] is True


def test_parse_panorama_markdown():
    spec = parse_input(SCENARIOS / "panorama_zk_partition.md")
    assert spec["system"] == "panorama"
    assert len(spec["reports"]) >= 5


def test_spec_from_dict_defaults():
    raw = parse_input(SCENARIOS / "murphy_crawler.md")
    spec = spec_from_dict(raw)
    assert spec.simulation.outer_samples == 5000
    assert spec.seed == 42


def test_invalid_system_rejected():
    with pytest.raises(Exception):
        spec_from_dict(
            {
                "system": "invalid",
                "nodes": [{"id": "a"}],
                "fault": {"type": "x", "target": "a"},
            }
        )
