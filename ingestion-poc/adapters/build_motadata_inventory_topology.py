#!/usr/bin/env python3
"""Build Motadata inventory topology from CI-bind + span service→host edges.

Writes:
  datasets/ingest_samples/motadata-ingest/topology.json
  (optional) refresh each incidents/*/topology.json with a relevant subgraph
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO / "datasets" / "ingest_samples" / "motadata-ingest"
DEFAULT_BIND = OUT_ROOT / "ci_bind.json"
DEFAULT_SPANS = REPO / "datasets" / "ingest_samples" / "jsonl_resolved" / "span.jsonl"
DEFAULT_OUT = OUT_ROOT / "topology.json"

# Motadata plugin_id → CI type (best-effort).
_PLUGIN_TYPE = {
    88: "Host",
    157: "NetworkDevice",
    181: "Host",
    199: "Host",
    426: "Host",
    362: "Host",
}


def _node(ci_id: str, ci_type: str, **extra: Any) -> dict[str, Any]:
    return {"id": ci_id, "type": ci_type, "name": ci_id, **extra}


def load_ci_nodes(bind_path: Path) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    if not bind_path.is_file():
        return nodes
    doc = json.loads(bind_path.read_text(encoding="utf-8"))
    for mid, entry in (doc.get("monitors") or {}).items():
        ci_id = str(entry.get("ci_id") or f"monitor-{mid}").strip()
        if not ci_id:
            continue
        plugin = entry.get("plugin_id")
        ci_type = _PLUGIN_TYPE.get(int(plugin) if plugin is not None else -1, "Host")
        # Prefer explicit NetworkDevice naming cues
        low = ci_id.lower()
        if any(tok in low for tok in ("switch", "dlink", "router", "ospf", "cisco")):
            ci_type = "NetworkDevice"
        nodes[ci_id] = _node(
            ci_id,
            ci_type,
            monitor_id=str(mid),
            plugin_id=plugin,
            bind_source=entry.get("bind_source"),
        )
    return nodes


def scan_span_edges(
    span_path: Path,
    *,
    limit: int | None = 300_000,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]], Counter]:
    """Return (service_nodes, runs_on edges, pair counts)."""
    services: dict[str, dict[str, Any]] = {}
    pair_counts: Counter = Counter()
    if not span_path.is_file():
        return services, [], pair_counts

    n = 0
    with span_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            if limit is not None and n > limit:
                break
            row = json.loads(line)
            fields = row.get("fields") or {}
            host = fields.get("host_name")
            svc = row.get("service_span_service_name")
            if not svc:
                continue
            svc = str(svc).strip()
            services.setdefault(
                svc,
                _node(
                    svc,
                    "Service",
                    service_type=row.get("service_span_service_type"),
                ),
            )
            if host:
                host = str(host).strip()
                pair_counts[(svc, host)] += 1

    edges: list[dict[str, str]] = []
    for (svc, host), _count in sorted(pair_counts.items(), key=lambda x: -x[1]):
        edges.append({"from": svc, "to": host, "relation": "runs_on"})
    return services, edges, pair_counts


def build_inventory(
    *,
    bind_path: Path = DEFAULT_BIND,
    span_path: Path = DEFAULT_SPANS,
    span_limit: int | None = 300_000,
) -> dict[str, Any]:
    host_nodes = load_ci_nodes(bind_path)
    services, runs_on, pair_counts = scan_span_edges(span_path, limit=span_limit)

    # Ensure APM hosts from spans exist even if missing from bind.
    for _svc, host in pair_counts:
        host_nodes.setdefault(host, _node(host, "Host", bind_source="span_host_name"))

    nodes = list(host_nodes.values()) + list(services.values())

    edges: list[dict[str, str]] = list(runs_on)
    # Known Motadata APM dependency (ProductCatalog → hibernate) when both present.
    if "ProductCatalog_dotnet." in services and "hibernatewithmysql" in services:
        edges.append(
            {
                "from": "ProductCatalog_dotnet.",
                "to": "hibernatewithmysql",
                "relation": "depends_on",
            }
        )

    return {
        "version": "1.0.0",
        "source": "motadata_inventory",
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "host_count": len(host_nodes),
            "service_count": len(services),
            "span_service_host_pairs": {
                f"{a}|{b}": c for (a, b), c in pair_counts.most_common(20)
            },
        },
        "note": (
            "Inventory from Motadata ci_bind monitors + span fields.host_name→service "
            "runs_on edges. Not a full Motadata CMDB export."
        ),
    }


def subgraph_for_cis(inventory: dict[str, Any], ci_ids: set[str]) -> dict[str, Any]:
    """Keep nodes in ci_ids plus one-hop upstream (edge.to) / downstream neighbors."""
    keep = set(ci_ids)
    for e in inventory.get("edges") or []:
        if e.get("from") in ci_ids or e.get("to") in ci_ids:
            keep.add(e["from"])
            keep.add(e["to"])
    nodes = [n for n in inventory.get("nodes") or [] if n["id"] in keep]
    edges = [
        e
        for e in inventory.get("edges") or []
        if e.get("from") in keep and e.get("to") in keep
    ]
    return {
        "version": inventory.get("version", "1.0.0"),
        "source": "motadata_inventory_subgraph",
        "nodes": nodes,
        "edges": edges,
        "note": f"Subgraph for CIs {sorted(ci_ids)}",
        "parent_stats": inventory.get("stats"),
    }


def refresh_incident_topologies(inventory: dict[str, Any], incidents_dir: Path) -> list[str]:
    updated: list[str] = []
    if not incidents_dir.is_dir():
        return updated
    for pack in sorted(incidents_dir.iterdir()):
        if not pack.is_dir() or not (pack / "ground_truth.json").is_file():
            continue
        gt = json.loads((pack / "ground_truth.json").read_text(encoding="utf-8"))
        seed_path = pack / "symptom_seed.json"
        cis = {gt.get("root_ci")}
        if seed_path.is_file():
            seed = json.loads(seed_path.read_text(encoding="utf-8"))
            if seed.get("ci"):
                cis.add(seed["ci"])
        for blast in gt.get("blast_radius") or []:
            cis.add(blast)
        cis.discard(None)
        cis.discard("")
        # Always include APM host if any service in subgraph
        sub = subgraph_for_cis(inventory, set(cis))
        # Single-host infra packs: ensure the host node exists even with no edges
        if not sub["nodes"] and cis:
            for ci in cis:
                sub["nodes"].append(_node(str(ci), "Host"))
        (pack / "topology.json").write_text(json.dumps(sub, indent=2) + "\n")
        updated.append(pack.name)
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Motadata inventory topology")
    parser.add_argument("--bind", type=Path, default=DEFAULT_BIND)
    parser.add_argument("--spans", type=Path, default=DEFAULT_SPANS)
    parser.add_argument("--span-limit", type=int, default=300_000)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--refresh-incidents",
        action="store_true",
        help="Rewrite incidents/*/topology.json as inventory subgraphs",
    )
    args = parser.parse_args(argv)

    inventory = build_inventory(
        bind_path=args.bind.resolve(),
        span_path=args.spans.resolve(),
        span_limit=args.span_limit if args.span_limit > 0 else None,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(inventory, indent=2) + "\n")
    print(
        f"wrote {args.out} nodes={inventory['stats']['node_count']} "
        f"edges={inventory['stats']['edge_count']}"
    )

    if args.refresh_incidents:
        updated = refresh_incident_topologies(inventory, OUT_ROOT / "incidents")
        print(f"refreshed incidents: {', '.join(updated) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
