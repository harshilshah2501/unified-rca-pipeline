#!/usr/bin/env python3
"""Summarize Action 6 5M thin ladder → fragment for Report 21."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action6-5m"
REPORT = ROOT / "reports/21-action6-5m-thin-ladder.md"


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
    "# Report 21a — Action 6 priority 5: 5M thin ladder",
    "",
    "**Envelope:** approved [`../design-v3/action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md).",
    "Milestone A remain frozen. Consolidated decision: [Report 21](./21-action6-milestone-b-close.md).",
    "",
    f"Source: `{OUT}` — {len(cells)} cells.",
    "",
    "| Cell | Segs | Ins/Del | T_cold conv | T_cold seg | Conv T_mut p50 | Seg T_mut p50 | Mean segs rebuilt | Seg/Conv ratio |",
    "| ---- | ---: | ------- | ----------: | ---------: | -------------: | ------------: | ----------------: | -------------: |",
]

for name, data in cells:
    conv = [r["t_mutation_visible_ms"] for r in data.get("conventional_batches", [])]
    seg = [r["t_mutation_visible_ms"] for r in data.get("segmented_batches", [])]
    rebuilt = [r.get("segments_rebuilt", 0) for r in data.get("segmented_batches", [])]
    cold = data.get("t_cold_ready_ms") or {}
    cp, sp = pct(conv, 50), pct(seg, 50)
    ratio = (sp / cp) if cp and sp and cp > 0 else None
    lines.append(
        f"| {name} | {data.get('segments')} | "
        f"{data.get('mutation_batch_inserts')}/{data.get('mutation_batch_deletes')} | "
        f"{fmt(cold.get('csr_csc'))} | {fmt(cold.get('segmented_csr_csc'))} | "
        f"{fmt(cp)} | {fmt(sp)} | "
        f"{fmt(statistics.mean(rebuilt) if rebuilt else None, 1)} | {fmt(ratio, 2)} |"
    )

lines += [
    "",
    "## Gate notes",
    "",
    "Ratio < 1.0 means segmented mutation visibility is faster than conventional full rebuild.",
    "",
    "## Links",
    "",
    "- Envelope: [`../design-v3/action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md)",
    "- Prior: [Report 18](./18-action6-mutation-lifecycle.md)",
    "",
]
REPORT.write_text("\n".join(lines) + "\n")
print(f"wrote {REPORT} ({len(cells)} cells)")
