from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class SeasonalBaseline:
    """Accumulate window percentiles per season_key; expected = mean of history."""

    history: dict[str, list[tuple[float, float, float]]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def observe(self, season_key: str, p50: float, p95: float, p99: float) -> None:
        self.history[season_key].append((p50, p95, p99))

    def expected(self, season_key: str) -> dict:
        rows = self.history.get(season_key) or []
        if not rows:
            return {
                "baseline_version": "seasonal_v1",
                "expected_p50": 0.0,
                "expected_p95": 0.0,
                "expected_p99": 0.0,
            }
        n = len(rows)
        return {
            "baseline_version": "seasonal_v1",
            "expected_p50": sum(r[0] for r in rows) / n,
            "expected_p95": sum(r[1] for r in rows) / n,
            "expected_p99": sum(r[2] for r in rows) / n,
        }
