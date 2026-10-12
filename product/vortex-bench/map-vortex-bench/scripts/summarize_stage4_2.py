#!/usr/bin/env python3
"""Summarize Stage 4.2 screen cells → report 09 crossover candidates."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "map-vortex-bench/out/design-v3/stage4/screen"
REPORT = ROOT / "reports/09-design-v3-stage4_2-screen.md"


def fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def class_p(sc, cls, key):
    qb = sc.get("query_by_class") or {}
    block = qb.get(cls) or {}
    return block.get(key)


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
    "# Report 09 — Design v3 Stage 4.2 layout screen (≤5M)",
    "",
    "**This is a screening report of crossover candidates — not a production architecture recommendation.**",
    "",
    "Identical pre-generated query traces are replayed across layouts for each `(family, scale, profile)`.",
    "Hybrid runs with **zero mutation churn**. Primary edge order is clustered; natural order is a 500k control.",
    "",
    f"Source: `{OUT}` — {len(cells)} scenario rows.",
    "",
    "## Per-cell metrics",
    "",
    "| Cell | Layout | Build ms (med) | Fwd p50 | Fwd p95 | Rev p50 | Rev p95 | Peak RSS | Steady idx B | OK |",
    "| ---- | ------ | -------------: | ------: | ------: | ------: | ------: | -------: | -----------: | -- |",
]

by_regime: dict[tuple, list] = defaultdict(list)
for row in cells:
    sc = row["sc"]
    cell = row["cell"]
    med = sc.get("median") or {}
    build = med.get("build_ms") or 0.0
    lines.append(
        f"| {cell} | {sc.get('layout','')} | {build:.1f} | "
        f"{fmt(class_p(sc,'forward_bfs','p50_ms'))} | {fmt(class_p(sc,'forward_bfs','p95_ms'))} | "
        f"{fmt(class_p(sc,'reverse_blast','p50_ms'))} | {fmt(class_p(sc,'reverse_blast','p95_ms'))} | "
        f"{sc.get('peak_rss_bytes')} | {sc.get('steady_index_bytes')} | {sc.get('correctness_ok')} |"
    )
    parts = cell.split("-")
    scale = parts[0] if parts else ""
    profile = sc.get("workload_profile") or "unknown"
    fam = sc.get("estate_shape") or ""
    by_regime[(profile, fam, scale)].append(sc)

lines += ["", "## Rankings by regime (lowest reverse p95, then build)", ""]
for key in sorted(by_regime.keys()):
    profile, fam, scale = key
    ranked = sorted(
        by_regime[key],
        key=lambda s: (
            class_p(s, "reverse_blast", "p95_ms") or 1e18,
            (s.get("median") or {}).get("build_ms") or 1e18,
        ),
    )
    lines.append(f"### {profile} × {fam} × {scale}")
    lines.append("")
    for i, s in enumerate(ranked, 1):
        lines.append(
            f"{i}. `{s.get('layout')}` — rev_p95={fmt(class_p(s,'reverse_blast','p95_ms'))} "
            f"fwd_p95={fmt(class_p(s,'forward_bfs','p95_ms'))} "
            f"build={fmt((s.get('median') or {}).get('build_ms'))} "
            f"rss={s.get('peak_rss_bytes')} idx={s.get('steady_index_bytes')}"
        )
    lines.append("")

# Crossover heuristics
lines += ["## Crossover candidates", ""]
crossovers = []
for key, group in by_regime.items():
    by_lay = {s.get("layout"): s for s in group}
    hb = by_lay.get("hash_bi")
    cc = by_lay.get("csr_csc")
    h = by_lay.get("hash")
    if hb and cc:
        hb_rev = class_p(hb, "reverse_blast", "p95_ms")
        cc_rev = class_p(cc, "reverse_blast", "p95_ms")
        hb_idx = hb.get("steady_index_bytes") or 0
        cc_idx = cc.get("steady_index_bytes") or 0
        if hb_rev is not None and cc_rev is not None and cc_rev < hb_rev * 0.9:
            crossovers.append(
                f"- `{key}`: `csr_csc` reverse p95 ({cc_rev:.3f}) beats `hash_bi` ({hb_rev:.3f})"
            )
        if cc_idx and hb_idx and cc_idx < hb_idx * 0.85:
            crossovers.append(
                f"- `{key}`: `csr_csc` steady index ({cc_idx}) undercuts `hash_bi` ({hb_idx})"
            )
    if h and hb:
        h_fwd = class_p(h, "forward_bfs", "p95_ms")
        hb_fwd = class_p(hb, "forward_bfs", "p95_ms")
        profile = key[0]
        if profile == "forward_dominant" and h_fwd is not None and hb_fwd is not None:
            h_build = (h.get("median") or {}).get("build_ms") or 0
            hb_build = (hb.get("median") or {}).get("build_ms") or 0
            if h_build < hb_build * 0.9 and h_fwd <= hb_fwd * 1.15:
                crossovers.append(
                    f"- `{key}`: `hash` wins forward-only build ({h_build:.1f} vs hash_bi {hb_build:.1f}) with similar fwd tail"
                )

if crossovers:
    lines.extend(crossovers)
else:
    lines.append(
        "No strong automated crossover flags at the 10%/15% thresholds; inspect rankings above."
    )

# Illustrative break-even using mean reverse latency × Qr sweep
lines += [
    "",
    "## Illustrative index-economics break-even (not a decision lock)",
    "",
    "For each regime with both `hash` and `hash_bi` (or `csr_csc`), estimate "
    "`cost(Qr) ≈ (1−Qr)·mean_fwd + Qr·mean_rev` using **mean** class latencies from the trace. "
    "Labeled **illustrative** only.",
    "",
]

for key, group in sorted(by_regime.items()):
    by_lay = {s.get("layout"): s for s in group}
    if "hash" not in by_lay or "hash_bi" not in by_lay:
        continue
    def means(s):
        qb = s.get("query_by_class") or {}
        # approximate mean ≈ p50 for screening tables when mean not stored
        return (
            (qb.get("forward_bfs") or {}).get("p50_ms") or 0.0,
            (qb.get("reverse_blast") or {}).get("p50_ms") or 0.0,
        )
    hf, hr = means(by_lay["hash"])
    bf, br = means(by_lay["hash_bi"])
    lines.append(f"### {key[0]} × {key[1]} × {key[2]}")
    lines.append("")
    lines.append("| Qr | hash cost | hash_bi cost | cheaper |")
    lines.append("| --: | --------: | -----------: | ------- |")
    for qr_pct in range(0, 101, 10):
        qr = qr_pct / 100.0
        ch = (1 - qr) * hf + qr * hr
        cb = (1 - qr) * bf + qr * br
        win = "hash" if ch <= cb else "hash_bi"
        lines.append(f"| {qr_pct}% | {ch:.3f} | {cb:.3f} | {win} |")
    lines.append("")

lines += [
    "## Skips / failures",
    "",
]
if skips:
    for s in skips:
        lines.append(f"- `{s}`")
else:
    lines.append("None recorded in status.log.")

lines += [
    "",
    "## Explicit non-recommendation",
    "",
    "Do **not** treat this screen as Motadata production topology guidance. "
    "Deferred: concurrency stress, mutation/lifecycle economics, 10M+, Stage 4.3–4.6 confirmation.",
    "",
]

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines))
print(f"wrote {REPORT} ({len(cells)} scenarios)")
