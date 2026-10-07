"""SimulatedMetricStore — synthetic time-series with fault injection and causal propagation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import numpy as np

from murphy.store import DictMetricStore
from murphy.types import Entity, MetricSample

FaultType = Literal["spike", "step", "drift"]


@dataclass
class MetricBaseline:
    """Stable baseline parameters for a single entity metric."""

    mean: float
    std: float = 0.0
    noise_std: float | None = None

    @property
    def effective_noise(self) -> float:
        return self.noise_std if self.noise_std is not None else max(self.std, 1e-6)


@dataclass
class CausalRule:
    """Linear causal influence: dst = intercept + coef * src + noise."""

    src_entity: str
    src_metric: str
    dst_entity: str
    dst_metric: str
    coefficient: float
    intercept: float = 0.0


@dataclass
class FaultSpec:
    """Fault injected at incident_time on a specific entity metric."""

    entity_id: str
    metric_name: str
    fault_type: FaultType = "spike"
    multiplier: float = 8.0
    drift_rate: float = 0.0


class SimulatedMetricStore(DictMetricStore):
    """
    Primary MetricStore for development and testing.

    Generates synthetic metric time-series with:
    - Normal entities: Gaussian noise around a stable mean
    - Faulty entities: spike/step/drift anomaly at incident_time
    - Causal propagation: upstream metrics influence downstream via linear rules
    """

    def __init__(self, seed: int = 42) -> None:
        super().__init__()
        self._rng = np.random.default_rng(seed)
        self._baselines: dict[str, dict[str, MetricBaseline]] = {}
        self._causal_rules: list[CausalRule] = []
        self._faults: list[FaultSpec] = []
        self._generation_order: list[str] = []

    def define_metric(
        self,
        entity_id: str,
        metric_name: str,
        mean: float,
        std: float = 0.0,
        noise_std: float | None = None,
    ) -> None:
        self._baselines.setdefault(entity_id, {})[metric_name] = MetricBaseline(
            mean=mean, std=std, noise_std=noise_std
        )

    def add_causal_rule(
        self,
        src_entity: str,
        src_metric: str,
        dst_entity: str,
        dst_metric: str,
        coefficient: float,
        intercept: float = 0.0,
    ) -> None:
        self._causal_rules.append(
            CausalRule(
                src_entity=src_entity,
                src_metric=src_metric,
                dst_entity=dst_entity,
                dst_metric=dst_metric,
                coefficient=coefficient,
                intercept=intercept,
            )
        )
        if dst_entity not in self._generation_order:
            self._generation_order.append(dst_entity)

    def inject_fault(
        self,
        entity_id: str,
        metric_name: str,
        fault_type: FaultType = "spike",
        multiplier: float = 8.0,
        drift_rate: float = 0.0,
    ) -> None:
        self._faults.append(
            FaultSpec(
                entity_id=entity_id,
                metric_name=metric_name,
                fault_type=fault_type,
                multiplier=multiplier,
                drift_rate=drift_rate,
            )
        )

    def simulate(
        self,
        incident_time: datetime,
        lookback_days: int = 7,
        interval_minutes: int = 30,
        n_slices: int | None = None,
    ) -> None:
        """
        Generate time-series from baselines and causal rules.

        Historical samples are strictly before incident_time.
        One incident snapshot is written at incident_time with faults applied.
        """
        if n_slices is None:
            n_slices = int(lookback_days * 24 * 60 / interval_minutes)

        interval = timedelta(minutes=interval_minutes)
        start = incident_time - n_slices * interval

        for i in range(n_slices):
            ts = start + i * interval
            if ts >= incident_time:
                break
            values = self._sample_timestep(is_incident=False)
            self._emit_samples(ts, values)

        incident_values = self._sample_timestep(is_incident=True)
        self._apply_faults(incident_values)
        self._propagate_causal(incident_values)
        self._emit_samples(incident_time, incident_values)

    def _sample_timestep(self, is_incident: bool) -> dict[str, dict[str, float]]:
        values: dict[str, dict[str, float]] = {}

        for entity_id, metrics in self._baselines.items():
            values[entity_id] = {}
            for metric_name, baseline in metrics.items():
                noise = self._rng.normal(0, baseline.effective_noise)
                values[entity_id][metric_name] = baseline.mean + noise

        self._propagate_causal(values)
        return values

    def _propagate_causal(self, values: dict[str, dict[str, float]]) -> None:
        for rule in self._causal_rules:
            src_val = values.get(rule.src_entity, {}).get(rule.src_metric)
            if src_val is None:
                continue
            dst_metrics = values.setdefault(rule.dst_entity, {})
            propagated = rule.intercept + rule.coefficient * src_val
            if rule.dst_metric in self._baselines.get(rule.dst_entity, {}):
                noise = self._rng.normal(
                    0,
                    self._baselines[rule.dst_entity][rule.dst_metric].effective_noise,
                )
                propagated += noise
            dst_metrics[rule.dst_metric] = propagated

    def _apply_faults(self, values: dict[str, dict[str, float]]) -> None:
        for fault in self._faults:
            entity_metrics = values.setdefault(fault.entity_id, {})
            baseline = self._baselines.get(fault.entity_id, {}).get(fault.metric_name)
            base_mean = baseline.mean if baseline else 1.0

            current = entity_metrics.get(fault.metric_name, base_mean)
            if fault.fault_type == "spike":
                entity_metrics[fault.metric_name] = current * fault.multiplier
            elif fault.fault_type == "step":
                entity_metrics[fault.metric_name] = base_mean * fault.multiplier
            elif fault.fault_type == "drift":
                entity_metrics[fault.metric_name] = current + fault.drift_rate

    def _emit_samples(
        self,
        timestamp: datetime,
        values: dict[str, dict[str, float]],
    ) -> None:
        for entity_id, metrics in values.items():
            for metric_name, value in metrics.items():
                self.add_sample(
                    MetricSample(entity_id, metric_name, timestamp, float(value))
                )

    @classmethod
    def build_figure1_topology(cls, app_id: str = "web_app") -> list[Entity]:
        """Paper Figure 1 topology with infrastructure entities for cyclic dependencies."""
        return [
            Entity(
                id="crawler_vm",
                entity_type="vm",
                app_id=app_id,
                metadata={
                    "display_name": "Crawler machine",
                    "neighbors": ["frontend_ms", "host_crawler", "nic_crawler"],
                    "host_id": "host_crawler",
                    "nic_ids": ["nic_crawler"],
                },
            ),
            Entity(
                id="frontend_ms",
                entity_type="microservice",
                app_id=app_id,
                metadata={
                    "display_name": "front-end",
                    "neighbors": ["crawler_vm", "backend_vm_1"],
                    "upstream": ["crawler_vm"],
                    "downstream": ["backend_vm_1"],
                },
            ),
            Entity(
                id="backend_vm_1",
                entity_type="vm",
                app_id=app_id,
                metadata={
                    "display_name": "back-end",
                    "neighbors": ["frontend_ms", "host_backend", "nic_backend"],
                    "host_id": "host_backend",
                    "nic_ids": ["nic_backend"],
                },
            ),
            Entity(
                id="normal_vm",
                entity_type="vm",
                app_id=app_id,
                metadata={
                    "display_name": "idle worker",
                    "neighbors": ["frontend_ms"],
                },
            ),
            Entity(
                id="host_crawler",
                entity_type="host",
                app_id=app_id,
                metadata={"display_name": "Crawler host", "tor_switch_id": "tor_switch_1"},
            ),
            Entity(
                id="host_backend",
                entity_type="host",
                app_id=app_id,
                metadata={"display_name": "Backend host", "tor_switch_id": "tor_switch_1"},
            ),
            Entity(
                id="nic_crawler",
                entity_type="nic",
                app_id=app_id,
                metadata={"display_name": "Crawler vNIC", "vm_id": "crawler_vm"},
            ),
            Entity(
                id="nic_backend",
                entity_type="nic",
                app_id=app_id,
                metadata={"display_name": "Backend vNIC", "vm_id": "backend_vm_1"},
            ),
            Entity(
                id="tor_switch_1",
                entity_type="router",
                app_id=app_id,
                metadata={"display_name": "ToR Switch"},
            ),
        ]
