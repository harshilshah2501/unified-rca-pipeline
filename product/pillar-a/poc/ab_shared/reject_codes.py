"""Reject reason codes used by Pillar A admit (identity + metric)."""

IDENTITY_UNRESOLVED = "identity_unresolved"
IDENTITY_SYNTHESIZED = "identity_synthesized"
UNKNOWN_METRIC_ID = "unknown_metric_id"

# Graph-only codes kept listed for IDENTIFIED_STREAM_REJECT.md parity in docs;
# Pillar A admit does not emit them.
NEVER_CI_VERTEX = "never_ci_vertex"
UNKNOWN_RELATION = "unknown_relation"
MISSING_ENDPOINT_TYPE = "missing_endpoint_type"
ILLEGAL_EDGE_TRIPLET = "illegal_edge_triplet"

REJECT_CODES = (
    IDENTITY_UNRESOLVED,
    IDENTITY_SYNTHESIZED,
    UNKNOWN_METRIC_ID,
)

REJECT_CODES_FULL_CATALOG = (
    IDENTITY_UNRESOLVED,
    IDENTITY_SYNTHESIZED,
    NEVER_CI_VERTEX,
    UNKNOWN_RELATION,
    UNKNOWN_METRIC_ID,
    MISSING_ENDPOINT_TYPE,
    ILLEGAL_EDGE_TRIPLET,
)
