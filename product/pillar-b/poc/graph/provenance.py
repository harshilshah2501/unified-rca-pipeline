"""Retired map-edge provenance helpers.

Motadata-aligned ``graph_edge.v1`` stores Snowflake ``evidence_event_id`` instead
of a nested ``discovered_via`` block. GraphWriter no longer calls this module.

Kept for unit tests that still exercise the old evidence_type heuristic and for
any caller that needs to classify a telemetry bind string into
authoritative / declared / corroborating for *non-map* audit.
"""

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
    """Build a legacy ``discovered_via`` object (not written to Motadata edges)."""
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
    """Map a bind / telemetry source string to authoritative | declared | corroborating."""
    src = telemetry_source.lower()
    if any(k in src for k in ("inventory", "cgroup", "kubernetes", "agent")):
        return "authoritative"
    if any(k in src for k in ("catalog", "cmdb", "terraform", "helm", "bootstrap")):
        return "declared"
    return "corroborating"


def origin_for_source(telemetry_source: str) -> str:
    """Map bind source to Motadata-era maintain origin: declared | stream."""
    if evidence_for_source(telemetry_source) == "declared":
        return "declared"
    return "stream"
