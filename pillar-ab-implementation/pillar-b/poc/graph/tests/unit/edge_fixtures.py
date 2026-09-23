"""Motadata-aligned edge fixture helper for unit tests."""

from __future__ import annotations

from typing import Any


def motadata_edge(
    *,
    source_id: str,
    target_id: str,
    edge_type: str = "DEPENDS_ON",
    edge_id: int = 1,
    evidence_event_id: int = 2,
    valid_from: str | None = "2026-08-20T00:00:00Z",
    valid_to: str | None = None,
    origin: str = "declared",
    telemetry_source: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": "graph_edge.v1",
        "edge_id": edge_id,
        "source_id": source_id,
        "target_id": target_id,
        "edge_type": edge_type,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "evidence_event_id": evidence_event_id,
        "origin": origin,
    }
    if telemetry_source:
        row["telemetry_source"] = telemetry_source
    return row
