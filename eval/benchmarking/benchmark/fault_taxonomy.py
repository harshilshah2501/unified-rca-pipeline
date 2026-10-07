#!/usr/bin/env python3
"""Fault-bucket taxonomy for corpus packs (aligned with docs/FAULT_BUCKET_COVERAGE.md).

Buckets:
  1 symptom      — what you notice first (availability, error rate, slowdown)
  2 infra         — shared resource / network / storage layer
  3 application  — dependency / topology / execution-path class
  4 external     — change-induced / security (outside organic ops)

Apply tags into ground_truth.json via ``python3 -m …`` or ``tag_corpus_fault_buckets.py``.
"""

from __future__ import annotations

from typing import Any

# Display labels for dashboard / docs (human-facing; ids stay 1_symptom …)
BUCKET_LABELS = {
    "1_symptom": "Symptom-layer",
    "2_infra": "Infrastructure",
    "3_application": "Application",
    "4_external": "External / change",
}

BUCKET_BLURBS = {
    "1_symptom": "What users notice first (errors, slowdown) — root may still be elsewhere",
    "2_infra": "Shared host, network, storage, or OS layer",
    "3_application": "App / service dependency or resource issue",
    "4_external": "Change, deploy, or outside organic ops",
}

# signature → (fault_bucket, fault_type, short title)
SIGNATURE_TAXONOMY: dict[str, tuple[str, str, str]] = {
    "cpu_contention": ("2_infra", "resource_contention", "Host CPU contention"),
    "link_failure": ("2_infra", "network_fault", "Link / interface failure"),
    "storage_contention": ("2_infra", "storage_noisy_neighbor", "Storage / datastore contention"),
    "os_resource_exhaustion": ("2_infra", "resource_contention", "Guest OS resource exhaustion"),
    "app_resource_exhaustion": ("3_application", "dependency_downstream", "App resource exhaustion"),
    "app_error_rate": ("1_symptom", "error_rate", "HTTP error-rate spike"),
    "ping_degradation": ("2_infra", "network_fault", "Ping latency / loss"),
    "host_cpu_saturation": ("2_infra", "resource_contention", "Host CPU saturation"),
}

# Explicit pack overrides when signature alone is ambiguous
PACK_TAXONOMY: dict[str, tuple[str, str, str]] = {
    "UC-1": ("2_infra", "resource_contention", "CPU contention on ESXi host"),
    "UC-2": ("2_infra", "network_fault", "Core switch link failure"),
    "UC-3": ("2_infra", "storage_noisy_neighbor", "Datastore storage contention"),
    "UC-3b": ("2_infra", "storage_noisy_neighbor", "Datastore storage contention (variant)"),
    "UC-4": ("2_infra", "resource_contention", "Guest OS resource exhaustion"),
    "UC-5": ("3_application", "dependency_downstream", "Orders-api resource exhaustion"),
    "motadata-apm-001": ("1_symptom", "error_rate", "ProductCatalog HTTP error rate"),
    "motadata-ping-001": ("2_infra", "network_fault", "dlink-48 ping degradation"),
    "motadata-ping-002": ("2_infra", "network_fault", "Netgear Switch ping / packet loss"),
    "motadata-ping-003": ("2_infra", "network_fault", "proxmox-ve-129 ping / packet loss"),
    "motadata-ping-004": (
        "2_infra",
        "network_fault",
        "localhost.localdomain packet loss burst",
    ),
    "motadata-cpu-001": ("2_infra", "resource_contention", "Fluentbit host CPU saturation"),
    "motadata-multi-001": (
        "2_infra",
        "resource_contention",
        "HB1 host multi-signal (CPU+mem+ping)",
    ),
    "motadata-deps-001": (
        "3_application",
        "dependency_downstream",
        "ProductCatalog app error-rate with hibernate dependency graph",
    ),
}


def resolve_taxonomy(
    pack_id: str,
    *,
    signature: str | None = None,
) -> dict[str, str]:
    if pack_id in PACK_TAXONOMY:
        bucket, ftype, title = PACK_TAXONOMY[pack_id]
    elif signature and signature in SIGNATURE_TAXONOMY:
        bucket, ftype, title = SIGNATURE_TAXONOMY[signature]
    else:
        bucket, ftype, title = ("2_infra", "unknown", pack_id)
    return {
        "fault_bucket": bucket,
        "fault_type": ftype,
        "fault_title": title,
        "fault_bucket_label": BUCKET_LABELS.get(bucket, bucket),
        "fault_bucket_blurb": BUCKET_BLURBS.get(bucket, ""),
    }


def apply_to_ground_truth(gt: dict[str, Any], pack_id: str) -> dict[str, Any]:
    """Return a copy of gt with taxonomy fields merged (non-destructive extras)."""
    out = dict(gt)
    tax = resolve_taxonomy(pack_id, signature=out.get("signature"))
    out["fault_bucket"] = tax["fault_bucket"]
    out["fault_type"] = tax["fault_type"]
    out["fault_title"] = tax["fault_title"]
    return out
