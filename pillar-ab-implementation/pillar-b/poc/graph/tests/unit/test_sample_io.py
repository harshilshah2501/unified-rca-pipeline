"""Expected vs actual for lab GraphWriter sample I/O cases."""

from __future__ import annotations

import json
from pathlib import Path

from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from graph.compare import compare_spine
from graph.graph_writer import GraphWriter

CASES = SAMPLE_ESTATE / "cases"


def test_case_a_map_spine_expected_vs_actual():
    expected = json.loads((CASES / "case_a_map_spine" / "expected_spine.json").read_text(encoding="utf-8"))
    writer = GraphWriter(tenant=expected["tenant"])
    writer.load_estate_bootstrap(SAMPLE_ESTATE / expected["inputs"]["bootstrap"])
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / expected["inputs"]["stream"]))
    assert writer.rejects == expected["rejects"]
    snapshot = writer.publish_map(MemoryDest(), version=expected["version"])
    diffs = compare_spine(expected, snapshot)
    assert not diffs, "\n".join(diffs)


def test_case_b_rejects_expected_vs_actual():
    expected = json.loads((CASES / "case_b_rejects" / "expected_rejects.json").read_text(encoding="utf-8"))
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / expected["inputs"]["bootstrap"])
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / expected["inputs"]["stream"]))
    reasons = sorted({reason for _, reason in writer.rejects})
    assert reasons == expected["reject_reasons"]
    assert len(writer.rejects) == expected["reject_count"]
    snapshot = writer.publish_map(MemoryDest())
    present = {n["entity_id"] for n in snapshot["nodes"]}
    for cid in expected["must_not_appear_as_nodes"]:
        assert cid not in present, f"{cid} must not land on map/"
    for cid in expected["bootstrap_nodes_still_present"]:
        assert cid in present, f"bootstrap node {cid} should remain after reject tape"
