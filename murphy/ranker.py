"""Root cause ranking by anomaly score."""

from __future__ import annotations

from murphy.types import RootCause

_STD_FLOOR = 1e-9


class RootCauseRanker:
    """
    Rank root cause entities by anomaly score.
    Score = max over metrics of |current - mean| / std.
    """

    def compute_anomaly_score(
        self,
        entity_id: str,
        current_metrics: dict[str, float],
        historical_stats: dict[str, tuple[float, float]],
    ) -> float:
        max_score = 0.0
        for metric_name, value in current_metrics.items():
            if metric_name not in historical_stats:
                continue
            mean, std = historical_stats[metric_name]
            std = max(std, _STD_FLOOR)
            score = abs(value - mean) / std
            max_score = max(max_score, score)
        return max_score

    def rank(self, root_causes: list[RootCause]) -> list[RootCause]:
        return sorted(root_causes, key=lambda rc: rc.anomaly_score, reverse=True)
