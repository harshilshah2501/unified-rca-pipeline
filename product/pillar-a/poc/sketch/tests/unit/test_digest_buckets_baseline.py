from sketch.digest import TDigestAdapter
from sketch.buckets import Histogram
from sketch.baseline import SeasonalBaseline


def test_digest_update_merge_quantile():
    a = TDigestAdapter()
    for x in range(1, 101):
        a.update(float(x))
    p50 = a.quantile(0.5)
    assert 40 < p50 < 60
    b = TDigestAdapter()
    b.update(1000.0)
    a.merge(b)
    cents = a.to_centroids()
    assert cents
    assert a.sample_count() == 101


def test_buckets_latency():
    h = Histogram("latency_v1")
    h.update(25)
    h.update(75)
    h.update(150)
    body = h.to_json_body()
    assert body["counts"][0] == 1
    assert body["counts"][1] == 1
    assert body["counts"][2] == 1
    assert sum(body["counts"]) == 3


def test_seasonal_baseline_differs_by_key():
    b = SeasonalBaseline()
    b.observe("Thu-09:00", 80, 170, 300)
    b.observe("Sun-02:00", 20, 40, 60)
    thu = b.expected("Thu-09:00")
    sun = b.expected("Sun-02:00")
    assert thu["expected_p95"] == 170
    assert sun["expected_p95"] == 40


def test_writer_baselines_separate_1m_and_5m():
    """1m and 5m must not share one seasonal accumulator (Detect realism)."""
    from ab_shared.ingest_source import ListIngestSource
    from sketch.sketch_flush import SketchWriter

    rec = {
        "schema_version": "ingest.v1",
        "ts": "2026-08-20T03:32:00Z",
        "tenant": "default",
        "ci_id": "checkout-api",
        "ci_type": "Service",
        "fact_kind": "metric_sample",
        "name": "request.latency_ms",
        "value": 100.0,
        "identity": {"status": "resolved"},
    }
    writer = SketchWriter()
    writer.ingest(ListIngestSource([rec]))
    # Force build_row for each window state so baselines are populated.
    for st in writer.states.values():
        writer.build_row(st)
    keys = set(writer.baselines.keys())
    assert ("default", "checkout-api", "request.latency_ms", "1m") in keys
    assert ("default", "checkout-api", "request.latency_ms", "5m") in keys
    # Same season_key may appear in both, but histories are independent objects.
    b1 = writer.baselines[("default", "checkout-api", "request.latency_ms", "1m")]
    b5 = writer.baselines[("default", "checkout-api", "request.latency_ms", "5m")]
    assert b1 is not b5


def test_detect_contrast_prior_vs_spike():
    """Door-C style: prior season observation → expected; spike current p95 high."""
    from ab_shared.ingest_source import ListIngestSource
    from sketch.sketch_flush import SketchWriter

    prior = {
        "schema_version": "ingest.v1",
        "ts": "2026-08-20T03:31:00Z",
        "tenant": "default",
        "ci_id": "checkout-api",
        "ci_type": "Service",
        "fact_kind": "metric_sample",
        "name": "request.latency_ms",
        "value": 90.0,
        "identity": {"status": "resolved"},
    }
    writer = SketchWriter()
    writer.ingest(ListIngestSource([prior]))
    for st in list(writer.states.values()):
        writer.build_row(st)

    # New window_start same season hour but fresh state key via cleared states after first flush pattern:
    # Simulate second window by observing another sample in a later 5m slot same season.
    spike = {
        **prior,
        "ts": "2026-08-27T03:31:00Z",  # next Thu 03:xx → same season_key Thu-03:00
        "value": 900.0,
    }
    writer2 = SketchWriter()
    # Seed baselines from first writer (5m only) to mimic E5 history.
    bkey = ("default", "checkout-api", "request.latency_ms", "5m")
    writer2.baselines[bkey] = writer.baselines[bkey]
    writer2.ingest(ListIngestSource([spike]))
    rows = [writer2.build_row(st) for st in writer2.states.values() if st.key and st.key.window == "5m"]
    assert rows
    row = rows[0]
    assert row["season_key"] == "Thu-03:00"
    assert row["baseline"]["expected_p95"] < 200
    p95 = row["tdigest"]  # use digest quantile via build already
    # Current window is spike-only → digests p95 ~900
    from sketch.digest import TDigestAdapter
    # Re-read from state
    st5 = next(st for st in writer2.states.values() if st.key and st.key.window == "5m")
    assert st5.digest.quantile(0.95) > row["baseline"]["expected_p95"] * 2
