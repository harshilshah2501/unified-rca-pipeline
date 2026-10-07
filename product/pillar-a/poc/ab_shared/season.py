from __future__ import annotations

from datetime import datetime
from typing import Protocol


class SeasonPolicy(Protocol):
    def season_key(self, ts: datetime) -> str:
        """Calendar slot for seasonal baseline, e.g. Thu-09:00."""


class HourOfWeekSeason:
    """Hour-of-week in the timestamp's timezone (tests use UTC)."""

    def season_key(self, ts: datetime) -> str:
        if ts.tzinfo is None:
            raise ValueError("season_key requires a timezone-aware datetime")
        return f"{ts.strftime('%a')}-{ts.hour:02d}:00"
