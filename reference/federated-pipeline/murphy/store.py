"""MetricStore interface and dict-backed storage for synthetic data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np

from murphy.types import Entity, MetricSample

_STD_FLOOR = 1e-9


class MetricStore(ABC):
    """
    Abstract interface over the monitoring database.

    Concrete implementations: SimulatedMetricStore (synthetic generator),
    CsvMetricStore (DeathStarBench CSV/Parquet traces).
    """

    @abstractmethod
    def get_historical_metrics(
        self,
        entity_id: str,
        metric_name: str,
        end_time: datetime,
        lookback_days: int = 7,
    ) -> list[MetricSample]:
        """Return metric samples prior to end_time within lookback window."""

    @abstractmethod
    def get_current_metrics(
        self,
        entity_id: str,
        incident_time: datetime,
    ) -> dict[str, float]:
        """Return all current metric values for entity at incident_time."""

    @abstractmethod
    def get_entity_metadata(self, app_id: str) -> list[Entity]:
        """Return all entities belonging to app_id."""

    def get_entity(self, entity_id: str) -> Entity | None:
        """Optional helper: lookup a single entity by id."""
        return None

    def compute_historical_stats(
        self,
        entity_id: str,
        end_time: datetime,
        lookback_days: int = 7,
    ) -> dict[str, tuple[float, float]]:
        """Compute mean and std per metric for an entity over the lookback window."""
        raise NotImplementedError

    def list_metric_names(
        self,
        entity_id: str,
        end_time: datetime,
        lookback_days: int = 7,
    ) -> list[str]:
        """Return metric names with historical data for an entity."""
        raise NotImplementedError


class DictMetricStore(MetricStore):
    """Dict-backed MetricStore holding pre-generated or loaded samples."""

    def __init__(
        self,
        entities: list[Entity] | None = None,
        samples: list[MetricSample] | None = None,
    ) -> None:
        self._entities: dict[str, Entity] = {}
        self._samples: list[MetricSample] = []
        if entities:
            for entity in entities:
                self._entities[entity.id] = entity
        if samples:
            self._samples.extend(samples)

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.id] = entity

    def add_sample(self, sample: MetricSample) -> None:
        self._samples.append(sample)

    def add_samples(self, samples: list[MetricSample]) -> None:
        self._samples.extend(samples)

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def get_entity_metadata(self, app_id: str) -> list[Entity]:
        return [e for e in self._entities.values() if e.app_id == app_id]

    def get_historical_metrics(
        self,
        entity_id: str,
        metric_name: str,
        end_time: datetime,
        lookback_days: int = 7,
    ) -> list[MetricSample]:
        start_time = end_time - timedelta(days=lookback_days)
        result = [
            s
            for s in self._samples
            if s.entity_id == entity_id
            and s.metric_name == metric_name
            and start_time <= s.timestamp < end_time
        ]
        return sorted(result, key=lambda s: s.timestamp)

    def get_current_metrics(
        self,
        entity_id: str,
        incident_time: datetime,
    ) -> dict[str, float]:
        by_metric: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        for s in self._samples:
            if s.entity_id == entity_id and s.timestamp <= incident_time:
                by_metric[s.metric_name].append((s.timestamp, s.value))

        current: dict[str, float] = {}
        for metric_name, points in by_metric.items():
            points.sort(key=lambda p: p[0])
            current[metric_name] = points[-1][1]
        return current

    def compute_historical_stats(
        self,
        entity_id: str,
        end_time: datetime,
        lookback_days: int = 7,
    ) -> dict[str, tuple[float, float]]:
        start_time = end_time - timedelta(days=lookback_days)
        by_metric: dict[str, list[float]] = defaultdict(list)
        for s in self._samples:
            if (
                s.entity_id == entity_id
                and start_time <= s.timestamp < end_time
            ):
                by_metric[s.metric_name].append(s.value)

        stats: dict[str, tuple[float, float]] = {}
        for metric_name, values in by_metric.items():
            arr = np.array(values, dtype=float)
            std = float(np.std(arr))
            stats[metric_name] = (float(np.mean(arr)), max(std, _STD_FLOOR))
        return stats

    def list_metric_names(
        self,
        entity_id: str,
        end_time: datetime,
        lookback_days: int = 7,
    ) -> list[str]:
        start_time = end_time - timedelta(days=lookback_days)
        names: set[str] = set()
        for s in self._samples:
            if (
                s.entity_id == entity_id
                and start_time <= s.timestamp < end_time
            ):
                names.add(s.metric_name)
        return sorted(names)


# Backward-compatible alias used by unit tests
InMemoryMetricStore = DictMetricStore
