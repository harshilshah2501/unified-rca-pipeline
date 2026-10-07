"""MRF diagnosis engine — Ridge regression + counterfactual Gibbs sampling."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from scipy import stats
from sklearn.linear_model import Ridge

from murphy.graph import RelationshipGraph
from murphy.ranker import RootCauseRanker
from murphy.store import MetricStore
from murphy.types import RootCause, Symptom, model_key

_MIN_TRAINING_SLICES = 10
_STD_FLOOR = 1e-9


@dataclass
class _GibbsContext:
    path_entities: list[str]
    in_neighbors: dict[str, list[str]]
    entity_metrics: dict[str, list[str]]
    models: dict[str, EntityModel]
    symptom_entity_id: str
    symptom_metric: str
    gibbs_iterations: int
    fixed_entity_id: str


class EntityModel:
    """Ridge regression model for one entity's metric, trained on in-neighbors."""

    def __init__(self, entity_id: str, metric_name: str, alpha: float = 1.0) -> None:
        self.entity_id = entity_id
        self.metric_name = metric_name
        self.alpha = alpha
        self.selected_features: list[str] = []
        self._ridge: Ridge | None = None
        self.residual_std: float = 1.0
        self.fallback_mean: float = 0.0
        self.fallback_std: float = 1.0
        self._feature_means: dict[str, float] = {}
        self.fitted = False

    def fit(
        self,
        historical_data: dict[str, list[float]],
        target_series: list[float],
        top_b: int = 10,
    ) -> None:
        n = len(target_series)
        if n < _MIN_TRAINING_SLICES:
            self.fallback_mean = float(np.mean(target_series)) if n else 0.0
            self.fallback_std = max(float(np.std(target_series)) if n else 1.0, _STD_FLOOR)
            self.fitted = False
            return

        correlations: list[tuple[str, float]] = []
        target_arr = np.array(target_series, dtype=float)
        for feature_id, series in historical_data.items():
            if len(series) != n:
                continue
            feat_arr = np.array(series, dtype=float)
            if np.std(feat_arr) < _STD_FLOOR or np.std(target_arr) < _STD_FLOOR:
                corr = 0.0
            else:
                corr = float(np.corrcoef(feat_arr, target_arr)[0, 1])
            correlations.append((feature_id, abs(corr)))

        correlations.sort(key=lambda x: x[1], reverse=True)
        self.selected_features = [f for f, _ in correlations[:top_b]]

        if not self.selected_features:
            self.fallback_mean = float(np.mean(target_arr))
            self.fallback_std = max(float(np.std(target_arr)), _STD_FLOOR)
            self.fitted = False
            return

        X = np.column_stack(
            [historical_data[f] for f in self.selected_features]
        )
        for i, feat in enumerate(self.selected_features):
            self._feature_means[feat] = float(np.mean(X[:, i]))

        self._ridge = Ridge(alpha=self.alpha)
        self._ridge.fit(X, target_arr)
        preds = self._ridge.predict(X)
        residuals = target_arr - preds
        self.residual_std = max(float(np.std(residuals)), _STD_FLOOR)
        self.fitted = True

    def _feature_vector(self, neighbor_values: dict[str, float]) -> np.ndarray:
        return np.array(
            [
                neighbor_values.get(f, self._feature_means.get(f, 0.0))
                for f in self.selected_features
            ],
            dtype=float,
        ).reshape(1, -1)

    def predict(self, neighbor_values: dict[str, float]) -> float:
        if not self.fitted or self._ridge is None:
            return self.fallback_mean
        return float(self._ridge.predict(self._feature_vector(neighbor_values))[0])

    def sample(self, neighbor_values: dict[str, float]) -> float:
        if not self.fitted or self._ridge is None:
            return float(
                np.random.normal(self.fallback_mean, self.fallback_std)
            )
        pred = self.predict(neighbor_values)
        return float(np.random.normal(pred, self.residual_std))


def _build_neighbor_values(
    entity_id: str,
    assignment: dict[str, dict[str, float]],
    in_neighbors: list[str],
) -> dict[str, float]:
    neighbor_values: dict[str, float] = {}
    for neighbor_id in in_neighbors:
        metrics = assignment.get(neighbor_id, {})
        for metric_name, value in metrics.items():
            neighbor_values[model_key(neighbor_id, metric_name)] = value
    return neighbor_values


def _gibbs_sample(
    assignment: dict[str, dict[str, float]],
    ctx: _GibbsContext,
) -> float:
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

    symptom_metrics = assignment.get(ctx.symptom_entity_id, {})
    return symptom_metrics.get(ctx.symptom_metric, 0.0)


def _run_gibbs_samples(
    candidate_entity_id: str,
    candidate_metric: str,
    start_values: dict[str, float],
    current_metrics: dict[str, dict[str, float]],
    historical_stats: dict[str, dict[str, tuple[float, float]]],
    ctx: _GibbsContext,
    n_samples: int,
    counterfactual_stdevs: float = 2.0,
) -> list[float]:
    samples: list[float] = []
    for _ in range(n_samples):
        assignment = {
            eid: dict(metrics) for eid, metrics in current_metrics.items()
        }
        if candidate_entity_id not in assignment:
            assignment[candidate_entity_id] = {}
        for metric_name, value in start_values.items():
            assignment[candidate_entity_id][metric_name] = value
        samples.append(_gibbs_sample(assignment, ctx))
    return samples


def _counterfactual_values_for_entity(
    entity_id: str,
    current_metrics: dict[str, dict[str, float]],
    historical_stats: dict[str, dict[str, tuple[float, float]]],
    counterfactual_stdevs: float,
) -> dict[str, float]:
    """Counterfactual all metrics on entity A per paper step 1."""
    result: dict[str, float] = {}
    metrics = current_metrics.get(entity_id, {})
    stats = historical_stats.get(entity_id, {})
    for metric_name, current_val in metrics.items():
        mean, std = stats.get(metric_name, (current_val, 1.0))
        std = max(std, _STD_FLOOR)
        if current_val > mean:
            result[metric_name] = mean - counterfactual_stdevs * std
        elif current_val < mean:
            result[metric_name] = mean + counterfactual_stdevs * std
        else:
            result[metric_name] = current_val
    return result


def _evaluate_candidate_worker(args: tuple) -> dict[str, Any]:
    """Top-level picklable worker for parallel candidate evaluation."""
    (
        candidate_entity_id,
        candidate_metric,
        symptom_entity_id,
        symptom_metric,
        current_metrics,
        historical_stats,
        path_entities,
        in_neighbors,
        entity_metrics,
        models_data,
        gibbs_iterations,
        n_samples,
        counterfactual_stdevs,
    ) = args

    models: dict[str, EntityModel] = {}
    for key, data in models_data.items():
        model = EntityModel(data["entity_id"], data["metric_name"], data["alpha"])
        model.selected_features = data["selected_features"]
        model.residual_std = data["residual_std"]
        model.fallback_mean = data["fallback_mean"]
        model.fallback_std = data["fallback_std"]
        model.fitted = data["fitted"]
        model._feature_means = data["feature_means"]
        if data["fitted"]:
            model._ridge = Ridge(alpha=data["alpha"])
            model._ridge.coef_ = np.array(data["coef"])
            model._ridge.intercept_ = np.array(data["intercept"])
        models[key] = model

    ctx = _GibbsContext(
        path_entities=path_entities,
        in_neighbors=in_neighbors,
        entity_metrics=entity_metrics,
        models=models,
        symptom_entity_id=symptom_entity_id,
        symptom_metric=symptom_metric,
        gibbs_iterations=gibbs_iterations,
        fixed_entity_id=candidate_entity_id,
    )

    stats_a = historical_stats.get(candidate_entity_id, {}).get(
        candidate_metric, (0.0, 1.0)
    )
    mean_a, std_a = stats_a
    std_a = max(std_a, _STD_FLOOR)
    current_a = current_metrics.get(candidate_entity_id, {}).get(
        candidate_metric, mean_a
    )

    counterfactual_values = _counterfactual_values_for_entity(
        candidate_entity_id, current_metrics, historical_stats, counterfactual_stdevs
    )
    true_values = dict(current_metrics.get(candidate_entity_id, {}))

    d1 = _run_gibbs_samples(
        candidate_entity_id,
        candidate_metric,
        counterfactual_values,
        current_metrics,
        historical_stats,
        ctx,
        n_samples,
        counterfactual_stdevs,
    )
    d2 = _run_gibbs_samples(
        candidate_entity_id,
        candidate_metric,
        true_values,
        current_metrics,
        historical_stats,
        ctx,
        n_samples,
        counterfactual_stdevs,
    )
    is_sig, p_val = MRFDiagnosisEngine.is_root_cause_static(d1, d2)
    return {
        "entity_id": candidate_entity_id,
        "metric_name": candidate_metric,
        "d1_samples": d1,
        "d2_samples": d2,
        "p_value": p_val,
        "is_significant": is_sig,
    }


def _serialize_model(model: EntityModel) -> dict[str, Any]:
    data: dict[str, Any] = {
        "entity_id": model.entity_id,
        "metric_name": model.metric_name,
        "alpha": model.alpha,
        "selected_features": model.selected_features,
        "residual_std": model.residual_std,
        "fallback_mean": model.fallback_mean,
        "fallback_std": model.fallback_std,
        "fitted": model.fitted,
        "feature_means": model._feature_means,
    }
    if model.fitted and model._ridge is not None:
        data["coef"] = model._ridge.coef_.tolist()
        data["intercept"] = model._ridge.intercept_.tolist()
    return data


class MRFDiagnosisEngine:
    """Counterfactual Gibbs inference over the relationship graph."""

    def __init__(
        self,
        graph: RelationshipGraph,
        store: MetricStore,
        gibbs_iterations: int = 4,
        n_samples: int = 5000,
        counterfactual_stdevs: float = 2.0,
        ridge_alpha: float = 1.0,
        top_b_neighbors: int = 10,
        parallel: bool = True,
        max_workers: int | None = None,
    ) -> None:
        self.graph = graph
        self.store = store
        self.gibbs_iterations = gibbs_iterations
        self.n_samples = n_samples
        self.counterfactual_stdevs = counterfactual_stdevs
        self.ridge_alpha = ridge_alpha
        self.top_b_neighbors = top_b_neighbors
        self.parallel = parallel
        self.max_workers = max_workers
        self._ranker = RootCauseRanker()

    def train_all_models(
        self,
        candidate_entities: set[str],
        incident_time: datetime,
    ) -> dict[str, EntityModel]:
        models: dict[str, EntityModel] = {}
        for entity_id in candidate_entities:
            metric_names = self._list_metrics(entity_id, incident_time)
            in_nbrs = self.graph.in_neighbors(entity_id)
            for metric_name in metric_names:
                target_samples = self.store.get_historical_metrics(
                    entity_id, metric_name, incident_time
                )
                if not target_samples:
                    continue
                timestamps = [s.timestamp for s in target_samples]
                target_series = [s.value for s in target_samples]

                historical_data: dict[str, list[float]] = {}
                for neighbor_id in in_nbrs:
                    for n_metric in self._list_metrics(neighbor_id, incident_time):
                        n_samples_list = self.store.get_historical_metrics(
                            neighbor_id, n_metric, incident_time
                        )
                        aligned = self._align_to_timestamps(
                            n_samples_list, timestamps
                        )
                        if aligned:
                            historical_data[model_key(neighbor_id, n_metric)] = aligned

                model = EntityModel(entity_id, metric_name, alpha=self.ridge_alpha)
                model.fit(historical_data, target_series, top_b=self.top_b_neighbors)
                models[model_key(entity_id, metric_name)] = model
        return models

    def evaluate_candidate(
        self,
        candidate_entity_id: str,
        candidate_metric: str,
        symptom_entity_id: str,
        symptom_metric: str,
        current_metrics: dict[str, dict[str, float]],
        models: dict[str, EntityModel],
        historical_stats: dict[str, dict[str, tuple[float, float]]],
    ) -> tuple[list[float], list[float]]:
        path_entities = self.graph.shortest_path_subgraph(
            candidate_entity_id, symptom_entity_id
        )
        if not path_entities:
            return [], []

        ctx = self._build_gibbs_context(
            path_entities, models, symptom_entity_id, symptom_metric, candidate_entity_id
        )

        counterfactual_values = _counterfactual_values_for_entity(
            candidate_entity_id,
            current_metrics,
            historical_stats,
            self.counterfactual_stdevs,
        )
        true_values = dict(current_metrics.get(candidate_entity_id, {}))

        d1 = _run_gibbs_samples(
            candidate_entity_id,
            candidate_metric,
            counterfactual_values,
            current_metrics,
            historical_stats,
            ctx,
            self.n_samples,
            self.counterfactual_stdevs,
        )
        d2 = _run_gibbs_samples(
            candidate_entity_id,
            candidate_metric,
            true_values,
            current_metrics,
            historical_stats,
            ctx,
            self.n_samples,
            self.counterfactual_stdevs,
        )
        return d1, d2

    @staticmethod
    def is_root_cause(
        d1_samples: list[float],
        d2_samples: list[float],
        alpha: float = 0.05,
    ) -> tuple[bool, float]:
        return MRFDiagnosisEngine.is_root_cause_static(d1_samples, d2_samples, alpha)

    @staticmethod
    def is_root_cause_static(
        d1_samples: list[float],
        d2_samples: list[float],
        alpha: float = 0.05,
    ) -> tuple[bool, float]:
        if not d1_samples or not d2_samples:
            return False, 1.0
        result = stats.ttest_ind(d1_samples, d2_samples, alternative="less")
        p_value = float(result.pvalue)
        return p_value < alpha, p_value

    def diagnose(
        self,
        symptom: Symptom,
        incident_time: datetime,
        app_id: str | None = None,
    ) -> tuple[list[RootCause], dict[str, dict[str, float]], dict[str, dict[str, tuple[float, float]]]]:
        """
        Full diagnosis pipeline. Returns root causes, current_metrics, historical_stats.
        """
        if app_id is None:
            entity = self.store.get_entity(symptom.entity_id)
            if entity is None:
                entities = self.store.get_entity_metadata("")
                for e in entities:
                    if e.id == symptom.entity_id:
                        entity = e
                        break
            app_id = entity.app_id if entity else ""

        self.graph.build_from_monitoring_db(app_id, self.store)

        all_entities = self.graph.entity_ids
        current_metrics: dict[str, dict[str, float]] = {}
        historical_stats: dict[str, dict[str, tuple[float, float]]] = {}

        for entity_id in all_entities:
            current_metrics[entity_id] = self.store.get_current_metrics(
                entity_id, incident_time
            )
            historical_stats[entity_id] = self.store.compute_historical_stats(
                entity_id, incident_time
            )

        candidates = self.graph.prune_candidates(
            symptom.entity_id,
            current_metrics,
            historical_stats,
        )
        candidates.discard(symptom.entity_id)

        train_entities = set(candidates)
        train_entities.add(symptom.entity_id)
        for candidate_id in candidates:
            train_entities.update(
                self.graph.shortest_path_subgraph(candidate_id, symptom.entity_id)
            )

        models = self.train_all_models(train_entities, incident_time)

        candidate_pairs = self._candidate_metric_pairs(
            candidates, current_metrics, historical_stats
        )

        root_causes = self._evaluate_all_candidates(
            candidate_pairs,
            symptom,
            current_metrics,
            models,
            historical_stats,
        )

        for rc in root_causes:
            rc.anomaly_score = self._ranker.compute_anomaly_score(
                rc.entity_id,
                current_metrics.get(rc.entity_id, {}),
                historical_stats.get(rc.entity_id, {}),
            )

        return root_causes, current_metrics, historical_stats

    def _evaluate_all_candidates(
        self,
        candidate_pairs: list[tuple[str, str]],
        symptom: Symptom,
        current_metrics: dict[str, dict[str, float]],
        models: dict[str, EntityModel],
        historical_stats: dict[str, dict[str, tuple[float, float]]],
    ) -> list[RootCause]:
        if not candidate_pairs:
            return []

        in_neighbors = {
            eid: self.graph.in_neighbors(eid) for eid in self.graph.entity_ids
        }
        entity_metrics: dict[str, list[str]] = {}
        for key in models:
            eid, metric = key.split(":", 1)
            entity_metrics.setdefault(eid, []).append(metric)

        models_data = {k: _serialize_model(m) for k, m in models.items()}

        worker_args = []
        for candidate_id, candidate_metric in candidate_pairs:
            path_entities = self.graph.shortest_path_subgraph(
                candidate_id, symptom.entity_id
            )
            if not path_entities:
                continue
            worker_args.append(
                (
                    candidate_id,
                    candidate_metric,
                    symptom.entity_id,
                    symptom.metric_name,
                    current_metrics,
                    historical_stats,
                    path_entities,
                    in_neighbors,
                    entity_metrics,
                    models_data,
                    self.gibbs_iterations,
                    self.n_samples,
                    self.counterfactual_stdevs,
                )
            )

        results: list[dict[str, Any]] = []
        if self.parallel and len(worker_args) > 1:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(_evaluate_candidate_worker, args)
                    for args in worker_args
                ]
                for future in as_completed(futures):
                    results.append(future.result())
        else:
            for args in worker_args:
                results.append(_evaluate_candidate_worker(args))

        root_causes: list[RootCause] = []
        for r in results:
            if not r["is_significant"]:
                continue
            root_causes.append(
                RootCause(
                    entity_id=r["entity_id"],
                    metric_name=r["metric_name"],
                    anomaly_score=0.0,
                    d1_samples=r["d1_samples"],
                    d2_samples=r["d2_samples"],
                    p_value=r["p_value"],
                    is_significant=r["is_significant"],
                )
            )
        return root_causes

    def _candidate_metric_pairs(
        self,
        candidates: set[str],
        current_metrics: dict[str, dict[str, float]],
        historical_stats: dict[str, dict[str, tuple[float, float]]],
    ) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for entity_id in candidates:
            metrics = current_metrics.get(entity_id, {})
            stats = historical_stats.get(entity_id, {})
            best_metric: str | None = None
            best_score = -1.0
            for metric_name, value in metrics.items():
                if metric_name not in stats:
                    continue
                mean, std = stats[metric_name]
                std = max(std, _STD_FLOOR)
                score = abs(value - mean) / std
                if score > best_score:
                    best_score = score
                    best_metric = metric_name
            if best_metric is not None:
                pairs.append((entity_id, best_metric))
        return pairs

    def _build_gibbs_context(
        self,
        path_entities: list[str],
        models: dict[str, EntityModel],
        symptom_entity_id: str,
        symptom_metric: str,
        fixed_entity_id: str,
    ) -> _GibbsContext:
        entity_metrics: dict[str, list[str]] = {}
        for key in models:
            eid, metric = key.split(":", 1)
            if eid in path_entities:
                entity_metrics.setdefault(eid, []).append(metric)

        in_neighbors = {
            eid: self.graph.in_neighbors(eid) for eid in path_entities
        }
        return _GibbsContext(
            path_entities=path_entities,
            in_neighbors=in_neighbors,
            entity_metrics=entity_metrics,
            models=models,
            symptom_entity_id=symptom_entity_id,
            symptom_metric=symptom_metric,
            gibbs_iterations=self.gibbs_iterations,
            fixed_entity_id=fixed_entity_id,
        )

    def _list_metrics(self, entity_id: str, incident_time: datetime) -> list[str]:
        if hasattr(self.store, "list_metric_names"):
            return self.store.list_metric_names(entity_id, incident_time)  # type: ignore[attr-defined]
        current = self.store.get_current_metrics(entity_id, incident_time)
        return list(current.keys())

    @staticmethod
    def _align_to_timestamps(
        samples: list,
        timestamps: list[datetime],
    ) -> list[float]:
        ts_to_val = {s.timestamp: s.value for s in samples}
        aligned: list[float] = []
        col_mean = float(np.mean([s.value for s in samples])) if samples else 0.0
        for ts in timestamps:
            aligned.append(ts_to_val.get(ts, col_mean))
        return aligned
