"""E11 Package — EvidenceBundle → VerdictCard (operator-facing close).

D4: required verdict card; narrative optional. Verify locks confidence on the card.
Does not create ServiceOps tickets in this PoC (handoff fields only).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from graph.case_path.identify import EvidenceBundle


@dataclass(frozen=True)
class VerdictCard:
    """E11 output: operator verdict — not a CMDB write, not an open ticket unless attached."""

    case_id: str
    tenant: str
    root_ci_id: str
    root_ci_type: str
    detect_class: str
    summary: str
    path_from_seed: tuple[str, ...]
    blast_radius: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    confidence_tier: int
    confidence_label: str
    evidence_counts: dict[str, int]
    narrative: str | None = None
    serviceops_handoff: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path_from_seed"] = list(self.path_from_seed)
        d["blast_radius"] = list(self.blast_radius)
        d["recommended_actions"] = list(self.recommended_actions)
        return d


_TIER_LABEL = {1: "high", 2: "medium", 3: "low"}


def package_verdict(
    bundle: EvidenceBundle,
    *,
    blast_radius: list[str] | None = None,
    narrative: str | None = None,
    include_narrative: bool = True,
) -> VerdictCard:
    """Build the operator VerdictCard from an EvidenceBundle (D4 required card)."""
    blast = tuple(
        blast_radius
        if blast_radius is not None
        else _default_blast(bundle)
    )
    actions = _default_actions(bundle)
    summary = (
        f"{bundle.detect_class} on path "
        f"{' → '.join(bundle.path_from_seed)}; "
        f"leaf claim {bundle.leaf_ci_id} ({bundle.leaf_ci_type}) "
        f"with confidence tier {bundle.confidence_tier}"
    )
    narr = narrative
    if include_narrative and narr is None:
        narr = _default_narrative(bundle)
    counts = {
        "metrics": len(bundle.metrics),
        "logs": len(bundle.logs),
        "traces": len(bundle.traces),
        "changes": len(bundle.changes),
        "topology": len(bundle.topology),
    }
    handoff = {
        "ci_id": bundle.leaf_ci_id,
        "tenant": bundle.tenant,
        "case_id": bundle.case_id,
        "detect_class": bundle.detect_class,
        "note": "ServiceOps ticket key = same ci_id (FR-J1); ticket create is out of PoC",
    }
    return VerdictCard(
        case_id=bundle.case_id,
        tenant=bundle.tenant,
        root_ci_id=bundle.leaf_ci_id,
        root_ci_type=bundle.leaf_ci_type,
        detect_class=bundle.detect_class,
        summary=summary,
        path_from_seed=bundle.path_from_seed,
        blast_radius=blast,
        recommended_actions=actions,
        confidence_tier=bundle.confidence_tier,
        confidence_label=_TIER_LABEL.get(bundle.confidence_tier, "unknown"),
        evidence_counts=counts,
        narrative=narr,
        serviceops_handoff=handoff,
        labels={
            "weakest_evidence_type": bundle.weakest_evidence_type,
            "identify_rationale": bundle.rationale,
        },
    )


def _default_blast(bundle: EvidenceBundle) -> list[str]:
    # Upstream of leaf on the walk path (seed first) — teaching blast set
    return list(dict.fromkeys(bundle.path_from_seed))


def _default_actions(bundle: EvidenceBundle) -> tuple[str, ...]:
    leaf = bundle.leaf_ci_id
    if bundle.leaf_ci_type == "Database":
        return (
            f"Check connection pool / slow queries on {leaf}",
            "Confirm recent schema or capacity changes (change feed empty in lab)",
            f"Validate dependents along {' → '.join(bundle.path_from_seed)}",
        )
    if bundle.leaf_ci_type == "Host":
        return (
            f"Inspect host saturation on {leaf}",
            "Review colocated runtimes on the same host",
        )
    return (
        f"Investigate {leaf}",
        "Widen WorkingSet hops if evidence is thin",
    )


def _default_narrative(bundle: EvidenceBundle) -> str:
    metric_bit = ""
    if bundle.metrics:
        metric_bit = bundle.metrics[0].get("summary", "")
    log_bit = bundle.logs[0].get("summary", "") if bundle.logs else ""
    return (
        f"Case {bundle.case_id}: {bundle.detect_class} localized to "
        f"{bundle.leaf_ci_id}. {metric_bit} {log_bit} "
        f"Weakest evidence channel: {bundle.weakest_evidence_type}."
    ).strip()
