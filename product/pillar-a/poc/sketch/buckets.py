from __future__ import annotations

BUCKET_SCHEMAS: dict[str, list[float]] = {
    "latency_v1": [0, 50, 100, 200, 500, 1000, 2000],
    "cpu_v1": [0, 20, 40, 60, 80, 100],
}

METRIC_BUCKET = {
    "request.latency_ms": "latency_v1",
    "cpu.utilization_pct": "cpu_v1",
}


class Histogram:
    def __init__(self, schema_version: str) -> None:
        if schema_version not in BUCKET_SCHEMAS:
            raise ValueError(schema_version)
        self.schema_version = schema_version
        self.bounds = list(BUCKET_SCHEMAS[schema_version])
        self.counts = [0] * (len(self.bounds) - 1)

    def update(self, x: float) -> None:
        for i in range(len(self.counts)):
            lo, hi = self.bounds[i], self.bounds[i + 1]
            if lo <= x < hi or (i == len(self.counts) - 1 and x == hi):
                self.counts[i] += 1
                return
        # above max → last bucket
        self.counts[-1] += 1

    def to_json_body(self) -> dict:
        return {
            "bucket_schema_version": self.schema_version,
            "bounds": self.bounds,
            "counts": list(self.counts),
        }


def histogram_for_metric(metric_id: str) -> Histogram:
    return Histogram(METRIC_BUCKET[metric_id])
