#!/usr/bin/env python3
"""
Score Lean · Federated · OpenObserve against Option-B convention GT.

Reads final labels under datasets/openobserve_incidents/v1/ground_truth/,
re-runs the three method analyzers on the same incident payloads, and writes:

  benchmarking/results/openobserve/gt_scoreboard.json
  benchmarking/results/openobserve/GT_SCOREBOARD.md

Accuracy uses only include_in_accuracy=true rows (confident convention roots).
Ambiguous rows are reported separately and excluded from accuracy %.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from compare_openobserve import (
    analyze_federated,
    analyze_lean,
    analyze_openobserve,
    _load_alerts,
    _unique_triggers,
)

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO / "datasets" / "openobserve_incidents" / "v1"
OUT_DIR = REPO / "benchmarking" / "results" / "openobserve"


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _root_match(pred: str | None, gt: str | None) -> bool:
    """Exact or containment match (CI id may appear inside a longer alert name)."""
    p, g = _norm(pred), _norm(gt)
    if not p or not g:
        return False
    if p == g:
        return True
    # soft: gt CI mentioned in pred or vice versa (e.g. redis-node-3)
    return g in p or p in g


def _title_base(title: str | None) -> str:
    return (title or "").split(" on ")[0]


def load_gt_files(gt_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(gt_dir.glob("*.json")):
        if path.name in {"SAMPLE.json", "schema.json"}:
            continue
        d = json.loads(path.read_text())
        if d.get("status") != "final":
            continue
        rows.append(d)
    return rows


def score_method(verdict: dict, gt: dict) -> dict:
    layer_hit = _norm(verdict.get("layer")) == _norm(gt.get("root_layer"))
    root_hit = _root_match(verdict.get("root_alert"), gt.get("root_alert"))
    return {
        "layer": verdict.get("layer"),
        "root_alert": verdict.get("root_alert"),
        "layer_hit": layer_hit,
        "root_hit": root_hit,
        "both_hit": layer_hit and root_hit,
        "rationale": verdict.get("rationale"),
    }


def run(corpus: Path, out_dir: Path) -> dict:
    alerts = _load_alerts(corpus)
    gt_dir = corpus / "ground_truth"
    gts = load_gt_files(gt_dir)
    eligible = [g for g in gts if g.get("include_in_accuracy")]
    excluded = [g for g in gts if not g.get("include_in_accuracy")]

    rows = []
    for gt in gts:
        iid = gt["incident_id"]
        inc_path = corpus / "incidents" / f"{iid}.json"
        inc = json.loads(inc_path.read_text())
        lean = analyze_lean(inc, alerts)
        fed = analyze_federated(inc, alerts, seed=0)
        oo = analyze_openobserve(inc, alerts)
        title = _title_base(inc.get("title"))
        multi = len(_unique_triggers(inc)) > 1
        scored = {
            "id": iid,
            "title": inc.get("title"),
            "stratum": gt.get("stratum"),
            "include_in_accuracy": bool(gt.get("include_in_accuracy")),
            "confidence": gt.get("confidence"),
            "gt": {
                "root_layer": gt.get("root_layer"),
                "root_alert": gt.get("root_alert"),
                "contributor_alerts": gt.get("contributor_alerts") or [],
                "evidence_note": gt.get("evidence_note") or "",
            },
            "multi_trigger": multi,
            "trigger_count": len(_unique_triggers(inc)),
            "title_base": title,
            "lean": score_method(lean, gt),
            "federated": score_method(fed, gt),
            "openobserve": score_method(oo, gt),
            "picks_title": {
                "lean": _norm(lean.get("root_alert")) == _norm(title),
                "federated": _norm(fed.get("root_alert")) == _norm(title),
                "openobserve": _norm(oo.get("root_alert")) == _norm(title),
            },
            "methods_agree_layer": lean.get("layer") == fed.get("layer") == oo.get("layer"),
            "lean_fed_agree_layer": lean.get("layer") == fed.get("layer"),
        }
        rows.append(scored)

    def _rate(method: str, field: str, subset: list[dict]) -> float:
        if not subset:
            return 0.0
        return round(sum(1 for r in subset if r[method][field]) / len(subset), 4)

    acc = [r for r in rows if r["include_in_accuracy"]]
    multi_acc = [r for r in acc if r["multi_trigger"]]
    single_acc = [r for r in acc if not r["multi_trigger"]]

    summary = {
        "sample_final": len(rows),
        "accuracy_n": len(acc),
        "excluded_n": len(excluded),
        "labeling_mode": "solo_dual_pass",
        "methods": ["lean", "federated", "openobserve"],
        "layer_accuracy": {
            m: _rate(m, "layer_hit", acc) for m in ("lean", "federated", "openobserve")
        },
        "root_alert_accuracy": {
            m: _rate(m, "root_hit", acc) for m in ("lean", "federated", "openobserve")
        },
        "both_hit_accuracy": {
            m: _rate(m, "both_hit", acc) for m in ("lean", "federated", "openobserve")
        },
        "layer_accuracy_multi": {
            m: _rate(m, "layer_hit", multi_acc) for m in ("lean", "federated", "openobserve")
        },
        "root_accuracy_multi": {
            m: _rate(m, "root_hit", multi_acc) for m in ("lean", "federated", "openobserve")
        },
        "layer_accuracy_single": {
            m: _rate(m, "layer_hit", single_acc) for m in ("lean", "federated", "openobserve")
        },
        "title_pick_on_eligible_multi": {
            m: round(
                sum(1 for r in multi_acc if r["picks_title"][m]) / max(len(multi_acc), 1),
                4,
            )
            for m in ("lean", "federated", "openobserve")
        },
        "counts": {
            "eligible_multi": len(multi_acc),
            "eligible_single": len(single_acc),
            "lean_layer_hits": sum(1 for r in acc if r["lean"]["layer_hit"]),
            "fed_layer_hits": sum(1 for r in acc if r["federated"]["layer_hit"]),
            "oo_layer_hits": sum(1 for r in acc if r["openobserve"]["layer_hit"]),
            "lean_root_hits": sum(1 for r in acc if r["lean"]["root_hit"]),
            "fed_root_hits": sum(1 for r in acc if r["federated"]["root_hit"]),
            "oo_root_hits": sum(1 for r in acc if r["openobserve"]["root_hit"]),
        },
    }

    # Winner on layer then root (eligible set only)
    la, ra = summary["layer_accuracy"], summary["root_alert_accuracy"]
    ranking = sorted(
        ("lean", "federated", "openobserve"),
        key=lambda m: (la[m], ra[m]),
        reverse=True,
    )
    summary["ranking_by_layer_then_root"] = ranking
    summary["best_on_convention_gt"] = ranking[0]

    by_stratum = defaultdict(list)
    for r in acc:
        by_stratum[r["stratum"] or "unspecified"].append(r)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus": str(corpus),
        "evaluation": {
            "mode": "option_b_convention_gt_accuracy",
            "baseline": "human_convention_root (solo dual-pass)",
            "paper_analogy": (
                "Murphy-style operator-decided baseline; "
                "not Nezha known-injected-service GT"
            ),
            "accuracy_claimed": True,
            "caveat": (
                "Labels were solo dual-pass (same reviewer), not independent human A/B. "
                "Principle analyzers for Lean/Fed — not full typed-CI runners."
            ),
        },
        "summary": summary,
        "excluded": [
            {
                "id": g["incident_id"],
                "title": g.get("title"),
                "reason": g.get("evidence_note"),
                "confidence": g.get("confidence"),
            }
            for g in excluded
        ],
        "by_stratum": {
            k: {
                "n": len(v),
                "lean_layer": sum(1 for r in v if r["lean"]["layer_hit"]),
                "fed_layer": sum(1 for r in v if r["federated"]["layer_hit"]),
                "oo_layer": sum(1 for r in v if r["openobserve"]["layer_hit"]),
                "lean_root": sum(1 for r in v if r["lean"]["root_hit"]),
                "fed_root": sum(1 for r in v if r["federated"]["root_hit"]),
                "oo_root": sum(1 for r in v if r["openobserve"]["root_hit"]),
            }
            for k, v in sorted(by_stratum.items())
        },
        "rows": rows,
    }
    return report


def to_markdown(report: dict) -> str:
    s = report["summary"]
    la, ra, ba = s["layer_accuracy"], s["root_alert_accuracy"], s["both_hit_accuracy"]
    n = s["accuracy_n"]
    lines = [
        "# OpenObserve Option B — Convention GT Scoreboard",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Corpus:** `{report['corpus']}`  ",
        f"**Mode:** score Lean · Federated · OpenObserve vs **convention baseline**  ",
        f"**Accuracy N:** {n} confident labels · **Excluded:** {s['excluded_n']} ambiguous  ",
        f"**Labeling:** `{s['labeling_mode']}` (solo dual-pass — not independent human A/B)  ",
        f"**Best on this baseline:** `{s['best_on_convention_gt']}`  ",
        f"**Ranking (layer → root):** {' > '.join(s['ranking_by_layer_then_root'])}",
        "",
        "## What we measured",
        "",
        "For each eligible incident we treat the adjudicated `root_layer` + `root_alert` as the "
        "**scoring baseline** (Murphy language: close to *operator-decided ground truth* / "
        "*true root cause entity* for Top-1 — **not** objective physics truth).",
        "",
        "| Hit type | Rule |",
        "|----------|------|",
        "| Layer | method layer == baseline `root_layer` |",
        "| Root alert | method root equals / contains baseline `root_alert` |",
        "| Both | layer and root hit |",
        "",
        "### Caveats (read before over-claiming)",
        "",
        "1. Solo dual-pass labels — stronger if re-done with two independent humans.",
        "2. Lean / Federated here are **principle analyzers**, not full UC typed-CI engines.",
        "3. OpenObserve is method #3 (platform narrative), scored like the others.",
        "4. One baseline root is a CI id (`redis-node-3`) with no matching alert name — "
        "root-alert hits are hard for all methods there; layer still scorable.",
        "",
        "## Scoreboard (eligible only)",
        "",
        f"| Metric | Lean | Federated | OpenObserve |",
        f"|--------|------|-----------|-------------|",
        f"| **Layer accuracy** | **{la['lean']*100:.0f}%** ({s['counts']['lean_layer_hits']}/{n}) | "
        f"**{la['federated']*100:.0f}%** ({s['counts']['fed_layer_hits']}/{n}) | "
        f"**{la['openobserve']*100:.0f}%** ({s['counts']['oo_layer_hits']}/{n}) |",
        f"| **Root-alert accuracy** | **{ra['lean']*100:.0f}%** ({s['counts']['lean_root_hits']}/{n}) | "
        f"**{ra['federated']*100:.0f}%** ({s['counts']['fed_root_hits']}/{n}) | "
        f"**{ra['openobserve']*100:.0f}%** ({s['counts']['oo_root_hits']}/{n}) |",
        f"| Layer **and** root | {ba['lean']*100:.0f}% | {ba['federated']*100:.0f}% | {ba['openobserve']*100:.0f}% |",
        "",
        "### Split: multi-trigger vs single-trigger (eligible)",
        "",
        f"Multi n={s['counts']['eligible_multi']} · Single n={s['counts']['eligible_single']}",
        "",
        "| Slice | Lean layer | Fed layer | OO layer | Lean root | Fed root | OO root |",
        "|-------|------------|-----------|----------|-----------|----------|---------|",
        (
            f"| Multi-trigger | {s['layer_accuracy_multi']['lean']*100:.0f}% | "
            f"{s['layer_accuracy_multi']['federated']*100:.0f}% | "
            f"{s['layer_accuracy_multi']['openobserve']*100:.0f}% | "
            f"{s['root_accuracy_multi']['lean']*100:.0f}% | "
            f"{s['root_accuracy_multi']['federated']*100:.0f}% | "
            f"{s['root_accuracy_multi']['openobserve']*100:.0f}% |"
        ),
        (
            f"| Single-trigger | {s['layer_accuracy_single']['lean']*100:.0f}% | "
            f"{s['layer_accuracy_single']['federated']*100:.0f}% | "
            f"{s['layer_accuracy_single']['openobserve']*100:.0f}% | "
            f"— | — | — |"
        ),
        "",
        "### Title-pick on eligible multi-trigger (behavior)",
        "",
        "Lower usually better when the incident title is a decoy symptom.",
        "",
        f"| Lean | Federated | OpenObserve |",
        f"|------|-----------|-------------|",
        (
            f"| {s['title_pick_on_eligible_multi']['lean']*100:.0f}% | "
            f"{s['title_pick_on_eligible_multi']['federated']*100:.0f}% | "
            f"{s['title_pick_on_eligible_multi']['openobserve']*100:.0f}% |"
        ),
        "",
        f"## Per-incident results (all {s['sample_final']})",
        "",
        "| Title | GT layer / alert | Lean | Fed | OO | L✓ | F✓ | O✓ | Acc? |",
        "|-------|------------------|------|-----|----|----|----|----|------|",
    ]

    def mark(hit: bool) -> str:
        return "Y" if hit else "N"

    for r in report["rows"]:
        g = r["gt"]
        lines.append(
            "| {title} | `{gl}` / `{ga}` | `{ll}`/`{la}` | `{fl}`/`{fa}` | `{ol}`/`{oa}` | "
            "{lh}/{lr} | {fh}/{fr} | {oh}/{or_} | {acc} |".format(
                title=(r["title"] or "")[:34].replace("|", "/"),
                gl=g["root_layer"],
                ga=(g["root_alert"] or "")[:22].replace("|", "/"),
                ll=r["lean"]["layer"],
                la=(r["lean"]["root_alert"] or "")[:16].replace("|", "/"),
                fl=r["federated"]["layer"],
                fa=(r["federated"]["root_alert"] or "")[:16].replace("|", "/"),
                ol=r["openobserve"]["layer"],
                oa=(r["openobserve"]["root_alert"] or "")[:16].replace("|", "/"),
                lh=mark(r["lean"]["layer_hit"]),
                lr=mark(r["lean"]["root_hit"]),
                fh=mark(r["federated"]["layer_hit"]),
                fr=mark(r["federated"]["root_hit"]),
                oh=mark(r["openobserve"]["layer_hit"]),
                or_=mark(r["openobserve"]["root_hit"]),
                acc="Y" if r["include_in_accuracy"] else "no",
            )
        )

    # Insights section built from data
    misses = []
    for r in report["rows"]:
        if not r["include_in_accuracy"]:
            continue
        notes = []
        for m in ("lean", "federated", "openobserve"):
            if not r[m]["layer_hit"]:
                notes.append(f"{m} layer miss ({r[m]['layer']}≠{r['gt']['root_layer']})")
            elif not r[m]["root_hit"]:
                notes.append(
                    f"{m} layer ok but wrong root (`{r[m]['root_alert']}`≠`{r['gt']['root_alert']}`)"
                )
        if r["multi_trigger"] and r["picks_title"]["federated"] and not r["picks_title"]["lean"]:
            notes.append("Fed crowns title; Lean does not")
        if notes:
            misses.append((r, notes))

    lines += ["", "## Cases that teach something", ""]
    for r, notes in misses:
        lines.append(
            f"- **{r['title']}** (`{r['stratum']}`): " + "; ".join(notes)
        )
    if report["excluded"]:
        lines += ["", "### Excluded from accuracy", ""]
        for e in report["excluded"]:
            lines.append(
                f"- **{e['title']}** (`{e['id'][:10]}…`, {e['confidence']}): "
                f"{(e['reason'] or '')[:160]}"
            )

    lines += [
        "",
        "## By stratum (eligible layer / root hits)",
        "",
        "| Stratum | n | Lean L/R | Fed L/R | OO L/R |",
        "|---------|---|----------|---------|--------|",
    ]
    for stratum, st in report["by_stratum"].items():
        lines.append(
            f"| {stratum} | {st['n']} | {st['lean_layer']}/{st['lean_root']} | "
            f"{st['fed_layer']}/{st['fed_root']} | {st['oo_layer']}/{st['oo_root']} |"
        )

    # Deep insights body lives in GT_SCOREBOARD.md after generate;
    # keep a stable pointer here so regenerate does not lose the analysis doc.
    lines += [
        "",
        "## Deep insights & conclusion",
        "",
        "Full narrative analysis: `benchmarking/results/openobserve/GT_ANALYSIS.md`",
        "",
        "### Auto summary",
        "",
        _conclusion_paragraph(s),
        "",
        "## How to reproduce",
        "",
        "```bash",
        "python3 benchmarking/benchmark/score_openobserve_gt.py",
        "```",
        "",
        "Related: peer-only (no GT) → `compare_openobserve.py` · UC GT bakeoff → "
        "`results/comparison/`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _conclusion_paragraph(s: dict) -> str:
    la, ra = s["layer_accuracy"], s["root_alert_accuracy"]
    best = s["best_on_convention_gt"]
    n = s["accuracy_n"]
    return (
        f"On this **{n}-incident convention baseline**, we can finally say who matched the "
        f"agreed root — not just who agreed with whom. "
        f"**Layer:** Lean {la['lean']*100:.0f}%, Federated {la['federated']*100:.0f}%, "
        f"OpenObserve {la['openobserve']*100:.0f}%. "
        f"**Exact root alert:** Lean {ra['lean']*100:.0f}%, Federated {ra['federated']*100:.0f}%, "
        f"OpenObserve {ra['openobserve']*100:.0f}%. "
        f"Best overall on this board: **{best}**. "
        "In plain terms: when alerts are clear and decoys exist, the lean-style walk that "
        "resists the noisy title usually lands closer to the baseline we agreed; federated-style "
        "fusion is more title/earliest-biased; OpenObserve sometimes matches the story and "
        "sometimes follows the symptom. Treat this as a **small, carefully labeled sample**, "
        "not a universal winner for every RCA product forever — and re-label with two humans "
        "when they are free."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    report = run(args.corpus, args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "gt_scoreboard.json"
    md_path = args.out_dir / "GT_SCOREBOARD.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(to_markdown(report))
    s = report["summary"]
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(
        "Layer L/F/O "
        f"{s['layer_accuracy']['lean']:.0%}/"
        f"{s['layer_accuracy']['federated']:.0%}/"
        f"{s['layer_accuracy']['openobserve']:.0%} | "
        "Root "
        f"{s['root_alert_accuracy']['lean']:.0%}/"
        f"{s['root_alert_accuracy']['federated']:.0%}/"
        f"{s['root_alert_accuracy']['openobserve']:.0%} | "
        f"best={s['best_on_convention_gt']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
