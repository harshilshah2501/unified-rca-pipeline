"""Panorama adapter — majority voting with optional simulated fallback."""

from __future__ import annotations

from dataclasses import dataclass

from poc.adapters.panorama_majority import (
    Inference,
    ObserverReport,
    Status,
    infer_panorama,
)
from poc.types import DetectionFlag


@dataclass
class PanoramaConfig:
    evidence_threshold: float = 0.5
    grpc_server: str | None = None


_FLAG_STATUSES = {Status.UNHEALTHY, Status.MAYBE_UNHEALTHY, Status.SUSPECT}


class PanoramaAdapter:
    """Wraps Panorama detection as DetectionFlag payloads."""

    def __init__(self, config: PanoramaConfig | None = None) -> None:
        self.config = config or PanoramaConfig()

    def detect_from_reports(
        self,
        subject: str,
        reports: list[ObserverReport],
        incident_id: str | None = None,
    ) -> DetectionFlag | None:
        """Run InferPano majority voting and emit a DetectionFlag if unhealthy."""
        inference = infer_panorama(subject, reports)
        if inference is None:
            return None
        return self.detect_from_inference_result(inference, incident_id=incident_id)

    def detect_from_inference_result(
        self,
        inference: Inference,
        incident_id: str | None = None,
    ) -> DetectionFlag | None:
        primary = inference.primary_metric
        if primary is None:
            return None
        metric_name, value = primary
        if value.status not in _FLAG_STATUSES:
            return None
        if value.score < self.config.evidence_threshold:
            return None

        # Normalize score to [0, 1] for fusion (Panorama scores are often 0–100).
        evidence = value.score
        if evidence > 1.0:
            evidence = min(evidence / 100.0, 1.0)

        flag = DetectionFlag(
            entity=inference.subject,
            evidence_score=round(evidence, 4),
            observer_count=len(inference.observers),
            status=value.status.name,
            metric=metric_name,
        )
        if incident_id:
            flag.incident_id = incident_id
        return flag

    def detect_from_inference(
        self,
        subject: str,
        status: str,
        evidence_score: float,
        observer_count: int,
        metric: str,
        incident_id: str | None = None,
    ) -> DetectionFlag | None:
        if evidence_score < self.config.evidence_threshold:
            return None
        if status not in {"UNHEALTHY", "MAYBE_UNHEALTHY", "SUSPECT"}:
            return None

        flag = DetectionFlag(
            entity=subject,
            evidence_score=evidence_score,
            observer_count=observer_count,
            status=status,
            metric=metric,
        )
        if incident_id:
            flag.incident_id = incident_id
        return flag

    def detect_simulated(
        self,
        entity: str,
        metric: str,
        evidence_score: float = 0.82,
        observer_count: int = 7,
        status: str = "UNHEALTHY",
    ) -> DetectionFlag:
        """PoC fallback when no observer reports are available."""
        return DetectionFlag(
            entity=entity,
            evidence_score=evidence_score,
            observer_count=observer_count,
            status=status,
            metric=metric,
        )
