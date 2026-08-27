from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Timezone-aware UTC now."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FrozenClock:
    def __init__(self, when: datetime) -> None:
        if when.tzinfo is None:
            raise ValueError("FrozenClock requires a timezone-aware datetime")
        self._when = when.astimezone(timezone.utc)

    def now(self) -> datetime:
        return self._when
