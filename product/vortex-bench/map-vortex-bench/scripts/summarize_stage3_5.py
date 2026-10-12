#!/usr/bin/env python3
import json
from pathlib import Path
import sys

out_root = Path(sys.argv[1] if len(sys.argv) > 1 else "out/design-v3/stage3_5")
rows = []
for p in sorted(out_root.glob("*/results.json")):
    r = json.loads(p.read_text())
    for s in r["scenarios"]:
        qc = s.get("query_by_class") or {}
        rows.append(
            {
                "dir": p.parent.name,
                "edges": r["edges"],
                "shape": r["estate_shape"],
                "sort": s["edge_sort"],
                "layout": s["layout"],
                "reverse_algorithm": s.get("reverse_algorithm"),
                "build_ms": round(s["median"]["build_ms"], 3),
                "p50_total": round(s["p50_total_ms"], 3),
                "fwd_p50": (qc.get("forward_bfs") or {}).get("p50_ms"),
                "fwd_p95": (qc.get("forward_bfs") or {}).get("p95_ms"),
                "rev_p50": (qc.get("reverse_blast") or {}).get("p50_ms"),
                "rev_p95": (qc.get("reverse_blast") or {}).get("p95_ms"),
                "dep_p95": (qc.get("dependency_chain") or {}).get("p95_ms"),
                "agg_p95": (qc.get("aggregate") or {}).get("p95_ms"),
                "peak_rss": s.get("peak_rss_bytes"),
                "correctness_ok": s["correctness_ok"],
                "query_events": s.get("query_events"),
            }
        )

path = out_root / "stage3_5-summary.json"
path.write_text(json.dumps({"rows": rows}, indent=2))
print("=== 500k clustered (per-class) ===")
print(f"{'shape':8} {'layout':8} {'build':>8} {'fwd95':>10} {'rev95':>10} {'algo':<22} ok")
for x in rows:
    if x["edges"] != 500000 or "luster" not in x["sort"]:
        continue
    rss = None if x["peak_rss"] is None else round(x["peak_rss"] / 1e6, 1)
    print(
        f"{x['shape']:8} {x['layout']:8} {x['build_ms']:8} "
        f"{x['fwd_p95']!s:>10} {x['rev_p95']!s:>10} {str(x['reverse_algorithm']):<22} {x['correctness_ok']}"
    )
print("wrote", path)
