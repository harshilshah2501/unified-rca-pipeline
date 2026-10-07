from sketch.metric_admit import admit_metric
from sketch.windowing import assignments
from datetime import datetime, timezone
from ab_shared.season import HourOfWeekSeason


def test_admit_resolved_wave1():
    rec = {
        "fact_kind": "metric_sample",
        "tenant": "default",
        "ci_id": "checkout-api",
        "ci_type": "Service",
        "name": "request.latency_ms",
        "value": 10,
        "ts": "2026-08-20T03:30:00Z",
        "identity": {"status": "resolved"},
    }
    sample, reason = admit_metric(rec)
    assert reason is None
    assert sample["metric_id"] == "request.latency_ms"


def test_unknown_metric():
    rec = {
        "fact_kind": "metric_sample",
        "tenant": "default",
        "ci_id": "checkout-api",
        "name": "disk.queue_depth",
        "value": 1,
        "ts": "2026-08-20T03:30:00Z",
        "identity": {"status": "resolved"},
    }
    sample, reason = admit_metric(rec)
    assert sample is None
    assert reason == "unknown_metric_id"


def test_window_feeds_1m_and_5m():
    slots = assignments("2026-08-20T03:32:00Z", season=HourOfWeekSeason())
    windows = {s["window"] for s in slots}
    assert windows == {"1m", "5m"}
    five = next(s for s in slots if s["window"] == "5m")
    assert five["window_start"] == "2026-08-20T03:30:00Z"
    assert five["season_key"] == "Thu-03:00"
