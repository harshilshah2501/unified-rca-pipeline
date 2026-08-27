from __future__ import annotations

from typing import Any


def build_discovered_via(
    evidence_type: str,
    *,
    confidence: str = "medium",
    telemetry_source: str = "lab",
    direction_inference: str = "",
    refresh: str = "poll 5m",
    signal_fields: list[str] | None = None,
    endpoint_binding: str | None = None,
) -> dict[str, Any]:
    if evidence_type not in {"authoritative", "declared", "corroborating"}:
        raise ValueError(f"bad evidence_type {evidence_type!r}")
    block: dict[str, Any] = {
        "evidence_type": evidence_type,
        "confidence": confidence,
        "telemetry_source": telemetry_source,
        "direction_inference": direction_inference,
        "refresh": refresh,
    }
    if signal_fields is not None:
        block["signal_fields"] = signal_fields
    if endpoint_binding is not None:
        block["endpoint_binding"] = endpoint_binding
    return block


def evidence_for_source(telemetry_source: str) -> str:
    src = telemetry_source.lower()
    if any(k in src for k in ("inventory", "cgroup", "kubernetes", "agent")):
        return "authoritative"
    if any(k in src for k in ("catalog", "cmdb", "terraform", "helm")):
        return "declared"
    return "corroborating"
