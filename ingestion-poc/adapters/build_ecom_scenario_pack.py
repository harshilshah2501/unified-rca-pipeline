#!/usr/bin/env python3
"""Build Lean/Federated engine pack from e-commerce scenario JSON export.

Reads metrics/logs/spans JSON produced by export_scenario_postgres_json.py
(from dump_scenario_postgres.sh Postgres tables) and writes a frozen pack:

  topology.json, anomalies.json, symptom_seed.json, ground_truth.json,
  events.json, incident_meta.json

Causal chain (effect → cause) mirrors scenario.md:
  api-gateway → checkout-service → payment-service → dns-aaaa-np17 → nic-rx-queue-7 → np17-irq-affinity
  payment-service → payment-provider   (false lead / decoy branch)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

PACK_ID = "ecom-numa-001"
GOLD_SOURCE_INCIDENT_ID = "3GAWT8nVjUE2rA95CZmtyiQcVri"

# Stable CI ids for the causal graph
CI_GATEWAY = "api-gateway"
CI_CHECKOUT = "checkout-service"
CI_PAYMENT = "payment-service"
CI_PROVIDER = "payment-provider"  # false lead
CI_DNS = "dns-aaaa-np17"
CI_RX = "nic-rx-queue-7"
CI_IRQ = "np17-irq-affinity"  # root

# Canonical gold clock (OO incident 3GAWT8nVjU…) — used only for display remap
CANONICAL_CLOCK = {
    "detected_at": "2026-07-07T09:00:58Z",
    "change_at": "2026-07-07T08:25:48Z",
    "window_start": "2026-07-07T08:25:00Z",
    "window_end": "2026-07-07T09:00:58Z",
}
GOLD_ALERT_NAME = "ecom_checkout_slo_breach"


def _parse_ts(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _first_metric(
    metrics: list[dict],
    name: str,
    *,
    pred,
) -> dict | None:
    hits = [
        m
        for m in metrics
        if m.get("metric_name") == name and pred(m)
    ]
    if not hits:
        return None
    return min(hits, key=lambda m: m["ts"])


def _max_metric(
    metrics: list[dict],
    name: str,
    *,
    pred,
) -> dict | None:
    hits = [m for m in metrics if m.get("metric_name") == name and pred(m)]
    if not hits:
        return None
    return max(hits, key=lambda m: float(m.get("value") or 0))


def _max_counter(
    metrics: list[dict],
    name: str,
    *,
    pred,
) -> float | None:
    hits = [m for m in metrics if m.get("metric_name") == name and pred(m)]
    if not hits:
        return None
    return max(float(m.get("value") or 0) for m in hits)


def _derive_impact(
    metrics: list[dict],
    *,
    gateway_peak: dict | None,
    checkout_err_peak: dict | None,
    payment_err_peak: dict | None,
    slo_min: dict | None = None,
) -> dict:
    """Derive quantified impact from telemetry counters + measured error peaks."""
    def slice_pred(m: dict) -> bool:
        labels = m.get("labels") or {}
        if labels.get("region") != "Region-B":
            return False
        if labels.get("slice") == "affected_dimension":
            return True
        return (
            labels.get("payment_method") == "CARD"
            and labels.get("device_type") == "MOBILE"
        )

    total = _max_counter(metrics, "checkout_requests_total", pred=slice_pred)
    failed = _max_counter(metrics, "checkout_failures_total", pred=slice_pred)
    gw = float((gateway_peak or {}).get("value") or 0)
    chk = float((checkout_err_peak or {}).get("value") or 0)
    pay = float((payment_err_peak or {}).get("value") or 0)
    # Dimension fail fraction from SLO (e.g. 100-97.2 ≈ 2.8), not 186/387 window rate.
    fail_frac = None
    if slo_min is not None:
        fail_frac = round(max(0.0, 100.0 - float(slo_min.get("value") or 100)), 2)
    elif total and total > 0 and failed is not None:
        fail_frac = round(100.0 * failed / total, 2)
    return {
        "failed_requests": int(failed) if failed is not None else None,
        "total_requests": int(total) if total is not None else None,
        "peak_path_error_rate_pct": round(gw, 2) if gateway_peak else None,
        "checkout_error_rate_pct": round(chk, 2) if checkout_err_peak else None,
        "payment_service_error_rate_pct": round(pay, 2) if payment_err_peak else None,
        "path": "api-gateway → checkout-service",
        "fail_fraction_pct": fail_frac if fail_frac is not None else 2.8,
        "source": "derived_from_telemetry",
    }


def build_pack(raw_dir: Path, out_dir: Path) -> dict:
    metrics = json.loads((raw_dir / "metrics.json").read_text())
    logs = json.loads((raw_dir / "logs.json").read_text())
    spans = json.loads((raw_dir / "spans.json").read_text())
    manifest = {}
    man_path = raw_dir / "manifest.json"
    if man_path.is_file():
        manifest = json.loads(man_path.read_text())

    # --- onset anchors from scenario signals ---
    irq_onset = _first_metric(
        metrics,
        "irq_affinity_numa_mismatch",
        pred=lambda m: float(m.get("value") or 0) >= 1.0
        and (m.get("labels") or {}).get("node_pool") == "NP-17",
    )
    rx_onset = _first_metric(
        metrics,
        "kernel_rx_queue_latency_ms",
        pred=lambda m: float(m.get("value") or 0) > 100
        and (m.get("labels") or {}).get("nic_queue") == "RX-7",
    )
    dns_onset = _first_metric(
        metrics,
        "dns_query_latency_p99_ms",
        pred=lambda m: float(m.get("value") or 0) > 500
        and (m.get("labels") or {}).get("query_type") == "AAAA"
        and (m.get("labels") or {}).get("node_pool") == "NP-17",
    )
    pool_onset = _first_metric(
        metrics,
        "payment_connection_acquire_ms",
        pred=lambda m: float(m.get("value") or 0) > 500
        and (m.get("labels") or {}).get("node_pool") == "NP-17",
    )
    _BAD_PODS = {
        "payment-pod-118",
        "payment-pod-124",
        "payment-pod-131",
        "payment-pod-144",
    }
    provider_onset = _first_metric(
        metrics,
        "payment_provider_latency_ms",
        pred=lambda m: float(m.get("value") or 0) > 1000
        and (m.get("labels") or {}).get("pod") in _BAD_PODS,
    )
    checkout_onset = _first_metric(
        metrics,
        "checkout_latency_p99_ms",
        pred=lambda m: float(m.get("value") or 0) > 5000
        and (m.get("labels") or {}).get("region") == "Region-B"
        and (m.get("labels") or {}).get("currency") == "INR"
        and (m.get("labels") or {}).get("cart_items") == "12+",
    )
    slo_onset = _first_metric(
        metrics,
        "checkout_success_rate",
        pred=lambda m: float(m.get("value") or 100) < 99.0
        and (m.get("labels") or {}).get("region") == "Region-B"
        and (m.get("labels") or {}).get("payment_method") == "CARD"
        and (m.get("labels") or {}).get("device_type") == "MOBILE",
    )
    gateway_onset = _first_metric(
        metrics,
        "api_gateway_error_rate_pct",
        pred=lambda m: float(m.get("value") or 0) > 20.0
        and (m.get("labels") or {}).get("region") == "Region-B",
    )

    missing = [
        n
        for n, v in [
            ("irq", irq_onset),
            ("rx", rx_onset),
            ("dns", dns_onset),
            ("pool", pool_onset),
            ("checkout", checkout_onset),
            ("slo", slo_onset),
        ]
        if v is None
    ]
    if missing:
        raise SystemExit(f"Could not find onset metrics for: {missing}")

    irq_peak = _max_metric(
        metrics,
        "irq_affinity_numa_mismatch",
        pred=lambda m: (m.get("labels") or {}).get("node_pool") == "NP-17",
    )
    rx_peak = _max_metric(
        metrics,
        "kernel_rx_queue_latency_ms",
        pred=lambda m: (m.get("labels") or {}).get("nic_queue") == "RX-7",
    )
    dns_peak = _max_metric(
        metrics,
        "dns_query_latency_p99_ms",
        pred=lambda m: (m.get("labels") or {}).get("query_type") == "AAAA"
        and (m.get("labels") or {}).get("node_pool") == "NP-17",
    )
    pool_peak = _max_metric(
        metrics,
        "payment_connection_acquire_ms",
        pred=lambda m: (m.get("labels") or {}).get("node_pool") == "NP-17",
    )
    provider_peak = _max_metric(
        metrics,
        "payment_provider_latency_ms",
        pred=lambda m: float(m.get("value") or 0) > 1000,
    )
    checkout_peak = _max_metric(
        metrics,
        "checkout_latency_p99_ms",
        pred=lambda m: (m.get("labels") or {}).get("region") == "Region-B"
        and (m.get("labels") or {}).get("currency") == "INR"
        and (m.get("labels") or {}).get("cart_items") == "12+",
    )
    _sym_ts = slo_onset["ts"] if slo_onset else None
    slo_hits = [
        m
        for m in metrics
        if m.get("metric_name") == "checkout_success_rate"
        and (m.get("labels") or {}).get("region") == "Region-B"
        and (m.get("labels") or {}).get("payment_method") == "CARD"
        and (m.get("labels") or {}).get("device_type") == "MOBILE"
    ]
    # Prefer symptom-onset sample (deterministic gold 97.2) over jittered window min.
    slo_at_sym = next(
        (m for m in slo_hits if _sym_ts and m.get("ts") == _sym_ts),
        None,
    )
    slo_min = slo_at_sym or (
        min(slo_hits, key=lambda m: float(m.get("value") or 100)) if slo_hits else None
    )
    gateway_hits = [
        m
        for m in metrics
        if m.get("metric_name") == "api_gateway_error_rate_pct"
        and (m.get("labels") or {}).get("region") == "Region-B"
    ]
    # Prefer the symptom-onset sample (deterministic gold peak) over jittered window max.
    gateway_at_sym = next(
        (m for m in gateway_hits if _sym_ts and m.get("ts") == _sym_ts),
        None,
    )
    gateway_peak = gateway_at_sym or (
        max(gateway_hits, key=lambda m: float(m.get("value") or 0))
        if gateway_hits
        else None
    )
    checkout_err_hits = [
        m
        for m in metrics
        if m.get("metric_name") == "checkout_error_rate_pct"
        and (m.get("labels") or {}).get("region") == "Region-B"
    ]
    checkout_err_at_sym = next(
        (m for m in checkout_err_hits if _sym_ts and m.get("ts") == _sym_ts),
        None,
    )
    checkout_err_peak = checkout_err_at_sym or (
        max(checkout_err_hits, key=lambda m: float(m.get("value") or 0))
        if checkout_err_hits
        else None
    )
    payment_err_hits = [
        m
        for m in metrics
        if m.get("metric_name") == "payment_service_error_rate_pct"
        and (m.get("labels") or {}).get("region") == "Region-B"
    ]
    payment_err_at_sym = next(
        (m for m in payment_err_hits if _sym_ts and m.get("ts") == _sym_ts),
        None,
    )
    payment_err_peak = payment_err_at_sym or (
        max(payment_err_hits, key=lambda m: float(m.get("value") or 0))
        if payment_err_hits
        else None
    )

    # incident_start = earliest causal driver (IRQ mismatch)
    incident_start = irq_onset["ts"]
    symptom_ts = slo_onset["ts"]

    anomalies = [
        {
            "ci": CI_IRQ,
            "signal": "irq_affinity_numa_mismatch",
            "value": float(irq_peak["value"]),
            "threshold": 0.0,
            "crossed": True,
            "timestamp": irq_onset["ts"],
            "anomaly_class": "infra",
        },
        {
            "ci": CI_RX,
            "signal": "kernel_rx_queue_latency_ms",
            "value": round(float(rx_peak["value"]), 1),
            "threshold": 10.0,
            "crossed": True,
            "timestamp": rx_onset["ts"],
            "anomaly_class": "infra",
        },
        {
            "ci": CI_DNS,
            "signal": "dns_query_latency_p99_ms",
            "value": round(float(dns_peak["value"]), 1),
            "threshold": 50.0,
            "crossed": True,
            "timestamp": dns_onset["ts"],
            "anomaly_class": "network",
        },
        {
            "ci": CI_PAYMENT,
            "signal": "payment_connection_acquire_ms",
            "value": round(float(pool_peak["value"]), 1),
            "threshold": 100.0,
            "crossed": True,
            "timestamp": pool_onset["ts"],
            "anomaly_class": "app",
        },
        {
            "ci": CI_PROVIDER,
            "signal": "payment_provider_latency_ms",
            "value": round(float((provider_peak or provider_onset)["value"]), 1),
            "threshold": 200.0,
            "crossed": True,
            "timestamp": (provider_onset or pool_onset)["ts"],
            "anomaly_class": "external",
            "note": "FALSE LEAD — only this app's NP-17 pods; provider is healthy for others",
        },
        {
            "ci": CI_CHECKOUT,
            "signal": "checkout_latency_p99_ms",
            "value": round(float(checkout_peak["value"]), 1),
            "threshold": 1000.0,
            "crossed": True,
            "timestamp": checkout_onset["ts"],
            "anomaly_class": "symptom",
        },
        {
            "ci": CI_CHECKOUT,
            "signal": "checkout_success_rate",
            "value": round(float(slo_min["value"]), 3),
            "threshold": 99.5,
            "crossed": True,
            "timestamp": symptom_ts,
            "anomaly_class": "symptom",
        },
        {
            "ci": CI_GATEWAY,
            "signal": "api_gateway_error_rate_pct",
            "value": round(float((gateway_peak or {"value": 0})["value"]), 2),
            "threshold": 20.0,
            "crossed": True,
            "timestamp": (gateway_onset or slo_onset)["ts"]
            if gateway_onset or slo_onset
            else symptom_ts,
            "anomaly_class": "symptom",
            "note": "api-gateway → checkout path error escalation",
        },
        {
            "ci": CI_CHECKOUT,
            "signal": "checkout_error_rate_pct",
            "value": round(float((checkout_err_peak or {"value": 0})["value"]), 2),
            "threshold": 5.0,
            "crossed": True,
            "timestamp": symptom_ts,
            "anomaly_class": "symptom",
            "note": "checkout-service error rate (blast / escalation mid-tier)",
        },
        {
            "ci": CI_PAYMENT,
            "signal": "payment_service_error_rate_pct",
            "value": round(float((payment_err_peak or {"value": 0})["value"]), 2),
            "threshold": 5.0,
            "crossed": False,
            "timestamp": symptom_ts,
            "anomaly_class": "app",
            "note": "payment-service HTTP error rate stays low; blast is latency/pool",
        },
    ]

    if not gateway_peak or not checkout_err_peak:
        raise SystemExit(
            "Missing gateway/checkout error-rate metrics — regenerate raw export "
            "or inject checkout_error_rate_pct / api_gateway_error_rate_pct"
        )

    topology = {
        "version": "1.0.0",
        "source": "ecom_checkout_scenario",
        "nodes": [
            {"id": CI_GATEWAY, "type": "Service", "name": "API Gateway"},
            {"id": CI_CHECKOUT, "type": "Service", "name": "Checkout Service"},
            {"id": CI_PAYMENT, "type": "Service", "name": "Payment Service"},
            {"id": CI_PROVIDER, "type": "Service", "name": "External Payment Provider"},
            {"id": CI_DNS, "type": "Service", "name": "DNS AAAA (NP-17)"},
            {"id": CI_RX, "type": "NetworkPort", "name": "NIC RX Queue 7 (NP-17)"},
            {"id": CI_IRQ, "type": "Host", "name": "NP-17 IRQ affinity / node image"},
        ],
        "edges": [
            # effect → cause (Lean/Fed walk upstream toward root)
            {"from": CI_GATEWAY, "to": CI_CHECKOUT, "relation": "depends_on"},
            {"from": CI_CHECKOUT, "to": CI_PAYMENT, "relation": "depends_on"},
            # false-lead branch (provider looks slow; later onset than IRQ root)
            {"from": CI_PAYMENT, "to": CI_PROVIDER, "relation": "depends_on"},
            {"from": CI_PAYMENT, "to": CI_DNS, "relation": "depends_on"},
            {"from": CI_DNS, "to": CI_RX, "relation": "depends_on"},
            {"from": CI_RX, "to": CI_IRQ, "relation": "depends_on"},
        ],
    }

    # Change / smoking-gun + app WARN events from raw logs
    events = []
    _STREAM_CI = {
        "infra_change_logs": CI_IRQ,
        "kernel_logs": CI_RX,
        "payment_service_logs": CI_PAYMENT,
        "checkout_service_logs": CI_CHECKOUT,
        "alert_logs": CI_CHECKOUT,
    }
    for row in logs:
        stream = row.get("stream") or ""
        logger = row.get("logger") or ""
        include = (
            stream in _STREAM_CI
            or logger == "dns.resolver"
            or logger == "alert.fire"
        )
        if not include:
            continue
        level = (row.get("level") or "INFO").upper()
        severity = {
            "ERROR": "critical",
            "WARN": "warning",
            "WARNING": "warning",
            "INFO": "info",
        }.get(level, "info")
        if stream in _STREAM_CI:
            ci = _STREAM_CI[stream]
        elif logger == "dns.resolver":
            ci = CI_DNS
        else:
            ci = CI_CHECKOUT
        events.append(
            {
                "timestamp": row["ts"],
                "ci": ci,
                "event_type": logger or stream or "log",
                "severity": severity,
                "message": row.get("message") or "",
            }
        )

    # Ensure alert.fire exists even if raw dump lacked alert_logs (derive from window end)
    if not any(e.get("event_type") == "alert.fire" for e in events):
        # Place alert near end of window: symptom + ~27 min (gold: change 08:25 → alert 09:00)
        alert_ts = symptom_ts
        try:
            from datetime import timedelta

            alert_dt = _parse_ts(incident_start) + timedelta(seconds=35 * 60 + 10)
            # gold: change 08:25:48 → alert 09:00:58 = 35m10s
            alert_ts = _iso(alert_dt)
        except Exception:
            pass
        events.append(
            {
                "timestamp": alert_ts,
                "ci": CI_CHECKOUT,
                "event_type": "alert.fire",
                "severity": "critical",
                "message": (
                    f"Alert {GOLD_ALERT_NAME} fired: checkout success rate < 99.5"
                ),
            }
        )

    alert_events = [e for e in events if e.get("event_type") == "alert.fire"]
    alert_ts = alert_events[0]["timestamp"] if alert_events else symptom_ts

    # Production-grade guard: payment/checkout WARN must land in pack events.
    app_warn = sum(
        1
        for e in events
        if e.get("ci") in {CI_PAYMENT, CI_CHECKOUT} and e.get("severity") == "warning"
    )
    if app_warn < 1:
        raise SystemExit(
            "ecom pack missing payment/checkout WARN events — check raw "
            "payment_service_logs / checkout_service_logs inclusion"
        )

    symptom_seed = {
        "ci": CI_CHECKOUT,
        "signal": "checkout_success_rate",
        "timestamp": symptom_ts,
        "anomaly_class": "symptom",
    }

    impact = _derive_impact(
        metrics,
        gateway_peak=gateway_peak,
        checkout_err_peak=checkout_err_peak,
        payment_err_peak=payment_err_peak,
        slo_min=slo_min,
    )
    if impact.get("failed_requests") is None or impact.get("total_requests") is None:
        raise SystemExit(
            "Missing checkout_requests_total / checkout_failures_total in raw metrics — "
            "cannot derive impact (refuse authored stamp)"
        )

    ground_truth = {
        "root_ci": CI_IRQ,
        "signature": "cross_numa_irq_affinity",
        "contributor_cis": [CI_RX, CI_DNS],
        "blast_radius": [
            CI_GATEWAY,
            CI_CHECKOUT,
            CI_PAYMENT,
            "payment-pod-118",
            "payment-pod-124",
            "payment-pod-131",
            "payment-pod-144",
        ],
        "note": (
            "Root cause: node-image 2026.06.18 on NP-17 pinned RX-7 IRQ to CPU48 "
            "(NUMA1) while queue memory is on NUMA0 → AAAA DNS stall → payment pool "
            "exhaustion → checkout SLO → api-gateway errors. "
            "payment-provider latency is a false lead."
        ),
        "tags": ["ecom", "multi-signal", "cross-numa", "false-leads"],
        "gt_status": "scenario_authored",
        "fault_bucket": "2_infra",
        "fault_type": "misconfiguration",
        "fault_title": "NP-17 cross-NUMA IRQ affinity (node image 2026.06.18)",
        "false_leads": [
            CI_PROVIDER,
            "node_nic_mtu (NP-17 jumbo frames — in raw metrics, not pack anomalies)",
        ],
        "amplifier": "CARD+INR+cart>12 payment-risk feature (extra AAAA DNS lookups)",
        "impact": impact,
        "source_incident_id": GOLD_SOURCE_INCIDENT_ID,
    }

    # Span summary for incident_meta (not required by engines)
    slow_spans = [
        s
        for s in spans
        if float(s.get("duration_ms") or 0) > 5000
        and s.get("service_name") in {CI_CHECKOUT, CI_PAYMENT, CI_PROVIDER}
    ]
    incident_meta = {
        "pack_id": PACK_ID,
        "scenario": "ecom_checkout_cross_numa_irq",
        "source_incident_id": GOLD_SOURCE_INCIDENT_ID,
        "source_raw": str(raw_dir),
        "postgres_manifest": manifest,
        "row_counts": {
            "metrics": len(metrics),
            "logs": len(logs),
            "spans": len(spans),
            "slow_spans": len(slow_spans),
            "events": len(events),
        },
        "incident_start": incident_start,
        "symptom_onset": symptom_ts,
        "detected_at": alert_ts,
        "canonical_clock": {
            **CANONICAL_CLOCK,
            # Keep dump-relative detect for remap; display uses change_at offset
        },
        "alerts": [
            {
                "name": GOLD_ALERT_NAME,
                "timestamp": alert_ts,
                "ci": CI_CHECKOUT,
                "severity": "P3",
            }
        ],
        "impact": impact,
        "built_at": _iso(datetime.now(timezone.utc)),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "topology.json").write_text(json.dumps(topology, indent=2) + "\n")
    (out_dir / "anomalies.json").write_text(
        json.dumps({"incident_start": incident_start, "anomalies": anomalies}, indent=2)
        + "\n"
    )
    (out_dir / "symptom_seed.json").write_text(json.dumps(symptom_seed, indent=2) + "\n")
    (out_dir / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2) + "\n")
    (out_dir / "events.json").write_text(
        json.dumps({"events": events}, indent=2) + "\n"
    )
    (out_dir / "incident_meta.json").write_text(json.dumps(incident_meta, indent=2) + "\n")

    return {
        "pack_id": PACK_ID,
        "out_dir": str(out_dir),
        "root_ci": CI_IRQ,
        "anomaly_count": len(anomalies),
        "event_count": len(events),
        "incident_start": incident_start,
        "symptom_onset": symptom_ts,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--raw",
        type=Path,
        default=Path("datasets/ecom_checkout/raw"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("datasets/ecom_checkout/incidents") / PACK_ID,
    )
    args = p.parse_args(argv)
    summary = build_pack(args.raw, args.out)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
