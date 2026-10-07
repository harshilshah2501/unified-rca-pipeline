"""Murphy adapter — maps hop schemas to murphy.Murphy.diagnose()."""

from __future__ import annotations

from datetime import datetime, timedelta

from murphy.murphy import Murphy
from murphy.store import MetricStore
from murphy.types import Symptom

from poc.types import MurphyRequest, MurphyResult


def scores_to_posterior(root_causes: list) -> dict[str, float]:
    """Normalize Murphy anomaly scores into a probability-like posterior."""
    if not root_causes:
        return {}

    scores = {rc.entity_id: max(rc.anomaly_score, 0.0) for rc in root_causes}
    total = sum(scores.values())
    if total <= 0:
        n = len(scores)
        return {eid: 1.0 / n for eid in scores}

    return {eid: score / total for eid, score in scores.items()}


class MurphyAdapter:
    def __init__(self, store: MetricStore, murphy: Murphy | None = None) -> None:
        self.store = store
        self.murphy = murphy or Murphy(monitoring_db=store)

    def build_symptom(
        self,
        request: MurphyRequest,
        incident_time: datetime | None = None,
    ) -> Symptom:
        entity = request.symptom_entity
        metric = request.symptom_metric
        incident_time = incident_time or request.timestamp

        metrics = self.store.get_current_metrics(entity, incident_time)
        if metric not in metrics:
            raise ValueError(
                f"Metric {metric!r} not found for entity {entity!r} at {incident_time}"
            )

        return Symptom(
            entity_id=entity,
            metric_name=metric,
            observed_value=metrics[metric],
            incident_time=incident_time,
        )

    def diagnose(self, request: MurphyRequest, incident_time: datetime | None = None) -> MurphyResult:
        symptom = self.build_symptom(request, incident_time)
        murphy = self.murphy
        if request.gibbs_iterations != murphy.engine.gibbs_iterations:
            murphy = Murphy(
                monitoring_db=self.store,
                gibbs_iterations=request.gibbs_iterations,
            )

        result = murphy.diagnose(symptom, incident_time=symptom.incident_time)
        posterior = scores_to_posterior(result.root_causes)

        return MurphyResult(
            incident_id=request.incident_id,
            symptom_entity=request.symptom_entity,
            symptom_metric=request.symptom_metric,
            posterior=posterior,
            converged=bool(posterior),
        )


def default_windows(incident_time: datetime) -> tuple[datetime, datetime, datetime]:
    """Return baseline_start, baseline_end (=incident), suffering_end."""
    baseline_start = incident_time - timedelta(hours=2)
    suffering_end = incident_time + timedelta(minutes=5)
    return baseline_start, incident_time, suffering_end
