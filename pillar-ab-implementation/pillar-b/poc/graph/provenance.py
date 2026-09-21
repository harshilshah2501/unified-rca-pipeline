"""Provenance stamps for ``graph_edge.v1`` (``discovered_via``).

Not an eligibility check — ``edge_catalog`` / ``ci_qualify`` decide WRITE vs DROP.
This module only builds the audit block when an edge is written or refreshed:

* ``authoritative`` — inventory / agent / k8s owns the fact
* ``declared`` — CMDB / catalog / bootstrap asserted it
* ``corroborating`` — inferred from weaker telemetry (e.g. traces)

E5 maintain later *uses* ``evidence_type`` when decaying edges.
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
    """Build the nested ``discovered_via`` object required on map edges."""
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
    if any(k in src for k in ("catalog", "cmdb", "terraform", "helm")):
        return "declared"
    return "corroborating"
