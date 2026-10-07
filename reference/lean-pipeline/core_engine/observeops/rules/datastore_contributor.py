"""Datastore contributor rule — UC-3 noisy neighbor."""

from __future__ import annotations

from core_engine.observeops.ingest.bundle import crossed_anomalies
from core_engine.observeops.registry import rule


def contributors(bundle: dict) -> list[str]:
    crossed = crossed_anomalies(bundle)
    cfg = rule("datastore_contributor")
    return [
        a["ci"]
        for a in crossed
        if a["ci"].startswith(cfg["ci_prefix"]) and a["signal"] == cfg["signal"]
    ]
