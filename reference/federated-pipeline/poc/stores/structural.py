"""In-memory structural-tier store (Panorama LOS + Murphy metrics/topology)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from poc.adapters.panorama_majority import ObserverReport, Status


@dataclass
class MetricPoint:
    entity_id: str
    metric_name: str
    timestamp: datetime
    value: float


@dataclass
class TopologyEdge:
    src: str
    dst: str


@dataclass
class StructuralStore:
    """PoC stand-in for DashMap LOS + property store + CSR edges."""

    los: list[ObserverReport] = field(default_factory=list)
    metrics: list[MetricPoint] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)
    entities: set[str] = field(default_factory=set)

    def add_observer_report(self, report: ObserverReport) -> None:
        self.los.append(report)
        self.entities.add(report.observer)
        self.entities.add(report.subject)

    def add_metric(self, point: MetricPoint) -> None:
        self.metrics.append(point)
        self.entities.add(point.entity_id)

    def add_edge(self, src: str, dst: str) -> None:
        self.edges.append(TopologyEdge(src=src, dst=dst))
        self.entities.add(src)
        self.entities.add(dst)

    def reports_for(self, subject: str) -> list[ObserverReport]:
        return [r for r in self.los if r.subject == subject]

    def summary(self) -> dict[str, Any]:
        return {
            "entities": len(self.entities),
            "los_reports": len(self.los),
            "metric_points": len(self.metrics),
            "edges": len(self.edges),
        }
