#!/usr/bin/env python3
"""M2 cost harness — L0 (Lean-only) vs F1 (dual-sink) on identical replay.

Fairness: same host, same JSONL bytes; only sink fan-out changes.
Outputs: ``benchmarking/results/costing/<run_id>/{cost_report.json,cost_report.md}``

```bash
# Local smoke
python3 ingestion-poc/lab/run_cost_harness.py --events 100000

# pro6000 (headline)
python3 ingestion-poc/lab/run_cost_harness.py --events 500000 --vector --seconds-soak 120
```
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
COSTING = REPO / "benchmarking" / "results" / "costing"
VECTOR_DIR = REPO / "ingestion-poc" / "vector"

sys.path.insert(0, str(LAB))
sys.path.insert(0, str(REPO / "ingestion-poc" / "pipeline"))

from f1_run import (  # noqa: E402
    LEAN_CLASSES,
    SPEED_CLASSES,
    STRUCTURAL_CLASSES,
    count_lines,
)
from host_check import host_profile  # noqa: E402
from vector_replay_eps import write_synthetic_stream  # noqa: E402


def _now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_l0_sinks(stream: Path, out_dir: Path) -> dict[str, int]:
    """Lean-only fan-out (profile L0)."""
    lean_path = out_dir / "lean" / "events.jsonl"
    lean_path.parent.mkdir(parents=True, exist_ok=True)
    if lean_path.exists():
        lean_path.unlink()
    counts = {"total": 0, "lean": 0, "structural": 0, "speed": 0}
    with stream.open() as src, lean_path.open("w") as lean_fh:
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            counts["total"] += 1
            if row.get("signal_class") in LEAN_CLASSES:
                lean_fh.write(json.dumps(row, separators=(",", ":")) + "\n")
                counts["lean"] += 1
    return counts


def write_f1_sinks(stream: Path, out_dir: Path) -> dict[str, int]:
    """Full F1 fan-out (lean + structural + speed)."""
    from f1_run import write_python_sinks

    return write_python_sinks(stream, out_dir)


def _dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and ".vector-data" not in p.parts:
            total += p.stat().st_size
    return total


def _cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return float(usage.ru_utime + usage.ru_stime)


def run_python_profile(
    *,
    profile: str,
    stream: Path,
    out_dir: Path,
) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    cpu0 = _cpu_seconds()
    t0 = time.perf_counter()
    if profile == "L0":
        counts = write_l0_sinks(stream, out_dir)
    else:
        counts = write_f1_sinks(stream, out_dir)
    wall = time.perf_counter() - t0
    cpu = _cpu_seconds() - cpu0

    sink_bytes = _dir_bytes(out_dir)
    events = int(counts.get("total") or 0)
    eps = events / wall if wall > 0 else 0.0
    gb_day = (sink_bytes / wall) * 86400 / 1e9 if wall > 0 else 0.0
    return {
        "profile": profile,
        "engine": "python_fanout",
        "events": events,
        "sink_counts": counts,
        "elapsed_s": round(wall, 4),
        "eps": round(eps, 2),
        "cpu_seconds": round(cpu, 4),
        "cpu_seconds_per_1m_events": round(cpu / events * 1_000_000, 4) if events else None,
        "sink_bytes": sink_bytes,
        "gb_per_day_extrapolated": round(gb_day, 4),
        "mean_ingest_ms": round((wall / events) * 1000, 4) if events else None,
        "p99_ingest_ms": None,
        "p99_note": "Python fan-out is bulk file write; p99 not instrumented (see Dragonfly soak)",
        "out_dir": str(out_dir),
    }


def _docker_rm_tree(path: Path) -> None:
    """Remove a directory that may contain root-owned Vector outputs."""
    if not path.exists():
        return
    parent = path.parent.resolve()
    name = path.name
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{parent}:/parent",
            "alpine:3.20",
            "rm",
            "-rf",
            f"/parent/{name}",
        ],
        check=False,
        capture_output=True,
    )
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def _kill_cost_vector_containers() -> None:
    """Stop harness-named and any leftover Vector lab containers."""
    filters = [
        ["docker", "ps", "-aq", "--filter", "name=rca-cost"],
        ["docker", "ps", "-aq", "--filter", "ancestor=timberio/vector:0.41.1-alpine"],
    ]
    ids: list[str] = []
    for cmd in filters:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        ids.extend(x for x in (proc.stdout or "").split() if x)
    # unique preserve order
    seen: set[str] = set()
    uniq = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    if uniq:
        subprocess.run(["docker", "rm", "-f", *uniq], check=False, capture_output=True)


def run_vector_profile(
    *,
    profile: str,
    stream: Path,
    out_dir: Path,
    timeout_s: int = 90,
    events: int | None = None,
) -> dict[str, Any]:
    """Docker Vector sink write for L0 or F1.

    File sources stay open, so we start Vector in the background, wait until
    sink file sizes reach the input stream size (cheap), then stop the container.
    """
    _kill_cost_vector_containers()
    _docker_rm_tree(out_dir)
    out_dir.mkdir(parents=True)
    for sub in ("lean", "structural", "speed_tier"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    config = "vector.l0-smoke.toml" if profile == "L0" else "vector.f1-smoke.toml"
    image = os.environ.get("VECTOR_IMAGE", "timberio/vector:0.41.1-alpine")
    rel_stream = stream.resolve().relative_to(REPO).as_posix()
    name = f"rca-cost-{profile.lower()}-{os.getpid()}-{int(time.time())}"
    subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--entrypoint",
        "sh",
        "-v",
        f"{REPO}:/workspace:ro",
        "-v",
        f"{VECTOR_DIR}:/etc/vector:ro",
        "-v",
        f"{out_dir.resolve()}:/out",
        "-e",
        f"INGEST_STREAM=/workspace/{rel_stream}",
        "-e",
        "F1_OUT_DIR=/out",
        "-e",
        "VECTOR_DATA_DIR=/tmp/vector-data",
        image,
        "-c",
        f"mkdir -p /tmp/vector-data && exec vector --config /etc/vector/{config}",
    ]

    if events is None:
        events = count_lines(stream)
    stream_bytes = stream.stat().st_size
    # Synthetic compact re-encode ≈ same size; 90% is enough to declare complete.
    lean_target = int(stream_bytes * 0.90)
    struct_target = lean_target if profile == "F1" else 0

    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    done = False
    first_done_at: float | None = None
    lean_path = out_dir / "lean" / "events.jsonl"
    struct_path = out_dir / "structural" / "stream.jsonl"
    try:
        deadline = t0 + timeout_s
        while time.perf_counter() < deadline:
            lean_sz = lean_path.stat().st_size if lean_path.is_file() else 0
            struct_sz = struct_path.stat().st_size if struct_path.is_file() else 0
            if lean_sz >= lean_target and struct_sz >= struct_target:
                done = True
                first_done_at = time.perf_counter()
                time.sleep(0.15)
                break
            if proc.poll() is not None:
                if lean_sz >= lean_target and struct_sz >= struct_target:
                    done = True
                    first_done_at = time.perf_counter()
                break
            time.sleep(0.05)
        subprocess.run(["docker", "stop", "-t", "1", name], check=False, capture_output=True)
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)

    wall = (first_done_at - t0) if first_done_at else (time.perf_counter() - t0)
    if not lean_path.is_file() or lean_path.stat().st_size == 0:
        raise RuntimeError(
            f"Vector {profile} produced no lean sink.\n"
            f"done={done} wall={wall:.2f}s target={lean_target}"
        )

    counts = {
        "total": events,
        "lean": count_lines(lean_path),
        "structural": count_lines(out_dir / "structural" / "stream.jsonl"),
        "speed": count_lines(out_dir / "speed_tier" / "feed.jsonl"),
    }
    measured_events = counts["lean"] if counts["lean"] else events
    sink_bytes = _dir_bytes(out_dir)
    eps = measured_events / wall if wall > 0 else 0.0
    gb_day = (sink_bytes / wall) * 86400 / 1e9 if wall > 0 else 0.0
    return {
        "profile": profile,
        "engine": "vector_docker",
        "image": image,
        "config": config,
        "events": events,
        "events_written_lean": counts["lean"],
        "sink_counts": counts,
        "elapsed_s": round(wall, 4),
        "eps": round(eps, 2),
        "cpu_seconds": None,
        "cpu_seconds_per_1m_events": None,
        "sink_bytes": sink_bytes,
        "gb_per_day_extrapolated": round(gb_day, 4),
        "mean_ingest_ms": round((wall / measured_events) * 1000, 4) if measured_events else None,
        "p99_ingest_ms": None,
        "sinks_complete": done,
        "returncode": proc.returncode,
        "out_dir": str(out_dir),
        "note": (
            "Wall = time until lean(/structural) sink size ≥90% of stream; includes Vector startup"
            if done
            else "Stopped before size target — EPS may be understated"
        ),
    }


def run_dragonfly_soak(
    *,
    seconds: int,
    workers: int,
    port: int,
    threads: int,
    out_json: Path,
) -> dict[str, Any]:
    """Longer phase0 soak via existing lab runner helpers."""
    from run_lab_eps import ensure_dragonfly, run_phase0

    ensure_dragonfly(port, threads)
    result = run_phase0(
        port=port,
        workers=workers,
        pipeline=128,
        seconds=seconds,
        output=out_json,
    )
    return result


def render_md(doc: dict[str, Any]) -> str:
    host = doc.get("host") or {}
    rows = doc.get("profiles") or []
    soak = doc.get("dragonfly_soak")

    lines = [
        "# Cost report — L0 vs F1",
        "",
        f"**Run:** `{doc.get('run_id')}`  ",
        f"**Captured:** {doc.get('captured_at')}  ",
        f"**Host:** {host.get('hostname')} · {host.get('cpu_count')} CPU · "
        f"{(host.get('memory') or {}).get('total_gib') or host.get('mem_gib')} GiB · "
        f"tier {host.get('tier')}",
        "",
        "## Fairness contract",
        "",
        "- Identical replay JSONL for L0 and F1.",
        "- Only sink fan-out differs (L0 = lean; F1 = lean + structural + speed).",
        "- GB/day is **extrapolated** from sink write rate (not retention-backed).",
        "- Vector EPS includes container startup (conservative).",
        "",
        "## Profile comparison",
        "",
        "| Profile | Engine | Events | EPS | CPU-s / 1M evt | Sink bytes | GB/day (extrapolated) | Mean ingest ms |",
        "|---------|--------|--------|-----|----------------|------------|----------------------|----------------|",
    ]
    for r in rows:
        cpu1m = r.get("cpu_seconds_per_1m_events")
        cpu_s = f"{cpu1m:.2f}" if isinstance(cpu1m, (int, float)) else "—"
        mean = r.get("mean_ingest_ms")
        mean_s = f"{mean:.4f}" if isinstance(mean, (int, float)) else "—"
        lines.append(
            f"| {r.get('profile')} | {r.get('engine')} | {r.get('events')} | "
            f"{r.get('eps')} | {cpu_s} | {r.get('sink_bytes')} | "
            f"{r.get('gb_per_day_extrapolated')} | {mean_s} |"
        )

    if soak:
        lines += [
            "",
            "## Dragonfly soak (C_store speed-tier proxy)",
            "",
            f"- Sustained EPS: **{soak.get('eps')}**",
            f"- p99 write: **{soak.get('p99_ms')} ms**",
            f"- Duration: {soak.get('seconds')}s · workers={soak.get('workers')} · "
            f"proactor={soak.get('proactor_threads')}",
            f"- Artifact: `{soak.get('artifact')}`",
            "",
        ]

    # Delta L0 vs F1 (python preferred)
    py = [r for r in rows if r.get("engine") == "python_fanout"]
    if len(py) >= 2:
        by = {r["profile"]: r for r in py}
        if "L0" in by and "F1" in by:
            l0, f1 = by["L0"], by["F1"]
            eps_delta = (f1["eps"] / l0["eps"] - 1) * 100 if l0["eps"] else None
            byte_ratio = (
                f1["sink_bytes"] / l0["sink_bytes"] if l0["sink_bytes"] else None
            )
            lines += [
                "## L0 → F1 delta (Python fan-out)",
                "",
                f"- EPS change: **{eps_delta:+.1f}%**" if eps_delta is not None else "- EPS change: n/a",
                f"- Sink byte multiplier: **{byte_ratio:.2f}×**"
                if byte_ratio is not None
                else "- Sink byte multiplier: n/a",
                f"- Extra sinks: structural={STRUCTURAL_CLASSES}, speed={SPEED_CLASSES}",
                "",
            ]

    lines += [
        "## Notes",
        "",
        "- Headline ≥50K EPS gate is the **Dragonfly soak** (store path), not Vector/Python fan-out.",
        "- RCA accuracy is measured separately (UC / Motadata bakeoff); this report is ingest cost only.",
        "- Confidence: Python metrics = measured; GB/day = extrapolated; Vector EPS = measured wall incl. startup.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L0 vs F1 ingest cost harness")
    parser.add_argument("--events", type=int, default=200_000)
    parser.add_argument("--stream", type=Path, help="Existing ingest.v1 JSONL")
    parser.add_argument("--vector", action="store_true", help="Also run Docker Vector L0+F1")
    parser.add_argument("--vector-timeout", type=int, default=90)
    parser.add_argument(
        "--seconds-soak",
        type=int,
        default=0,
        help="If >0, run Dragonfly phase0 soak this many seconds",
    )
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--port", type=int, default=6380)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Default: benchmarking/results/costing/<run_id>",
    )
    args = parser.parse_args(argv)

    host = host_profile()
    knobs = host.get("recommended") or {}
    workers = args.workers or int(knobs.get("phase0_workers") or knobs.get("workers") or 4)
    threads = int(
        knobs.get("df_proactor_threads") or knobs.get("proactor_threads") or 2
    )
    run_id = args.run_id or f"cost-{host.get('hostname', 'host')}-{_now_id()}"
    out_root = args.out_dir or (COSTING / run_id)
    out_root.mkdir(parents=True, exist_ok=True)

    stream = args.stream
    if stream is None:
        stream = out_root / "replay_stream.jsonl"
        write_synthetic_stream(stream, args.events)
    else:
        stream = stream.resolve()

    profiles: list[dict[str, Any]] = []
    work = out_root / "work"
    work.mkdir(exist_ok=True)

    print(f"=== Python L0 ({stream.name}) ===")
    profiles.append(
        run_python_profile(profile="L0", stream=stream, out_dir=work / "py-L0")
    )
    print(json.dumps(profiles[-1], indent=2))

    print(f"=== Python F1 ===")
    profiles.append(
        run_python_profile(profile="F1", stream=stream, out_dir=work / "py-F1")
    )
    print(json.dumps(profiles[-1], indent=2))

    if args.vector:
        if not shutil.which("docker"):
            print("WARNING: --vector requested but docker not found; skipping")
        else:
            print("=== Vector L0 ===")
            profiles.append(
                run_vector_profile(
                    profile="L0",
                    stream=stream,
                    out_dir=work / "vec-L0",
                    timeout_s=args.vector_timeout,
                )
            )
            print(json.dumps(profiles[-1], indent=2))
            print("=== Vector F1 ===")
            profiles.append(
                run_vector_profile(
                    profile="F1",
                    stream=stream,
                    out_dir=work / "vec-F1",
                    timeout_s=args.vector_timeout,
                )
            )
            print(json.dumps(profiles[-1], indent=2))

    soak_doc = None
    if args.seconds_soak > 0:
        print(f"=== Dragonfly soak {args.seconds_soak}s ===")
        soak_path = out_root / "phase0_soak.json"
        try:
            raw = run_dragonfly_soak(
                seconds=args.seconds_soak,
                workers=workers,
                port=args.port,
                threads=threads,
                out_json=soak_path,
            )
            # run_phase0 returns dict-like from JSON
            if isinstance(raw, dict):
                soak_doc = {
                    "eps": raw.get("eps"),
                    "p99_ms": raw.get("p99_latency_ms") or raw.get("p99_ms"),
                    "seconds": args.seconds_soak,
                    "workers": workers,
                    "proactor_threads": threads,
                    "artifact": str(soak_path.relative_to(REPO)),
                }
        except Exception as exc:
            soak_doc = {"error": str(exc), "seconds": args.seconds_soak}

    doc = {
        "schema_version": "cost_report.v1",
        "run_id": run_id,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": {
            "hostname": host.get("hostname"),
            "cpu_count": host.get("cpu_count"),
            "mem_gib": (host.get("memory") or {}).get("total_gib"),
            "memory": host.get("memory"),
            "tier": host.get("tier"),
        },
        "stream": str(stream),
        "stream_events": count_lines(stream),
        "profiles": profiles,
        "dragonfly_soak": soak_doc,
        "gate_note": (
            "≥50K EPS sustained gate refers to Dragonfly soak / phase0, "
            "not Python/Vector fan-out EPS"
        ),
    }

    (out_root / "cost_report.json").write_text(json.dumps(doc, indent=2) + "\n")
    (out_root / "cost_report.md").write_text(render_md(doc))
    latest = COSTING / "LATEST.md"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(
        f"# Latest cost report\n\n"
        f"- Run: `{run_id}`\n"
        f"- Path: [`{run_id}/cost_report.md`](./{run_id}/cost_report.md)\n"
        f"- Captured: {doc['captured_at']}\n"
    )
    print(f"\nWrote {out_root / 'cost_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
