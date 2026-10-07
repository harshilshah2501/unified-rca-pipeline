"""Lean RCA core — invocation-graph search (PRD §2.1–§2.3)."""

from core_engine.lean.invocation_graph import InvocationGraph
from core_engine.lean.search import best_first_walk
from core_engine.lean.temporal import rank_by_onset
from core_engine.lean.info_gain import score_candidate
from core_engine.lean.care import care_fallback_candidates
from core_engine.lean.signature import infer_signature

__all__ = [
    "InvocationGraph",
    "best_first_walk",
    "rank_by_onset",
    "score_candidate",
    "care_fallback_candidates",
    "infer_signature",
]
