"""Nezha adapter — pattern ranking with dataset and simulation paths."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from poc.types import NezhaRequest, NezhaResult, PatternRank

logger = logging.getLogger(__name__)

# federated-pipeline/poc/adapters → federated-pipeline/Nezha
NEZHA_ROOT = Path(__file__).resolve().parents[2] / "Nezha"


def rank_patterns(
    normal_counts: dict[str, int],
    abnormal_counts: dict[str, int],
    min_support: int = 5,
    min_score: float = 0.67,
    top_k: int = 5,
) -> list[PatternRank]:
    """Core Nezha scoring: S_C / (S_C + S_P)."""
    scored: list[PatternRank] = []

    for pattern, abnormal in abnormal_counts.items():
        if abnormal <= min_support:
            continue
        normal = normal_counts.get(pattern, 0)
        score = abnormal / (abnormal + normal) if (abnormal + normal) else 1.0
        if score < min_score:
            continue

        expected, actual = _split_pattern_pair(pattern)
        scored.append(
            PatternRank(
                expected_pattern=expected,
                actual_pattern=actual,
                score=round(score, 4),
                support_count=abnormal,
            )
        )

    scored.sort(key=lambda p: p.score, reverse=True)
    return scored[:top_k]


def _split_pattern_pair(pattern: str) -> tuple[str, str]:
    if "→" in pattern:
        parts = pattern.split("→", 1)
        return parts[0], parts[1]
    if "_" in pattern:
        parts = pattern.split("_", 1)
        return parts[0], parts[1]
    return pattern, pattern


def _abnormal_minute(inject_time: str) -> str:
    """Match Nezha evaluation: inspect minute = inject minute + 2."""
    date, clock = inject_time.split(" ")
    hour_s, minute_s, *_ = clock.split(":")
    hour = int(hour_s)
    minute = int(minute_s) + 2
    if minute >= 60:
        hour += 1
        minute -= 60
    return f"{date} {hour:02d}:{minute:02d}"


class NezhaAdapter:
    def __init__(self) -> None:
        self.prefer_dataset = False
        self.dataset_ns = "hipster"
        self.dataset_fault: dict[str, Any] | None = None

    def diagnose(self, request: NezhaRequest) -> NezhaResult:
        if self.prefer_dataset and self.dataset_fault:
            try:
                return self.diagnose_from_dataset(request)
            except Exception as exc:  # noqa: BLE001 — fall back for PoC robustness
                logger.warning("Nezha dataset path failed (%s); using simulated patterns", exc)
        return self.diagnose_simulated(request)

    def diagnose_simulated(self, request: NezhaRequest) -> NezhaResult:
        """PoC pattern drift using in-memory counts for a known service."""
        patterns = _SIMULATED_PATTERNS.get(request.service, _DEFAULT_PATTERNS)
        ranked = rank_patterns(
            patterns["normal"],
            patterns["abnormal"],
            top_k=request.top_k,
        )
        return NezhaResult(
            incident_id=request.incident_id,
            service=request.service,
            ranked_patterns=ranked,
        )

    def diagnose_from_counts(
        self,
        request: NezhaRequest,
        normal_counts: dict[str, int],
        abnormal_counts: dict[str, int],
    ) -> NezhaResult:
        ranked = rank_patterns(
            normal_counts,
            abnormal_counts,
            top_k=request.top_k,
        )
        return NezhaResult(
            incident_id=request.incident_id,
            service=request.service,
            ranked_patterns=ranked,
        )

    def diagnose_from_dataset(self, request: NezhaRequest) -> NezhaResult:
        """Run Nezha pattern_ranker against Online Boutique / TrainTicket rca_data."""
        if not self.dataset_fault:
            raise ValueError("dataset_fault is required for diagnose_from_dataset")

        nezha = _load_nezha_modules()
        ns = self.dataset_ns
        fault = self.dataset_fault
        normal_time = _NORMAL_TIMES[ns]
        abnormal_time = _abnormal_minute(fault["inject_time"])

        miner = nezha["get_miner"](ns)
        construction = str(NEZHA_ROOT / "construct_data")
        normal_patterns, normal_graphs, _ = nezha["get_pattern"](
            normal_time, ns, construction, miner
        )
        result_list, _ = nezha["pattern_ranker"](
            normal_patterns,
            normal_graphs,
            abnormal_time,
            ns,
            miner,
            topk=request.top_k,
        )

        service = fault.get("service") or request.service
        ranked = _results_to_pattern_ranks(result_list, nezha["from_id_to_template"], miner, service)
        if not ranked:
            # Keep service-scoped simulated patterns if dataset ranks don't match service.
            return self.diagnose_simulated(request)

        return NezhaResult(
            incident_id=request.incident_id,
            service=service,
            ranked_patterns=ranked[: request.top_k],
        )


def _load_nezha_modules() -> dict[str, Any]:
    if str(NEZHA_ROOT) not in sys.path:
        sys.path.insert(0, str(NEZHA_ROOT))

    from drain3 import TemplateMiner  # noqa: F401
    from drain3.template_miner_config import TemplateMinerConfig
    from drain3.file_persistence import FilePersistence
    from log_parsing import from_id_to_template
    from pattern_ranker import get_pattern, pattern_ranker

    def get_miner(ns: str):
        config = TemplateMinerConfig()
        config.load(str(NEZHA_ROOT / "log_template" / f"drain3_{ns}.ini"))
        config.profiling_enabled = False
        persistence = FilePersistence(str(NEZHA_ROOT / "log_template" / f"{ns}.bin"))
        return TemplateMiner(persistence, config=config)

    return {
        "get_miner": get_miner,
        "get_pattern": get_pattern,
        "pattern_ranker": pattern_ranker,
        "from_id_to_template": from_id_to_template,
        "TemplateMinerConfig": TemplateMinerConfig,
        "FilePersistence": FilePersistence,
    }


def _results_to_pattern_ranks(
    result_list: list[dict],
    from_id_to_template,
    miner,
    service: str,
) -> list[PatternRank]:
    ranked: list[PatternRank] = []
    for item in result_list:
        pod = str(item.get("pod", ""))
        if service and service not in pod:
            continue
        events = item["events"]
        src_id, tgt_id = events.split("_", 1)
        expected = from_id_to_template(int(src_id), miner)
        actual = from_id_to_template(int(tgt_id), miner)
        ranked.append(
            PatternRank(
                expected_pattern=expected,
                actual_pattern=actual,
                score=round(float(item["score"]), 4),
                support_count=int(item.get("deepth", 1)),
            )
        )
    if ranked:
        return ranked

    # If no pod matched, still surface top patterns with template labels.
    for item in result_list[:5]:
        events = item["events"]
        src_id, tgt_id = events.split("_", 1)
        ranked.append(
            PatternRank(
                expected_pattern=from_id_to_template(int(src_id), miner),
                actual_pattern=from_id_to_template(int(tgt_id), miner),
                score=round(float(item["score"]), 4),
                support_count=int(item.get("deepth", 1)),
            )
        )
    return ranked


_NORMAL_TIMES = {
    "hipster": "2022-08-22 03:51",
    "ts": "2023-01-29 08:50",
}

_DEFAULT_PATTERNS = {
    "normal": {"service_start→db_query": 420, "service_start→cache_hit": 890},
    "abnormal": {"service_start→db_query": 38, "service_start→db_timeout": 142},
}

_SIMULATED_PATTERNS: dict[str, dict[str, dict[str, int]]] = {
    "crawler_vm": {
        "normal": {
            "crawler_vm→session_open": 520,
            "crawler_vm→frontend_request": 480,
            "frontend_ms→backend_call": 310,
        },
        "abnormal": {
            "crawler_vm→session_open": 42,
            "crawler_vm→frontend_timeout": 198,
            "frontend_ms→backend_call": 28,
        },
    },
    "checkoutservice": {
        "normal": {
            "Start charge card→Charge successfully": 480,
            "Place order→Order complete": 410,
        },
        "abnormal": {
            "Start charge card→Charge successfully": 40,
            "Checkout→CpuUsageRate(%)": 160,
        },
    },
    "frontend": {
        "normal": {
            "Serving product page→GetProduct start": 500,
            "frontend→checkout_call": 450,
        },
        "abnormal": {
            "Serving product page→GetProduct start": 55,
            "frontend→checkout_timeout": 140,
        },
    },
    "frontend_ms": {
        "normal": {
            "frontend_ms→route_request": 600,
            "frontend_ms→backend_call": 580,
        },
        "abnormal": {
            "frontend_ms→route_request": 55,
            "frontend_ms→backend_timeout": 165,
            "frontend_ms→backend_call": 22,
        },
    },
    "backend_vm_1": {
        "normal": {
            "backend_vm_1→process_request": 700,
            "backend_vm_1→db_read": 650,
        },
        "abnormal": {
            "backend_vm_1→process_request": 48,
            "backend_vm_1→cpu_throttle": 152,
        },
    },
}
