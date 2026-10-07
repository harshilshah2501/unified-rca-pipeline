from __future__ import annotations

from typing import Any

from ab_shared.dest import Dest
from graph.read_api import get_neighbors
from sketch.sketch_read import get_metric_baseline, get_window_percentiles, load_rows


def identity_join(snapshot: dict[str, Any], dest: Dest) -> dict[str, Any]:
    """Every sketch entity_id must exist as a graph node."""
    node_ids = {n["ci_id"] for n in snapshot.get("nodes", [])}
    rows = load_rows(dest)
    missing = sorted({r["entity_id"] for r in rows} - node_ids)
    return {
        "ok": not missing,
        "missing_from_graph": missing,
        "sketch_entities": sorted({r["entity_id"] for r in rows}),
        "graph_nodes": sorted(node_ids),
    }


def working_set_embryo(
    snapshot: dict[str, Any],
    dest: Dest,
    *,
    seed_ci: str,
    window: str = "5m",
    window_start: str = "2026-08-20T03:30:00Z",
    season_key: str = "Thu-03:00",
    hops: int = 1,
) -> dict[str, Any]:
    metrics = ("request.latency_ms", "cpu.utilization_pct")
    sketches = []
    for mid in metrics:
        pct = get_window_percentiles(
            dest,
            tenant="default",
            entity_id=seed_ci,
            metric_id=mid,
            window=window,
            window_start=window_start,
        )
        base = get_metric_baseline(
            dest,
            tenant="default",
            entity_id=seed_ci,
            metric_id=mid,
            season_key=season_key,
            window=window,
        )
        if pct or base:
            sketches.append({"metric_id": mid, "percentiles": pct, "baseline": base})
    return {
        "seed_ci": seed_ci,
        "neighbors": get_neighbors(snapshot, seed_ci, hops=hops),
        "sketches": sketches,
    }


def door_c_flags(
    dest: Dest,
    *,
    entity_id: str,
    metric_id: str = "request.latency_ms",
    window: str = "5m",
    window_start: str = "2026-08-20T03:30:00Z",
    season_key: str = "Thu-03:00",
    ratio: float = 1.5,
) -> dict[str, Any]:
    pct = get_window_percentiles(
        dest,
        tenant="default",
        entity_id=entity_id,
        metric_id=metric_id,
        window=window,
        window_start=window_start,
    )
    base = get_metric_baseline(
        dest,
        tenant="default",
        entity_id=entity_id,
        metric_id=metric_id,
        season_key=season_key,
        window=window,
    )
    if not pct or not base:
        return {"fired": False, "reason": "missing_sketch_or_baseline"}
    expected = base["expected_p95"] or 0.0
    fired = expected > 0 and pct["p95"] > expected * ratio
    return {
        "fired": fired,
        "class": "SLOWDOWN" if fired else None,
        "p95": pct["p95"],
        "expected_p95": expected,
        "ratio": ratio,
    }
