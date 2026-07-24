#!/usr/bin/env python3
"""Push ObserveOps UC-1..UC-5 synthetic telemetry to OpenObserve.

Sends logs (+ pack events), metrics series, and OTLP-JSON traces/spans so OO
can run its RCA engine on the same incidents used for Lean/Federated reports.

Credentials via env (never commit):
  OPENOBSERVE_URL       default http://172.16.14.77:5080
  OPENOBSERVE_ORG       default default
  OPENOBSERVE_USER
  OPENOBSERVE_PASSWORD

Examples:
  # Inventory / payload preview (no network)
  .venv/bin/python ingestion-poc/adapters/push_observeops_uc_to_openobserve.py --dry-run

  # Live push
  export OPENOBSERVE_USER='admin@motadata.com'
  export OPENOBSERVE_PASSWORD='...'
  .venv/bin/python ingestion-poc/adapters/push_observeops_uc_to_openobserve.py
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "observeops"
DEFAULT_PARITY_RUN = "adr001-rerun-20260723"
UCS = ["UC-1", "UC-2", "UC-3", "UC-4", "UC-5"]

# Stream naming: one log stream per UC; metrics use __name__; traces via OTLP
LOG_STREAM_PREFIX = "observeops_uc"
# Streams created by earlier shifted/truncated pushes (safe to wipe)
STALE_LOG_STREAMS = [f"{LOG_STREAM_PREFIX}_uc{i}" for i in range(1, 6)] + [
    "observeops_ingest_probe",
]
STALE_METRIC_PREFIX = "observeops_"


def _auth(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def _request_json(
    method: str,
    url: str,
    auth: str,
    *,
    payload: Any | None = None,
    timeout: int = 60,
) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                body = raw[:500]
            return {"status": resp.status, "body": body, "url": url}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")[:800]
        return {"status": e.code, "error": err, "url": url}
    except urllib.error.URLError as e:
        return {"status": 0, "error": str(e.reason), "url": url}


def _parse_ts_ms(ts: str | None, *, shift_ms: int = 0) -> int:
    if not ts:
        return int(time.time() * 1000)
    s = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return int(time.time() * 1000)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000) + shift_ms


def _collect_pack_timestamps(uc: dict) -> list[str]:
    ts: list[str] = []
    for row in uc["logs"]:
        if row.get("ts"):
            ts.append(row["ts"])
    for ev in uc["events"]:
        if ev.get("timestamp"):
            ts.append(ev["timestamp"])
    for series in uc["metric_series"]:
        for pt in series.get("points") or []:
            if pt.get("timestamp"):
                ts.append(pt["timestamp"])
    for a in uc["anomalies"]:
        if a.get("timestamp"):
            ts.append(a["timestamp"])
    for sp in uc["spans"]:
        if sp.get("start_time"):
            ts.append(sp["start_time"])
    seed_ts = (uc.get("seed") or {}).get("timestamp")
    if seed_ts:
        ts.append(seed_ts)
    return ts


def compute_shift_ms(
    uc: dict,
    *,
    end_offset_minutes: float = 20.0,
) -> tuple[int, str | None, str]:
    """Shift pack times so the latest point lands ~end_offset_minutes ago.

    OpenObserve rejects ingest older than ZO_INGEST_ALLOWED_UPTO (often 5h).
    Relative deltas inside the UC window are preserved.
    """
    stamps = _collect_pack_timestamps(uc)
    if not stamps:
        return 0, None, datetime.now(timezone.utc).isoformat()
    max_ms = max(_parse_ts_ms(t) for t in stamps)
    target_max = int(time.time() * 1000) - int(end_offset_minutes * 60_000)
    shift = target_max - max_ms
    original_max = datetime.fromtimestamp(max_ms / 1000, tz=timezone.utc).isoformat()
    shifted_max = datetime.fromtimestamp(target_max / 1000, tz=timezone.utc).isoformat()
    return shift, original_max, shifted_max


def _post_json(
    url: str,
    auth: str,
    payload: Any,
    *,
    dry_run: bool,
    timeout: int = 120,
    content_type: str = "application/json",
) -> dict:
    body = json.dumps(payload).encode()
    if dry_run:
        return {
            "dry_run": True,
            "url": url,
            "bytes": len(body),
            "records": len(payload) if isinstance(payload, list) else 1,
        }
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": auth,
            "Content-Type": content_type,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                return {"status": resp.status, "body": json.loads(raw)}
            except json.JSONDecodeError:
                return {"status": resp.status, "body": raw[:500]}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")[:800]
        return {"status": e.code, "error": err, "url": url}
    except urllib.error.URLError as e:
        return {"status": 0, "error": str(e.reason), "url": url}


def _load_uc(uc_id: str, *, pack_dir: Path | None = None) -> dict:
    pack = pack_dir or (CORPUS / uc_id)
    raw = pack / "raw"
    events_doc = (
        json.loads((pack / "events.json").read_text())
        if (pack / "events.json").is_file()
        else {"events": []}
    )
    events = events_doc.get("events", [])
    logs = (
        json.loads((raw / "logs.json").read_text())
        if (raw / "logs.json").is_file()
        else []
    )
    spans = (
        json.loads((raw / "spans.json").read_text())
        if (raw / "spans.json").is_file()
        else []
    )
    metric_series = []
    mdir = pack / "metrics"
    if mdir.is_dir():
        for mf in sorted(mdir.glob("*.json")):
            metric_series.append(json.loads(mf.read_text()))
    anomalies = (
        json.loads((pack / "anomalies.json").read_text())
        if (pack / "anomalies.json").is_file()
        else {"anomalies": []}
    )
    gt = (
        json.loads((pack / "ground_truth.json").read_text())
        if (pack / "ground_truth.json").is_file()
        else {}
    )
    seed = (
        json.loads((pack / "symptom_seed.json").read_text())
        if (pack / "symptom_seed.json").is_file()
        else {}
    )
    changes: list[dict] = []
    ch_path = pack / "changes.jsonl"
    if ch_path.is_file():
        for line in ch_path.read_text().splitlines():
            line = line.strip()
            if line:
                changes.append(json.loads(line))
    return {
        "uc_id": uc_id,
        "pack_dir": str(pack),
        "events": events,
        "logs": logs,
        "spans": spans,
        "changes": changes,
        "metric_series": metric_series,
        "anomalies": anomalies.get("anomalies") or [],
        "gt": gt,
        "seed": seed,
    }


def parity_pack_dir(uc_id: str, run_id: str) -> Path:
    """Exact Lean shared-detect inputs for a bakeoff run."""
    return (
        REPO
        / "benchmarking"
        / "results"
        / "lean"
        / uc_id
        / f"run-{run_id}"
        / "parity_corpus"
        / uc_id
    )


def list_oo_streams(base: str, org: str, auth: str, *, stream_type: str = "") -> list[dict]:
    url = f"{base}/api/{org}/streams"
    if stream_type:
        url += f"?type={stream_type}"
    res = _request_json("GET", url, auth)
    if res.get("error"):
        return []
    body = res.get("body") or {}
    items = body if isinstance(body, list) else body.get("list") or body.get("streams") or []
    if isinstance(items, dict):
        items = items.get("list") or []
    return [s for s in items if isinstance(s, dict)]


def purge_stale_observeops_streams(
    *,
    base: str,
    org: str,
    auth: str,
    dry_run: bool = False,
) -> dict:
    """Delete observeops_* log/metric streams from earlier shifted pushes."""
    deleted: list[dict] = []
    skipped: list[str] = []

    def _delete(name: str, stype: str) -> None:
        url = f"{base}/api/{org}/streams/{name}?type={stype}&delete_all=true"
        if dry_run:
            deleted.append({"name": name, "type": stype, "dry_run": True})
            return
        res = _request_json("DELETE", url, auth)
        deleted.append({"name": name, "type": stype, **res})

    # Logs we know we created
    for name in STALE_LOG_STREAMS:
        _delete(name, "logs")

    # Any observeops_* metrics/logs/traces present on the server
    for stype in ("logs", "metrics", "traces"):
        for s in list_oo_streams(base, org, auth, stream_type=stype):
            name = str(s.get("name") or s.get("stream") or "")
            if not name.startswith(STALE_METRIC_PREFIX) and name not in STALE_LOG_STREAMS:
                continue
            if name in STALE_LOG_STREAMS and stype == "logs":
                continue  # already queued
            _delete(name, stype)

    return {"deleted": deleted, "skipped": skipped}


def build_log_records(uc: dict, *, shift_ms: int = 0) -> list[dict]:
    """Logs + events (+ parity anomalies/changes as log rows) → OO log JSON."""
    uc_id = uc["uc_id"]
    out: list[dict] = []
    for row in uc["logs"]:
        labels = dict(row.get("labels") or {})
        out.append(
            {
                "_timestamp": _parse_ts_ms(row.get("ts"), shift_ms=shift_ms),
                "message": row.get("message") or "",
                "level": row.get("level") or "INFO",
                "logger": row.get("logger"),
                "stream_src": row.get("stream"),
                "ci": labels.get("ci"),
                "uc_id": uc_id,
                "corpus": "observeops",
                "source": "synthetic",
                "parity_input": True,
                "scenario": uc["gt"].get("fault_title") or uc_id,
                "root_ci_gt": uc["gt"].get("root_ci"),
                "signature_gt": uc["gt"].get("signature"),
                "original_ts": row.get("ts"),
                **{f"label_{k}": v for k, v in labels.items() if k != "ci"},
            }
        )
    for ev in uc["events"]:
        out.append(
            {
                "_timestamp": _parse_ts_ms(ev.get("timestamp"), shift_ms=shift_ms),
                "message": ev.get("message") or "",
                "level": (ev.get("severity") or "info").upper(),
                "event_type": ev.get("event_type"),
                "ci": ev.get("ci"),
                "uc_id": uc_id,
                "corpus": "observeops",
                "source": "parity_event",
                "parity_input": True,
                "scenario": uc["gt"].get("fault_title") or uc_id,
                "root_ci_gt": uc["gt"].get("root_ci"),
                "signature_gt": uc["gt"].get("signature"),
                "original_ts": ev.get("timestamp"),
            }
        )
    # Lean evidence trail also includes crossed anomalies — emit as logs for OO
    for a in uc["anomalies"]:
        if not a.get("crossed"):
            continue
        out.append(
            {
                "_timestamp": _parse_ts_ms(a.get("timestamp"), shift_ms=shift_ms),
                "message": (
                    f"anomaly crossed: {a.get('ci')} {a.get('signal')}="
                    f"{a.get('value')} (threshold={a.get('threshold')})"
                ),
                "level": "WARN",
                "event_type": "anomaly.crossed",
                "ci": a.get("ci"),
                "signal": a.get("signal"),
                "value": a.get("value"),
                "threshold": a.get("threshold"),
                "uc_id": uc_id,
                "corpus": "observeops",
                "source": "parity_anomaly",
                "parity_input": True,
                "scenario": uc["gt"].get("fault_title") or uc_id,
                "root_ci_gt": uc["gt"].get("root_ci"),
                "signature_gt": uc["gt"].get("signature"),
                "original_ts": a.get("timestamp"),
            }
        )
    for ch in uc.get("changes") or []:
        ts = ch.get("timestamp") or ch.get("ts") or (uc.get("seed") or {}).get("timestamp")
        out.append(
            {
                "_timestamp": _parse_ts_ms(ts, shift_ms=shift_ms),
                "message": ch.get("message") or ch.get("summary") or json.dumps(ch),
                "level": "INFO",
                "event_type": ch.get("change_type") or "change",
                "ci": ch.get("ci") or ch.get("entity"),
                "uc_id": uc_id,
                "corpus": "observeops",
                "source": "parity_change",
                "parity_input": True,
                "scenario": uc["gt"].get("fault_title") or uc_id,
                "root_ci_gt": uc["gt"].get("root_ci"),
                "signature_gt": uc["gt"].get("signature"),
                "original_ts": ts,
            }
        )
    # Always include symptom seed marker (Lean hop-0)
    seed = uc.get("seed") or {}
    if seed.get("timestamp"):
        out.append(
            {
                "_timestamp": _parse_ts_ms(seed.get("timestamp"), shift_ms=shift_ms),
                "message": (
                    f"symptom seed: {seed.get('ci')} {seed.get('signal')}"
                ),
                "level": "ERROR",
                "event_type": "symptom_seed",
                "ci": seed.get("ci"),
                "signal": seed.get("signal"),
                "uc_id": uc_id,
                "corpus": "observeops",
                "source": "parity_seed",
                "parity_input": True,
                "scenario": uc["gt"].get("fault_title") or uc_id,
                "root_ci_gt": uc["gt"].get("root_ci"),
                "signature_gt": uc["gt"].get("signature"),
                "original_ts": seed.get("timestamp"),
            }
        )
    return out


def build_metric_records(
    uc: dict,
    *,
    shift_ms: int = 0,
    retain_hours: float | None = 4.5,
) -> list[dict]:
    """Pack metrics/ series + crossed anomaly peaks → OO metrics JSON.

    If retain_hours is set, keep only points within that many hours of the pack's
    latest timestamp (pre-shift). OO typically rejects ingest older than ~5h.
    """
    uc_id = uc["uc_id"]
    max_ms = None
    if retain_hours is not None:
        stamps = _collect_pack_timestamps(uc)
        if stamps:
            max_ms = max(_parse_ts_ms(t) for t in stamps)
    cutoff = None
    if max_ms is not None and retain_hours is not None:
        cutoff = max_ms - int(retain_hours * 3600_000)

    out: list[dict] = []
    dropped = 0
    for series in uc["metric_series"]:
        ci = series.get("ci") or "unknown"
        signal = series.get("signal") or "metric"
        name = f"observeops_{signal.replace('.', '_')}"
        for pt in series.get("points") or []:
            raw_ms = _parse_ts_ms(pt.get("timestamp"))
            if cutoff is not None and raw_ms < cutoff:
                dropped += 1
                continue
            out.append(
                {
                    "__name__": name,
                    "__type__": "gauge",
                    "_timestamp": raw_ms + shift_ms,
                    "value": float(pt.get("value") or 0),
                    "ci": ci,
                    "signal": signal,
                    "uc_id": uc_id,
                    "corpus": "observeops",
                    "source": "parity_metric",
                    "parity_input": True,
                    "root_ci_gt": uc["gt"].get("root_ci"),
                    "signature_gt": uc["gt"].get("signature"),
                }
            )
    # Ensure incident-window peaks exist even if series lookback is long
    for a in uc["anomalies"]:
        if not a.get("crossed"):
            continue
        signal = a.get("signal") or "anomaly"
        out.append(
            {
                "__name__": f"observeops_{signal.replace('.', '_')}",
                "__type__": "gauge",
                "_timestamp": _parse_ts_ms(a.get("timestamp"), shift_ms=shift_ms),
                "value": float(a.get("value") or 0),
                "ci": a.get("ci"),
                "signal": signal,
                "threshold": a.get("threshold"),
                "crossed": True,
                "uc_id": uc_id,
                "corpus": "observeops",
                "source": "parity_anomaly_peak",
                "parity_input": True,
                "root_ci_gt": uc["gt"].get("root_ci"),
                "signature_gt": uc["gt"].get("signature"),
            }
        )
    # stash for callers that want drop stats (optional)
    uc["_metrics_dropped"] = dropped
    return out


def _hex_id(raw: str, nbytes: int) -> str:
    """OTLP requires hex-only ids (16 bytes trace / 8 bytes span)."""
    h = "".join(c for c in raw.lower() if c in "0123456789abcdef")
    if len(h) < nbytes * 2:
        # deterministic pad from alnum hash-ish mapping
        mapped = []
        for c in raw.lower():
            if c in "0123456789abcdef":
                mapped.append(c)
            else:
                mapped.append(format(ord(c) % 16, "x"))
        h = "".join(mapped)
    h = (h + "0" * (nbytes * 2))[: nbytes * 2]
    return h


def build_otlp_traces(uc: dict, *, shift_ms: int = 0) -> dict:
    """Convert pack spans → OTLP/HTTP JSON resourceSpans."""
    uc_id = uc["uc_id"]
    by_service: dict[str, list[dict]] = {}
    for sp in uc["spans"]:
        svc = sp.get("service_name") or "unknown"
        by_service.setdefault(svc, []).append(sp)

    resource_spans = []
    for svc, spans in by_service.items():
        scope_spans = []
        otlp_spans = []
        for sp in spans:
            start_ms = _parse_ts_ms(sp.get("start_time"), shift_ms=shift_ms)
            dur = float(sp.get("duration_ms") or 0)
            start_ns = start_ms * 1_000_000
            end_ns = start_ns + int(dur * 1_000_000)
            attrs = [
                {"key": "uc_id", "value": {"stringValue": uc_id}},
                {"key": "corpus", "value": {"stringValue": "observeops"}},
                {"key": "source", "value": {"stringValue": "synthetic"}},
                {
                    "key": "root_ci_gt",
                    "value": {"stringValue": str(uc["gt"].get("root_ci") or "")},
                },
                {
                    "key": "signature_gt",
                    "value": {"stringValue": str(uc["gt"].get("signature") or "")},
                },
            ]
            for k, v in (sp.get("attributes") or {}).items():
                attrs.append(
                    {"key": str(k), "value": {"stringValue": str(v)}}
                )
            tid = _hex_id(str(sp.get("trace_id") or uc_id), 16)
            sid = _hex_id(str(sp.get("span_id") or "s0"), 8)
            parent = sp.get("parent_span_id")
            parent_hex = _hex_id(str(parent), 8) if parent else None
            kind = sp.get("kind") or sp.get("span_kind") or "INTERNAL"
            kind_map = {
                "SERVER": 2,
                "CLIENT": 3,
                "PRODUCER": 4,
                "CONSUMER": 5,
                "INTERNAL": 1,
            }
            span_obj: dict[str, Any] = {
                "traceId": tid,
                "spanId": sid,
                "name": sp.get("span_name") or "span",
                "kind": kind_map.get(str(kind).upper(), 1),
                "startTimeUnixNano": str(start_ns),
                "endTimeUnixNano": str(end_ns),
                "attributes": attrs,
            }
            if parent_hex:
                span_obj["parentSpanId"] = parent_hex
            otlp_spans.append(span_obj)
        scope_spans.append({"scope": {"name": "observeops-synthetic"}, "spans": otlp_spans})
        resource_spans.append(
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": svc}},
                        {"key": "uc_id", "value": {"stringValue": uc_id}},
                        {
                            "key": "deployment.environment",
                            "value": {"stringValue": "observeops-synthetic"},
                        },
                    ]
                },
                "scopeSpans": scope_spans,
            }
        )
    return {"resourceSpans": resource_spans}


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _ingest_ok(r: dict | None) -> bool:
    if r is None:
        return True
    if r.get("dry_run"):
        return True
    if r.get("error"):
        return False
    status = r.get("status")
    if status not in (200, 201):
        # OTLP partial success is often 206
        if status != 206:
            return False
    body = r.get("body")
    if isinstance(body, dict):
        partial = body.get("partialSuccess") or {}
        if isinstance(partial, dict) and int(partial.get("rejectedSpans") or 0) > 0:
            return False
        for st in body.get("status") or []:
            if isinstance(st, dict) and int(st.get("failed") or 0) > 0:
                return False
    return True


def push_uc(
    uc: dict,
    *,
    base: str,
    org: str,
    auth: str,
    dry_run: bool,
    batch: int,
    shift_to_now: bool,
    end_offset_minutes: float,
    retain_hours: float | None,
) -> dict:
    uc_id = uc["uc_id"]
    stream = f"{LOG_STREAM_PREFIX}_{uc_id.lower().replace('-', '')}"
    summary: dict[str, Any] = {
        "uc_id": uc_id,
        "log_stream": stream,
        "pack_dir": uc.get("pack_dir"),
    }

    shift_ms = 0
    if shift_to_now:
        shift_ms, original_max, shifted_max = compute_shift_ms(
            uc, end_offset_minutes=end_offset_minutes
        )
        summary["time_shift"] = {
            "shift_ms": shift_ms,
            "original_max_ts": original_max,
            "shifted_max_ts": shifted_max,
            "end_offset_minutes": end_offset_minutes,
            "retain_hours": retain_hours,
        }

    logs = build_log_records(uc, shift_ms=shift_ms)
    metrics = build_metric_records(
        uc, shift_ms=shift_ms, retain_hours=retain_hours
    )
    traces = build_otlp_traces(uc, shift_ms=shift_ms)
    span_n = sum(
        len(ss.get("spans") or [])
        for rs in traces.get("resourceSpans") or []
        for ss in rs.get("scopeSpans") or []
    )

    # Logs
    log_url = f"{base}/api/{org}/{stream}/_json"
    log_results = []
    for batch_rows in chunked(logs, batch):
        log_results.append(_post_json(log_url, auth, batch_rows, dry_run=dry_run))
    summary["logs"] = {
        "count": len(logs),
        "batches": len(log_results),
        "result": log_results[-1] if log_results else None,
        "ok": all(_ingest_ok(r) for r in log_results),
    }

    # Metrics
    met_url = f"{base}/api/{org}/ingest/metrics/_json"
    met_results = []
    for batch_rows in chunked(metrics, batch):
        met_results.append(_post_json(met_url, auth, batch_rows, dry_run=dry_run))
    summary["metrics"] = {
        "count": len(metrics),
        "dropped_outside_retain": int(uc.get("_metrics_dropped") or 0),
        "batches": len(met_results),
        "result": met_results[-1] if met_results else None,
        "ok": all(_ingest_ok(r) for r in met_results),
    }

    # Traces (OTLP/HTTP JSON)
    tr_url = f"{base}/api/{org}/v1/traces"
    tr_result = (
        _post_json(tr_url, auth, traces, dry_run=dry_run) if span_n else None
    )
    summary["traces"] = {
        "span_count": span_n,
        "result": tr_result,
        "ok": _ingest_ok(tr_result),
    }

    summary["ok"] = (
        summary["logs"]["ok"] and summary["metrics"]["ok"] and summary["traces"]["ok"]
    )

    summary["gt"] = {
        "root_ci": uc["gt"].get("root_ci"),
        "signature": uc["gt"].get("signature"),
        "fault_title": uc["gt"].get("fault_title"),
        "seed": uc["seed"],
    }
    return summary


def preview_samples(uc: dict, *, shift_ms: int = 0, retain_hours: float | None = None) -> dict:
    logs = build_log_records(uc, shift_ms=shift_ms)
    metrics = build_metric_records(uc, shift_ms=shift_ms, retain_hours=retain_hours)
    traces = build_otlp_traces(uc, shift_ms=shift_ms)
    return {
        "uc_id": uc["uc_id"],
        "pack_dir": uc.get("pack_dir"),
        "gt": uc["gt"],
        "counts": {
            "log_records": len(logs),
            "metric_points": len(metrics),
            "metrics_dropped_outside_retain": int(uc.get("_metrics_dropped") or 0),
            "spans": len(uc["spans"]),
            "events_folded_into_logs": len(uc["events"]),
        },
        "sample_log": logs[0] if logs else None,
        "sample_metric": metrics[-1] if metrics else None,
        "sample_trace_resource": (traces.get("resourceSpans") or [None])[0],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=os.environ.get("OPENOBSERVE_URL", "http://172.16.14.77:5080"))
    p.add_argument("--org", default=os.environ.get("OPENOBSERVE_ORG", "default"))
    p.add_argument("--user", default=os.environ.get("OPENOBSERVE_USER", ""))
    p.add_argument("--password", default=os.environ.get("OPENOBSERVE_PASSWORD", ""))
    p.add_argument("--uc", action="append", choices=UCS, help="Subset of UCs (default: all)")
    p.add_argument("--batch", type=int, default=500, help="Ingest batch size")
    p.add_argument("--dry-run", action="store_true", help="Build payloads; do not POST")
    p.add_argument(
        "--preview",
        action="store_true",
        help="Print sample records per UC and exit",
    )
    p.add_argument(
        "--parity-run-id",
        default=None,
        help=(
            "Load exact Lean/Fed shared-detect parity_corpus for this run-id "
            f"(e.g. {DEFAULT_PARITY_RUN}). Implies --no-shift-to-now --retain-hours 0."
        ),
    )
    p.add_argument(
        "--purge-stale",
        action="store_true",
        help="Delete observeops_* streams from earlier shifted/truncated pushes before ingest",
    )
    p.add_argument(
        "--shift-to-now",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Rebase timestamps into OO ingest window (default: on unless --parity-run-id)",
    )
    p.add_argument(
        "--end-offset-minutes",
        type=float,
        default=20.0,
        help="After shift, pack max timestamp is this many minutes ago",
    )
    p.add_argument(
        "--retain-hours",
        type=float,
        default=None,
        help="Keep metric points within this many hours of pack max; 0 = full series",
    )
    p.add_argument(
        "--out-summary",
        type=Path,
        default=REPO / "benchmarking/results/comparison/oo_push_summary.json",
    )
    args = p.parse_args(argv)

    # Parity mode defaults: original timestamps, full metrics
    if args.parity_run_id:
        if args.shift_to_now is None:
            args.shift_to_now = False
        if args.retain_hours is None:
            args.retain_hours = 0.0
    else:
        if args.shift_to_now is None:
            args.shift_to_now = True
        if args.retain_hours is None:
            args.retain_hours = 4.5

    ids = args.uc or UCS
    packs = []
    for uc in ids:
        if args.parity_run_id:
            pack_dir = parity_pack_dir(uc, args.parity_run_id)
            if not pack_dir.is_dir():
                raise SystemExit(f"Missing parity pack: {pack_dir}")
            packs.append(_load_uc(uc, pack_dir=pack_dir))
        else:
            packs.append(_load_uc(uc))
    retain = None if args.retain_hours <= 0 else args.retain_hours

    if args.preview or (args.dry_run and not args.purge_stale):
        previews = []
        for uc in packs:
            shift = 0
            if args.shift_to_now:
                shift, _, _ = compute_shift_ms(
                    uc, end_offset_minutes=args.end_offset_minutes
                )
            previews.append(
                preview_samples(uc, shift_ms=shift, retain_hours=retain)
            )
        print(json.dumps({"mode": "preview" if args.preview else "dry_run", "ucs": previews}, indent=2))
        if args.preview and not args.dry_run:
            return 0
        if args.dry_run and not args.purge_stale:
            # still run push_uc dry paths below for summary file
            pass

    if not args.dry_run:
        if not args.user or not args.password:
            raise SystemExit(
                "Set OPENOBSERVE_USER and OPENOBSERVE_PASSWORD (or --user/--password)."
            )
        # Connectivity probe
        probe = args.base_url.rstrip("/") + "/"
        try:
            urllib.request.urlopen(probe, timeout=8)
        except Exception as e:
            raise SystemExit(
                f"OpenObserve unreachable at {args.base_url}: {e}\n"
                "This environment cannot route to 172.16.14.77. "
                "Run this script from a host on the Motadata LAN/VPN."
            ) from e

    auth = _auth(args.user, args.password) if not args.dry_run else ""
    base = args.base_url.rstrip("/")

    purge_result = None
    if args.purge_stale:
        purge_result = purge_stale_observeops_streams(
            base=base, org=args.org, auth=auth, dry_run=args.dry_run
        )
        print(json.dumps({"purge_stale": purge_result}, indent=2), file=sys.stderr)
        if not args.dry_run:
            # OO deletes streams asynchronously; ingesting into a stream mid-delete
            # returns HTTP 400 "stream is being deleted".
            wait_s = int(os.environ.get("OO_PURGE_WAIT_SECONDS", "90"))
            print(
                f"Waiting {wait_s}s for OO stream deletion to settle…",
                file=sys.stderr,
            )
            time.sleep(wait_s)

    results = [
        push_uc(
            uc,
            base=base,
            org=args.org,
            auth=auth,
            dry_run=args.dry_run,
            batch=args.batch,
            shift_to_now=args.shift_to_now,
            end_offset_minutes=args.end_offset_minutes,
            retain_hours=retain,
        )
        for uc in packs
    ]
    summary = {
        "base_url": base,
        "org": args.org,
        "dry_run": args.dry_run,
        "parity_run_id": args.parity_run_id,
        "shift_to_now": args.shift_to_now,
        "retain_hours": retain,
        "purge_stale": purge_result,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "totals": {
            "logs": sum(r["logs"]["count"] for r in results),
            "metrics": sum(r["metrics"]["count"] for r in results),
            "spans": sum(r["traces"]["span_count"] for r in results),
        },
        "note": (
            "Parity mode: loads lean parity_corpus (same shared-detect inputs as "
            "Lean/Fed), original timestamps, full metric series. "
            "OO streams: observeops_uc_uc1..uc5 (logs); metrics via ingest/metrics/_json. "
            "Filter by uc_id / corpus=observeops / parity_input=true around 2026-07-10."
            if args.parity_run_id
            else (
                "OO streams: observeops_uc_uc1..uc5; filter by uc_id / corpus=observeops."
            )
        ),
    }
    # Enrich per-UC with pack path + no-shift confirmation
    for r, uc in zip(results, packs):
        r["pack_dir"] = uc.get("pack_dir")
        r["shift_ms"] = (
            r.get("time_shift", {}).get("shift_ms", 0) if args.shift_to_now else 0
        )

    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {args.out_summary}", file=sys.stderr)
    if not args.dry_run and any(not r.get("ok", True) for r in results):
        failed = [r["uc_id"] for r in results if not r.get("ok", True)]
        print(f"Push incomplete for: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
