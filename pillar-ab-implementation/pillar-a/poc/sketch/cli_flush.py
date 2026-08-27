"""Lab CLI: flush metric stream → history/sketches.jsonl (Pillar A only)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ab_shared.dest import FileDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import FIXTURES, POC_ROOT
from ab_shared.season import HourOfWeekSeason
from sketch.maintain import refresh_seasonal_baselines
from sketch.sketch_flush import SketchWriter


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pillar A SketchWriter flush (lab)")
    p.add_argument(
        "--stream",
        type=Path,
        default=FIXTURES / "stream.resolved.jsonl",
        help="Metric-only ingest.v1 JSONL",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=POC_ROOT / "out",
        help="FileDest root (writes <tenant>/history/sketches.jsonl)",
    )
    p.add_argument("--tenant", default="default")
    p.add_argument(
        "--refresh-baselines",
        action="store_true",
        help="After flush, rebuild seasonal baselines from Dest (E5 stub)",
    )
    args = p.parse_args(argv)

    writer = SketchWriter(season=HourOfWeekSeason())
    writer.ingest(JsonlIngestSource(args.stream))
    dest = FileDest(args.out, tenant=args.tenant)
    rows = writer.flush(dest)
    if args.refresh_baselines:
        refresh_seasonal_baselines(writer, dest)
    print(f"flushed {len(rows)} sketch.v1 rows → {args.out / args.tenant / 'history' / 'sketches.jsonl'}")
    print(f"rejects={len(writer.rejects)} baseline_keys={len(writer.baselines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
