"""Lean ObserveOps RCA — best-first walk + info-gain + conditional CARE."""

from __future__ import annotations

from core_engine.lean.care import care_fallback_candidates
from core_engine.lean.causal import verify_care_root
from core_engine.lean.info_gain import score_candidate
from core_engine.lean.invocation_graph import InvocationGraph
from core_engine.lean.search import (
    best_first_walk,
    expansions_to_target,
    naive_bfs_expansions,
)
from core_engine.lean.signature import infer_signature
from core_engine.lean.temporal import delta_t_ambiguous, onset_by_ci, rank_by_onset
from core_engine.observeops.ingest.bundle import (
    crossed_anomalies,
    evidence_from_bundle,
    load_bundle,
)
from core_engine.observeops.registry import decisive_signals, load_registry
from core_engine.observeops.rules import datastore_contributor, shared_upstream, upstream_healthy
from lean_rca.report import build_sre_report


def diagnose(uc_id: str, corpus_dir) -> dict:
    load_registry()
    bundle = load_bundle(uc_id, corpus_dir)
    seed = bundle["symptom_seed"]
    crossed = crossed_anomalies(bundle)

    graph = InvocationGraph.from_topology(bundle["topology"])
    onset_times = onset_by_ci(crossed)
    decisive = decisive_signals()

    def score_fn(ci: str) -> float:
        return score_candidate(ci, crossed, onset_times, decisive)

    ranked, expansion_order = best_first_walk(graph, seed["ci"], score_fn)
    candidates = [ci for ci, _ in ranked]
    all_upstream = graph.collect_upstream(seed["ci"])

    tier = 1
    fallback = False
    causal_verified: bool | None = None
    causal_log: list[dict] | None = None
    crossed_cis = {a["ci"] for a in crossed}
    anomaly_candidates = sorted(crossed_cis)
    ambiguous = delta_t_ambiguous(onset_times, anomaly_candidates)

    shared = shared_upstream.apply(bundle, all_upstream)
    if not crossed:
        root_ci = seed["ci"]
    elif shared and shared in crossed_cis and not ambiguous:
        root_ci = shared
    elif ambiguous:
        # Prefer Motadata shared-upstream rules under Δt ambiguity so an
        # unrelated earlier anomaly (e.g. UC-3b switch noise) does not win
        # solely by onset / raw CARE severity.
        care_ranked = care_fallback_candidates(crossed, anomaly_candidates) or []
        fallback = True
        tier = 2
        if shared and shared in crossed_cis:
            root_ci = shared
        elif care_ranked:
            root_ci = care_ranked[0]
        else:
            root_ci = candidates[0] if candidates else rank_by_onset(crossed)[0]["ci"]
        causal_verified, causal_log = verify_care_root(
            graph, seed["ci"], root_ci, crossed
        )
        if causal_verified:
            tier = 3
        if shared and shared in crossed_cis and not care_ranked:
            causal_log = (causal_log or []) + [
                {"check": "care_candidates", "passed": False}
            ]
    else:
        search_anomalies = [c for c in candidates if c in crossed_cis]
        if search_anomalies:
            root_ci = min(search_anomalies, key=lambda ci: onset_times[ci])
        else:
            root_ci = rank_by_onset(crossed)[0]["ci"]

    root_ci = upstream_healthy.gate(bundle, root_ci)
    obs_to_convergence = expansions_to_target(expansion_order, seed["ci"], root_ci)
    naive_expansions = naive_bfs_expansions(graph, seed["ci"], root_ci)
    sig = infer_signature(crossed)
    contribs = datastore_contributor.contributors(bundle)
    evidence = evidence_from_bundle(bundle)
    verdict = {
        "engine": "lean",
        "uc_id": uc_id,
        "root_ci": root_ci,
        "signature": sig,
        "contributor_cis": contribs,
        "evidence": evidence,
        "observations": len(crossed),
        "evidentiary_tier": tier,
        "fallback_fired": fallback,
        "causal_verified": causal_verified,
        "causal_log": causal_log,
        "obs_to_convergence": obs_to_convergence,
        "naive_bfs_expansions": naive_expansions,
        "efficiency_ratio": naive_expansions / max(obs_to_convergence, 1),
        "upstream_healthy_verified": upstream_healthy.upstream_healthy(bundle),
    }
    return build_sre_report(verdict, bundle)
