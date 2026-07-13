"""CARE conditional fallback — Tier 2 when Δt ambiguity (PRD §2.5)."""

from __future__ import annotations

from core_engine.lean.temporal import delta_t_ambiguous, onset_by_ci


def care_fallback_candidates(
    crossed: list[dict],
    candidates: list[str],
    window_seconds: float = 10.0,
) -> list[str] | None:
    """
    When temporal ambiguity exists, return candidates for CARE spectrum ranking.
    PoC: rank by anomaly severity sum on decisive signals.
    """
    onset = onset_by_ci(crossed)
    ambiguous_set = [c for c in candidates if c in onset]
    if not delta_t_ambiguous(onset, ambiguous_set, window_seconds):
        return None
    # Rank by total severity
    scores: list[tuple[str, float]] = []
    for ci in ambiguous_set:
        total = sum(
            a["value"] / max(a["threshold"], 1e-9)
            for a in crossed
            if a["ci"] == ci and a.get("crossed")
        )
        scores.append((ci, total))
    scores.sort(key=lambda x: x[1], reverse=True)
    return [ci for ci, _ in scores]
