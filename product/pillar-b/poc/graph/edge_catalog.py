"""Relation-name catalog for edges on Dest ``map/``.

Ingest still uses snake_case ``relation`` (fifteen-name catalog).
Stored ``graph_edge.v1`` uses Motadata SCREAMING_SNAKE ``edge_type``.

``classify_relation`` decides emit / reject for an ingest ``relation``:

* **emit** — in the fifteen-name catalog → proceed to triplet allowlist
* **reject** — unknown relation → DROP (``unknown_relation``)

Pairing legality for every catalog name: ``edge_triplets`` /
``contracts/EDGE_TRIPLET_ALLOWLIST.md`` (no wave-wise emit split).
"""

from __future__ import annotations

from ab_shared import reject_codes as rc

ALL_RELATIONS = frozenset(
    {
        "depends_on",
        "runs_on",
        "mounts",
        "connects_to",
        "backs",
        "uses",
        "hosted_on",
        "member_of",
        "part_of",
        "routes_through",
        "authenticates_via",
        "monitored_by",
        "backed_up_by",
        "clustered_with",
        "communicates_with",
    }
)

# Kept as an alias for older tests/docs that imported WAVE1_RELATIONS.
WAVE1_RELATIONS = ALL_RELATIONS

_INGEST_TO_EDGE_TYPE = {r: r.upper() for r in ALL_RELATIONS}
_EDGE_TYPE_TO_INGEST = {v: k for k, v in _INGEST_TO_EDGE_TYPE.items()}

# Fusion / writer_stream.v1 camelCase → Motadata ingest snake (RELATION_MAPPING.md §3).
_FUSION_TO_INGEST = {
    "dependsOn": "depends_on",
    "runsOn": "runs_on",
    "communicatesWith": "communicates_with",
    "memberOf": "member_of",
    "composedOf": "part_of",  # Dest arrow may flip at publish; PoC stores Motadata part_of
}

ALL_EDGE_TYPES = frozenset(_INGEST_TO_EDGE_TYPE.values())


def to_edge_type(relation: str) -> str:
    """Map ingest ``relation`` (snake_case), Fusion camelCase, or Motadata name to storage ``edge_type``."""
    key = normalize_relation(relation or "")
    if key in _INGEST_TO_EDGE_TYPE:
        return _INGEST_TO_EDGE_TYPE[key]
    upper = (relation or "").strip().upper()
    if upper in _EDGE_TYPE_TO_INGEST:
        return upper
    raise ValueError(f"unknown relation {relation!r}")


def from_edge_type(edge_type: str) -> str:
    """Map Motadata ``edge_type`` back to ingest snake_case."""
    key = (edge_type or "").strip()
    if key in _EDGE_TYPE_TO_INGEST:
        return _EDGE_TYPE_TO_INGEST[key]
    lower = key.lower()
    if lower in _INGEST_TO_EDGE_TYPE:
        return lower
    raise ValueError(f"unknown edge_type {edge_type!r}")


def normalize_relation(name: str) -> str:
    """Return ingest snake_case for classify / filters (Fusion camelCase accepted)."""
    key = (name or "").strip()
    if key in ALL_RELATIONS:
        return key
    if key in _FUSION_TO_INGEST:
        return _FUSION_TO_INGEST[key]
    upper = key.upper()
    if upper in _EDGE_TYPE_TO_INGEST:
        return _EDGE_TYPE_TO_INGEST[upper]
    return key


def classify_relation(relation: str) -> tuple[str, str | None]:
    """Return (action, reason). action in emit | reject."""
    ingest = normalize_relation(relation)
    if ingest not in ALL_RELATIONS:
        return "reject", rc.UNKNOWN_RELATION
    return "emit", None
