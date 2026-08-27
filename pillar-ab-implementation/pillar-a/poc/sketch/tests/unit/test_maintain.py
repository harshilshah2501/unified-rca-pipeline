from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import ListIngestSource
from sketch.maintain import refresh_seasonal_baselines
from sketch.sketch_flush import SketchWriter


def _sample(ts: str, value: float) -> dict:
    return {
        "schema_version": "ingest.v1",
        "ts": ts,
        "tenant": "default",
        "ci_id": "checkout-api",
        "ci_type": "Service",
        "signal_class": "metric_sample",
        "name": "request.latency_ms",
        "value": value,
        "identity": {"status": "resolved"},
    }


def test_refresh_seasonal_baselines_from_dest_splits_windows():
    writer = SketchWriter()
    writer.ingest(
        ListIngestSource(
            [
                _sample("2026-08-20T03:31:00Z", 100.0),
                _sample("2026-08-27T03:31:00Z", 120.0),
            ]
        )
    )
    dest = MemoryDest()
    writer.flush(dest)

    writer2 = SketchWriter()
    rebuilt = refresh_seasonal_baselines(writer2, dest)
    assert ("default", "checkout-api", "request.latency_ms", "1m") in rebuilt
    assert ("default", "checkout-api", "request.latency_ms", "5m") in rebuilt
    # Two Thursday windows → two observations under Thu-03:00 for 5m
    hist5 = rebuilt[("default", "checkout-api", "request.latency_ms", "5m")].history
    assert len(hist5.get("Thu-03:00", [])) == 2


def test_writer_refresh_baselines_with_dest():
    writer = SketchWriter()
    writer.ingest(ListIngestSource([_sample("2026-08-20T03:31:00Z", 80.0)]))
    dest = MemoryDest()
    writer.flush(dest)
    writer.baselines.clear()
    writer.refresh_baselines(dest)
    assert writer.baselines
    assert ("default", "checkout-api", "request.latency_ms", "5m") in writer.baselines
