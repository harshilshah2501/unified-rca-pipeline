"""E5 Maintain (Pillar A side) — seasonal baseline refresh from sketch history.

Independent of Pillar B edge validity. Not a package merge with Topology.
"""

from __future__ import annotations

import json
from typing import Any

from ab_shared.dest import Dest
from sketch.baseline import SeasonalBaseline
from sketch.digest import TDigestAdapter
from sketch.sketch_flush import SketchWriter


def _rows_from_dest(dest: Dest) -> list[dict[str, Any]]:
    raw = dest.get("history", "sketches.jsonl")
    if not raw:
        return []
    rows: list[dict[str, Any]] = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def refresh_seasonal_baselines(writer: SketchWriter, dest: Dest) -> dict[tuple, SeasonalBaseline]:
    """Rebuild writer.baselines from durable sketch rows on Dest (history/).

    Groups by (tenant, entity_id, metric_id, window) so 1m/5m stay separate.
    Each row contributes digest percentiles into its season_key history.
    """
    rebuilt: dict[tuple, SeasonalBaseline] = {}
    for row in _rows_from_dest(dest):
        bkey = writer._baseline_key(
            row["tenant"], row["entity_id"], row["metric_id"], row["window"]
        )
        acc = rebuilt.setdefault(bkey, SeasonalBaseline())
        dig = TDigestAdapter.from_json_body(row.get("tdigest") or {})
        acc.observe(
            row["season_key"],
            dig.quantile(0.50),
            dig.quantile(0.95),
            dig.quantile(0.99),
        )
    writer.baselines = rebuilt
    return rebuilt
