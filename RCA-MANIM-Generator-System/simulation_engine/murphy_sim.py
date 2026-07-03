"""Murphy counterfactual simulation with frame instrumentation."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from murphy.adapters.simulated_store import SimulatedMetricStore
from murphy.graph import RelationshipGraph
from murphy.mrf import (
    MRFDiagnosisEngine,
    _GibbsContext,
    _build_neighbor_values,
    _counterfactual_values_for_entity,
)
from murphy.types import Entity, Symptom, model_key
from rca_spec_parser import RCASpec
from simulation_engine.base import SimulationFrame


def _parse_incident_time(spec: RCASpec) -> datetime:
    if spec.incident_time:
        return datetime.fromisoformat(spec.incident_time)
    return datetime(2024, 6, 15, 12, 0, 0)


def _build_store(spec: RCASpec) -> SimulatedMetricStore:
    store = SimulatedMetricStore(seed=spec.seed)
    app_id = spec.app_id or "web_app"

    for node in spec.nodes:
        entity = Entity(
            id=node["id"],
            entity_type=node.get("entity_type", "vm"),
            app_id=app_id,
            metadata={"display_name": node["id"]},
        )
        store.add_entity(entity)
        means = node.get("mean", {})
        stds = node.get("std", {})
        noise = node.get("noise_std", {})
        for metric in node.get("metrics", []):
            store.define_metric(
                node["id"],
                metric,
                mean=float(means.get(metric, 1.0)),
                std=float(stds.get(metric, 0.0)),
                noise_std=float(noise[metric]) if metric in noise else None,
            )

    for edge in spec.edges:
        src_metric = edge.get("src_metric")
        dst_metric = edge.get("dst_metric")
        if src_metric and dst_metric:
            store.add_causal_rule(
                edge["from"],
                src_metric,
                edge["to"],
                dst_metric,
                coefficient=float(edge.get("weight", 1.0)),
                intercept=float(edge.get("intercept", 0.0)),
            )

    if spec.fault.metrics:
        for metric in spec.fault.metrics:
            store.inject_fault(
                spec.fault.target,
                metric,
                fault_type=spec.fault.type if spec.fault.type in ("spike", "step", "drift") else "spike",
                multiplier=spec.fault.multiplier,
            )

    incident_time = _parse_incident_time(spec)
    store.simulate(incident_time=incident_time, lookback_days=7, interval_minutes=30)
    return store


def _build_graph(spec: RCASpec, store: SimulatedMetricStore) -> RelationshipGraph:
    graph = RelationshipGraph(max_hops=5)
    app_id = spec.app_id or "web_app"
    for node in spec.nodes:
        graph.add_entity(
            Entity(
                id=node["id"],
                entity_type=node.get("entity_type", "vm"),
                app_id=app_id,
                metadata={"display_name": node["id"]},
            )
        )
    for edge in spec.edges:
        graph.add_edge(
            edge["from"],
            edge["to"],
            bidirectional=bool(edge.get("bidirectional", False)),
        )
    return graph


def _gibbs_sample_traced(
    assignment: dict[str, dict[str, float]],
    ctx: _GibbsContext,
    path_entities: list[str],
) -> tuple[float, list[dict[str, float]]]:
    sweeps: list[dict[str, float]] = []
    for _ in range(ctx.gibbs_iterations):
        for entity_id in ctx.path_entities:
            if entity_id == ctx.fixed_entity_id:
                continue
            metrics = ctx.entity_metrics.get(entity_id, [])
            if not metrics:
                continue
            in_nbrs = ctx.in_neighbors.get(entity_id, [])
            neighbor_values = _build_neighbor_values(entity_id, assignment, in_nbrs)
            if entity_id not in assignment:
                assignment[entity_id] = {}
            for metric_name in metrics:
                key = model_key(entity_id, metric_name)
                model = ctx.models.get(key)
                if model is None:
                    continue
                assignment[entity_id][metric_name] = model.sample(neighbor_values)
        snapshot: dict[str, float] = {}
        for entity_id in path_entities:
            for metric_name, value in assignment.get(entity_id, {}).items():
                snapshot[f"{entity_id}:{metric_name}"] = float(value)
        sweeps.append(snapshot)

    symptom_metrics = assignment.get(ctx.symptom_entity_id, {})
    symptom_val = symptom_metrics.get(ctx.symptom_metric, 0.0)
    return float(symptom_val), sweeps


def _run_traced_gibbs(
    candidate_entity_id: str,
    start_values: dict[str, float],
    current_metrics: dict[str, dict[str, float]],
    ctx: _GibbsContext,
    n_samples: int,
    path_entities: list[str],
    rng: np.random.Generator,
    sample_stride: int,
) -> tuple[list[float], list[dict[str, float]]]:
    samples: list[float] = []
    trace_frames: list[dict[str, float]] = []
    for i in range(n_samples):
        assignment = {eid: dict(metrics) for eid, metrics in current_metrics.items()}
        if candidate_entity_id not in assignment:
            assignment[candidate_entity_id] = {}
        for metric_name, value in start_values.items():
            assignment[candidate_entity_id][metric_name] = value
        symptom_val, sweeps = _gibbs_sample_traced(assignment, ctx, path_entities)
        samples.append(symptom_val)
        if i % sample_stride == 0 and sweeps:
            trace_frames.append(sweeps[-1])
    return samples, trace_frames


class MurphySimulator:
    def run(self, spec: RCASpec) -> list[SimulationFrame]:
        np.random.seed(spec.seed)
        store = _build_store(spec)
        graph = _build_graph(spec, store)
        incident_time = _parse_incident_time(spec)

        symptom_entity = (spec.symptom or {}).get("entity", spec.nodes[-1]["id"])
        symptom_metric = (spec.symptom or {}).get("metric", spec.nodes[-1].get("metrics", ["value"])[0])
        current = store.get_current_metrics(symptom_entity, incident_time)
        observed = current.get(symptom_metric, 0.0)

        symptom = Symptom(
            entity_id=symptom_entity,
            metric_name=symptom_metric,
            observed_value=observed,
            incident_time=incident_time,
        )

        engine = MRFDiagnosisEngine(
            graph=graph,
            store=store,
            gibbs_iterations=spec.simulation.inner_sweeps,
            n_samples=spec.simulation.outer_samples,
            parallel=False,
        )

        app_id = spec.app_id or "web_app"
        current_metrics: dict[str, dict[str, float]] = {}
        historical_stats: dict[str, dict[str, tuple[float, float]]] = {}
        for entity_id in graph.entity_ids:
            current_metrics[entity_id] = store.get_current_metrics(entity_id, incident_time)
            historical_stats[entity_id] = store.compute_historical_stats(entity_id, incident_time)

        candidates = graph.prune_candidates(
            symptom.entity_id, current_metrics, historical_stats
        )
        candidates.discard(symptom.entity_id)

        train_entities = set(candidates)
        train_entities.add(symptom.entity_id)
        focus_candidate = spec.fault.target
        if focus_candidate not in train_entities:
            train_entities.add(focus_candidate)
        train_entities.update(
            graph.shortest_path_subgraph(focus_candidate, symptom.entity_id)
        )

        models = engine.train_all_models(train_entities, incident_time)
        path_entities = graph.shortest_path_subgraph(focus_candidate, symptom.entity_id)
        if not path_entities:
            path_entities = [focus_candidate, symptom.entity_id]

        in_neighbors = {eid: graph.in_neighbors(eid) for eid in graph.entity_ids}
        entity_metrics: dict[str, list[str]] = {}
        for key in models:
            eid, metric = key.split(":", 1)
            entity_metrics.setdefault(eid, []).append(metric)

        focus_metric = spec.fault.metrics[0] if spec.fault.metrics else next(
            iter(current_metrics.get(focus_candidate, {})), symptom_metric
        )

        ctx = _GibbsContext(
            path_entities=path_entities,
            in_neighbors=in_neighbors,
            entity_metrics=entity_metrics,
            models=models,
            symptom_entity_id=symptom.entity_id,
            symptom_metric=symptom.metric_name,
            gibbs_iterations=spec.simulation.inner_sweeps,
            fixed_entity_id=focus_candidate,
        )

        counterfactual_values = _counterfactual_values_for_entity(
            focus_candidate, current_metrics, historical_stats, 2.0
        )
        true_values = dict(current_metrics.get(focus_candidate, {}))

        sample_stride = max(1, spec.simulation.outer_samples // 20)
        d1, d1_traces = _run_traced_gibbs(
            focus_candidate,
            counterfactual_values,
            current_metrics,
            ctx,
            spec.simulation.outer_samples,
            path_entities,
            np.random.default_rng(spec.seed),
            sample_stride,
        )
        d2, d2_traces = _run_traced_gibbs(
            focus_candidate,
            true_values,
            current_metrics,
            ctx,
            spec.simulation.outer_samples,
            path_entities,
            np.random.default_rng(spec.seed + 1),
            sample_stride,
        )

        is_sig, p_value = MRFDiagnosisEngine.is_root_cause_static(d1, d2)
        frames: list[SimulationFrame] = []

        baseline_states: dict[str, float | str] = {}
        for eid, metrics in current_metrics.items():
            for mname, val in metrics.items():
                baseline_states[f"{eid}:{mname}"] = val

        frames.append(
            SimulationFrame(
                step=0,
                node_states=baseline_states,
                distributions={},
                edges_active=[],
                metadata={
                    "phase": "baseline",
                    "path_entities": path_entities,
                    "focus_candidate": focus_candidate,
                    "focus_metric": focus_metric,
                    "symptom": f"{symptom_entity}:{symptom_metric}",
                },
            )
        )

        for hop_idx in range(1, len(path_entities)):
            src = path_entities[hop_idx - 1]
            dst = path_entities[hop_idx]
            hop_states = dict(baseline_states)
            frames.append(
                SimulationFrame(
                    step=hop_idx,
                    node_states=hop_states,
                    distributions={},
                    edges_active=[(src, dst)],
                    metadata={
                        "phase": "propagation",
                        "hop": hop_idx,
                        "world": "D2",
                    },
                )
            )

        convergence_start = len(frames)
        max_traces = max(len(d1_traces), len(d2_traces))
        for i in range(max_traces):
            d1_partial = d1[: (i + 1) * sample_stride]
            d2_partial = d2[: (i + 1) * sample_stride]
            trace_state: dict[str, float | str] = {}
            if i < len(d2_traces):
                trace_state.update({k: v for k, v in d2_traces[i].items()})
            frames.append(
                SimulationFrame(
                    step=convergence_start + i,
                    node_states=trace_state,
                    distributions={"D1": d1_partial, "D2": d2_partial},
                    edges_active=[],
                    metadata={
                        "phase": "convergence",
                        "sample_index": (i + 1) * sample_stride,
                        "d1_mean": float(np.mean(d1_partial)) if d1_partial else None,
                        "d2_mean": float(np.mean(d2_partial)) if d2_partial else None,
                    },
                )
            )

        frames.append(
            SimulationFrame(
                step=len(frames),
                node_states=baseline_states,
                distributions={"D1": d1, "D2": d2},
                edges_active=[],
                metadata={
                    "phase": "result",
                    "p_value": p_value,
                    "is_significant": is_sig,
                    "d1_mean": float(np.mean(d1)),
                    "d2_mean": float(np.mean(d2)),
                    "ttest": (
                        f"p={p_value:.4f} significant"
                        if is_sig
                        else f"p={p_value:.4f} not significant"
                    ),
                },
            )
        )
        return frames
