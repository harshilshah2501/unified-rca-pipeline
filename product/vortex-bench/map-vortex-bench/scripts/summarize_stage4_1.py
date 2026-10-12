#!/usr/bin/env python3
"""Summarize Stage 4.1 characterize outputs → report 08 markdown."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # product/vortex-bench
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/stage4/characterize"
REPORT = ROOT / "reports/08-design-v3-stage4_1-properties.md"

rows = []
for props in sorted(OUT.glob("*/properties.json")):
    cell = props.parent.name
    data = json.loads(props.read_text())
    rows.append((cell, data))

lines = [
    "# Report 08 — Design v3 Stage 4.1 graph properties",
    "",
    "Post-generation structural metrics for six synthetic estate families.",
    "These are **modeling assumptions**, not Motadata production claims.",
    "",
    f"Source cells: `{OUT}`",
    "",
    "## Summary table",
    "",
    "| Cell | Family | Nodes | Edges | Mean out | Out max | Out p99 | Top1% share | Reciprocity | Components | Validation |",
    "| ---- | ------ | ----: | ----: | -------: | ------: | ------: | ----------: | ----------: | ---------: | ---------- |",
]
failed = []
for cell, d in rows:
    ok = d.get("validation_ok", False)
    if not ok:
        failed.append((cell, d.get("validation_notes", [])))
    lines.append(
        "| {cell} | {fam} | {n} | {e} | {mean:.2f} | {omax} | {op99} | {top:.3f} | {rec:.3f} | {cc} | {ok} |".format(
            cell=cell,
            fam=d.get("family", ""),
            n=d.get("nodes", 0),
            e=d.get("edges", 0),
            mean=d.get("mean_out_degree", 0),
            omax=d.get("out_max", 0),
            op99=d.get("out_p99", 0),
            top=d.get("top1pct_sources_edge_share", 0),
            rec=d.get("reciprocity", 0),
            cc=d.get("weak_component_count", 0),
            ok="OK" if ok else "FAIL",
        )
    )

lines += ["", "## Validation failures", ""]
if not failed:
    lines.append("None — all characterized cells passed family gates.")
else:
    for cell, notes in failed:
        lines.append(f"- **{cell}**: {notes}")

lines += [
    "",
    "## Notes",
    "",
    "- Mean out-degree target **5** for uniform / hubby / power_law / community; hierarchical / layered record realized means.",
    "- Intra-community share recorded for `community` family when available.",
    "- Stage 4.2 layout screening consumes only families that passed validation.",
    "",
]
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines))
print(f"wrote {REPORT} ({len(rows)} cells)")
