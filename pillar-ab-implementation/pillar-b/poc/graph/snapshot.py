"""Validate GraphState and publish / load the Dest ``map/`` room.

``publish_map`` on GraphWriter ends here: schema-validate nodes, edges, and the
packaged ``graph_snapshot.v1``, then cold-encode per Dest profile:

* ``files.v1`` — JSON / JSONL under Dest keys (lab default for unit tests)
* ``vortex_s3.v1`` — Motadata cold SoT via ``map_vortex_cold`` (parts + manifest + latest)

See ``contracts/MAP_WRITE_READ_RECORD.md`` and ``contracts/MAP_WRITER_VORTEX_COHESION.md``.
"""

from __future__ import annotations

import json
import os
from typing import Any

from ab_shared.dest import Dest, FileDest
from ab_shared.schema import validate
from graph.cold_vortex import (
    PROFILE_FILES,
    PROFILE_VORTEX,
    load_vortex,
    looks_like_vortex_map,
    map_room_root,
    publish_vortex,
)
from graph.graph_builder import GraphState
from graph.timeutil import to_epoch_ms

_CLOCK_KEYS = ("last_seen", "valid_from", "valid_to")


def resolve_dest_profile(explicit: str | None = None) -> str:
    """Return ``files.v1`` or ``vortex_s3.v1`` (env ``POC_MAP_DEST_PROFILE``)."""
    raw = (explicit or os.environ.get("POC_MAP_DEST_PROFILE") or PROFILE_FILES).strip()
    if raw not in {PROFILE_FILES, PROFILE_VORTEX}:
        raise ValueError(
            f"unknown map Dest profile {raw!r}; use {PROFILE_FILES!r} or {PROFILE_VORTEX!r}"
        )
    return raw


def _normalize_clocks(row: dict[str, Any]) -> None:
    """Coerce ISO strings (legacy tests / CLI) to epoch-ms integers before schema validate."""
    for key in _CLOCK_KEYS:
        if key not in row:
            continue
        val = row[key]
        if val is None:
            continue
        if isinstance(val, str):
            row[key] = to_epoch_ms(val)


def build_snapshot(state: GraphState, *, version: str = "1") -> dict[str, Any]:
    """Assemble and schema-validate a ``graph_snapshot.v1`` from in-memory state."""
    nodes = list(state.nodes.values())
    edges = list(state.edges.values())
    for n in nodes:
        _normalize_clocks(n)
        validate("graph_node_v1.schema.json", n)
    for e in edges:
        _normalize_clocks(e)
        validate("graph_edge_v1.schema.json", e)
    snapshot = {
        "schema_version": "graph_snapshot.v1",
        "tenant": state.tenant,
        "version": version,
        "nodes": nodes,
        "edges": edges,
    }
    validate("graph_snapshot_v1.schema.json", snapshot)
    return snapshot


def _strip_for_vortex(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Drop PoC-only additional properties before Rust cold deserialize."""
    node_keep = {
        "schema_version",
        "entity_id",
        "type",
        "name",
        "env",
        "region",
        "owner",
        "namespace",
        "last_seen",
        "valid_from",
        "valid_to",
        "version",
    }
    edge_keep = {
        "schema_version",
        "edge_id",
        "source_id",
        "target_id",
        "edge_type",
        "valid_from",
        "valid_to",
        "evidence_event_id",
    }
    return {
        "schema_version": snapshot["schema_version"],
        "tenant": snapshot["tenant"],
        "version": snapshot["version"],
        "nodes": [{k: n.get(k) for k in node_keep if k in n} for n in snapshot["nodes"]],
        "edges": [{k: e.get(k) for k in edge_keep if k in e} for e in snapshot["edges"]],
    }


def publish_snapshot(
    dest: Dest,
    snapshot: dict[str, Any],
    *,
    profile: str | None = None,
) -> None:
    """Write map room per Dest profile."""
    validate("graph_snapshot_v1.schema.json", snapshot)
    prof = resolve_dest_profile(profile)
    if prof == PROFILE_FILES:
        dest.put("map", "graph_snapshot.json", json.dumps(snapshot, indent=2).encode("utf-8"))
        dest.put(
            "map",
            "nodes.jsonl",
            ("\n".join(json.dumps(n) for n in snapshot["nodes"]) + "\n").encode("utf-8"),
        )
        dest.put(
            "map",
            "edges.jsonl",
            ("\n".join(json.dumps(e) for e in snapshot["edges"]) + "\n").encode("utf-8"),
        )
        dest.put(
            "map",
            "dest_profile.json",
            json.dumps({"profile": PROFILE_FILES}).encode("utf-8"),
        )
        return

    if not isinstance(dest, FileDest):
        raise TypeError(
            f"{PROFILE_VORTEX} publish requires FileDest (got {type(dest).__name__}); "
            "MemoryDest stays on files.v1 for unit tests"
        )
    tenant_map = map_room_root(dest.root)
    publish_vortex(_strip_for_vortex(snapshot), tenant_map)
    # Pointer for load auto-detect + lab inspection (not Motadata SoT).
    dest.put(
        "map",
        "dest_profile.json",
        json.dumps({"profile": PROFILE_VORTEX, "version": snapshot["version"]}).encode("utf-8"),
    )


def load_snapshot(dest: Dest, *, profile: str | None = None) -> dict[str, Any] | None:
    """Read packaged snapshot from Dest ``map/`` (Scope / Diagnose / tests).

    When ``profile`` is omitted: prefer ``vortex_s3.v1`` if ``latest.json`` exists
    under a FileDest map room; else ``graph_snapshot.json`` (files.v1).
    """
    if profile is None and isinstance(dest, FileDest):
        tenant_map = map_room_root(dest.root)
        if looks_like_vortex_map(tenant_map):
            profile = PROFILE_VORTEX
    prof = resolve_dest_profile(profile) if profile else PROFILE_FILES

    if prof == PROFILE_VORTEX:
        if not isinstance(dest, FileDest):
            raise TypeError(f"{PROFILE_VORTEX} load requires FileDest")
        tenant_map = map_room_root(dest.root)
        if not looks_like_vortex_map(tenant_map):
            return None
        snap = load_vortex(tenant_map)
        validate("graph_snapshot_v1.schema.json", snap)
        return snap

    raw = dest.get("map", "graph_snapshot.json")
    if raw is None:
        return None
    snapshot = json.loads(raw.decode("utf-8"))
    validate("graph_snapshot_v1.schema.json", snapshot)
    return snapshot
