#!/usr/bin/env python3
"""Summarize Action 1 oracle JSON → reports/12-action1-correctness-oracle.md."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action1"
REPORT = ROOT / "reports/12-action1-correctness-oracle.md"

rows = []
for p in sorted(OUT.glob("*/action1_oracle.json")):
    data = json.loads(p.read_text())
    rows.append((p.parent.name, data))

lines = [
    "# Report 12 — Action 1: independent typed-multigraph correctness oracle",
    "",
    "**Priority:** P0 blocking for the decision-validation sprint.",
    "",
    "This report replaces walk-checksum-only claims with an independent oracle that checks:",
    "",
    "1. Edge counts (generator vs layout forward arcs).",
    "2. Directed typed-edge **multiset** equality (including duplicates).",
    "3. Forward/reverse adjacency symmetry (reverse reconstruction equals forward multiset).",
    "4. Reachable-node equivalence vs hash reference for p10/p50/p90/max_hub × hops {1,2,3} × {forward, reverse}.",
    "5. Both **clustered** and **natural** edge orders.",
    "",
    "Frozen candidates: `hash` · `hash_bi` · `csr_csc`.",
    "",
    f"Source: `{OUT}` — {len(rows)} estate cells.",
    "",
]

if rows:
    lines.append("## Degree-bin definition (confirmed)")
    lines.append("")
    lines.append(rows[0][1].get("degree_bin_definition", "—"))
    lines.append("")

lines += [
    "## Results matrix",
    "",
    "| Cell | Layout | Edge sort | All OK | Failed checks |",
    "| ---- | ------ | --------- | ------ | ------------- |",
]

any_fail = False
for cell, data in rows:
    if not data.get("all_ok", False):
        any_fail = True
    for lay in data.get("layouts", []):
        failed = [c["name"] for c in lay.get("checks", []) if not c.get("ok")]
        ok = lay.get("all_ok", False)
        if not ok:
            any_fail = True
        lines.append(
            f"| {cell} | {lay.get('layout')} | {lay.get('edge_sort')} | "
            f"{'PASS' if ok else 'FAIL'} | {', '.join(failed) if failed else '—'} |"
        )

lines += [
    "",
    "## Exit gate",
    "",
]
if not rows:
    lines.append("No oracle JSON found — run `scripts/action1_oracle.sh` first.")
elif any_fail:
    lines.append(
        "**NOT PASSED.** Failed cells must be fixed and rerun, or excluded with a documented explanation "
        "before Milestone A performance rankings are treated as final."
    )
else:
    lines.append(
        "**PASSED** for the cells in this matrix: every frozen candidate passed the independent oracle "
        "on both clustered and natural order under the listed estates/scales."
    )

lines += [
    "",
    "## Notes",
    "",
    "- Oracle builds layouts from the in-memory Arrow edge batch (same logical multiset); Vortex encode/decode is not on this path.",
    "- Hybrid / segmented layouts are out of scope for Action 1 primary matrix.",
    "- Program: [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md).",
    "",
]

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines))
print(f"wrote {REPORT} ({len(rows)} cells)")
