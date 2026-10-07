from datetime import datetime, timezone

from ab_shared.clock import FrozenClock
from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import FIXTURES
from ab_shared.schema import is_valid
from ab_shared.season import HourOfWeekSeason
from sketch.sketch_flush import SketchWriter
from sketch.sketch_read import get_metric_baseline, get_window_percentiles


def test_flush_and_read_checkout_latency():
    writer = SketchWriter(season=HourOfWeekSeason())
    writer.ingest(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    dest = MemoryDest()
    rows = writer.flush(dest)
    assert rows
    for row in rows:
        assert is_valid("sketch_v1.schema.json", row)
        assert "relation" not in row
    pct = get_window_percentiles(
        dest,
        tenant="default",
        entity_id="checkout-api",
        metric_id="request.latency_ms",
        window="5m",
        window_start="2026-08-20T03:30:00Z",
    )
    assert pct is not None
    assert pct["p95"] > 0
    base = get_metric_baseline(
        dest,
        tenant="default",
        entity_id="checkout-api",
        metric_id="request.latency_ms",
        season_key="Thu-03:00",
    )
    assert base is not None


def test_rejects_unknown_metric_from_fixture():
    writer = SketchWriter()
    writer.ingest(JsonlIngestSource(FIXTURES / "stream.reject.jsonl"))
    assert any(r[1] == "unknown_metric_id" for r in writer.rejects)
    assert any(r[1] == "identity_unresolved" for r in writer.rejects)
    assert any(r[1] == "identity_synthesized" for r in writer.rejects)


def test_frozen_clock_season_key_stable():
    clock = FrozenClock(datetime(2026, 8, 20, 3, 30, tzinfo=timezone.utc))
    assert HourOfWeekSeason().season_key(clock.now()) == "Thu-03:00"
