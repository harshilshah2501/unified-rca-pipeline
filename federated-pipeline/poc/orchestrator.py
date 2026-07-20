"""Unified RCA orchestrator — coordinates Panorama → Murphy → Nezha."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass

from murphy.store import MetricStore

from poc.adapters.murphy import MurphyAdapter, default_windows
from poc.adapters.nezha import NezhaAdapter
from poc.adapters.panorama import PanoramaAdapter, PanoramaConfig
from poc.types import (
    DetectionFlag,
    HopLog,
    MurphyRequest,
    MurphyResult,
    NezhaRequest,
    NezhaResult,
    RCAVerdict,
    TimeWindow,
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    theta_pano: float = 0.5
    theta_murphy: float = 0.3
    fusion_weights: tuple[float, float, float] = (0.2, 0.4, 0.4)
    tenant: str = "default"


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class UnifiedRCAOrchestrator:
    """
    Coordinates the three-tier RCA pipeline.

    Hop 1: Panorama detection flag
    Hop 2: Build MurphyRequest
    Hop 3: Murphy macro localization
    Hop 4: Build NezhaRequest (narrowing)
    Hop 5: Nezha micro localization
    Hop 6: Fuse verdict
    """

    def __init__(
        self,
        metric_store: MetricStore,
        config: OrchestratorConfig | None = None,
    ) -> None:
        self.config = config or OrchestratorConfig()
        self.panorama = PanoramaAdapter(
            PanoramaConfig(evidence_threshold=self.config.theta_pano)
        )
        self.murphy = MurphyAdapter(metric_store)
        self.nezha = NezhaAdapter()
        self.hop_logs: list[HopLog] = []

    def flag_to_murphy_request(self, flag: DetectionFlag) -> MurphyRequest:
        """Hop 2 — translate Panorama flag into Murphy input."""
        return MurphyRequest(
            incident_id=flag.incident_id,
            timestamp=flag.timestamp,
            symptom_entity=flag.symptom_entity or flag.entity,
            symptom_metric=flag.symptom_metric or flag.metric,
            flagged_entities=[flag.entity],
            gibbs_iterations=4,
        )

    def murphy_to_nezha_request(
        self,
        murphy_result: MurphyResult,
        flag: DetectionFlag,
    ) -> NezhaRequest | None:
        """Hop 4 — narrow Murphy posterior to a Nezha scope."""
        if not murphy_result.posterior:
            return None

        top_entity = max(murphy_result.posterior, key=murphy_result.posterior.get)
        max_posterior = murphy_result.posterior[top_entity]
        if max_posterior < self.config.theta_murphy:
            return None

        baseline_start, baseline_end, suffering_end = default_windows(flag.timestamp)
        return NezhaRequest(
            incident_id=flag.incident_id,
            tenant=self.config.tenant,
            service=top_entity,
            time_window=TimeWindow(start=baseline_end, end=suffering_end),
            baseline_window=TimeWindow(start=baseline_start, end=baseline_end),
            top_k=5,
        )

    def fuse_verdict(
        self,
        flag: DetectionFlag,
        murphy_result: MurphyResult,
        nezha_result: NezhaResult | None,
    ) -> RCAVerdict:
        """Hop 6 — combine outputs into a single RCA verdict."""
        w_pano, w_murphy, w_nezha = self.config.fusion_weights

        murphy_entity = ""
        murphy_posterior = 0.0
        if murphy_result.posterior:
            murphy_entity = max(murphy_result.posterior, key=murphy_result.posterior.get)
            murphy_posterior = murphy_result.posterior[murphy_entity]

        nezha_score = 0.0
        pattern_str = ""
        if nezha_result and nezha_result.ranked_patterns:
            top = nezha_result.ranked_patterns[0]
            nezha_score = top.score
            pattern_str = f"{top.expected_pattern} → {top.actual_pattern}"

        confidence = (
            w_pano * flag.evidence_score
            + w_murphy * murphy_posterior
            + w_nezha * nezha_score
        )

        root_entity = murphy_entity or flag.symptom_entity or flag.entity

        confidence_level = "high" if confidence >= 0.6 else "low"
        summary = (
            f"{root_entity} identified as root cause; "
            f"Panorama {flag.status} (score={flag.evidence_score:.2f}), "
            f"Murphy posterior={murphy_posterior:.2f}"
        )
        if pattern_str:
            summary += f", Nezha pattern shift: {pattern_str} (score={nezha_score:.2f})"

        return RCAVerdict(
            incident_id=flag.incident_id,
            root_cause_entity=root_entity,
            root_cause_pattern=pattern_str,
            confidence=confidence,
            confidence_level=confidence_level,
            evidence={
                "panorama": {
                    "evidence_score": flag.evidence_score,
                    "status": flag.status,
                    "entity": flag.entity,
                },
                "murphy": {
                    "posterior": murphy_posterior,
                    "entity": murphy_entity,
                    "distribution": murphy_result.posterior,
                },
                "nezha": {
                    "pattern_score": nezha_score,
                    "rank": 1 if nezha_result and nezha_result.ranked_patterns else None,
                },
            },
            summary=summary,
        )

    def _log_hop(
        self,
        hop: int,
        component: str,
        incident_id: str,
        started: float,
        input_payload: dict,
        output_payload: dict,
    ) -> None:
        entry = HopLog(
            hop=hop,
            component=component,
            incident_id=incident_id,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            input_hash=_hash_payload(input_payload),
            output_hash=_hash_payload(output_payload),
        )
        self.hop_logs.append(entry)
        logger.info(
            "hop=%d component=%s incident=%s latency_ms=%.2f in=%s out=%s",
            entry.hop,
            entry.component,
            entry.incident_id,
            entry.latency_ms,
            entry.input_hash,
            entry.output_hash,
        )

    def run_pipeline(
        self,
        flag: DetectionFlag,
        incident_time=None,
    ) -> RCAVerdict:
        """Execute the full Panorama → Murphy → Nezha → fusion pipeline."""
        self.hop_logs.clear()

        t0 = time.perf_counter()
        hop1 = getattr(flag, "detect_source", None) or "shared_detect"
        self._log_hop(1, hop1, flag.incident_id, t0, {}, flag.to_dict())

        t1 = time.perf_counter()
        murphy_request = self.flag_to_murphy_request(flag)
        self._log_hop(
            2, "orchestrator", flag.incident_id, t1, flag.to_dict(), murphy_request.to_dict()
        )

        t2 = time.perf_counter()
        murphy_result = self.murphy.diagnose(murphy_request, incident_time=incident_time)
        self._log_hop(
            3,
            "murphy",
            flag.incident_id,
            t2,
            murphy_request.to_dict(),
            murphy_result.to_dict(),
        )

        t3 = time.perf_counter()
        nezha_request = self.murphy_to_nezha_request(murphy_result, flag)
        nezha_result = None
        if nezha_request:
            self._log_hop(
                4,
                "orchestrator",
                flag.incident_id,
                t3,
                murphy_result.to_dict(),
                nezha_request.to_dict(),
            )
            t4 = time.perf_counter()
            nezha_result = self.nezha.diagnose(nezha_request)
            self._log_hop(
                5,
                "nezha",
                flag.incident_id,
                t4,
                nezha_request.to_dict(),
                nezha_result.to_dict(),
            )
        else:
            self._log_hop(
                4,
                "orchestrator",
                flag.incident_id,
                t3,
                murphy_result.to_dict(),
                {"skipped": True, "reason": "murphy_posterior_below_threshold"},
            )

        t5 = time.perf_counter()
        verdict = self.fuse_verdict(flag, murphy_result, nezha_result)
        self._log_hop(
            6,
            "orchestrator",
            flag.incident_id,
            t5,
            {
                "panorama": flag.to_dict(),
                "murphy": murphy_result.to_dict(),
                "nezha": nezha_result.to_dict() if nezha_result else None,
            },
            verdict.to_dict(),
        )
        return verdict
