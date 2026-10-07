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
