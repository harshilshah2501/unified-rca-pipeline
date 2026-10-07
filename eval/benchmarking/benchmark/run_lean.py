#!/usr/bin/env python3
"""Step 3 — Run lean ObserveOps RCA on corpus bundles."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "lean-pipeline"))
sys.path.insert(0, str(REPO / "benchmarking"))

from benchmark.corpus_util import (  # noqa: E402
    is_frozen_pack_corpus,
    pack_ids,
    results_dir,
)
from benchmark.parity import (  # noqa: E402
    detect_meta_for_scoreboard,
    materialize_parity_corpus,
    resolve_changes_path,
    run_shared_detect,
)
from core_engine.observeops.engine import diagnose  # noqa: E402

DEFAULT_CORPUS = REPO / "datasets" / "observeops"
RESULTS = REPO / "benchmarking" / "results" / "lean"


def _results_dir(corpus: Path, uc_id: str, run_id: str) -> Path:
    return results_dir(RESULTS, corpus, uc_id, run_id)


def _corpus_version(corpus: Path) -> str:
    manifest = corpus / "manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text()).get("corpus_version", "unknown")
    return "unknown"


def _pack_ids(corpus: Path) -> list[str]:
    return pack_ids(corpus)


def run_uc(
    uc_id: str,
    run_id: str | None = None,
    corpus: Path | None = None,
    *,
    shared_detect: bool = True,
) -> dict:
    corpus = corpus or DEFAULT_CORPUS
    ts = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = _results_dir(corpus, uc_id, ts)
    out_dir.mkdir(parents=True, exist_ok=True)

    detect_meta: dict = {}
    diagnose_corpus = corpus
    # Frozen packs (OO / Motadata) already carry anomalies + seed — skip metrics/ detect.
    if shared_detect and not is_frozen_pack_corpus(corpus):
        detect = run_shared_detect(uc_id, corpus)
        changes = resolve_changes_path(uc_id, corpus)
        diagnose_corpus = materialize_parity_corpus(
            uc_id,
            corpus,
            detect,
            out_dir / "parity_corpus",
            changes_path=changes,
        )
        detect_meta = detect_meta_for_scoreboard(detect)

    t0 = time.perf_counter()
    verdict = diagnose(uc_id, diagnose_corpus)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    (out_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    meta = {
        "uc_id": uc_id,
        "run_id": ts,
        "corpus": str(corpus),
        "corpus_version": _corpus_version(corpus),
        "engine": "lean",
        "latency_ms": round(latency_ms, 4),
        "system_latency_ms": round(
            latency_ms + float(detect_meta.get("detect_latency_ms") or 0.0), 4
        ),
        **detect_meta,
    }
    if not detect_meta:
        meta["pipeline_profile"] = "legacy-frozen-bundle"
        meta["detect_source"] = "none"
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
        help="Corpus root (ObserveOps, OO engine_packs, or Motadata incidents)",
    )
    parser.add_argument(
        "--no-shared-detect",
        action="store_true",
        help="Skip shared threshold detect (legacy frozen anomalies/seed)",
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
        v = run_uc(
            uc,
            args.run_id,
            corpus=corpus,
            shared_detect=not args.no_shared_detect,
        )
        gt_path = corpus / uc / "ground_truth.json"
        gt = json.loads(gt_path.read_text())["root_ci"]
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
