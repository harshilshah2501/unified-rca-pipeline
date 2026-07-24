#!/usr/bin/env python3
"""Rebuild benchmarking/dashboard/data.json from latest comparison JSONs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UC = REPO / "benchmarking" / "results" / "comparison" / "comparison.json"
MOTADATA = REPO / "benchmarking" / "results" / "motadata" / "comparison.json"
OO = REPO / "benchmarking" / "results" / "openobserve" / "comparison.json"
OO_GT = REPO / "benchmarking" / "results" / "openobserve" / "gt_scoreboard.json"
OO_ENGINE = REPO / "benchmarking" / "results" / "openobserve" / "engine_scoreboard.json"
OUT = REPO / "benchmarking" / "dashboard" / "data.json"
OBSERVEOPS = REPO / "datasets" / "observeops"
MOTADATA_INCIDENTS = (
    REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "incidents"
)
LEAN_RESULTS = REPO / "benchmarking" / "results" / "lean"

sys.path.insert(0, str(REPO / "benchmarking" / "benchmark"))
from fault_taxonomy import BUCKET_LABELS, resolve_taxonomy  # noqa: E402


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _latest_lean_verdict(sample_id: str, corpus: str) -> dict | None:
    """Prefer newest lean verdict.json for this pack."""
    if corpus == "motadata":
        base = LEAN_RESULTS / "motadata" / sample_id
    else:
        base = LEAN_RESULTS / sample_id
    if not base.is_dir():
        return None
    verdicts = sorted(base.glob("run-*/verdict.json"), key=lambda p: p.stat().st_mtime)
    return _read_json(verdicts[-1]) if verdicts else None


def _pack_dir(sample_id: str, corpus: str) -> Path | None:
    if corpus == "motadata":
        p = MOTADATA_INCIDENTS / sample_id
    else:
        p = OBSERVEOPS / sample_id
    return p if p.is_dir() else None


def _fmt_evidence_line(ev: dict) -> str:
    ci = ev.get("ci") or "?"
    signal = ev.get("signal") or "?"
    val = ev.get("value")
    ts = (ev.get("timestamp") or "")[:19]
    src = ev.get("source") or ""
    extra = f" = {val}" if val is not None else ""
    tail = f" @ {ts}" if ts else ""
    src_s = f" ({src})" if src else ""
    return f"{ci} · {signal}{extra}{tail}{src_s}"


def _review_bundle(sample_id: str, corpus: str, gt: dict) -> dict:
    """Seed + anomalies + Lean evidence for the Samples detail panel."""
    pack = _pack_dir(sample_id, corpus)
    seed = _read_json(pack / "symptom_seed.json") if pack else None
    anomalies_doc = _read_json(pack / "anomalies.json") if pack else None
    pack_gt = _read_json(pack / "ground_truth.json") if pack else None
    # Prefer live pack GT for status/note (comparison JSON may be a slim copy)
    merged_gt = {**(gt or {}), **(pack_gt or {})}
    anoms = list((anomalies_doc or {}).get("anomalies") or [])[:8]
    verdict = _latest_lean_verdict(sample_id, corpus) or {}
    evidence = list(verdict.get("evidence") or [])[:5]
    if not evidence and anoms:
        evidence = [
            {
                "ci": a.get("ci"),
                "signal": a.get("signal"),
                "value": a.get("value"),
                "timestamp": a.get("timestamp"),
                "source": "anomaly",
            }
            for a in anoms[:5]
        ]
    seed_line = None
    if seed:
        seed_line = (
            f"{seed.get('ci')} · {seed.get('signal')} "
            f"@ {(seed.get('timestamp') or '')[:19]} "
            f"[{seed.get('anomaly_class') or '?'}]"
        ).strip()
    return {
        "seed_line": seed_line,
        "seed": seed,
        "anomaly_lines": [
            f"{a.get('ci')} · {a.get('signal')} = {a.get('value')} "
            f"(thr {a.get('threshold')}) @ {(a.get('timestamp') or '')[:19]}"
            for a in anoms
        ],
        "evidence_lines": [_fmt_evidence_line(e) for e in evidence],
        "causal_chain": list(verdict.get("causal_chain") or [])[:6],
        "evidentiary_tier": verdict.get("evidentiary_tier"),
        "gt_note": merged_gt.get("note"),
        "gt_status": merged_gt.get("gt_status"),
    }


def _sample_row(
    *,
    sample_id: str,
    corpus: str,
    gt: dict,
    lean: dict | None,
    fed: dict | None,
    winner: str | None,
) -> dict:
    sig = (gt or {}).get("signature")
    tax = resolve_taxonomy(sample_id, signature=sig)
    lean = lean or {}
    fed = fed or {}
    lean_ok = bool(lean.get("root_match")) and bool(
        lean.get("signature_match") or lean.get("status") == "pass"
    )
    # UC rows use status=pass; prefer explicit matches when present
    if "root_match" in lean:
        lean_ok = bool(lean.get("root_match") and lean.get("signature_match"))
    fed_ok = False
    if fed:
        if "root_match" in fed:
            fed_ok = bool(fed.get("root_match") and fed.get("signature_match"))
        else:
            fed_ok = fed.get("status") == "pass"
    review = _review_bundle(sample_id, corpus, gt or {})
    return {
        "id": sample_id,
        "corpus": corpus,
        "fault_bucket": tax["fault_bucket"],
        "fault_bucket_label": tax["fault_bucket_label"],
        "fault_type": tax["fault_type"],
        "fault_title": tax["fault_title"],
        "gt_root": (gt or {}).get("root_ci"),
        "gt_sig": sig,
        "lean_root": lean.get("root_ci"),
        "lean_sig": lean.get("signature"),
        "lean_ok": lean_ok,
        "fed_root": fed.get("root_ci"),
        "fed_sig": fed.get("signature"),
        "fed_ok": fed_ok,
        "winner": winner,
        "review": review,
        "manual_check": [
            "Confirm symptom seed CI matches the blast you expect "
            "(see Seed below)",
            f"Lean root `{lean.get('root_ci')}` vs GT `{gt.get('root_ci')}`",
            f"Signature `{lean.get('signature')}` vs GT `{sig}`",
            "Skim evidence lines below (Lean verdict / anomalies)",
        ],
    }


def build_samples(uc: dict, motadata: dict | None) -> dict:
    rows: list[dict] = []
    for r in uc.get("rows") or []:
        uid = r.get("uc_id")
        if not uid:
            continue
        rows.append(
            _sample_row(
                sample_id=uid,
                corpus="observeops",
                gt=r.get("ground_truth") or {},
                lean=r.get("lean"),
                fed=r.get("federated"),
                winner=r.get("winner"),
            )
        )
    if motadata:
        for r in motadata.get("rows") or []:
            iid = r.get("incident_id")
            if not iid:
                continue
            rows.append(
                _sample_row(
                    sample_id=iid,
                    corpus="motadata",
                    gt=r.get("ground_truth") or {},
                    lean=r.get("lean"),
                    fed=r.get("federated"),
                    winner=r.get("winner"),
                )
            )
    by_bucket: dict[str, int] = {}
    for r in rows:
        by_bucket[r["fault_bucket"]] = by_bucket.get(r["fault_bucket"], 0) + 1
    return {
        "note": (
            "Manual-verify strip: GT vs Lean vs Federated on diverse fault types. "
            "Automation flags mismatches; human review remains authoritative."
        ),
        "buckets": [
            {"id": k, "label": BUCKET_LABELS.get(k, k), "count": by_bucket.get(k, 0)}
            for k in ("1_symptom", "2_infra", "3_application", "4_external")
        ],
        "rows": rows,
    }


def main() -> int:
    uc = json.loads(UC.read_text())
    motadata = json.loads(MOTADATA.read_text()) if MOTADATA.is_file() else None
    oo = json.loads(OO.read_text())
    oo_rows = []
    for r in oo["rows"]:
        a = r.get("agree_layer") or {}
        p = r.get("picks_incident_title") or {}
        oo_eng = r.get("openobserve") or {}
        oo_rows.append(
            {
                "id": r["id"],
                "title": r["title"],
                "oo_layer": oo_eng.get("layer"),
                "lean_layer": r["lean"]["layer"],
                "fed_layer": r["federated"]["layer"],
                "lean_root": r["lean"].get("root_alert"),
                "fed_root": r["federated"].get("root_alert"),
                "oo_root": oo_eng.get("root_alert"),
                "oo_snippet": (oo_eng.get("cause_snippet") or "")[:160],
                "oo_has_narrative": oo_eng.get("has_narrative"),
                "agree_lf": a.get("lean_federated"),
                "agree_lo": a.get("lean_openobserve"),
                "agree_fo": a.get("federated_openobserve"),
                "triple": a.get("triple"),
                "triggers": r["trigger_count"],
                "lean_title_pick": p.get("lean"),
                "fed_title_pick": p.get("federated"),
                "oo_title_pick": p.get("openobserve"),
                "multi": r["multi_trigger"],
            }
        )
    uc_rows = []
    for r in uc.get("rows", []):
        uid = r.get("uc_id")
        gt = r.get("ground_truth") or {}
        tax = resolve_taxonomy(uid or "", signature=gt.get("signature"))
        uc_rows.append(
            {
                "uc_id": uid,
                "gt": gt.get("root_ci"),
                "gt_sig": gt.get("signature"),
                "fault_bucket": tax["fault_bucket"],
                "fault_bucket_label": tax["fault_bucket_label"],
                "fault_type": tax["fault_type"],
                "fed": (r.get("federated") or {}).get("root_ci"),
                "lean": (r.get("lean") or {}).get("root_ci"),
                "winner": r.get("winner"),
                "fed_obs": (r.get("federated") or {}).get("observations"),
                "lean_obs": (r.get("lean") or {}).get("observations"),
                "lean_tier": (r.get("lean") or {}).get("evidentiary_tier"),
                "fed_tier": (r.get("federated") or {}).get("evidentiary_tier"),
            }
        )
    oo_gt = json.loads(OO_GT.read_text()) if OO_GT.exists() else None
    oo_engine = json.loads(OO_ENGINE.read_text()) if OO_ENGINE.exists() else None
    payload = {
        "uc": {
            "generated_at": uc.get("generated_at"),
            "run_id": uc.get("run_id_filter"),
            "axes": uc.get("axes"),
            "summary": uc.get("summary"),
            "rows": uc_rows,
        },
        "samples": build_samples(uc, motadata),
        "motadata": {
            "generated_at": (motadata or {}).get("generated_at"),
            "run_id": (motadata or {}).get("run_id_filter"),
            "summary": (motadata or {}).get("summary"),
        }
        if motadata
        else None,
        "openobserve": {
            "generated_at": oo.get("generated_at"),
            "evaluation": oo.get("evaluation"),
            "summary": oo.get("summary"),
            "behavioral_edge": oo.get("behavioral_edge_lean_vs_federated"),
            "closest_to_openobserve": oo.get("closest_to_openobserve_layer"),
            "overall_better": oo.get("overall_better"),
            "by_layer": oo.get("by_openobserve_layer") or oo.get("by_reference_layer"),
            "rows": oo_rows,
        },
        "openobserve_gt": {
            "generated_at": (oo_gt or {}).get("generated_at"),
            "evaluation": (oo_gt or {}).get("evaluation"),
            "summary": (oo_gt or {}).get("summary"),
            "excluded": (oo_gt or {}).get("excluded"),
            "rows": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "stratum": r.get("stratum"),
                    "eligible": r["include_in_accuracy"],
                    "gt_layer": r["gt"]["root_layer"],
                    "gt_root": r["gt"]["root_alert"],
                    "lean_layer_hit": r["lean"]["layer_hit"],
                    "lean_root_hit": r["lean"]["root_hit"],
                    "fed_layer_hit": r["federated"]["layer_hit"],
                    "fed_root_hit": r["federated"]["root_hit"],
                    "oo_layer_hit": r["openobserve"]["layer_hit"],
                    "oo_root_hit": r["openobserve"]["root_hit"],
                    "lean_root": r["lean"].get("root_alert"),
                    "fed_root": r["federated"].get("root_alert"),
                    "oo_root": r["openobserve"].get("root_alert"),
                }
                for r in ((oo_gt or {}).get("rows") or [])
            ],
        }
        if oo_gt
        else None,
        "openobserve_engine": {
            "generated_at": oo_engine.get("generated_at"),
            "run_id": oo_engine.get("run_id_filter"),
            "evaluation": oo_engine.get("evaluation"),
            "summary": oo_engine.get("summary"),
            "reproducibility_sources": oo_engine.get("reproducibility_sources"),
        }
        if oo_engine
        else None,
    }
    # Snapshot PoC status for static viewers (live SSH still via /api/status).
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from poc_status import build_status  # noqa: WPS433

        payload["poc"] = build_status(check_ssh=False)
    except Exception as exc:  # noqa: BLE001
        payload["poc"] = {"error": str(exc)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    OUT.write_text(text)
    js = OUT.with_suffix(".js")
    js.write_text("window.RCA_DASHBOARD_DATA = " + json.dumps(payload) + ";\n")
    print(f"Wrote {OUT}")
    print(f"Wrote {js}")
    print(f"samples={len(payload['samples']['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
