"""Phase 0 — single-node event-path throughput probe.

Measures sustained write+score ops against Redis-compatible storage
(Dragonfly preferred; Redis acceptable for a lower bound).

Usage:
  docker run -d --name df -p 6380:6379 \\
    docker.dragonflydb.io/dragonflydb/dragonfly --proactor_threads=2
  python -m poc.benchmarks.phase0_dragonfly --port 6380 --workers 4 --seconds 15
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass


LUA_SCORE = """
-- KEYS[1]=tg ZSET, KEYS[2]=pc HSET, ARGV[1]=member, ARGV[2]=score, ARGV[3]=pattern, ARGV[4]=count
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[1])
local cur = redis.call('HGET', KEYS[2], ARGV[3])
if not cur then cur = 0 end
redis.call('HSET', KEYS[2], ARGV[3], tonumber(cur) + tonumber(ARGV[4]))
return redis.call('HGET', KEYS[2], ARGV[3])
"""


@dataclass
class BenchmarkResult:
    backend: str
    host: str
    port: int
    seconds: float
    events: int
    eps: float
    event_bytes: int
    p99_latency_ms: float
    workers: int
    pipeline_size: int
    thread_count: int | None
    cpu_count: int
    hardware: str
    notes: str


def _detect_backend(info: dict) -> tuple[str, int | None]:
    df_ver = info.get("dragonfly_version")
    threads = info.get("thread_count")
    if threads is not None:
        try:
            threads = int(threads)
        except (TypeError, ValueError):
            threads = None
    if df_ver or "dragonfly" in str(info.get("redis_version", "")).lower():
        return f"dragonfly/{df_ver or info.get('redis_version')}", threads
    return f"redis/{info.get('redis_version', 'unknown')}", threads


def _worker_loop(
    worker_id: int,
    host: str,
    port: int,
    seconds: float,
    event_bytes: int,
    pipeline_size: int,
    sha: str,
) -> tuple[int, list[float]]:
    import redis

    client = redis.Redis(host=host, port=port, decode_responses=False)
    latencies: list[float] = []
    events = 0
    deadline = time.perf_counter() + seconds
    tenant = f"bench{worker_id}"
    phase = "fault-suffering"
    base = worker_id * 10_000_000

    while time.perf_counter() < deadline:
        pipe = client.pipeline(transaction=False)
        batch_t0 = time.perf_counter()
        for i in range(pipeline_size):
            seq = base + events + i
            trace_id = f"t{seq}"
            pattern = f"svcA→svcB_{seq % 1024}"
            pattern_hash = int(hashlib.md5(pattern.encode()).hexdigest(), 16) % 256
            minute = int(time.time() // 60)
            tg = f"tg:{tenant}:{trace_id}:{minute}"
            pc = f"pc:{phase}:{tenant}:{pattern_hash}"
            member = f"{trace_id}:{i}".encode()
            if len(member) < event_bytes:
                member = member + b"x" * (event_bytes - len(member))
            pipe.evalsha(sha, 2, tg, pc, member, float(seq), pattern, 1)
        pipe.execute()
        batch_ms = (time.perf_counter() - batch_t0) * 1000.0 / pipeline_size
        latencies.extend([batch_ms] * pipeline_size)
        events += pipeline_size

    return events, latencies


def run_benchmark(
    host: str,
    port: int,
    seconds: float,
    event_bytes: int = 200,
    pipeline_size: int = 64,
    workers: int = 1,
) -> BenchmarkResult:
    try:
        import redis
    except ImportError as exc:
        raise SystemExit(
            "Install redis-py: pip install redis\n"
            f"Original error: {exc}"
        ) from exc

    client = redis.Redis(host=host, port=port, decode_responses=False)
    client.ping()
    info = client.info("server")
    backend_name, thread_count = _detect_backend(info)
    sha = client.script_load(LUA_SCORE)

    workers = max(1, workers)
    all_latencies: list[float] = []
    total_events = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _worker_loop,
                wid,
                host,
                port,
                seconds,
                event_bytes,
                pipeline_size,
                sha,
            )
            for wid in range(workers)
        ]
        for fut in as_completed(futures):
            events, latencies = fut.result()
            total_events += events
            all_latencies.extend(latencies)

    elapsed = max(seconds, 1e-9)
    all_latencies.sort()
    p99 = all_latencies[int(len(all_latencies) * 0.99)] if all_latencies else 0.0
    cpu_count = os.cpu_count() or 1
    hardware = platform.processor() or platform.machine()

    return BenchmarkResult(
        backend=backend_name,
        host=host,
        port=port,
        seconds=seconds,
        events=total_events,
        eps=total_events / elapsed,
        event_bytes=event_bytes,
        p99_latency_ms=round(p99, 3),
        workers=workers,
        pipeline_size=pipeline_size,
        thread_count=thread_count,
        cpu_count=cpu_count,
        hardware=hardware,
        notes=(
            "Lua ZADD+HSET path approximating Nezha pattern write/score; "
            f"{workers} concurrent client workers"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 0 Dragonfly/Redis EPS probe")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--event-bytes", type=int, default=200)
    parser.add_argument("--pipeline-size", type=int, default=64)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(2, os.cpu_count() or 2),
        help="Concurrent client workers (default: CPU count)",
    )
    parser.add_argument("--output", help="Write JSON result path")
    args = parser.parse_args(argv)

    result = run_benchmark(
        host=args.host,
        port=args.port,
        seconds=args.seconds,
        event_bytes=args.event_bytes,
        pipeline_size=args.pipeline_size,
        workers=args.workers,
    )
    payload = json.dumps(asdict(result), indent=2)
    print(payload)
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
