#!/usr/bin/env python3
"""Summarize Stage 1 2×2 results into stage1-summary.json."""
import json
import sys
from pathlib import Path

out_root = Path(sys.argv[1] if len(sys.argv) > 1 else "out/design-v3/stage1")
rows = []
for p in sorted(out_root.glob("*/results.json")):
    r = json.loads(p.read_text())
    for s in r["scenarios"]:
        rows.append(
            {
                "dir": p.parent.name,
                "shape": r["estate_shape"],
                "sort": s["edge_sort"],
                "builder": s["adj_builder"],
                "p50_total_ms": s["p50_total_ms"],
                "p95_total_ms": s["p95_total_ms"],
                "build_ms": s["median"]["build_ms"],
                "decode_ms": s["median"]["decode_nodes_ms"]
                + s["median"]["decode_edges_ms"],
                "key_clones": s["median"]["profile"]["source_key_clones"],
                "hm_ops": s["median"]["profile"]["hashmap_source_ops"],
                "correctness_ok": s["correctness_ok"],
                "samples": s["samples"],
            }
        )

# Factorial table: for each shape, contrast cells
summary = {"rows": rows, "effects": []}
for shape in ("uniform", "hubby"):
    cells = {
        (x["sort"], x["builder"]): x
        for x in rows
        if x["shape"] == shape
    }
    def g(sort, builder):
        return cells.get((sort, builder)) or cells.get(
            (sort.capitalize() if sort[0].islower() else sort, builder)
        )

    # keys may be "Natural"/"Clustered"
    def find(sort_sub, builder):
        for (s, b), v in cells.items():
            if sort_sub.lower() in s.lower() and b == builder:
                return v
        return None

    nn = find("natural", "naive")
    ns = find("natural", "sort_aware")
    cn = find("clustered", "naive")
    cs = find("clustered", "sort_aware")
    if not all([nn, ns, cn, cs]):
        continue
    order_effect = (nn["build_ms"] - cn["build_ms"]) / nn["build_ms"] * 100
    builder_on_clustered = (cn["build_ms"] - cs["build_ms"]) / cn["build_ms"] * 100
    builder_on_natural = (nn["build_ms"] - ns["build_ms"]) / nn["build_ms"] * 100
    summary["effects"].append(
        {
            "shape": shape,
            "order_effect_pct_faster_clustered_vs_natural_naive": round(order_effect, 2),
            "builder_effect_pct_on_clustered": round(builder_on_clustered, 2),
            "builder_effect_pct_on_natural": round(builder_on_natural, 2),
            "cells": {
                "natural_naive_build_ms": nn["build_ms"],
                "natural_sort_aware_build_ms": ns["build_ms"],
                "clustered_naive_build_ms": cn["build_ms"],
                "clustered_sort_aware_build_ms": cs["build_ms"],
            },
        }
    )

path = out_root / "stage1-summary.json"
path.write_text(json.dumps(summary, indent=2))
print(json.dumps(summary["effects"], indent=2))
print("wrote", path)
