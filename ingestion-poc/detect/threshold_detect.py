"""Shared threshold detector — fair front door for Lean and Federated.

Scans ObserveOps-style metrics/*.json series, marks threshold crossings,
emits anomalies + symptom_seed (Lean bundle shape) and timing metadata.

This is Profile A (parity-shared-detect), not Panorama.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DetectResult:
    anomalies: dict[str, Any]
    symptom_seed: dict[str, Any]
    detect_latency_ms: float
    points_scanned: int
    series_scanned: int
    detect_source: str = "shared_threshold"
    pipeline_profile: str = "parity-shared-detect"
    by_anomaly_class: dict[str, int] | None = None
    change_context: dict[str, Any] | None = None

    def to_meta(self) -> dict[str, Any]:
        meta = {
            "detect_source": self.detect_source,
            "pipeline_profile": self.pipeline_profile,
            "detect_latency_ms": round(self.detect_latency_ms, 4),
            "points_scanned": self.points_scanned,
            "series_scanned": self.series_scanned,
        }
        if self.by_anomaly_class is not None:
            meta["by_anomaly_class"] = self.by_anomaly_class
        if self.change_context is not None:
            meta["change_near_onset"] = self.change_context.get("change_near_onset")
            meta["change_count_in_window"] = self.change_context.get(
                "change_count_in_window"
            )
        return meta


def classify_anomaly_class(signal: str) -> str:
    """D3 — map signal name to an explicit anomaly class (distinct from latency)."""
    s = (signal or "").lower()
    if any(
        tok in s
        for tok in (
            "error_rate",
            "error.rate",
            "http.error",
            "5xx",
            "fail_rate",
            "failure_rate",
        )
    ):
        return "error_rate"
    if any(
        tok in s
        for tok in (
            "latency",
            "p95",
            "p99",
            "response_time",
            "duration",
            "rtt",
        )
    ):
        return "performance"
    if any(
        tok in s
        for tok in (
            "cpu",
            "mem",
            "memory",
            "disk",
            "iops",
            "ready",
            "load",
            "usage",
            "filesystem",
            "used_pct",
            "oom",
        )
    ):
        return "resource"
    if any(tok in s for tok in ("link", "ifoper", "packet", "discard", "bandwidth")):
        return "network"
    return "threshold"


def _load_metric_series(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _result_from_crossings(
    crossed: list[dict[str, Any]],
    *,
    points_scanned: int,
    series_scanned: int,
    t0: float,
    empty_ok: bool = False,
    empty_context: str = "",
) -> DetectResult:
    """Collapse crossings to latest per (ci, signal) and build DetectResult."""
    latest_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in crossed:
        key = (row["ci"], row["signal"])
        prev = latest_by_key.get(key)
        if prev is None or row["timestamp"] > prev["timestamp"]:
            latest_by_key[key] = row

    anomalies_list = sorted(
        latest_by_key.values(),
        key=lambda r: (r["timestamp"], r["ci"], r["signal"]),
    )
    # D3: stamp anomaly_class on every retained crossing
    by_class: dict[str, int] = {}
    for row in anomalies_list:
        cls = classify_anomaly_class(str(row.get("signal") or ""))
        row["anomaly_class"] = cls
        by_class[cls] = by_class.get(cls, 0) + 1

    if not anomalies_list:
        if empty_ok:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return DetectResult(
                anomalies={"incident_start": None, "anomalies": []},
                symptom_seed={},
                detect_latency_ms=elapsed_ms,
                points_scanned=points_scanned,
                series_scanned=series_scanned,
                by_anomaly_class={},
            )
        raise ValueError(f"No threshold crossings found{empty_context}")

    incident_start = anomalies_list[0]["timestamp"]
    # Symptom seed = chronologically last crossing (downstream symptom convention).
    seed_row = anomalies_list[-1]
    symptom_seed = {
        "ci": seed_row["ci"],
        "signal": seed_row["signal"],
        "timestamp": seed_row["timestamp"],
        "anomaly_class": seed_row.get("anomaly_class"),
    }
    anomalies = {
        "incident_start": incident_start,
        "anomalies": anomalies_list,
    }
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return DetectResult(
        anomalies=anomalies,
        symptom_seed=symptom_seed,
        detect_latency_ms=elapsed_ms,
        points_scanned=points_scanned,
        series_scanned=series_scanned,
        by_anomaly_class=by_class,
    )


def detect_from_metrics_dir(metrics_dir: Path) -> DetectResult:
    """Run threshold detect over all `*.json` metric series in a directory."""
    t0 = time.perf_counter()
    crossed: list[dict[str, Any]] = []
    points_scanned = 0
    series_files = sorted(metrics_dir.glob("*.json")) if metrics_dir.is_dir() else []

    for path in series_files:
        series = _load_metric_series(path)
        ci = series["ci"]
        signal = series["signal"]
        threshold = float(series["threshold"])
        for point in series.get("points") or []:
            points_scanned += 1
            value = float(point["value"])
            if value > threshold:
                crossed.append(
                    {
                        "ci": ci,
                        "signal": signal,
                        "value": value,
                        "threshold": threshold,
                        "crossed": True,
                        "timestamp": point["timestamp"],
                    }
                )

    return _result_from_crossings(
        crossed,
        points_scanned=points_scanned,
        series_scanned=len(series_files),
        t0=t0,
        empty_context=f" in {metrics_dir}",
    )


def detect_from_ingest_jsonl(
    stream_path: Path,
    *,
    empty_ok: bool = False,
) -> DetectResult:
    """Run threshold detect over `ingest.v1` JSONL (`metric_sample` rows with threshold).

    Ignores pre-baked `signal_class: anomaly` rows so detect is recomputed from samples.
    """
    t0 = time.perf_counter()
    crossed: list[dict[str, Any]] = []
    points_scanned = 0
    series_keys: set[tuple[str, str]] = set()

    with stream_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("signal_class") != "metric_sample":
                continue
            threshold = row.get("threshold")
            if threshold is None:
                continue
            value = row.get("value")
            if value is None:
                continue
            points_scanned += 1
            ci = str(row["ci_id"])
            signal = str(row["name"])
            series_keys.add((ci, signal))
            if float(value) > float(threshold):
                crossed.append(
                    {
                        "ci": ci,
                        "signal": signal,
                        "value": float(value),
                        "threshold": float(threshold),
                        "crossed": True,
                        "timestamp": row["ts"],
                    }
                )

    return _result_from_crossings(
        crossed,
        points_scanned=points_scanned,
        series_scanned=len(series_keys),
        t0=t0,
        empty_ok=empty_ok,
        empty_context=f" in {stream_path}",
    )


def detect_uc(uc_dir: Path) -> DetectResult:
    """Detect for one ObserveOps UC directory (expects metrics/)."""
    metrics_dir = uc_dir / "metrics"
    if not metrics_dir.is_dir():
        raise FileNotFoundError(f"Missing metrics dir: {metrics_dir}")
    return detect_from_metrics_dir(metrics_dir)


def write_detect_artifacts(
    result: DetectResult,
    out_dir: Path,
    *,
    changes_path: Path | None = None,
    change_window_minutes: int = 30,
) -> None:
    """Write Lean-shaped anomalies.json + symptom_seed.json (+ detect_meta / change_context)."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if changes_path is not None:
        from change_near_onset import (
            change_near_onset,
            load_changes,
            write_change_context,
        )

        changes = load_changes(changes_path)
        ctx = change_near_onset(
            incident_start=result.anomalies.get("incident_start"),
            changes=changes,
            window_minutes=change_window_minutes,
        )
        result.change_context = ctx
        if result.symptom_seed:
            result.symptom_seed = {
                **result.symptom_seed,
                "change_near_onset": ctx["change_near_onset"],
                "change_count_in_window": ctx["change_count_in_window"],
            }
        write_change_context(ctx, out_dir)

    (out_dir / "anomalies.json").write_text(
        json.dumps(result.anomalies, indent=2) + "\n"
    )
    (out_dir / "symptom_seed.json").write_text(
        json.dumps(result.symptom_seed, indent=2) + "\n"
    )
    (out_dir / "detect_meta.json").write_text(
        json.dumps(result.to_meta(), indent=2) + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Shared threshold detector (parity front door)")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--uc-dir",
        type=Path,
        help="UC directory containing metrics/",
    )
    src.add_argument(
        "--ingest-jsonl",
        type=Path,
        help="ingest.v1 JSONL stream (metric_sample rows)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Optional directory to write anomalies.json + symptom_seed.json",
    )
    parser.add_argument(
        "--empty-ok",
        action="store_true",
        help="Allow zero crossings (Motadata smoke without thresholds)",
    )
    parser.add_argument(
        "--changes",
        type=Path,
        help="D2: change feed JSON/JSONL (deploy/config) for change-near-onset",
    )
    parser.add_argument(
        "--change-window-minutes",
        type=int,
        default=30,
        help="D2: minutes before incident_start to search for changes",
    )
    args = parser.parse_args(argv)
    if args.uc_dir:
        result = detect_uc(args.uc_dir.resolve())
    else:
        result = detect_from_ingest_jsonl(
            args.ingest_jsonl.resolve(), empty_ok=args.empty_ok
        )
    seed = result.symptom_seed
    seed_s = (
        f"{seed.get('ci')}/{seed.get('signal')}" if seed else "(none)"
    )
    classes = result.by_anomaly_class or {}
    print(
        f"detect_source={result.detect_source} "
        f"series={result.series_scanned} points={result.points_scanned} "
        f"anomalies={len(result.anomalies['anomalies'])} "
        f"by_class={classes} "
        f"seed={seed_s} "
        f"detect_latency_ms={result.detect_latency_ms:.3f}"
    )
    if args.out_dir:
        write_detect_artifacts(
            result,
            args.out_dir.resolve(),
            changes_path=args.changes.resolve() if args.changes else None,
            change_window_minutes=args.change_window_minutes,
        )
        if result.change_context is not None:
            print(
                f"change_near_onset={result.change_context['change_near_onset']} "
                f"in_window={result.change_context['change_count_in_window']}"
            )
        print(f"wrote {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
