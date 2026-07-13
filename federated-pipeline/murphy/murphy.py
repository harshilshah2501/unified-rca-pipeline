"""Top-level Murphy orchestrator."""

from __future__ import annotations

from datetime import datetime

from murphy.explainer import ExplanationGenerator
from murphy.graph import RelationshipGraph
from murphy.mrf import MRFDiagnosisEngine
from murphy.ranker import RootCauseRanker
from murphy.store import MetricStore
from murphy.types import DiagnosisResult, Entity, Symptom


class Murphy:
    """
    Top-level Murphy orchestrator.
    Matches paper Figure 2 workflow.
    """

    def __init__(
        self,
        monitoring_db: MetricStore,
        gibbs_iterations: int = 4,
        n_samples: int = 5000,
        max_graph_hops: int = 5,
        ridge_alpha: float = 1.0,
        top_b_neighbors: int = 10,
        counterfactual_stdevs: float = 2.0,
        parallel: bool = True,
        max_workers: int | None = None,
    ) -> None:
        self.monitoring_db = monitoring_db
        self.graph = RelationshipGraph(max_hops=max_graph_hops)
        self.engine = MRFDiagnosisEngine(
            graph=self.graph,
            store=monitoring_db,
            gibbs_iterations=gibbs_iterations,
            n_samples=n_samples,
            counterfactual_stdevs=counterfactual_stdevs,
            ridge_alpha=ridge_alpha,
            top_b_neighbors=top_b_neighbors,
            parallel=parallel,
            max_workers=max_workers,
        )
        self.ranker = RootCauseRanker()
        self.explainer = ExplanationGenerator()

    def diagnose(
        self,
        symptom: Symptom,
        incident_time: datetime | None = None,
    ) -> DiagnosisResult:
        incident_time = incident_time or symptom.incident_time

        root_causes, current_metrics, historical_stats = self.engine.diagnose(
            symptom, incident_time
        )
        ranked = self.ranker.rank(root_causes)

        entities: dict[str, Entity] = {}
        for eid in self.graph.entity_ids:
            entity = self.monitoring_db.get_entity(eid)
            if entity:
                entities[eid] = entity

        explanation_chains: dict[str, list] = {}
        for rc in ranked:
            chain = self.explainer.generate_chain(
                rc,
                symptom,
                self.graph,
                current_metrics,
                historical_stats,
            )
            explanation_chains[rc.entity_id] = chain

        return DiagnosisResult(
            symptom=symptom,
            root_causes=ranked,
            explanation_chains=explanation_chains,
        )

    def _resolve_app_id(self, symptom: Symptom) -> str:
        entity = self.monitoring_db.get_entity(symptom.entity_id)
        if entity:
            return entity.app_id
        for e in self.monitoring_db.get_entity_metadata(""):
            if e.id == symptom.entity_id:
                return e.app_id
        return ""
