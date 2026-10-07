"""Murphy Figure 1 crawler incident — end-to-end PoC scenario."""

from __future__ import annotations

from datetime import datetime

from murphy.murphy import Murphy
from murphy.tests.fixtures.crawler_incident import (
    INCIDENT_TIME,
    build_crawler_incident_store,
)

from poc.adapters.panorama import PanoramaAdapter
from poc.orchestrator import UnifiedRCAOrchestrator
from poc.types import DetectionFlag, RCAVerdict


def build_crawler_orchestrator() -> UnifiedRCAOrchestrator:
    store = build_crawler_incident_store()
    orchestrator = UnifiedRCAOrchestrator(
        metric_store=store,
    )
    orchestrator.murphy.murphy = Murphy(
        monitoring_db=store,
        gibbs_iterations=4,
        n_samples=800,
        max_graph_hops=5,
        parallel=False,
    )
    return orchestrator


def build_crawler_detection_flag(incident_time: datetime | None = None) -> DetectionFlag:
    """
    Simulated Panorama output for the crawler incident.

    Observers converge on frontend_ms latency degradation. Murphy receives
    the downstream CPU symptom at backend_vm_1 (paper Figure 1).
    """
    incident_time = incident_time or INCIDENT_TIME
    flag = PanoramaAdapter().detect_simulated(
        entity="frontend_ms",
        metric="latency_p90",
        evidence_score=0.82,
        observer_count=7,
        status="UNHEALTHY",
    )
    flag.timestamp = incident_time
    flag.symptom_entity = "backend_vm_1"
    flag.symptom_metric = "cpu_usage"
    return flag


def run_crawler_scenario() -> RCAVerdict:
    orchestrator = build_crawler_orchestrator()
    flag = build_crawler_detection_flag()
    return orchestrator.run_pipeline(flag, incident_time=INCIDENT_TIME)
