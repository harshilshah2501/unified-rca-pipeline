from __future__ import annotations

from ab_shared import reject_codes as rc
from ab_shared.identity_gate import ResolvedOnlyGate

WAVE1_METRICS = frozenset({"request.latency_ms", "cpu.utilization_pct"})


def normalize_metric_id(record: dict) -> str | None:
    mid = record.get("metric_id") or record.get("name")
    if not mid:
        return None
    # Accept brief aliases that map to wave-1 names
    aliases = {
        "request.p95_latency_ms": "request.latency_ms",
        "cpu.util": "cpu.utilization_pct",
    }
    return aliases.get(mid, mid)


def admit_metric(record: dict, gate: ResolvedOnlyGate | None = None) -> tuple[dict | None, str | None]:
    gate = gate or ResolvedOnlyGate()
    if record.get("signal_class") != "metric_sample":
        return None, None
    result = gate.admit(record)
    if not result.accepted:
        return None, result.reason
    metric_id = normalize_metric_id(record)
    if metric_id not in WAVE1_METRICS:
        return None, rc.UNKNOWN_METRIC_ID
    if "value" not in record:
        return None, rc.UNKNOWN_METRIC_ID
    out = {
        "tenant": record["tenant"],
        "entity_id": record["ci_id"],
        "entity_type": record.get("ci_type", "Service"),
        "metric_id": metric_id,
        "value": float(record["value"]),
        "ts": record["ts"],
    }
    return out, None
