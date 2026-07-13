"""Core data types for Murphy performance diagnosis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Entity:
    id: str
    entity_type: str  # vm, host, nic, flow, microservice, container, router
    app_id: str
    metadata: dict = field(default_factory=dict)


@dataclass
class MetricSample:
    entity_id: str
    metric_name: str
    timestamp: datetime
    value: float


@dataclass
class Symptom:
    entity_id: str
    metric_name: str
    observed_value: float
    incident_time: datetime


@dataclass
class RootCause:
    entity_id: str
    metric_name: str
    anomaly_score: float
    d1_samples: list[float]
    d2_samples: list[float]
    p_value: float
    is_significant: bool


@dataclass
class ExplanationStep:
    from_entity: str
    to_entity: str
    from_state: str
    to_state: str
    edge_label: str


@dataclass
class DiagnosisResult:
    symptom: Symptom
    root_causes: list[RootCause]
    explanation_chains: dict[str, list[ExplanationStep]]


def model_key(entity_id: str, metric_name: str) -> str:
    """Composite key for per-entity-metric Ridge models."""
    return f"{entity_id}:{metric_name}"
