#!/usr/bin/env python3
"""Comparative Lean vs Federated bakeoff for the e-com cross-NUMA scenario only."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "ecom_checkout" / "incidents"
PACK_ID = "ecom-numa-001"
OUT = REPO / "benchmarking" / "results" / "ecom"
PY = REPO / ".venv" / "bin" / "python"
if not PY.is_file():
    PY = Path(sys.executable)


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(REPO), check=True)


def _latest_verdict(base: Path, run_id: str | None) -> tuple[dict | None, Path | None]:
    pack_dir = base / PACK_ID
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


def _score(verdict: dict | None, gt: dict, meta: dict) -> dict:
    if not verdict:
        return {
            "status": "missing",
            "root_match": False,
            "signature_match": False,
            "root_ci": None,
            "signature": None,
            "latency_ms": meta.get("latency_ms"),
            "fallback_fired": None,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("ecom-%Y%m%dT%H%M%SZ"),
    )
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args(argv)

    pack = CORPUS / PACK_ID
    if not (pack / "topology.json").is_file():
        print(f"ERROR: pack missing at {pack}", file=sys.stderr)
        return 1

    if not args.skip_run:
        for engine in ("run_lean.py", "run_federated.py"):
            _run(
                [
                    str(PY),
                    f"benchmarking/benchmark/{engine}",
                    "--corpus",
                    str(CORPUS),
                    "--uc",
                    PACK_ID,
                    "--run-id",
                    args.run_id,
                    "--no-shared-detect",
                ]
            )

    gt = json.loads((pack / "ground_truth.json").read_text())
    lean_v, lean_path = _latest_verdict(
        REPO / "benchmarking" / "results" / "lean" / "ecom", args.run_id
    )
    fed_v, fed_path = _latest_verdict(
        REPO / "benchmarking" / "results" / "federated" / "ecom", args.run_id
    )

    def meta(path: Path | None) -> dict:
        if not path:
            return {}
        mp = path.parent / "run_meta.json"
        return json.loads(mp.read_text()) if mp.is_file() else {}

    lean_s = _score(lean_v, gt, meta(lean_path))
    fed_s = _score(fed_v, gt, meta(fed_path))

    # Comprehensive gold-shaped reports (engine-agnostic sections + verdict localization)
    raw = REPO / "datasets" / "ecom_checkout" / "raw"
    for label, verdict, vpath in (
        ("lean", lean_v, lean_path),
        ("federated", fed_v, fed_path),
    ):
        if not verdict or not vpath:
            continue
        _run(
            [
                str(PY),
                "benchmarking/benchmark/comprehensive_rca_report.py",
                "--pack",
                str(pack),
                "--raw",
                str(raw),
                "--verdict",
                str(vpath),
                "--out-dir",
                str(vpath.parent),
            ]
        )

    report = {
        "run_id": args.run_id,
        "pack_id": PACK_ID,
        "ground_truth": {
            "root_ci": gt.get("root_ci"),
            "signature": gt.get("signature"),
        },
        "lean": lean_s,
        "federated": fed_s,
        "comprehensive_reports": {
            "lean": str(lean_path.parent / "incident_report.md") if lean_path else None,
            "federated": str(fed_path.parent / "incident_report.md") if fed_path else None,
        },
        "note": (
            "Primary objective: comprehensive correct RCA (incident_report.md). "
            "Lean vs Fed bakeoff metrics are secondary."
        ),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "COMPARISON.json").write_text(json.dumps(report, indent=2) + "\n")
    md = [
        "# E-com checkout — Lean vs Federated (ecom-numa-001)",
        "",
        f"**run_id:** `{args.run_id}`",
        "",
        "**Full analysis:** [`docs/ECOM_CHECKOUT_RCA_ANALYSIS.md`](../../docs/ECOM_CHECKOUT_RCA_ANALYSIS.md)",
        "",
        "## Ground truth",
        f"- root_ci: `{gt.get('root_ci')}`",
        f"- signature: `{gt.get('signature')}`",
        "",
        "## Results",
        "",
        "| Engine | Status | Root | Signature | Latency ms | Fallback |",
        "|--------|--------|------|-----------|------------|----------|",
    ]
    for name, s in (("Lean", lean_s), ("Federated", fed_s)):
        md.append(
            f"| {name} | **{s['status']}** | `{s.get('root_ci')}` "
            f"{'✓' if s.get('root_match') else '✗'} | `{s.get('signature')}` "
            f"{'✓' if s.get('signature_match') else '✗'} | "
            f"{s.get('latency_ms')} | {s.get('fallback_fired')} |"
        )
    md.extend(
        [
            "",
            "## Notes",
            "- Scenario: `datasets/scenario.md` (cross-NUMA IRQ affinity on NP-17).",
            "- Data path: Postgres (`dump_scenario_postgres.sh`) → JSON → engine pack.",
            "- False lead on path: `payment-provider` (high latency, later onset than IRQ).",
            "- Comprehensive reports: each run dir writes `incident_report.md` "
            "(metrics+logs+traces+changes+actions).",
            "- Federated currently stamps GT signature onto the verdict; Lean infers it.",
            "",
        ]
    )
    (OUT / "COMPARISON.md").write_text("\n".join(md))
    print((OUT / "COMPARISON.md").read_text())
    print(f"Wrote {OUT / 'COMPARISON.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
