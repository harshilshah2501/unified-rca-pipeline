"""Wave-1 edge triplet allowlist — Motadata storage types × ingest relation.

Normative prose: ``contracts/EDGE_TRIPLET_ALLOWLIST.md``.
Illegal or unresolvable pairs → DROP (not warn-and-write).
"""

from __future__ import annotations

from ab_shared import reject_codes as rc
from graph.ci_qualify import to_storage_type
from graph.edge_catalog import normalize_relation

# Motadata storage types that may appear as communicates_with peers.
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

_RUNS_ON_SRC = frozenset(
    {"process", "service", "pod", "container", "db", "queue"}
)
_RUNS_ON_DST = frozenset({"host", "node"})

_HOSTED_ON_SRC = _RUNS_ON_SRC | frozenset({"host"})
_HOSTED_ON_DST = frozenset({"host"})

_DEPENDS_ON: frozenset[tuple[str, str]] = frozenset(
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

_COMMUNICATES_WITH: frozenset[tuple[str, str]] = frozenset(
    (a, b) for a in _NETWORKABLE for b in _NETWORKABLE
)


def _pairs_for(relation: str) -> frozenset[tuple[str, str]] | None:
    """Return allowed (src, dst) storage pairs, or None if relation has no wave-1 matrix."""
    rel = normalize_relation(relation)
    if rel == "runs_on":
        return frozenset((s, d) for s in _RUNS_ON_SRC for d in _RUNS_ON_DST)
    if rel == "hosted_on":
        return frozenset((s, d) for s in _HOSTED_ON_SRC for d in _HOSTED_ON_DST)
    if rel == "depends_on":
        return _DEPENDS_ON
    if rel == "part_of":
        return _PART_OF
    if rel == "communicates_with":
        return _COMMUNICATES_WITH
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
        # Not a wave-1 matrix relation — caller should have classified emit/skip/reject first.
        return "reject", rc.ILLEGAL_EDGE_TRIPLET
    if (src_storage_type, dst_storage_type) not in pairs:
        return "reject", rc.ILLEGAL_EDGE_TRIPLET
    return "ok", None
