"""Explanation generator — state machine and causal chain text."""

from __future__ import annotations

from murphy.graph import RelationshipGraph
from murphy.types import Entity, ExplanationStep, RootCause, Symptom

_STD_FLOOR = 1e-9

_STATE_LABELS = {
    "heavy_hitter": "heavy hitter",
    "degraded_performance": "degraded performance",
    "high_drop_rate": "high drop rate",
    "nonfunctional": "nonfunctional",
}

_EDGE_LABELS: dict[tuple[str, str], str] = {
    ("heavy_hitter", "degraded_performance"): "sent high load to",
    ("heavy_hitter", "heavy_hitter"): "sent high requests to",
    ("degraded_performance", "degraded_performance"): "propagated load to",
    ("degraded_performance", "high_drop_rate"): "caused elevated drop rate at",
    ("high_drop_rate", "nonfunctional"): "caused failure at",
    ("degraded_performance", "heavy_hitter"): "increased load at",
}


class ExplanationGenerator:
    """State machine-based causal chain explanation from paper §4.3."""

    STATE_THRESHOLDS: dict[str, dict[str, float]] = {
        "cpu_usage": {"heavy_hitter": 0.8, "degraded": 0.6},
        "latency_p90": {"degraded": 2.0},
        "drop_rate": {"high_drop": 0.05},
        "session_count": {"heavy_hitter": 2.0},
        "throughput": {"heavy_hitter": 2.0},
    }

    def classify_state(
        self,
        entity_id: str,
        current_metrics: dict[str, float],
        historical_stats: dict[str, tuple[float, float]],
    ) -> str:
        """Classify entity into one of 4 states using threshold-based labeling."""
        states: list[str] = []

        drop_rate = current_metrics.get("drop_rate")
        if drop_rate is not None:
            threshold = self.STATE_THRESHOLDS["drop_rate"]["high_drop"]
            if drop_rate >= threshold:
                states.append("high_drop_rate")

        availability = current_metrics.get("availability")
        if availability is not None and availability < 0.01:
            states.append("nonfunctional")

        for metric_name, thresholds in self.STATE_THRESHOLDS.items():
            if metric_name == "drop_rate":
                continue
            value = current_metrics.get(metric_name)
            if value is None or metric_name not in historical_stats:
                continue
            mean, std = historical_stats[metric_name]
            std = max(std, _STD_FLOOR)

            if "heavy_hitter" in thresholds:
                hh = thresholds["heavy_hitter"]
                if metric_name in ("session_count", "throughput"):
                    if value >= mean * hh:
                        states.append("heavy_hitter")
                elif value >= hh:
                    states.append("heavy_hitter")

            if "degraded" in thresholds:
                deg = thresholds["degraded"]
                if metric_name == "latency_p90":
                    if value >= mean * deg:
                        states.append("degraded_performance")
                elif value >= deg:
                    states.append("degraded_performance")

        if "nonfunctional" in states:
            return "nonfunctional"
        if "high_drop_rate" in states:
            return "high_drop_rate"
        if "degraded_performance" in states:
            return "degraded_performance"
        if "heavy_hitter" in states:
            return "heavy_hitter"
        return "degraded_performance"

    def generate_chain(
        self,
        root_cause: RootCause,
        symptom: Symptom,
        graph: RelationshipGraph,
        current_metrics: dict[str, dict[str, float]],
        historical_stats: dict[str, dict[str, tuple[float, float]]],
    ) -> list[ExplanationStep]:
        """Walk shortest path from root cause to symptom entity."""
        path = graph.shortest_path_hops(root_cause.entity_id, symptom.entity_id)
        if len(path) < 2:
            return []

        steps: list[ExplanationStep] = []
        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]
            from_state = self.classify_state(
                from_id,
                current_metrics.get(from_id, {}),
                historical_stats.get(from_id, {}),
            )
            to_state = self.classify_state(
                to_id,
                current_metrics.get(to_id, {}),
                historical_stats.get(to_id, {}),
            )
            edge_label = _EDGE_LABELS.get(
                (from_state, to_state),
                "affected",
            )
            steps.append(
                ExplanationStep(
                    from_entity=from_id,
                    to_entity=to_id,
                    from_state=from_state,
                    to_state=to_state,
                    edge_label=edge_label,
                )
            )
        return steps

    def format_text(
        self,
        chain: list[ExplanationStep],
        entities: dict[str, Entity],
    ) -> str:
        """Render chain as human-readable text for SRE consumption."""
        if not chain:
            return ""

        def display_name(entity_id: str) -> str:
            entity = entities.get(entity_id)
            if entity and entity.metadata.get("display_name"):
                return f"{entity_id} ({entity.metadata['display_name']})"
            return entity_id

        sentences: list[str] = []
        for step in chain:
            from_name = display_name(step.from_entity)
            to_name = display_name(step.to_entity)
            from_label = _STATE_LABELS.get(step.from_state, step.from_state)
            to_label = _STATE_LABELS.get(step.to_state, step.to_state)
            sentences.append(
                f"Entity {from_name} ({from_label}) {step.edge_label} "
                f"Entity {to_name} ({to_label})."
            )

        last = chain[-1]
        last_name = display_name(last.to_entity)
        last_label = _STATE_LABELS.get(last.to_state, last.to_state)
        sentences.append(
            f"Entity {last_name} faced {last_label}."
        )
        return " ".join(sentences)
