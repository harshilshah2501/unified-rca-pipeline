"""Motadata-aligned edge fixture helper for unit tests."""

from __future__ import annotations

from typing import Any

# 2026-08-20T00:00:00Z
_DEFAULT_VALID_FROM_MS = 1_787_184_000_000


def motadata_edge(
    *,
    source_id: str,
    target_id: str,
    edge_type: str = "DEPENDS_ON",
    edge_id: int = 1,
    evidence_event_id: int = 2,
    valid_from: int | str | None = _DEFAULT_VALID_FROM_MS,
    valid_to: int | str | None = None,
    origin: str = "declared",
    telemetry_source: str | None = None,
) -> dict[str, Any]:
    from graph.timeutil import to_epoch_ms

    vf = to_epoch_ms(valid_from) if valid_from is not None else None
    vt = to_epoch_ms(valid_to) if valid_to is not None else None
    row: dict[str, Any] = {
        "schema_version": "graph_edge.v1",
        "edge_id": edge_id,
        "source_id": source_id,
        "target_id": target_id,
        "edge_type": edge_type,
        "valid_from": vf,
        "valid_to": vt,
        "evidence_event_id": evidence_event_id,
        "origin": origin,
    }
    if telemetry_source:
        row["telemetry_source"] = telemetry_source
    return row
