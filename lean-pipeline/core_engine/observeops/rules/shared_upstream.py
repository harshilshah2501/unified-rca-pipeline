"""Shared-upstream rule — if ≥2 VMs show same signal, blame shared host/datastore."""

from __future__ import annotations

from core_engine.observeops.ingest.bundle import crossed_anomalies
from core_engine.observeops.registry import rule


def apply(bundle: dict, candidates: list[str]) -> str | None:
    """
    UC-1: cpu.ready on ≥2 VMs -> esxi-host-01
    UC-3: storage latency on multiple VMs -> datastore-01
    """
    crossed = crossed_anomalies(bundle)
    cfg = rule("shared_upstream")

    cpu = cfg["cpu_contention"]
    vm_ready = [
        a["ci"]
        for a in crossed
        if a["ci"].startswith(cpu["ci_prefix"]) and a["signal"] == cpu["signal"]
    ]
    if len(vm_ready) >= cpu["min_crossed"]:
        for c in candidates:
            if c.startswith(cpu["target_prefix"]):
                return c

    storage = cfg["storage_contention"]
    storage_signals = set(storage["signals"])
    vm_storage = [a["ci"] for a in crossed if a["signal"] in storage_signals]
    if len(vm_storage) >= storage["min_crossed"]:
        for c in candidates:
            if c.startswith(storage["target_prefix"]):
                return c
    return None
