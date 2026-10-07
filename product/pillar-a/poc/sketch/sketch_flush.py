from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ab_shared.dest import Dest
from ab_shared.ingest_source import IngestSource
from ab_shared.schema import validate
from ab_shared.season import HourOfWeekSeason, SeasonPolicy
from sketch.baseline import SeasonalBaseline
from sketch.buckets import Histogram, histogram_for_metric
from sketch.digest import TDigestAdapter
from sketch.metric_admit import admit_metric
from sketch.windowing import assignments


@dataclass
class SketchKey:
    tenant: str
    entity_id: str
    entity_type: str
    metric_id: str
    window: str
    season_key: str
    window_start: str
    window_end: str

    def as_tuple(self) -> tuple:
        return (
            self.tenant,
            self.entity_id,
            self.metric_id,
            self.window,
            self.season_key,
            self.window_start,
        )


@dataclass
class SketchState:
    digest: TDigestAdapter = field(default_factory=TDigestAdapter)
    hist: Histogram | None = None
    key: SketchKey | None = None


class SketchWriter:
    def __init__(self, season: SeasonPolicy | None = None) -> None:
        self.season = season or HourOfWeekSeason()
        self.states: dict[tuple, SketchState] = {}
        # Key includes window so 1m and 5m do not share one seasonal accumulator.
        self.baselines: dict[tuple[str, str, str, str], SeasonalBaseline] = {}
        self.rejects: list[tuple[dict, str]] = []

    def _baseline_key(
        self, tenant: str, entity_id: str, metric_id: str, window: str
    ) -> tuple[str, str, str, str]:
        return (tenant, entity_id, metric_id, window)

    def ingest(self, source: IngestSource) -> None:
        for rec in source.records():
            sample, reason = admit_metric(rec)
            if sample is None:
                if reason:
                    self.rejects.append((rec, reason))
                continue
            for slot in assignments(sample["ts"], season=self.season):
                key = SketchKey(
                    tenant=sample["tenant"],
                    entity_id=sample["entity_id"],
                    entity_type=sample["entity_type"],
                    metric_id=sample["metric_id"],
                    window=slot["window"],
                    season_key=slot["season_key"],
                    window_start=slot["window_start"],
                    window_end=slot["window_end"],
                )
                st = self.states.get(key.as_tuple())
                if st is None:
                    st = SketchState(hist=histogram_for_metric(sample["metric_id"]), key=key)
                    self.states[key.as_tuple()] = st
                st.digest.update(sample["value"])
                assert st.hist is not None
                st.hist.update(sample["value"])

    def build_row(self, state: SketchState) -> dict[str, Any]:
        assert state.key and state.hist
        key = state.key
        bkey = self._baseline_key(key.tenant, key.entity_id, key.metric_id, key.window)
        baseline_acc = self.baselines.setdefault(bkey, SeasonalBaseline())
        p50 = state.digest.quantile(0.50)
        p95 = state.digest.quantile(0.95)
        p99 = state.digest.quantile(0.99)
        baseline_acc.observe(key.season_key, p50, p95, p99)
        hist = baseline_acc.history[key.season_key]
        if len(hist) <= 1:
            expected = {
                "baseline_version": "seasonal_v1",
                "expected_p50": p50,
                "expected_p95": p95,
                "expected_p99": p99,
            }
        else:
            prior = hist[:-1]
            n = len(prior)
            expected = {
                "baseline_version": "seasonal_v1",
                "expected_p50": sum(r[0] for r in prior) / n,
                "expected_p95": sum(r[1] for r in prior) / n,
                "expected_p99": sum(r[2] for r in prior) / n,
            }
        row = {
            "schema_version": "sketch.v1",
            "tenant": key.tenant,
            "entity_id": key.entity_id,
            "entity_type": key.entity_type,
            "metric_id": key.metric_id,
            "window": key.window,
            "window_start": key.window_start,
            "window_end": key.window_end,
            "season_key": key.season_key,
            "sample_count": state.digest.sample_count(),
            "tdigest": state.digest.to_json_body(),
            "buckets": state.hist.to_json_body(),
            "baseline": expected,
        }
        validate("sketch_v1.schema.json", row)
        return row

    def flush(self, dest: Dest) -> list[dict[str, Any]]:
        rows = [self.build_row(st) for st in self.states.values()]
        payload = ("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else "")).encode("utf-8")
        dest.put("history", "sketches.jsonl", payload)
        return rows

    def refresh_baselines(self, dest: Dest | None = None) -> None:
        """E5 Maintain stub (A side).

        If ``dest`` is provided, rebuild seasonal accumulators from durable
        ``history/sketches.jsonl`` (preferred). Otherwise seed empty season
        slots from in-memory live window digests.
        """
        if dest is not None:
            from sketch.maintain import refresh_seasonal_baselines

            refresh_seasonal_baselines(self, dest)
            return
        for st in self.states.values():
            assert st.key
            key = st.key
            bkey = self._baseline_key(key.tenant, key.entity_id, key.metric_id, key.window)
            acc = self.baselines.setdefault(bkey, SeasonalBaseline())
            if not acc.history.get(key.season_key):
                acc.observe(
                    key.season_key,
                    st.digest.quantile(0.50),
                    st.digest.quantile(0.95),
                    st.digest.quantile(0.99),
                )
