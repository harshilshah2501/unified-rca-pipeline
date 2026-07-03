"""Unit tests for MRF diagnosis engine."""

from datetime import datetime, timedelta

import numpy as np

from murphy.graph import RelationshipGraph
from murphy.mrf import EntityModel, MRFDiagnosisEngine
from murphy.store import InMemoryMetricStore
from murphy.types import Entity, MetricSample, Symptom, model_key


def _make_chain_store(n: int = 200, incident_spike: float = 5.0) -> InMemoryMetricStore:
    """Simple A -> B -> C causal chain for MRF tests."""
    entities = [
        Entity("a", "vm", "app", metadata={"neighbors": ["b"]}),
        Entity("b", "microservice", "app", metadata={"neighbors": ["a", "c"]}),
        Entity("c", "vm", "app", metadata={"neighbors": ["b"]}),
    ]
    store = InMemoryMetricStore(entities=entities)
    start = datetime(2024, 1, 1)
    interval = timedelta(minutes=30)
    rng = np.random.default_rng(0)

    for i in range(n):
        ts = start + i * interval
        a_val = 10.0 + rng.normal(0, 1)
        b_val = 20.0 + 2.0 * a_val + rng.normal(0, 2)
        is_incident = i >= n - 5
        if is_incident:
            a_val *= incident_spike
            b_val = 20.0 + 2.0 * a_val + rng.normal(0, 2)
        c_val = 0.1 + 0.002 * b_val + rng.normal(0, 0.01)
        if is_incident:
            c_val = min(0.99, 0.1 + 0.002 * b_val + 0.3)

        store.add_samples(
            [
                MetricSample("a", "load", ts, float(a_val)),
                MetricSample("b", "latency_p90", ts, float(b_val)),
                MetricSample("c", "cpu_usage", ts, float(np.clip(c_val, 0, 1))),
            ]
        )
    return store


def test_entity_model_top_b_neighbor_selection():
    n = 100
    rng = np.random.default_rng(1)
    target = rng.standard_normal(n).tolist()
    historical = {
        f"neighbor_{i}:metric": (rng.standard_normal(n) * (0.1 * i + 0.01)).tolist()
        for i in range(15)
    }
    historical["neighbor_14:metric"] = target.copy()

    model = EntityModel("v", "cpu_usage")
    model.fit(historical, target, top_b=10)
    assert len(model.selected_features) == 10
    assert "neighbor_14:metric" in model.selected_features


def test_entity_model_ridge_vs_random_baseline():
    n = 150
    rng = np.random.default_rng(2)
    x = rng.standard_normal(n)
    target = (2.0 * x + rng.normal(0, 0.5, n)).tolist()
    historical = {"n1:load": x.tolist()}

    model = EntityModel("v", "cpu_usage")
    model.fit(historical, target, top_b=10)

    test_x = {"n1:load": 1.5}
    pred = model.predict(test_x)
    random_pred = float(np.mean(target))
    ridge_err = abs(pred - (2.0 * 1.5))
    random_err = abs(random_pred - (2.0 * 1.5))
    assert ridge_err < random_err


def test_counterfactual_lower_than_baseline_for_root_cause():
    store = _make_chain_store(n=200)
    graph = RelationshipGraph()
    graph.build_from_monitoring_db("app", store)
    for e in store.get_entity_metadata("app"):
        graph.add_entity(e)
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")

    incident_time = datetime(2024, 1, 1) + 199 * timedelta(minutes=30)
    engine = MRFDiagnosisEngine(
        graph=graph,
        store=store,
        gibbs_iterations=4,
        n_samples=200,
        parallel=False,
    )

    current_metrics = {}
    historical_stats = {}
    for eid in ["a", "b", "c"]:
        current_metrics[eid] = store.get_current_metrics(eid, incident_time)
        historical_stats[eid] = store.compute_historical_stats(eid, incident_time)

    models = engine.train_all_models({"a", "b", "c"}, incident_time)
    d1, d2 = engine.evaluate_candidate(
        "a",
        "load",
        "c",
        "cpu_usage",
        current_metrics,
        models,
        historical_stats,
    )
    assert len(d1) == 200
    assert len(d2) == 200
    assert np.mean(d1) < np.mean(d2)


def test_ttest_significance_threshold():
    d1 = list(np.random.normal(0.3, 0.05, 500))
    d2 = list(np.random.normal(0.8, 0.05, 500))
    is_sig, p_val = MRFDiagnosisEngine.is_root_cause(d1, d2)
    assert is_sig
    assert p_val < 0.05


def test_gibbs_iterations_improves_prediction():
    store = _make_chain_store(n=200)
    graph = RelationshipGraph()
    for e in store.get_entity_metadata("app"):
        graph.add_entity(e)
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")

    incident_time = datetime(2024, 1, 1) + 199 * timedelta(minutes=30)
    current_metrics = {
        eid: store.get_current_metrics(eid, incident_time)
        for eid in ["a", "b", "c"]
    }
    historical_stats = {
        eid: store.compute_historical_stats(eid, incident_time)
        for eid in ["a", "b", "c"]
    }

    engine_w1 = MRFDiagnosisEngine(
        graph=graph, store=store, gibbs_iterations=1, n_samples=100, parallel=False
    )
    engine_w4 = MRFDiagnosisEngine(
        graph=graph, store=store, gibbs_iterations=4, n_samples=100, parallel=False
    )
    models = engine_w4.train_all_models({"a", "b", "c"}, incident_time)

    true_cpu = current_metrics["c"]["cpu_usage"]
    separations_w1: list[float] = []
    separations_w4: list[float] = []

    for _ in range(20):
        d1_w1, d2_w1 = engine_w1.evaluate_candidate(
            "a", "load", "c", "cpu_usage",
            current_metrics, models, historical_stats,
        )
        d1_w4, d2_w4 = engine_w4.evaluate_candidate(
            "a", "load", "c", "cpu_usage",
            current_metrics, models, historical_stats,
        )
        separations_w1.append(abs(np.mean(d1_w1) - np.mean(d2_w1)))
        separations_w4.append(abs(np.mean(d1_w4) - np.mean(d2_w4)))

    assert np.mean(separations_w4) >= np.mean(separations_w1)
