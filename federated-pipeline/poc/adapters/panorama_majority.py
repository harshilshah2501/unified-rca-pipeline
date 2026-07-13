"""Panorama bounded-look-back majority voting (Python port of decision/majority.go)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable


class Status(IntEnum):
    """Matches panorama/idl/health.proto Status enum ordering for tie-breaks."""

    NA = 0
    UNHEALTHY = 1
    HEALTHY = 2
    MAYBE_UNHEALTHY = 3
    PENDING = 4
    SUSPECT = 5
    INIT = 6


VIEW_METRIC_HISTORY_SIZE = 2

STATUS_ALIASES = {
    "u": Status.UNHEALTHY,
    "unhealthy": Status.UNHEALTHY,
    "h": Status.HEALTHY,
    "healthy": Status.HEALTHY,
    "m": Status.MAYBE_UNHEALTHY,
    "maybe_unhealthy": Status.MAYBE_UNHEALTHY,
    "p": Status.PENDING,
    "pending": Status.PENDING,
    "s": Status.SUSPECT,
    "suspect": Status.SUSPECT,
}


@dataclass
class MetricValue:
    status: Status
    score: float


@dataclass
class Observation:
    metrics: dict[str, MetricValue]
    ts: float = 0.0


@dataclass
class ObserverReport:
    observer: str
    subject: str
    metric: str
    status: Status | str
    score: float
    ts: float = 0.0

    def resolved_status(self) -> Status:
        if isinstance(self.status, Status):
            return self.status
        key = str(self.status).strip().lower()
        if key not in STATUS_ALIASES:
            raise ValueError(f"Unknown status: {self.status!r}")
        return STATUS_ALIASES[key]


@dataclass
class Inference:
    subject: str
    observers: list[str]
    metrics: dict[str, MetricValue] = field(default_factory=dict)

    @property
    def primary_metric(self) -> tuple[str, MetricValue] | None:
        if not self.metrics:
            return None
        # Prefer unhealthy-ish metrics by severity, then highest score.
        def rank(item: tuple[str, MetricValue]) -> tuple[int, float]:
            name, value = item
            severity = {
                Status.UNHEALTHY: 3,
                Status.MAYBE_UNHEALTHY: 2,
                Status.SUSPECT: 1,
            }.get(value.status, 0)
            return (severity, value.score)

        return max(self.metrics.items(), key=rank)


def _infer_view(observer: str, subject: str, observations: list[Observation]) -> Inference | None:
    """Bounded look-back over the last N values per metric (InferView)."""
    if not observations:
        return None

    metrics: dict[str, MetricValue] = {}
    aggs: dict[str, dict[str, object]] = {}
    pts = observations[-1].ts

    for observation in reversed(observations):
        for name, metric in observation.metrics.items():
            agg = aggs.setdefault(name, {"cnt": 0, "stop": False})
            if agg["stop"] or agg["cnt"] >= VIEW_METRIC_HISTORY_SIZE:
                continue
            if name not in metrics:
                metrics[name] = MetricValue(status=metric.status, score=metric.score)
                agg["cnt"] = int(agg["cnt"]) + 1
                continue

            current = metrics[name]
            if metric.status == Status.PENDING and current.status == Status.HEALTHY:
                continue
            if current.status != metric.status:
                agg["stop"] = True
                continue
            current.score += metric.score
            agg["cnt"] = int(agg["cnt"]) + 1

    for name, metric in metrics.items():
        cnt = int(aggs[name]["cnt"])
        if cnt > 1:
            metric.score = metric.score / cnt

    return Inference(subject=subject, observers=[observer], metrics=metrics)


def infer_panorama(subject: str, reports: Iterable[ObserverReport]) -> Inference | None:
    """
    Majority vote across observers for one subject (InferPano).

    Reports are grouped by observer; each observer's recent observations are
    summarized via InferView, then statuses are majority-voted and scores averaged.
    """
    by_observer: dict[str, list[ObserverReport]] = defaultdict(list)
    for report in reports:
        if report.subject != subject:
            continue
        by_observer[report.observer].append(report)

    if not by_observer:
        return None

    workbook: dict[str, Inference] = {}
    for observer, observer_reports in by_observer.items():
        observer_reports.sort(key=lambda r: r.ts)
        # Collapse same-timestamp reports into one Observation.
        observations: list[Observation] = []
        bucket: dict[float, dict[str, MetricValue]] = defaultdict(dict)
        for report in observer_reports:
            bucket[report.ts][report.metric] = MetricValue(
                status=report.resolved_status(),
                score=report.score,
            )
        for ts in sorted(bucket):
            observations.append(Observation(metrics=bucket[ts], ts=ts))
        inference = _infer_view(observer, subject, observations)
        if inference is not None:
            workbook[observer] = inference

    if not workbook:
        return None

    stat_score: dict[str, float] = defaultdict(float)
    stat_cnt: dict[str, int] = defaultdict(int)
    status_hist: dict[str, dict[Status, int]] = defaultdict(lambda: defaultdict(int))

    for inference in workbook.values():
        for name, metric in inference.metrics.items():
            stat_score[name] += metric.score
            stat_cnt[name] += 1
            status_hist[name][metric.status] += 1

    metrics: dict[str, MetricValue] = {}
    for name, cnt in stat_cnt.items():
        maxcnt = 0
        maxstatus = Status.HEALTHY
        for status, votes in status_hist[name].items():
            if votes > maxcnt or (votes == maxcnt and status > maxstatus):
                maxcnt = votes
                maxstatus = status
        metrics[name] = MetricValue(
            status=maxstatus,
            score=stat_score[name] / cnt,
        )

    return Inference(
        subject=subject,
        observers=sorted(workbook.keys()),
        metrics=metrics,
    )
