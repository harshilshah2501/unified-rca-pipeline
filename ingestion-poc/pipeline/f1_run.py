#!/usr/bin/env python3
"""N3 F1 smoke: ingest.v1 stream → structural/lean/speed sinks + shared detect.

Default path uses a Python sink writer (always available). Optional ``--vector``
runs timberio/vector via Docker against ``vector.f1-smoke.toml``, then detect.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ingestion-poc" / "detect"))

from threshold_detect import detect_from_ingest_jsonl, write_detect_artifacts  # noqa: E402

STRUCTURAL_CLASSES = {"metric_sample", "event", "trace_span", "anomaly"}
LEAN_CLASSES = {"metric_sample", "event", "anomaly"}
SPEED_CLASSES = {"event", "trace_span", "anomaly"}


def resolve_inputs(suite: str) -> tuple[Path, Path | None, str]:
    """Return (stream.jsonl, topology.json|None, suite_id)."""
    s = suite.strip()
    uc: str | None = None
    if s.upper() in {f"UC-{i}" for i in range(1, 6)}:
        uc = s.upper()
    elif s.isdigit() and 1 <= int(s) <= 5:
        uc = f"UC-{s}"
    elif s.upper().startswith("UC") and s[-1].isdigit():
        uc = f"UC-{s[-1]}"

    if uc:
        base = REPO_ROOT / "datasets" / "ingest_samples" / "observeops-replay" / uc
        stream = base / "stream.jsonl"
        topo = base / "topology.json"
        if not stream.is_file():
            raise FileNotFoundError(f"Missing stream: {stream}")
        return stream, topo if topo.is_file() else None, uc

    if s.lower() in {"motadata", "motadata-ingest", "motadata_smoke"}:
        stream = (
            REPO_ROOT
            / "datasets"
            / "ingest_samples"
            / "motadata-ingest"
            / "stream.jsonl"
        )
        if not stream.is_file():
            raise FileNotFoundError(
                f"Missing Motadata smoke stream: {stream} "
                "(run: python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke)"
            )
        return stream, None, "motadata-ingest"

    stream = Path(s).expanduser().resolve()
    if not stream.is_file():
        raise FileNotFoundError(f"Not a suite name or stream file: {suite}")
    return stream, None, stream.parent.name


def write_python_sinks(stream: Path, out_dir: Path) -> dict[str, int]:
    """Fan-out ingest.v1 lines into F1 sink files (Vector-equivalent)."""
    lean_path = out_dir / "lean" / "events.jsonl"
    structural_path = out_dir / "structural" / "stream.jsonl"
    speed_path = out_dir / "speed_tier" / "feed.jsonl"
    for p in (lean_path, structural_path, speed_path):
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            p.unlink()

    counts = {"total": 0, "lean": 0, "structural": 0, "speed": 0}
    with (
        stream.open() as src,
        lean_path.open("w") as lean_fh,
        structural_path.open("w") as struct_fh,
        speed_path.open("w") as speed_fh,
    ):
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            counts["total"] += 1
            cls = row.get("fact_kind")
            encoded = json.dumps(row, separators=(",", ":")) + "\n"
            if cls in LEAN_CLASSES:
                lean_fh.write(encoded)
                counts["lean"] += 1
            if cls in STRUCTURAL_CLASSES:
                struct_fh.write(encoded)
                counts["structural"] += 1
            if cls in SPEED_CLASSES:
                speed_fh.write(encoded)
                counts["speed"] += 1
    return counts


def count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open() as fh:
        return sum(1 for line in fh if line.strip())


def run_vector_docker(stream: Path, out_dir: Path, timeout_s: int = 25) -> dict[str, Any]:
    """Run Vector F1 config via Docker; timeout expected (file source stays open)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / ".vector-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("lean", "structural", "speed_tier"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
        # Clear prior sink files
        for old in (out_dir / sub).glob("*.jsonl"):
            old.unlink()

    image = os.environ.get("VECTOR_IMAGE", "timberio/vector:0.41.1-alpine")
    rel_stream = stream.relative_to(REPO_ROOT).as_posix()
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{REPO_ROOT}:/workspace:ro",
        "-v",
        f"{REPO_ROOT / 'ingestion-poc' / 'vector'}:/etc/vector:ro",
        "-v",
        f"{out_dir}:/out",
        "-e",
        f"INGEST_STREAM=/workspace/{rel_stream}",
        "-e",
        "F1_OUT_DIR=/out",
        "-e",
        "VECTOR_DATA_DIR=/out/.vector-data",
        image,
        "--config",
        "/etc/vector/vector.f1-smoke.toml",
    ]
    t0 = time.perf_counter()
    timed_out = False
    rc = -1
    stdout = ""
    stderr = ""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        rc = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = 0
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    structural = out_dir / "structural" / "stream.jsonl"
    # Vector file sink may use date templates; our config uses fixed paths.
    if not structural.is_file() or structural.stat().st_size == 0:
        raise RuntimeError(
            "Vector run produced no structural sink output.\n"
            f"rc={rc} timed_out={timed_out}\n"
            f"stdout:\n{stdout[-2000:]}\nstderr:\n{stderr[-2000:]}"
        )

    return {
        "engine": "vector_docker",
        "image": image,
        "timed_out_ok": timed_out,
        "returncode": rc,
        "vector_wall_ms": round(elapsed_ms, 3),
    }


def run_f1(
    suite: str,
    out_dir: Path,
    *,
    use_vector: bool = False,
    empty_ok: bool | None = None,
    changes_path: Path | None = None,
    change_window_minutes: int = 30,
) -> dict[str, Any]:
    stream, topo, suite_id = resolve_inputs(suite)
    if empty_ok is None:
        empty_ok = suite_id == "motadata-ingest"

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    t0 = time.perf_counter()
    if use_vector:
        sink_meta = run_vector_docker(stream, out_dir)
        sink_counts = {
            "total": count_lines(stream),
            "lean": count_lines(out_dir / "lean" / "events.jsonl"),
            "structural": count_lines(out_dir / "structural" / "stream.jsonl"),
            "speed": count_lines(out_dir / "speed_tier" / "feed.jsonl"),
        }
    else:
        sink_counts = write_python_sinks(stream, out_dir)
        sink_meta = {"engine": "python_fanout", "vector_wall_ms": None}

    result = detect_from_ingest_jsonl(stream, empty_ok=empty_ok)
    write_detect_artifacts(
        result,
        out_dir,
        changes_path=changes_path,
        change_window_minutes=change_window_minutes,
    )

    if topo is not None:
        shutil.copy2(topo, out_dir / "topology.json")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    run_meta: dict[str, Any] = {
        "schema_version": "f1_smoke.v1",
        "suite_id": suite_id,
        "profile": "F1",
        "stream": str(stream),
        "out_dir": str(out_dir),
        "sink_engine": sink_meta.get("engine"),
        "sink_meta": sink_meta,
        "sink_counts": sink_counts,
        "detect": result.to_meta(),
        "anomaly_count": len(result.anomalies.get("anomalies") or []),
        "by_anomaly_class": result.by_anomaly_class,
        "symptom_seed": result.symptom_seed,
        "change_context": result.change_context,
        "topology_copied": topo is not None,
        "total_wall_ms": round(elapsed_ms, 3),
        "note": (
            "F1 sinks = lean + structural + speed_tier; "
            "detect = shared threshold on metric_sample rows "
            "(D3 anomaly_class; optional D2 change feed)"
        ),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2) + "\n")
    return run_meta


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="N3 F1 smoke: stream → sinks + detect")
    parser.add_argument(
        "--suite",
        default="UC-1",
        help="UC-1..UC-5 | motadata | or path to stream.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: ingestion-poc/out/f1-smoke/<suite>)",
    )
    parser.add_argument(
        "--vector",
        action="store_true",
        help="Use Docker Vector for sinks (else Python fan-out)",
    )
    parser.add_argument(
        "--empty-ok",
        action="store_true",
        help="Allow zero threshold crossings",
    )
    parser.add_argument(
        "--changes",
        type=Path,
        default=None,
        help="D2 change feed JSON/JSONL for change-near-onset",
    )
    parser.add_argument(
        "--change-window-minutes",
        type=int,
        default=30,
    )
    args = parser.parse_args(argv)

    suite = args.suite
    out = args.out_dir
    if out is None:
        _, _, suite_id = resolve_inputs(suite)
        out = REPO_ROOT / "ingestion-poc" / "out" / "f1-smoke" / suite_id

    meta = run_f1(
        suite,
        out.resolve(),
        use_vector=args.vector,
        empty_ok=True if args.empty_ok else None,
        changes_path=args.changes.resolve() if args.changes else None,
        change_window_minutes=args.change_window_minutes,
    )
    print(json.dumps(meta, indent=2))
    print(f"\nF1 smoke OK → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
