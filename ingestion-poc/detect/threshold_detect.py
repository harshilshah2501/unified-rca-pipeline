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

    def to_meta(self) -> dict[str, Any]:
        return {
            "detect_source": self.detect_source,
            "pipeline_profile": self.pipeline_profile,
            "detect_latency_ms": round(self.detect_latency_ms, 4),
            "points_scanned": self.points_scanned,
            "series_scanned": self.series_scanned,
        }


def _load_metric_series(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


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

    # Collapse to one anomaly row per (ci, signal): latest crossing in that series.
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
    if not anomalies_list:
        raise ValueError(f"No threshold crossings found in {metrics_dir}")

    incident_start = anomalies_list[0]["timestamp"]
    # Symptom seed = chronologically last crossing (downstream symptom convention).
    seed_row = anomalies_list[-1]
    symptom_seed = {
        "ci": seed_row["ci"],
        "signal": seed_row["signal"],
        "timestamp": seed_row["timestamp"],
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
        series_scanned=len(series_files),
    )


def detect_uc(uc_dir: Path) -> DetectResult:
    """Detect for one ObserveOps UC directory (expects metrics/)."""
    metrics_dir = uc_dir / "metrics"
    if not metrics_dir.is_dir():
        raise FileNotFoundError(f"Missing metrics dir: {metrics_dir}")
    return detect_from_metrics_dir(metrics_dir)


def write_detect_artifacts(result: DetectResult, out_dir: Path) -> None:
    """Write Lean-shaped anomalies.json + symptom_seed.json (+ detect_meta.json)."""
    out_dir.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument(
        "--uc-dir",
        type=Path,
        required=True,
        help="UC directory containing metrics/",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Optional directory to write anomalies.json + symptom_seed.json",
    )
    args = parser.parse_args(argv)
    result = detect_uc(args.uc_dir.resolve())
    print(
        f"detect_source={result.detect_source} "
        f"series={result.series_scanned} points={result.points_scanned} "
        f"anomalies={len(result.anomalies['anomalies'])} "
        f"seed={result.symptom_seed['ci']}/{result.symptom_seed['signal']} "
        f"detect_latency_ms={result.detect_latency_ms:.3f}"
    )
    if args.out_dir:
        write_detect_artifacts(result, args.out_dir.resolve())
        print(f"wrote {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
