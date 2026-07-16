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

DEFAULT_CORPUS = REPO / "datasets" / "observeops"
OO_PACKS = REPO / "datasets" / "openobserve_incidents" / "v1" / "engine_packs"
RESULTS = REPO / "benchmarking" / "results" / "lean"


def _is_oo_packs(corpus: Path) -> bool:
    return corpus.resolve() == OO_PACKS.resolve() or corpus.name == "engine_packs"


def _results_dir(corpus: Path, uc_id: str, run_id: str) -> Path:
    if _is_oo_packs(corpus):
        return RESULTS / "oo" / uc_id / f"run-{run_id}"
    return RESULTS / uc_id / f"run-{run_id}"


def _corpus_version(corpus: Path) -> str:
    manifest = corpus / "manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text()).get("corpus_version", "unknown")
    return "unknown"


def _pack_ids(corpus: Path) -> list[str]:
    if _is_oo_packs(corpus):
        return sorted(
            p.name
            for p in corpus.iterdir()
            if p.is_dir() and (p / "topology.json").exists()
        )
    return [f"UC-{i}" for i in range(1, 6)]


def run_uc(
    uc_id: str,
    run_id: str | None = None,
    corpus: Path | None = None,
) -> dict:
    corpus = corpus or DEFAULT_CORPUS
    verdict = diagnose(uc_id, corpus)
    ts = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = _results_dir(corpus, uc_id, ts)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    meta = {
        "uc_id": uc_id,
        "run_id": ts,
        "corpus": str(corpus),
        "corpus_version": _corpus_version(corpus),
        "engine": "lean",
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run lean RCA on ObserveOps / OO packs")
    parser.add_argument("--uc", help="Single UC e.g. UC-1 or OO incident id")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--run-id", help="Fixed run id")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="Corpus root (ObserveOps or OO engine_packs)",
    )
    args = parser.parse_args(argv)
    corpus = args.corpus.resolve()

    if args.all:
        ucs = _pack_ids(corpus)
    elif args.uc:
        ucs = [args.uc]
    else:
        parser.error("Specify --uc UC-N or --all")
        return 1

    for uc in ucs:
        v = run_uc(uc, args.run_id, corpus=corpus)
        gt = json.loads((corpus / uc / "ground_truth.json").read_text())["root_ci"]
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
