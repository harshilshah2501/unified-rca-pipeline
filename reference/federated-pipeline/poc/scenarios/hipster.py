"""Online Boutique (hipster) Federated RCA scenario.

Uses:
- Real Panorama majority voting over observer reports
- Real Murphy MRF on a boutique call-graph fixture
- Nezha pattern scoring (live dataset when available, else scored fallback)
"""

from __future__ import annotations

from datetime import datetime

from murphy.adapters.simulated_store import SimulatedMetricStore
from murphy.murphy import Murphy
from murphy.types import Entity

from poc.adapters.panorama import PanoramaAdapter
from poc.adapters.panorama_majority import ObserverReport, Status
from poc.orchestrator import UnifiedRCAOrchestrator
from poc.types import DetectionFlag, RCAVerdict

APP_ID = "online_boutique"
INCIDENT_TIME = datetime(2022, 8, 22, 4, 44, 0)

# First checkoutservice cpu_contention fault from 2022-08-22 fault list.
HIPSTER_FAULT = {
    "inject_time": "2022-08-22 04:44:16",
    "inject_pod": "checkoutservice-578fcf4766-9csqn",
    "inject_type": "cpu_contention",
    "service": "checkoutservice",
}


def build_hipster_store(seed: int = 7) -> SimulatedMetricStore:
    """
    Boutique topology: frontend → checkout → (payment, shipping, cart).

    Injects CPU contention on checkoutservice that propagates to frontend latency.
    """
    store = SimulatedMetricStore(seed=seed)

    entities = [
        Entity(
            "frontend", "microservice", APP_ID,
            metadata={
                "neighbors": ["checkoutservice", "cartservice"],
                "downstream": ["checkoutservice", "cartservice"],
            },
        ),
        Entity(
            "checkoutservice", "microservice", APP_ID,
            metadata={
                "neighbors": ["frontend", "paymentservice", "shippingservice", "cartservice"],
                "upstream": ["frontend"],
                "downstream": ["paymentservice", "shippingservice", "cartservice"],
            },
        ),
        Entity(
            "paymentservice", "microservice", APP_ID,
            metadata={"neighbors": ["checkoutservice"], "upstream": ["checkoutservice"]},
        ),
        Entity(
            "shippingservice", "microservice", APP_ID,
            metadata={"neighbors": ["checkoutservice"], "upstream": ["checkoutservice"]},
        ),
        Entity(
            "cartservice", "microservice", APP_ID,
            metadata={
                "neighbors": ["frontend", "checkoutservice"],
                "upstream": ["frontend", "checkoutservice"],
            },
        ),
    ]
    for entity in entities:
        store.add_entity(entity)

    store.define_metric("checkoutservice", "cpu_usage", mean=0.22, noise_std=0.01)
    store.define_metric("frontend", "latency_p90", mean=40.0, noise_std=2.0)
    store.define_metric("paymentservice", "latency_p90", mean=25.0, noise_std=1.5)
    store.define_metric("shippingservice", "latency_p90", mean=30.0, noise_std=1.5)
    store.define_metric("cartservice", "latency_p90", mean=20.0, noise_std=1.0)

    store.add_causal_rule(
        "checkoutservice", "cpu_usage", "frontend", "latency_p90",
        coefficient=120.0, intercept=40.0,
    )
    store.add_causal_rule(
        "checkoutservice", "cpu_usage", "paymentservice", "latency_p90",
        coefficient=40.0, intercept=25.0,
    )

    store.inject_fault(
        "checkoutservice", "cpu_usage",
        fault_type="spike", multiplier=6.0,
    )
    store.simulate(incident_time=INCIDENT_TIME, lookback_days=7, interval_minutes=30)
    return store


def build_hipster_observer_reports() -> list[ObserverReport]:
    """Observers around checkout agree it is unhealthy (Panorama-style evidence)."""
    subject = "checkoutservice"
    return [
        ObserverReport("frontend", subject, "cpu", Status.UNHEALTHY, 80.0, ts=1.0),
        ObserverReport("paymentservice", subject, "cpu", Status.UNHEALTHY, 75.0, ts=1.0),
        ObserverReport("shippingservice", subject, "cpu", Status.UNHEALTHY, 70.0, ts=1.0),
        ObserverReport("cartservice", subject, "cpu", Status.MAYBE_UNHEALTHY, 55.0, ts=1.0),
        ObserverReport("frontend", subject, "cpu", Status.UNHEALTHY, 85.0, ts=2.0),
        ObserverReport("paymentservice", subject, "cpu", Status.UNHEALTHY, 78.0, ts=2.0),
        # One healthy outlier — majority should still flag UNHEALTHY.
        ObserverReport("adservice", subject, "cpu", Status.HEALTHY, 10.0, ts=2.0),
    ]


def build_hipster_detection_flag() -> DetectionFlag:
    adapter = PanoramaAdapter()
    flag = adapter.detect_from_reports(
        subject="checkoutservice",
        reports=build_hipster_observer_reports(),
    )
    if flag is None:
        raise RuntimeError("Panorama majority did not flag checkoutservice")
    flag.timestamp = INCIDENT_TIME
    # Symptom visible at frontend; root cause is checkout CPU.
    flag.symptom_entity = "frontend"
    flag.symptom_metric = "latency_p90"
    return flag


def build_hipster_orchestrator() -> UnifiedRCAOrchestrator:
    store = build_hipster_store()
    from poc.orchestrator import OrchestratorConfig

    orchestrator = UnifiedRCAOrchestrator(
        metric_store=store,
        config=OrchestratorConfig(tenant="hipster"),
    )
    orchestrator.murphy.murphy = Murphy(
        monitoring_db=store,
        gibbs_iterations=4,
        n_samples=800,
        max_graph_hops=4,
        parallel=False,
    )
    # Prefer live Nezha dataset for this service when available.
    orchestrator.nezha.prefer_dataset = True
    orchestrator.nezha.dataset_ns = "hipster"
    orchestrator.nezha.dataset_fault = HIPSTER_FAULT
    return orchestrator


def run_hipster_scenario() -> RCAVerdict:
    orchestrator = build_hipster_orchestrator()
    flag = build_hipster_detection_flag()
    return orchestrator.run_pipeline(flag, incident_time=INCIDENT_TIME)
