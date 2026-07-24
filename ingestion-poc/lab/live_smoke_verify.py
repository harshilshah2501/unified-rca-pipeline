#!/usr/bin/env python3
"""Verify LIVE smoke out-dir: sink counts + live_smoke_meta.json.

Usage:
  python3 ingestion-poc/lab/live_smoke_verify.py --out-dir ingestion-poc/out/live-...
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LIVE smoke sink verifier")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--min-lines",
        type=int,
        default=1,
        help="Minimum lines across lean+structural+speed (default 1)",
    )
    args = parser.parse_args(argv)
    out: Path = args.out_dir
    sinks = {
        "lean/events.jsonl": _count_lines(out / "lean" / "events.jsonl"),
        "structural/stream.jsonl": _count_lines(out / "structural" / "stream.jsonl"),
        "speed_tier/feed.jsonl": _count_lines(out / "speed_tier" / "feed.jsonl"),
    }
    total = sum(sinks.values())
    meta = {
        "live_run_id": out.name,
        "detect_source": "shared_threshold",
        "sink_counts": sinks,
        "sink_total_lines": total,
        "pass": total >= args.min_lines,
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "live_smoke_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))
    if not meta["pass"]:
        print(
            f"FAIL: need >= {args.min_lines} sink lines; got {total}",
            file=sys.stderr,
        )
        return 1
    print("PASS: LIVE sink smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
