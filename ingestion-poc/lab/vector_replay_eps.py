#!/usr/bin/env python3
"""Measure F1 Python fan-out EPS (Vector-equivalent sink write path)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ingestion-poc" / "pipeline"))

from f1_run import write_python_sinks  # noqa: E402


def _synthetic_row(i: int) -> dict:
    return {
        "schema_version": "ingest.v1",
        "ts": "2026-07-21T12:00:00Z",
        "tenant": "lab",
        "ci_id": f"svc-{i % 50}",
        "ci_type": "Service",
        "fact_kind": "metric_sample" if i % 3 else "event",
        "name": "lab.metric" if i % 3 else "lab.event",
        "value": float(i % 100),
        "threshold": 50.0 if i % 3 else None,
        "severity": 0.5,
        "labels": {"source": "lab_eps"},
    }


def write_synthetic_stream(path: Path, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for i in range(n):
            fh.write(json.dumps(_synthetic_row(i), separators=(",", ":")) + "\n")


def measure_fanout(stream: Path, out_dir: Path) -> dict:
    if out_dir.exists():
        import shutil

        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    t0 = time.perf_counter()
    counts = write_python_sinks(stream, out_dir)
    elapsed = time.perf_counter() - t0
    total = int(counts.get("total") or 0)
    return {
        "path": "python_f1_fanout",
        "events": total,
        "elapsed_s": round(elapsed, 4),
        "eps": round(total / elapsed, 2) if elapsed > 0 else 0.0,
        "sink_counts": counts,
        "stream": str(stream),
        "out_dir": str(out_dir),
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Vector-equivalent Python fan-out (not Docker Vector process EPS)",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F1 fan-out EPS probe")
    parser.add_argument(
        "--events",
        type=int,
        default=50_000,
        help="Synthetic events to generate (ignored if --stream set)",
    )
    parser.add_argument("--stream", type=Path, help="Existing ingest.v1 JSONL")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO / "ingestion-poc" / "out" / "lab-fanout",
    )
    parser.add_argument("--output", type=Path, help="Write JSON result")
    args = parser.parse_args(argv)

    if args.stream:
        stream = args.stream.resolve()
    else:
        stream = args.out_dir.parent / "lab-synthetic-stream.jsonl"
        write_synthetic_stream(stream, args.events)

    result = measure_fanout(stream, args.out_dir.resolve())
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
