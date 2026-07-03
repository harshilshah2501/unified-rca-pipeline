"""Synthetic Figure 1 crawler incident fixture from Murphy paper."""

from __future__ import annotations

from datetime import datetime

from murphy.adapters.simulated_store import SimulatedMetricStore
from murphy.types import Symptom

APP_ID = "web_app"
INCIDENT_TIME = datetime(2024, 6, 15, 12, 0, 0)


def build_crawler_incident_store(
    seed: int = 42,
    incident_scale: float = 8.0,
) -> SimulatedMetricStore:
    """
    Build simulated store reproducing paper Figure 1 incident.

    Crawler VM (heavy hitter) -> Frontend (degraded latency) -> Backend (high CPU).
    Includes Host/NIC/ToR infrastructure entities for cyclic topology.
    """
    store = SimulatedMetricStore(seed=seed)

    for entity in SimulatedMetricStore.build_figure1_topology(APP_ID):
        store.add_entity(entity)

    store.define_metric("crawler_vm", "session_count", mean=12.0, noise_std=1.0)
    store.define_metric("crawler_vm", "throughput", mean=120.0, noise_std=10.0)
    store.define_metric("frontend_ms", "latency_p90", mean=45.0, noise_std=3.0)
    store.define_metric("backend_vm_1", "cpu_usage", mean=0.25, noise_std=0.01)
    store.define_metric("normal_vm", "cpu_usage", mean=0.2, noise_std=0.006)

    store.add_causal_rule(
        "crawler_vm", "session_count", "frontend_ms", "latency_p90",
        coefficient=0.8, intercept=45.0,
    )
    store.add_causal_rule(
        "frontend_ms", "latency_p90", "backend_vm_1", "cpu_usage",
        coefficient=0.004, intercept=0.25,
    )

    store.inject_fault(
        "crawler_vm", "session_count",
        fault_type="spike", multiplier=incident_scale,
    )
    store.inject_fault(
        "crawler_vm", "throughput",
        fault_type="spike", multiplier=incident_scale,
    )

    store.simulate(incident_time=INCIDENT_TIME, lookback_days=7, interval_minutes=30)
    return store


def build_crawler_symptom() -> Symptom:
    store = build_crawler_incident_store()
    cpu = store.get_current_metrics("backend_vm_1", INCIDENT_TIME)["cpu_usage"]
    return Symptom(
        entity_id="backend_vm_1",
        metric_name="cpu_usage",
        observed_value=cpu,
        incident_time=INCIDENT_TIME,
    )
