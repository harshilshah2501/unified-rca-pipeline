#!/usr/bin/env python3
"""Optional Federated N4 metric_slice read smoke (+ optional Dragonfly load)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ingestion-poc" / "builders"))
sys.path.insert(0, str(REPO / "federated-pipeline"))

from federated_store_writer import write_federated_stores  # noqa: E402


def read_metric_slice(path: Path) -> dict[str, Any]:
    """Scan metric_slice.jsonl — stand-in for Federated store query."""
    t0 = time.perf_counter()
    by_entity: dict[str, int] = defaultdict(int)
    by_metric: dict[str, int] = defaultdict(int)
    rows = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows += 1
            by_entity[str(row.get("entity_id") or "?")] += 1
            by_metric[str(row.get("metric_name") or "?")] += 1
    elapsed = time.perf_counter() - t0
    top_entities = sorted(by_entity.items(), key=lambda x: -x[1])[:10]
    return {
        "rows": rows,
        "entities": len(by_entity),
        "metrics": len(by_metric),
        "top_entities": top_entities,
        "elapsed_s": round(elapsed, 4),
        "rows_per_s": round(rows / elapsed, 2) if elapsed > 0 else 0.0,
        "path": str(path),
    }


LUA_SCORE = """
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[1])
local cur = redis.call('HGET', KEYS[2], ARGV[3])
if not cur then cur = 0 end
redis.call('HSET', KEYS[2], ARGV[3], tonumber(cur) + tonumber(ARGV[4]))
return redis.call('HGET', KEYS[2], ARGV[3])
"""


def load_speed_stub_to_dragonfly(
    stub_path: Path,
    *,
    host: str,
    port: int,
    max_rows: int = 50_000,
) -> dict[str, Any]:
    """Push speed_tier stub / feed lines into Dragonfly via Nezha-shaped Lua path."""
    import hashlib

    import redis

    client = redis.Redis(host=host, port=port, decode_responses=False)
    client.ping()
    sha = client.script_load(LUA_SCORE)
    t0 = time.perf_counter()
    n = 0
    with stub_path.open(encoding="utf-8") as fh:
        pipe = client.pipeline(transaction=False)
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ci = str(row.get("ci_id") or row.get("entity_id") or "unknown")
            name = str(row.get("name") or row.get("metric_name") or "event")
            pattern = f"{ci}→{name}"
            pattern_hash = int(hashlib.md5(pattern.encode()).hexdigest(), 16) % 256
            minute = int(time.time() // 60)
            tg = f"tg:lab:{ci}:{minute}"
            pc = f"pc:lab:{pattern_hash}"
            member = f"{ci}:{n}".encode()
            pipe.evalsha(sha, 2, tg, pc, member, float(n), pattern, 1)
            n += 1
            if n % 256 == 0:
                pipe.execute()
                pipe = client.pipeline(transaction=False)
            if n >= max_rows:
                break
        if n % 256:
            pipe.execute()
    elapsed = time.perf_counter() - t0
    return {
        "rows_loaded": n,
        "elapsed_s": round(elapsed, 4),
        "eps": round(n / elapsed, 2) if elapsed > 0 else 0.0,
        "host": host,
        "port": port,
        "source": str(stub_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="N4 metric_slice read + optional DF load")
    parser.add_argument(
        "--structural",
        type=Path,
        help="F1 structural/stream.jsonl (builds metric_slice if --store-out set)",
    )
    parser.add_argument(
        "--metric-slice",
        type=Path,
        help="Existing metric_slice.jsonl to read",
    )
    parser.add_argument(
        "--store-out",
        type=Path,
        help="Write Federated stores here from --structural",
    )
    parser.add_argument("--topology", type=Path, help="Optional topology.json")
    parser.add_argument("--speed-feed", type=Path, help="Optional speed_tier feed")
    parser.add_argument("--load-dragonfly", action="store_true")
    parser.add_argument("--df-host", default="127.0.0.1")
    parser.add_argument("--df-port", type=int, default=6380)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    result: dict[str, Any] = {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    slice_path = args.metric_slice
    if args.structural and args.store_out:
        topo = None
        if args.topology and args.topology.is_file():
            topo = json.loads(args.topology.read_text())
        meta = write_federated_stores(
            structural_jsonl=args.structural.resolve(),
            out_dir=args.store_out.resolve(),
            topology=topo,
            speed_jsonl=args.speed_feed.resolve() if args.speed_feed else None,
        )
        result["store_meta"] = meta
        slice_path = args.store_out.resolve() / "metric_slice.jsonl"

    if slice_path is None or not slice_path.is_file():
        raise SystemExit("Need --metric-slice or (--structural and --store-out)")

    result["metric_slice_read"] = read_metric_slice(slice_path.resolve())

    if args.load_dragonfly:
        # Prefer speed stub from store-out, else speed feed
        stub = None
        if args.store_out:
            cand = args.store_out.resolve() / "speed_tier_stub.jsonl"
            if cand.is_file():
                stub = cand
        if stub is None and args.speed_feed and args.speed_feed.is_file():
            stub = args.speed_feed.resolve()
        if stub is None:
            raise SystemExit("--load-dragonfly needs speed stub/feed")
        result["dragonfly_load"] = load_speed_stub_to_dragonfly(
            stub, host=args.df_host, port=args.df_port
        )

    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
