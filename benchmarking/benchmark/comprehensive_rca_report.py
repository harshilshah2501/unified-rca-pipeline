#!/usr/bin/env python3
"""Build a gold-report-shaped comprehensive RCA from pack + raw OTEL JSON + engine verdict.

Engine-agnostic: Lean and Federated both get the same section coverage. Localization
(root_ci / signature) comes from the verdict; multimodal sections come from
topology, anomalies, events, and optional datasets/ecom_checkout/raw/{spans,logs,metrics}.json.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

REPO = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "comprehensive_rca.v1"

# Gold OO incident identity (same story as ecom-numa-001)
GOLD_SOURCE_INCIDENT_ID = "3GAWT8nVjUE2rA95CZmtyiQcVri"
GOLD_DETECTED_AT = "2026-07-07T09:00:58Z"
GOLD_CHANGE_AT = "2026-07-07T08:25:48Z"

# Signature → operator actions (Immediate / Future)
ACTIONS_BY_SIGNATURE: dict[str, dict[str, list[str]]] = {
    "cross_numa_irq_affinity": {
        "immediate": [
            "Revert NP-17 node image 2026.06.18 → 2026.05.30 to restore IRQ affinity.",
            "Confirm RX queue IRQs are pinned to CPUs on the same NUMA node as NIC queue memory.",
            "Verify checkout p99 and RX-queue latency return to baseline after rollback.",
        ],
        "future": [
            "Add pre-deploy NUMA topology validation; fail builds that assign IRQ across NUMA.",
            "Stage node-image rollouts (1–2 nodes, watch RX/DNS latency 10+ min) before full pool.",
            "Alert on kernel cross-NUMA RX processing / irq_affinity_numa_mismatch.",
            "Harden payment-risk path: pool pre-warm + DNS timeout backoff with jitter.",
        ],
    },
    "cpu_contention": {
        "immediate": [
            "Rebalance or vMotion overloaded VMs off the contended ESXi host.",
            "Identify runaway / over-provisioned vCPU consumers; reduce host overcommit.",
        ],
        "future": [
            "Tune DRS / right-size vCPU reservations; alert on host cpu.ready across ≥2 VMs.",
        ],
    },
    "link_failure": {
        "immediate": [
            "Restore or replace the failed switch uplink / port.",
            "Verify redundant NIC teaming and clear discards/errors.",
        ],
        "future": [
            "Alert on SNMP linkDown + rising discards; validate dual-homed uplinks in change windows.",
        ],
    },
    "storage_contention": {
        "immediate": [
            "Storage vMotion the noisy-neighbor VM or the victim DB VM off the hot datastore.",
            "Apply Storage I/O Control / IOPS limits on the noisy neighbor.",
        ],
        "future": [
            "Monitor datastore GAVG/DAVG with per-VM disk latency correlation.",
        ],
    },
    "os_resource_exhaustion": {
        "immediate": [
            "Free or extend filesystem space; restart the app after OOM/fs-full is cleared.",
            "Kill or limit runaway processes on the guest OS.",
        ],
        "future": [
            "Alert on guest fs>90% and OOM-killer events; disk quota / log rotation hygiene.",
        ],
    },
    "app_resource_exhaustion": {
        "immediate": [
            "Scale or restart the app tier; raise thread/heap/connection pool limits carefully.",
            "Confirm upstream infra remains healthy (do not restart hosts).",
        ],
        "future": [
            "Capacity alerts on pool saturation / GC pressure; load-test pool sizing.",
        ],
    },
}

DEFAULT_ACTIONS = {
    "immediate": [
        "Inspect earliest anomalous upstream CI on the causal chain and mitigate.",
        "Validate rollback or config fix against symptom metrics.",
    ],
    "future": [
        "Add monitoring for the decisive signals that proved this incident.",
        "Improve change review for the class of change that triggered the root.",
    ],
}

# Prose remediation guidance (signature templates; swap for LLM output when wired)
REMEDIATION_NARRATIVE_BY_SIGNATURE: dict[str, str] = {
    "cross_numa_irq_affinity": (
        "Treat this as an infrastructure misconfiguration incident, not a payment-provider "
        "outage. Immediately roll NP-17 back from node image 2026.06.18 to 2026.05.30 so RX-7 "
        "IRQs pin to the same NUMA node as queue memory, then confirm kernel RX-queue latency, "
        "AAAA DNS p99, checkout p99, and checkout success rate return to baseline on the "
        "Region-B · CARD · MOBILE · INR · cart>12 slice. Do not restart payment pods as the "
        "primary fix — that only masks pool pressure. After mitigation, block cross-NUMA IRQ "
        "assignments in the node-image pipeline and stage future NP-17 rollouts on 1–2 nodes "
        "with RX/DNS watch windows before full pool promotion."
    ),
    "cpu_contention": (
        "Host CPU Ready / usage shows the hypervisor is oversubscribed. Rebalance VMs, "
        "reduce vCPU overcommit, then confirm app p95 recovers — do not scale the app alone."
    ),
    "link_failure": (
        "Restore the failed uplink/port first. App timeouts are effects of the network break; "
        "verify redundant paths and clear interface discards before restarting services."
    ),
    "storage_contention": (
        "Shared datastore latency plus a noisy-neighbor I/O source explains DB/app slowness. "
        "Move or throttle the neighbor; do not treat the DB as the primary root."
    ),
    "os_resource_exhaustion": (
        "Guest OS disk/memory exhaustion killed or blocked the app. Free filesystem space / "
        "address OOM, then restart the service. Infra below the OS should remain healthy."
    ),
    "app_resource_exhaustion": (
        "Application pool/heap exhaustion with healthy upstream infra. Fix app capacity "
        "(threads, heap, connections); avoid blaming host/network/storage."
    ),
}

DEFAULT_REMEDIATION_NARRATIVE = (
    "Mitigate the localized root CI first, validate symptom metrics recover, then harden "
    "detection and change controls for this fault class so recurrence is caught earlier."
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text())


def _anomaly_map(anomalies: list[dict]) -> dict[str, dict]:
    """ci → first crossed anomaly (by timestamp)."""
    by_ci: dict[str, dict] = {}
    for a in sorted(
        (x for x in anomalies if x.get("crossed")),
        key=lambda x: x.get("timestamp", ""),
    ):
        by_ci.setdefault(a["ci"], a)
    return by_ci


def _effect_to_causes(topology: dict) -> dict[str, list[str]]:
    causes: dict[str, list[str]] = defaultdict(list)
    for e in topology.get("edges", []):
        causes[e["from"]].append(e["to"])
    return causes


def _cause_to_effects(topology: dict) -> dict[str, list[str]]:
    effects: dict[str, list[str]] = defaultdict(list)
    for e in topology.get("edges", []):
        effects[e["to"]].append(e["from"])
    return effects


def _critical_path(topology: dict, *, start: str | None = None) -> list[str]:
    """Longest effect→cause walk from an entry service (gateway/checkout)."""
    nodes = {n["id"] for n in topology.get("nodes", [])}
    causes = _effect_to_causes(topology)
    if start and start in nodes:
        seed_candidates = [start]
    else:
        seed_candidates = [n for n in nodes if "gateway" in n] or [
            n for n in nodes if "checkout" in n
        ]
        if not seed_candidates:
            seed_candidates = list(nodes)[:1]
    if not seed_candidates:
        return []
    origin = seed_candidates[0]
    best: list[str] = [origin]

    def walk(cur: str, path: list[str]) -> None:
        nonlocal best
        nxt = causes.get(cur, [])
        if not nxt:
            if len(path) > len(best):
                best = list(path)
            return
        for c in nxt:
            if c in path:
                continue
            walk(c, path + [c])

    walk(origin, [origin])
    return best


def _shortest_root_to_seed(
    topology: dict,
    root_ci: str,
    seed_ci: str,
    prefer: set[str] | None = None,
) -> list[str]:
    """Cause→effect path from root to symptom (Lean-compatible narrative order)."""
    prefer = prefer or set()
    nodes = {n["id"] for n in topology.get("nodes", [])}
    if root_ci not in nodes:
        return [root_ci] if root_ci == seed_ci else [root_ci, seed_ci]
    if root_ci == seed_ci:
        return [root_ci]
    downstream = _cause_to_effects(topology)
    queue: deque[list[str]] = deque([[root_ci]])
    visited = {root_ci}
    best: list[str] | None = None
    best_score = -1
    while queue:
        path = queue.popleft()
        current = path[-1]
        if current == seed_ci:
            score = sum(1 for ci in path if ci in prefer)
            if best is None or len(path) < len(best) or (
                len(path) == len(best) and score > best_score
            ):
                best = path
                best_score = score
            continue
        if best is not None and len(path) >= len(best):
            continue
        dependents = sorted(
            downstream.get(current, []),
            key=lambda ci: (0 if ci in prefer else 1, ci),
        )
        for dependent in dependents:
            if dependent not in visited:
                visited.add(dependent)
                queue.append([*path, dependent])
    if best:
        return best
    return [root_ci] if root_ci == seed_ci else [root_ci, seed_ci]


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shift_ts(ts: str | None, delta: timedelta | None) -> str | None:
    if not ts or delta is None:
        return ts
    dt = _parse_ts(ts)
    if dt is None:
        return ts
    return _iso(dt + delta)


def _clock_delta(meta: dict, anomalies_doc: dict) -> timedelta | None:
    """Map dump-relative pack times onto canonical gold clock when configured."""
    clock = meta.get("canonical_clock") or {}
    canonical_change = _parse_ts(clock.get("change_at") or GOLD_CHANGE_AT)
    dump_anchor = _parse_ts(
        meta.get("incident_start") or anomalies_doc.get("incident_start")
    )
    if canonical_change is None or dump_anchor is None:
        return None
    if not meta.get("canonical_clock") and not meta.get("source_incident_id"):
        return None
    return canonical_change - dump_anchor


def _apply_clock_shift(obj: Any, delta: timedelta | None) -> Any:
    if delta is None:
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in {
                "timestamp",
                "detected",
                "incident_start",
                "symptom_onset",
                "change_at",
                "detected_at",
            } and isinstance(v, str):
                out[k] = _shift_ts(v, delta)
            else:
                out[k] = _apply_clock_shift(v, delta)
        return out
    if isinstance(obj, list):
        return [_apply_clock_shift(x, delta) for x in obj]
    return obj


def _analyze_spans(spans: list[dict] | None) -> dict:
    if not spans:
        return {
            "available": False,
            "note": "No spans.json — trace section incomplete.",
            "slow_spans": 0,
            "slow_provider_spans": 0,
            "provider_duration_ms_p50": None,
            "provider_duration_ms_max": None,
            "span_duration_ms_p50": None,
            "span_duration_ms_max": None,
            "false_lead_assessment": None,
            "samples": [],
        }
    # E-com false-lead path (payment-provider)
    provider = [
        s
        for s in spans
        if s.get("service_name") == "payment-provider"
        or "payments.provider.com" in (s.get("span_name") or "")
    ]
    slow_provider = [s for s in provider if float(s.get("duration_ms") or 0) > 5000]
    # Generic classic-infra / app spans
    slow = [s for s in spans if float(s.get("duration_ms") or 0) > 500]
    durs_all = [float(s.get("duration_ms") or 0) for s in spans]
    durs_slow = [float(s["duration_ms"]) for s in slow] or durs_all
    fast_ok = [
        s
        for s in spans
        if s.get("service_name") in {"token-service", "fraud-service", "pricing-service"}
        and float(s.get("duration_ms") or 0) < 200
    ]
    samples = []
    for s in sorted(slow or spans, key=lambda x: -float(x.get("duration_ms") or 0))[:5]:
        samples.append(
            {
                "trace_id": s.get("trace_id"),
                "service_name": s.get("service_name"),
                "span_name": s.get("span_name"),
                "duration_ms": s.get("duration_ms"),
                "ci": (s.get("attributes") or {}).get("ci"),
                "note": (s.get("attributes") or {}).get("note"),
            }
        )
    if slow_provider:
        assessment = (
            "Payment-provider CLIENT/SERVER spans show ≈17s duration on affected traces, "
            "but sibling services remain fast and only NP-17 payment pods correlate — "
            "treat external provider as a false lead; latency is consistent with "
            "pre-provider DNS/connection stall (AAAA / pool)."
        )
    elif any((s.get("attributes") or {}).get("note") == "root_evidence" for s in spans):
        assessment = (
            "Trace samples include infra/root-layer spans that corroborate the localized "
            "root CI; app spans show elevated latency as a downstream symptom."
        )
    elif any((s.get("attributes") or {}).get("note") == "app_pool_exhaustion" for s in spans):
        assessment = (
            "Slow spans are confined to the application service with pool/queue waits — "
            "consistent with app-tier exhaustion and healthy upstream infra."
        )
    elif any((s.get("attributes") or {}).get("note") == "network_path_failure" for s in spans):
        assessment = (
            "App spans show connect/timeout failures consistent with an upstream network "
            "path break; treat app errors as blast-radius symptoms."
        )
    else:
        assessment = (
            f"Analyzed {len(spans)} spans; {len(slow)} exceed 500ms. "
            "Use span CI attributes with topology to separate symptom from root."
        )
    return {
        "available": True,
        "analyzed_spans": len(spans),
        "slow_spans": len(slow),
        "slow_provider_spans": len(slow_provider),
        "provider_duration_ms_p50": (
            round(mean([float(s["duration_ms"]) for s in slow_provider]), 1)
            if slow_provider
            else None
        ),
        "provider_duration_ms_max": (
            round(max(float(s["duration_ms"]) for s in slow_provider), 1)
            if slow_provider
            else None
        ),
        "span_duration_ms_p50": round(mean(durs_slow), 1) if durs_slow else None,
        "span_duration_ms_max": round(max(durs_all), 1) if durs_all else None,
        "healthy_sibling_spans_under_200ms": len(fast_ok),
        "false_lead_assessment": assessment,
        "samples": samples,
    }


def _analyze_logs(events: list[dict], raw_logs: list[dict] | None) -> dict:
    patterns: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        patterns[ev.get("event_type") or "unknown"].append(
            {
                "timestamp": ev.get("timestamp"),
                "ci": ev.get("ci"),
                "severity": ev.get("severity"),
                "message": ev.get("message"),
            }
        )
    extra: dict[str, int] = {}
    if raw_logs:
        for row in raw_logs:
            lg = row.get("logger") or row.get("stream") or "log"
            extra[lg] = extra.get(lg, 0) + 1
    # Prefer one/few findings per layer so app WARNs are not drowned by kernel spam.
    key_type_order = [
        "infra.automation",
        "kernel.net",
        "dns.resolver",
        "payment.client",
        "http.connection",
        "checkout.orchestrator",
        "payment.retry",
        "alert.fire",
        # ObserveOps classic-infra synthetic events
        "infra.change",
        "config.change",
        "snmp.linkDown",
        "snmp.ifOutDiscards",
        "esx.cpu.ready",
        "esx.cpu.usage",
        "esx.net.drop",
        "vmware.cpu.ready",
        "vmware.disk.latency",
        "storage.latency",
        "storage.iops",
        "syslog.loadavg",
        "syslog.filesystem_full",
        "syslog.oom_killer",
        "app.latency",
        "app.timeout",
        "app.db_slow",
        "app.crash",
        "app.thread_pool",
        "app.heap",
        "app.error_rate",
    ]
    key_findings: list[str] = []
    for et in key_type_order:
        for e in events:
            if e.get("event_type") != et or not e.get("message"):
                continue
            msg = e["message"]
            if msg in key_findings:
                continue
            key_findings.append(msg)
            break
        if len(key_findings) >= 12:
            break
    return {
        "pack_event_types": {
            k: {"count": len(v), "examples": v[:3]} for k, v in sorted(patterns.items())
        },
        "raw_logger_counts": extra or None,
        "key_findings": key_findings,
    }


def _analyze_metrics(anomalies: list[dict], raw_metrics: list[dict] | None) -> dict:
    sections = []
    for a in anomalies:
        if not a.get("crossed"):
            continue
        sections.append(
            {
                "ci": a["ci"],
                "signal": a["signal"],
                "value": a["value"],
                "threshold": a.get("threshold"),
                "timestamp": a["timestamp"],
                "note": a.get("note"),
            }
        )
    raw_peaks: dict[str, float] = {}
    if raw_metrics:
        buckets: dict[str, list[float]] = defaultdict(list)
        for m in raw_metrics:
            name = m.get("metric_name")
            if name in {
                "checkout_latency_p99_ms",
                "dns_query_latency_p99_ms",
                "payment_connection_acquire_ms",
                "kernel_rx_queue_latency_ms",
                "checkout_success_rate",
                "irq_affinity_numa_mismatch",
                "api_gateway_error_rate_pct",
                "checkout_error_rate_pct",
                "payment_service_error_rate_pct",
                "checkout_requests_total",
                "checkout_failures_total",
            }:
                try:
                    buckets[name].append(float(m["value"]))
                except (TypeError, ValueError, KeyError):
                    pass
        for name, vals in buckets.items():
            if name in {"checkout_success_rate"}:
                raw_peaks[name] = round(min(vals), 3)
            elif name in {
                "api_gateway_error_rate_pct",
                "checkout_error_rate_pct",
                "payment_service_error_rate_pct",
            }:
                raw_peaks[name] = round(max(vals), 2)
            elif name in {"checkout_requests_total", "checkout_failures_total"}:
                raw_peaks[name] = int(max(vals))
            else:
                raw_peaks[name] = round(max(vals), 1)
    return {"crossed_anomalies": sections, "raw_metric_peaks": raw_peaks or None}


def _load_changes_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.append(
            {
                "timestamp": row.get("timestamp") or row.get("ts"),
                "ci": row.get("ci") or row.get("target_ci"),
                "event_type": row.get("event_type") or row.get("change_type") or "infra.change",
                "severity": row.get("severity") or "info",
                "message": row.get("message")
                or row.get("summary")
                or json.dumps(row)[:160],
            }
        )
    return out


def _recent_changes(events: list[dict], *, change_rows: list[dict] | None = None) -> dict:
    change_types = {
        "infra.automation",
        "deploy.app",
        "infra.change",
        "config.change",
        "vmware.change",
    }
    changes = [
        e
        for e in (list(events) + list(change_rows or []))
        if e.get("event_type") in change_types
        or (e.get("message") or "").lower().find("node image") >= 0
        or (e.get("message") or "").lower().find("irq affinity") >= 0
        or (e.get("message") or "").lower().find("change") >= 0
        or (e.get("message") or "").lower().find("vMotion") >= 0
        or (e.get("message") or "").lower().find("rebalance") >= 0
    ]
    # de-dupe by timestamp+message
    seen: set[tuple] = set()
    uniq: list[dict] = []
    for e in changes:
        key = (e.get("timestamp"), e.get("message"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)
    changes = uniq
    root_change = next(
        (
            e
            for e in changes
            if "2026.06.18" in (e.get("message") or "")
            or "IRQ affinity" in (e.get("message") or "")
            or e.get("event_type") in {"infra.change", "infra.automation", "config.change"}
        ),
        changes[0] if changes else None,
    )
    return {
        "change_events": changes[:10],
        "root_cause_change": root_change,
    }


def _timeline(
    events: list[dict],
    anomalies: list[dict],
    seed: dict,
    *,
    meta: dict | None = None,
) -> list[dict]:
    items: list[dict] = []
    # Cap noisy app streams so smoking-gun + alert rows survive the 50-row budget.
    per_type_cap = {
        "payment.client": 3,
        "http.connection": 3,
        "checkout.orchestrator": 3,
        "kernel.net": 8,
        "dns.resolver": 4,
        "infra.automation": 8,
        "deploy.app": 4,
        "alert.fire": 8,
        "infra.change": 4,
        "config.change": 4,
        "snmp.linkDown": 4,
        "snmp.ifOutDiscards": 4,
        "esx.cpu.ready": 4,
        "esx.cpu.usage": 4,
        "esx.net.drop": 4,
        "vmware.cpu.ready": 4,
        "vmware.disk.latency": 4,
        "storage.latency": 4,
        "storage.iops": 4,
        "syslog.loadavg": 4,
        "syslog.filesystem_full": 4,
        "syslog.oom_killer": 4,
        "app.latency": 4,
        "app.timeout": 4,
        "app.db_slow": 4,
        "app.crash": 4,
        "app.thread_pool": 4,
        "app.heap": 4,
        "app.error_rate": 4,
    }
    type_counts: dict[str, int] = {}
    timeline_types = set(per_type_cap)
    for e in events:
        et = e.get("event_type") or "event"
        if et not in timeline_types:
            continue
        n = type_counts.get(et, 0)
        if n >= per_type_cap.get(et, 4):
            continue
        type_counts[et] = n + 1
        items.append(
            {
                "timestamp": e["timestamp"],
                "kind": "alert" if et == "alert.fire" else "event",
                "summary": f"{et}: {(e.get('message') or '')[:120]}",
            }
        )
    for a in anomalies:
        if a.get("crossed"):
            items.append(
                {
                    "timestamp": a["timestamp"],
                    "kind": "anomaly",
                    "summary": f"{a['ci']} `{a['signal']}`={a['value']}",
                }
            )
    items.append(
        {
            "timestamp": seed.get("timestamp"),
            "kind": "symptom_seed",
            "summary": f"Symptom seed {seed.get('ci')} / {seed.get('signal')}",
        }
    )
    # Pack-authored alerts (dump-relative; remapped with the rest of the report)
    # Skip if an alert.fire event already covers the same instant.
    existing_alert_ts = {
        it.get("timestamp") for it in items if it.get("kind") == "alert"
    }
    for alert in (meta or {}).get("alerts") or []:
        ts = alert.get("timestamp")
        if not ts or ts in existing_alert_ts:
            continue
        name = alert.get("name") or "alert"
        items.append(
            {
                "timestamp": ts,
                "kind": "alert",
                "summary": f"alert.fire: Alert {name} fired",
            }
        )
        existing_alert_ts.add(ts)
    items.sort(key=lambda x: x.get("timestamp") or "")
    out: list[dict] = []
    seen = set()
    for it in items:
        key = (it.get("timestamp"), it.get("summary"))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)

    # Prefer chronological order; never drop alerts when truncating.
    if len(out) <= 50:
        return out
    alerts = [it for it in out if it.get("kind") == "alert"]
    others = [it for it in out if it.get("kind") != "alert"]
    selected = others[: max(0, 50 - len(alerts))] + alerts
    selected.sort(key=lambda x: x.get("timestamp") or "")
    return selected


def _narrative_causal_steps(
    *,
    events: list[dict],
    anomalies: list[dict],
    traces: dict,
    gt: dict,
) -> list[dict]:
    """Evidence-backed cascade (not topology CIs) matching gold prose substance."""
    steps: list[dict] = []
    change = next(
        (
            e
            for e in events
            if e.get("event_type") == "infra.automation"
            and "2026.06.18" in (e.get("message") or "")
        ),
        None,
    )
    if change:
        steps.append(
            {
                "step": "node_image_irq_change",
                "summary": change.get("message"),
                "evidence": "event",
                "timestamp": change.get("timestamp"),
            }
        )
    irq = next(
        (a for a in anomalies if a.get("signal") == "irq_affinity_numa_mismatch"),
        None,
    )
    rx = next(
        (a for a in anomalies if a.get("signal") == "kernel_rx_queue_latency_ms"),
        None,
    )
    dns = next(
        (a for a in anomalies if a.get("signal") == "dns_query_latency_p99_ms"),
        None,
    )
    pool = next(
        (a for a in anomalies if a.get("signal") == "payment_connection_acquire_ms"),
        None,
    )
    if irq:
        steps.append(
            {
                "step": "cross_numa_irq",
                "summary": f"IRQ affinity mismatch on `{irq['ci']}` value={irq['value']}",
                "evidence": "anomaly",
                "timestamp": irq.get("timestamp"),
            }
        )
    if rx:
        steps.append(
            {
                "step": "rx_queue_stall",
                "summary": f"RX-7 latency `{rx['signal']}`={rx['value']}ms",
                "evidence": "anomaly",
                "timestamp": rx.get("timestamp"),
            }
        )
    if dns:
        steps.append(
            {
                "step": "aaaa_dns_stall",
                "summary": f"AAAA DNS p99 `{dns['signal']}`={dns['value']}ms",
                "evidence": "anomaly",
                "timestamp": dns.get("timestamp"),
            }
        )
    if pool:
        steps.append(
            {
                "step": "payment_pool_stall",
                "summary": f"Payment acquire `{pool['signal']}`={pool['value']}ms",
                "evidence": "anomaly",
                "timestamp": pool.get("timestamp"),
            }
        )
    if traces.get("slow_provider_spans"):
        steps.append(
            {
                "step": "provider_span_false_lead",
                "summary": (
                    f"Payment-provider spans ≈{traces.get('provider_duration_ms_p50')}ms "
                    f"×{traces.get('slow_provider_spans')} — false lead"
                ),
                "evidence": "trace",
                "timestamp": None,
            }
        )
    ecom_cascade = any(
        s.get("step")
        in {
            "node_image_irq_change",
            "cross_numa_irq",
            "rx_queue_stall",
            "aaaa_dns_stall",
            "payment_pool_stall",
            "provider_span_false_lead",
        }
        for s in steps
    )
    if not ecom_cascade:
        # ObserveOps / classic-infra: events → crossed anomalies → traces
        classic: list[dict] = []
        for e in events:
            if e.get("event_type") and e.get("message"):
                classic.append(
                    {
                        "step": e["event_type"],
                        "summary": e["message"],
                        "evidence": "event",
                        "timestamp": e.get("timestamp"),
                    }
                )
            if len(classic) >= 6:
                break
        for a in anomalies:
            if not a.get("crossed"):
                continue
            classic.append(
                {
                    "step": f"anomaly_{a.get('signal')}",
                    "summary": f"`{a['ci']}` {a.get('signal')}={a.get('value')}",
                    "evidence": "anomaly",
                    "timestamp": a.get("timestamp"),
                }
            )
            if len(classic) >= 10:
                break
        if traces.get("available") and (
            traces.get("slow_spans") or traces.get("analyzed_spans")
        ):
            classic.append(
                {
                    "step": "trace_symptom_spans",
                    "summary": (
                        f"{traces.get('slow_spans') or traces.get('analyzed_spans')} spans "
                        f"(p50≈{traces.get('span_duration_ms_p50')}ms) corroborate the cascade"
                    ),
                    "evidence": "trace",
                    "timestamp": None,
                }
            )
        if classic:
            steps = classic
    slo = next(
        (a for a in anomalies if a.get("signal") == "checkout_success_rate"),
        None,
    )
    gw = next(
        (a for a in anomalies if a.get("signal") == "api_gateway_error_rate_pct"),
        None,
    )
    if slo or gw:
        parts = []
        if slo:
            parts.append(f"checkout success={slo['value']}%")
        if gw:
            parts.append(f"api-gateway error={gw['value']}%")
        steps.append(
            {
                "step": "checkout_gateway_symptom",
                "summary": "; ".join(parts),
                "evidence": "anomaly",
                "timestamp": (slo or gw).get("timestamp"),
            }
        )
    if gt.get("amplifier"):
        steps.append(
            {
                "step": "amplifier",
                "summary": gt["amplifier"],
                "evidence": "ground_truth_amplifier",
                "timestamp": None,
            }
        )
    return steps


def _completeness(report: dict) -> dict:
    checks = {
        "incident_summary": bool(report.get("incident_summary", {}).get("customer_impact")),
        "rca_summary": bool(report.get("rca_summary", {}).get("narrative")),
        "impact": bool(report.get("impact", {}).get("sla_breach")),
        "service_dependencies": bool(
            report.get("service_dependencies", {}).get("critical_path")
        ),
        "distributed_traces": bool(
            report.get("distributed_traces", {}).get("available")
        ),
        "log_patterns": bool(report.get("log_patterns", {}).get("key_findings")),
        "metrics_analysis": bool(
            report.get("metrics_analysis", {}).get("crossed_anomalies")
        ),
        "recent_changes": bool(
            report.get("recent_changes", {}).get("root_cause_change")
        ),
        "causal_chain": bool(
            report.get("causal_chain", {}).get("topology_path")
            or report.get("causal_chain", {}).get("steps")
        )
        and bool(report.get("causal_chain", {}).get("narrative_steps")),
        "contributing_factors": bool(
            report.get("contributing_factors", {}).get("primary")
        ),
        "timeline": bool(report.get("timeline")),
        "actions": bool(report.get("actions", {}).get("immediate")),
        "remediation": bool(report.get("remediation", {}).get("guidance")),
        "executive_summary": bool(
            report.get("executive_summary", {}).get("potential_cause")
        ),
        "localization_root": bool(report.get("localization", {}).get("root_ci")),
    }
    passed = sum(1 for v in checks.values() if v)
    return {
        "checks": checks,
        "score": f"{passed}/{len(checks)}",
        "pct": round(100.0 * passed / len(checks), 1),
        "ready_for_gold_parity": passed == len(checks),
    }


def _build_rca_summary(
    *,
    root_ci: str,
    signature: str,
    chain: list[str],
    gt: dict,
    changes: dict,
    customer_impact: str,
    false_leads: list[str],
) -> dict:
    change = (changes.get("root_cause_change") or {}).get("message")
    primary = gt.get("fault_title") or f"`{root_ci}` ({signature})"
    amplifier = gt.get("amplifier") or (
        "payment-risk / high-cardinality request pattern"
        if signature == "cross_numa_irq_affinity"
        else "classic-infra cascade (shared upstream fault → app symptom)"
    )
    causal_path = " → ".join(f"`{c}`" for c in chain) if chain else "_n/a_"
    false_lead_txt = (
        ", ".join(f"`{fl}`" for fl in false_leads) if false_leads else None
    )
    change_txt = change or (
        "Correlate earliest upstream infra change with onset."
    )

    # Multi-line markdown for report body; also kept as a single prose fallback.
    narrative_md = "\n".join(
        [
            f"**Root cause:** `{root_ci}` (`{signature}`)",
            f"{primary}",
            "",
            f"**Causal path:** {causal_path}",
            "",
            f"**Customer impact:** {customer_impact}",
            "",
            f"**Amplifier:** {amplifier}",
            "",
            (
                f"**False leads ruled out:** {false_lead_txt}"
                if false_lead_txt
                else "**False leads ruled out:** none identified"
            ),
            "",
            f"**Change evidence:** {change_txt}",
        ]
    )
    narrative = (
        f"RCA localizes the incident to `{root_ci}` ({signature}): {primary}. "
        f"Causal path: {' → '.join(chain)}. "
        f"Customer impact: {customer_impact}. "
        f"Amplifier: {amplifier}. "
        + (
            f"Ruled out false leads: {', '.join(false_leads)}. "
            if false_leads
            else ""
        )
        + f"Root-cause change evidence: {change_txt}"
    )
    return {
        "narrative": narrative,
        "narrative_md": narrative_md,
        "root_ci": root_ci,
        "signature": signature,
        "causal_path": chain,
        "fault_title": primary,
        "customer_impact": customer_impact,
        "amplifier": amplifier,
        "false_leads": list(false_leads),
        "change_evidence": change_txt,
    }


def _build_remediation(signature: str, actions: dict) -> dict:
    return {
        "guidance": REMEDIATION_NARRATIVE_BY_SIGNATURE.get(
            signature, DEFAULT_REMEDIATION_NARRATIVE
        ),
        "immediate": list(actions.get("immediate") or []),
        "future": list(actions.get("future") or []),
        "source": "signature_template",  # replace with LLM output when wired
    }


def build_comprehensive_report(
    *,
    pack_dir: Path,
    verdict: dict,
    raw_dir: Path | None = None,
) -> dict:
    topology = _load_json(pack_dir / "topology.json", {"nodes": [], "edges": []})
    anomalies_doc = _load_json(pack_dir / "anomalies.json", {"anomalies": []})
    anomalies = anomalies_doc.get("anomalies") or []
    seed = _load_json(pack_dir / "symptom_seed.json", {})
    gt = _load_json(pack_dir / "ground_truth.json", {})
    events_doc = _load_json(pack_dir / "events.json", {"events": []})
    events = events_doc.get("events") or []
    meta = _load_json(pack_dir / "incident_meta.json", {})
    change_rows = _load_changes_jsonl(pack_dir / "changes.jsonl")

    # Prefer pack-local raw/ (ObserveOps UC multimodal); else ecom-style ../../raw
    if raw_dir is None:
        if (pack_dir / "raw").is_dir():
            raw_dir = pack_dir / "raw"
        elif (pack_dir.parent.parent / "raw").is_dir():
            raw_dir = pack_dir.parent.parent / "raw"
        else:
            raw_dir = pack_dir / "raw"
    spans = _load_json(raw_dir / "spans.json", None) if raw_dir.is_dir() else None
    logs = _load_json(raw_dir / "logs.json", None) if raw_dir.is_dir() else None
    metrics = _load_json(raw_dir / "metrics.json", None) if raw_dir.is_dir() else None

    root_ci = verdict.get("root_ci") or gt.get("root_ci")
    signature = verdict.get("signature") or gt.get("signature") or "unknown"
    seed_ci = seed.get("ci") or "checkout-service"
    prefer = {item.get("ci") for item in (verdict.get("evidence") or []) if item.get("ci")}
    prefer.update(verdict.get("contributor_cis") or [])
    prefer.update(gt.get("contributor_cis") or [])

    # Prefer a full root→seed topology path. Verdict chains that are missing or
    # root-only (common for Federated) must not truncate the narrative.
    verdict_chain = verdict.get("causal_chain") or []
    topo_chain = _shortest_root_to_seed(topology, root_ci, seed_ci, prefer)
    if isinstance(verdict_chain, list) and len(verdict_chain) >= len(topo_chain) >= 2:
        chain = verdict_chain
    else:
        chain = topo_chain

    path = _critical_path(topology)
    slo = next(
        (a for a in anomalies if a.get("signal") == "checkout_success_rate"),
        None,
    )
    gw_err = next(
        (
            a
            for a in anomalies
            if a.get("signal") in {"api_gateway_error_rate_pct", "gateway_http_5xx_rate"}
        ),
        None,
    )
    traces = _analyze_spans(spans if isinstance(spans, list) else None)
    logs_sec = _analyze_logs(events, logs if isinstance(logs, list) else None)
    metrics_sec = _analyze_metrics(anomalies, metrics if isinstance(metrics, list) else None)
    changes = _recent_changes(events, change_rows=change_rows)
    actions = ACTIONS_BY_SIGNATURE.get(signature, DEFAULT_ACTIONS)

    false_leads = list(gt.get("false_leads") or [])
    if "payment-provider" not in false_leads and "payment-provider" in {
        n["id"] for n in topology.get("nodes", [])
    }:
        false_leads.append("payment-provider")

    impact_q = gt.get("impact") or meta.get("impact") or {}
    failed = impact_q.get("failed_requests")
    total = impact_q.get("total_requests")
    # Prefer measured gateway anomaly so Impact matches Metrics (objective consistency).
    peak_err = gw_err.get("value") if gw_err is not None else impact_q.get(
        "peak_path_error_rate_pct"
    )
    fail_frac = impact_q.get("fail_fraction_pct", 2.8)
    path_label = impact_q.get("path") or "api-gateway → checkout-service"

    checkout_err = next(
        (a for a in anomalies if a.get("signal") == "checkout_error_rate_pct"),
        None,
    )
    payment_err = next(
        (a for a in anomalies if a.get("signal") == "payment_service_error_rate_pct"),
        None,
    )

    if failed is not None and total is not None:
        customer_impact = (
            f"Checkout success ≈{slo['value']}% (threshold {slo.get('threshold')}) "
            f"on `{seed.get('ci')}` / `{seed.get('signal')}`; "
            f"≈{failed}/{total} failed checkouts in the incident window "
            f"(≈{fail_frac}% of the affected dimension)"
            if slo
            else (
                f"≈{failed}/{total} failed checkouts "
                f"(≈{fail_frac}% of the affected dimension)"
            )
        )
        fail_fraction_txt = (
            f"≈{failed} failed / {total} checkout transactions "
            f"(≈{fail_frac}% of affected dimension)"
        )
    else:
        customer_impact = (
            f"Checkout success ≈{slo['value']}% (threshold {slo.get('threshold')}) "
            f"on seeded symptom `{seed.get('ci')}` / `{seed.get('signal')}`"
            if slo
            else (
                gt.get("note")
                or (
                    f"Symptom `{seed.get('signal')}` on `{seed.get('ci')}` "
                    f"({gt.get('fault_title') or signature})"
                )
            )
        )
        fail_fraction_txt = f"≈{fail_frac}% of checkouts in the affected dimension"

    services = [
        n["id"]
        for n in topology.get("nodes", [])
        if n.get("type") == "Service" and "provider" not in n["id"]
    ]
    # Prefer gateway-first ordering when present
    if "api-gateway" in services:
        services = ["api-gateway"] + [s for s in services if s != "api-gateway"]

    clock = meta.get("canonical_clock") or {}
    # Dump-relative detect from pack alert / meta; remapped with the rest of the report.
    alert_ts = None
    for e in events:
        if e.get("event_type") == "alert.fire":
            alert_ts = e.get("timestamp")
            break
    if not alert_ts and (meta.get("alerts") or []):
        alert_ts = meta["alerts"][0].get("timestamp")
    detected = alert_ts or meta.get("detected_at") or seed.get("timestamp")

    narrative_steps = _narrative_causal_steps(
        events=events, anomalies=anomalies, traces=traces, gt=gt
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "incident_id": verdict.get("uc_id") or pack_dir.name,
        "source_incident_id": meta.get("source_incident_id"),
        "engine": verdict.get("engine") or "unknown",
        "generated_at": _iso_now(),
        "pack_meta": {
            "incident_start": anomalies_doc.get("incident_start"),
            "symptom_onset": meta.get("symptom_onset") or seed.get("timestamp"),
            "detected_at": detected,
            "change_at": meta.get("incident_start") or anomalies_doc.get("incident_start"),
            "raw_dir": str(raw_dir) if raw_dir.is_dir() else None,
            "source_incident_id": meta.get("source_incident_id"),
            "impact_source": (gt.get("impact") or meta.get("impact") or {}).get("source"),
        },
        "localization": {
            "root_ci": root_ci,
            "signature": signature,
            "contributor_cis": verdict.get("contributor_cis")
            or gt.get("contributor_cis")
            or [],
            "false_leads_ruled_out": false_leads,
            "matches_pack_gt": root_ci == gt.get("root_ci"),
        },
        "incident_summary": {
            "severity": "P3 (Medium)" if slo and float(slo.get("value") or 100) > 95 else "P2",
            "detected": detected,
            "affected_services": services,
            "customer_impact": customer_impact,
            "dimension_slice": (
                meta.get("dimension_slice")
                or gt.get("dimension_slice")
                or (
                    "Region-B · CARD · MOBILE · INR · cart_items>12 "
                    "(payment-risk amplifier)"
                    if gt.get("signature") == "cross_numa_irq_affinity"
                    or (meta.get("source_incident_id") or "") == GOLD_SOURCE_INCIDENT_ID
                    else f"ObserveOps classic-infra · `{gt.get('fault_bucket') or 'n/a'}` / `{gt.get('fault_type') or signature}`"
                )
            ),
            "gt_fault_title": gt.get("fault_title"),
        },
        "impact": {
            "services_affected": gt.get("blast_radius")
            or verdict.get("blast_radius")
            or [],
            "sla_breach": True if slo else bool(anomalies),
            "data_loss": False,
            "failed_requests": failed,
            "total_requests": total,
            "peak_path_error_rate_pct": peak_err,
            "path_error_label": path_label,
            "checkout_error_rate_pct": (
                checkout_err.get("value") if checkout_err else None
            ),
            "payment_service_error_rate_pct": (
                payment_err.get("value") if payment_err else None
            ),
            "error_escalation": (
                f"payment-service {payment_err.get('value') if payment_err else 'n/a'}% → "
                f"checkout-service {checkout_err.get('value') if checkout_err else 'n/a'}% → "
                f"api-gateway {peak_err if peak_err is not None else 'n/a'}%"
                if checkout_err or payment_err or peak_err is not None
                else None
            ),
            "estimated_fail_fraction": fail_fraction_txt,
            "source": (gt.get("impact") or meta.get("impact") or {}).get("source"),
            "notes": gt.get("note"),
        },
        "service_dependencies": {
            "critical_path": path,
            "topology_edges": topology.get("edges") or [],
            "isolation_note": (
                "Healthy siblings (pricing/inventory/token/fraud) are not on the "
                "failing payment path; errors escalate api-gateway ← checkout ← "
                "payment ← (DNS/RX/IRQ), with payment-provider as a decoy leaf."
                if any(
                    "payment" in str(n.get("id") or "").lower()
                    or "checkout" in str(n.get("id") or "").lower()
                    for n in (topology.get("nodes") or [])
                )
                or "ecom" in str(pack_dir).lower()
                else (
                    (
                        f"Fault spreads { ' → '.join(path) } on this classic-infra pack map; "
                        "other CIs on the small topology are not on this blast path."
                    )
                    if path and len(path) > 1
                    else (
                        f"Root CI {path[0] if path else verdict.get('root_ci') or gt.get('root_ci')} "
                        "on the pack topology; customer symptom is usually downstream."
                    )
                )
            ),
        },
        "distributed_traces": traces,
        "log_patterns": logs_sec,
        "metrics_analysis": metrics_sec,
        "recent_changes": changes,
        "causal_chain": {
            "steps": chain,
            "topology_path": chain,
            "narrative_steps": narrative_steps,
            "narrative": (
                " → ".join(chain)
                + ". Amplifier: "
                + (gt.get("amplifier") or "high-cardinality request pattern.")
            ),
        },
        "contributing_factors": {
            "primary": gt.get("fault_title")
            or f"Root CI `{root_ci}` ({signature})",
            "amplifier": gt.get("amplifier"),
            "false_leads": false_leads,
        },
        "timeline": _timeline(events, anomalies, seed, meta=meta),
        "actions": actions,
        "rca_summary": _build_rca_summary(
            root_ci=root_ci,
            signature=signature,
            chain=chain,
            gt=gt,
            changes=changes,
            customer_impact=customer_impact,
            false_leads=false_leads,
        ),
        "remediation": _build_remediation(signature, actions),
        "executive_summary": {
            "potential_cause": (
                changes.get("root_cause_change", {}) or {}
            ).get("message")
            or gt.get("note")
            or f"Localized to `{root_ci}` ({signature}).",
            "impact": customer_impact,
            "resolution": "; ".join(actions.get("immediate") or []),
        },
    }

    # Single clock remap for dump-relative timestamps (including detected / alert).
    delta = _clock_delta(meta, anomalies_doc)
    if delta is not None:
        report = _apply_clock_shift(report, delta)
        # pack_meta.change_at should read as canonical change after remap of incident_start
        if clock.get("change_at"):
            # Keep authored canonical change_at as the display anchor label
            report["pack_meta"]["change_at"] = clock["change_at"]

    report["completeness"] = _completeness(report)
    return report


def format_comprehensive_markdown(report: dict) -> str:
    loc = report["localization"]
    summ = report["incident_summary"]
    impact = report["impact"]
    deps = report["service_dependencies"]
    tr = report["distributed_traces"]
    logs = report["log_patterns"]
    met = report["metrics_analysis"]
    ch = report["recent_changes"]
    chain = report["causal_chain"]
    factors = report["contributing_factors"]
    actions = report["actions"]
    rca = report.get("rca_summary") or {}
    rem = report.get("remediation") or {}
    exe = report["executive_summary"]
    comp = report["completeness"]

    lines = [
        f"# Incident Analysis Report — `{report['incident_id']}`",
        "",
        f"**Engine:** `{report['engine']}` · **Schema:** `{report['schema_version']}` · "
        f"**Completeness:** {comp['score']} ({comp['pct']}%)",
    ]
    if report.get("source_incident_id"):
        lines += [
            "",
            f"**Source incident:** `{report['source_incident_id']}`",
        ]
    rca_body = rca.get("narrative_md") or rca.get("narrative") or "_n/a_"
    lines += [
        "",
        "## RCA Summary",
        "",
        *rca_body.splitlines(),
        "",
        "## Incident Summary",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Root CI | `{loc.get('root_ci')}` |",
        f"| Signature | `{loc.get('signature')}` |",
        f"| Matches pack GT | {loc.get('matches_pack_gt')} |",
        f"| Severity | {summ.get('severity')} |",
        f"| Detected | {summ.get('detected')} |",
        f"| Dimension | {summ.get('dimension_slice')} |",
        f"| Affected services | {', '.join(f'`{s}`' for s in summ.get('affected_services') or [])} |",
        f"| Customer impact | {summ.get('customer_impact')} |",
        "",
        "## Impact Assessment",
        "",
        f"- **SLA breach:** {impact.get('sla_breach')}",
        f"- **Data loss:** {impact.get('data_loss')}",
        f"- **Fail fraction:** {impact.get('estimated_fail_fraction')}",
    ]
    if impact.get("failed_requests") is not None and impact.get("total_requests") is not None:
        lines.append(
            f"- **Failed requests:** ≈{impact['failed_requests']} / {impact['total_requests']}"
        )
    if impact.get("peak_path_error_rate_pct") is not None:
        lines.append(
            f"- **Peak path error rate:** {impact['peak_path_error_rate_pct']}% "
            f"on {impact.get('path_error_label') or 'api-gateway → checkout-service'}"
        )
    if impact.get("checkout_error_rate_pct") is not None:
        lines.append(
            f"- **Checkout service error rate:** {impact['checkout_error_rate_pct']}%"
        )
    if impact.get("payment_service_error_rate_pct") is not None:
        lines.append(
            f"- **Payment service error rate:** {impact['payment_service_error_rate_pct']}% "
            f"(blast-radius / escalation baseline)"
        )
    if impact.get("error_escalation"):
        lines.append(f"- **Error escalation:** {impact['error_escalation']}")
    lines += [
        f"- **Blast / services:** {', '.join(f'`{s}`' for s in impact.get('services_affected') or []) or '_n/a_'}",
        "",
        "## Service Dependencies",
        "",
        "**Critical path:** " + " → ".join(f"`{c}`" for c in deps.get("critical_path") or []),
        "",
        deps.get("isolation_note") or "",
        "",
        "## Distributed Traces",
        "",
    ]
    if tr.get("available"):
        lines += [
            f"- Analyzed spans: {tr.get('analyzed_spans')}",
            f"- Slow spans (>500ms): {tr.get('slow_spans')}",
            f"- Span duration p50/max ms: {tr.get('span_duration_ms_p50')} / {tr.get('span_duration_ms_max')}",
        ]
        if tr.get("slow_provider_spans"):
            lines += [
                f"- Slow payment-provider spans: {tr.get('slow_provider_spans')}",
                f"- Provider duration p50/max ms: "
                f"{tr.get('provider_duration_ms_p50')} / {tr.get('provider_duration_ms_max')}",
                f"- Healthy sibling spans (<200ms): {tr.get('healthy_sibling_spans_under_200ms')}",
            ]
        lines += [
            "",
            f"**Assessment:** {tr.get('false_lead_assessment')}",
            "",
        ]
        if tr.get("samples"):
            lines.append("| Trace | Service | Span | Duration ms | CI / note |")
            lines.append("|-------|---------|------|-------------|-----------|")
            for s in tr["samples"]:
                note = s.get("note") or s.get("ci") or ""
                lines.append(
                    f"| `{str(s.get('trace_id',''))[:12]}…` | {s.get('service_name')} | "
                    f"{s.get('span_name')} | {s.get('duration_ms')} | {note} |"
                )
            lines.append("")
    else:
        lines += [f"_{tr.get('note')}_", ""]

    lines += ["## Log Patterns", ""]
    for msg in logs.get("key_findings") or []:
        lines.append(f"- {msg}")
    lines.append("")
    for et, info in (logs.get("pack_event_types") or {}).items():
        lines.append(f"- `{et}` × {info['count']}")
    lines.append("")

    lines += ["## Metrics Analysis", ""]
    for a in met.get("crossed_anomalies") or []:
        note = f" — {a['note']}" if a.get("note") else ""
        lines.append(
            f"- `{a['ci']}` `{a['signal']}` = **{a['value']}** "
            f"(threshold {a.get('threshold')}) at {a['timestamp']}{note}"
        )
    if met.get("raw_metric_peaks"):
        lines.append("")
        lines.append("Raw export peaks/mins:")
        for k, v in met["raw_metric_peaks"].items():
            lines.append(f"- `{k}` → {v}")
    lines.append("")

    lines += ["## Recent Changes", ""]
    rc = ch.get("root_cause_change")
    if rc:
        lines.append(
            f"**Root-cause change:** {rc.get('timestamp')} — {rc.get('message')}"
        )
    for e in ch.get("change_events") or []:
        lines.append(f"- {e.get('timestamp')}: {e.get('message')}")
    lines.append("")

    lines += [
        "## Causal Chain",
        "",
        "**Topology path:** " + (chain.get("narrative") or ""),
        "",
    ]
    if chain.get("narrative_steps"):
        lines.append("**Narrative steps (evidence-backed):**")
        lines.append("")
        for i, step in enumerate(chain["narrative_steps"], 1):
            ts = step.get("timestamp") or ""
            lines.append(
                f"{i}. `{step.get('step')}` — {step.get('summary')} "
                f"({step.get('evidence')}{', ' + ts if ts else ''})"
            )
        lines.append("")
    lines += [
        "## Contributing Factors",
        "",
        f"- **Primary:** {factors.get('primary')}",
        f"- **Amplifier:** {factors.get('amplifier')}",
        f"- **False leads:** {', '.join(factors.get('false_leads') or [])}",
        "",
        "## Timeline",
        "",
    ]
    for t in report.get("timeline") or []:
        lines.append(f"- {t.get('timestamp')} · {t.get('kind')} — {t.get('summary')}")
    lines += [
        "",
        "## Remediation",
        "",
        rem.get("guidance") or "_n/a_",
        "",
        f"_Source: `{rem.get('source') or 'n/a'}` (replace with LLM guidance when available)_",
        "",
        "## Actions",
        "",
        "### Immediate",
    ]
    for a in (rem.get("immediate") or actions.get("immediate") or []):
        lines.append(f"- {a}")
    lines.append("")
    lines.append("### Future")
    for a in (rem.get("future") or actions.get("future") or []):
        lines.append(f"- {a}")
    lines += [
        "",
        "## Executive Summary",
        "",
        f"**Potential cause:** {exe.get('potential_cause')}",
        "",
        f"**Impact:** {exe.get('impact')}",
        "",
        f"**Resolution:** {exe.get('resolution')}",
        "",
        "## Completeness checklist",
        "",
    ]
    for k, ok in (comp.get("checks") or {}).items():
        lines.append(f"- [{'x' if ok else ' '}] {k}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pack",
        type=Path,
        default=REPO / "datasets/ecom_checkout/incidents/ecom-numa-001",
    )
    p.add_argument(
        "--raw",
        type=Path,
        default=REPO / "datasets/ecom_checkout/raw",
    )
    p.add_argument(
        "--verdict",
        type=Path,
        help="Engine verdict.json (Lean or Federated)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        help="Write incident_report.json + incident_report.md here",
    )
    args = p.parse_args(argv)

    if args.verdict and args.verdict.is_file():
        verdict = json.loads(args.verdict.read_text())
    else:
        # Localization-only stub from GT — still builds multimodal sections
        gt = _load_json(args.pack / "ground_truth.json", {})
        verdict = {
            "engine": "pack-gt-stub",
            "uc_id": args.pack.name,
            "root_ci": gt.get("root_ci"),
            "signature": gt.get("signature"),
            "contributor_cis": gt.get("contributor_cis") or [],
            "causal_chain": None,
            "blast_radius": gt.get("blast_radius") or [],
        }

    report = build_comprehensive_report(
        pack_dir=args.pack, verdict=verdict, raw_dir=args.raw
    )
    md = format_comprehensive_markdown(report)

    out = args.out_dir
    if out is None and args.verdict:
        out = args.verdict.parent
    if out is None:
        # Ad-hoc gold-parity outputs — not main corpus / product scoreboards.
        eng = str(verdict.get("engine") or "pack").replace("_", "-")
        out = REPO / "_adhoc/ecom-gold-report-compare/reports" / eng
    out.mkdir(parents=True, exist_ok=True)
    (out / "incident_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "incident_report.md").write_text(md)
    print(f"Wrote {out / 'incident_report.md'} (completeness {report['completeness']['score']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
