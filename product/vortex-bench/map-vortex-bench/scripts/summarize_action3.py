#!/usr/bin/env python3
"""Summarize Action 3 cells → Report 14 (envelope-conditional winner)."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/action3"
REPORT = ROOT / "reports/14-action3-final-compare.md"


def fmt(v, digits=3):
    if v is None:
        return "—"
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return "—"
        return f"{v:.{digits}f}"
    return str(v)


def class_p(sc, cls, key):
    qb = sc.get("query_by_class") or {}
    block = qb.get(cls) or {}
    return block.get(key)


def envelope_score(sc):
    """0.7 fwd + 0.2 rev + 0.1 dep on class p95 (matches approved mix weights)."""
    f = class_p(sc, "forward_bfs", "p95_ms")
    r = class_p(sc, "reverse_blast", "p95_ms")
    d = class_p(sc, "dependency_chain", "p95_ms")
    if f is None or r is None or d is None:
        return None
    return 0.7 * f + 0.2 * r + 0.1 * d


cells = []
for res in sorted(OUT.glob("cells/*/results.json")):
    data = json.loads(res.read_text())
    name = res.parent.name
    for sc in data.get("scenarios", []):
        cells.append({"cell": name, "report": data, "sc": sc})

skips = []
status = OUT / "status.log"
if status.exists():
    for line in status.read_text().splitlines():
        if line.startswith(("FAIL", "SKIP", "PREP_FAIL")):
            skips.append(line)

lines = [
    "# Report 14 — Action 3: final three-layout comparison",
    "",
    "**Envelope:** approved Action 2 `motadata_like_hubby` + `scope_policy_mixed` "
    "(70% forward / 20% reverse / 10% dependency; hops=2 on the mixed profile). "
    "Winners are **envelope-conditional**, not Motadata-wide locks.",
    "",
    "Frozen candidates: `hash` · `hash_bi` · `csr_csc`.",
    "",
    f"Source: `{OUT}` — {len(cells)} scenario rows.",
    "",
    "## Coverage",
    "",
    "- **1M:** `uniform` + `hubby` × "
    "`forward_dominant` / `balanced` / `reverse_heavy` / `scope_policy_mixed` × 3 layouts "
    "(clustered; build repeats ≥ 20).",
    "- **1M natural control:** `hubby` × `scope_policy_mixed` × 3 layouts.",
    "- **5M thin ladder:** `uniform` + `hubby` × `scope_policy_mixed` × 3 layouts "
    "(build repeats ≥ 10).",
    "",
    "## Per-cell metrics",
    "",
    "| Cell | Layout | N | Build p50 | Build p95 | Fwd p95 | Rev p95 | Dep p95 | "
    "Env score | Peak RSS | Steady idx B | OK |",
    "| ---- | ------ | -: | --------: | --------: | ------: | ------: | ------: | "
    "--------: | -------: | -----------: | -- |",
]

by_regime: dict[tuple, list] = defaultdict(list)
for row in cells:
    sc = row["sc"]
    cell = row["cell"]
    score = envelope_score(sc)
    lines.append(
        f"| {cell} | {sc.get('layout','')} | {sc.get('samples','')} | "
        f"{fmt(sc.get('build_p50_ms'))} | {fmt(sc.get('build_p95_ms'))} | "
        f"{fmt(class_p(sc,'forward_bfs','p95_ms'))} | "
        f"{fmt(class_p(sc,'reverse_blast','p95_ms'))} | "
        f"{fmt(class_p(sc,'dependency_chain','p95_ms'))} | "
        f"{fmt(score)} | {sc.get('peak_rss_bytes')} | {sc.get('steady_index_bytes')} | "
        f"{sc.get('correctness_ok')} |"
    )
    profile = sc.get("workload_profile") or "unknown"
    fam = sc.get("estate_shape") or ""
    scale = cell.split("-")[0] if cell else ""
    order = "natural" if "-natural-" in cell else "clustered"
    by_regime[(scale, fam, profile, order)].append((cell, sc, score))

lines += ["", "## Rankings by regime (lowest envelope-weighted p95)", ""]
for key in sorted(by_regime.keys()):
    scale, fam, profile, order = key
    ranked = sorted(
        by_regime[key],
        key=lambda t: (
            t[2] if t[2] is not None else 1e18,
            t[1].get("build_p50_ms") or 1e18,
            t[1].get("peak_rss_bytes") or 1e18,
        ),
    )
    lines.append(f"### {scale} × {fam} × {profile} × {order}")
    lines.append("")
    for i, (cell, s, score) in enumerate(ranked, 1):
        lines.append(
            f"{i}. `{s.get('layout')}` — env={fmt(score)} "
            f"fwd_p95={fmt(class_p(s,'forward_bfs','p95_ms'))} "
            f"rev_p95={fmt(class_p(s,'reverse_blast','p95_ms'))} "
            f"build_p50={fmt(s.get('build_p50_ms'))} "
            f"rss={s.get('peak_rss_bytes')} idx={s.get('steady_index_bytes')}"
        )
    lines.append("")

# Primary decision cells: hubby × scope_policy_mixed clustered
lines += ["## Envelope decision table (`hubby` × `scope_policy_mixed`)", ""]
for scale in ("1M", "5M"):
    key = (scale, "hubby", "scope_policy_mixed", "clustered")
    rows = by_regime.get(key, [])
    if not rows:
        lines.append(f"- **{scale}:** no cells yet.")
        continue
    ranked = sorted(
        rows,
        key=lambda t: (t[2] if t[2] is not None else 1e18, t[1].get("build_p50_ms") or 1e18),
    )
    winner = ranked[0]
    lines.append(
        f"- **{scale} latency winner (env score):** `{winner[1].get('layout')}` "
        f"(env={fmt(winner[2])}; N={winner[1].get('samples')})."
    )
    mem = sorted(rows, key=lambda t: t[1].get("steady_index_bytes") or 1e18)
    lines.append(
        f"- **{scale} leanest steady index:** `{mem[0][1].get('layout')}` "
        f"({mem[0][1].get('steady_index_bytes')} B)."
    )
    build = sorted(rows, key=lambda t: t[1].get("build_p50_ms") or 1e18)
    lines.append(
        f"- **{scale} fastest build p50:** `{build[0][1].get('layout')}` "
        f"({fmt(build[0][1].get('build_p50_ms'))} ms)."
    )
lines.append("")

if skips:
    lines += ["## Skips / failures", ""]
    for s in skips[:80]:
        lines.append(f"- `{s}`")
    lines.append("")

lines += [
    "## Gate call",
    "",
    "Relative performance and memory trade-offs among `hash` / `hash_bi` / `csr_csc` "
    "are reported with build-repeat distributions (p50/p95) under the **approved** "
    "Action 2 envelope. Query latency uses one identical replayed trace per cell "
    "(last build); build uncertainty comes from N repeats.",
    "",
    "**Status:** see sprint / gates after this report is reviewed.",
    "",
    "## Links",
    "",
    "- Program: [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md)",
    "- Envelope: [`../design-v3/action2-synthetic-operating-envelope.md`](../design-v3/action2-synthetic-operating-envelope.md)",
    "- Prior: [Report 13](./13-action2-operating-envelope.md)",
    "",
]

REPORT.write_text("\n".join(lines) + "\n")
print(f"wrote {REPORT} ({len(cells)} cells)")
