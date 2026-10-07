#!/usr/bin/env python3
"""Run Lean + Federated once each over OO engine packs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKS = REPO / "datasets" / "openobserve_incidents" / "v1" / "engine_packs"
OUT_DIR = REPO / "benchmarking" / "results" / "openobserve"
VENV_PY = REPO / ".venv" / "bin" / "python"


def _python() -> str:
    return str(VENV_PY) if VENV_PY.exists() else sys.executable


def _pack_ids() -> list[str]:
    return sorted(
        p.name
        for p in PACKS.iterdir()
        if p.is_dir() and (p / "topology.json").exists()
    )


def _run_engine(engine: str, run_id: str, packs: list[str]) -> int:
    script = REPO / "benchmarking" / "benchmark" / f"run_{engine}.py"
    # --all prefers corpus listing; pass --all for full set
    cmd = [
        _python(),
        str(script),
        "--corpus",
        str(PACKS),
        "--run-id",
        run_id,
    ]
    if len(packs) == len(_pack_ids()):
        cmd.append("--all")
    else:
        # run one-by-one for subset
        rc = 0
        for pid in packs:
            c = cmd + ["--uc", pid]
            print(f"$ {' '.join(c)}")
            r = subprocess.run(c, cwd=REPO)
            rc = rc or r.returncode
        return rc
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="Shared run id for both engines")
    parser.add_argument("--engine", choices=("lean", "federated", "both"), default="both")
    parser.add_argument("--limit", type=int, help="Only first N packs (smoke)")
    args = parser.parse_args(argv)

    run_id = args.run_id or datetime.now(timezone.utc).strftime("oo-bakeoff-%Y%m%dT%H%M%SZ")
    packs = _pack_ids()
    if args.limit:
        packs = packs[: args.limit]

    engines = ["lean", "federated"] if args.engine == "both" else [args.engine]
    rc = 0
    for eng in engines:
        if len(packs) == len(_pack_ids()) and not args.limit:
            r = _run_engine(eng, run_id, packs)
        else:
            r = _run_engine(eng, run_id, packs)
        rc = rc or r

    meta = {
        "run_id": run_id,
        "packs": packs,
        "engines": engines,
        "corpus": str(PACKS),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "engine_bakeoff_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Bakeoff run_id={run_id} packs={len(packs)} engines={engines}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
