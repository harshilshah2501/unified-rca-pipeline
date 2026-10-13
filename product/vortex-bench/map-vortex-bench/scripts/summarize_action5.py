#!/usr/bin/env python3
"""Summarize Action 5 → Report 16."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action5"
REPORT = ROOT / "reports/16-action5-concurrency.md"


def fmt(v, d=3):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{d}f}"
    return str(v)


cells = []
for res in sorted(OUT.glob("cells/*/results.json")):
    data = json.loads(res.read_text())
    for sc in data.get("scenarios", []):
        cells.append((res.parent.name, sc))

lines = [
    "# Report 16 — Action 5: concurrency and memory",
    "",
    "**Envelope:** approved `motadata_like_hubby` + `scope_policy_mixed`.",
    "Shared-graph concurrent trace replay; dual-index hold on 1M × readers=1 cells.",
    "",
    f"Source: `{OUT}` — {len(cells)} scenario rows.",
    "",
    "## Per-cell concurrency",
    "",
    "| Cell | Layout | Readers | QPS | Lat p50 | Lat p95 | Lat p99 | Peak RSS | Dual-hold RSS | Steady idx | OK |",
    "| ---- | ------ | ------: | --: | ------: | ------: | ------: | -------: | ------------: | ---------: | -- |",
]

by = defaultdict(list)
for name, sc in cells:
    conc = sc.get("concurrent") or {}
    readers = conc.get("readers") or 1
    lines.append(
        f"| {name} | {sc.get('layout')} | {readers} | "
        f"{fmt(conc.get('throughput_qps'), 1)} | {fmt(conc.get('latency_p50_ms'))} | "
        f"{fmt(conc.get('latency_p95_ms'))} | {fmt(conc.get('latency_p99_ms'))} | "
        f"{sc.get('peak_rss_bytes')} | {sc.get('dual_hold_peak_rss_bytes')} | "
        f"{sc.get('steady_index_bytes')} | {sc.get('correctness_ok')} |"
    )
    scale = name.split("-")[0]
    by[(scale, readers)].append((name, sc, conc))

lines += ["", "## Rankings (highest QPS, then lowest p95)", ""]
for key in sorted(by.keys()):
    scale, readers = key
    ranked = sorted(
        by[key],
        key=lambda t: (
            -(t[2].get("throughput_qps") or 0),
            t[2].get("latency_p95_ms") or 1e18,
        ),
    )
    lines.append(f"### {scale} × {readers} readers")
    lines.append("")
    for i, (_n, s, c) in enumerate(ranked, 1):
        lines.append(
            f"{i}. `{s.get('layout')}` — qps={fmt(c.get('throughput_qps'), 1)} "
            f"p95={fmt(c.get('latency_p95_ms'))} p99={fmt(c.get('latency_p99_ms'))} "
            f"rss={s.get('peak_rss_bytes')} dual={s.get('dual_hold_peak_rss_bytes')}"
        )
    lines.append("")

lines += [
    "## Gate call",
    "",
    "Action 5 checks whether the Action 3 provisional winner (`csr_csc`) retains "
    "advantage under concurrent Scope-like replays and dual-index memory pressure.",
    "",
    "**Status:** filled after run.",
    "",
    "## Links",
    "",
    "- Matrix: [`../design-v3/action4-5-run-matrix.md`](../design-v3/action4-5-run-matrix.md)",
    "- Prior: [Report 15](./15-action4-cold-recovery.md)",
    "",
]
REPORT.write_text("\n".join(lines) + "\n")
print(f"wrote {REPORT} ({len(cells)} cells)")
