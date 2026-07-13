#!/usr/bin/env python3
"""Step 3 — Run lean ObserveOps RCA on corpus bundles."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "lean-pipeline"))
sys.path.insert(0, str(REPO / "benchmarking"))

from core_engine.observeops.engine import diagnose  # noqa: E402

CORPUS = REPO / "datasets" / "observeops"
RESULTS = REPO / "benchmarking" / "results" / "lean"


def run_uc(uc_id: str, run_id: str | None = None) -> dict:
    verdict = diagnose(uc_id, CORPUS)
    ts = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = RESULTS / uc_id / f"run-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    meta = {
        "uc_id": uc_id,
        "run_id": ts,
        "corpus_version": json.loads((CORPUS / "manifest.json").read_text())["corpus_version"],
        "engine": "lean",
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run lean RCA on ObserveOps corpus")
    parser.add_argument("--uc", help="Single UC e.g. UC-1")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--run-id", help="Fixed run id")
    args = parser.parse_args(argv)

    if args.all:
        ucs = [f"UC-{i}" for i in range(1, 6)]
    elif args.uc:
        ucs = [args.uc]
    else:
        parser.error("Specify --uc UC-N or --all")
        return 1

    for uc in ucs:
        v = run_uc(uc, args.run_id)
        gt = json.loads((CORPUS / uc / "ground_truth.json").read_text())["root_ci"]
        match = v["root_ci"] == gt
        print(
            f"{uc}: root_ci={v['root_ci']} sig={v['signature']} "
            f"tier={v['evidentiary_tier']} fallback_fired={v['fallback_fired']} "
            f"causal_verified={v['causal_verified']} "
            f"obs_to_convergence={v['obs_to_convergence']} "
            f"naive_bfs_expansions={v['naive_bfs_expansions']} "
            f"efficiency_ratio={v['efficiency_ratio']:.2f} "
            f"{'PASS' if match else 'FAIL'}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
