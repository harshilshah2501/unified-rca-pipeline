from datetime import datetime, timezone

from ab_shared.clock import FrozenClock
from ab_shared.dest import FileDest, MemoryDest
from ab_shared.identity_gate import ResolvedOnlyGate
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import FIXTURES
from ab_shared.reject_codes import REJECT_CODES
from ab_shared.schema import is_valid
from ab_shared.season import HourOfWeekSeason


def test_reject_catalog_lists_pillar_a_codes():
    assert set(REJECT_CODES) == {
        "identity_unresolved",
        "identity_synthesized",
        "unknown_metric_id",
    }


def test_schemas_validate_golden_examples():
    import json

    expected = FIXTURES / "expected"
    assert is_valid(
        "ingest_v1.schema.json",
        json.loads((expected / "ingest.example.json").read_text()),
    )
    assert is_valid(
        "sketch_v1.schema.json",
        json.loads((expected / "sketch.example.json").read_text()),
    )


def test_gate_drops_unattributed_and_synthesized():
    gate = ResolvedOnlyGate()
    ok = {"identity": {"status": "resolved"}}
    assert gate.admit(ok).accepted
    unattr = {"identity": {"status": "unattributed"}}
    r = gate.admit(unattr)
    assert not r.accepted and r.reason == "identity_unresolved"
    synth = {"identity": {"status": "synthesized"}}
    r = gate.admit(synth)
    assert not r.accepted and r.reason == "identity_synthesized"
    missing = {}
    r = gate.admit(missing)
    assert not r.accepted and r.reason == "identity_unresolved"


def test_gate_reason_codes_from_reject_fixture():
    gate = ResolvedOnlyGate()
    src = JsonlIngestSource(FIXTURES / "stream.reject.jsonl")
    reasons = []
    for rec in src.records():
        result = gate.admit(rec)
        if not result.accepted:
            reasons.append(result.reason)
    assert "identity_unresolved" in reasons
    assert "identity_synthesized" in reasons


def test_season_hour_of_week_example():
    ts = datetime(2026, 8, 20, 9, 15, tzinfo=timezone.utc)
    assert HourOfWeekSeason().season_key(ts) == "Thu-09:00"
    ts2 = datetime(2026, 8, 20, 3, 30, tzinfo=timezone.utc)
    assert HourOfWeekSeason().season_key(ts2) == "Thu-03:00"


def test_memory_dest_round_trip():
    dest = MemoryDest()
    dest.put("history", "sketches.jsonl", b"{}\n")
    assert dest.get("history", "sketches.jsonl") == b"{}\n"
    assert dest.list_keys("history") == ["sketches.jsonl"]
    assert dest.get("history", "missing") is None


def test_file_dest_round_trip(tmp_path):
    dest = FileDest(tmp_path, tenant="default")
    dest.put("history", "sketches.jsonl", b"{}\n")
    assert dest.get("history", "sketches.jsonl") == b"{}\n"


def test_frozen_clock():
    fixed = datetime(2026, 8, 20, 3, 30, tzinfo=timezone.utc)
    clock = FrozenClock(fixed)
    assert clock.now() == fixed
