#!/usr/bin/env python3
"""Synthesize GT-aligned multimodal evidence for ObserveOps UC-1..UC-5.

Writes (without changing ground_truth / topology / anomalies):
  datasets/observeops/UC-N/events.json          — enriched structured events
  datasets/observeops/UC-N/raw/logs.json        — synthetic log rows
  datasets/observeops/UC-N/raw/spans.json       — synthetic app→infra spans
  datasets/observeops/UC-N/raw/manifest.json    — provenance

Events reinforce the authored root; spans show app latency as symptom (not
a competing root). Does not invent a new causal story.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "observeops"

# Shared ISO window used by frozen UC anomalies
T0 = "2026-07-10T10:00:00Z"
T05 = "2026-07-10T10:00:05Z"
T08 = "2026-07-10T10:00:08Z"
T12 = "2026-07-10T10:00:12Z"
T18 = "2026-07-10T10:00:18Z"
T25 = "2026-07-10T10:00:25Z"


def _ev(ts: str, ci: str, et: str, sev: str, msg: str) -> dict:
    return {
        "timestamp": ts,
        "ci": ci,
        "event_type": et,
        "severity": sev,
        "message": msg,
    }


def _log(stream: str, ts: str, level: str, logger: str, msg: str, **extra) -> dict:
    row = {
        "stream": stream,
        "ts": ts,
        "level": level,
        "logger": logger,
        "message": msg,
        "labels": extra,
    }
    return row


def _span(
    tid: str,
    sid: str,
    parent: str | None,
    service: str,
    name: str,
    start: str,
    dur_ms: float,
    **attrs,
) -> dict:
    return {
        "trace_id": tid,
        "span_id": sid,
        "parent_span_id": parent,
        "service_name": service,
        "span_name": name,
        "kind": "SERVER" if parent is None else "CLIENT",
        "start_time": start,
        "duration_ms": dur_ms,
        "attributes": attrs,
    }


def uc1() -> tuple[list[dict], list[dict], list[dict]]:
    events = [
        _ev("2026-07-10T09:55:00Z", "esxi-host-01", "infra.change", "info",
            "DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01"),
        _ev(T05, "esxi-host-01", "esx.cpu.ready", "critical",
            "ESXi cpu.ready elevated on esxi-host-01 (12% > 5% threshold)"),
        _ev(T05, "esxi-host-01", "esx.cpu.usage", "warning",
            "ESXi cpu.usage 92% sustained on esxi-host-01"),
        _ev(T12, "vm-app-01", "vmware.cpu.ready", "warning",
            "VM cpu.ready 11% on vm-app-01 (host scheduler starvation)"),
        _ev(T18, "guest-os-vm-app-01", "syslog.loadavg", "warning",
            "load average 8.0 on guest-os-vm-app-01 (run-queue backlog)"),
        _ev(T25, "orders-api", "app.latency", "critical",
            "orders-api p95 latency 1450ms (SLO threshold 1000ms)"),
    ]
    logs = [
        _log("esx_logs", T05, "ERROR", "esx.cpu.ready",
             "cpu.ready=12% on esxi-host-01 — vCPUs waiting for physical cores",
             ci="esxi-host-01"),
        _log("esx_logs", T05, "WARN", "esx.cpu.usage",
             "cpu.usage=92% on esxi-host-01", ci="esxi-host-01"),
        _log("vmware_logs", T12, "WARN", "vmware.cpu.ready",
             "vm-app-01 cpu.ready=11% (co-located with other VMs on esxi-host-01)",
             ci="vm-app-01", host="esxi-host-01"),
        _log("syslog", T18, "WARN", "syslog.loadavg",
             "loadavg=8.0 on guest-os-vm-app-01", ci="guest-os-vm-app-01"),
        _log("app_logs", T25, "ERROR", "app.latency",
             "request p95=1450ms endpoint=/orders", ci="orders-api"),
    ]
    spans = [
        _span("uc1-t1", "s1", None, "orders-api", "POST /orders", T25, 1480.0,
              ci="orders-api", layer="app"),
        _span("uc1-t1", "s2", "s1", "guest-os-vm-app-01", "os.sched.wait", T25, 900.0,
              ci="guest-os-vm-app-01", layer="os"),
        _span("uc1-t1", "s3", "s2", "esxi-host-01", "hypervisor.cpu.ready", T25, 700.0,
              ci="esxi-host-01", layer="hypervisor", note="root_evidence"),
        _span("uc1-t2", "s4", None, "orders-api", "GET /orders/{id}", T25, 1320.0,
              ci="orders-api", layer="app"),
    ]
    return events, logs, spans


def uc2() -> tuple[list[dict], list[dict], list[dict]]:
    # Keep required SNMP events; add downstream symptom evidence
    events = [
        _ev("2026-07-10T09:58:00Z", "switch-core-01:GigE0/2", "infra.change", "info",
            "Network change window: uplink maintenance on switch-core-01 GigE0/2"),
        _ev(T0, "switch-core-01:GigE0/2", "snmp.linkDown", "critical",
            "SNMP TRAP linkDown: ifDescr=GigE0/2 ifOperStatus=down"),
        _ev(T05, "switch-core-01:GigE0/2", "snmp.ifOutDiscards", "warning",
            "ifOutDiscards rising on GigE0/2"),
        _ev(T08, "esxi-host-01", "esx.net.drop", "warning",
            "vmnic packet drops / link-down detected on esxi-host-01 uplink"),
        _ev(T12, "orders-api", "app.timeout", "critical",
            "orders-api TCP timeouts / elevated error rate behind failed uplink"),
    ]
    logs = [
        _log("snmp_traps", T0, "CRITICAL", "snmp.linkDown",
             "SNMP TRAP linkDown: ifDescr=GigE0/2 ifOperStatus=down",
             ci="switch-core-01:GigE0/2"),
        _log("snmp_traps", T05, "WARN", "snmp.ifOutDiscards",
             "ifOutDiscards rising on GigE0/2", ci="switch-core-01:GigE0/2"),
        _log("esx_logs", T08, "WARN", "esx.net.drop",
             "Uplink redundancy lost — host path via GigE0/2 down",
             ci="esxi-host-01"),
        _log("app_logs", T12, "ERROR", "app.timeout",
             "downstream call timeout after uplink failure", ci="orders-api"),
    ]
    spans = [
        _span("uc2-t1", "s1", None, "orders-api", "POST /checkout", T12, 5200.0,
              ci="orders-api", error=True),
        _span("uc2-t1", "s2", "s1", "orders-api", "tcp.connect", T12, 4800.0,
              ci="orders-api", note="network_path_failure"),
        _span("uc2-t2", "s3", None, "orders-api", "GET /health", T12, 3100.0,
              ci="orders-api", error=True),
    ]
    return events, logs, spans


def uc3() -> tuple[list[dict], list[dict], list[dict]]:
    events = [
        _ev("2026-07-10T09:57:00Z", "vm-neighbor-01", "infra.change", "info",
            "Batch / fio workload started on vm-neighbor-01 (shared datastore-01)"),
        _ev(T05, "datastore-01", "storage.latency", "critical",
            "datastore-01 GAVG latency > 30ms (shared storage contention)"),
        _ev(T08, "vm-neighbor-01", "storage.iops", "warning",
            "vm-neighbor-01 heavy random I/O on datastore-01 (noisy neighbor)"),
        _ev(T12, "vm-db-01", "vmware.disk.latency", "critical",
            "vm-db-01 virtualDisk.totalLatency elevated (victim VM)"),
        _ev(T18, "orders-api", "app.db_slow", "critical",
            "orders-api slow DB queries / timeouts (storage-backed)"),
    ]
    logs = [
        _log("storage_logs", T05, "ERROR", "storage.latency",
             "datastore-01 GAVG=45ms DAVG=38ms", ci="datastore-01"),
        _log("vmware_logs", T08, "WARN", "storage.iops",
             "vm-neighbor-01 saturating datastore-01 with fio-like workload",
             ci="vm-neighbor-01"),
        _log("vmware_logs", T12, "ERROR", "vmware.disk.latency",
             "vm-db-01 disk latency spike — victim of shared datastore",
             ci="vm-db-01"),
        _log("app_logs", T18, "ERROR", "app.db_slow",
             "SQL query timeout waiting on datastore-backed volume", ci="orders-api"),
    ]
    spans = [
        _span("uc3-t1", "s1", None, "orders-api", "POST /orders", T18, 4200.0,
              ci="orders-api"),
        _span("uc3-t1", "s2", "s1", "vm-db-01", "db.query", T18, 3900.0,
              ci="vm-db-01", layer="db"),
        _span("uc3-t1", "s3", "s2", "datastore-01", "storage.io.wait", T18, 3500.0,
              ci="datastore-01", layer="storage", note="root_evidence"),
    ]
    return events, logs, spans


def uc4() -> tuple[list[dict], list[dict], list[dict]]:
    events = [
        _ev("2026-07-10T09:56:00Z", "guest-os-vm-app-01", "infra.change", "info",
            "Log retention / disk fill activity on guest-os-vm-app-01 filesystem"),
        _ev(T05, "guest-os-vm-app-01", "syslog.filesystem_full", "critical",
            "No space left on device writing /var/log/orders-api"),
        _ev(T12, "guest-os-vm-app-01", "syslog.oom_killer", "critical",
            "kernel: Out of memory: Killed process 1842 (orders-api)"),
        _ev(T18, "orders-api", "app.crash", "critical",
            "orders-api service down after OOM / filesystem-full on guest OS"),
    ]
    logs = [
        _log("syslog", T05, "CRITICAL", "syslog.filesystem_full",
             "No space left on device writing /var/log/orders-api",
             ci="guest-os-vm-app-01"),
        _log("syslog", T12, "CRITICAL", "syslog.oom_killer",
             "kernel: Out of memory: Killed process 1842 (orders-api)",
             ci="guest-os-vm-app-01"),
        _log("app_logs", T18, "ERROR", "app.crash",
             "process exited; health checks failing", ci="orders-api"),
    ]
    spans = [
        _span("uc4-t1", "s1", None, "orders-api", "POST /orders", T18, 50.0,
              ci="orders-api", error=True, status="unavailable"),
        _span("uc4-t2", "s2", None, "orders-api", "GET /health", T18, 30.0,
              ci="orders-api", error=True, status="unavailable"),
    ]
    return events, logs, spans


def uc5() -> tuple[list[dict], list[dict], list[dict]]:
    events = [
        _ev("2026-07-10T09:59:00Z", "orders-api", "config.change", "info",
            "App deploy / pool-size config change on orders-api (infra below unchanged)"),
        _ev(T05, "orders-api", "app.thread_pool", "critical",
            "orders-api thread pool exhausted (app-tier fault; infra healthy)"),
        _ev(T08, "orders-api", "app.heap", "warning",
            "JVM heap pressure / GC thrash on orders-api"),
        _ev(T12, "orders-api", "app.error_rate", "critical",
            "orders-api error rate elevated — root is application resource exhaustion"),
    ]
    logs = [
        _log("app_logs", T05, "ERROR", "app.thread_pool",
             "RejectedExecutionException: thread pool saturated", ci="orders-api"),
        _log("app_logs", T08, "WARN", "app.heap",
             "GC overhead limit approaching; heap nearly full", ci="orders-api"),
        _log("app_logs", T12, "ERROR", "app.error_rate",
             "5xx rate spike — no infra anomaly on host/guest/network",
             ci="orders-api"),
        _log("esx_logs", T05, "INFO", "esx.health",
             "esxi-host-01 cpu/mem within baseline (upstream_healthy=true)",
             ci="esxi-host-01"),
    ]
    spans = [
        _span("uc5-t1", "s1", None, "orders-api", "POST /orders", T12, 2800.0,
              ci="orders-api", error=True, note="app_pool_exhaustion"),
        _span("uc5-t1", "s2", "s1", "orders-api", "internal.worker", T12, 2500.0,
              ci="orders-api", queue_wait_ms=2200),
        _span("uc5-t2", "s3", None, "orders-api", "GET /orders", T12, 2100.0,
              ci="orders-api", error=True),
    ]
    return events, logs, spans


GENERATORS = {
    "UC-1": uc1,
    "UC-2": uc2,
    "UC-3": uc3,
    "UC-4": uc4,
    "UC-5": uc5,
}


def _write_uc(uc_id: str) -> dict:
    pack = CORPUS / uc_id
    if not pack.is_dir():
        raise SystemExit(f"missing pack {pack}")
    events, logs, spans = GENERATORS[uc_id]()
    (pack / "events.json").write_text(
        json.dumps({"events": events}, indent=2) + "\n"
    )
    raw = pack / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "logs.json").write_text(json.dumps(logs, indent=2) + "\n")
    (raw / "spans.json").write_text(json.dumps(spans, indent=2) + "\n")
    man = {
        "source": "synthesize_observeops_uc_multimodal.py",
        "uc_id": uc_id,
        "note": (
            "Synthetic multimodal evidence aligned to pack GT; "
            "does not replace anomalies/topology/ground_truth."
        ),
        "counts": {"events": len(events), "logs": len(logs), "spans": len(spans)},
    }
    (raw / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    return {"uc_id": uc_id, **man["counts"]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--uc",
        action="append",
        choices=sorted(GENERATORS),
        help="UC id (repeatable). Default: all UC-1..UC-5",
    )
    args = p.parse_args(argv)
    ids = args.uc or list(GENERATORS)
    summary = [_write_uc(uc) for uc in ids]
    print(json.dumps({"wrote": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
