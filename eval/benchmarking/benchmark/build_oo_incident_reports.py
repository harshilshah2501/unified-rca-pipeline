#!/usr/bin/env python3
"""Build OpenObserve incident_report.json/.md beside Lean/Federated.

Sources (priority):
  1. Optional live fetch from OO portal (--live-fetch + OPENOBSERVE_* creds)
  2. Fair Slice A portal extracts under reports/OO/_fair_extracts/
  3. Scoreboard + fair/UC-N.md write-ups

Writes:
  benchmarking/results/comparison/reports/openobserve/UC-N/incident_report.json
  benchmarking/results/comparison/reports/openobserve/UC-N/incident_report.md

These feed the PoC console Incident Analysis OO tab the same way Lean/Federated
use their comprehensive reports.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "benchmarking" / "results" / "comparison" / "reports"
OO_FAIR = REPORTS / "OO" / "fair"
OO_EXTRACTS = REPORTS / "OO" / "_fair_extracts"
OUT_ROOT = REPORTS / "openobserve"
OBSERVEOPS = REPO / "datasets" / "observeops"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def _get_json(url: str, auth: str) -> dict | list:
    req = urllib.request.Request(
        url, headers={"Authorization": auth, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _find_analysis_md(uc: str) -> Path | None:
    """Prefer fair_r* analysis; fall back to older *analysis.md."""
    candidates = [
        OO_EXTRACTS / f"{uc}_fair_r4_analysis.md",
        OO_EXTRACTS / f"{uc}_fair_r3_analysis.md",
        OO_EXTRACTS / f"{uc.replace('-', '')}_fair_r3_analysis.md",
        OO_EXTRACTS / f"UC{uc.split('-')[1]}_fair_r3_analysis.md",
        OO_EXTRACTS / f"{uc}_analysis.md",
        OO_EXTRACTS / f"UC{uc.split('-')[1]}_analysis.md",
    ]
    # UC-1 uses UC1_ prefix in some files
    n = uc.split("-")[-1]
    candidates.extend(
        [
            OO_EXTRACTS / f"UC{n}_fair_r3_analysis.md",
            OO_EXTRACTS / f"UC{n}_fair_r4_analysis.md",
            OO_EXTRACTS / f"UC{n}_analysis.md",
        ]
    )
    for p in candidates:
        if p.is_file():
            return p
    # glob
    for p in sorted(OO_EXTRACTS.glob(f"*{uc}*analysis*.md")) + sorted(
        OO_EXTRACTS.glob(f"*UC{n}*analysis*.md")
    ):
        if p.is_file():
            return p
    return None


def _find_blind(uc: str) -> dict | None:
    for name in (
        f"{uc}_blind_extract.json",
        f"UC{uc.split('-')[-1]}_blind_extract.json",
        f"{uc.replace('-', '')}_blind_extract.json",
    ):
        doc = _read_json(OO_EXTRACTS / name)
        if doc:
            return doc
    for p in OO_EXTRACTS.glob(f"*{uc}*blind*.json"):
        doc = _read_json(p)
        if doc:
            return doc
    return None


def _section(md: str, heading: str) -> str:
    """Return markdown body under ## heading until next ##."""
    pat = re.compile(
        rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)",
        re.M | re.S | re.I,
    )
    m = pat.search(md)
    return (m.group(1).strip() if m else "")


def _bullets(block: str) -> list[str]:
    out = []
    for ln in block.splitlines():
        s = ln.strip()
        if s.startswith(("- ", "* ", "• ")):
            out.append(re.sub(r"^[-*•]\s+", "", s).strip())
        elif re.match(r"^\d+\.\s+", s):
            out.append(re.sub(r"^\d+\.\s+", "", s).strip())
        elif s.startswith("**") and "—" in s:
            # **-Label** — text
            out.append(re.sub(r"^\*\*|\*\*$", "", s).replace("**", "").strip())
    return [x for x in out if x]


def _summary_field(md: str, label: str) -> str | None:
    pat = re.compile(
        rf"-\s+\*\*{re.escape(label)}\*\*:\s*(.+)$", re.M | re.I
    )
    m = pat.search(md)
    return m.group(1).strip() if m else None


def _exec_field(md: str, label: str) -> str | None:
    pat = re.compile(
        rf"\*\*{re.escape(label)}\*\*:\s*(.+?)(?=\n\*\*|\n##|\Z)",
        re.S | re.I,
    )
    m = pat.search(md)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _parse_metric_table(md: str) -> list[dict]:
    """Parse simple | Metric | Value | Threshold | Status | tables."""
    rows = []
    for ln in md.splitlines():
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"metric", "---", ""} or set(cells[0]) <= {"-"}:
            continue
        if "---" in cells[0]:
            continue
        name, val, thr = cells[0], cells[1], cells[2] if len(cells) > 2 else None
        # strip units for numeric attempt
        def _num(x: str | None) -> float | None:
            if not x:
                return None
            m = re.search(r"([\d.]+)", x.replace(",", ""))
            return float(m.group(1)) if m else None

        rows.append(
            {
                "ci": "orders-api",
                "signal": name,
                "value": _num(val),
                "threshold": _num(thr),
                "raw_value": val,
                "raw_threshold": thr,
                "crossed": True,
            }
        )
    return rows


def _timeline_from_md(block: str) -> list[dict]:
    items = []
    for ln in block.splitlines():
        s = ln.strip()
        if not s.startswith("-"):
            continue
        s = s.lstrip("- ").strip()
        # **09:23:44 UTC** — text
        m = re.match(r"\*\*([^*]+)\*\*\s*[—\-–]\s*(.+)$", s)
        if m:
            items.append(
                {
                    "timestamp": m.group(1).strip(),
                    "summary": m.group(2).strip(),
                }
            )
        elif "—" in s or " - " in s:
            parts = re.split(r"\s+[—\-–]\s+", s, maxsplit=1)
            if len(parts) == 2:
                items.append({"timestamp": parts[0].strip("* "), "summary": parts[1]})
    return items


def _subsection(block: str, title: str) -> str:
    pat = re.compile(
        rf"^###\s+{re.escape(title)}\s*\n(.*?)(?=^###\s+|\Z)",
        re.M | re.S | re.I,
    )
    m = pat.search(block)
    return (m.group(1).strip() if m else "")


def build_report_for_uc(
    uc: str,
    *,
    case: dict,
    analysis_md: str,
    blind: dict | None,
    gt: dict,
    seed: dict,
    live_payload: dict | None = None,
) -> dict[str, Any]:
    summ_block = _section(analysis_md, "Incident Summary") or analysis_md
    impact_block = _section(analysis_md, "Impact Assessment")
    evidence = _section(analysis_md, "Evidence")
    timeline_block = _section(analysis_md, "Timeline")
    actions_block = _section(analysis_md, "Actions")
    exe_block = _section(analysis_md, "Executive Summary")

    deps_txt = _subsection(evidence, "Service Dependencies")
    traces_txt = _subsection(evidence, "Distributed Traces")
    logs_txt = _subsection(evidence, "Log Patterns")
    metrics_txt = _subsection(evidence, "Metrics Analysis")

    oo_root = (
        (blind or {}).get("OO_root")
        or case.get("oo_root")
        or (None if case.get("oo_correct") is False and not case.get("oo_root") else None)
    )
    cause = (
        (blind or {}).get("OO_potential_cause_verbatim")
        or _exec_field(exe_block or analysis_md, "Potential Cause")
        or case.get("oo_note")
        or "No OpenObserve Potential Cause available."
    )
    incident_id = (
        (blind or {}).get("incident_id")
        or case.get("incident_id")
        or _summary_field(summ_block, "Incident ID")
        or uc
    )
    detected = _summary_field(summ_block, "Detected") or ""
    severity = _summary_field(summ_block, "Severity") or "P3 (Medium)"
    sev_code = severity.split()[0] if severity else "P3"

    customer = (
        _summary_field(summ_block, "Customer Impact")
        or f"Symptom on {seed.get('ci') or 'app'} ({seed.get('signal') or 'anomaly'})"
    )
    affected = _summary_field(summ_block, "Affected Services") or seed.get("ci") or ""

    log_findings = _bullets(logs_txt)
    if not log_findings and logs_txt:
        # prose paragraphs → single finding
        para = re.sub(r"\s+", " ", logs_txt).strip()
        if para:
            log_findings = [para[:400]]

    metric_rows = _parse_metric_table(metrics_txt)
    if not metric_rows and metrics_txt:
        metric_rows = []

    imm = _bullets(_subsection(actions_block, "Immediate") or actions_block)
    fut = _bullets(_subsection(actions_block, "Future"))

    matches = bool(case.get("oo_correct"))
    # Prefer a short CI-like root for localization when OO named something long
    root_ci = None
    if matches:
        root_ci = gt.get("root_ci")
    elif oo_root:
        # keep portal claim as-is for display; matching stays false
        root_ci = str(oo_root).split("(")[0].strip() or str(oo_root)

    report: dict[str, Any] = {
        "schema_version": "comprehensive_rca.v1",
        "incident_id": incident_id,
        "source_incident_id": incident_id,
        "engine": "openobserve",
        "generated_at": _iso_now(),
        "pack_meta": {
            "uc_id": uc,
            "fair_slice": "A_fair",
            "parity_run_id": "adr001-rerun-20260723",
            "detected_at": detected,
            "source": "oo_portal_fair_extract",
            "analysis_source": "live_fetch" if live_payload else "fair_extract_md",
            "live_refreshed": bool(live_payload),
        },
        "localization": {
            "root_ci": root_ci,
            "signature": gt.get("signature") if matches else None,
            "oo_claimed_root": oo_root or case.get("oo_note"),
            "contributor_cis": [],
            "false_leads_ruled_out": [],
            "matches_pack_gt": matches,
        },
        "incident_summary": {
            "severity": sev_code,
            "detected": detected,
            "affected_services": [a.strip() for a in affected.split(",") if a.strip()],
            "customer_impact": customer,
            "dimension_slice": "OpenObserve fair Slice A · ObserveOps UC",
            "gt_fault_title": gt.get("fault_title"),
        },
        "impact": {
            "services_affected": [a.strip() for a in affected.split(",") if a.strip()]
            or ([seed.get("ci")] if seed.get("ci") else []),
            "sla_breach": "yes" in (impact_block or "").lower()
            and "sla breach" in (impact_block or "").lower(),
            "data_loss": False,
            "estimated_fail_fraction": None,
            "notes": None,
        },
        "service_dependencies": {
            "critical_path": [root_ci] if root_ci else [],
            "topology_edges": [],
            "isolation_note": deps_txt
            or (
                "OpenObserve fair Analysis reported limited or no topology for this lab slice."
            ),
        },
        "distributed_traces": {
            "available": "no trace" not in (traces_txt or "").lower()
            and "unable" not in (traces_txt or "").lower()
            and bool(traces_txt),
            "analyzed_spans": 0,
            "slow_spans": 0,
            "assessment": traces_txt
            or "No distributed-trace assessment in the OO Analysis extract.",
        },
        "log_patterns": {
            "key_findings": log_findings,
            "pack_event_types": {},
        },
        "metrics_analysis": {
            "crossed_anomalies": metric_rows,
            "assessment": metrics_txt[:500] if metrics_txt else "",
        },
        "timeline": _timeline_from_md(timeline_block),
        "actions": {
            "immediate": imm
            or [
                "Treat OpenObserve as a third-party baseline; confirm against Lean/Federated "
                "and pack GT before acting."
            ],
            "future": fut
            or [
                "Keep fair OO alerts symptom-only — never paste GT into alert text."
            ],
        },
        "remediation": {
            "immediate": imm,
            "future": fut,
        },
        "rca_summary": {
            "fault_title": gt.get("fault_title"),
            "root_ci": root_ci,
            "signature": gt.get("signature") if matches else None,
            "causal_path": [root_ci] if root_ci else [],
            "customer_impact": customer,
            "change_evidence": None,
            "narrative": cause,
        },
        "executive_summary": {
            "potential_cause": cause,
            "impact": _exec_field(exe_block or analysis_md, "Impact") or customer,
            "resolution": _exec_field(exe_block or analysis_md, "Resolution")
            or (imm[0] if imm else "See Lean/Federated for pack-topology root CI."),
        },
        "fair_score": {
            "oo_correct": matches,
            "pack_gt_root": gt.get("root_ci"),
            "pack_gt_signature": gt.get("signature"),
            "oo_note": case.get("oo_note"),
        },
        "portal_analysis_markdown": analysis_md,
    }
    if live_payload:
        report["live_incident"] = {
            "id": live_payload.get("id"),
            "title": live_payload.get("title"),
            "status": live_payload.get("status"),
        }
    # completeness-ish
    report["completeness"] = {
        "score": round(
            sum(
                [
                    1.0 if cause else 0,
                    1.0 if log_findings else 0,
                    1.0 if metric_rows else 0.3,
                    1.0 if report["timeline"] else 0.3,
                    1.0 if imm else 0.5,
                ]
            )
            / 5.0,
            2,
        ),
        "source": "oo_portal_fair",
    }
    return report


def format_oo_markdown(report: dict, analysis_md: str) -> str:
    loc = report["localization"]
    fair = report.get("fair_score") or {}
    exe = report["executive_summary"]
    header = [
        f"# Incident Analysis Report — OpenObserve · `{report['pack_meta'].get('uc_id')}`",
        "",
        f"**Engine:** openobserve (fair Slice A portal Analysis)  ",
        f"**Portal incident:** `{report['incident_id']}`  ",
        f"**Pack GT:** `{fair.get('pack_gt_root')}` / `{fair.get('pack_gt_signature')}`  ",
        f"**OO match to pack GT:** {'Yes' if fair.get('oo_correct') else 'No'}  ",
        f"**OO claimed root:** {loc.get('oo_claimed_root') or loc.get('root_ci') or '—'}  ",
        f"**Generated:** {report.get('generated_at')}  ",
        "",
        "## Executive Summary (from portal)",
        "",
        f"**Potential Cause:** {exe.get('potential_cause')}",
        "",
        f"**Impact:** {exe.get('impact')}",
        "",
        f"**Resolution:** {exe.get('resolution')}",
        "",
        "---",
        "",
        "## Portal Analysis (verbatim fair extract)",
        "",
        analysis_md.strip(),
        "",
    ]
    return "\n".join(header)


def try_live_fetch(incident_id: str, *, base: str, org: str, auth: str) -> dict | None:
    try:
        detail = _get_json(
            f"{base}/api/v2/{org}/alerts/incidents/{incident_id}", auth
        )
        return detail if isinstance(detail, dict) else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        print(f"  live fetch failed for {incident_id}: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--live-fetch",
        action="store_true",
        help="Also pull incident JSON from OO portal (needs OPENOBSERVE_USER/PASSWORD)",
    )
    ap.add_argument(
        "--base-url",
        default=os.environ.get("OPENOBSERVE_URL", "http://172.16.14.77:5080"),
    )
    ap.add_argument("--org", default=os.environ.get("OPENOBSERVE_ORG", "default"))
    ap.add_argument("--user", default=os.environ.get("OPENOBSERVE_USER", ""))
    ap.add_argument("--password", default=os.environ.get("OPENOBSERVE_PASSWORD", ""))
    args = ap.parse_args()

    sb = _read_json(OO_FAIR / "scoreboard.json") or {}
    cases = {c["uc"]: c for c in (sb.get("cases") or []) if c.get("uc")}
    if not cases:
        raise SystemExit(f"No cases in {OO_FAIR / 'scoreboard.json'}")

    auth = None
    if args.live_fetch:
        if not args.user or not args.password:
            print(
                "WARN: --live-fetch requested but OPENOBSERVE_USER/PASSWORD unset; "
                "building from fair extracts only."
            )
        else:
            auth = _auth_header(args.user, args.password)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    written = []
    for uc in ["UC-1", "UC-2", "UC-3", "UC-4", "UC-5"]:
        case = cases.get(uc) or {}
        analysis_path = _find_analysis_md(uc)
        if not analysis_path:
            print(f"SKIP {uc}: no fair analysis markdown under {OO_EXTRACTS}")
            continue
        analysis_md = analysis_path.read_text(encoding="utf-8")
        blind = _find_blind(uc)
        gt = _read_json(OBSERVEOPS / uc / "ground_truth.json") or {
            "root_ci": case.get("gt_root"),
            "signature": case.get("gt_signature"),
        }
        seed = _read_json(OBSERVEOPS / uc / "symptom_seed.json") or {}

        live = None
        iid = (blind or {}).get("incident_id") or case.get("incident_id")
        if auth and iid:
            print(f"{uc}: live-fetch {iid} …")
            live = try_live_fetch(
                iid, base=args.base_url.rstrip("/"), org=args.org, auth=auth
            )
            if live:
                # Prefer portal suggested_root_cause / analysis fields when present
                src = (
                    live.get("suggested_root_cause")
                    or live.get("analysis")
                    or live.get("description")
                )
                if isinstance(src, str) and len(src) > 200 and src.lstrip().startswith("#"):
                    analysis_md = src
                elif isinstance(src, str) and len(src) > 80:
                    # wrap as executive-only supplement
                    analysis_md = (
                        analysis_md
                        + "\n\n## Live portal refresh note\n\n"
                        + src[:4000]
                    )

        report = build_report_for_uc(
            uc,
            case=case,
            analysis_md=analysis_md,
            blind=blind,
            gt=gt,
            seed=seed,
            live_payload=live,
        )
        out_dir = OUT_ROOT / uc
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "incident_report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (out_dir / "incident_report.md").write_text(
            format_oo_markdown(report, analysis_md), encoding="utf-8"
        )
        # keep a copy of the raw analysis for audit
        (out_dir / "portal_analysis.md").write_text(analysis_md, encoding="utf-8")
        written.append(uc)
        print(
            f"Wrote {out_dir}/incident_report.{{json,md}} "
            f"(match={report['localization']['matches_pack_gt']})"
        )

    meta = {
        "generated_at": _iso_now(),
        "ucs": written,
        "source": "OO/_fair_extracts + fair/scoreboard.json",
        "live_fetch": bool(auth),
        "out": str(OUT_ROOT.relative_to(REPO)),
    }
    (OUT_ROOT / "README.md").write_text(
        "\n".join(
            [
                "# OpenObserve incident reports (fair Slice A)",
                "",
                "Comprehensive `incident_report.json` / `.md` per UC, built from the",
                "OpenObserve portal fair Analysis extracts — same folder shape as",
                "[`../lean/`](../lean/) and [`../federated/`](../federated/).",
                "",
                f"**Generated:** {meta['generated_at']}  ",
                f"**UCs:** {', '.join(written)}  ",
                f"**Live fetch:** {meta['live_fetch']}  ",
                "",
                "Rebuild:",
                "",
                "```bash",
                ".venv/bin/python benchmarking/benchmark/build_oo_incident_reports.py",
                "# optional refresh from portal:",
                "OPENOBSERVE_USER=… OPENOBSERVE_PASSWORD=… \\",
                "  .venv/bin/python benchmarking/benchmark/build_oo_incident_reports.py --live-fetch",
                "```",
                "",
                "Canonical accuracy cite remains [`../OO/fair/`](../OO/fair/) +",
                "[`../LEAN_FED_OO_COMPARISON.md`](../LEAN_FED_OO_COMPARISON.md).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (OUT_ROOT / "build_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Done: {len(written)} OO reports → {OUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
