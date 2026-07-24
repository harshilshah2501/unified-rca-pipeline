#!/usr/bin/env python3
"""Synthesize Motadata APM metric_samples (error_rate / duration) from span.jsonl.

Emits ingest.v1 lines that Detect can threshold — Motadata spans alone do not
carry metric thresholds.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SRC = REPO / "datasets" / "ingest_samples" / "jsonl_resolved" / "span.jsonl"
DEFAULT_OUT = (
    REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "span_metrics.jsonl"
)


def _minute_key(ts: str) -> str:
    # 2026-07-21T05:58:03+00:00 → 2026-07-21T05:58:00Z
    if not ts:
        return "unknown"
    core = ts.replace("+00:00", "Z")
    if len(core) >= 16:
        return core[:16] + ":00Z"
    return core


def synthesize(
    span_path: Path,
    *,
    limit_spans: int | None = None,
    services: set[str] | None = None,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    n = 0
    with span_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n += 1
            svc = str(row.get("service_span_service_name") or "unknown-service")
            if services and svc not in services:
                if limit_spans is not None and n >= limit_spans:
                    break
                continue
            minute = _minute_key(
                str(row.get("timestamp") or row.get("service_span_start_time_us") or "")
            )
            key = (svc, minute)
            b = buckets.setdefault(
                key,
                {
                    "n": 0,
                    "err": 0,
                    "err4": 0,
                    "err5": 0,
                    "dur_sum": 0.0,
                    "host": None,
                },
            )
            b["n"] += 1
            code_raw = row.get("service_span_http_status_code")
            try:
                code = int(code_raw) if code_raw not in (None, "") else 0
            except (TypeError, ValueError):
                code = 0
            has_error = bool(row.get("service_span_has_error"))
            if code >= 400 or has_error:
                b["err"] += 1
            if 400 <= code < 500:
                b["err4"] += 1
            if code >= 500:
                b["err5"] += 1
            try:
                dur_ms = float(row.get("service_span_duration_us") or 0) / 1000.0
            except (TypeError, ValueError):
                dur_ms = 0.0
            b["dur_sum"] += dur_ms
            fields = row.get("fields") or {}
            if not b["host"]:
                b["host"] = fields.get("host_name")
            if limit_spans is not None and n >= limit_spans:
                break

    out: list[dict[str, Any]] = []
    for (svc, minute), b in sorted(buckets.items(), key=lambda x: x[0][1]):
        if b["n"] == 0:
            continue
        err_rate = b["err"] / b["n"]
        err4 = b["err4"] / b["n"]
        err5 = b["err5"] / b["n"]
        avg_dur = b["dur_sum"] / b["n"]
        labels = {
            "source": "motadata",
            "signal_kind": "span_derived",
            "span_count": b["n"],
            "host_name": b["host"],
        }
        base = {
            "schema_version": "ingest.v1",
            "ts": minute,
            "tenant": "default",
            "ci_id": svc,
            "ci_type": "Service",
            "signal_class": "metric_sample",
            "severity": None,
            "labels": labels,
        }
        out.append(
            {
                **base,
                "name": "http.error_rate",
                "value": round(err_rate, 6),
                "threshold": 0.05,
                "labels": {**labels, "error_spans": b["err"]},
            }
        )
        out.append(
            {
                **base,
                "name": "http.error_rate_4xx",
                "value": round(err4, 6),
                "threshold": 0.15,
                "labels": {**labels, "error_spans": b["err4"]},
            }
        )
        out.append(
            {
                **base,
                "name": "http.error_rate_5xx",
                "value": round(err5, 6),
                "threshold": 0.02,
                "labels": {**labels, "error_spans": b["err5"]},
            }
        )
        out.append(
            {
                **base,
                "name": "span.duration_ms",
                "value": round(avg_dur, 3),
                "threshold": 500.0,
                "labels": labels,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Span → Motadata error_rate metrics")
    parser.add_argument("--span-jsonl", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit-spans", type=int, default=None)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Limit to 50k spans for quick runs",
    )
    args = parser.parse_args(argv)
    limit = args.limit_spans
    if args.smoke and limit is None:
        limit = 50000
    rows = synthesize(args.span_jsonl.resolve(), limit_spans=limit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    crossed = sum(
        1
        for r in rows
        if r["name"] == "http.error_rate" and r["value"] > (r["threshold"] or 0)
    )
    print(
        f"wrote {args.out} lines={len(rows)} "
        f"error_rate_crossings≈{crossed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
