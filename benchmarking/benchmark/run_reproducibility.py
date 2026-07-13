#!/usr/bin/env python3
"""N-run reproducibility harness for federated and lean engines."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
N_DEFAULT = 20


def _hash_verdict(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_reproducibility(engine: str, n: int, run_prefix: str) -> dict:
    script = REPO / "benchmarking" / "benchmark" / f"run_{engine}.py"
    py = REPO / ".venv" / "bin" / "python"
    if not py.exists():
        py = Path(sys.executable)
    hashes: dict[str, list[str]] = {f"UC-{i}": [] for i in range(1, 6)}
    for i in range(n):
        run_id = f"{run_prefix}-{i:02d}"
        subprocess.run(
            [str(py), str(script), "--all", "--run-id", run_id],
            cwd=REPO,
            check=True,
        )
    results_base = REPO / "benchmarking" / "results" / engine
    summary: dict[str, dict] = {}
    for uc in hashes:
        uc_hashes = []
        for run_dir in sorted((results_base / uc).glob(f"run-{run_prefix}-*/verdict.json")):
            uc_hashes.append(_hash_verdict(run_dir))
        unique = len(set(uc_hashes))
        total = len(uc_hashes)
        pct = (100.0 if total == 0 else (100.0 if unique == 1 else 0.0))
        summary[uc] = {
            "runs": total,
            "unique_hashes": unique,
            "reproducibility_pct": pct,
            "bit_identical": unique == 1 and total > 0,
        }
    out = REPO / "benchmarking" / "results" / f"reproducibility_{engine}_{run_prefix}.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproducibility harness N=20")
    parser.add_argument("--engine", choices=["federated", "lean"], required=True)
    parser.add_argument("--n", type=int, default=N_DEFAULT)
    parser.add_argument("--prefix", default="repro")
    args = parser.parse_args(argv)
    summary = run_reproducibility(args.engine, args.n, args.prefix)
    for uc, s in summary.items():
        print(f"{uc}: {s['reproducibility_pct']}% ({s['unique_hashes']} unique / {s['runs']} runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
