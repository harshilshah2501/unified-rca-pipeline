#!/usr/bin/env python3
"""Summarize Action 6 → Report 18."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action6"
REPORT = ROOT / "reports/18-action6-mutation-lifecycle.md"


def pct(xs, p):
    if not xs:
        return None
    ys = sorted(xs)
    i = min(len(ys) - 1, max(0, int(round((p / 100.0) * (len(ys) - 1)))))
    return ys[i]


def fmt(v, d=2):
    if v is None:
        return "—"
    return f"{v:.{d}f}"


cells = []
for res in sorted(OUT.glob("cells/*/action6_results.json")):
    cells.append((res.parent.name, json.loads(res.read_text())))

lines = [
    "# Report 18 — Action 6: mutation lifecycle (Milestone B)",
    "",
    "**Milestone A is frozen.** This report does not reopen `hash` / `hash_bi` / `csr_csc` selection.",
    "",
    "Central question: can **segmented CSR+CSC** preserve conventional CSR+CSC query advantages while reducing "
    r"$T_{\mathrm{mutation\text{-}visible}}$ vs full rebuild?",
    "",
    f"Source: `{OUT}` — {len(cells)} cells.",
    "",
    "## Per-cell summary",
    "",
    "| Cell | Segs | T_cold conv | T_cold seg | Conv T_mut p50 | Seg T_mut p50 | Seg T_mut p95 | Mean segs rebuilt |",
    "| ---- | ---: | ----------: | ---------: | -------------: | ------------: | ------------: | ----------------: |",
]

for name, data in cells:
    conv = [r["t_mutation_visible_ms"] for r in data.get("conventional_batches", [])]
    seg = [r["t_mutation_visible_ms"] for r in data.get("segmented_batches", [])]
    rebuilt = [r.get("segments_rebuilt", 0) for r in data.get("segmented_batches", [])]
    cold = data.get("t_cold_ready_ms") or {}
    lines.append(
        f"| {name} | {data.get('segments')} | {fmt(cold.get('csr_csc'))} | {fmt(cold.get('segmented_csr_csc'))} | "
        f"{fmt(pct(conv, 50))} | {fmt(pct(seg, 50))} | {fmt(pct(seg, 95))} | "
        f"{fmt(statistics.mean(rebuilt) if rebuilt else None, 1)} |"
    )

lines += [
    "",
    "## Gate call",
    "",
    "Compare T_mutation_visible distributions and retained query behavior. "
    "Segmented wins only if mutation visibility improves **without** undoing Milestone A query/memory advantages.",
    "",
    "**Status:** filled after first Action 6 ladder.",
    "",
    "## Links",
    "",
    "- Spec: [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md)",
    "- Milestone A: [Report 17](./17-milestone-a-close.md)",
    "",
]
REPORT.write_text("\n".join(lines) + "\n")
print(f"wrote {REPORT} ({len(cells)} cells)")
