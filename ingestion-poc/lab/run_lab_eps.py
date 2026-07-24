#!/usr/bin/env python3
"""Standing lab EPS runner — Dragonfly phase0 + F1 fan-out + N4 metric_slice.

Designed for **pro6000-server** headline numbers; auto-downgrades on laptop/WSL.

```bash
# From repo root (starts Dragonfly via compose if needed)
python3 ingestion-poc/lab/run_lab_eps.py

# pro6000 (after host check shows tier B+)
DF_PROACTOR_THREADS=8 python3 ingestion-poc/lab/run_lab_eps.py --seconds 30
```
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
COMPOSE = REPO / "ingestion-poc" / "compose" / "docker-compose.lab.yml"
CAPACITY = REPO / "benchmarking" / "capacity" / "lab"

sys.path.insert(0, str(LAB))
sys.path.insert(0, str(REPO / "federated-pipeline"))

from host_check import host_profile  # noqa: E402
from metric_slice_read import load_speed_stub_to_dragonfly, read_metric_slice  # noqa: E402
from vector_replay_eps import measure_fanout, write_synthetic_stream  # noqa: E402


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(REPO), check=True, env=env)


def _compose_env(threads: int, port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["DF_PROACTOR_THREADS"] = str(threads)
    env["DF_PORT"] = str(port)
    return env


def ensure_dragonfly(port: int, threads: int) -> None:
    """Start lab Dragonfly if not already reachable."""
    try:
        import redis

        client = redis.Redis(host="127.0.0.1", port=port, socket_connect_timeout=1)
        client.ping()
        print(f"Dragonfly already up on :{port}")
        return
    except Exception:
        pass

    if not shutil.which("docker"):
        raise SystemExit("Docker required to start Dragonfly (or start one manually)")

    env = _compose_env(threads, port)
    # Prefer compose plugin; fall back to docker-compose v1; then plain docker run.
    compose_cmds: list[list[str]] = [
        ["docker", "compose", "-f", str(COMPOSE), "up", "-d", "dragonfly"],
        ["docker-compose", "-f", str(COMPOSE), "up", "-d", "dragonfly"],
    ]
    started = False
    for cmd in compose_cmds:
        if cmd[0] == "docker-compose" and not shutil.which("docker-compose"):
            continue
        try:
            _run(cmd, env=env)
            started = True
            break
        except subprocess.CalledProcessError as exc:
            print(f"compose start failed ({exc.returncode}), trying next backend…")

    if not started:
        # Plain docker run (pro6000 may lack compose plugin)
        name = "rca-lab-dragonfly"
        subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)
        _run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-p",
                f"{port}:6379",
                "docker.dragonflydb.io/dragonflydb/dragonfly:v1.25.1",
                f"--proactor_threads={threads}",
                "--port=6379",
            ]
        )

    deadline = time.time() + 45
    import redis

    while time.time() < deadline:
        try:
            redis.Redis(host="127.0.0.1", port=port, socket_connect_timeout=1).ping()
            print(f"Dragonfly ready on :{port}")
            return
        except Exception:
            time.sleep(0.5)
    raise SystemExit(f"Dragonfly did not become ready on :{port}")


def run_phase0(
    *,
    port: int,
    workers: int,
    pipeline: int,
    seconds: float,
    output: Path,
) -> dict[str, Any]:
    # Run as a script (not ``python -m poc...``) so ``poc/__init__.py`` does not
    # pull Murphy/numpy just for the Dragonfly probe.
    script = REPO / "federated-pipeline" / "poc" / "benchmarks" / "phase0_dragonfly.py"
    cmd = [
        sys.executable,
        str(script),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--workers",
        str(workers),
        "--pipeline-size",
        str(pipeline),
        "--seconds",
        str(seconds),
        "--output",
        str(output),
    ]
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(REPO), check=True)
    return json.loads(output.read_text())


def to_markdown(report: dict[str, Any]) -> str:
    host = report["host"]
    rec = host.get("recommended") or {}
    phase0 = report.get("phase0") or {}
    fanout = report.get("fanout") or {}
    slice_r = report.get("metric_slice_read") or {}
    df_load = report.get("dragonfly_load") or {}
    lines = [
        "# Lab EPS report",
        "",
        f"**Captured:** `{report.get('captured_at')}`",
        f"**Hostname:** `{host.get('hostname')}`",
        f"**Tier:** `{host.get('tier')}` — {rec.get('note')}",
        f"**CPU / RAM:** {host.get('cpu_count')} cores / "
        f"{(host.get('memory') or {}).get('total_gib')} GiB",
        "",
        "## Results",
        "",
        "| Probe | EPS | Notes |",
        "|-------|-----|-------|",
        (
            f"| Dragonfly phase0 (Lua) | **{phase0.get('eps', '—')}** | "
            f"p99={phase0.get('p99_latency_ms')} ms; "
            f"workers={phase0.get('workers')}; "
            f"pipeline={phase0.get('pipeline_size')} |"
        ),
        (
            f"| F1 Python fan-out | **{fanout.get('eps', '—')}** | "
            f"events={fanout.get('events')} |"
        ),
        (
            f"| N4 metric_slice read | **{slice_r.get('rows_per_s', '—')}** rows/s | "
            f"rows={slice_r.get('rows')}; entities={slice_r.get('entities')} |"
        ),
    ]
    if df_load:
        lines.append(
            f"| Speed→Dragonfly load | **{df_load.get('eps', '—')}** | "
            f"rows={df_load.get('rows_loaded')} |"
        )
    lines.extend(
        [
            "",
            "## Headline eligibility",
            "",
        ]
    )
    if rec.get("headline_eligible"):
        lines.append(
            "This host is **eligible** for published ≥50K EPS claims "
            "(Tier B+ / pro6000)."
        )
    else:
        lines.append(
            "This host is **not** eligible for published ≥50K EPS claims. "
            "Re-run on `pro6000-server` and copy results into "
            "`federated-pipeline/docs/CAPACITY.md`."
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python3 ingestion-poc/lab/run_lab_eps.py",
            "```",
            "",
            "Artifacts: `benchmarking/capacity/lab/<run_id>/`",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Standing lab EPS (Dragonfly + F1 + N4)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DF_PORT", "6380")))
    parser.add_argument("--seconds", type=float, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--pipeline", type=int, default=None)
    parser.add_argument("--fanout-events", type=int, default=None)
    parser.add_argument("--skip-dragonfly-start", action="store_true")
    parser.add_argument("--skip-phase0", action="store_true")
    parser.add_argument("--skip-fanout", action="store_true")
    parser.add_argument("--skip-n4", action="store_true")
    parser.add_argument("--no-df-load", action="store_true")
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    )
    args = parser.parse_args(argv)

    host = host_profile()
    rec = host["recommended"]
    threads = int(os.environ.get("DF_PROACTOR_THREADS", rec["df_proactor_threads"]))
    workers = args.workers or rec["phase0_workers"]
    pipeline = args.pipeline or rec["phase0_pipeline"]
    seconds = args.seconds if args.seconds is not None else float(rec["phase0_seconds"])
    fanout_n = args.fanout_events or rec["fanout_events"]

    out_dir = CAPACITY / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "host_profile.json").write_text(json.dumps(host, indent=2) + "\n")

    report: dict[str, Any] = {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": args.run_id,
        "host": host,
        "config": {
            "df_port": args.port,
            "df_proactor_threads": threads,
            "phase0_workers": workers,
            "phase0_pipeline": pipeline,
            "phase0_seconds": seconds,
            "fanout_events": fanout_n,
        },
    }

    if not args.skip_dragonfly_start:
        ensure_dragonfly(args.port, threads)

    if not args.skip_phase0:
        phase0_path = out_dir / "phase0_dragonfly.json"
        report["phase0"] = run_phase0(
            port=args.port,
            workers=workers,
            pipeline=pipeline,
            seconds=seconds,
            output=phase0_path,
        )

    fanout_dir = out_dir / "fanout"
    if not args.skip_fanout:
        stream = out_dir / "synthetic_stream.jsonl"
        write_synthetic_stream(stream, fanout_n)
        report["fanout"] = measure_fanout(stream, fanout_dir)
        (out_dir / "fanout_eps.json").write_text(
            json.dumps(report["fanout"], indent=2) + "\n"
        )

    if not args.skip_n4 and not args.skip_fanout:
        structural = fanout_dir / "structural" / "stream.jsonl"
        speed = fanout_dir / "speed_tier" / "feed.jsonl"
        store_out = out_dir / "federated_stores"
        sys.path.insert(0, str(REPO / "ingestion-poc" / "builders"))
        from federated_store_writer import write_federated_stores  # noqa: E402

        meta = write_federated_stores(
            structural_jsonl=structural,
            out_dir=store_out,
            topology=None,
            speed_jsonl=speed if speed.is_file() else None,
        )
        report["store_meta"] = meta
        slice_path = store_out / "metric_slice.jsonl"
        report["metric_slice_read"] = read_metric_slice(slice_path)
        if not args.no_df_load:
            stub = store_out / "speed_tier_stub.jsonl"
            feed = speed if speed.is_file() else stub
            if feed.is_file():
                report["dragonfly_load"] = load_speed_stub_to_dragonfly(
                    feed, host="127.0.0.1", port=args.port, max_rows=min(fanout_n, 100_000)
                )

    (out_dir / "lab_report.json").write_text(json.dumps(report, indent=2) + "\n")
    md = to_markdown(report)
    (out_dir / "LAB_REPORT.md").write_text(md + "\n")
    # Convenience pointer for latest
    latest = CAPACITY / "LATEST.md"
    latest.write_text(md + f"\n\nRun dir: `{out_dir}`\n")
    print(md)
    print(f"\nWrote {out_dir / 'LAB_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
