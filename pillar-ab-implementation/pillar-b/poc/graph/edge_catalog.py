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

WAVE1_RELATIONS = frozenset(
    {"runs_on", "hosted_on", "depends_on", "communicates_with", "part_of"}
)


def classify_relation(relation: str) -> tuple[str, str | None]:
    """Return (action, reason). action in emit | skip | reject."""
    if relation not in ALL_RELATIONS:
        return "reject", rc.UNKNOWN_RELATION
    if relation not in WAVE1_RELATIONS:
        return "skip", None
    return "emit", None
