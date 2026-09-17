"""Lab CLI: flush topo stream → map/*.json(l) (Pillar B only)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ab_shared.dest import FileDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import FIXTURES, POC_ROOT
from graph.graph_writer import GraphWriter


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pillar B GraphWriter flush (lab)")
    p.add_argument(
        "--seed",
        type=Path,
        default=FIXTURES / "topology.seed.json",
        help="Seed topology JSON (nodes + declared edges)",
    )
    p.add_argument(
        "--stream",
        type=Path,
        default=FIXTURES / "stream.resolved.jsonl",
        help="Topo-only ingest.v1 JSONL (metric_sample lines are silently skipped)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=POC_ROOT / "out",
        help="FileDest root (writes <tenant>/map/graph_snapshot.json, nodes.jsonl, edges.jsonl)",
    )
    p.add_argument("--tenant", default="default")
    p.add_argument("--version", default="1", help="GraphSnapshot version for initial flush")
    p.add_argument(
        "--maintain-validity",
        action="store_true",
        help="After flush, run E5 graph validity stub and republish snapshot",
    )
    p.add_argument(
        "--as-of",
        default="2026-08-20T04:00:00Z",
        help="Maintain cutoff timestamp (RFC3339 Z)",
    )
    p.add_argument(
        "--snapshot-version-after-maintain",
        default="2",
        help="GraphSnapshot version after maintain + second flush",
    )
    args = p.parse_args(argv)

    writer = GraphWriter(tenant=args.tenant)
    if args.seed and args.seed.exists():
        writer.load_seed(args.seed)
    writer.ingest(JsonlIngestSource(args.stream))
    dest = FileDest(args.out, tenant=args.tenant)
    snapshot = writer.flush(dest, version=args.version)
    maintain_stats: dict[str, int] = {}
    if args.maintain_validity:
        maintain_stats = writer.maintain_validity(args.as_of)
        snapshot = writer.flush(dest, version=args.snapshot_version_after_maintain)

    map_dir = args.out / args.tenant / "map"
    print(
        f"flushed graph_snapshot.v1 version={snapshot['version']} "
        f"nodes={len(snapshot['nodes'])} edges={len(snapshot['edges'])} → {map_dir}"
    )
    print(f"rejects={len(writer.rejects)} maintain={maintain_stats or 'skipped'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
