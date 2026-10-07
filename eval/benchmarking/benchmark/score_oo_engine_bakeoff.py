#!/usr/bin/env python3
"""
Score Lean / Federated engine verdicts on OO packs vs Option B GT.

Accuracy (pillar 1): verdict.root_ci matches Option B root_alert (pack ground_truth.root_ci).
Also harvests Verifiability / Efficiency proxies from engine verdict fields.
OpenObserve platform narrative is not scored here (peer track remains separate).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKS = REPO / "datasets" / "openobserve_incidents" / "v1" / "engine_packs"
GT_DIR = REPO / "datasets" / "openobserve_incidents" / "v1" / "ground_truth"
LEAN_OO = REPO / "benchmarking" / "results" / "lean" / "oo"
FED_OO = REPO / "benchmarking" / "results" / "federated" / "oo"
OUT_DIR = REPO / "benchmarking" / "results" / "openobserve"
RESULTS = REPO / "benchmarking" / "results"


def _latest_repro(engine: str) -> dict | None:
    """Prefer newest OO reproducibility report for engine."""
    matches = sorted(RESULTS.glob(f"reproducibility_{engine}_oo_*.json"))
    if not matches:
        return None
    return json.loads(matches[-1].read_text())


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _root_match(pred: str | None, gt: str | None) -> bool:
    p, g = _norm(pred), _norm(gt)
    if not p or not g:
        return False
    if p == g:
        return True
    return g in p or p in g


def _latest_verdict(base: Path, pack_id: str, run_id: str | None) -> dict | None:
    pack_dir = base / pack_id
    if not pack_dir.exists():
        return None
    if run_id:
        path = pack_dir / f"run-{run_id}" / "verdict.json"
        if path.exists():
            return json.loads(path.read_text())
        return None
    runs = sorted(pack_dir.glob("run-*/verdict.json"))
    if not runs:
        return None
    return json.loads(runs[-1].read_text())


def _load_option_b(pack_id: str) -> dict | None:
    path = GT_DIR / f"{pack_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _pack_gt(pack_id: str) -> dict:
    return json.loads((PACKS / pack_id / "ground_truth.json").read_text())


def _pack_ids() -> list[str]:
    return sorted(
        p.name
        for p in PACKS.iterdir()
        if p.is_dir() and (p / "topology.json").exists()
    )


def _score_engine(verdict: dict | None, gt_root: str) -> dict:
    if not verdict:
        return {
            "root_ci": None,
            "root_hit": False,
            "signature": None,
            "evidentiary_tier": None,
            "fallback_fired": None,
            "observations": None,
            "obs_to_convergence": None,
            "naive_bfs_expansions": None,
            "efficiency_ratio": None,
            "causal_verified": None,
            "missing": True,
        }
    return {
        "root_ci": verdict.get("root_ci"),
        "root_hit": _root_match(verdict.get("root_ci"), gt_root),
        "signature": verdict.get("signature"),
        "evidentiary_tier": verdict.get("evidentiary_tier"),
        "fallback_fired": verdict.get("fallback_fired"),
        "observations": verdict.get("observations"),
        "obs_to_convergence": verdict.get("obs_to_convergence"),
        "naive_bfs_expansions": verdict.get("naive_bfs_expansions"),
        "efficiency_ratio": verdict.get("efficiency_ratio"),
        "causal_verified": verdict.get("causal_verified"),
        "missing": False,
    }


def run(run_id: str | None = None) -> dict:
    rows = []
    for pid in _pack_ids():
        pack_gt = _pack_gt(pid)
        opt_b = _load_option_b(pid) or {}
        eligible = bool(pack_gt.get("include_in_accuracy"))
        gt_root = pack_gt.get("root_ci")
        lean = _score_engine(_latest_verdict(LEAN_OO, pid, run_id), gt_root)
        fed = _score_engine(_latest_verdict(FED_OO, pid, run_id), gt_root)
        title = (opt_b.get("title") or pid)
        rows.append(
            {
                "id": pid,
                "title": title,
                "stratum": opt_b.get("stratum"),
                "include_in_accuracy": eligible,
                "gt_root_ci": gt_root,
                "gt_layer": pack_gt.get("root_layer") or opt_b.get("root_layer"),
                "lean": lean,
                "federated": fed,
            }
        )

    eligible_rows = [r for r in rows if r["include_in_accuracy"]]
    n = len(eligible_rows) or 1

    def _acc(eng: str) -> float:
        return sum(1 for r in eligible_rows if r[eng]["root_hit"]) / len(eligible_rows) if eligible_rows else 0.0

    def _avg(eng: str, field: str) -> float | None:
        vals = [
            r[eng][field]
            for r in eligible_rows
            if r[eng].get(field) is not None and not r[eng].get("missing")
        ]
        if not vals:
            return None
        return sum(vals) / len(vals)

    def _pct(eng: str, pred) -> float | None:
        present = [r for r in eligible_rows if not r[eng].get("missing")]
        if not present:
            return None
        return sum(1 for r in present if pred(r[eng])) / len(present)

    lean_repro = _latest_repro("lean")
    fed_repro = _latest_repro("federated")

    def _repro_pct(rep: dict | None) -> float | None:
        if not rep:
            return None
        return float(rep.get("overall_reproducibility_pct"))

    summary = {
        "sample_packs": len(rows),
        "accuracy_n": len(eligible_rows),
        "excluded_n": len(rows) - len(eligible_rows),
        "accuracy": {
            "lean": _acc("lean"),
            "federated": _acc("federated"),
        },
        "verifiability": {
            "lean_fallback_rate": _pct("lean", lambda v: bool(v.get("fallback_fired"))),
            "federated_fallback_rate": _pct(
                "federated", lambda v: bool(v.get("fallback_fired"))
            ),
            "lean_avg_tier": _avg("lean", "evidentiary_tier"),
            "federated_avg_tier": _avg("federated", "evidentiary_tier"),
            "lean_causal_verified_rate": _pct(
                "lean", lambda v: v.get("causal_verified") is True
            ),
        },
        "efficiency": {
            "lean_avg_observations": _avg("lean", "observations"),
            "federated_avg_observations": _avg("federated", "observations"),
            "lean_avg_obs_to_convergence": _avg("lean", "obs_to_convergence"),
            "lean_avg_efficiency_ratio": _avg("lean", "efficiency_ratio"),
        },
        "reproducibility": {
            "lean_overall_pct": _repro_pct(lean_repro),
            "federated_overall_pct": _repro_pct(fed_repro),
            "lean_n": (lean_repro or {}).get("n"),
            "federated_n": (fed_repro or {}).get("n"),
            "lean_packs": (lean_repro or {}).get("pack_count"),
            "federated_packs": (fed_repro or {}).get("pack_count"),
            "definition": (
                "Per pack: N runs, SHA-256(verdict.json); 100% iff all hashes identical."
            ),
        },
        "best_on_accuracy": (
            "lean"
            if _acc("lean") > _acc("federated")
            else ("federated" if _acc("federated") > _acc("lean") else "tie")
        ),
        "pillars_note": (
            "Accuracy vs Option B. Verifiability/Efficiency from verdicts. "
            "Reproducibility = N-run bit-identical verdict hashes (when report present)."
        ),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id_filter": run_id,
        "corpus": str(PACKS),
        "evaluation": {
            "mode": "oo_engine_pack_bakeoff",
            "accuracy_target": "option_b_root_alert_as_root_ci",
            "engines": ["lean", "federated"],
            "openobserve_scored": False,
        },
        "summary": summary,
        "reproducibility_sources": {
            "lean_loaded": bool(lean_repro),
            "federated_loaded": bool(fed_repro),
        },
        "rows": rows,
    }


def to_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# OpenObserve — Lean/Federated engine pack scoreboard",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Corpus:** `{report['corpus']}`  ",
        f"**Run filter:** `{report.get('run_id_filter') or 'latest per pack'}`  ",
        f"**Accuracy N:** {s['accuracy_n']} eligible · **Excluded:** {s['excluded_n']}  ",
        f"**Best on Accuracy:** `{s['best_on_accuracy']}`",
        "",
        "## Pillars in scope",
        "",
        "| Pillar | Status |",
        "|--------|--------|",
        "| **Accuracy** | scored (`root_ci` vs Option B `root_alert`) |",
        "| **Verifiability** | proxies from verdict (tier / fallback / causal) |",
        "| **Efficiency** | proxies from verdict (observations / walk ratio) |",
        "| **Reproducibility** | N-run bit-identical `verdict.json` hashes |",
        "",
        s["pillars_note"],
        "",
        "## Reproducibility (N-run hash stability)",
        "",
        s["reproducibility"]["definition"],
        "",
        "| Engine | Overall | N | Packs scored |",
        "|--------|---------|---|--------------|",
        (
            f"| Lean | {_fmt_repro(s['reproducibility']['lean_overall_pct'])} | "
            f"{s['reproducibility']['lean_n'] or '—'} | "
            f"{s['reproducibility']['lean_packs'] or '—'} |"
        ),
        (
            f"| Federated | {_fmt_repro(s['reproducibility']['federated_overall_pct'])} | "
            f"{s['reproducibility']['federated_n'] or '—'} | "
            f"{s['reproducibility']['federated_packs'] or '—'} |"
        ),
        "",
        "## Accuracy (eligible only)",
        "",
        "| Engine | Root-CI accuracy | Hits |",
        "|--------|------------------|------|",
        (
            f"| Lean | **{s['accuracy']['lean']*100:.0f}%** | "
            f"{int(s['accuracy']['lean']*s['accuracy_n'])}/{s['accuracy_n']} |"
        ),
        (
            f"| Federated | **{s['accuracy']['federated']*100:.0f}%** | "
            f"{int(s['accuracy']['federated']*s['accuracy_n'])}/{s['accuracy_n']} |"
        ),
        "",
        "## Verifiability proxies (eligible, present verdicts)",
        "",
        "| Metric | Lean | Federated |",
        "|--------|------|-----------|",
        (
            f"| Fallback rate | {_fmt_pct(s['verifiability']['lean_fallback_rate'])} | "
            f"{_fmt_pct(s['verifiability']['federated_fallback_rate'])} |"
        ),
        (
            f"| Avg evidentiary tier | {_fmt_num(s['verifiability']['lean_avg_tier'])} | "
            f"{_fmt_num(s['verifiability']['federated_avg_tier'])} |"
        ),
        (
            f"| Causal verified rate | {_fmt_pct(s['verifiability']['lean_causal_verified_rate'])} | — |"
        ),
        "",
        "## Efficiency proxies (eligible)",
        "",
        "| Metric | Lean | Federated |",
        "|--------|------|-----------|",
        (
            f"| Avg observations | {_fmt_num(s['efficiency']['lean_avg_observations'])} | "
            f"{_fmt_num(s['efficiency']['federated_avg_observations'])} |"
        ),
        (
            f"| Avg obs_to_convergence | {_fmt_num(s['efficiency']['lean_avg_obs_to_convergence'])} | — |"
        ),
        (
            f"| Avg efficiency_ratio | {_fmt_num(s['efficiency']['lean_avg_efficiency_ratio'])} | — |"
        ),
        "",
        "## Per-incident (all packs)",
        "",
        "| Title | GT root | Lean | Fed | L✓ | F✓ | Acc? |",
        "|-------|---------|------|-----|----|----|------|",
    ]
    for r in report["rows"]:
        title = (r["title"] or "")[:36]
        lean_r = (r["lean"].get("root_ci") or "—")[:22]
        fed_r = (r["federated"].get("root_ci") or "—")[:22]
        lines.append(
            f"| {title} | `{r['gt_root_ci']}` | `{lean_r}` | `{fed_r}` | "
            f"{'Y' if r['lean']['root_hit'] else 'N'} | "
            f"{'Y' if r['federated']['root_hit'] else 'N'} | "
            f"{'Y' if r['include_in_accuracy'] else 'no'} |"
        )
    lines += [
        "",
        "## How to reproduce",
        "",
        "```bash",
        "python3 benchmarking/benchmark/project_oo_engine_packs.py",
        ".venv/bin/python benchmarking/benchmark/run_oo_engine_bakeoff.py",
        "python3 benchmarking/benchmark/score_oo_engine_bakeoff.py",
        "```",
        "",
        "Peer track (no engine packs): `compare_openobserve.py` · "
        "Convention Accuracy (alert heuristics): `score_openobserve_gt.py`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _fmt_pct(x: float | None) -> str:
    return "—" if x is None else f"{x*100:.0f}%"


def _fmt_repro(x: float | None) -> str:
    """overall_reproducibility_pct is already 0–100."""
    return "—" if x is None else f"**{x:.0f}%**"


def _fmt_num(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="Score a specific bakeoff run id")
    args = parser.parse_args(argv)

    report = run(args.run_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "engine_scoreboard.json"
    md_path = OUT_DIR / "ENGINE_SCOREBOARD.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(to_markdown(report))
    s = report["summary"]
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(
        f"Accuracy L/F {s['accuracy']['lean']:.0%}/{s['accuracy']['federated']:.0%} "
        f"n={s['accuracy_n']} best={s['best_on_accuracy']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
