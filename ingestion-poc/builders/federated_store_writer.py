#!/usr/bin/env python3
"""N4 — Federated-first store writer from F1 structural (+ optional speed) feeds.

Writes file-backed metric slice + topology edges + Dragonfly-key stub (no Redis
required). Timing recorded in ``store_meta.json``.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_ts(ts: str) -> str:
    """Normalize to ISO-8601 Z."""
    if not ts:
        return ts
    if ts.endswith("Z"):
        return ts
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ts


def _edges_from_topology(topology: dict[str, Any] | None) -> list[dict[str, str]]:
    if not topology:
        return []
    edges = []
    for e in topology.get("edges") or []:
        edges.append(
            {
                "src": e["from"],
                "dst": e["to"],
                "relation": e.get("relation") or "",
            }
        )
    return edges


def write_federated_stores(
    *,
    structural_jsonl: Path,
    out_dir: Path,
    topology: dict[str, Any] | None = None,
    speed_jsonl: Path | None = None,
) -> dict[str, Any]:
    """Materialize Federated-shaped artifacts under ``out_dir``."""
    t0 = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = out_dir / "metric_slice.jsonl"
    entities: set[str] = set()
    metric_points = 0
    events = 0
    spans = 0

    with structural_jsonl.open() as src, metrics_path.open("w") as metrics_fh:
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cls = row.get("fact_kind")
            ci = str(row.get("ci_id") or "")
            if ci:
                entities.add(ci)
            if cls == "metric_sample":
                value = row.get("value")
                if value is None:
                    continue
                point = {
                    "entity_id": ci,
                    "metric_name": row.get("name"),
                    "timestamp": _parse_ts(row.get("ts") or ""),
                    "value": float(value),
                    "threshold": row.get("threshold"),
                    "ci_type": row.get("ci_type"),
                    "labels": row.get("labels") or {},
                }
                metrics_fh.write(json.dumps(point, separators=(",", ":")) + "\n")
                metric_points += 1
            elif cls == "event":
                events += 1
            elif cls == "trace_span":
                spans += 1

    edges = _edges_from_topology(topology)
    edges_path = out_dir / "topology_edges.json"
    edges_path.write_text(
        json.dumps({"edges": edges, "entity_count": len(entities)}, indent=2) + "\n"
    )
    if topology is not None:
        (out_dir / "topology.json").write_text(json.dumps(topology, indent=2) + "\n")

    # Dragonfly / speed-tier stub: materialize Nezha-shaped key records as JSONL
    # (no live Redis). Ready for a later redis writer.
    speed_out = out_dir / "speed_tier_stub.jsonl"
    speed_keys = 0
    speed_src = speed_jsonl if speed_jsonl and speed_jsonl.is_file() else None
    with speed_out.open("w") as speed_fh:
        if speed_src:
            for line in speed_src.open():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                labels = row.get("labels") or {}
                tenant = row.get("tenant") or "default"
                trace_id = labels.get("trace_id") or row.get("name") or "no-trace"
                span_id = labels.get("span_id") or ""
                service = str(row.get("ci_id") or "")
                event_type = str(row.get("name") or row.get("fact_kind") or "event")
                ts = row.get("ts") or ""
                try:
                    epoch = datetime.fromisoformat(
                        ts.replace("Z", "+00:00")
                    ).timestamp()
                except ValueError:
                    epoch = 0.0
                minute = int(epoch // 60) if epoch else 0
                pattern = f"{service}→{event_type}"
                stub = {
                    "tg_key": f"tg:{tenant}:{trace_id}:{minute}",
                    "pc_key": f"pc:fault-suffering:{tenant}:stub",
                    "member": f"{span_id}:{service}:{event_type}",
                    "timestamp": epoch,
                    "pattern": pattern,
                    "source_fact_kind": row.get("fact_kind"),
                }
                speed_fh.write(json.dumps(stub, separators=(",", ":")) + "\n")
                speed_keys += 1

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    meta = {
        "schema_version": "federated_store.v1",
        "writer": "federated_store_writer",
        "structural_source": str(structural_jsonl),
        "out_dir": str(out_dir),
        "metric_points": metric_points,
        "entities": len(entities),
        "topology_edges": len(edges),
        "structural_events_seen": events,
        "structural_spans_seen": spans,
        "speed_stub_keys": speed_keys,
        "dragonfly": "file_stub",
        "write_latency_ms": round(elapsed_ms, 3),
        "artifacts": [
            "metric_slice.jsonl",
            "topology_edges.json",
            "speed_tier_stub.jsonl",
            "store_meta.json",
        ],
    }
    (out_dir / "store_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="N4 Federated store writer")
    parser.add_argument(
        "--f1-dir",
        type=Path,
        required=True,
        help="F1 smoke output dir (expects structural/stream.jsonl)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Default: <f1-dir>/federated_stores",
    )
    args = parser.parse_args(argv)
    f1 = args.f1_dir.resolve()
    structural = f1 / "structural" / "stream.jsonl"
    if not structural.is_file():
        raise SystemExit(f"Missing structural feed: {structural}")
    topo = None
    topo_path = f1 / "topology.json"
    if topo_path.is_file():
        topo = json.loads(topo_path.read_text())
    out = (args.out_dir or (f1 / "federated_stores")).resolve()
    meta = write_federated_stores(
        structural_jsonl=structural,
        out_dir=out,
        topology=topo,
        speed_jsonl=f1 / "speed_tier" / "feed.jsonl",
    )
    print(json.dumps(meta, indent=2))
    print(f"\nN4 OK → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
