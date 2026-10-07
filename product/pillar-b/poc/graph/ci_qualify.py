"""CI vs observation / signal qualification for map vertices (Motadata CI-only).

``may_emit_vertex`` gates WRITE vs DROP for nodes on Dest ``map/``.

Ingest still uses PascalCase ``ci_type`` (``Service``, ``Host``, …).
Stored ``graph_node.v1.type`` uses Motadata lowercase (``service``, ``host``, …).

Non-CI Motadata names (alert, incident, metric, …) are rejected — they never
become map vertices.
"""

from __future__ import annotations

from enum import Enum

from ab_shared import reject_codes as rc

# Ingest PascalCase → Motadata storage type
_INGEST_TO_STORAGE: dict[str, str] = {
    "Service": "service",
    "Host": "host",
    "Pod": "pod",
    "Container": "container",
    "Process": "process",
    "Runtime": "process",
    "Endpoint": "endpoint",
    "Deployment": "k8s_deployment",
    "K8sDeployment": "k8s_deployment",
    "Database": "db",
    "Datastore": "db",
    "Db": "db",
    "Queue": "queue",
    "Network": "network",
    "Customer": "customer",
    "BusinessService": "business_service",
    "Namespace": "namespace",
    "Node": "node",
    "Volume": "volume",
    "GuestOS": "host",
    "VirtualMachine": "host",
    "HypervisorHost": "host",
    "NetworkPort": "network",
    "Middleware": "service",
    "Monitor": "service",
}

ALLOWED_STORAGE_TYPES = frozenset(_INGEST_TO_STORAGE.values()) | frozenset(
    {
        "service",
        "host",
        "pod",
        "container",
        "process",
        "endpoint",
        "k8s_deployment",
        "db",
        "queue",
        "network",
        "customer",
        "business_service",
        "namespace",
        "node",
        "volume",
    }
)

FORBIDDEN_STORAGE_TYPES = frozenset(
    {
        "alert",
        "incident",
        "itsm_ticket",
        "red_metric",
        "log_pattern",
        "trace",
        "change",
        "metric",
        "anomaly",
        "event",
        "ticket",
    }
)

_FORBIDDEN_INGEST = frozenset(
    {
        "Alert",
        "Incident",
        "Change",
        "ITSMTicket",
        "ItsmTicket",
        "Metric",
        "LogPattern",
        "Trace",
        "Anomaly",
        "Event",
        "Ticket",
        "RedMetric",
    }
)

# Legacy qualify() buckets (ingest PascalCase) — still used by unit tests
NEVER_CI = frozenset(_FORBIDDEN_INGEST)
WAVE1_TYPES = frozenset(
    {"Service", "Host", "Runtime", "Database", "BusinessService", "Customer", "Queue"}
)


class Category(str, Enum):
    CLEARLY = "clearly_qualifies"
    TEMPORARY = "qualifies_temporarily"
    PAUSE = "not_decided"
    NEVER = "does_not_qualify"


def qualify(ci_type: str) -> Category:
    if ci_type in NEVER_CI or (ci_type or "").lower() in FORBIDDEN_STORAGE_TYPES:
        return Category.NEVER
    if ci_type in {"Pod", "Container", "Process", "Endpoint"}:
        return Category.TEMPORARY
    if ci_type in {"Deployment", "Network"}:
        return Category.PAUSE
    if ci_type == "Database":
        return Category.CLEARLY
    if ci_type in WAVE1_TYPES or ci_type in {
        "Datastore",
        "GuestOS",
        "VirtualMachine",
        "HypervisorHost",
        "NetworkPort",
        "Middleware",
        "Monitor",
    }:
        return Category.CLEARLY
    return Category.PAUSE


def to_storage_type(ci_type: str) -> str:
    """Map ingest ``ci_type`` to Motadata ``graph_node.v1.type``."""
    key = (ci_type or "").strip()
    if key in _INGEST_TO_STORAGE:
        return _INGEST_TO_STORAGE[key]
    lower = key.lower()
    if lower in ALLOWED_STORAGE_TYPES:
        return lower
    raise ValueError(f"unqualified or forbidden ci_type {ci_type!r}")


# Motadata storage → product/case-path display name (LeafClaim, VerdictCard)
_STORAGE_TO_PRODUCT: dict[str, str] = {
    "service": "Service",
    "host": "Host",
    "pod": "Pod",
    "container": "Container",
    "process": "Runtime",
    "endpoint": "Endpoint",
    "k8s_deployment": "Deployment",
    "db": "Database",
    "queue": "Queue",
    "network": "Network",
    "customer": "Customer",
    "business_service": "BusinessService",
    "namespace": "Namespace",
    "node": "Node",
    "volume": "Volume",
}


def storage_type_matches(stored: str, filter_name: str) -> bool:
    """True when a stored Motadata type matches a filter (PascalCase or Motadata)."""
    try:
        want = to_storage_type(filter_name)
    except ValueError:
        want = (filter_name or "").lower()
    return (stored or "").lower() == want


def to_product_type(stored_or_ingest: str) -> str:
    """Map Motadata storage or ingest type to case-path PascalCase display name."""
    key = (stored_or_ingest or "").strip()
    if key in _STORAGE_TO_PRODUCT:
        return _STORAGE_TO_PRODUCT[key]
    lower = key.lower()
    if lower in _STORAGE_TO_PRODUCT:
        return _STORAGE_TO_PRODUCT[lower]
    try:
        return _STORAGE_TO_PRODUCT[to_storage_type(key)]
    except (ValueError, KeyError):
        return key


def may_emit_vertex(ci_type: str) -> tuple[bool, str | None]:
    """Return (ok, reason). reason is a reject_codes constant when not ok."""
    key = (ci_type or "").strip()
    if not key:
        return False, rc.NEVER_CI_VERTEX
    if key in _FORBIDDEN_INGEST or key.lower() in FORBIDDEN_STORAGE_TYPES:
        return False, rc.NEVER_CI_VERTEX
    cat = qualify(key)
    if cat == Category.NEVER:
        return False, rc.NEVER_CI_VERTEX
    if cat == Category.PAUSE and key not in {"Database", "Network"}:
        # Network is PAUSE in legacy qualify but Motadata allows network storage —
        # only emit when we have an explicit storage mapping.
        if key not in _INGEST_TO_STORAGE:
            return False, rc.NEVER_CI_VERTEX
    try:
        to_storage_type(key)
        return True, None
    except ValueError:
        return False, rc.NEVER_CI_VERTEX
