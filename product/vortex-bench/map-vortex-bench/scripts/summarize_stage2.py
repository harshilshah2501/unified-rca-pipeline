#!/usr/bin/env python3
import json
import statistics
from collections import defaultdict
from pathlib import Path
import sys

out_root = Path(sys.argv[1] if len(sys.argv) > 1 else "out/design-v3/stage2")
rows = []
query_lats = defaultdict(list)
for p in sorted(out_root.glob("*/results.json")):
    r = json.loads(p.read_text())
    for s in r["scenarios"]:
        rows.append(
            {
                "dir": p.parent.name,
                "edges": r["edges"],
                "shape": r["estate_shape"],
                "sort": s["edge_sort"],
                "builder": s["adj_builder"],
                "load": s["load_mode"],
                "build_ms": s["median"]["build_ms"],
                "decode_ms": s["median"]["decode_nodes_ms"]
                + s["median"]["decode_edges_ms"],
                "p50_total": s["p50_total_ms"],
                "p95_total": s["p95_total_ms"],
                "query_p50": s.get("query_p50_ms"),
                "query_p95": s.get("query_p95_ms"),
            }
        )
    for qf in p.parent.glob("*-queries.jsonl"):
        for line in qf.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            key = (r["estate_shape"], e["seed_degree_bin"], e["type"])
            query_lats[str(key)].append(e["latency_ms"])

# Rank: mean build speedup clustered vs natural under naive @ spine
effects = []
by = defaultdict(dict)
for row in rows:
    if row["load"] != "spine":
        continue
    key = (row["edges"], row["shape"], row["builder"])
    by[key][row["sort"]] = row

for key, sorts in sorted(by.items()):
    nat = next((v for k, v in sorts.items() if "atural" in k), None)
    clu = next((v for k, v in sorts.items() if "luster" in k), None)
    if not nat or not clu:
        continue
    pct = (nat["build_ms"] - clu["build_ms"]) / nat["build_ms"] * 100
    effects.append(
        {
            "edges": key[0],
            "shape": key[1],
            "builder": key[2],
            "clustered_build_pct_faster": round(pct, 2),
            "decode_share_clustered": round(
                clu["decode_ms"] / max(clu["p50_total"], 1e-9), 3
            ),
        }
    )

# Builder effect on clustered
builder_fx = []
by2 = defaultdict(dict)
for row in rows:
    if row["load"] != "spine" or "luster" not in row["sort"]:
        continue
    key = (row["edges"], row["shape"])
    by2[key][row["builder"]] = row
for key, builders in sorted(by2.items()):
    n = builders.get("naive")
    s = builders.get("sort_aware")
    if n and s:
        pct = (n["build_ms"] - s["build_ms"]) / n["build_ms"] * 100
        builder_fx.append(
            {
                "edges": key[0],
                "shape": key[1],
                "sort_aware_pct_faster_on_clustered": round(pct, 2),
            }
        )

q_summary = {
    k: {
        "n": len(v),
        "p50": statistics.median(v),
        "p95": sorted(v)[max(0, int(round(0.95 * (len(v) - 1))))],
    }
    for k, v in query_lats.items()
    if v
}

out = {
    "order_effects": effects,
    "builder_on_clustered": builder_fx,
    "query_latency_by_shape_bin_type": q_summary,
    "row_count": len(rows),
}
path = out_root / "stage2-summary.json"
path.write_text(json.dumps(out, indent=2))
print(json.dumps({k: out[k] for k in ("order_effects", "builder_on_clustered")}, indent=2)[:2000])
print("wrote", path)