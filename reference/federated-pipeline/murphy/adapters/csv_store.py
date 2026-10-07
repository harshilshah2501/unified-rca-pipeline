"""
CsvMetricStore — load metric traces from DeathStarBench CSV/Parquet files.

DeathStarBench: https://github.com/delimitrou/DeathStarBench

Expected file layout (to be aligned with exported trace format):

    data_dir/
      entities.csv          # id, entity_type, app_id, metadata_json
      metrics/
        {entity_id}_{metric_name}.csv   # timestamp, value

Or a single long-format file:

    metrics.csv           # entity_id, metric_name, timestamp, value

Use this store to validate Murphy against the paper's reported ~86% top-1
accuracy on DeathStarBench once traces are exported to the schema above.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from murphy.store import DictMetricStore, MetricStore
from murphy.types import Entity, MetricSample


class CsvMetricStore(DictMetricStore):
    """Load real traces from DeathStarBench CSV/Parquet exports."""

    def __init__(self, data_dir: str | Path) -> None:
        super().__init__()
        self.data_dir = Path(data_dir)

    @classmethod
    def from_deathstarbench(cls, data_dir: str | Path) -> CsvMetricStore:
        """Load DeathStarBench trace directory. Raises until export format is wired."""
        store = cls(data_dir)
        store._load()
        return store

    def _load(self) -> None:
        entities_file = self.data_dir / "entities.csv"
        metrics_file = self.data_dir / "metrics.csv"

        if not self.data_dir.exists():
            raise FileNotFoundError(
                f"CsvMetricStore: data directory not found: {self.data_dir}"
            )

        if entities_file.exists() and metrics_file.exists():
            raise NotImplementedError(
                "CsvMetricStore: parsing entities.csv and metrics.csv is not yet "
                "implemented. Export DeathStarBench traces to the documented schema "
                "and implement _load_entities() / _load_metrics()."
            )

        raise NotImplementedError(
            "CsvMetricStore: no recognized trace files in "
            f"{self.data_dir}. Expected entities.csv and metrics.csv. "
            "See adapters/csv_store.py module docstring for the expected layout."
        )

    def load_entities(self, entities: list[Entity]) -> None:
        """Manually register entities when loading custom CSV layouts."""
        for entity in entities:
            self.add_entity(entity)

    def load_samples(self, samples: list[MetricSample]) -> None:
        """Manually load parsed metric samples."""
        self.add_samples(samples)
