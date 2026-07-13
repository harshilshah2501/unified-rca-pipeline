"""Dual-stream ingest normalizer — write path for speed + structural tiers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import uuid4

from poc.adapters.panorama_majority import ObserverReport, Status
from poc.stores.speed import SpeedEvent, SpeedStore
from poc.stores.structural import MetricPoint, StructuralStore, TopologyEdge

logger = logging.getLogger(__name__)


@dataclass
class RawTelemetry:
    """Normalized ingest record before tier split."""

    kind: str  # span | log | metric | observer | topology
    tenant: str = "default"
    payload: dict[str, Any] | None = None


class IngestNormalizer:
    """
    Splits raw telemetry into:
      Stream A → SpeedStore (Nezha events)
      Stream B → StructuralStore (Panorama LOS + Murphy metrics/edges)
    """

    def __init__(
        self,
        speed: SpeedStore | None = None,
        structural: StructuralStore | None = None,
        tenant: str = "default",
    ) -> None:
        self.speed = speed
        self.structural = structural or StructuralStore()
        self.tenant = tenant
        self.stats = {"span": 0, "observer": 0, "metric": 0, "topology": 0, "skipped": 0}

    def ingest(self, records: Iterator[RawTelemetry] | list[RawTelemetry]) -> dict[str, Any]:
        batch: list[SpeedEvent] = []
        for record in records:
            kind = record.kind
            payload = record.payload or {}
            if kind == "span":
                event = self._span_to_event(payload)
                if self.speed is not None:
                    batch.append(event)
                self.stats["span"] += 1
            elif kind == "observer":
                self.structural.add_observer_report(self._to_observer(payload))
                self.stats["observer"] += 1
            elif kind == "metric":
                self.structural.add_metric(self._to_metric(payload))
                self.stats["metric"] += 1
            elif kind == "topology":
                self.structural.add_edge(payload["src"], payload["dst"])
                self.stats["topology"] += 1
            else:
                self.stats["skipped"] += 1

            if len(batch) >= 64 and self.speed is not None:
                self.speed.write_batch(batch)
                batch.clear()

        if batch and self.speed is not None:
            self.speed.write_batch(batch)

        return {
            "stats": dict(self.stats),
            "speed": self.speed.summary() if self.speed else None,
            "structural": self.structural.summary(),
        }

    def _span_to_event(self, payload: dict[str, Any]) -> SpeedEvent:
        return SpeedEvent(
            tenant=payload.get("tenant", self.tenant),
            trace_id=payload.get("trace_id", str(uuid4())),
            span_id=payload.get("span_id", str(uuid4())[:8]),
            service=payload["service"],
            event_type=payload.get("event_type", payload.get("operation", "span")),
            timestamp=float(payload.get("timestamp", time.time())),
            phase=payload.get("phase", "fault-suffering"),
        )

    def _to_observer(self, payload: dict[str, Any]) -> ObserverReport:
        status = payload.get("status", "UNHEALTHY")
        if isinstance(status, str):
            status = Status[status.upper()] if status.upper() in Status.__members__ else Status.UNHEALTHY
        return ObserverReport(
            observer=payload["observer"],
            subject=payload["subject"],
            metric=payload.get("metric", "health"),
            status=status,
            score=float(payload.get("score", 50.0)),
            ts=float(payload.get("ts", time.time())),
        )

    def _to_metric(self, payload: dict[str, Any]) -> MetricPoint:
        ts = payload.get("timestamp")
        if isinstance(ts, str):
            timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        elif isinstance(ts, datetime):
            timestamp = ts
        else:
            timestamp = datetime.now(timezone.utc)
        return MetricPoint(
            entity_id=payload["entity_id"],
            metric_name=payload["metric_name"],
            timestamp=timestamp,
            value=float(payload["value"]),
        )


def demo_hipster_ingest(speed: SpeedStore | None = None) -> dict[str, Any]:
    """Seed both tiers with Online Boutique-shaped telemetry for the PoC."""
    normalizer = IngestNormalizer(speed=speed, tenant="hipster")
    now = time.time()
    records = [
        RawTelemetry("topology", payload={"src": "frontend", "dst": "checkoutservice"}),
        RawTelemetry("topology", payload={"src": "checkoutservice", "dst": "paymentservice"}),
        RawTelemetry("topology", payload={"src": "checkoutservice", "dst": "shippingservice"}),
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
            "metric",
            payload={
                "entity_id": "checkoutservice",
                "metric_name": "cpu_usage",
                "value": 0.92,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ),
        RawTelemetry(
            "metric",
            payload={
                "entity_id": "frontend",
                "metric_name": "latency_p90",
                "value": 180.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ),
    ]
    # Baseline + fault-suffering spans for Nezha pattern counts.
    for i in range(40):
        records.append(
            RawTelemetry(
                "span",
                payload={
                    "tenant": "hipster",
                    "trace_id": f"base-{i}",
                    "span_id": f"s{i}",
                    "service": "checkoutservice",
                    "event_type": "Charge successfully",
                    "timestamp": now - 3600 + i,
                    "phase": "fault-free",
                },
            )
        )
    for i in range(120):
        records.append(
            RawTelemetry(
                "span",
                payload={
                    "tenant": "hipster",
                    "trace_id": f"fault-{i}",
                    "span_id": f"f{i}",
                    "service": "checkoutservice",
                    "event_type": "CpuUsageRate(%)",
                    "timestamp": now + i,
                    "phase": "fault-suffering",
                },
            )
        )

    result = normalizer.ingest(records)
    result["pattern_counts"] = {
        "fault-free": speed.pattern_counts("hipster", "fault-free") if speed else {},
        "fault-suffering": speed.pattern_counts("hipster", "fault-suffering") if speed else {},
    } if speed else {}
    return result
