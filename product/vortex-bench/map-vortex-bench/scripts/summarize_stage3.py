#!/usr/bin/env python3
import json
from pathlib import Path
import sys

out_root = Path(sys.argv[1] if len(sys.argv) > 1 else "out/design-v3/stage3")
rows = []
for p in sorted(out_root.glob("*/results.json")):
    r = json.loads(p.read_text())
    for s in r["scenarios"]:
        rows.append(
            {
                "dir": p.parent.name,
                "edges": r["edges"],
                "shape": r["estate_shape"],
                "sort": s["edge_sort"],
                "layout": s["layout"],
                "build_ms": round(s["median"]["build_ms"], 3),
                "p50_total": round(s["p50_total_ms"], 3),
                "p95_total": round(s["p95_total_ms"], 3),
                "query_p50": s.get("query_p50_ms"),
                "query_p95": s.get("query_p95_ms"),
                "peak_rss": s.get("peak_rss_bytes"),
                "correctness_ok": s["correctness_ok"],
                "query_events": s.get("query_events"),
            }
        )

# Pareto-ish table: clustered primary
primary = [x for x in rows if "luster" in x["sort"]]
path = out_root / "stage3-summary.json"
path.write_text(json.dumps({"all": rows, "clustered_primary": primary}, indent=2))
print("layouts at 500k clustered:")
for x in primary:
    if x["edges"] == 500000:
        print(
            f"  {x['shape']:8} {x['layout']:8} build={x['build_ms']:8} "
            f"q_p95={x['query_p95']} rss={x['peak_rss']} ok={x['correctness_ok']}"
        )
print("wrote", path)
