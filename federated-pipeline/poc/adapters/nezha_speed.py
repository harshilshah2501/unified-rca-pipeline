"""Nezha adapter backed by speed-tier pattern counts (Redis/Dragonfly)."""

from __future__ import annotations

from poc.adapters.nezha import NezhaAdapter, rank_patterns
from poc.types import NezhaRequest, NezhaResult


class SpeedBackedNezhaAdapter(NezhaAdapter):
    """Nezha micro-localization using pattern counts from the speed tier."""

    def __init__(self, speed_store) -> None:
        super().__init__()
        self.speed_store = speed_store

    def diagnose(self, request: NezhaRequest) -> NezhaResult:
        tenant = request.tenant
        normal = self.speed_store.pattern_counts(tenant, "fault-free")
        abnormal = self.speed_store.pattern_counts(tenant, "fault-suffering")
        service = request.service
        normal_f = {k: v for k, v in normal.items() if service in k}
        abnormal_f = {k: v for k, v in abnormal.items() if service in k}
        ranked = rank_patterns(
            normal_f or normal,
            abnormal_f or abnormal,
            top_k=request.top_k,
            min_score=0.5,
            min_support=3,
        )
        if ranked:
            return NezhaResult(
                incident_id=request.incident_id,
                service=service,
                ranked_patterns=ranked,
            )
        return super().diagnose(request)
