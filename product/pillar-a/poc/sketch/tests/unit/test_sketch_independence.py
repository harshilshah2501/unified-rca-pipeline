from ab_shared.clock import FrozenClock
from ab_shared.dest import MemoryDest
from ab_shared.season import HourOfWeekSeason
from datetime import datetime, timezone


def test_sketch_depends_only_on_shared_stubs():
    clock = FrozenClock(datetime(2026, 8, 20, 3, 30, tzinfo=timezone.utc))
    season = HourOfWeekSeason()
    dest = MemoryDest()
    assert season.season_key(clock.now()) == "Thu-03:00"
    dest.put("history", "probe", b"ok")
    assert dest.get("history", "probe") == b"ok"
