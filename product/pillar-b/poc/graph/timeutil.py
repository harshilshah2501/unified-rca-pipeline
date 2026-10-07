"""Time helpers — Unix epoch milliseconds UTC for graph_node / graph_edge clocks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_epoch_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def to_epoch_ms(value: Any) -> int:
    """Accept int/float epoch ms, or ISO-8601 string (legacy fixtures / CLI ``as_of``)."""
    if value is None:
        return now_epoch_ms()
    if isinstance(value, bool):
        raise TypeError("bool is not a timestamp")
    if isinstance(value, (int, float)):
        return int(value)
    ts = str(value).strip()
    if ts.endswith("Z"):
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def epoch_ms_to_datetime(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
