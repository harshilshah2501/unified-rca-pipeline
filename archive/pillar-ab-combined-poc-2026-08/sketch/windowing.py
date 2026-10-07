from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ab_shared.season import HourOfWeekSeason, SeasonPolicy

WINDOWS = ("1m", "5m")


def _parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def window_start(ts: datetime, window: str) -> datetime:
    if window == "1m":
        return ts.replace(second=0, microsecond=0)
    if window == "5m":
        minute = (ts.minute // 5) * 5
        return ts.replace(minute=minute, second=0, microsecond=0)
    if window == "1h":
        return ts.replace(minute=0, second=0, microsecond=0)
    if window == "1d":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(window)


def window_end(start: datetime, window: str) -> datetime:
    deltas = {"1m": timedelta(minutes=1), "5m": timedelta(minutes=5), "1h": timedelta(hours=1), "1d": timedelta(days=1)}
    return start + deltas[window]


def assignments(
    ts: str,
    *,
    windows: tuple[str, ...] = WINDOWS,
    season: SeasonPolicy | None = None,
) -> list[dict]:
    season = season or HourOfWeekSeason()
    dt = _parse_ts(ts)
    out = []
    for w in windows:
        start = window_start(dt, w)
        out.append(
            {
                "window": w,
                "window_start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "window_end": window_end(start, w).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "season_key": season.season_key(start),
            }
        )
    return out
