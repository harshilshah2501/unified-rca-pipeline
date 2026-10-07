"""Hop payload types — mirrors PoC/ORCHESTRATOR.md schemas."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


@dataclass
class TimeWindow:
    start: datetime
    end: datetime

    def to_dict(self) -> dict[str, str]:
        return {"start": _iso(self.start), "end": _iso(self.end)}


@dataclass
class DetectionFlag:
    entity: str
    evidence_score: float
    observer_count: int
    status: str
    metric: str
    incident_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=_utc_now)
    symptom_entity: str | None = None
    symptom_metric: str | None = None
    # Fair bakeoff: "shared_detect". Product Panorama path: "panorama".
    detect_source: str = "shared_detect"

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "incident_id": self.incident_id,
            "timestamp": _iso(self.timestamp),
            "entity": self.entity,
            "evidence_score": self.evidence_score,
            "observer_count": self.observer_count,
            "status": self.status,
            "metric": self.metric,
            "detect_source": self.detect_source,
        }
        if self.symptom_entity:
            payload["symptom_entity"] = self.symptom_entity
        if self.symptom_metric:
            payload["symptom_metric"] = self.symptom_metric
        return payload


@dataclass
class MurphyRequest:
    symptom_entity: str
    symptom_metric: str
    flagged_entities: list[str]
    incident_id: str
    lookback_hours: int = 168
    gibbs_iterations: int = 500
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "timestamp": _iso(self.timestamp),
            "symptom_entity": self.symptom_entity,
            "symptom_metric": self.symptom_metric,
            "flagged_entities": self.flagged_entities,
            "lookback_hours": self.lookback_hours,
            "gibbs_iterations": self.gibbs_iterations,
        }


@dataclass
class MurphyResult:
    incident_id: str
    symptom_entity: str
    symptom_metric: str
    posterior: dict[str, float]
    converged: bool = True
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "timestamp": _iso(self.timestamp),
            "symptom_entity": self.symptom_entity,
            "symptom_metric": self.symptom_metric,
            "posterior": self.posterior,
            "converged": self.converged,
        }


@dataclass
class PatternRank:
    expected_pattern: str
    actual_pattern: str
    score: float
    support_count: int


@dataclass
class NezhaRequest:
    tenant: str
    service: str
    time_window: TimeWindow
    baseline_window: TimeWindow
    incident_id: str
    top_k: int = 5
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "timestamp": _iso(self.timestamp),
            "tenant": self.tenant,
            "service": self.service,
            "time_window": self.time_window.to_dict(),
            "baseline_window": self.baseline_window.to_dict(),
            "top_k": self.top_k,
        }


@dataclass
class NezhaResult:
    incident_id: str
    service: str
    ranked_patterns: list[PatternRank]
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "timestamp": _iso(self.timestamp),
            "service": self.service,
            "ranked_patterns": [asdict(p) for p in self.ranked_patterns],
        }


@dataclass
class RCAVerdict:
    incident_id: str
    root_cause_entity: str
    root_cause_pattern: str
    confidence: float
    evidence: dict[str, Any]
    summary: str
    timestamp: datetime = field(default_factory=_utc_now)
    topology_stale: bool = False
    confidence_level: str = "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "timestamp": _iso(self.timestamp),
            "root_cause_entity": self.root_cause_entity,
            "root_cause_pattern": self.root_cause_pattern,
            "confidence": round(self.confidence, 4),
            "confidence_level": self.confidence_level,
            "evidence": self.evidence,
            "summary": self.summary,
            "topology_stale": self.topology_stale,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class HopLog:
    hop: int
    component: str
    incident_id: str
    latency_ms: float
    input_hash: str
    output_hash: str
