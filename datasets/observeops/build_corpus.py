#!/usr/bin/env python3
"""Generate frozen ObserveOps corpus bundles UC-1..UC-5 + UC-3b from shared topology."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARED_TOPOLOGY = ROOT / "shared_topology.json"
CORPUS_VERSION = "1.1.0"
INTERVAL_MINUTES = 30
LOOKBACK_DAYS = 7

# ISO timestamps — fixed for reproducibility (same bundle every run)
T_EARLY = "2026-07-10T09:59:58Z"  # UC-3b confound (unrelated network noise)
T0 = "2026-07-10T10:00:00Z"
T1 = "2026-07-10T10:00:05Z"
T2 = "2026-07-10T10:00:12Z"
T3 = "2026-07-10T10:00:18Z"
T4 = "2026-07-10T10:00:25Z"


def _event(
    ci: str,
    event_type: str,
    message: str,
    ts: str,
    severity: str = "critical",
) -> dict:
    return {
        "timestamp": ts,
        "ci": ci,
        "event_type": event_type,
        "severity": severity,
        "message": message,
    }


def _parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _anomaly(ci: str, signal: str, value: float, threshold: float, ts: str, crossed: bool = True) -> dict:
    return {
        "ci": ci,
        "signal": signal,
        "value": value,
        "threshold": threshold,
        "crossed": crossed,
        "timestamp": ts,
    }


def _metric_filename(ci: str, signal: str) -> str:
    return f"{ci.replace(':', '_').replace('/', '_')}__{signal}.json"


def _build_metric_series(anomaly: dict, incident_start: str) -> dict:
    """7-day baseline at 30min interval plus incident spike (matches federated adapter)."""
    incident = _parse_ts(incident_start)
    interval = timedelta(minutes=INTERVAL_MINUTES)
    baseline_start = incident - timedelta(days=LOOKBACK_DAYS)
    baseline_val = anomaly["threshold"] * 0.4 if anomaly["crossed"] else anomaly["value"]
    points: list[dict] = []
    t = baseline_start
    while t < incident:
        points.append({"timestamp": _fmt_ts(t), "value": baseline_val})
        t += interval
    points.append({"timestamp": anomaly["timestamp"], "value": anomaly["value"]})
    return {
        "ci": anomaly["ci"],
        "signal": anomaly["signal"],
        "threshold": anomaly["threshold"],
        "interval_minutes": INTERVAL_MINUTES,
        "lookback_days": LOOKBACK_DAYS,
        "points": points,
    }


def _topology_sha256() -> str:
    return hashlib.sha256(SHARED_TOPOLOGY.read_bytes()).hexdigest()


UC_SPECS = {
    "UC-1": {
        "ground_truth": {
            "root_ci": "esxi-host-01",
            "signature": "cpu_contention",
            "contributor_cis": [],
            "blast_radius": ["vm-app-01", "vm-db-01", "guest-os-vm-app-01", "orders-api"],
        },
        "symptom_seed": {"ci": "orders-api", "signal": "request.p95_latency_ms", "timestamp": T4},
        "injection": {
            "fault": "ESXi CPU contention via stress-ng in co-located VMs",
            "inject_on": "esxi-host-01",
            "method": "stress-ng --cpu across vm-app-01, vm-db-01",
        },
        "anomalies": [
            _anomaly("esxi-host-01", "cpu.usage", 92.0, 85.0, T1),
            _anomaly("esxi-host-01", "cpu.ready", 12.0, 5.0, T1),
            _anomaly("vm-app-01", "cpu.ready", 11.0, 5.0, T2),
            _anomaly("vm-db-01", "cpu.ready", 10.0, 5.0, T2),
            _anomaly("guest-os-vm-app-01", "load.avg", 8.0, 4.0, T3),
            _anomaly("orders-api", "request.p95_latency_ms", 1450.0, 1000.0, T4),
        ],
    },
    "UC-2": {
        "ground_truth": {
            "root_ci": "switch-core-01:GigE0/2",
            "signature": "link_failure",
            "contributor_cis": [],
            "blast_radius": ["esxi-host-01", "vm-app-01", "vm-db-01", "orders-api"],
        },
        "symptom_seed": {"ci": "orders-api", "signal": "tcp.timeouts", "timestamp": T3},
        "injection": {
            "fault": "Switch uplink admin-down or saturation",
            "inject_on": "switch-core-01:GigE0/2",
            "method": "ifOperStatus=down or iperf flood",
        },
        "anomalies": [
            _anomaly("switch-core-01:GigE0/2", "linkDown", 1.0, 0.5, T0),
            _anomaly("switch-core-01:GigE0/2", "ifOutDiscards", 450.0, 0.0, T1),
            _anomaly("esxi-host-01", "vmnic.dropped_packets", 120.0, 0.0, T2),
            _anomaly("vm-app-01", "tcp.retransmits", 85.0, 10.0, T2),
            _anomaly("orders-api", "tcp.timeouts", 42.0, 5.0, T3),
        ],
        "events": [
            _event(
                "switch-core-01:GigE0/2",
                "snmp.linkDown",
                "SNMP TRAP linkDown: ifDescr=GigE0/2 ifOperStatus=down",
                T0,
            ),
            _event(
                "switch-core-01:GigE0/2",
                "snmp.ifOutDiscards",
                "ifOutDiscards rising on GigE0/2",
                T1,
                severity="warning",
            ),
        ],
    },
    "UC-3": {
        "ground_truth": {
            "root_ci": "datastore-01",
            "signature": "storage_contention",
            "contributor_cis": ["vm-neighbor-01"],
            "blast_radius": ["vm-db-01", "guest-os-vm-db-01", "orders-api"],
        },
        "symptom_seed": {"ci": "orders-api", "signal": "request.p95_latency_ms", "timestamp": T4},
        "injection": {
            "fault": "Noisy neighbor fio on shared datastore",
            "inject_on": "vm-neighbor-01",
            "method": "fio random read/write on datastore-01",
        },
        "anomalies": [
            _anomaly("datastore-01", "gavg_latency_ms", 45.0, 30.0, T1),
            _anomaly("datastore-01", "davg_latency_ms", 28.0, 20.0, T1),
            _anomaly("vm-neighbor-01", "virtualDisk.iops", 12000.0, 5000.0, T1),
            _anomaly("vm-db-01", "virtualDisk.totalLatency_ms", 38.0, 30.0, T2),
            _anomaly("guest-os-vm-db-01", "disk.iowait_pct", 72.0, 50.0, T3),
            _anomaly("orders-api", "request.p95_latency_ms", 2100.0, 1000.0, T4),
        ],
    },
    "UC-3b": {
        "ground_truth": {
            "root_ci": "datastore-01",
            "signature": "storage_contention",
            "contributor_cis": ["vm-neighbor-01"],
            "blast_radius": ["vm-db-01", "guest-os-vm-db-01", "orders-api"],
        },
        "symptom_seed": {"ci": "orders-api", "signal": "request.p95_latency_ms", "timestamp": T4},
        "injection": {
            "fault": "Noisy neighbor fio + early unrelated switch utilization noise",
            "inject_on": "vm-neighbor-01",
            "method": "fio on datastore-01; concurrent non-causal switch utilization blip",
        },
        "anomalies": [
            # Unrelated network noise first — must NOT become root
            _anomaly(
                "switch-core-01:GigE0/2",
                "utilization_pct",
                92.0,
                90.0,
                T_EARLY,
            ),
            _anomaly("datastore-01", "gavg_latency_ms", 45.0, 30.0, T1),
            _anomaly("datastore-01", "davg_latency_ms", 28.0, 20.0, T1),
            _anomaly("vm-neighbor-01", "virtualDisk.iops", 12000.0, 5000.0, T1),
            _anomaly("vm-db-01", "virtualDisk.totalLatency_ms", 38.0, 30.0, T2),
            _anomaly("guest-os-vm-db-01", "disk.iowait_pct", 72.0, 50.0, T3),
            _anomaly("orders-api", "request.p95_latency_ms", 2100.0, 1000.0, T4),
        ],
        "events": [
            _event(
                "switch-core-01:GigE0/2",
                "snmp.utilization",
                "ifUtilizationPct=92 on GigE0/2 (concurrent noise; not causal for storage)",
                T_EARLY,
                severity="warning",
            ),
        ],
    },
    "UC-4": {
        "ground_truth": {
            "root_ci": "guest-os-vm-app-01",
            "signature": "os_resource_exhaustion",
            "contributor_cis": [],
            "blast_radius": ["orders-api"],
        },
        "symptom_seed": {"ci": "orders-api", "signal": "error_rate_5xx", "timestamp": T3},
        "injection": {
            "fault": "Filesystem full on guest OS",
            "inject_on": "guest-os-vm-app-01",
            "method": "fallocate until fs 100%",
        },
        "anomalies": [
            _anomaly("guest-os-vm-app-01", "filesystem.used_pct", 99.0, 95.0, T1),
            _anomaly("guest-os-vm-app-01", "oom_killer_event", 1.0, 0.5, T2),
            _anomaly("orders-api", "error_rate_5xx", 0.42, 0.05, T3),
            _anomaly("orders-api", "health_check", 0.0, 1.0, T3),
            # upstream healthy — no crossings
            _anomaly("esxi-host-01", "cpu.usage", 45.0, 85.0, T2, crossed=False),
            _anomaly("switch-core-01:GigE0/2", "linkDown", 0.0, 0.5, T2, crossed=False),
        ],
        "events": [
            _event(
                "guest-os-vm-app-01",
                "syslog.filesystem_full",
                "No space left on device writing /var/log/orders-api",
                T1,
            ),
            _event(
                "guest-os-vm-app-01",
                "syslog.oom_killer",
                "kernel: Out of memory: Killed process 1842 (orders-api)",
                T2,
            ),
        ],
    },
    "UC-5": {
        "ground_truth": {
            "root_ci": "orders-api",
            "signature": "app_resource_exhaustion",
            "contributor_cis": [],
            "blast_radius": ["orders-api"],
            "upstream_healthy": True,
        },
        "symptom_seed": {"ci": "orders-api", "signal": "request.p95_latency_ms", "timestamp": T2},
        "injection": {
            "fault": "JVM heap exhaustion / connection pool saturation",
            "inject_on": "orders-api",
            "method": "hold all DB connections + heap fill",
        },
        "anomalies": [
            _anomaly("orders-api", "jvm.heap.used_pct", 96.0, 90.0, T1),
            _anomaly("orders-api", "db.conn_pool.active_ratio", 1.0, 0.95, T1),
            _anomaly("orders-api", "request.p95_latency_ms", 1800.0, 1000.0, T2),
            _anomaly("orders-api", "error_rate_5xx", 0.18, 0.05, T2),
            # all upstream healthy
            _anomaly("guest-os-vm-app-01", "filesystem.used_pct", 55.0, 95.0, T1, crossed=False),
            _anomaly("esxi-host-01", "cpu.usage", 38.0, 85.0, T1, crossed=False),
            _anomaly("esxi-host-01", "cpu.ready", 1.2, 5.0, T1, crossed=False),
            _anomaly("datastore-01", "gavg_latency_ms", 8.0, 30.0, T1, crossed=False),
            _anomaly("switch-core-01:GigE0/2", "linkDown", 0.0, 0.5, T1, crossed=False),
        ],
    },
}


def build_uc(uc_id: str, spec: dict) -> None:
    uc_dir = ROOT / uc_id
    uc_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(SHARED_TOPOLOGY, uc_dir / "topology.json")
    (uc_dir / "ground_truth.json").write_text(json.dumps(spec["ground_truth"], indent=2) + "\n")
    (uc_dir / "symptom_seed.json").write_text(json.dumps(spec["symptom_seed"], indent=2) + "\n")
    anomalies = {"incident_start": T0, "anomalies": spec["anomalies"]}
    (uc_dir / "anomalies.json").write_text(json.dumps(anomalies, indent=2) + "\n")
    events = spec.get("events") or []
    (uc_dir / "events.json").write_text(json.dumps({"events": events}, indent=2) + "\n")
    manifest_lines = [
        f"uc_id: {uc_id}",
        f"fault: {spec['injection']['fault']}",
        f"inject_on: {spec['injection']['inject_on']}",
        f"method: {spec['injection']['method']}",
        f"corpus_version: {CORPUS_VERSION}",
        f"source: rca-use-cases-only.md",
    ]
    (uc_dir / "injection_manifest.yaml").write_text("\n".join(manifest_lines) + "\n")
    metrics_dir = uc_dir / "metrics"
    if metrics_dir.exists():
        shutil.rmtree(metrics_dir)
    metrics_dir.mkdir(exist_ok=True)
    for a in spec["anomalies"]:
        series = _build_metric_series(a, T0)
        key = _metric_filename(a["ci"], a["signal"])
        (metrics_dir / key).write_text(json.dumps(series, indent=2) + "\n")


def main() -> None:
    if not SHARED_TOPOLOGY.exists():
        raise SystemExit(f"Missing {SHARED_TOPOLOGY}")
    topo_hash = _topology_sha256()
    for uc_id, spec in UC_SPECS.items():
        build_uc(uc_id, spec)
        print(f"built {uc_id}")
    manifest = {
        "corpus_version": CORPUS_VERSION,
        "source": "rca-use-cases-only.md",
        "use_cases": list(UC_SPECS.keys()),
        "shared_topology": "shared_topology.json",
        "topology_sha256": topo_hash,
        "benchmark_contract": "COMPARISON_BENCHMARK.md",
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    yaml_lines = [
        f"corpus_version: {CORPUS_VERSION}",
        "source: rca-use-cases-only.md",
        "use_cases:",
        *[f"  - {uc_id}" for uc_id in UC_SPECS],
        "shared_topology: shared_topology.json",
        f"topology_sha256: {topo_hash}",
        "benchmark_contract: COMPARISON_BENCHMARK.md",
    ]
    (ROOT / "manifest.yaml").write_text("\n".join(yaml_lines) + "\n")
    print("done")


if __name__ == "__main__":
    main()
