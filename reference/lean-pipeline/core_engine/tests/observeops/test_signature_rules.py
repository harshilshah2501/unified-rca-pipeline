"""Focused signature-inference tests for the frozen ObserveOps corpus."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "lean-pipeline"))

from core_engine.lean.signature import infer_signature  # noqa: E402
from core_engine.observeops.ingest.bundle import crossed_anomalies, load_bundle  # noqa: E402

CORPUS = REPO / "datasets" / "observeops"


@pytest.mark.parametrize(
    ("uc_id", "expected_signature"),
    [
        ("UC-1", "cpu_contention"),
        ("UC-2", "link_failure"),
        ("UC-3", "storage_contention"),
        ("UC-4", "os_resource_exhaustion"),
        ("UC-5", "app_resource_exhaustion"),
    ],
)
def test_frozen_bundle_infers_expected_signature(uc_id: str, expected_signature: str) -> None:
    crossed = crossed_anomalies(load_bundle(uc_id, CORPUS))

    assert infer_signature(crossed) == expected_signature


def test_cpu_contention_needs_host_usage_and_two_vm_ready_anomalies() -> None:
    crossed = [
        {"ci": "vm-app-01", "signal": "cpu.ready", "crossed": True},
        {"ci": "esxi-host-01", "signal": "cpu.ready", "crossed": True},
    ]

    assert infer_signature(crossed) != "cpu_contention"


def test_storage_contention_needs_datastore_and_correlated_vm_evidence() -> None:
    crossed = [
        {
            "ci": "datastore-01",
            "signal": "gavg_latency_ms",
            "crossed": True,
        },
        {
            "ci": "vm-neighbor-01",
            "signal": "virtualDisk.iops",
            "crossed": True,
        },
    ]

    assert infer_signature(crossed) != "storage_contention"


def test_os_exhaustion_needs_app_failure_and_critical_filesystem_usage() -> None:
    crossed = [
        {
            "ci": "guest-os-vm-app-01",
            "signal": "filesystem.used_pct",
            "value": 91,
            "crossed": True,
        },
        {
            "ci": "orders-api",
            "signal": "request.p95_latency_ms",
            "crossed": True,
        },
    ]

    assert infer_signature(crossed) != "os_resource_exhaustion"


def test_link_saturation_needs_discards_on_the_same_port() -> None:
    crossed = [
        {
            "ci": "switch-core-01:GigE0/2",
            "signal": "utilization_pct",
            "value": 95,
            "crossed": True,
        },
        {
            "ci": "switch-core-01:GigE0/3",
            "signal": "ifOutDiscards",
            "crossed": True,
        },
    ]

    assert infer_signature(crossed) != "link_failure"


def test_motadata_app_error_rate() -> None:
    crossed = [
        {
            "ci": "ProductCatalog_dotnet.",
            "signal": "http.error_rate",
            "value": 0.2,
            "crossed": True,
        }
    ]
    assert infer_signature(crossed) == "app_error_rate"


def test_motadata_ping_degradation() -> None:
    crossed = [
        {
            "ci": "dlink-48",
            "signal": "ping.latency.ms",
            "value": 400,
            "crossed": True,
        }
    ]
    assert infer_signature(crossed) == "ping_degradation"


def test_motadata_host_cpu_saturation() -> None:
    crossed = [
        {
            "ci": "Fluentbit",
            "signal": "system.cpu.percent",
            "value": 98,
            "crossed": True,
        }
    ]
    assert infer_signature(crossed) == "host_cpu_saturation"


def test_motadata_multi_signal_prefers_host_cpu_over_ping() -> None:
    """Same-host CPU+ping window: resource signature wins (multi pack)."""
    crossed = [
        {
            "ci": "HB1-host",
            "signal": "system.cpu.percent",
            "value": 94,
            "crossed": True,
        },
        {
            "ci": "HB1-host",
            "signal": "ping.packet.lost.percent",
            "value": 33,
            "crossed": True,
        },
    ]
    assert infer_signature(crossed) == "host_cpu_saturation"


def test_motadata_cpu_does_not_steal_observeops_cpu_contention() -> None:
    """VMware contention still wins when classic signals are present."""
    crossed = [
        {"ci": "esxi-host-01", "signal": "cpu.usage", "crossed": True},
        {"ci": "esxi-host-01", "signal": "cpu.ready", "crossed": True},
        {"ci": "vm-a", "signal": "cpu.ready", "crossed": True},
        {"ci": "vm-b", "signal": "cpu.ready", "crossed": True},
        {"ci": "Fluentbit", "signal": "system.cpu.percent", "crossed": True},
    ]
    assert infer_signature(crossed) == "cpu_contention"
