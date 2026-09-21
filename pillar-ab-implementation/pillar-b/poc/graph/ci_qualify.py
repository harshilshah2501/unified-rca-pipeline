"""CI type eligibility for vertices on Dest ``map/``.

``may_emit_vertex`` is the gate GraphWriter uses before creating a node.
Never-CI types (Alert, Change, Incident, …) always DROP. Wave-1 / clearly
qualifying types WRITE. Temporary / paused types are withheld from emit in
this PoC (returned as not allowed with ``never_ci_vertex``-style reasons).

This does not judge instance health — only whether the *class* may sit on the map.
"""

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
    """Coarse catalog bucket for teaching / tests; prefer ``may_emit_vertex`` at emit time."""
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
    """Return ``(True, None)`` if this CI type may be a map vertex, else ``(False, reason_code)``."""
    cat = qualify(ci_type)
    if cat == Category.NEVER:
        return False, rc.NEVER_CI_VERTEX
    if cat == Category.PAUSE and ci_type not in {"Database"}:
        return False, rc.NEVER_CI_VERTEX
    return True, None
