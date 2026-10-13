#!/usr/bin/env python3
"""Summarize Action 4 → Report 15."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action4"
REPORT = ROOT / "reports/15-action4-cold-recovery.md"


def fmt(v, d=2):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{d}f}"
    return str(v)


cells = []
for res in sorted(OUT.glob("cells/*/results.json")):
    data = json.loads(res.read_text())
    name = res.parent.name
    for sc in data.get("scenarios", []):
        cells.append((name, sc))

lines = [
    "# Report 15 — Action 4: cold-to-hot recovery (T_ready)",
    "",
    "**Envelope:** approved `motadata_like_hubby` + `scope_policy_mixed`.",
    "Frozen layouts only. `remote_proxy` is a **lab copy+disk-cold proxy**, not Motadata Dest S3.",
    "",
    r"$T_{\mathrm{ready}} = T_{\mathrm{remote\_fetch}} + T_{\mathrm{decode}} + T_{\mathrm{build}} + T_{\mathrm{publish}}$",
    "",
    f"Source: `{OUT}` — {len(cells)} scenario rows.",
    "",
    "## Per-cell T_ready",
    "",
    "| Cell | Layout | Coldness | N | T_ready p50 | T_ready p95 | Build p50 | Decode n+e (med) | Remote fetch (med) | Peak RSS | OK |",
    "| ---- | ------ | -------- | -: | ----------: | ----------: | --------: | ---------------: | -----------------: | -------: | -- |",
]

by = defaultdict(list)
for name, sc in cells:
    med = sc.get("median") or {}
    dec = (med.get("decode_nodes_ms") or 0) + (med.get("decode_edges_ms") or 0)
    lines.append(
        f"| {name} | {sc.get('layout')} | {sc.get('coldness')} | {sc.get('samples')} | "
        f"{fmt(sc.get('t_ready_p50_ms'))} | {fmt(sc.get('t_ready_p95_ms'))} | "
        f"{fmt(sc.get('build_p50_ms'))} | {fmt(dec)} | {fmt(med.get('remote_fetch_ms'))} | "
        f"{sc.get('peak_rss_bytes')} | {sc.get('correctness_ok')} |"
    )
    scale = name.split("-")[0]
    by[(scale, sc.get("coldness"))].append(sc)

lines += ["", "## Fastest T_ready by scale × coldness", ""]
for key in sorted(by.keys()):
    scale, cold = key
    ranked = sorted(by[key], key=lambda s: s.get("t_ready_p50_ms") or 1e18)
    lines.append(f"### {scale} × {cold}")
    lines.append("")
    for i, s in enumerate(ranked, 1):
        lines.append(
            f"{i}. `{s.get('layout')}` — t_ready_p50={fmt(s.get('t_ready_p50_ms'))} "
            f"build_p50={fmt(s.get('build_p50_ms'))} rss={s.get('peak_rss_bytes')}"
        )
    lines.append("")

lines += [
    "## Gate call",
    "",
    "Action 4 distinguishes process-cold (cache may be warm), disk-cold (best-effort page-cache drop), "
    "page-cache-warm, and remote_proxy (local copy proxy). Choose recovery winner by **T_ready**, "
    "not build-only.",
    "",
    "**Status:** filled after run.",
    "",
    "## Links",
    "",
    "- Matrix: [`../design-v3/action4-5-run-matrix.md`](../design-v3/action4-5-run-matrix.md)",
    "- Prior: [Report 14](./14-action3-final-compare.md)",
    "",
]
REPORT.write_text("\n".join(lines) + "\n")
print(f"wrote {REPORT} ({len(cells)} cells)")
