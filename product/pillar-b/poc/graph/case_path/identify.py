"""E10 Identify — LeafClaim + WorkingSet → EvidenceBundle.

Corroborates the leaf with multimodal evidence refs. Does not open S3 dumps;
sketch/trace/log/change items are structured refs (or lab stubs).
Identify (E10) ≠ Identity (E2 Normalize).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from graph.case_path.localize import LeafClaim
from graph.case_path.scope import WorkingSet

EvidenceProvider = Callable[[LeafClaim, WorkingSet], dict[str, list[dict[str, Any]]]]


@dataclass(frozen=True)
class EvidenceBundle:
    """E10 output: multimodal corroboration + confidence tier (Verify starts here)."""

    case_id: str
    tenant: str
    leaf_ci_id: str
    leaf_ci_type: str
    detect_class: str
    path_from_seed: tuple[str, ...]
    metrics: tuple[dict[str, Any], ...]
    logs: tuple[dict[str, Any], ...]
    traces: tuple[dict[str, Any], ...]
    changes: tuple[dict[str, Any], ...]
    topology: tuple[dict[str, Any], ...]
    confidence_tier: int  # 1=strong … 3=weak (teaching scale)
    weakest_evidence_type: str
    rationale: str
    labels: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path_from_seed"] = list(self.path_from_seed)
        d["metrics"] = list(self.metrics)
        d["logs"] = list(self.logs)
        d["traces"] = list(self.traces)
        d["changes"] = list(self.changes)
        d["topology"] = list(self.topology)
        return d


def build_evidence_bundle(
    claim: LeafClaim,
    working_set: WorkingSet,
    *,
    evidence_provider: EvidenceProvider | None = None,
) -> EvidenceBundle:
    """Assemble an EvidenceBundle for the LeafClaim.

    Default lab provider synthesizes teaching evidence from WorkingSet sketch_refs
    and the claim path. Inject ``evidence_provider`` for Dest-backed lookups later.
    """
    provided = (
        evidence_provider(claim, working_set)
        if evidence_provider is not None
        else _default_lab_evidence(claim, working_set)
    )
    metrics = tuple(provided.get("metrics") or [])
    logs = tuple(provided.get("logs") or [])
    traces = tuple(provided.get("traces") or [])
    changes = tuple(provided.get("changes") or [])
    topology = tuple(provided.get("topology") or [])

    tier, weakest = _confidence_tier(metrics, logs, traces, changes, topology)
    rationale = (
        f"Identify leaf={claim.claim_ci_id}: "
        f"metrics={len(metrics)} logs={len(logs)} traces={len(traces)} "
        f"changes={len(changes)} topology={len(topology)}; "
        f"tier={tier} weakest={weakest}"
    )
    return EvidenceBundle(
        case_id=claim.case_id,
        tenant=claim.tenant,
        leaf_ci_id=claim.claim_ci_id,
        leaf_ci_type=claim.claim_ci_type,
        detect_class=claim.detect_class,
        path_from_seed=claim.path_from_seed,
        metrics=metrics,
        logs=logs,
        traces=traces,
        changes=changes,
        topology=topology,
        confidence_tier=tier,
        weakest_evidence_type=weakest,
        rationale=rationale,
        labels={"alternatives": list(claim.alternatives)},
    )


def _default_lab_evidence(
    claim: LeafClaim,
    working_set: WorkingSet,
) -> dict[str, list[dict[str, Any]]]:
    """Teaching stubs — enough to exercise Package without live stores."""
    metrics: list[dict[str, Any]] = []
    for ref in working_set.sketch_refs:
        entity = ref.get("entity_id") or ref.get("ci_id")
        if entity in (claim.claim_ci_id, working_set.seed_ci_id):
            metrics.append(
                {
                    "kind": "sketch_ref",
                    "ci_id": entity,
                    "metric_id": ref.get("metric_id", "request.latency_ms"),
                    "summary": ref.get("summary")
                    or f"sketch ref for {entity}/{ref.get('metric_id')}",
                }
            )
    if not metrics:
        # Fabric teaching line: p95 vs expected on the seed, attributed to leaf path
        metrics.append(
            {
                "kind": "detect_contrast",
                "ci_id": working_set.seed_ci_id,
                "metric_id": "request.latency_ms",
                "summary": "p95 elevated vs seasonal baseline (lab Detect contrast)",
                "leaf_ci_id": claim.claim_ci_id,
            }
        )

    logs = [
        {
            "kind": "log_pattern",
            "ci_id": claim.claim_ci_id,
            "pattern": "connection pool exhausted",
            "summary": f"lab log pattern on {claim.claim_ci_id}",
        }
    ]
    traces = [
        {
            "kind": "span_ref",
            "ci_id": claim.claim_ci_id,
            "trace_id": "trace-lab-checkout-1",
            "summary": f"slow span toward {claim.claim_ci_id}",
        }
    ]
    changes: list[dict[str, Any]] = []  # empty = honest gap in lab
    topology = [
        {
            "kind": "walk_path",
            "path": list(claim.path_from_seed),
            "summary": "→".join(claim.path_from_seed),
        }
    ]
    return {
        "metrics": metrics,
        "logs": logs,
        "traces": traces,
        "changes": changes,
        "topology": topology,
    }


def _confidence_tier(
    metrics: tuple,
    logs: tuple,
    traces: tuple,
    changes: tuple,
    topology: tuple,
) -> tuple[int, str]:
    """1 = strong (multi-modal), 2 = medium, 3 = weak."""
    counts = {
        "metrics": len(metrics),
        "logs": len(logs),
        "traces": len(traces),
        "changes": len(changes),
        "topology": len(topology),
    }
    present = [k for k, n in counts.items() if n > 0]
    if len(present) >= 3 and counts["topology"] and (counts["metrics"] or counts["logs"]):
        # changes often empty in lab — still tier 2 if other three exist
        weakest = min(
            (k for k in ("changes", "metrics", "logs", "traces", "topology") if counts[k] == 0),
            default="corroborating",
            key=lambda k: {"changes": 0, "traces": 1, "logs": 2, "metrics": 3, "topology": 4}[k],
        )
        if counts["changes"] == 0:
            return 2, "changes"
        return 1, weakest
    if len(present) >= 2:
        weakest = min(present, key=lambda k: counts[k]) if present else "none"
        # prefer naming an absent modality when only 2 present
        for k in ("changes", "traces", "logs", "metrics"):
            if counts[k] == 0:
                return 2, k
        return 2, weakest
    return 3, present[0] if present else "none"
