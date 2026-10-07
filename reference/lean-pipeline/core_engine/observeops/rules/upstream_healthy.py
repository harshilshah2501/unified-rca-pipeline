"""Upstream healthy gate — UC-5 anti-false-positive."""

from __future__ import annotations

from core_engine.observeops.ingest.bundle import crossed_anomalies
from core_engine.observeops.registry import app_prefixes, infra_prefixes


def upstream_healthy(bundle: dict) -> bool:
    crossed = {a["ci"] for a in crossed_anomalies(bundle)}
    infra = infra_prefixes()
    infra_crossed = [ci for ci in crossed if any(ci.startswith(p) for p in infra)]
    return len(infra_crossed) == 0


def gate(bundle: dict, candidate: str) -> str:
    """If upstream healthy and symptom is app-layer, root stays at app."""
    if bundle["ground_truth"].get("upstream_healthy") or upstream_healthy(bundle):
        seed = bundle["symptom_seed"]["ci"]
        if any(seed.startswith(p) for p in app_prefixes()):
            return seed
    return candidate
