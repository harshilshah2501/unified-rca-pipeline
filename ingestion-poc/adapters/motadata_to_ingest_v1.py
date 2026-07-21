#!/usr/bin/env python3
"""Convert Motadata resolved JSONL (logs/metrics/traces/spans) → ingest.v1.

Input (default): datasets/ingest_samples/jsonl_resolved/
Output (default): datasets/ingest_samples/motadata-ingest/stream.jsonl  (gitignored if large)

Does not push or require GitHub — large dumps stay local.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SRC = REPO / "datasets" / "ingest_samples" / "jsonl_resolved"
DEFAULT_OUT = REPO / "datasets" / "ingest_samples" / "motadata-ingest"

SEVERITY = {
    "critical": 1.0,
    "error": 0.9,
    "warning": 0.7,
    "informational": 0.3,
    "info": 0.3,
    "debug": 0.1,
    "ok": 0.0,
}


def _to_iso(ts: Any) -> str:
    if ts is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(ts).strip()
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    elif s.endswith("Z"):
        pass
    elif "T" in s and "+" not in s and not s.endswith("Z"):
        s = s + "Z" if len(s) == 19 else s
    return s


def _emit(obj: dict[str, Any]) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _iter_jsonl(path: Path, limit: int | None) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
        yield  # pragma: no cover
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
            n += 1
            if limit is not None and n >= limit:
                break


def convert_log(row: dict[str, Any]) -> dict[str, Any]:
    attrs = row.get("attributes") or {}
    host = attrs.get("hostname") or row.get("event_source") or "unknown-host"
    sev = str(row.get("event_severity") or attrs.get("severity") or "info").lower()
    return {
        "schema_version": "ingest.v1",
        "ts": _to_iso(row.get("timestamp")),
        "tenant": "default",
        "ci_id": str(host),
        "ci_type": "Host",
        "signal_class": "event",
        "name": row.get("event_log_type") or attrs.get("syslog.tag") or "log",
        "value": 1.0,
        "threshold": None,
        "severity": SEVERITY.get(sev, 0.5),
        "labels": {
            "source": "motadata",
            "signal_kind": "log",
            "event_source": row.get("event_source"),
            "event_category": row.get("event_category"),
            "plugin_id": row.get("plugin_id"),
            "log_id": row.get("log_id"),
            "message": row.get("message"),
            "syslog_tag": attrs.get("syslog.tag"),
            "pipeline": attrs.get("pipeline"),
        },
    }


def convert_metric_numeric(row: dict[str, Any]) -> list[dict[str, Any]]:
    obj_id = row.get("id")
    ci_id = f"monitor-{obj_id}"
    ts = _to_iso(row.get("timestamp"))
    plugin_id = row.get("plugin_id")
    out: list[dict[str, Any]] = []
    for name, value in (row.get("fields") or {}).items():
        if isinstance(value, bool):
            num = 1.0 if value else 0.0
        elif isinstance(value, (int, float)):
            num = float(value)
        else:
            continue  # non-numeric → skip (string metrics handled separately)
        out.append(
            {
                "schema_version": "ingest.v1",
                "ts": ts,
                "tenant": "default",
                "ci_id": ci_id,
                "ci_type": "Monitor",
                "signal_class": "metric_sample",
                "name": str(name),
                "value": num,
                "threshold": None,
                "severity": None,
                "labels": {
                    "source": "motadata",
                    "signal_kind": "metric_numeric",
                    "monitor_id": obj_id,
                    "plugin_id": plugin_id,
                },
            }
        )
    return out


def convert_metric_string(row: dict[str, Any]) -> list[dict[str, Any]]:
    obj_id = row.get("id")
    ci_id = f"monitor-{obj_id}"
    ts = _to_iso(row.get("timestamp"))
    plugin_id = row.get("plugin_id")
    out: list[dict[str, Any]] = []
    for name, value in (row.get("fields") or {}).items():
        out.append(
            {
                "schema_version": "ingest.v1",
                "ts": ts,
                "tenant": "default",
                "ci_id": ci_id,
                "ci_type": "Monitor",
                "signal_class": "event",
                "name": str(name),
                "value": 1.0,
                "threshold": None,
                "severity": 0.2,
                "labels": {
                    "source": "motadata",
                    "signal_kind": "metric_string",
                    "monitor_id": obj_id,
                    "plugin_id": plugin_id,
                    "string_value": str(value),
                },
            }
        )
    return out


def convert_trace(row: dict[str, Any]) -> dict[str, Any]:
    svc = row.get("service_trace_service_name") or "unknown-service"
    dur_us = row.get("service_trace_duration_us")
    try:
        dur_ms = float(dur_us) / 1000.0 if dur_us is not None else 0.0
    except (TypeError, ValueError):
        dur_ms = 0.0
    errors = int(row.get("service_trace_span_errors") or 0)
    status = row.get("service_trace_status_code")
    return {
        "schema_version": "ingest.v1",
        "ts": _to_iso(row.get("timestamp") or row.get("service_trace_start_time_us")),
        "tenant": "default",
        "ci_id": str(svc),
        "ci_type": "Service",
        "signal_class": "trace_span",
        "name": row.get("service_trace_root_span_name") or "trace",
        "value": dur_ms,
        "threshold": None,
        "severity": 1.0 if errors else 0.2,
        "labels": {
            "source": "motadata",
            "signal_kind": "trace_summary",
            "trace_id": row.get("service_trace_id"),
            "span_count": row.get("service_trace_spans"),
            "span_errors": errors,
            "status_code": status,
            "event_source": row.get("event_source"),
            "is_trace_summary": True,
        },
    }


def convert_span(row: dict[str, Any]) -> dict[str, Any]:
    svc = row.get("service_span_service_name") or "unknown-service"
    dur_us = row.get("service_span_duration_us")
    try:
        dur_ms = float(dur_us) / 1000.0 if dur_us is not None else 0.0
    except (TypeError, ValueError):
        dur_ms = 0.0
    parent = row.get("service_span_parent_id")
    if parent in (None, "", "0000000000000000"):
        parent = None
    has_error = bool(row.get("service_span_has_error"))
    fields = row.get("fields") or {}
    return {
        "schema_version": "ingest.v1",
        "ts": _to_iso(row.get("timestamp") or row.get("service_span_start_time_us")),
        "tenant": "default",
        "ci_id": str(svc),
        "ci_type": "Service",
        "signal_class": "trace_span",
        "name": row.get("service_span_name") or "span",
        "value": dur_ms,
        "threshold": None,
        "severity": 1.0 if has_error else 0.2,
        "labels": {
            "source": "motadata",
            "signal_kind": "span",
            "trace_id": row.get("service_span_trace_id"),
            "span_id": row.get("service_span_id"),
            "parent_span_id": parent,
            "is_root": bool(row.get("service_span_is_root_span")),
            "kind": row.get("service_span_kind"),
            "http_method": row.get("service_span_http_method")
            or fields.get("http_request_method"),
            "http_route": row.get("service_span_http_route") or fields.get("http_route"),
            "http_status": row.get("service_span_http_status_code")
            or fields.get("http_response_status_code"),
            "db_operation": row.get("service_span_db_operation"),
            "db_name": row.get("service_span_db_name"),
            "event_source": row.get("event_source"),
            "host_name": fields.get("host_name"),
            "status": row.get("service_span_status_code_string"),
        },
    }


def convert_sources(
    src: Path,
    *,
    limit_logs: int | None,
    limit_metrics: int | None,
    limit_traces: int | None,
    limit_spans: int | None,
    include: set[str],
) -> Iterable[dict[str, Any]]:
    if "logs" in include:
        for row in _iter_jsonl(src / "log.jsonl", limit_logs):
            yield convert_log(row)
    if "metrics" in include:
        for row in _iter_jsonl(src / "metric_numeric.jsonl", limit_metrics):
            yield from convert_metric_numeric(row)
        for row in _iter_jsonl(src / "metric_string.jsonl", limit_metrics):
            yield from convert_metric_string(row)
    if "traces" in include:
        for row in _iter_jsonl(src / "trace.jsonl", limit_traces):
            yield convert_trace(row)
    if "spans" in include:
        for row in _iter_jsonl(src / "span.jsonl", limit_spans):
            yield convert_span(row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Motadata JSONL → ingest.v1")
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--out-name",
        default="stream.jsonl",
        help="Output filename inside out-dir",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Small limits for quick validation (default if no --full)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Convert entire corpus (can be multi-GB; local only)",
    )
    parser.add_argument("--limit-logs", type=int, default=None)
    parser.add_argument("--limit-metrics", type=int, default=None)
    parser.add_argument("--limit-traces", type=int, default=None)
    parser.add_argument("--limit-spans", type=int, default=None)
    parser.add_argument(
        "--include",
        default="logs,metrics,traces,spans",
        help="Comma list: logs,metrics,traces,spans",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Sort by ts in memory (only for small/smoke runs)",
    )
    args = parser.parse_args(argv)

    include = {x.strip() for x in args.include.split(",") if x.strip()}
    src = args.src.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.full:
        lim_logs = args.limit_logs
        lim_metrics = args.limit_metrics
        lim_traces = args.limit_traces
        lim_spans = args.limit_spans
    else:
        # smoke defaults
        lim_logs = args.limit_logs if args.limit_logs is not None else 2000
        lim_metrics = args.limit_metrics if args.limit_metrics is not None else 2000
        lim_traces = args.limit_traces if args.limit_traces is not None else 1000
        lim_spans = args.limit_spans if args.limit_spans is not None else 5000

    rows = list(
        convert_sources(
            src,
            limit_logs=lim_logs,
            limit_metrics=lim_metrics,
            limit_traces=lim_traces,
            limit_spans=lim_spans,
            include=include,
        )
    )
    if args.sort or not args.full:
        rows.sort(key=lambda r: (r.get("ts") or "", r.get("ci_id") or "", r.get("name") or ""))

    out_path = out_dir / args.out_name
    with out_path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(_emit(r) + "\n")

    by_class: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    cis: set[str] = set()
    for r in rows:
        by_class[r["signal_class"]] = by_class.get(r["signal_class"], 0) + 1
        kind = (r.get("labels") or {}).get("signal_kind") or "?"
        by_kind[kind] = by_kind.get(kind, 0) + 1
        cis.add(r["ci_id"])

    manifest = {
        "schema_version": "motadata_ingest.v1",
        "source": str(src),
        "output": str(out_path),
        "mode": "full" if args.full else "smoke",
        "limits": {
            "logs": lim_logs,
            "metrics": lim_metrics,
            "traces": lim_traces,
            "spans": lim_spans,
        },
        "include": sorted(include),
        "stream_lines": len(rows),
        "by_signal_class": by_class,
        "by_signal_kind": by_kind,
        "unique_ci_ids": len(cis),
        "ci_id_sample": sorted(cis)[:30],
        "note": "ci_id for metrics is monitor-{id}; logs use hostname/IP; traces/spans use service name. Topology/GT not yet attached.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    print(f"Wrote {out_path} ({len(rows)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
