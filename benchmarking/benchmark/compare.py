#!/usr/bin/env python3
"""Compare federated vs lean on the same ObserveOps corpus → bakeoff report.

Flow:
  1. Both engines run on datasets/observeops/UC-1..UC-5 (identical bundles)
  2. Per-engine verdicts land under results/federated/ and results/lean/
  3. This script scores both against ground truth and writes a comparative analysis
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "observeops"
RESULTS = REPO / "benchmarking" / "results"
FED = REPO / "benchmarking" / "results" / "federated"
LEAN = REPO / "benchmarking" / "results" / "lean"
OUT_DIR = REPO / "benchmarking" / "results" / "comparison"

INFRA_PREFIXES = ("esxi-", "switch-", "datastore-", "vm-", "guest-os-")


def find_verdict(base: Path, uc_id: str, run_id: str | None) -> tuple[dict | None, Path | None]:
    uc_dir = base / uc_id
    if not uc_dir.exists():
        return None, None
    if run_id:
        path = uc_dir / f"run-{run_id}" / "verdict.json"
        if path.exists():
            return json.loads(path.read_text()), path
        return None, None
    runs = sorted(uc_dir.glob("run-*/verdict.json"))
    if not runs:
        return None, None
    return json.loads(runs[-1].read_text()), runs[-1]


def _load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _pct(value: Any) -> float | None:
    """Normalize harness fractions and percentages to percentage points."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value * 100 if 0 <= value <= 1 else value)


def find_reproducibility(engine: str, run_id: str | None) -> tuple[dict, Path | None]:
    """Find a reproducibility harness output without rerunning the harness."""
    preferred = RESULTS / f"reproducibility_{engine}_full-repro.json"
    if preferred.exists():
        return _load_json(preferred) or {}, preferred

    candidates = list(RESULTS.glob(f"reproducibility_{engine}_*.json"))
    if not candidates:
        return {}, None
    if run_id:
        matching = [path for path in candidates if run_id.startswith(
            path.stem.removeprefix(f"reproducibility_{engine}_")
        )]
        if matching:
            candidates = matching
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return _load_json(latest) or {}, latest


def _run_meta(verdict_path: Path | None) -> dict:
    if not verdict_path:
        return {}
    return _load_json(verdict_path.parent / "run_meta.json") or {}


def _latency_from_meta(meta: dict) -> tuple[float | None, str | None]:
    """Return only explicitly recorded latency or hop-total values (RCA-only)."""
    for field in ("latency_ms", "total_latency_ms", "hop_total_ms", "hop_totals"):
        value = meta.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value), field
    return None, None


def _detect_from_meta(meta: dict) -> tuple[float | None, float | None, str | None]:
    """Return detect_latency_ms, system_latency_ms, detect_source."""
    detect = meta.get("detect_latency_ms")
    system = meta.get("system_latency_ms")
    source = meta.get("detect_source")
    detect_f = (
        float(detect)
        if isinstance(detect, (int, float)) and not isinstance(detect, bool)
        else None
    )
    system_f = (
        float(system)
        if isinstance(system, (int, float)) and not isinstance(system, bool)
        else None
    )
    src = source if isinstance(source, str) else None
    return detect_f, system_f, src


def score_uc(
    uc_id: str,
    verdict: dict | None,
    ground_truth: dict,
    verdict_path: Path | None = None,
) -> dict:
    if not verdict:
        return {
            "status": "missing",
            "root_match": False,
            "signature_match": False,
            "contributor_match": False,
            "uc5_fp": False,
            "root_ci": None,
            "signature": None,
            "tier": None,
            "fallback_fired": None,
            "observations": None,
            "obs_to_convergence": None,
            "naive_bfs_expansions": None,
            "efficiency_ratio": None,
            "causal_verified": None,
            "evidence_count": None,
            "has_evidence": None,
            "main_path": None,
            "latency_ms": None,
            "latency_source": None,
            "detect_latency_ms": None,
            "system_latency_ms": None,
            "detect_source": None,
            "pipeline_profile": None,
        }

    root_match = verdict.get("root_ci") == ground_truth["root_ci"]
    signature_match = verdict.get("signature") == ground_truth.get("signature")
    gt_contrib = set(ground_truth.get("contributor_cis") or [])
    got_contrib = set(verdict.get("contributor_cis") or [])
    contributor_match = gt_contrib <= got_contrib if gt_contrib else True
    uc5_fp = False
    if uc_id == "UC-5":
        root = verdict.get("root_ci", "")
        uc5_fp = any(root.startswith(p) for p in INFRA_PREFIXES)
        if ground_truth.get("upstream_healthy") and uc5_fp:
            uc5_fp = True

    status = "pass" if root_match and not uc5_fp and contributor_match else "fail"
    evidence = verdict.get("evidence")
    fallback_fired = verdict.get("fallback_fired")
    meta = _run_meta(verdict_path)
    latency_ms, latency_source = _latency_from_meta(meta)
    detect_latency_ms, system_latency_ms, detect_source = _detect_from_meta(meta)
    return {
        "status": status,
        "root_match": root_match,
        "signature_match": signature_match,
        "contributor_match": contributor_match,
        "uc5_fp": uc5_fp,
        "root_ci": verdict.get("root_ci"),
        "signature": verdict.get("signature"),
        "tier": verdict.get("evidentiary_tier"),
        "fallback_fired": fallback_fired,
        "observations": verdict.get("observations"),
        "obs_to_convergence": verdict.get("obs_to_convergence"),
        "naive_bfs_expansions": verdict.get("naive_bfs_expansions"),
        "efficiency_ratio": verdict.get("efficiency_ratio"),
        "causal_verified": verdict.get("causal_verified"),
        "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
        "has_evidence": bool(evidence) if isinstance(evidence, list) else False,
        "main_path": not fallback_fired if isinstance(fallback_fired, bool) else None,
        "latency_ms": latency_ms,
        "latency_source": latency_source,
        "detect_latency_ms": detect_latency_ms,
        "system_latency_ms": system_latency_ms,
        "detect_source": detect_source,
        "pipeline_profile": meta.get("pipeline_profile"),
        "engine": verdict.get("engine"),
    }


def winner_for_uc(fed: dict, lean: dict) -> str:
    if fed["status"] == "missing" and lean["status"] == "missing":
        return "none"
    if fed["status"] == "pass" and lean["status"] != "pass":
        return "federated"
    if lean["status"] == "pass" and fed["status"] != "pass":
        return "lean"
    if fed["status"] != "pass" and lean["status"] != "pass":
        return "tie-fail"
    # Both pass: observation count is the primary efficiency tie-break; recorded
    # latency is used only if counts cannot decide. Otherwise the result is a tie.
    fo, lo = fed.get("observations"), lean.get("observations")
    if isinstance(fo, int) and isinstance(lo, int) and fo != lo:
        return "federated" if fo < lo else "lean"
    fl, ll = fed.get("latency_ms"), lean.get("latency_ms")
    if isinstance(fl, (int, float)) and isinstance(ll, (int, float)) and fl != ll:
        return "federated" if fl < ll else "lean"
    return "tie"


def _mean(values: list[float | int]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _engine_axes(rows: list[dict], engine: str, repro: dict) -> dict:
    scores = [row[engine] for row in rows]
    available = [score for score in scores if score["status"] != "missing"]
    reproducibility = {
        row["uc_id"]: _pct((repro.get(row["uc_id"]) or {}).get("reproducibility_pct"))
        for row in rows
    }
    repro_values = [value for value in reproducibility.values() if value is not None]
    observations = [
        score["observations"]
        for score in available
        if isinstance(score.get("observations"), int)
    ]
    latencies = [
        score["latency_ms"]
        for score in available
        if isinstance(score.get("latency_ms"), (int, float))
    ]
    detect_latencies = [
        score["detect_latency_ms"]
        for score in available
        if isinstance(score.get("detect_latency_ms"), (int, float))
    ]
    system_latencies = [
        score["system_latency_ms"]
        for score in available
        if isinstance(score.get("system_latency_ms"), (int, float))
    ]
    tier_counts: dict[str, int] = {}
    for score in available:
        tier = score.get("tier")
        if tier is not None:
            tier_counts[str(tier)] = tier_counts.get(str(tier), 0) + 1
    total = len(available)
    main_path = sum(score.get("main_path") is True for score in available)
    fallback = sum(score.get("fallback_fired") is True for score in available)
    evidence = sum(score.get("has_evidence") is True for score in available)
    signatures = sum(score.get("signature_match") is True for score in available)
    return {
        "accuracy": {
            "root_ci_pass": sum(score["status"] == "pass" for score in scores),
            "total_use_cases": 5,
            "uc5_infra_false_positives": sum(score["uc5_fp"] for score in scores),
        },
        "reproducibility": {
            "per_uc_pct": reproducibility,
            "overall_reproducibility_pct": _mean(repro_values),
            "reported_use_cases": len(repro_values),
        },
        "verifiability": {
            "evaluated_verdicts": total,
            "main_path_count": main_path,
            "fallback_count": fallback,
            "unknown_path_count": total - main_path - fallback,
            "main_path_pct": round(main_path * 100 / total, 2) if total else None,
            "fallback_pct": round(fallback * 100 / total, 2) if total else None,
            "with_evidence_count": evidence,
            "with_evidence_pct": round(evidence * 100 / total, 2) if total else None,
            "signature_match_count": signatures,
            "signature_match_pct": round(signatures * 100 / total, 2) if total else None,
            "evidentiary_tier_counts": tier_counts,
        },
        "efficiency": {
            "average_observations": _mean(observations),
            "observation_samples": len(observations),
            "average_obs_to_convergence": _mean(
                [
                    score["obs_to_convergence"]
                    for score in available
                    if isinstance(score.get("obs_to_convergence"), int)
                ]
            ),
            "average_naive_bfs_expansions": _mean(
                [
                    score["naive_bfs_expansions"]
                    for score in available
                    if isinstance(score.get("naive_bfs_expansions"), int)
                ]
            ),
            "average_efficiency_ratio": _mean(
                [
                    score["efficiency_ratio"]
                    for score in available
                    if isinstance(score.get("efficiency_ratio"), (int, float))
                ]
            ),
            "average_latency_ms": _mean(latencies),
            "latency_samples": len(latencies),
            "latency_sources": sorted(
                {
                    score["latency_source"]
                    for score in available
                    if score.get("latency_source")
                }
            ),
            "average_detect_latency_ms": _mean(detect_latencies),
            "average_system_latency_ms": _mean(system_latencies),
            "detect_sources": sorted(
                {
                    score["detect_source"]
                    for score in available
                    if score.get("detect_source")
                }
            ),
        },
    }


def build_report(run_id: str | None) -> dict:
    rows = []
    winners = {"federated": 0, "lean": 0, "tie": 0, "tie-fail": 0, "none": 0}

    for i in range(1, 6):
        uc = f"UC-{i}"
        gt = json.loads((CORPUS / uc / "ground_truth.json").read_text())
        fed_v, fed_path = find_verdict(FED, uc, run_id)
        lean_v, lean_path = find_verdict(LEAN, uc, run_id)
        fed_s = score_uc(uc, fed_v, gt, fed_path)
        lean_s = score_uc(uc, lean_v, gt, lean_path)
        win = winner_for_uc(fed_s, lean_s)
        winners[win] = winners.get(win, 0) + 1
        rows.append(
            {
                "uc_id": uc,
                "ground_truth": {
                    "root_ci": gt["root_ci"],
                    "signature": gt.get("signature"),
                },
                "federated": {**fed_s, "verdict_path": str(fed_path) if fed_path else None},
                "lean": {**lean_s, "verdict_path": str(lean_path) if lean_path else None},
                "winner": win,
            }
        )

    fed_repro, fed_repro_path = find_reproducibility("federated", run_id)
    lean_repro, lean_repro_path = find_reproducibility("lean", run_id)
    axes = {
        "federated": _engine_axes(rows, "federated", fed_repro),
        "lean": _engine_axes(rows, "lean", lean_repro),
    }
    fed_pass = axes["federated"]["accuracy"]["root_ci_pass"]
    lean_pass = axes["lean"]["accuracy"]["root_ci_pass"]
    if fed_pass > lean_pass:
        overall = "federated"
    elif lean_pass > fed_pass:
        overall = "lean"
    elif winners["federated"] > winners["lean"]:
        overall = "federated"
    elif winners["lean"] > winners["federated"]:
        overall = "lean"
    else:
        overall = "tie"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "corpus": str(CORPUS.relative_to(REPO)),
        "run_id_filter": run_id,
        "reproducibility_sources": {
            "federated": str(fed_repro_path.relative_to(REPO)) if fed_repro_path else None,
            "lean": str(lean_repro_path.relative_to(REPO)) if lean_repro_path else None,
        },
        "axes": axes,
        "summary": {
            "federated_pass": f"{fed_pass}/5",
            "lean_pass": f"{lean_pass}/5",
            "federated_signature_match": (
                f"{axes['federated']['verifiability']['signature_match_count']}/5"
            ),
            "lean_signature_match": (
                f"{axes['lean']['verifiability']['signature_match_count']}/5"
            ),
            "per_uc_winners": winners,
            "overall_better": overall,
            "rationale": _overall_rationale(overall, fed_pass, lean_pass, winners),
            "winner_tie_break_policy": (
                "Accuracy (root-CI match with UC-5 infrastructure false-positive guard), "
                "then fewer observations, then lower explicitly recorded latency; otherwise tie."
            ),
        },
        "rows": rows,
    }


def _overall_rationale(overall: str, fed_pass: int, lean_pass: int, winners: dict) -> str:
    if fed_pass == lean_pass == 5 and overall == "lean":
        return (
            f"Both engines are 5/5 on root-CI accuracy and signatures; "
            f"lean wins more per-UC tie-breaks on observation count "
            f"({winners.get('lean', 0)} vs federated {winners.get('federated', 0)}; "
            f"ties={winners.get('tie', 0)})."
        )
    if fed_pass == lean_pass == 5 and overall == "federated":
        return (
            f"Both engines are 5/5 on root-CI accuracy and signatures; "
            f"federated wins more per-UC tie-breaks on observation count "
            f"({winners.get('federated', 0)} vs lean {winners.get('lean', 0)}; "
            f"ties={winners.get('tie', 0)})."
        )
    if overall == "tie":
        return (
            f"Both engines match ground-truth root on {fed_pass}/5 UCs equally; "
            "no decisive accuracy or efficiency gap on this corpus."
        )
    if overall == "federated":
        return (
            f"Federated leads on accuracy ({fed_pass}/5 vs lean {lean_pass}/5) "
            f"and/or per-UC wins ({winners.get('federated', 0)} vs {winners.get('lean', 0)})."
        )
    return (
        f"Lean leads on accuracy ({lean_pass}/5 vs federated {fed_pass}/5) "
        f"and/or per-UC wins ({winners.get('lean', 0)} vs {winners.get('federated', 0)})."
    )


def _display(value: Any, suffix: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def _verifiability_note(score: dict) -> str:
    if score["status"] == "missing":
        return "missing"
    path = (
        "main"
        if score.get("main_path") is True
        else "CARE"
        if score.get("fallback_fired") is True
        else "path unknown"
    )
    causal = score.get("causal_verified")
    causal_bit = (
        f"; causal {'Y' if causal else 'N'}"
        if isinstance(causal, bool)
        else ""
    )
    evidence = score.get("evidence_count")
    return (
        f"tier {score.get('tier') if score.get('tier') is not None else '—'}; "
        f"{path}{causal_bit}; evidence {evidence if evidence is not None else '—'}; "
        f"sig {'Y' if score.get('signature_match') else 'N'}"
    )


def to_markdown(report: dict) -> str:
    s = report["summary"]
    axes = report["axes"]
    fa, la = axes["federated"], axes["lean"]
    lines = [
        "# Federated vs Lean — Comparative Analysis",
        "",
        f"**Corpus:** `{report['corpus']}` (identical bundles for both engines)",
        f"**Generated:** `{report['generated_at']}`",
    ]
    if report["run_id_filter"]:
        lines.append(f"**Matched run id:** `{report['run_id_filter']}`")
    else:
        lines.append("**Runs compared:** latest `run-*/verdict.json` per engine/UC")
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"**Overall better on this corpus: `{s['overall_better']}`**",
            "",
            s["rationale"],
            "",
            "## Scoreboard",
            "",
            "| Metric | Federated | Lean |",
            "|--------|-----------|------|",
            f"| Root-CI accuracy | **{s['federated_pass']}** | **{s['lean_pass']}** |",
            f"| Signature match | {s['federated_signature_match']} | {s['lean_signature_match']} |",
            "",
            "## Four-axis scoreboard",
            "",
            "| Axis | Federated | Lean |",
            "|------|-----------|------|",
            (
                f"| Accuracy | {fa['accuracy']['root_ci_pass']}/5 root-CI; "
                f"UC-5 infra FP {fa['accuracy']['uc5_infra_false_positives']} | "
                f"{la['accuracy']['root_ci_pass']}/5 root-CI; "
                f"UC-5 infra FP {la['accuracy']['uc5_infra_false_positives']} |"
            ),
            (
                f"| Reproducibility | {_display(fa['reproducibility']['overall_reproducibility_pct'], '%')} "
                f"({fa['reproducibility']['reported_use_cases']}/5 reported) | "
                f"{_display(la['reproducibility']['overall_reproducibility_pct'], '%')} "
                f"({la['reproducibility']['reported_use_cases']}/5 reported) |"
            ),
            (
                f"| Verifiability | main {fa['verifiability']['main_path_count']}/"
                f"{fa['verifiability']['evaluated_verdicts']}; fallback "
                f"{fa['verifiability']['fallback_count']}; evidence "
                f"{fa['verifiability']['with_evidence_count']}/"
                f"{fa['verifiability']['evaluated_verdicts']} | main "
                f"{la['verifiability']['main_path_count']}/{la['verifiability']['evaluated_verdicts']}; "
                f"fallback {la['verifiability']['fallback_count']}; evidence "
                f"{la['verifiability']['with_evidence_count']}/"
                f"{la['verifiability']['evaluated_verdicts']} |"
            ),
            (
                f"| Efficiency | avg observations {_display(fa['efficiency']['average_observations'])}; "
                f"avg RCA {_display(fa['efficiency']['average_latency_ms'], ' ms')}; "
                f"avg detect {_display(fa['efficiency'].get('average_detect_latency_ms'), ' ms')}; "
                f"avg system {_display(fa['efficiency'].get('average_system_latency_ms'), ' ms')} | "
                f"avg observations {_display(la['efficiency']['average_observations'])}; "
                f"best-first {_display(la['efficiency'].get('average_obs_to_convergence'))} vs "
                f"naive BFS {_display(la['efficiency'].get('average_naive_bfs_expansions'))} "
                f"(ratio {_display(la['efficiency'].get('average_efficiency_ratio'))}); "
                f"avg RCA {_display(la['efficiency']['average_latency_ms'], ' ms')}; "
                f"avg detect {_display(la['efficiency'].get('average_detect_latency_ms'), ' ms')}; "
                f"avg system {_display(la['efficiency'].get('average_system_latency_ms'), ' ms')} |"
            ),
            "",
            (
                "Reproducibility inputs: federated "
                f"`{report['reproducibility_sources']['federated'] or 'not found'}`; lean "
                f"`{report['reproducibility_sources']['lean'] or 'not found'}`."
            ),
            "Main path means `fallback_fired: false`; CARE sets fallback and may promote to Tier 3 when `causal_verified`.",
            "Lean efficiency ratio = naive_bfs_expansions / max(obs_to_convergence, 1).",
            "Parity profile: shared threshold detect (`detect_latency_ms`) + RCA (`latency_ms`); "
            "`system_latency_ms` = detect + RCA. See `docs/PIPELINE_PARITY.md`.",
            "",
            "## Per use-case",
            "",
            "| UC | Ground truth | Federated | Lean | Repro F/L | Verifiability F/L | Winner |",
            "|----|--------------|-----------|------|-----------|---------------------|--------|",
        ]
    )
    for row in report["rows"]:
        gt = row["ground_truth"]["root_ci"]
        f, l = row["federated"], row["lean"]
        fr = fa["reproducibility"]["per_uc_pct"][row["uc_id"]]
        lr = la["reproducibility"]["per_uc_pct"][row["uc_id"]]
        lines.append(
            f"| {row['uc_id']} | `{gt}` | `{f.get('root_ci') or '—'}` | `{l.get('root_ci') or '—'}` | "
            f"{_display(fr, '%')}/{_display(lr, '%')} | "
            f"{_verifiability_note(f)} / {_verifiability_note(l)} | "
            f"**{row['winner']}** |"
        )

    lines.extend(
        [
            "",
            "## Efficiency and winner policy",
            "",
            s["winner_tie_break_policy"],
            "",
            "| UC | Fed observations | Lean observations | Lean best-first | Lean naive BFS | Ratio | Fed latency | Lean latency |",
            "|----|------------------|-------------------|-----------------|----------------|-------|-------------|--------------|",
        ]
    )
    for row in report["rows"]:
        f, l = row["federated"], row["lean"]
        lines.append(
            f"| {row['uc_id']} | {_display(f.get('observations'))} | "
            f"{_display(l.get('observations'))} | "
            f"{_display(l.get('obs_to_convergence'))} | "
            f"{_display(l.get('naive_bfs_expansions'))} | "
            f"{_display(l.get('efficiency_ratio'))} | "
            f"{_display(f.get('latency_ms'), ' ms')} | {_display(l.get('latency_ms'), ' ms')} |"
        )

    # Parity timing table (detect + RCA + system)
    lines.extend(
        [
            "",
            "## Parity timings (shared detect + RCA)",
            "",
            "| UC | Detect | Fed RCA | Lean RCA | Fed system | Lean system | Hop-1 component |",
            "|----|--------|---------|----------|------------|-------------|-----------------|",
        ]
    )
    for row in report["rows"]:
        f, l = row["federated"], row["lean"]
        detect = f.get("detect_latency_ms")
        if detect is None:
            detect = l.get("detect_latency_ms")
        lines.append(
            f"| {row['uc_id']} | {_display(detect, ' ms')} | "
            f"{_display(f.get('latency_ms'), ' ms')} | {_display(l.get('latency_ms'), ' ms')} | "
            f"{_display(f.get('system_latency_ms'), ' ms')} | {_display(l.get('system_latency_ms'), ' ms')} | "
            f"`{f.get('detect_source') or l.get('detect_source') or '—'}` |"
        )

    lines.extend(
        [
            "",
            "## How to reproduce",
            "",
            "```bash",
            "RUN_ID=bakeoff-$(date -u +%Y%m%dT%H%M%SZ)",
            "# Prefer repo .venv (numpy + PyYAML). Shared threshold detect is on by default.",
            ".venv/bin/python benchmarking/benchmark/run_lean.py --all --run-id \"$RUN_ID\"",
            ".venv/bin/python benchmarking/benchmark/run_federated.py --all --run-id \"$RUN_ID\"",
            ".venv/bin/python benchmarking/benchmark/compare.py --run-id \"$RUN_ID\"",
            "```",
            "",
            "Parity contract: [PIPELINE_PARITY.md](../../../docs/PIPELINE_PARITY.md)",
            "Bakeoff metric contract: [COMPARISON_BENCHMARK.md](../../../datasets/observeops/COMPARISON_BENCHMARK.md)",
            "",
            "Machine-readable: `comparison.json` alongside this file.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Comparative analysis: federated vs lean on the same dataset"
    )
    parser.add_argument(
        "--run-id",
        help="Compare only this matched run id for both engines (recommended)",
    )
    args = parser.parse_args(argv)

    report = build_report(args.run_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUT_DIR / "COMPARISON.md"
    json_path = OUT_DIR / "comparison.json"
    md_path.write_text(to_markdown(report))
    json_path.write_text(json.dumps(report, indent=2) + "\n")

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"Overall better: {report['summary']['overall_better']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
