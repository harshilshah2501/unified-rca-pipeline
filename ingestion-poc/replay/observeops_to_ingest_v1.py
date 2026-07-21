#!/usr/bin/env python3
"""Convert ObserveOps UC bundles to ingest.v1 JSONL for Vector replay.

Emits:
  - metric_sample  (one line per metric point)
  - anomaly        (optional: points that exceed threshold)
  - event          (from events.json)

Also copies topology.json + ground_truth.json (+ optional seed/anomalies)
into the output incident directory for ingest PoC handoff.

See: docs/INGEST_DATA_FORMAT.md
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO / "datasets" / "observeops"
DEFAULT_OUT_ROOT = REPO / "datasets" / "ingest_samples" / "observeops-replay"

SEVERITY_MAP = {
    "critical": 1.0,
    "warning": 0.7,
    "info": 0.3,
    "ok": 0.0,
}


def _severity_from_threshold(value: float, threshold: float | None) -> float | None:
    if threshold is None or threshold == 0:
        return None
    return round(abs(value) / abs(threshold), 4)


def _ci_type(topology: dict, ci_id: str) -> str:
    for node in topology.get("nodes") or []:
        if node.get("id") == ci_id:
            return str(node.get("type") or "Unknown")
    return "Unknown"


def metric_rows(
    series: dict[str, Any],
    *,
    topology: dict,
    uc_id: str,
    emit_anomaly_rows: bool,
) -> list[dict[str, Any]]:
    ci = series["ci"]
    signal = series["signal"]
    threshold = series.get("threshold")
    threshold_f = float(threshold) if threshold is not None else None
    ci_type = _ci_type(topology, ci)
    rows: list[dict[str, Any]] = []
    for point in series.get("points") or []:
        value = float(point["value"])
        ts = point["timestamp"]
        sev = _severity_from_threshold(value, threshold_f)
        base = {
            "schema_version": "ingest.v1",
            "ts": ts,
            "tenant": "default",
            "ci_id": ci,
            "ci_type": ci_type,
            "signal_class": "metric_sample",
            "name": signal,
            "value": value,
            "threshold": threshold_f,
            "severity": sev,
            "labels": {
                "source": "observeops_replay",
                "uc_id": uc_id,
                "interval_minutes": series.get("interval_minutes"),
            },
        }
        rows.append(base)
        if (
            emit_anomaly_rows
            and threshold_f is not None
            and value > threshold_f
        ):
            anom = dict(base)
            anom["signal_class"] = "anomaly"
            anom["labels"] = {
                **base["labels"],
                "crossed": True,
            }
            rows.append(anom)
    return rows


def event_rows(
    events_doc: dict[str, Any],
    *,
    topology: dict,
    uc_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ev in events_doc.get("events") or []:
        ci = ev["ci"]
        sev_name = str(ev.get("severity") or "info").lower()
        rows.append(
            {
                "schema_version": "ingest.v1",
                "ts": ev["timestamp"],
                "tenant": "default",
                "ci_id": ci,
                "ci_type": _ci_type(topology, ci),
                "signal_class": "event",
                "name": ev.get("event_type") or "event",
                "value": 1.0,
                "threshold": None,
                "severity": SEVERITY_MAP.get(sev_name, 0.5),
                "labels": {
                    "source": "observeops_replay",
                    "uc_id": uc_id,
                    "severity_label": sev_name,
                    "message": ev.get("message"),
                },
            }
        )
    return rows


def convert_uc(
    uc_id: str,
    corpus: Path,
    out_root: Path,
    *,
    emit_anomaly_rows: bool = True,
    incident_window_only: bool = False,
) -> dict[str, Any]:
    uc_dir = corpus / uc_id
    if not uc_dir.is_dir():
        raise FileNotFoundError(uc_dir)

    topology = json.loads((uc_dir / "topology.json").read_text())
    seed = json.loads((uc_dir / "symptom_seed.json").read_text())
    anomalies = json.loads((uc_dir / "anomalies.json").read_text())
    incident_start = anomalies.get("incident_start") or seed.get("timestamp")

    rows: list[dict[str, Any]] = []
    metrics_dir = uc_dir / "metrics"
    series_count = 0
    if metrics_dir.is_dir():
        for path in sorted(metrics_dir.glob("*.json")):
            series = json.loads(path.read_text())
            series_count += 1
            rows.extend(
                metric_rows(
                    series,
                    topology=topology,
                    uc_id=uc_id,
                    emit_anomaly_rows=emit_anomaly_rows,
                )
            )

    events_path = uc_dir / "events.json"
    event_count = 0
    if events_path.exists():
        events_doc = json.loads(events_path.read_text())
        erows = event_rows(events_doc, topology=topology, uc_id=uc_id)
        event_count = len(erows)
        rows.extend(erows)

    if incident_window_only and incident_start:
        # Keep baseline day before incident_start through end (common UC pattern).
        # Filter to points on/after day of incident_start for denser incident replay.
        day = str(incident_start)[:10]
        rows = [r for r in rows if str(r["ts"])[:10] >= day]

    rows.sort(key=lambda r: (r["ts"], r["ci_id"], r["name"], r["signal_class"]))

    out_dir = out_root / uc_id
    out_dir.mkdir(parents=True, exist_ok=True)
    stream_path = out_dir / "stream.jsonl"
    with stream_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")

    for name in (
        "topology.json",
        "ground_truth.json",
        "symptom_seed.json",
        "anomalies.json",
    ):
        src = uc_dir / name
        if src.exists():
            shutil.copy2(src, out_dir / name)

    # Lightweight topo_update audit lines (one per edge) at incident_start.
    topo_path = out_dir / "topo_updates.jsonl"
    with topo_path.open("w", encoding="utf-8") as fh:
        for edge in topology.get("edges") or []:
            line = {
                "schema_version": "ingest.v1",
                "ts": incident_start or "1970-01-01T00:00:00Z",
                "tenant": "default",
                "ci_id": edge.get("from"),
                "ci_type": _ci_type(topology, edge.get("from", "")),
                "signal_class": "topo_update",
                "name": edge.get("relation") or "edge",
                "value": 1.0,
                "threshold": None,
                "severity": 1.0,
                "labels": {
                    "source": "observeops_replay",
                    "uc_id": uc_id,
                    "from": edge.get("from"),
                    "to": edge.get("to"),
                    "relation": edge.get("relation"),
                },
            }
            fh.write(json.dumps(line, separators=(",", ":")) + "\n")

    manifest = {
        "uc_id": uc_id,
        "schema_version": "ingest.v1",
        "source_corpus": str(corpus),
        "stream_file": "stream.jsonl",
        "stream_lines": len(rows),
        "metric_series_files": series_count,
        "event_lines": event_count,
        "emit_anomaly_rows": emit_anomaly_rows,
        "incident_window_only": incident_window_only,
        "incident_start": incident_start,
        "symptom_seed": seed,
        "ground_truth_root_ci": json.loads(
            (uc_dir / "ground_truth.json").read_text()
        ).get("root_ci"),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert ObserveOps UC-* to ingest.v1 JSONL"
    )
    parser.add_argument("--uc", help="Single UC e.g. UC-1")
    parser.add_argument("--all", action="store_true", help="Convert UC-1..UC-5")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="ObserveOps corpus root",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_OUT_ROOT,
        help="Output root for ingest samples",
    )
    parser.add_argument(
        "--no-anomaly-rows",
        action="store_true",
        help="Do not emit signal_class=anomaly duplicates for crossings",
    )
    parser.add_argument(
        "--incident-day-only",
        action="store_true",
        help="Keep only points on/after the incident calendar day",
    )
    args = parser.parse_args(argv)

    if args.all:
        ucs = [f"UC-{i}" for i in range(1, 6)]
    elif args.uc:
        ucs = [args.uc]
    else:
        parser.error("Specify --uc UC-N or --all")
        return 1

    out_root = args.out_root.resolve()
    corpus = args.corpus.resolve()
    summaries = []
    for uc in ucs:
        m = convert_uc(
            uc,
            corpus,
            out_root,
            emit_anomaly_rows=not args.no_anomaly_rows,
            incident_window_only=args.incident_day_only,
        )
        summaries.append(m)
        print(
            f"{uc}: lines={m['stream_lines']} "
            f"series={m['metric_series_files']} events={m['event_lines']} "
            f"→ {out_root / uc / 'stream.jsonl'}"
        )

    index = {
        "schema_version": "ingest_samples.v1",
        "suite": "observeops-replay",
        "ucs": summaries,
    }
    (out_root / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(f"Wrote index → {out_root / 'index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
