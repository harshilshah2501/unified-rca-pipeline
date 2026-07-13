#!/usr/bin/env python3
"""Step 2 — Run federated PoC on ObserveOps corpus bundles."""

from __future__ import annotations

import argparse
import json
import logging
import sys
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

CORPUS = REPO / "datasets" / "observeops"
RESULTS = REPO / "benchmarking" / "results" / "federated"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def run_uc(uc_id: str, run_id: str | None = None) -> dict:
    bundle = load_bundle(uc_id, CORPUS)
    store = build_metric_store(bundle)
    flag = build_detection_flag(bundle)
    incident_time = _parse_ts(bundle["symptom_seed"]["timestamp"])

    orchestrator = build_orchestrator(store)
    fallback_fired = False
    fallback_reason: str | None = None
    murphy_posterior: float | None = None
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
            max(posterior_dist.values()) if posterior_dist else rca.evidence.get("murphy", {}).get("posterior", 0.0) or 0.0
        )
        signature = bundle["ground_truth"].get("signature", "unknown")
        crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
        evidence = [
            {"ci": a["ci"], "signal": a["signal"], "value": a["value"], "timestamp": a["timestamp"]}
            for a in crossed
        ]
        observations = len(orchestrator.hop_logs)
    except Exception:
        root_ci, signature, evidence = earliest_crossed_root(bundle)
        observations = 0
        fallback_fired = True
        fallback_reason = "pipeline_exception"

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
    out_dir = RESULTS / uc_id / f"run-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    hop_logs = [asdict(h) for h in orchestrator.hop_logs]
    (out_dir / "hop_logs.json").write_text(json.dumps(hop_logs, indent=2) + "\n")
    meta = {
        "uc_id": uc_id,
        "run_id": ts,
        "corpus_version": json.loads((CORPUS / "manifest.json").read_text())["corpus_version"],
        "engine": "federated",
        "fallback_fired": fallback_fired,
        "murphy_posterior": murphy_posterior,
    }
    if fallback_reason:
        meta["fallback_reason"] = fallback_reason
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run federated RCA on ObserveOps corpus")
    parser.add_argument("--uc", help="Single UC e.g. UC-1")
    parser.add_argument("--all", action="store_true", help="Run all UCs")
    parser.add_argument("--run-id", help="Fixed run id for reproducibility")
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
        match = v["root_ci"] == load_bundle(uc, CORPUS)["ground_truth"]["root_ci"]
        fb = "fallback" if v.get("fallback_fired") else "fusion"
        print(f"{uc}: root_ci={v['root_ci']} {'PASS' if match else 'FAIL'} ({fb})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
