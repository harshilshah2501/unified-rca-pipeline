"""PoC snowflake-style UInt64 ids for Motadata-aligned edge / evidence fields.

Not a distributed ID service — timestamp-ms << 22 | (seq & 0x3fffff) with an
injectable clock and sequence for deterministic tests.
"""

from __future__ import annotations

import time
from typing import Callable

Clock = Callable[[], int]

_seq = 0
_clock: Clock | None = None


def reset_snowflake(*, clock: Clock | None = None, seq: int = 0) -> None:
    """Test helper: reset sequence and optional clock (returns unix ms)."""
    global _seq, _clock
    _seq = seq
    _clock = clock


def next_snowflake(*, ts_ms: int | None = None) -> int:
    """Allocate the next snowflake id."""
    global _seq
    if ts_ms is None:
        if _clock is not None:
            ts_ms = int(_clock())
        else:
            ts_ms = int(time.time() * 1000)
    _seq = (_seq + 1) & 0x3FFFFF
    return ((ts_ms & 0x1FFFFFFFFFF) << 22) | _seq


def snowflake_from_parts(ts_ms: int, seq: int) -> int:
    """Deterministic id for fixtures (no global state)."""
    return ((ts_ms & 0x1FFFFFFFFFF) << 22) | (seq & 0x3FFFFF)
