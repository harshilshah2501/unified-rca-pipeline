from __future__ import annotations

from enum import Enum

from ab_shared import reject_codes as rc

NEVER_CI = frozenset(
    {"Change", "Alert", "Incident", "ITSMTicket", "Metric", "LogPattern", "Trace"}
)

WAVE1_TYPES = frozenset(
    {"Service", "Host", "Runtime", "Database", "BusinessService", "Customer", "Queue"}
)


class Category(str, Enum):
    CLEARLY = "clearly_qualifies"
    TEMPORARY = "qualifies_temporarily"
    PAUSE = "not_decided"
    NEVER = "does_not_qualify"


def qualify(ci_type: str) -> Category:
    if ci_type in NEVER_CI:
        return Category.NEVER
    if ci_type in {"Pod", "Container", "Process", "Endpoint"}:
        return Category.TEMPORARY
    if ci_type in {"Deployment", "Network"}:
        return Category.PAUSE
    if ci_type == "Database":
        return Category.CLEARLY  # named instance/cluster only at emit time
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


def may_emit_vertex(ci_type: str) -> tuple[bool, str | None]:
    cat = qualify(ci_type)
    if cat == Category.NEVER:
        return False, rc.NEVER_CI_VERTEX
    if cat == Category.PAUSE and ci_type not in {"Database"}:
        return False, rc.NEVER_CI_VERTEX
    return True, None
