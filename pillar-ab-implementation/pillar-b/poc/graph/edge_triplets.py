"""Edge triplet allowlist — Motadata storage types × all fifteen relations.

Normative prose: ``contracts/EDGE_TRIPLET_ALLOWLIST.md``.
Illegal or unresolvable pairs → DROP (not warn-and-write).
"""

from __future__ import annotations

from ab_shared import reject_codes as rc
from graph.ci_qualify import to_storage_type
from graph.edge_catalog import normalize_relation

_NETWORKABLE = frozenset(
    {
        "service",
        "host",
        "pod",
        "container",
        "db",
        "queue",
        "endpoint",
        "network",
        "node",
        "process",
    }
)
_ALL_CI = _NETWORKABLE | frozenset(
    {"business_service", "k8s_deployment", "namespace", "volume", "customer"}
)

_RUNS_ON_SRC = frozenset(
    {"process", "service", "pod", "container", "db", "queue"}
)
_RUNS_ON_DST = frozenset({"host", "node"})
_HOSTED_ON_SRC = _RUNS_ON_SRC | frozenset({"host"})
_HOSTED_ON_DST = frozenset({"host"})

_DEPENDS_OR_USES: frozenset[tuple[str, str]] = frozenset(
    {
        *(("service", t) for t in ("service", "db", "queue", "endpoint", "business_service")),
        *(("business_service", t) for t in ("service", "db", "queue")),
        *(("pod", t) for t in ("service", "db", "queue", "endpoint")),
        *(("k8s_deployment", t) for t in ("service", "db", "queue", "endpoint")),
        *(("customer", t) for t in ("business_service", "service")),
    }
)

_PART_OF: frozenset[tuple[str, str]] = frozenset(
    {
        ("service", "business_service"),
        *(
            (child, parent)
            for child in ("process", "container", "volume")
            for parent in ("host", "pod", "service", "db")
        ),
        ("endpoint", "service"),
        ("endpoint", "host"),
        ("pod", "k8s_deployment"),
        ("pod", "namespace"),
    }
)

_COMMUNICATES_WITH = frozenset((a, b) for a in _NETWORKABLE for b in _NETWORKABLE)

_CONNECTS_TO_TYPES = frozenset({"host", "node", "network", "endpoint", "service"})
_CONNECTS_TO = frozenset((a, b) for a in _CONNECTS_TO_TYPES for b in _CONNECTS_TO_TYPES)

_MEMBER_SRC = frozenset({"host", "node", "pod", "service", "db", "queue", "network"})
_MEMBER_DST = frozenset({"namespace", "service", "business_service", "k8s_deployment"})
_MEMBER_OF = frozenset((s, d) for s in _MEMBER_SRC for d in _MEMBER_DST)

_MOUNTS = frozenset(
    (s, "volume") for s in ("host", "pod", "container", "service", "process")
)

_BACK_TYPES = frozenset({"db", "volume", "host", "service"})
_BACKS = frozenset((a, b) for a in _BACK_TYPES for b in _BACK_TYPES)
_BACKED_UP_BY = frozenset(
    (s, d) for s in _BACK_TYPES for d in ("service", "host", "db", "volume")
)

_ROUTES_THROUGH = frozenset(
    (s, d)
    for s in ("service", "host", "pod", "endpoint")
    for d in ("network", "service", "host", "endpoint")
)

_AUTHENTICATES_VIA = frozenset(
    (s, d)
    for s in ("service", "host", "pod", "customer")
    for d in ("service", "endpoint")
)

_MONITORED_BY = frozenset((s, "service") for s in _ALL_CI)

_CLUSTERED_WITH = frozenset(
    (t, t) for t in ("host", "node", "service", "db", "pod", "queue")
)


def _pairs_for(relation: str) -> frozenset[tuple[str, str]] | None:
    """Return allowed (src, dst) storage pairs for a Motadata catalog relation."""
    rel = normalize_relation(relation)
    if rel == "runs_on":
        return frozenset((s, d) for s in _RUNS_ON_SRC for d in _RUNS_ON_DST)
    if rel == "hosted_on":
        return frozenset((s, d) for s in _HOSTED_ON_SRC for d in _HOSTED_ON_DST)
    if rel in ("depends_on", "uses"):
        return _DEPENDS_OR_USES
    if rel == "part_of":
        return _PART_OF
    if rel == "communicates_with":
        return _COMMUNICATES_WITH
    if rel == "connects_to":
        return _CONNECTS_TO
    if rel == "member_of":
        return _MEMBER_OF
    if rel == "mounts":
        return _MOUNTS
    if rel == "backs":
        return _BACKS
    if rel == "backed_up_by":
        return _BACKED_UP_BY
    if rel == "routes_through":
        return _ROUTES_THROUGH
    if rel == "authenticates_via":
        return _AUTHENTICATES_VIA
    if rel == "monitored_by":
        return _MONITORED_BY
    if rel == "clustered_with":
        return _CLUSTERED_WITH
    return None


def storage_type_or_none(ci_type: str | None) -> str | None:
    """Map ingest or storage type to Motadata storage; None if missing/unqualified."""
    key = (ci_type or "").strip()
    if not key:
        return None
    try:
        return to_storage_type(key)
    except ValueError:
        return None


def check_edge_triplet(
    relation: str,
    src_storage_type: str | None,
    dst_storage_type: str | None,
) -> tuple[str, str | None]:
    """Return (action, reason).

    action is ``ok`` or ``reject``. reason is a reject_codes constant when reject.
    """
    if not src_storage_type or not dst_storage_type:
        return "reject", rc.MISSING_ENDPOINT_TYPE
    pairs = _pairs_for(relation)
    if pairs is None:
        return "reject", rc.ILLEGAL_EDGE_TRIPLET
    if (src_storage_type, dst_storage_type) not in pairs:
        return "reject", rc.ILLEGAL_EDGE_TRIPLET
    return "ok", None
