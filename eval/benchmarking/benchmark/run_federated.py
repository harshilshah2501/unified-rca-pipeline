#!/usr/bin/env python3
"""Step 2 — Run federated PoC on ObserveOps / OO engine-pack bundles."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "federated-pipeline"))
sys.path.insert(0, str(REPO / "lean-pipeline"))
sys.path.insert(0, str(REPO / "benchmarking"))

from benchmark.adapters.observeops_federated import (  # noqa: E402
    MURPHY_POSTERIOR_THRESHOLD,
    build_detection_flag,
    build_metric_store,
    build_orchestrator,
    earliest_crossed_root,
    fusion_root_from_posterior,
    has_direct_symptom_fault,
    load_bundle,
    map_root_cause_entity,
    recover_murphy_causal_posterior,
    resolve_root_ci,
    verdict_to_benchmark,
    _parse_ts,
)
from benchmark.corpus_util import (  # noqa: E402
    is_frozen_pack_corpus,
    pack_ids,
    results_dir,
)
from benchmark.parity import (  # noqa: E402
    annotate_change_near_onset,
    apply_detect_to_bundle,
    detect_meta_for_scoreboard,
    resolve_changes_path,
    run_shared_detect,
)
from core_engine.lean.signature import infer_signature  # noqa: E402

DEFAULT_CORPUS = REPO / "datasets" / "observeops"
RESULTS = REPO / "benchmarking" / "results" / "federated"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


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
    bundle = load_bundle(uc_id, corpus)
    detect_meta: dict = {}
    if shared_detect and not is_frozen_pack_corpus(corpus):
        detect = run_shared_detect(uc_id, corpus)
        annotate_change_near_onset(detect, resolve_changes_path(uc_id, corpus))
        detect_meta = detect_meta_for_scoreboard(detect)
        bundle = apply_detect_to_bundle(bundle, detect)

    store = build_metric_store(bundle)
    flag = build_detection_flag(bundle, detect_source="shared_detect")
    incident_time = _parse_ts(bundle["symptom_seed"]["timestamp"])

    orchestrator = build_orchestrator(store)
    fallback_fired = False
    fallback_reason: str | None = None
    murphy_posterior: float | None = None
    hop_logs: list = []
    t0 = time.perf_counter()
    try:
        rca = orchestrator.run_pipeline(flag, incident_time=incident_time)
        posterior_dist = rca.evidence.get("murphy", {}).get("distribution") or {}
        if not posterior_dist:
            posterior_dist = recover_murphy_causal_posterior(
                store,
                orchestrator.murphy.murphy,
                flag.symptom_entity or flag.entity,
                incident_time,
                direct_symptom_fault=has_direct_symptom_fault(
                    bundle, flag.symptom_entity or flag.entity
                ),
                bundle=bundle,
            )
            if posterior_dist:
                rca.evidence["murphy"]["distribution"] = posterior_dist
        if posterior_dist:
            fusion_root = fusion_root_from_posterior(
                bundle, posterior_dist, flag.symptom_entity or flag.entity
            )
            rca.root_cause_entity = map_root_cause_entity(bundle, fusion_root)
            rca.evidence["murphy"]["entity"] = fusion_root
            rca.evidence["murphy"]["posterior"] = float(
                posterior_dist.get(fusion_root, 0.0) or 0.0
            )
        else:
            rca.root_cause_entity = map_root_cause_entity(bundle, rca.root_cause_entity)
        root_ci, fallback_fired, fallback_reason = resolve_root_ci(
            bundle,
            rca,
            theta_murphy=MURPHY_POSTERIOR_THRESHOLD,
        )
        murphy_posterior = float(
            max(posterior_dist.values())
            if posterior_dist
            else rca.evidence.get("murphy", {}).get("posterior", 0.0) or 0.0
        )
        crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
        signature = infer_signature(crossed)
        evidence = [
            {
                "ci": a["ci"],
                "signal": a["signal"],
                "value": a["value"],
                "timestamp": a["timestamp"],
            }
            for a in crossed
        ]
        observations = len(orchestrator.hop_logs)
        hop_logs = [asdict(h) for h in orchestrator.hop_logs]
    except Exception:
        root_ci, _gt_sig, evidence = earliest_crossed_root(bundle)
        crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
        signature = infer_signature(crossed)
        observations = 0
        fallback_fired = True
        fallback_reason = "pipeline_exception"
        hop_logs = [asdict(h) for h in orchestrator.hop_logs]
    latency_ms = (time.perf_counter() - t0) * 1000.0

    verdict = verdict_to_benchmark(
        uc_id,
        root_ci,
        signature,
        evidence,
        observations,
        bundle["ground_truth"].get("contributor_cis"),
        fallback_fired=fallback_fired,
        fallback_reason=fallback_reason,
        murphy_posterior=murphy_posterior,
    )

    ts = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = _results_dir(corpus, uc_id, ts)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    (out_dir / "hop_logs.json").write_text(json.dumps(hop_logs, indent=2) + "\n")
    hop_total = sum(float(h.get("latency_ms") or 0.0) for h in hop_logs)
    meta = {
        "uc_id": uc_id,
        "run_id": ts,
        "corpus": str(corpus),
        "corpus_version": _corpus_version(corpus),
        "engine": "federated",
        "fallback_fired": fallback_fired,
        "murphy_posterior": murphy_posterior,
        "latency_ms": round(latency_ms, 4),
        "hop_total_ms": round(hop_total, 4),
        "system_latency_ms": round(
            latency_ms + float(detect_meta.get("detect_latency_ms") or 0.0), 4
        ),
        **detect_meta,
    }
    if not detect_meta:
        meta["pipeline_profile"] = "legacy-frozen-bundle"
        meta["detect_source"] = "none"
    if fallback_reason:
        meta["fallback_reason"] = fallback_reason
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run federated RCA on ObserveOps / OO packs"
    )
    parser.add_argument("--uc", help="Single UC e.g. UC-1 or OO incident id")
    parser.add_argument("--all", action="store_true", help="Run all packs/UCs")
    parser.add_argument("--run-id", help="Fixed run id for reproducibility")
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
        match = v["root_ci"] == load_bundle(uc, corpus)["ground_truth"]["root_ci"]
        fb = "fallback" if v.get("fallback_fired") else "fusion"
        print(f"{uc}: root_ci={v['root_ci']} {'PASS' if match else 'FAIL'} ({fb})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
