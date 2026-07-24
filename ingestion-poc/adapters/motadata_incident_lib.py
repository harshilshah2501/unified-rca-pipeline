"""Shared helpers for Motadata multi-incident Localize packs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ingestion-poc" / "adapters"))
sys.path.insert(0, str(REPO / "ingestion-poc" / "detect"))

from motadata_to_ingest_v1 import (  # noqa: E402
    convert_metric_numeric,
    load_ci_bind,
    load_threshold_catalog,
)
from threshold_detect import DetectResult, detect_from_ingest_jsonl, write_detect_artifacts  # noqa: E402

OUT_ROOT = REPO / "datasets" / "ingest_samples" / "motadata-ingest"
INCIDENTS = OUT_ROOT / "incidents"
METRIC_NUMERIC = REPO / "datasets" / "ingest_samples" / "jsonl_resolved" / "metric_numeric.jsonl"


def host_topology(ci_id: str, *, source: str, note: str) -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "source": source,
        "nodes": [{"id": ci_id, "type": "Host", "name": ci_id}],
        "edges": [],
        "note": note,
    }


def extract_monitor_metric_stream(
    monitor_id: int,
    *,
    metric_names: Iterable[str] | None = None,
    bind: dict[str, dict[str, Any]] | None = None,
    catalog: dict[str, Any] | None = None,
    src: Path = METRIC_NUMERIC,
    max_rows: int | None = None,
) -> list[dict[str, Any]]:
    """Convert Motadata numeric rows for one monitor into ingest.v1 samples."""
    names = set(metric_names) if metric_names is not None else None
    bind = bind if bind is not None else load_ci_bind(OUT_ROOT / "ci_bind.json")
    catalog = catalog if catalog is not None else load_threshold_catalog(None)
    out: list[dict[str, Any]] = []
    with src.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("id") != monitor_id:
                continue
            if names is not None:
                fields = row.get("fields") or {}
                filtered = {k: v for k, v in fields.items() if k in names}
                if not filtered:
                    continue
                row = {**row, "fields": filtered}
            out.extend(convert_metric_numeric(row, bind=bind, catalog=catalog))
            if max_rows is not None and len(out) >= max_rows:
                break
    out.sort(key=lambda r: (r.get("ts") or "", r.get("name") or ""))
    return out


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")


def prefer_seed(
    result: DetectResult,
    *,
    ci: str | None = None,
    signals: Iterable[str] | None = None,
) -> DetectResult:
    """Bias symptom_seed toward a preferred CI/signal when present."""
    anoms = list(result.anomalies.get("anomalies") or [])
    preferred = anoms
    if ci is not None:
        preferred = [a for a in preferred if a.get("ci") == ci]
    if signals is not None:
        sigs = set(signals)
        preferred = [a for a in preferred if a.get("signal") in sigs] or preferred
    if preferred:
        seed = preferred[-1]
        result.symptom_seed = {
            "ci": seed["ci"],
            "signal": seed["signal"],
            "timestamp": seed["timestamp"],
            "anomaly_class": seed.get("anomaly_class"),
        }
    return result


def write_incident_pack(
    incident_id: str,
    *,
    stream_rows: list[dict[str, Any]],
    topology: dict[str, Any],
    ground_truth: dict[str, Any],
    detect: DetectResult,
) -> Path:
    dest = INCIDENTS / incident_id
    dest.mkdir(parents=True, exist_ok=True)
    write_detect_artifacts(detect, dest)
    (dest / "topology.json").write_text(json.dumps(topology, indent=2) + "\n")
    (dest / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2) + "\n")
    (dest / "events.json").write_text(json.dumps({"events": []}, indent=2) + "\n")
    write_jsonl(dest / "stream.jsonl", stream_rows)
    meta = {
        "incident_id": incident_id,
        "anomaly_count": len(detect.anomalies.get("anomalies") or []),
        "by_anomaly_class": detect.by_anomaly_class,
        "symptom_seed": detect.symptom_seed,
        "ground_truth_root_ci": ground_truth.get("root_ci"),
        "ground_truth_signature": ground_truth.get("signature"),
        "detect": detect.to_meta(),
        "stream_rows": len(stream_rows),
    }
    (dest / "incident_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return dest


def lean_diagnose(incident_id: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["OBSERVEOPS_CORPUS"] = str(INCIDENTS)
    env["PYTHONPATH"] = f"{REPO / 'lean-pipeline'}:{REPO}"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "lean_rca",
            "diagnose",
            incident_id,
            "--format",
            "json",
        ],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"diagnose failed for {incident_id}:\n{proc.stderr}\n{proc.stdout}"
        )
    return json.loads(proc.stdout)
