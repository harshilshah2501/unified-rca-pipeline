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
    """Return (action, reason). action in emit | skip | reject.

    Hub admit language (GraphWriter walkthrough):
      emit  → WRITE (upsert edge when catalog checks already passed)
      skip  → phased map-NOOP (in fifteen-name catalog, not wave-1 yet)
      reject → DROP (unknown_relation)
    Wrong signal_class is handled earlier as silent NOOP (continue), not here.
    """
    if relation not in ALL_RELATIONS:
        return "reject", rc.UNKNOWN_RELATION
    if relation not in WAVE1_RELATIONS:
        return "skip", None
    return "emit", None
