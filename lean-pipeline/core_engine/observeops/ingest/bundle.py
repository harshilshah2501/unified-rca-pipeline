"""ObserveOps bundle ingest — typed invocation graph from frozen corpus."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def load_bundle(uc_id: str, corpus_dir: Path) -> dict:
    base = corpus_dir / uc_id
    events_path = base / "events.json"
    events = (
        json.loads(events_path.read_text())
        if events_path.exists()
        else {"events": []}
    )
    return {
        "uc_id": uc_id,
        "topology": json.loads((base / "topology.json").read_text()),
        "anomalies": json.loads((base / "anomalies.json").read_text()),
        "events": events,
        "symptom_seed": json.loads((base / "symptom_seed.json").read_text()),
        "ground_truth": json.loads((base / "ground_truth.json").read_text()),
    }


def upstream_map(topology: dict) -> dict[str, list[str]]:
    """Effect node -> list of upstream cause candidates."""
    upstream: dict[str, list[str]] = {n["id"]: [] for n in topology["nodes"]}
    for edge in topology["edges"]:
        upstream.setdefault(edge["from"], []).append(edge["to"])
    return upstream


def crossed_anomalies(bundle: dict) -> list[dict]:
    return [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]


def bundle_events(bundle: dict) -> list[dict]:
    return list(bundle.get("events", {}).get("events") or [])


def anomaly_by_ci_signal(bundle: dict) -> dict[tuple[str, str], dict]:
    return {(a["ci"], a["signal"]): a for a in bundle["anomalies"]["anomalies"]}


def evidence_from_bundle(bundle: dict) -> list[dict]:
    """Crossed anomalies + synthetic events for SRE evidence trail."""
    from core_engine.lean.temporal import rank_by_onset

    evidence: list[dict] = []
    for a in rank_by_onset(crossed_anomalies(bundle)):
        evidence.append(
            {
                "ci": a["ci"],
                "signal": a["signal"],
                "value": a["value"],
                "timestamp": a["timestamp"],
                "source": "anomaly",
            }
        )
    for ev in sorted(bundle_events(bundle), key=lambda e: e["timestamp"]):
        evidence.append(
            {
                "ci": ev["ci"],
                "signal": ev["event_type"],
                "value": ev["message"],
                "timestamp": ev["timestamp"],
                "source": "event",
                "severity": ev.get("severity"),
                "message": ev["message"],
            }
        )
    return evidence
