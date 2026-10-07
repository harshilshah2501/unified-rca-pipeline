"""Temporal onset ranking."""

from __future__ import annotations

from datetime import datetime


def parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def rank_by_onset(crossed: list[dict]) -> list[dict]:
    """Return crossed anomalies sorted by timestamp ascending."""
    return sorted(crossed, key=lambda a: parse_ts(a["timestamp"]))


def onset_by_ci(crossed: list[dict]) -> dict[str, datetime]:
    """Earliest crossed timestamp per CI."""
    out: dict[str, datetime] = {}
    for a in crossed:
        ts = parse_ts(a["timestamp"])
        ci = a["ci"]
        if ci not in out or ts < out[ci]:
            out[ci] = ts
    return out


def delta_t_ambiguous(
    onset_times: dict[str, datetime],
    candidates: list[str],
    window_seconds: float = 10.0,
) -> bool:
    """True when ≥2 candidates have onset within window (CARE trigger)."""
    if len(candidates) < 2:
        return False
    times = sorted(onset_times[c] for c in candidates if c in onset_times)
    if len(times) < 2:
        return False
    return (times[1] - times[0]).total_seconds() <= window_seconds
