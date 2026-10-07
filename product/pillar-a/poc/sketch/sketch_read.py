from __future__ import annotations

import json
from typing import Any

from ab_shared.dest import Dest


def load_rows(dest: Dest) -> list[dict[str, Any]]:
    raw = dest.get("history", "sketches.jsonl")
    if not raw:
        return []
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def get_window_percentiles(
    dest: Dest,
    *,
    tenant: str,
    entity_id: str,
    metric_id: str,
    window: str,
    window_start: str,
) -> dict[str, float] | None:
    for row in load_rows(dest):
        if (
            row["tenant"] == tenant
            and row["entity_id"] == entity_id
            and row["metric_id"] == metric_id
            and row["window"] == window
            and row["window_start"] == window_start
        ):
            cents = row["tdigest"].get("centroids") or []
            # Approximate from stored row via centroid weighted quantile if digest gone
            from sketch.digest import TDigestAdapter

            td = TDigestAdapter()
            for c in cents:
                w = int(max(1, round(c["w"])))
                for _ in range(w):
                    td.update(c["m"])
            if td.sample_count() == 0:
                return None
            return {
                "p50": td.quantile(0.50),
                "p95": td.quantile(0.95),
                "p99": td.quantile(0.99),
                "sample_count": row.get("sample_count", td.sample_count()),
            }
    return None


def get_metric_baseline(
    dest: Dest,
    *,
    tenant: str,
    entity_id: str,
    metric_id: str,
    season_key: str,
    window: str = "5m",
) -> dict[str, float] | None:
    for row in load_rows(dest):
        if (
            row["tenant"] == tenant
            and row["entity_id"] == entity_id
            and row["metric_id"] == metric_id
            and row["season_key"] == season_key
            and row["window"] == window
        ):
            b = row["baseline"]
            return {
                "expected_p50": b["expected_p50"],
                "expected_p95": b["expected_p95"],
                "expected_p99": b["expected_p99"],
            }
    return None
