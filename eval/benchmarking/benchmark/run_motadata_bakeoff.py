#!/usr/bin/env python3
"""L1 driver — Lean + Federated on Motadata incidents, then scoreboard."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "incidents"
PY = REPO / ".venv" / "bin" / "python"
if not PY.is_file():
    PY = Path(sys.executable)


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(REPO), check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Motadata L1 Lean vs Federated bakeoff")
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("motadata-l1-%Y%m%dT%H%M%SZ"),
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Only score existing verdicts",
    )
    args = parser.parse_args(argv)

    if not args.skip_run:
        for engine in ("run_lean.py", "run_federated.py"):
            _run(
                [
                    str(PY),
                    f"benchmarking/benchmark/{engine}",
                    "--corpus",
                    str(CORPUS),
                    "--all",
                    "--run-id",
                    args.run_id,
                    # Motadata packs are frozen; shared detect needs metrics/
                    "--no-shared-detect",
                ]
            )

    _run(
        [
            str(PY),
            "benchmarking/benchmark/score_motadata_bakeoff.py",
            "--run-id",
            args.run_id,
        ]
    )
    print(f"Done. Report: benchmarking/results/motadata/COMPARISON.md (run_id={args.run_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
