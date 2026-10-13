#!/usr/bin/env python3
"""Summarize Action 6 durability → Report 20."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action6-durability"
REPORT = ROOT / "reports/20-action6-durability-replay.md"

cells = []
for res in sorted(OUT.glob("cells/*/action6_durability_results.json")):
    cells.append((res.parent.name, json.loads(res.read_text())))

lines = [
    "# Report 20 — Action 6 priority 3: durability and replay (lab model)",
    "",
    "**Milestone A remains frozen.** Per-segment journals are out of scope.",
    "",
    "Lab durability model: durable `committed_gen` + `pending_batch` markers with crash injection "
    "at publication boundaries. **Not** Motadata's production commit protocol.",
    "",
    f"Source: `{OUT}` — {len(cells)} cells.",
    "",
]

all_ok = True
for name, d in cells:
    all_ok = all_ok and bool(d.get("all_ok"))
    lines += [
        f"## Cell `{name}`",
        "",
        f"Segments={d.get('segments')}, batch inserts/deletes="
        f"{d.get('mutation_batch_inserts')}/{d.get('mutation_batch_deletes')}, "
        f"all_ok={d.get('all_ok')}.",
        "",
        "| Crash point | OK | Gen before→after (expect) | Replayed | Lost | Recovery ms | Multiset | Sym | Notes |",
        "| ----------- | -- | ------------------------: | -------: | ---: | ----------: | -------- | --- | ----- |",
    ]
    for c in d.get("cases") or []:
        lines.append(
            f"| `{c.get('crash_point')}` | {c.get('ok')} | "
            f"{c.get('committed_generation_before')}→{c.get('committed_generation_after_recovery')} "
            f"({c.get('expected_generation')}) | {c.get('mutations_replayed')} | "
            f"{c.get('mutations_lost')} | {c.get('recovery_ms'):.1f} | "
            f"{c.get('oracle_multiset_ok')} | {c.get('symmetry_ok')} | {c.get('notes')} |"
        )
    lines.append("")

lines += [
    "## Gate call",
    "",
    "For each injected failure point, recovery must yield the expected committed generation and "
    "typed-edge multiset, keep CSR⇔CSC symmetry, and never serve an incomplete snapshot as committed.",
    "",
    f"**Priority 3 lab ladder:** {'PASSED' if cells and all_ok else 'FAILED or empty'}.",
    "",
    "Still open for Action 6: Motadata mutation realism (priority 4), 5M thin ladder (priority 5).",
    "",
    "## Links",
    "",
    "- Spec: [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md)",
    "- Prior: [Report 19](./19-action6-atomic-publish.md)",
    "",
]
REPORT.write_text("\n".join(lines) + "\n")
print(f"wrote {REPORT} ({len(cells)} cells, all_ok={all_ok})")
