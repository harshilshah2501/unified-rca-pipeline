"""Information-gain scoring for candidate CIs."""

from __future__ import annotations

from datetime import datetime


def score_candidate(
    ci: str,
    crossed: list[dict],
    onset_times: dict[str, datetime],
    decisive_signals: set[str],
) -> float:
    """
    Higher score = more informative upstream candidate.
    Factors: earliest onset, decisive signal presence, anomaly severity.
    """
    score = 0.0
    ci_anomalies = [a for a in crossed if a["ci"] == ci]
    if not ci_anomalies:
        # Onset-based anomaly scores can be negative.  A CI with no crossed
        # evidence must remain behind observed anomalies in the frontier.
        return -1_000_000_000_000.0
    if ci in onset_times:
        # Earlier onset → higher score (invert timestamp to seconds)
        score += 1000.0 - onset_times[ci].timestamp() % 1e6
    for a in ci_anomalies:
        if a["signal"] in decisive_signals:
            score += 50.0
        if a.get("crossed"):
            ratio = a["value"] / max(a["threshold"], 1e-9)
            score += min(ratio, 10.0) * 5.0
    return score
