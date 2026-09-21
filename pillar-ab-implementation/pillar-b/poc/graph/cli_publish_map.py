"""Lab entry: one-shot CLI that stands in for a Topology writer.

Wires sample-estate files → GraphWriter → FileDest ``map/``.
Product intent replaces this process with a long-running Topology writer;
the GraphWriter verbs stay the same.

Invoke via ``make publish-map`` from ``poc/``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ab_shared.dest import FileDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE, POC_ROOT
from graph.graph_writer import GraphWriter


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Pillar B GraphWriter lab publish: bootstrap + topo stream → map/"
    )
    p.add_argument(
        "--bootstrap",
        type=Path,
        default=SAMPLE_ESTATE / "topology.bootstrap.json",
        help="Declared estate bootstrap JSON (nodes + edges).",
    )
    p.add_argument(
        "--stream",
        type=Path,
        default=SAMPLE_ESTATE / "stream.resolved.jsonl",
        help="Topo-only ingest.v1 JSONL (non-topo signal_class lines are silent NOOP)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=POC_ROOT / "out",
        help="FileDest root (writes <tenant>/map/graph_snapshot.json, nodes.jsonl, edges.jsonl)",
    )
    p.add_argument("--tenant", default="default")
    p.add_argument("--version", default="1", help="GraphSnapshot version for initial publish_map")
    p.add_argument(
        "--maintain-map",
        "--maintain-validity",
        dest="maintain_map",
        action="store_true",
        help="After publish_map, run E5 maintain_map and republish snapshot",
    )
    p.add_argument(
        "--as-of",
        default="2026-08-20T04:00:00Z",
        help="Maintain cutoff timestamp (RFC3339 Z)",
    )
    p.add_argument(
        "--snapshot-version-after-maintain",
        default="2",
        help="GraphSnapshot version after maintain_map + second publish_map",
    )
    args = p.parse_args(argv)

    writer = GraphWriter(tenant=args.tenant)
    if args.bootstrap and args.bootstrap.exists():
        writer.load_estate_bootstrap(args.bootstrap)
    writer.write_topo_stream(JsonlIngestSource(args.stream))
    dest = FileDest(args.out, tenant=args.tenant)
    snapshot = writer.publish_map(dest, version=args.version)
    maintain_stats: dict[str, int] = {}
    if args.maintain_map:
        maintain_stats = writer.maintain_map(args.as_of)
        snapshot = writer.publish_map(dest, version=args.snapshot_version_after_maintain)

    map_dir = args.out / args.tenant / "map"
    print(
        f"published graph_snapshot.v1 version={snapshot['version']} "
        f"nodes={len(snapshot['nodes'])} edges={len(snapshot['edges'])} → {map_dir}"
    )
    print(f"rejects={len(writer.rejects)} maintain={maintain_stats or 'skipped'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
