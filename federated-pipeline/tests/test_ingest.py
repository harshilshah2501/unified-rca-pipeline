"""Ingest and storage-tier tests."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from poc.adapters.panorama import PanoramaAdapter
from poc.ingest import IngestNormalizer, RawTelemetry, demo_hipster_ingest
from poc.stores.speed import SpeedStore


def _redis_available() -> bool:
    try:
        import redis

        return bool(redis.Redis(host="127.0.0.1", port=6379).ping())
    except Exception:
        return False


@pytest.mark.skipif(not _redis_available(), reason="Redis not available on :6379")
def test_dual_stream_ingest_writes_both_tiers():
    speed = SpeedStore()
    result = demo_hipster_ingest(speed=speed)
    assert result["stats"]["span"] == 160
    assert result["stats"]["observer"] == 2
    assert result["stats"]["metric"] == 2
    assert result["stats"]["topology"] == 3
    assert result["structural"]["los_reports"] == 2
    assert result["structural"]["edges"] == 3
    assert speed.written >= 160

    suffering = result["pattern_counts"]["fault-suffering"]
    assert any("CpuUsageRate" in k for k in suffering)
    assert sum(suffering.values()) >= 120


@pytest.mark.skipif(not _redis_available(), reason="Redis not available on :6379")
def test_ingest_feeds_panorama_majority():
    normalizer = IngestNormalizer(speed=None)
    now = time.time()
    normalizer.ingest(
        [
            RawTelemetry(
                "observer",
                payload={
                    "observer": "frontend",
                    "subject": "checkoutservice",
                    "metric": "cpu",
                    "status": "UNHEALTHY",
                    "score": 80,
                    "ts": now,
                },
            ),
            RawTelemetry(
                "observer",
                payload={
                    "observer": "paymentservice",
                    "subject": "checkoutservice",
                    "metric": "cpu",
                    "status": "UNHEALTHY",
                    "score": 75,
                    "ts": now,
                },
            ),
            RawTelemetry(
                "observer",
                payload={
                    "observer": "shippingservice",
                    "subject": "checkoutservice",
                    "metric": "cpu",
                    "status": "UNHEALTHY",
                    "score": 70,
                    "ts": now,
                },
            ),
        ]
    )
    flag = PanoramaAdapter().detect_from_reports(
        "checkoutservice",
        normalizer.structural.reports_for("checkoutservice"),
    )
    assert flag is not None
    assert flag.entity == "checkoutservice"
    assert flag.status == "UNHEALTHY"
