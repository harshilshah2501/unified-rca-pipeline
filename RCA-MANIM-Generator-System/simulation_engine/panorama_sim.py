"""Panorama observer voting simulation with InferView / InferPano."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from rca_spec_parser import RCASpec
from simulation_engine.base import SimulationFrame

VIEW_METRIC_HISTORY_SIZE = 2

STATUS_SEVERITY = {
    "HEALTHY": 0,
    "PENDING": 1,
    "MAYBE_UNHEALTHY": 2,
    "UNHEALTHY": 3,
    "DEAD": 4,
}


@dataclass
class Report:
    observer: str
    subject: str
    metric: str
    status: str
    score: float
    tick: int = 0


@dataclass
class MetricValue:
    status: str
    score: float


@dataclass
class Observation:
    metrics: dict[str, MetricValue] = field(default_factory=dict)


@dataclass
class View:
    observer: str
    subject: str
    observations: list[Observation] = field(default_factory=list)


def infer_view(view: View) -> dict[str, MetricValue] | None:
    if not view.observations:
        return None
    metrics: dict[str, MetricValue] = {}
    aggs: dict[str, dict[str, Any]] = {}

    for obs in reversed(view.observations):
        for name, metric in obs.metrics.items():
            agg = aggs.setdefault(name, {"cnt": 0, "stop": False})
            if agg["stop"] or agg["cnt"] >= VIEW_METRIC_HISTORY_SIZE:
                continue
            if name not in metrics:
                metrics[name] = MetricValue(status=metric.status, score=metric.score)
                agg["cnt"] += 1
            else:
                existing = metrics[name]
                if metric.status == "PENDING" and existing.status == "HEALTHY":
                    continue
                if existing.status != metric.status:
                    agg["stop"] = True
                    continue
                existing.score += metric.score
                agg["cnt"] += 1

    for name, metric in metrics.items():
        if aggs[name]["cnt"] > 1:
            metric.score /= aggs[name]["cnt"]
    return metrics


def infer_pano(views: dict[str, View]) -> dict[str, MetricValue]:
    statmap: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"score_sum": 0.0, "cnt": 0, "status_hist": defaultdict(int)}
    )
    for view in views.values():
        inferred = infer_view(view)
        if not inferred:
            continue
        for name, metric in inferred.items():
            stat = statmap[name]
            stat["score_sum"] += metric.score
            stat["cnt"] += 1
            stat["status_hist"][metric.status] += 1

    result: dict[str, MetricValue] = {}
    for name, stat in statmap.items():
        max_cnt = 0
        max_status = "HEALTHY"
        for status, cnt in stat["status_hist"].items():
            if cnt > max_cnt:
                max_cnt = cnt
                max_status = status
            elif cnt == max_cnt and STATUS_SEVERITY.get(status, 0) > STATUS_SEVERITY.get(max_status, 0):
                max_status = status
        avg_score = stat["score_sum"] / stat["cnt"] if stat["cnt"] else 0.0
        result[name] = MetricValue(status=max_status, score=avg_score)
    return result


class PanoramaSimulator:
    def run(self, spec: RCASpec) -> list[SimulationFrame]:
        observers = [n["id"] for n in spec.nodes if n.get("role") == "observer"]
        subjects = [n["id"] for n in spec.nodes if n.get("role") == "subject"]
        subject = subjects[0] if subjects else spec.fault.target

        reports: list[Report] = []
        for raw in spec.reports:
            reports.append(
                Report(
                    observer=raw["observer"],
                    subject=raw.get("subject", subject),
                    metric=raw["metric"],
                    status=raw["status"],
                    score=float(raw["score"]),
                    tick=int(raw.get("tick", 0)),
                )
            )

        if not reports:
            reports = self._synthetic_reports(spec, observers, subject)

        ticks = sorted({r.tick for r in reports})
        views: dict[str, View] = {
            obs: View(observer=obs, subject=subject) for obs in observers
        }
        frames: list[SimulationFrame] = []

        for step, tick in enumerate(ticks):
            batch = [r for r in reports if r.tick == tick]
            for report in batch:
                view = views.setdefault(
                    report.observer, View(observer=report.observer, subject=report.subject)
                )
                obs = Observation(
                    metrics={
                        report.metric: MetricValue(
                            status=report.status, score=report.score
                        )
                    }
                )
                view.observations.append(obs)

            view_summaries = {obs: infer_view(v) for obs, v in views.items()}
            pano = infer_pano(views)
            vote_bars = {
                f"{obs}:{metric}": {
                    "status": mv.status,
                    "score": mv.score,
                }
                for obs, summary in view_summaries.items()
                if summary
                for metric, mv in summary.items()
            }
            consensus_locked = False
            if pano:
                statuses = {mv.status for mv in pano.values()}
                consensus_locked = len(statuses) == 1 and observers and all(
                    view_summaries.get(o) for o in observers
                )

            node_states: dict[str, float | str] = {}
            for obs in observers:
                summary = view_summaries.get(obs)
                if summary:
                    for metric, mv in summary.items():
                        node_states[f"{obs}:{metric}"] = f"{mv.status}({mv.score:.0f})"

            frames.append(
                SimulationFrame(
                    step=step,
                    node_states=node_states,
                    distributions={},
                    edges_active=[(r.observer, r.subject) for r in batch],
                    metadata={
                        "phase": "voting",
                        "tick": tick,
                        "batch_reports": [
                            {
                                "observer": r.observer,
                                "subject": r.subject,
                                "metric": r.metric,
                                "status": r.status,
                                "score": r.score,
                            }
                            for r in batch
                        ],
                        "view_summaries": {
                            obs: {m: {"status": v.status, "score": v.score} for m, v in s.items()}
                            for obs, s in view_summaries.items()
                            if s
                        },
                        "pano": {
                            m: {"status": v.status, "score": v.score} for m, v in pano.items()
                        },
                        "vote_bars": vote_bars,
                        "consensus_locked": consensus_locked,
                    },
                )
            )

        return frames

    def _synthetic_reports(
        self, spec: RCASpec, observers: list[str], subject: str
    ) -> list[Report]:
        metric = spec.fault.metrics[0] if spec.fault.metrics else "health"
        reports: list[Report] = []
        for i, obs in enumerate(observers):
            status = "UNHEALTHY" if i > 0 else "MAYBE_UNHEALTHY"
            reports.append(
                Report(
                    observer=obs,
                    subject=subject,
                    metric=metric,
                    status=status,
                    score=20.0 + i * 5,
                    tick=i + 1,
                )
            )
        return reports
