"""Infer fault signature from crossed signals (no ground-truth leak)."""

from __future__ import annotations


def _crossed(anomalies: list[dict]) -> list[dict]:
    return [anomaly for anomaly in anomalies if anomaly.get("crossed")]


def _has_signal(anomalies: list[dict], signal: str, *, ci_prefix: str | None = None) -> bool:
    return any(
        anomaly.get("signal") == signal
        and (ci_prefix is None or anomaly.get("ci", "").startswith(ci_prefix))
        for anomaly in anomalies
    )


def _app_symptom(anomalies: list[dict]) -> bool:
    """An app-down/error or latency anomaly, not just an app resource metric."""
    return any(
        anomaly.get("ci", "").startswith("orders-")
        and anomaly.get("signal")
        in {"request.p95_latency_ms", "error_rate_5xx", "health_check", "tcp.timeouts"}
        for anomaly in anomalies
    )


def _app_down_or_error(anomalies: list[dict]) -> bool:
    return any(
        anomaly.get("ci", "").startswith("orders-")
        and anomaly.get("signal") in {"error_rate_5xx", "health_check", "tcp.timeouts"}
        for anomaly in anomalies
    )


def _match_cpu_contention(crossed: list[dict]) -> bool:
    anomalies = _crossed(crossed)
    ready_vms = {
        anomaly.get("ci")
        for anomaly in anomalies
        if anomaly.get("ci", "").startswith("vm-") and anomaly.get("signal") == "cpu.ready"
    }
    return (
        _has_signal(anomalies, "cpu.usage", ci_prefix="esxi-")
        and _has_signal(anomalies, "cpu.ready", ci_prefix="esxi-")
        and len(ready_vms) >= 2
    )


def _match_link_failure(crossed: list[dict]) -> bool:
    anomalies = _crossed(crossed)
    if _has_signal(anomalies, "linkDown", ci_prefix="switch-"):
        return True

    utilization_signals = {
        "utilization_pct",
        "interface.utilization_pct",
        "ifUtilizationPct",
    }
    saturated_ports = {
        anomaly.get("ci")
        for anomaly in anomalies
        if anomaly.get("ci", "").startswith("switch-")
        and anomaly.get("signal") in utilization_signals
        and isinstance(anomaly.get("value"), (int, float))
        and anomaly["value"] > 90
    }
    discard_ports = {
        anomaly.get("ci")
        for anomaly in anomalies
        if anomaly.get("ci", "").startswith("switch-")
        and anomaly.get("signal") in {"ifInDiscards", "ifOutDiscards"}
    }
    return bool(saturated_ports & discard_ports)


def _match_storage_contention(crossed: list[dict]) -> bool:
    anomalies = _crossed(crossed)
    if not _has_signal(anomalies, "gavg_latency_ms", ci_prefix="datastore-"):
        return False

    vm_disk_latency = {
        anomaly.get("ci")
        for anomaly in anomalies
        if anomaly.get("ci", "").startswith("vm-")
        and anomaly.get("signal") == "virtualDisk.totalLatency_ms"
    }
    if len(vm_disk_latency) >= 2:
        return True

    noisy_neighbor_iops = {
        anomaly.get("ci")
        for anomaly in anomalies
        if anomaly.get("ci", "").startswith("vm-")
        and anomaly.get("signal") == "virtualDisk.iops"
    }
    return bool(vm_disk_latency and noisy_neighbor_iops - vm_disk_latency)


def _match_os_exhaustion(crossed: list[dict]) -> bool:
    anomalies = _crossed(crossed)
    return _app_down_or_error(anomalies) and any(
        anomaly.get("ci", "").startswith("guest-os-")
        and (
            anomaly.get("signal") == "oom_killer_event"
            or (
                anomaly.get("signal") == "filesystem.used_pct"
                and isinstance(anomaly.get("value"), (int, float))
                and anomaly["value"] > 95
            )
        )
        for anomaly in anomalies
    )


def _match_app_exhaustion(crossed: list[dict]) -> bool:
    anomalies = _crossed(crossed)
    app_signals = {"jvm.heap.used_pct", "db.conn_pool.active_ratio"}
    resource_cis = {
        anomaly.get("ci")
        for anomaly in anomalies
        if anomaly.get("ci", "").startswith("orders-") and anomaly.get("signal") in app_signals
    }
    symptom_cis = {
        anomaly.get("ci")
        for anomaly in anomalies
        if anomaly.get("ci", "").startswith("orders-")
        and anomaly.get("signal")
        in {"request.p95_latency_ms", "error_rate_5xx", "health_check", "tcp.timeouts"}
    }
    return bool(resource_cis & symptom_cis)


# --- Motadata / vendor metric vocabulary (I1) ---

_MOTADATA_HTTP_ERROR = {
    "http.error_rate",
    "http.error_rate_4xx",
    "http.error_rate_5xx",
}
_MOTADATA_PING = {
    "ping.latency.ms",
    "ping.max.latency.ms",
    "ping.packet.lost.percent",
    "ping.lost.packets",
}
_MOTADATA_HOST_CPU = {
    "system.cpu.percent",
    "system.1min.avg.cpu.percent",
    "system.5min.avg.cpu.percent",
}


def _match_app_error_rate(crossed: list[dict]) -> bool:
    """Motadata APM: elevated HTTP error rate on a service/app CI."""
    anomalies = _crossed(crossed)
    return any(anomaly.get("signal") in _MOTADATA_HTTP_ERROR for anomaly in anomalies)


def _match_ping_degradation(crossed: list[dict]) -> bool:
    """Motadata infra: ping latency or packet loss above threshold."""
    anomalies = _crossed(crossed)
    return any(anomaly.get("signal") in _MOTADATA_PING for anomaly in anomalies)


def _match_host_cpu_saturation(crossed: list[dict]) -> bool:
    """Motadata infra: host CPU percent saturation (not VMware cpu.ready contention)."""
    anomalies = _crossed(crossed)
    return any(anomaly.get("signal") in _MOTADATA_HOST_CPU for anomaly in anomalies)


# --- E-commerce cross-NUMA IRQ scenario (datasets/scenario.md) ---

_CROSS_NUMA_IRQ = {
    "irq_affinity_numa_mismatch",
    "kernel_rx_queue_latency_ms",
}


def _match_cross_numa_irq_affinity(crossed: list[dict]) -> bool:
    """Node-image IRQ affinity pinned across NUMA → RX/DNS stall chain."""
    anomalies = _crossed(crossed)
    return any(anomaly.get("signal") in _CROSS_NUMA_IRQ for anomaly in anomalies)


_SIGNATURE_CHECKS = [
    ("app_resource_exhaustion", _match_app_exhaustion),
    ("os_resource_exhaustion", _match_os_exhaustion),
    ("cpu_contention", _match_cpu_contention),
    ("storage_contention", _match_storage_contention),
    ("link_failure", _match_link_failure),
    # E-com multi-signal (before Motadata HTTP/ping — distinct signal names)
    ("cross_numa_irq_affinity", _match_cross_numa_irq_affinity),
    # Motadata broaden (after classic ObserveOps rules — different signal names)
    ("app_error_rate", _match_app_error_rate),
    # Prefer host CPU over ping when both appear on a multi-signal host window
    # (ping-only packs never include CPU metrics, so order is safe for L1 smokes).
    ("host_cpu_saturation", _match_host_cpu_saturation),
    ("ping_degradation", _match_ping_degradation),
]


def infer_signature(crossed: list[dict]) -> str:
    for name, check in _SIGNATURE_CHECKS:
        if check(crossed):
            return name
    return "unknown"
