#!/usr/bin/env python3
"""Capture lab host profile (Tier A laptop vs Tier B / pro6000)."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _mem_gib() -> dict:
    meminfo = Path("/proc/meminfo")
    out = {"total_gib": None, "available_gib": None}
    if not meminfo.is_file():
        return out
    vals: dict[str, int] = {}
    for line in meminfo.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                vals[parts[0][:-1]] = int(parts[1])
            except ValueError:
                pass
    # kB → GiB
    if "MemTotal" in vals:
        out["total_gib"] = round(vals["MemTotal"] / (1024 * 1024), 2)
    if "MemAvailable" in vals:
        out["available_gib"] = round(vals["MemAvailable"] / (1024 * 1024), 2)
    return out


def _disk_free_gib(path: Path) -> float | None:
    usage = shutil.disk_usage(path)
    return round(usage.free / (1024**3), 2)


def _nvidia() -> dict | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    line = (proc.stdout or "").strip().splitlines()[:1]
    if not line:
        return {"present": True}
    name, _, mem = line[0].partition(",")
    return {"present": True, "name": name.strip(), "memory": mem.strip()}


def classify_tier(cpu: int, total_gib: float | None) -> str:
    """Rough tier label for lab reports (see INGESTION_POC_PLAN.md)."""
    ram = total_gib or 0.0
    if cpu >= 16 and ram >= 64:
        return "B+"  # pro6000-class
    if cpu >= 8 and ram >= 32:
        return "A"
    return "laptop"


def recommended_profile(tier: str) -> dict:
    if tier == "B+":
        return {
            "df_proactor_threads": 8,
            "phase0_workers": 16,
            "phase0_pipeline": 128,
            "phase0_seconds": 30,
            "fanout_events": 500_000,
            "headline_eligible": True,
            "note": "Headline EPS (≥50K target) — run on this host",
        }
    if tier == "A":
        return {
            "df_proactor_threads": 4,
            "phase0_workers": 8,
            "phase0_pipeline": 128,
            "phase0_seconds": 20,
            "fanout_events": 200_000,
            "headline_eligible": False,
            "note": "Intermediate; prefer pro6000 for published ceilings",
        }
    return {
        "df_proactor_threads": 2,
        "phase0_workers": 4,
        "phase0_pipeline": 128,
        "phase0_seconds": 10,
        "fanout_events": 50_000,
        "headline_eligible": False,
        "note": "WSL/laptop floor only — not for published 50K+ claims",
    }


def host_profile() -> dict:
    mem = _mem_gib()
    cpu = os.cpu_count() or 1
    tier = classify_tier(cpu, mem.get("total_gib"))
    return {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": cpu,
        "memory": mem,
        "disk_free_gib_cwd": _disk_free_gib(Path.cwd()),
        "nvidia": _nvidia(),
        "tier": tier,
        "recommended": recommended_profile(tier),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lab host check")
    parser.add_argument("--output", type=Path, help="Write JSON profile")
    args = parser.parse_args(argv)
    profile = host_profile()
    text = json.dumps(profile, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
