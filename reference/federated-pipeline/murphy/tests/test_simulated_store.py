"""Tests for SimulatedMetricStore fault injection and causal propagation."""

from datetime import datetime

from murphy.adapters.simulated_store import SimulatedMetricStore
from murphy.types import Entity


def test_simulated_store_generates_baseline_and_incident():
    incident = datetime(2024, 1, 8, 12, 0, 0)
    store = SimulatedMetricStore(seed=1)
    store.add_entity(Entity("vm_a", "vm", "app1", metadata={"neighbors": ["vm_b"]}))
    store.add_entity(Entity("vm_b", "vm", "app1", metadata={"neighbors": ["vm_a"]}))
    store.define_metric("vm_a", "load", mean=10.0, noise_std=0.5)
    store.define_metric("vm_b", "cpu_usage", mean=0.3, noise_std=0.01)
    store.add_causal_rule("vm_a", "load", "vm_b", "cpu_usage", coefficient=0.01, intercept=0.2)
    store.inject_fault("vm_a", "load", fault_type="spike", multiplier=10.0)
    store.simulate(incident_time=incident, lookback_days=1, interval_minutes=30)

    hist = store.get_historical_metrics("vm_a", "load", incident)
    assert len(hist) > 0
    assert all(s.timestamp < incident for s in hist)

    current_a = store.get_current_metrics("vm_a", incident)["load"]
    current_b = store.get_current_metrics("vm_b", incident)["cpu_usage"]
    hist_mean_a = store.compute_historical_stats("vm_a", incident)["load"][0]

    assert current_a > hist_mean_a * 5
    assert current_b > 0.35


def test_figure1_topology_includes_infrastructure():
    entities = SimulatedMetricStore.build_figure1_topology()
    types = {e.entity_type for e in entities}
    assert "host" in types
    assert "nic" in types
    assert "router" in types
