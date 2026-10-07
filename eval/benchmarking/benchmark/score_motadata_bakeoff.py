#!/usr/bin/env python3
"""L1 — Score Lean vs Federated on Motadata incident packs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKS = REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "incidents"
LEAN = REPO / "benchmarking" / "results" / "lean" / "motadata"
FED = REPO / "benchmarking" / "results" / "federated" / "motadata"
OUT_DIR = REPO / "benchmarking" / "results" / "motadata"


def _pack_ids() -> list[str]:
    return sorted(
        p.name
        for p in PACKS.iterdir()
        if p.is_dir() and (p / "topology.json").is_file()
    )


def _latest_verdict(base: Path, pack_id: str, run_id: str | None) -> tuple[dict | None, Path | None]:
    pack_dir = base / pack_id
    if not pack_dir.is_dir():
        return None, None
    if run_id:
        path = pack_dir / f"run-{run_id}" / "verdict.json"
        if path.is_file():
            return json.loads(path.read_text()), path
        return None, None
    runs = sorted(pack_dir.glob("run-*/verdict.json"), key=lambda p: p.stat().st_mtime)
    if not runs:
        return None, None
    path = runs[-1]
    return json.loads(path.read_text()), path


def _run_meta(verdict_path: Path | None) -> dict:
    if not verdict_path:
        return {}
    meta_path = verdict_path.parent / "run_meta.json"
    if meta_path.is_file():
        return json.loads(meta_path.read_text())
    return {}


def _score(verdict: dict | None, gt: dict, meta: dict) -> dict:
    if not verdict:
        return {
            "status": "missing",
            "root_match": False,
            "signature_match": False,
            "root_ci": None,
            "signature": None,
            "latency_ms": None,
            "fallback_fired": None,
            "observations": None,
            "evidentiary_tier": None,
        }
    root_match = verdict.get("root_ci") == gt.get("root_ci")
    sig_match = verdict.get("signature") == gt.get("signature")
    status = "pass" if root_match and sig_match else ("root_only" if root_match else "fail")
    return {
        "status": status,
        "root_match": root_match,
        "signature_match": sig_match,
        "root_ci": verdict.get("root_ci"),
        "signature": verdict.get("signature"),
        "latency_ms": meta.get("latency_ms"),
        "fallback_fired": verdict.get("fallback_fired"),
        "observations": verdict.get("observations"),
        "evidentiary_tier": verdict.get("evidentiary_tier"),
        "engine": verdict.get("engine"),
    }


def winner_for(lean: dict, fed: dict) -> str:
    if lean["status"] == "missing" and fed["status"] == "missing":
        return "none"
    lean_ok = lean["status"] in {"pass", "root_only"}
    fed_ok = fed["status"] in {"pass", "root_only"}
    # Prefer full pass (root+sig); then root_only; then fail
    order = {"pass": 2, "root_only": 1, "fail": 0, "missing": -1}
    lo, fo = order.get(lean["status"], -1), order.get(fed["status"], -1)
    if lo > fo:
        return "lean"
    if fo > lo:
        return "federated"
    if not lean_ok and not fed_ok:
        return "tie-fail"
    # both same status band: fewer observations wins when available
    lo_obs, fo_obs = lean.get("observations"), fed.get("observations")
    if isinstance(lo_obs, int) and isinstance(fo_obs, int) and lo_obs != fo_obs:
        return "lean" if lo_obs < fo_obs else "federated"
    return "tie"


def build_report(run_id: str | None) -> dict:
    rows = []
    winners = {"lean": 0, "federated": 0, "tie": 0, "tie-fail": 0, "none": 0}
    for pid in _pack_ids():
        gt = json.loads((PACKS / pid / "ground_truth.json").read_text())
        lean_v, lean_path = _latest_verdict(LEAN, pid, run_id)
        fed_v, fed_path = _latest_verdict(FED, pid, run_id)
        lean_s = _score(lean_v, gt, _run_meta(lean_path))
        fed_s = _score(fed_v, gt, _run_meta(fed_path))
        w = winner_for(lean_s, fed_s)
        winners[w] = winners.get(w, 0) + 1
        rows.append(
            {
                "incident_id": pid,
                "ground_truth": {
                    "root_ci": gt.get("root_ci"),
                    "signature": gt.get("signature"),
                    "tags": gt.get("tags"),
                },
                "lean": lean_s,
                "federated": fed_s,
                "winner": w,
            }
        )

    n = len(rows) or 1
    lean_root = sum(1 for r in rows if r["lean"]["root_match"])
    fed_root = sum(1 for r in rows if r["federated"]["root_match"])
    lean_sig = sum(1 for r in rows if r["lean"]["signature_match"])
    fed_sig = sum(1 for r in rows if r["federated"]["signature_match"])
    lean_pass = sum(1 for r in rows if r["lean"]["status"] == "pass")
    fed_pass = sum(1 for r in rows if r["federated"]["status"] == "pass")

    if lean_pass > fed_pass:
        overall = "lean"
    elif fed_pass > lean_pass:
        overall = "federated"
    elif lean_root > fed_root:
        overall = "lean"
    elif fed_root > lean_root:
        overall = "federated"
    else:
        overall = "tie"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus": str(PACKS),
        "run_id_filter": run_id,
        "summary": {
            "overall_better": overall,
            "lean_pass": f"{lean_pass}/{len(rows)}",
            "federated_pass": f"{fed_pass}/{len(rows)}",
            "lean_root_match": f"{lean_root}/{len(rows)}",
            "federated_root_match": f"{fed_root}/{len(rows)}",
            "lean_signature_match": f"{lean_sig}/{len(rows)}",
            "federated_signature_match": f"{fed_sig}/{len(rows)}",
            "per_incident_winners": winners,
            "rationale": (
                f"Full pass (root+signature): Lean {lean_pass}/{len(rows)}, "
                f"Federated {fed_pass}/{len(rows)}. "
                f"Root-only: Lean {lean_root}/{len(rows)}, Federated {fed_root}/{len(rows)}."
            ),
        },
        "rows": rows,
    }


def to_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# Motadata L1 — Lean vs Federated",
        "",
        f"**Corpus:** `{report['corpus']}`",
        f"**Generated:** `{report['generated_at']}`",
        f"**Run id:** `{report['run_id_filter'] or 'latest'}`",
        "",
        "## Verdict",
        "",
        f"**Overall better on this Motadata slice: `{s['overall_better']}`**",
        "",
        s["rationale"],
        "",
        "## Scoreboard",
        "",
        "| Metric | Lean | Federated |",
        "|--------|------|-----------|",
        f"| Full pass (root+sig) | **{s['lean_pass']}** | **{s['federated_pass']}** |",
        f"| Root-CI match | {s['lean_root_match']} | {s['federated_root_match']} |",
        f"| Signature match | {s['lean_signature_match']} | {s['federated_signature_match']} |",
        "",
        "## Per incident",
        "",
        "| Incident | GT root / sig | Lean | Fed | Winner |",
        "|----------|---------------|------|-----|--------|",
    ]
    for row in report["rows"]:
        gt = row["ground_truth"]
        l, f = row["lean"], row["federated"]
        lines.append(
            f"| `{row['incident_id']}` | `{gt['root_ci']}` / `{gt['signature']}` | "
            f"`{l.get('root_ci') or '—'}` / `{l.get('signature') or '—'}` "
            f"({l['status']}) | "
            f"`{f.get('root_ci') or '—'}` / `{f.get('signature') or '—'}` "
            f"({f['status']}) | **{row['winner']}** |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "RUN_ID=motadata-l1-$(date -u +%Y%m%dT%H%M%SZ)",
            ".venv/bin/python benchmarking/benchmark/run_motadata_bakeoff.py --run-id \"$RUN_ID\"",
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score Motadata Lean vs Federated L1")
    parser.add_argument("--run-id", help="Matched run id (recommended)")
    args = parser.parse_args(argv)
    report = build_report(args.run_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "COMPARISON.md").write_text(to_markdown(report))
    (OUT_DIR / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT_DIR / 'COMPARISON.md'}")
    print(f"Overall better: {report['summary']['overall_better']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
