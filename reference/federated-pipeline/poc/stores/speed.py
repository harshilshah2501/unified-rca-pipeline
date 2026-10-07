"""Speed-tier event store — Redis/Dragonfly-backed Nezha keys (tg:/pc:)."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any


LUA_INGEST = """
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[1])
local cur = redis.call('HGET', KEYS[2], ARGV[3])
if not cur then cur = 0 end
redis.call('HSET', KEYS[2], ARGV[3], tonumber(cur) + 1)
return 1
"""


@dataclass
class SpeedEvent:
    tenant: str
    trace_id: str
    span_id: str
    service: str
    event_type: str
    timestamp: float
    phase: str = "fault-suffering"  # or fault-free

    @property
    def pattern(self) -> str:
        return f"{self.service}→{self.event_type}"

    @property
    def pattern_shard(self) -> int:
        return int(hashlib.md5(self.pattern.encode()).hexdigest(), 16) % 256


class SpeedStore:
    """Writes Nezha-shaped events into tg: ZSETs and pc: HSETs."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379) -> None:
        import redis

        self.client = redis.Redis(host=host, port=port, decode_responses=False)
        self.client.ping()
        self._sha = self.client.script_load(LUA_INGEST)
        self.written = 0

    def write_event(self, event: SpeedEvent) -> None:
        minute = int(event.timestamp // 60)
        tg = f"tg:{event.tenant}:{event.trace_id}:{minute}"
        pc = f"pc:{event.phase}:{event.tenant}:{event.pattern_shard}"
        member = f"{event.span_id}:{event.service}:{event.event_type}".encode()
        self.client.evalsha(
            self._sha,
            2,
            tg,
            pc,
            member,
            float(event.timestamp),
            event.pattern,
        )
        self.written += 1

    def write_batch(self, events: list[SpeedEvent]) -> None:
        pipe = self.client.pipeline(transaction=False)
        for event in events:
            minute = int(event.timestamp // 60)
            tg = f"tg:{event.tenant}:{event.trace_id}:{minute}"
            pc = f"pc:{event.phase}:{event.tenant}:{event.pattern_shard}"
            member = f"{event.span_id}:{event.service}:{event.event_type}".encode()
            pipe.evalsha(
                self._sha,
                2,
                tg,
                pc,
                member,
                float(event.timestamp),
                event.pattern,
            )
        pipe.execute()
        self.written += len(events)

    def pattern_counts(self, tenant: str, phase: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for shard in range(256):
            key = f"pc:{phase}:{tenant}:{shard}"
            raw = self.client.hgetall(key)
            for pattern, value in raw.items():
                p = pattern.decode() if isinstance(pattern, bytes) else pattern
                counts[p] = counts.get(p, 0) + int(value)
        return counts

    def summary(self) -> dict[str, Any]:
        return {"written": self.written, "backend": "redis-compatible"}
