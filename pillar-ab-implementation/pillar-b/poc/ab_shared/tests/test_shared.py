from datetime import datetime, timezone

from ab_shared.clock import FrozenClock
from ab_shared.dest import FileDest, MemoryDest
from ab_shared.identity_gate import ResolvedOnlyGate
from ab_shared.paths import FIXTURES
from ab_shared.reject_codes import REJECT_CODES
from ab_shared.schema import is_valid
from ab_shared.season import HourOfWeekSeason


def test_reject_catalog_lists_all_codes():
    assert set(REJECT_CODES) == {
        "identity_unresolved",
        "identity_synthesized",
        "never_ci_vertex",
        "unknown_relation",
        "unknown_metric_id",
    }


def test_schemas_validate_golden_examples():
    import json

    expected = FIXTURES / "expected"
    assert is_valid("ingest_v1.schema.json", json.loads((expected / "ingest.example.json").read_text()))
    assert is_valid("graph_node_v1.schema.json", json.loads((expected / "graph_node.example.json").read_text()))
    assert is_valid("graph_edge_v1.schema.json", json.loads((expected / "graph_edge.example.json").read_text()))
    assert is_valid("change_fact_v1.schema.json", json.loads((expected / "change_fact.example.json").read_text()))


def test_season_hour_of_week_example():
    ts = datetime(2026, 8, 20, 3, 30, tzinfo=timezone.utc)
    assert HourOfWeekSeason().season_key(ts) == "Thu-03:00"


def test_memory_dest_round_trip():
    dest = MemoryDest()
    dest.put("map", "graph_snapshot.json", b'{"ok":true}')
    assert dest.get("map", "graph_snapshot.json") == b'{"ok":true}'


def test_file_dest_round_trip(tmp_path):
    dest = FileDest(tmp_path, tenant="default")
    dest.put("map", "graph_snapshot.json", b"{}")
    assert dest.get("map", "graph_snapshot.json") == b"{}"


def test_frozen_clock():
    fixed = datetime(2026, 8, 20, 3, 30, tzinfo=timezone.utc)
    assert FrozenClock(fixed).now() == fixed


def test_gate_resolved_only():
    gate = ResolvedOnlyGate()
    assert gate.admit({"identity": {"status": "resolved"}}).accepted
    assert not gate.admit({"identity": {"status": "unattributed"}}).accepted
