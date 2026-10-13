#!/usr/bin/env python3
"""Summarize Action 6 overlap residual → Report 19."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action6-overlap"
REPORT = ROOT / "reports/19-action6-atomic-publish.md"

cells = []
for res in sorted(OUT.glob("cells/*/action6_overlap_results.json")):
    cells.append((res.parent.name, json.loads(res.read_text())))

lines = [
    "# Report 19 — Action 6 residual: atomic publish + dual-hold memory",
    "",
    "**Milestone A remains frozen.** This does not reopen the three-layout selection.",
    "",
    "Priorities covered: (1) atomic publication with pinned readers; (2) memory amplification during publication.",
    "Still deferred: durability/replay, Motadata mutation realism, 5M thin ladder.",
    "",
    f"Source: `{OUT}` — {len(cells)} cells.",
    "",
    "## Results",
    "",
    "| Cell | Segs | Ins/Del | Readers | Atomic OK | Overlap OK | Gen mismatch | Sym fail | Reader ops | "
    "Single RSS | Max dual-hold RSS | Final RSS |",
    "| ---- | ---: | ------- | ------: | --------- | ---------- | -----------: | -------: | ---------: | "
    "---------: | ----------------: | --------: |",
]

all_ok = True
for name, d in cells:
    batches = d.get("batches") or []
    duals = [b.get("dual_hold_peak_rss_bytes") for b in batches if b.get("dual_hold_peak_rss_bytes")]
    max_dual = max(duals) if duals else None
    ov = d.get("overlap_readers_report") or {}
    ok = bool(d.get("atomic_publish_ok"))
    all_ok = all_ok and ok
    lines.append(
        f"| {name} | {d.get('segments')} | {d.get('mutation_batch_inserts')}/{d.get('mutation_batch_deletes')} | "
        f"{d.get('overlap_readers')} | {ok} | {ov.get('ok')} | {ov.get('generation_mismatches')} | "
        f"{ov.get('symmetry_failures')} | {ov.get('ops')} | {d.get('single_snapshot_rss_bytes')} | "
        f"{max_dual} | {d.get('final_rss_bytes')} |"
    )

lines += [
    "",
    "## Gate call",
    "",
    "Readers must observe a single pinned generation per walk (no mixed forward/reverse generations). "
    "Old pins must remain CSR⇔CSC symmetric after publish. Dual-hold RSS reports peak while old and new "
    "snapshots coexist.",
    "",
    f"**Atomic publish under overlap (this ladder):** {'PASSED' if cells and all_ok else 'FAILED or empty'}.",
    "",
    "Per-segment edge journals remain a **separate** optimization hypothesis (not measured here).",
    "",
    "## Links",
    "",
    "- Spec: [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md)",
    "- Prior: [Report 18](./18-action6-mutation-lifecycle.md)",
    "",
]
REPORT.write_text("\n".join(lines) + "\n")
print(f"wrote {REPORT} ({len(cells)} cells, all_ok={all_ok})")
