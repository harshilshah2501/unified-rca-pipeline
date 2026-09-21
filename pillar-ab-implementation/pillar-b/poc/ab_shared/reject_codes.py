"""Stable DROP reason strings shared by gate / catalog / qualify.

Do not invent ad-hoc reject text in builder code — assert and log these codes.
Source of truth narrative: ``IDENTIFIED_STREAM_REJECT.md`` in slice contracts.
"""

IDENTITY_UNRESOLVED = "identity_unresolved"
IDENTITY_SYNTHESIZED = "identity_synthesized"
NEVER_CI_VERTEX = "never_ci_vertex"
UNKNOWN_RELATION = "unknown_relation"
UNKNOWN_METRIC_ID = "unknown_metric_id"

REJECT_CODES = (
    IDENTITY_UNRESOLVED,
    IDENTITY_SYNTHESIZED,
    NEVER_CI_VERTEX,
    UNKNOWN_RELATION,
    UNKNOWN_METRIC_ID,
)
