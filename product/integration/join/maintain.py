from __future__ import annotations

from typing import Any

from ab_shared.dest import Dest
from graph.graph_builder import GraphState
from graph.maintain import expire_edges
from graph.snapshot import build_snapshot, publish_snapshot
from sketch.sketch_flush import SketchWriter


def maintain(
    state: GraphState,
    writer: SketchWriter,
    dest: Dest,
    *,
    as_of: str = "2026-08-20T04:00:00Z",
    bump_version: str = "2",
) -> dict[str, Any]:
    writer.refresh_baselines()
    expired = expire_edges(state, as_of)
    snap = build_snapshot(state, version=bump_version)
    publish_snapshot(dest, snap)
    rows = writer.flush(dest)
    return {"expired_edges": expired, "snapshot_version": bump_version, "sketch_rows": len(rows)}
