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
REPORTS = REPO / "benchmarking" / "results" / "comparison" / "reports"
OO_FAIR = REPORTS / "OO" / "fair"
OO_SCOREBOARD = OO_FAIR / "scoreboard.json"
LEAN_RESULTS = REPO / "benchmarking" / "results" / "lean"
FED_RESULTS = REPO / "benchmarking" / "results" / "federated"


sys.path.insert(0, str(REPO / "benchmarking" / "benchmark"))
from fault_taxonomy import BUCKET_BLURBS, BUCKET_LABELS, resolve_taxonomy  # noqa: E402

sys.path.insert(0, str(REPO / "benchmarking" / "dashboard"))
from incident_narration import (  # noqa: E402
    deduction_steps as _deduction_steps,
    human_actions as _human_actions,
    human_customer_impact as _human_customer_impact,
    human_deps as _human_deps,
    human_executive as _human_executive,
    human_logs as _human_logs,
    human_metrics_from_anomalies as _human_metrics_from_anomalies,
    human_one_liner as _human_one_liner,
    plain as _plain,
)


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _latest_verdict(
    sample_id: str, engine: str, corpus: str = "observeops"
) -> dict | None:
    """Prefer pinned adr001 (ObserveOps) or newest Motadata L1 verdict."""
    if engine not in ("lean", "federated"):
        return None
    if corpus == "motadata":
        base = (LEAN_RESULTS if engine == "lean" else FED_RESULTS) / "motadata" / sample_id
    else:
        base = (LEAN_RESULTS if engine == "lean" else FED_RESULTS) / sample_id
    if not base.is_dir():
        return None
    if corpus != "motadata":
        pinned = base / "run-adr001-rerun-20260723" / "verdict.json"
        if pinned.is_file():
            return _read_json(pinned)
    verdicts = sorted(base.glob("run-*/verdict.json"), key=lambda p: p.stat().st_mtime)
    return _read_json(verdicts[-1]) if verdicts else None


def _latest_lean_verdict(sample_id: str, corpus: str) -> dict | None:
    """Prefer newest lean verdict.json for this pack."""
    return _latest_verdict(sample_id, "lean", corpus=corpus)


def _oo_blind_extract(uc_id: str) -> str | None:
    """Pull Potential Cause paragraph from OO/fair/UC-N.md."""
    md = OO_FAIR / f"{uc_id}.md"
    if not md.is_file():
        return None
    text = md.read_text(encoding="utf-8")
    marker = "## Blind extract (Potential Cause)"
    if marker not in text:
        return None
    rest = text.split(marker, 1)[1]
    # until next ## heading
    chunk = rest.split("\n## ", 1)[0].strip()
    lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
    return " ".join(lines) if lines else None



def _story_from_report(
    uc_id: str, engine: str, gt: dict, corpus: str = "observeops"
) -> dict:
    """Human-friendly Incident Analysis payload (OO-portal style)."""
    report = _read_json(REPORTS / engine / uc_id / "incident_report.json") or {}
    if not report and corpus == "motadata":
        return _story_from_pack(uc_id, engine, gt, corpus=corpus)
    verd = _latest_verdict(uc_id, engine, corpus=corpus) or {}
    if not report and not verd.get("root_ci"):
        return _story_from_pack(uc_id, engine, gt, corpus=corpus)
    pack = _pack_dir(uc_id, corpus)
    seed = _read_json(pack / "symptom_seed.json") if pack else {}
    loc = report.get("localization") or {}
    summ = report.get("incident_summary") or {}
    impact = report.get("impact") or {}
    deps = report.get("service_dependencies") or {}
    logs = report.get("log_patterns") or {}
    metrics = report.get("metrics_analysis") or {}
    traces = report.get("distributed_traces") or {}
    rca = report.get("rca_summary") or {}
    actions = report.get("actions") or {}
    rem = report.get("remediation") or {}
    exe = report.get("executive_summary") or {}
    timeline = report.get("timeline") or []

    root = loc.get("root_ci") or verd.get("root_ci") or ""
    title = (
        rca.get("fault_title")
        or summ.get("gt_fault_title")
        or gt.get("fault_title")
        or root
    )
    if engine == "openobserve":
        claimed = loc.get("oo_claimed_root") or root or "not identified"
        title = f"OpenObserve Analysis — {claimed}"
    path = rca.get("causal_path") or verd.get("causal_chain") or []
    path_s = " → ".join(path) if path else ""

    log_lines = list(logs.get("key_findings") or [])[:6]
    if not log_lines:
        for _k, block in (logs.get("pack_event_types") or {}).items():
            for ex in (block.get("examples") or [])[:1]:
                if ex.get("message"):
                    log_lines.append(_plain(ex["message"]))
    log_lines = _human_logs(log_lines, corpus=corpus)

    crossed = list(metrics.get("crossed_anomalies") or [])[:6]
    if crossed:
        metric_lines = _human_metrics_from_anomalies(crossed)
    elif verd.get("evidence"):
        metric_lines = _human_metrics_from_anomalies(
            [
                {
                    "ci": ev.get("ci"),
                    "signal": ev.get("signal"),
                    "value": ev.get("value"),
                    "threshold": None,
                }
                for ev in (verd.get("evidence") or [])[:6]
            ]
        )
    else:
        metric_lines = []

    trace_note = traces.get("assessment") or ""
    if traces.get("available") and traces.get("analyzed_spans"):
        n = traces.get("analyzed_spans")
        slow = traces.get("slow_spans") or 0
        trace_note = (
            f"This ObserveOps pack ships only a handful of synthetic spans "
            f"({n} examined"
            + (f", {slow} marked slow" if slow else "")
            + "). They corroborate app-side pain on the symptom CI; they are not a "
            "full multi-hop distributed trace, and Localize does not depend on them "
            "to name the root."
        )
    elif not trace_note:
        trace_note = (
            "This Motadata pack has no distributed-trace payload. Motadata L1 scoring "
            "is metrics/events + human GT for Localize — traces are not required here."
            if corpus == "motadata"
            else (
                "No useful distributed-trace window in this pack. Root finding relies on "
                "metrics, events, and the pack topology walk — not path-diff Identify."
            )
        )

    how_steps = _deduction_steps(
        engine, verd, seed=seed or {}, gt=gt, corpus=corpus
    )
    if engine == "openobserve":
        portal_cause = _plain(
            (exe.get("potential_cause") if isinstance(exe, dict) else None)
            or (rca.get("narrative") if isinstance(rca, dict) else None)
        )
        oo_claimed = loc.get("oo_claimed_root") or root
        how_steps = [
            (
                f"Detect-like: fair Slice A raised a symptom-only alert on "
                f"{(seed or {}).get('ci') or 'the app'} "
                f"({(seed or {}).get('signal') or 'anomaly'}) with no GT coaching — "
                f"same customer-pain style as a portal alert."
            ),
            (
                f"OpenObserve Analysis (portal): {portal_cause}"
                if portal_cause
                else "OpenObserve Analysis ran on the fair alert / incident in the lab portal."
            ),
            (
                f"Claimed root from Analysis: {oo_claimed or 'not identified'}. "
                + (
                    f"This matched pack GT ({gt.get('fault_title')} — {gt.get('root_ci')})."
                    if loc.get("matches_pack_gt")
                    else (
                        f"Pack truth for scoring remains {gt.get('fault_title')} — "
                        f"{gt.get('root_ci')} (OO miss on this UC)."
                    )
                )
            ),
            (
                "This report is the portal Analysis shaped like Lean/Federated "
                "incident_report.json — third-party baseline, not a Murphy or best-first walk."
            ),
        ]
    how = " ".join(how_steps[:2]) if how_steps else ""

    path_list = path if isinstance(path, list) else []
    deps_h = _human_deps(
        path=path_list,
        path_s=path_s,
        root=root,
        seed=seed or {},
        gt=gt,
        corpus=corpus,
        isolation_note=deps.get("isolation_note"),
    )

    sev = summ.get("severity") or ("P3" if corpus == "motadata" else "P2")
    sev_label = {"P1": "Critical", "P2": "High", "P3": "Medium", "P4": "Low"}.get(
        str(sev), str(sev)
    )

    cust = _human_customer_impact(
        raw=summ.get("customer_impact") or rca.get("customer_impact"),
        seed=seed or {},
        gt=gt,
        title=_plain(title),
        corpus=corpus,
    )

    rem_list = rem.get("immediate") if isinstance(rem, dict) else None
    if not rem_list and isinstance(verd.get("remediation"), list):
        rem_list = verd.get("remediation")
    if not rem_list:
        rem_list = actions.get("immediate") or []

    actions_now, actions_later = _human_actions(
        rem_list,
        title=_plain(title),
        root=root,
        corpus=corpus,
    )
    # Prefer report "future" when present and already prose-like
    fut = actions.get("future") or (rem.get("future") if isinstance(rem, dict) else None)
    if fut:
        actions_later = [_plain(x) for x in fut[:3] if _plain(x)] or actions_later

    one_liner = _human_one_liner(
        title=_plain(gt.get("fault_title") or title),
        root=root or (loc.get("oo_claimed_root") or ""),
        change=exe.get("potential_cause") or rca.get("change_evidence"),
        note=gt.get("note"),
        corpus=corpus,
    )
    executive = _human_executive(
        title=_plain(gt.get("fault_title") or title),
        root=root or "",
        impact=cust,
        fix=actions_now[0] if actions_now else "Mitigate the labeled root CI.",
        corpus=corpus,
    )
    if engine == "openobserve":
        portal_cause = _plain(exe.get("potential_cause") or rca.get("narrative"))
        portal_impact = _plain(exe.get("impact") or cust)
        portal_fix = _plain(
            exe.get("resolution")
            or (actions_now[0] if actions_now else "")
        )
        one_liner = portal_cause or one_liner
        executive = {
            "cause": portal_cause
            or f"OpenObserve did not produce a clear Potential Cause for {uc_id}.",
            "impact": portal_impact
            or "See portal Analysis extract for impact wording.",
            "fix": portal_fix
            or "Confirm against Lean/Federated and pack GT before acting.",
        }

    detected = summ.get("detected")
    if detected:
        detected_s = detected[:19].replace("T", " ") + " UTC"
    elif corpus == "motadata":
        detected_s = "From Motadata export window"
    else:
        detected_s = "—"

    return {
        "engine": engine,
        "headline": _plain(title),
        "one_liner": one_liner,
        "root_plain": (
            _plain(str(loc.get("oo_claimed_root") or root or "—"))
            if engine == "openobserve"
            else (f"{_plain(gt.get('fault_title') or title)} ({root})" if root else _plain(title))
        ),
        "root_ci": root,
        "matches_gt": bool(
            loc.get("matches_pack_gt")
            if loc.get("matches_pack_gt") is not None
            else root == gt.get("root_ci")
        ),
        "how_we_found_it": how,
        "how_steps": how_steps,
        "summary_rows": [
            ["Incident", uc_id],
            ["Severity", f"{sev} ({sev_label})"],
            ["Detected", detected_s],
            [
                "Status",
                "Human-confirmed Motadata L1"
                if corpus == "motadata"
                else "Open (pack replay)",
            ],
            [
                "Affected services",
                ", ".join(
                    summ.get("affected_services") or gt.get("blast_radius") or []
                )
                or "—",
            ],
            ["What customers saw", cust],
            ["Root cause", f"{_plain(title)} — {root}"],
            ["How the fault spread", path_s or root or "—"],
        ],
        "impact_rows": [
            [
                "Services affected",
                str(
                    len(
                        impact.get("services_affected")
                        or summ.get("affected_services")
                        or gt.get("blast_radius")
                        or ([root] if root else [])
                    )
                ),
            ],
            [
                "Blast radius",
                ", ".join(
                    impact.get("services_affected")
                    or gt.get("blast_radius")
                    or ([root] if root else [])
                )
                or "—",
            ],
            [
                "Estimated fail share",
                _plain(impact.get("estimated_fail_fraction")) or "—",
            ],
            [
                "SLA risk",
                "Yes"
                if impact.get("sla_breach")
                else ("Likely" if corpus == "motadata" else "No"),
            ],
            ["Data loss", "Yes" if impact.get("data_loss") else "No"],
        ],
        "dependencies": {
            "critical_path": deps_h["critical_path"],
            "note": deps_h["note"],
            "plain": deps_h["plain"],
        },
        "traces": _plain(trace_note),
        "logs": log_lines,
        "metrics": metric_lines,
        "timeline": [
            {
                "when": (t.get("timestamp") or "")[:19].replace("T", " "),
                "what": _plain(t.get("summary")),
            }
            for t in timeline[:10]
        ],
        "actions_now": actions_now,
        "actions_later": actions_later,
        "executive": executive,
    }


def _story_from_pack(
    sample_id: str, engine: str, gt: dict, corpus: str = "motadata"
) -> dict:
    """Build a human story when comprehensive incident_report.json is absent."""
    pack = _pack_dir(sample_id, corpus)
    seed = _read_json(pack / "symptom_seed.json") if pack else {}
    anomalies_doc = _read_json(pack / "anomalies.json") if pack else {}
    events_doc = _read_json(pack / "events.json") if pack else {}
    verd = _latest_verdict(sample_id, engine, corpus=corpus) or {}
    root = verd.get("root_ci") or gt.get("root_ci") or ""
    title = gt.get("fault_title") or root
    path = verd.get("causal_chain") or ([root] if root else [])
    path_s = " → ".join(path)

    anoms = [
        a
        for a in (anomalies_doc or {}).get("anomalies") or []
        if a.get("crossed", True)
    ][:8]
    timeline = []
    for a in anoms:
        ci = a.get("ci") or "?"
        sig = a.get("signal") or "?"
        val = a.get("value")
        ts = (a.get("timestamp") or "")[:19].replace("T", " ")
        if ts:
            timeline.append(
                {
                    "when": ts,
                    "what": f"{ci} · {sig}"
                    + (f" = {val}" if val is not None else ""),
                }
            )

    log_lines = []
    for ev in (events_doc or {}).get("events") or []:
        msg = ev.get("message") or ev.get("event_type")
        if msg:
            log_lines.append(_plain(msg))
        ts = (ev.get("timestamp") or "")[:19].replace("T", " ")
        if ts and msg:
            timeline.append({"when": ts, "what": _plain(msg)})
    log_lines = log_lines[:6]
    timeline = sorted(timeline, key=lambda t: t["when"])[:10]

    if anoms:
        metric_lines = _human_metrics_from_anomalies(anoms)
    elif verd.get("evidence"):
        metric_lines = _human_metrics_from_anomalies(
            [
                {
                    "ci": ev.get("ci"),
                    "signal": ev.get("signal"),
                    "value": ev.get("value"),
                    "threshold": None,
                }
                for ev in (verd.get("evidence") or [])[:6]
            ]
        )
    else:
        metric_lines = []

    rem = verd.get("remediation") or []
    if isinstance(rem, str):
        rem = [rem]

    how_steps = _deduction_steps(
        engine, verd, seed=seed or {}, gt=gt, corpus=corpus
    )
    how = " ".join(how_steps[:2]) if how_steps else ""

    seed_ci = (seed or {}).get("ci") or root
    matches = root == gt.get("root_ci")
    log_lines = _human_logs(log_lines, corpus=corpus)
    deps_h = _human_deps(
        path=path if isinstance(path, list) else [],
        path_s=path_s,
        root=root,
        seed=seed or {},
        gt=gt,
        corpus=corpus,
    )
    cust = _human_customer_impact(
        raw=gt.get("note"),
        seed=seed or {},
        gt=gt,
        title=_plain(title),
        corpus=corpus,
    )
    one_liner = _human_one_liner(
        title=_plain(title),
        root=root,
        change=None,
        note=gt.get("note"),
        corpus=corpus,
    )
    actions_now, actions_later = _human_actions(
        rem, title=_plain(title), root=root, corpus=corpus
    )
    executive = _human_executive(
        title=_plain(title),
        root=root,
        impact=cust,
        fix=actions_now[0] if actions_now else "Mitigate the labeled root CI.",
        corpus=corpus,
    )

    return {
        "engine": engine,
        "headline": _plain(title),
        "one_liner": one_liner,
        "root_plain": f"{_plain(title)} ({root})" if root else _plain(title),
        "root_ci": root,
        "matches_gt": matches,
        "how_we_found_it": how,
        "how_steps": how_steps,
        "summary_rows": [
            ["Incident", sample_id],
            ["Severity", "P3 (Medium)"],
            ["Detected", "Motadata export window"],
            ["Status", "Human-confirmed Motadata L1"],
            ["Affected services", ", ".join(gt.get("blast_radius") or [seed_ci])],
            ["What customers saw", cust],
            ["Root cause", f"{_plain(title)} — {root}"],
            ["How the fault spread", path_s or root or "—"],
        ],
        "impact_rows": [
            [
                "Services affected",
                str(len(gt.get("blast_radius") or ([root] if root else [1]))),
            ],
            [
                "Blast radius",
                ", ".join(gt.get("blast_radius") or ([root] if root else [])) or "—",
            ],
            ["Estimated fail share", "—"],
            ["SLA risk", "Likely"],
            ["Data loss", "No"],
        ],
        "dependencies": {
            "critical_path": deps_h["critical_path"],
            "note": deps_h["note"],
            "plain": deps_h["plain"],
        },
        "traces": (
            "This Motadata pack has no distributed-trace payload. Motadata L1 scoring "
            "is metrics/events + human GT for Localize — traces are not required here."
        ),
        "logs": log_lines
        or [
            "No rich syslog narrative in this Motadata slice; rely on threshold crossings "
            "and the human-labeled root CI for the Localize story."
        ],
        "metrics": metric_lines,
        "timeline": timeline,
        "actions_now": actions_now,
        "actions_later": actions_later,
        "executive": executive,
    }


def _oo_na_story(sample_id: str, gt: dict) -> dict:
    """OO fair compare is ObserveOps-UC only — not Motadata L1."""
    title = gt.get("fault_title") or gt.get("root_ci") or sample_id
    root = gt.get("root_ci") or "—"
    prose = (
        f"OpenObserve is not part of the Motadata L1 scoreboard. Fair OO Slice A only "
        f"covers ObserveOps UC-1..UC-5 with shifted fair alerts. For {sample_id}, use the "
        f"Lean or Federated tabs — those engines are scored against human GT "
        f"({title} → {root})."
    )
    return {
        "engine": "openobserve",
        "headline": "OpenObserve not scored on Motadata L1",
        "one_liner": prose,
        "root_plain": "—",
        "root_ci": None,
        "matches_gt": None,
        "how_we_found_it": prose,
        "how_steps": [
            "Fair OpenObserve Slice A is limited to ObserveOps UC packs with a "
            "symptom-only alert push and offline GT compare.",
            "Motadata L1 packs are a separate transfer surface: real-export slices with "
            "human ground truth, scored for Lean vs Federated only.",
            f"This pack’s labeled truth remains {title} at {root}. Switch to Lean or "
            f"Federated to read the Localize deduction on that label.",
        ],
        "summary_rows": [
            ["Incident", sample_id],
            ["Corpus", "Motadata L1 (human-confirmed)"],
            ["Pack truth", f"{title} — {root}"],
            ["OpenObserve", "Not in fair OO scoreboard for Motadata"],
        ],
        "impact_rows": [],
        "dependencies": {
            "critical_path": "—",
            "note": prose,
            "plain": prose,
        },
        "traces": (
            "No OO fair trace capture for Motadata L1 — the portal baseline was never "
            "pushed for these packs."
        ),
        "logs": [
            "There is no OpenObserve Analysis narrative for this Motadata pack. "
            "Compare Lean vs Federated instead."
        ],
        "metrics": [],
        "timeline": [],
        "actions_now": [
            "Open the Lean or Federated tab for this Motadata pack to see the scored "
            "Localize story against human GT."
        ],
        "actions_later": [
            "Keep OO fair compares on ObserveOps UC only so scoreboards stay unmixed."
        ],
        "executive": {
            "cause": f"N/A for OpenObserve on Motadata — pack truth is {title} ({root}).",
            "impact": "Motadata L1 customer/monitor impact is evaluated on Lean/Federated tabs.",
            "fix": "Use Lean or Federated for actionable root CI on this pack.",
        },
    }


def _oo_story(uc_id: str, oo: dict, gt: dict, seed: dict, blind: str | None) -> dict:
    """OO fair extract as the same human report shape (honest about gaps)."""
    correct = bool(oo.get("oo_correct"))
    claimed = oo.get("oo_root") or "Not identified"
    cause = blind or claimed or oo.get("oo_note") or "No Analysis narrative available."
    seed_ci = seed.get("ci") or "the app"
    seed_sig = seed.get("signal") or "latency / errors"
    title = gt.get("fault_title") or gt.get("root_ci") or uc_id
    how_steps = [
        (
            f"Detect-like hand-off: the fair lab raised a symptom-only alert on {seed_ci} "
            f"({seed_sig}) without coaching OpenObserve with pack ground truth. That mirrors "
            f"how a customer-pain alert looks in a portal, not how Lean/Federated share Detect."
        ),
        (
            "Analysis: OpenObserve produced a Potential Cause narrative from whatever "
            "metrics/logs the lab surface exposed. On these UC packs that often stays near "
            "the application layer even when the true fault is classic infrastructure."
        ),
        (
            f"Claimed root: {claimed}. "
            + (
                f"That matched pack truth ({title} — {gt.get('root_ci')})."
                if correct
                else (
                    f"Pack truth for scoring is still {title} at {gt.get('root_ci')} — "
                    f"so this OO run is counted as a miss on the fair UC scoreboard."
                )
            )
        ),
        (
            "This is a third-party baseline only. It is not Lean’s best-first topology walk "
            "and not Federated’s Murphy ranking — keep those engines on their own tabs for "
            "the PoC Localize story."
        ),
    ]
    deps_plain = (
        "OpenObserve’s fair write-up often lacks a reliable pack topology for this lab "
        "slice, so “service dependencies” here are weaker than Lean/Federated. Treat any "
        "ecommerce-looking guesses as narrative color, not as the ObserveOps blast path."
    )
    return {
        "engine": "openobserve",
        "headline": "OpenObserve Analysis (fair alert)",
        "one_liner": _plain(cause) if len(_plain(cause)) > 80 else (
            f"OpenObserve Analysis for {uc_id}: {_plain(cause)}. "
            f"Fair compare scores this against pack GT ({title})."
        ),
        "root_plain": _plain(str(claimed)),
        "root_ci": claimed if correct else None,
        "matches_gt": correct,
        "how_we_found_it": " ".join(how_steps[:2]),
        "how_steps": how_steps,
        "summary_rows": [
            ["Incident", oo.get("incident_id") or uc_id],
            ["Severity", "P3 (Medium)"],
            ["Detected", "Fair run (shifted to now)"],
            ["Status", "Compared offline to pack GT"],
            ["Affected services", seed.get("ci") or "orders-api"],
            [
                "What customers saw",
                (
                    f"The fair alert described customer pain on {seed_ci} ({seed_sig}). "
                    f"That is the portal’s symptom seed — not a guarantee OO named the "
                    f"true infra root."
                ),
            ],
            ["Root cause (OO)", _plain(str(claimed))],
            [
                "Pack truth (for scoring)",
                f"{title} — {gt.get('root_ci')}",
            ],
            ["Match to pack truth", "Yes" if correct else "No"],
        ],
        "impact_rows": [
            ["Services affected", "1 (symptom surface in fair alert)"],
            ["Blast radius", seed.get("ci") or "—"],
            ["Estimated fail share", "See Analysis narrative"],
            ["SLA risk", "Likely"],
            ["Data loss", "No"],
        ],
        "dependencies": {
            "critical_path": "—",
            "note": deps_plain,
            "plain": deps_plain,
        },
        "traces": (
            "Fair OO write-ups often note missing or weak traces on these UCs "
            "(for example UC-4: traces/logs not captured → precise failure point unknown). "
            "That gap is part of why OO may stay on the app symptom."
            if not correct
            else (
                "Analysis used available metrics/logs for an app-layer hit. Even when OO "
                "matches GT, Prefer Lean/Federated for the pack topology deduction."
            )
        ),
        "logs": (
            [
                _plain(oo.get("oo_note"))
                if len(_plain(oo.get("oo_note"))) >= 60
                else (
                    f"OpenObserve fair extract note: {_plain(oo.get('oo_note'))}. "
                    f"That lab detail is part of why the Analysis may stay thin compared "
                    f"with Lean/Federated pack reports."
                )
            ]
            if oo.get("oo_note")
            else [
                "See the Potential Cause narrative in the one-liner / executive cause — "
                "OO fair extracts do not always ship structured syslog bullets like the "
                "ObserveOps UC packs."
            ]
        ),
        "metrics": [
            (
                "Fair OO metrics are summarized inside the Analysis narrative rather than "
                "as a pack anomaly table. Prefer Lean/Federated Metrics analysis for "
                "threshold crossings on this UC topology."
            )
        ],
        "timeline": [],
        "actions_now": [
            "Treat OpenObserve as a third-party baseline. Confirm the root against Lean and "
            "Federated (and pack GT) before acting on the Analysis narrative alone."
        ],
        "actions_later": [
            "Keep fair OO alerts symptom-only — never paste GT into the alert text."
        ],
        "executive": {
            "cause": _plain(cause),
            "impact": (
                f"Customer symptom on {seed_ci} ({seed_sig}) in the fair alert window."
            ),
            "fix": "See Lean/Federated report for an actionable pack-topology root CI.",
        },
    }


def build_incident_room(uc: dict, motadata: dict | None = None) -> dict:
    """Incident Analysis: ObserveOps UC + human-confirmed Motadata L1."""
    sb = _read_json(OO_SCOREBOARD) or {}
    oo_by_uc = {c["uc"]: c for c in (sb.get("cases") or []) if c.get("uc")}
    cases = []

    for r in uc.get("rows") or []:
        uid = r.get("uc_id")
        if not uid:
            continue
        pack = OBSERVEOPS / uid
        gt = _read_json(pack / "ground_truth.json") or (r.get("ground_truth") or {})
        seed = _read_json(pack / "symptom_seed.json") or {}
        oo = oo_by_uc.get(uid) or {}
        blind = _oo_blind_extract(uid)
        cases.append(
            {
                "id": uid,
                "uc_id": uid,
                "corpus": "observeops",
                "group": "ObserveOps UC",
                "fault_title": gt.get("fault_title") or uid,
                "oo_available": True,
                "gt": {
                    "root_ci": gt.get("root_ci"),
                    "signature": gt.get("signature"),
                    "fault_title": gt.get("fault_title"),
                },
                "alert_plain": (
                    f"Shared Detect raised a customer-facing symptom on "
                    f"{seed.get('ci') or 'the app'} "
                    f"({seed.get('signal') or 'latency / errors'}). "
                    f"That is where people felt pain — the investigation seed — and on "
                    f"classic-infra packs it is usually downstream of the true fault "
                    f"({gt.get('fault_title') or uid}). Both engines start from this same seed."
                ),
                "stories": {
                    "lean": _story_from_report(uid, "lean", gt, corpus="observeops"),
                    "federated": _story_from_report(
                        uid, "federated", gt, corpus="observeops"
                    ),
                    "openobserve": (
                        _story_from_report(uid, "openobserve", gt, corpus="observeops")
                        if (REPORTS / "openobserve" / uid / "incident_report.json").is_file()
                        else _oo_story(uid, oo, gt, seed, blind)
                    ),
                },
            }
        )

    # Motadata L1 — only packs that pass both engines vs human GT
    if motadata:
        for r in motadata.get("rows") or []:
            iid = r.get("incident_id")
            if not iid:
                continue
            lean = r.get("lean") or {}
            fed = r.get("federated") or {}
            # verified: both engines match root+sig in comparison rows
            lean_ok = bool(lean.get("root_match") and lean.get("signature_match"))
            fed_ok = bool(fed.get("root_match") and fed.get("signature_match"))
            # fallback if fields named differently
            if "root_match" not in lean and "pass" in lean:
                lean_ok = bool(lean.get("pass"))
                fed_ok = bool(fed.get("pass"))
            pack = MOTADATA_INCIDENTS / iid
            gt = _read_json(pack / "ground_truth.json") or (r.get("ground_truth") or {})
            # Prefer explicit human-confirmed via samples rebuild: require GT present
            if not gt.get("root_ci"):
                continue
            seed = _read_json(pack / "symptom_seed.json") or {}
            # Include if bakeoff says both ok OR both verdicts match GT
            if not (lean_ok and fed_ok):
                lv = _latest_verdict(iid, "lean", "motadata") or {}
                fv = _latest_verdict(iid, "federated", "motadata") or {}
                lean_ok = lv.get("root_ci") == gt.get("root_ci")
                fed_ok = fv.get("root_ci") == gt.get("root_ci")
            if not (lean_ok and fed_ok):
                continue
            cases.append(
                {
                    "id": iid,
                    "uc_id": iid,
                    "corpus": "motadata",
                    "group": "Motadata L1",
                    "fault_title": gt.get("fault_title") or iid,
                    "oo_available": False,
                    "gt": {
                        "root_ci": gt.get("root_ci"),
                        "signature": gt.get("signature"),
                        "fault_title": gt.get("fault_title"),
                    },
                    "alert_plain": (
                        f"This Motadata L1 pack was cut from a real export. Operators first "
                        f"noticed pain on {seed.get('ci') or gt.get('root_ci') or 'the monitored CI'} "
                        f"({seed.get('signal') or gt.get('signature') or 'anomaly'}). "
                        f"Human ground truth labels {gt.get('root_ci') or 'the root CI'} "
                        f"({gt.get('fault_title') or 'see Samples'}) for scoring — automation "
                        f"does not invent that label."
                    ),
                    "stories": {
                        "lean": _story_from_report(
                            iid, "lean", gt, corpus="motadata"
                        ),
                        "federated": _story_from_report(
                            iid, "federated", gt, corpus="motadata"
                        ),
                        "openobserve": _oo_na_story(iid, gt),
                    },
                }
            )

    return {
        "title": "Incident Analysis",
        "run_id": "adr001-rerun-20260723",
        "motadata_run_id": (motadata or {}).get("run_id_filter")
        or (motadata or {}).get("run_id"),
        "note": (
            "ObserveOps UC packs + Motadata L1 (human-confirmed, both engines pass). "
            "Lab synthetic / EPS streams are capacity-only — not included (no RCA GT)."
        ),
        "oo_fair": {
            "date": sb.get("date"),
            "lean_root_accuracy": sb.get("lean_root_accuracy"),
            "federated_root_accuracy": sb.get("federated_root_accuracy"),
            "oo_root_accuracy": sb.get("oo_root_accuracy"),
            "contaminated": sb.get("contaminated_historical_oo"),
        },
        "cases": cases,
        "sim_href": "/rca-workflow-sim.html",
    }



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
            {
                "id": k,
                "label": BUCKET_LABELS.get(k, k),
                "blurb": BUCKET_BLURBS.get(k, ""),
                "count": by_bucket.get(k, 0),
            }
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
        "incident_room": build_incident_room(uc, motadata),
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
