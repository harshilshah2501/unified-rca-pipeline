#!/usr/bin/env python3
"""N5 — Lean bundle writer from F1 detect artifacts (+ topology / GT / events).

Produces an ObserveOps-shaped UC directory consumable by ``lean_rca diagnose``
via ``OBSERVEOPS_CORPUS=<parent>``.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def _events_from_stream(stream: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not stream.is_file():
        return events
    for line in stream.open():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("signal_class") != "event":
            continue
        labels = row.get("labels") or {}
        severity = labels.get("severity") or labels.get("level") or "info"
        events.append(
            {
                "timestamp": row.get("ts"),
                "ci": row.get("ci_id"),
                "event_type": row.get("name") or "event",
                "severity": severity,
                "message": labels.get("message")
                or labels.get("body")
                or str(row.get("name") or "event"),
            }
        )
    return events


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_lean_bundle(
    *,
    f1_dir: Path,
    out_bundle: Path,
    uc_id: str,
    ground_truth_src: Path | None = None,
    events_src: Path | None = None,
    reference_corpus: Path | None = None,
) -> dict[str, Any]:
    """Write Lean-diagnoseable bundle directory."""
    t0 = time.perf_counter()
    f1_dir = f1_dir.resolve()
    out_bundle.mkdir(parents=True, exist_ok=True)

    anomalies_path = f1_dir / "anomalies.json"
    seed_path = f1_dir / "symptom_seed.json"
    topo_path = f1_dir / "topology.json"
    for required in (anomalies_path, seed_path, topo_path):
        if not required.is_file():
            raise FileNotFoundError(f"F1 dir missing {required.name}: {required}")

    anomalies = _load_json(anomalies_path)
    seed = _load_json(seed_path)
    topology = _load_json(topo_path)

    ref = reference_corpus or (REPO_ROOT / "datasets" / "observeops")
    gt_path = ground_truth_src or (ref / uc_id / "ground_truth.json")
    if not gt_path.is_file():
        raise FileNotFoundError(
            f"ground_truth.json required for diagnose load: {gt_path}"
        )
    ground_truth = _load_json(gt_path)

    # Prefer frozen events when present; else derive from lean/structural stream.
    ev_path = events_src or (ref / uc_id / "events.json")
    if ev_path.is_file():
        events_doc = _load_json(ev_path)
    else:
        stream = f1_dir / "lean" / "events.jsonl"
        if not stream.is_file():
            stream = f1_dir / "structural" / "stream.jsonl"
        events_doc = {"events": _events_from_stream(stream)}

    (out_bundle / "topology.json").write_text(json.dumps(topology, indent=2) + "\n")
    (out_bundle / "anomalies.json").write_text(json.dumps(anomalies, indent=2) + "\n")
    (out_bundle / "symptom_seed.json").write_text(json.dumps(seed, indent=2) + "\n")
    (out_bundle / "ground_truth.json").write_text(
        json.dumps(ground_truth, indent=2) + "\n"
    )
    (out_bundle / "events.json").write_text(json.dumps(events_doc, indent=2) + "\n")

    # Optional: copy detect meta for provenance
    for name in ("detect_meta.json", "run_meta.json"):
        src = f1_dir / name
        if src.is_file():
            shutil.copy2(src, out_bundle / name)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    meta = {
        "schema_version": "lean_bundle.v1",
        "writer": "lean_bundle_writer",
        "uc_id": uc_id,
        "f1_dir": str(f1_dir),
        "out_bundle": str(out_bundle),
        "anomaly_count": len(anomalies.get("anomalies") or []),
        "symptom_seed": seed,
        "ground_truth_root_ci": ground_truth.get("root_ci"),
        "event_count": len(events_doc.get("events") or []),
        "write_latency_ms": round(elapsed_ms, 3),
        "artifacts": [
            "topology.json",
            "anomalies.json",
            "symptom_seed.json",
            "ground_truth.json",
            "events.json",
            "bundle_meta.json",
        ],
    }
    (out_bundle / "bundle_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="N5 Lean bundle writer")
    parser.add_argument("--f1-dir", type=Path, required=True)
    parser.add_argument(
        "--uc-id",
        default=None,
        help="UC id (default: F1 dir name, e.g. UC-1)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Parent corpus dir (default: ingestion-poc/out/lean-bundles)",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Run lean_rca diagnose after write",
    )
    args = parser.parse_args(argv)

    f1 = args.f1_dir.resolve()
    uc_id = args.uc_id or f1.name
    parent = (
        args.out_dir.resolve()
        if args.out_dir
        else (REPO_ROOT / "ingestion-poc" / "out" / "lean-bundles")
    )
    out_bundle = parent / uc_id
    meta = write_lean_bundle(f1_dir=f1, out_bundle=out_bundle, uc_id=uc_id)
    print(json.dumps(meta, indent=2))
    print(f"\nN5 OK → {out_bundle}")

    if args.diagnose:
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env["OBSERVEOPS_CORPUS"] = str(parent)
        env["PYTHONPATH"] = f"{REPO_ROOT / 'lean-pipeline'}:{REPO_ROOT}"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "lean_rca",
                "diagnose",
                uc_id,
                "--format",
                "json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        print(proc.stdout)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return proc.returncode
        verdict = json.loads(proc.stdout)
        root = verdict.get("root_ci")
        expected = meta["ground_truth_root_ci"]
        print(f"diagnose root_ci={root} expected={expected} match={root == expected}")
        if root != expected:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
