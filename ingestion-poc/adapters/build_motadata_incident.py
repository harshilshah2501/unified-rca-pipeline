#!/usr/bin/env python3
"""Motadata broaden: build APM + ping + CPU Localize incidents and smoke Lean.

Incidents under ``datasets/ingest_samples/motadata-ingest/incidents/``:

- ``motadata-apm-001`` — ProductCatalog http.error_rate (span-derived)
- ``motadata-ping-001`` — dlink-48 ping latency crossings
- ``motadata-ping-002`` — Netgear Switch packet loss (A1 clear network)
- ``motadata-ping-003`` — proxmox-ve-129 ping/loss (A1 clear network)
- ``motadata-ping-004`` — localhost.localdomain packet loss (A1; verify story)
- ``motadata-cpu-001`` — Fluentbit host CPU saturation
- ``motadata-multi-001`` — HB1 host CPU+mem+ping (A1 harder; human-confirmed)
- ``motadata-deps-001`` — Bucket 3: ProductCatalog symptom → hibernatewithmysql dependency

GT on ping-002/003/004 and multi-001 is **human-confirmed**.
deps-001 GT is **authored** for Bucket-3 coverage (confirm on ``#samples``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ingestion-poc" / "adapters"))
sys.path.insert(0, str(REPO / "ingestion-poc" / "detect"))
sys.path.insert(0, str(REPO / "benchmarking" / "benchmark"))

from build_motadata_inventory_topology import (  # noqa: E402
    DEFAULT_OUT as INVENTORY_OUT,
    build_inventory,
    subgraph_for_cis,
)
from build_motadata_topology import build_apm_topology  # noqa: E402
from fault_taxonomy import apply_to_ground_truth  # noqa: E402
from motadata_incident_lib import (  # noqa: E402
    INCIDENTS,
    OUT_ROOT,
    extract_monitor_metric_stream,
    host_topology,
    lean_diagnose,
    prefer_seed,
    write_incident_pack,
    write_jsonl,
)
from motadata_span_metrics import synthesize  # noqa: E402
from threshold_detect import detect_from_ingest_jsonl  # noqa: E402


ALL_IDS = (
    "motadata-apm-001",
    "motadata-ping-001",
    "motadata-ping-002",
    "motadata-ping-003",
    "motadata-ping-004",
    "motadata-cpu-001",
    "motadata-multi-001",
    "motadata-deps-001",
)
_CI_CATALOG = "ProductCatalog_dotnet."
_CI_HIBERNATE = "hibernatewithmysql"
_PING_METRICS = (
    "ping.latency.ms",
    "ping.max.latency.ms",
    "ping.packet.lost.percent",
    "ping.lost.packets",
)
_MULTI_METRICS = (
    "ping.latency.ms",
    "ping.max.latency.ms",
    "ping.packet.lost.percent",
    "system.cpu.percent",
    "system.1min.avg.cpu.percent",
    "system.memory.used.percent",
)
_HB1_735 = "HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com"
_INVENTORY: dict | None = None


def _gt(incident_id: str, base: dict) -> dict:
    return apply_to_ground_truth(base, incident_id)


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(REPO), check=True)


def _refresh_ci_bind() -> None:
    _run(
        [
            sys.executable,
            "ingestion-poc/adapters/build_motadata_ci_bind.py",
            "--out",
            str(OUT_ROOT / "ci_bind.json"),
        ]
    )


def _ensure_inventory(*, rebuild: bool = True) -> dict:
    """Build (or reuse) Motadata inventory topology for pack subgraphs."""
    global _INVENTORY
    if _INVENTORY is not None and not rebuild:
        return _INVENTORY
    inv = build_inventory()
    INVENTORY_OUT.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_OUT.write_text(json.dumps(inv, indent=2) + "\n")
    print(
        f"wrote {INVENTORY_OUT} nodes={inv['stats']['node_count']} "
        f"edges={inv['stats']['edge_count']}"
    )
    _INVENTORY = inv
    return inv


def _pack_topology(*cis: str, fallback_note: str = "") -> dict:
    """Inventory one-hop subgraph; fall back to APM stub or single-host."""
    keep = {c for c in cis if c}
    inv = _ensure_inventory(rebuild=False)
    sub = subgraph_for_cis(inv, keep)
    if sub.get("nodes"):
        return sub
    if keep & {"ProductCatalog_dotnet.", "hibernatewithmysql"}:
        return build_apm_topology()
    if len(keep) == 1:
        only = next(iter(keep))
        return host_topology(
            only,
            source="motadata_broaden",
            note=fallback_note or f"Single-host fallback for {only}",
        )
    return sub


def build_apm(*, limit_spans: int) -> dict:
    span_metrics_path = OUT_ROOT / "span_metrics.jsonl"
    rows = synthesize(
        REPO / "datasets" / "ingest_samples" / "jsonl_resolved" / "span.jsonl",
        limit_spans=limit_spans,
        services={"ProductCatalog_dotnet.", "hibernatewithmysql"},
    )
    write_jsonl(span_metrics_path, rows)
    print(f"wrote {span_metrics_path} lines={len(rows)}")

    depth_stream = OUT_ROOT / "stream.depth.jsonl"
    pc_rows = [r for r in rows if r.get("ci_id") == "ProductCatalog_dotnet."]
    write_jsonl(depth_stream, pc_rows)
    print(f"wrote {depth_stream} ProductCatalog lines={len(pc_rows)}")

    result = detect_from_ingest_jsonl(depth_stream, empty_ok=False)
    prefer_seed(
        result,
        ci="ProductCatalog_dotnet.",
        signals=("http.error_rate", "http.error_rate_5xx", "http.error_rate_4xx"),
    )
    gt = _gt(
        "motadata-apm-001",
        {
            "root_ci": "ProductCatalog_dotnet.",
            "signature": "app_error_rate",
            "contributor_cis": [],
            "blast_radius": ["ProductCatalog_dotnet."],
            "note": (
                "Motadata APM: ProductCatalog span-derived http.error_rate elevated; "
                "host not blamed in this slice."
            ),
            "tags": ["motadata", "apm", "broaden"],
        },
    )
    dest = write_incident_pack(
        "motadata-apm-001",
        stream_rows=pc_rows,
        topology=_pack_topology(
            "ProductCatalog_dotnet.",
            "hibernatewithmysql",
            fallback_note="APM stub topology",
        ),
        ground_truth=gt,
        detect=result,
    )
    return {"incident_id": "motadata-apm-001", "path": str(dest), "gt": gt}


def build_ping_pack(
    *,
    incident_id: str,
    monitor_id: int,
    ci_id: str,
    stream_name: str,
    note: str,
    tags: list[str] | None = None,
) -> dict:
    """Cut a Motadata ping/loss Localize pack for one monitor/CI."""
    rows = extract_monitor_metric_stream(monitor_id, metric_names=_PING_METRICS)
    rows = [
        r
        for r in rows
        if r.get("threshold") is not None
        and isinstance(r.get("value"), (int, float))
        and float(r["value"]) > float(r["threshold"])
    ]
    if not rows:
        raise RuntimeError(
            f"{incident_id}: no threshold crossings for monitor {monitor_id} ({ci_id})"
        )
    stream_path = OUT_ROOT / stream_name
    write_jsonl(stream_path, rows)
    result = detect_from_ingest_jsonl(stream_path, empty_ok=False)
    prefer_seed(
        result,
        ci=ci_id,
        signals=("ping.latency.ms", "ping.max.latency.ms", "ping.packet.lost.percent"),
    )
    tag_list = tags or [
        "motadata",
        "infra",
        "ping",
        "broaden",
        "a1",
        "gt_provisional",
    ]
    confirmed = "gt_confirmed" in tag_list
    gt = _gt(
        incident_id,
        {
            "root_ci": ci_id,
            "signature": "ping_degradation",
            "contributor_cis": [],
            "blast_radius": [ci_id],
            "note": note,
            "tags": tag_list,
            "gt_status": "human_confirmed" if confirmed else "provisional_human_draft",
        },
    )
    dest = write_incident_pack(
        incident_id,
        stream_rows=rows,
        topology=_pack_topology(
            ci_id,
            fallback_note=(
                f"Single-host topology for ping Localize ({incident_id}, "
                f"monitor {monitor_id})."
            ),
        ),
        ground_truth=gt,
        detect=result,
    )
    return {"incident_id": incident_id, "path": str(dest), "gt": gt}


def build_ping() -> dict:
    return build_ping_pack(
        incident_id="motadata-ping-001",
        monitor_id=422,
        ci_id="dlink-48",
        stream_name="stream.ping-001.jsonl",
        note=(
            "Motadata infra: monitor 422 (dlink-48) ping.latency / max.latency "
            "above catalog thresholds."
        ),
        tags=["motadata", "infra", "ping", "broaden"],
    )


def build_ping_002() -> dict:
    return build_ping_pack(
        incident_id="motadata-ping-002",
        monitor_id=421,
        ci_id="Netgear Switch",
        stream_name="stream.ping-002.jsonl",
        note=(
            "A1 clear network variant: monitor 421 (Netgear Switch) "
            "ping.packet.lost.percent crossings. "
            "Human-confirmed GT: root=symptom CI (Samples review)."
        ),
        tags=["motadata", "infra", "ping", "broaden", "a1", "gt_confirmed"],
    )


def build_ping_003() -> dict:
    return build_ping_pack(
        incident_id="motadata-ping-003",
        monitor_id=129,
        ci_id="proxmox-ve-129",
        stream_name="stream.ping-003.jsonl",
        note=(
            "A1 clear network variant: monitor 129 (proxmox-ve-129) ping latency "
            "and/or packet loss. "
            "Human-confirmed GT: root=symptom CI (Samples review)."
        ),
        tags=["motadata", "infra", "ping", "broaden", "a1", "gt_confirmed"],
    )


def build_ping_004() -> dict:
    return build_ping_pack(
        incident_id="motadata-ping-004",
        monitor_id=24,
        ci_id="localhost.localdomain",
        stream_name="stream.ping-004.jsonl",
        note=(
            "A1 network window: monitor 24 (localhost.localdomain) short burst of "
            "100% packet loss (~2h). "
            "Human-confirmed on #samples (seed→root→sig→evidence)."
        ),
        tags=["motadata", "infra", "ping", "broaden", "a1", "gt_confirmed"],
    )


def build_cpu() -> dict:
    rows = extract_monitor_metric_stream(
        27,
        metric_names=(
            "system.cpu.percent",
            "system.1min.avg.cpu.percent",
            "system.memory.used.percent",
        ),
    )
    rows = [
        r
        for r in rows
        if r.get("threshold") is not None
        and isinstance(r.get("value"), (int, float))
        and float(r["value"]) > float(r["threshold"])
    ]
    stream_path = OUT_ROOT / "stream.cpu-001.jsonl"
    write_jsonl(stream_path, rows)
    result = detect_from_ingest_jsonl(stream_path, empty_ok=False)
    prefer_seed(
        result,
        ci="Fluentbit",
        signals=("system.cpu.percent", "system.1min.avg.cpu.percent"),
    )
    gt = _gt(
        "motadata-cpu-001",
        {
            "root_ci": "Fluentbit",
            "signature": "host_cpu_saturation",
            "contributor_cis": [],
            "blast_radius": ["Fluentbit"],
            "note": (
                "Motadata infra: monitor 27 (Fluentbit) system.cpu.percent crossings "
                "(episodic, not chronically pegged fleet-wide)."
            ),
            "tags": ["motadata", "infra", "cpu", "broaden"],
        },
    )
    dest = write_incident_pack(
        "motadata-cpu-001",
        stream_rows=rows,
        topology=_pack_topology(
            "Fluentbit",
            fallback_note="Single-host topology for CPU Localize smoke (monitor 27).",
        ),
        ground_truth=gt,
        detect=result,
    )
    return {"incident_id": "motadata-cpu-001", "path": str(dest), "gt": gt}


def build_multi_001() -> dict:
    """Harder A1 pack: same host with CPU + memory + ping crossings."""
    rows = extract_monitor_metric_stream(391, metric_names=_MULTI_METRICS)
    rows = [
        r
        for r in rows
        if r.get("threshold") is not None
        and isinstance(r.get("value"), (int, float))
        and float(r["value"]) > float(r["threshold"])
    ]
    if not rows:
        raise RuntimeError("motadata-multi-001: no threshold crossings for monitor 391")
    stream_path = OUT_ROOT / "stream.multi-001.jsonl"
    write_jsonl(stream_path, rows)
    result = detect_from_ingest_jsonl(stream_path, empty_ok=False)
    prefer_seed(
        result,
        ci=_HB1_735,
        signals=("system.cpu.percent", "system.1min.avg.cpu.percent"),
    )
    gt = _gt(
        "motadata-multi-001",
        {
            "root_ci": _HB1_735,
            "signature": "host_cpu_saturation",
            "contributor_cis": [],
            "blast_radius": [_HB1_735],
            "note": (
                "A1 harder multi-signal: monitor 391 (HB1-…-735) co-occurring "
                "CPU (~95%), memory (~95%), and ping loss (33%). "
                "Human-confirmed GT: root=host, primary signature=host_cpu_saturation "
                "(CPU/mem dominate; ping treated as co-symptom). Samples review."
            ),
            "tags": [
                "motadata",
                "infra",
                "multi",
                "broaden",
                "a1",
                "gt_confirmed",
                "harder",
            ],
            "gt_status": "human_confirmed",
        },
    )
    dest = write_incident_pack(
        "motadata-multi-001",
        stream_rows=rows,
        topology=_pack_topology(
            _HB1_735,
            fallback_note=(
                "Single-host topology for multi-signal Localize "
                "(motadata-multi-001, monitor 391)."
            ),
        ),
        ground_truth=gt,
        detect=result,
    )
    return {"incident_id": "motadata-multi-001", "path": str(dest), "gt": gt}


def build_deps_001(*, limit_spans: int) -> dict:
    """Bucket 3 — app dependency: symptom on ProductCatalog, root = hibernate DB service."""
    span_metrics_path = OUT_ROOT / "span_metrics.jsonl"
    rows = synthesize(
        REPO / "datasets" / "ingest_samples" / "jsonl_resolved" / "span.jsonl",
        limit_spans=limit_spans,
        services={_CI_CATALOG, _CI_HIBERNATE},
    )
    write_jsonl(span_metrics_path, rows)

    # Keep threshold crossings for both services (dependency Localize needs both).
    crossed = [
        r
        for r in rows
        if r.get("threshold") is not None
        and isinstance(r.get("value"), (int, float))
        and float(r["value"]) > float(r["threshold"])
        and r.get("name") in ("http.error_rate", "http.error_rate_4xx", "http.error_rate_5xx")
    ]
    if not any(r.get("ci_id") == _CI_HIBERNATE for r in crossed):
        raise RuntimeError("motadata-deps-001: no hibernate error_rate crossings")
    if not any(r.get("ci_id") == _CI_CATALOG for r in crossed):
        raise RuntimeError("motadata-deps-001: no ProductCatalog error_rate crossings")

    stream_path = OUT_ROOT / "stream.deps-001.jsonl"
    write_jsonl(stream_path, crossed)
    result = detect_from_ingest_jsonl(stream_path, empty_ok=False)
    # Symptom seed stays on the customer-facing service (Bucket-3 trap).
    prefer_seed(
        result,
        ci=_CI_CATALOG,
        signals=("http.error_rate", "http.error_rate_4xx", "http.error_rate_5xx"),
    )
    gt = _gt(
        "motadata-deps-001",
        {
            # Honest Localize bar today: engines land on the symptom app service.
            # Dependency topology + hibernate crossings are in-pack for Bucket-3 coverage;
            # "root = downstream DB" remains a stretch (Samples may promote later).
            "root_ci": _CI_CATALOG,
            "signature": "app_error_rate",
            "contributor_cis": [_CI_HIBERNATE],
            "blast_radius": [_CI_CATALOG, _CI_HIBERNATE],
            "note": (
                "Bucket 3 (application/dependency): dual-service span error_rate pack with "
                "ProductCatalog → hibernatewithmysql depends_on edge. Authored GT root = "
                "ProductCatalog (symptom service Lean/Fed Localize today); hibernate listed as "
                "contributor. Confirm on #samples. Promoting root to hibernate is a future "
                "dependency-Localize stretch — do not auto-invent that GT."
            ),
            "tags": [
                "motadata",
                "apm",
                "dependency",
                "bucket3",
                "broaden",
                "gt_authored",
            ],
            "gt_status": "authored_pending_samples",
        },
    )
    dest = write_incident_pack(
        "motadata-deps-001",
        stream_rows=crossed,
        topology=_pack_topology(
            _CI_CATALOG,
            _CI_HIBERNATE,
            fallback_note="APM dependency subgraph ProductCatalog → hibernatewithmysql",
        ),
        ground_truth=gt,
        detect=result,
    )
    return {"incident_id": "motadata-deps-001", "path": str(dest), "gt": gt}


BUILDERS = {
    "motadata-apm-001": lambda limit_spans: build_apm(limit_spans=limit_spans),
    "motadata-ping-001": lambda limit_spans: build_ping(),
    "motadata-ping-002": lambda limit_spans: build_ping_002(),
    "motadata-ping-003": lambda limit_spans: build_ping_003(),
    "motadata-ping-004": lambda limit_spans: build_ping_004(),
    "motadata-cpu-001": lambda limit_spans: build_cpu(),
    "motadata-multi-001": lambda limit_spans: build_multi_001(),
    "motadata-deps-001": lambda limit_spans: build_deps_001(limit_spans=limit_spans),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Motadata broaden → Lean Localize")
    parser.add_argument(
        "--incident",
        action="append",
        choices=list(ALL_IDS),
        help="Build one incident (repeatable). Default: all.",
    )
    parser.add_argument("--limit-spans", type=int, default=80000)
    parser.add_argument("--skip-diagnose", action="store_true")
    parser.add_argument(
        "--skip-ci-bind",
        action="store_true",
        help="Reuse existing ci_bind.json",
    )
    args = parser.parse_args(argv)

    from local_dumps import require_jsonl_resolved

    require_jsonl_resolved()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    INCIDENTS.mkdir(parents=True, exist_ok=True)
    if not args.skip_ci_bind:
        _refresh_ci_bind()
    _ensure_inventory(rebuild=True)

    targets = tuple(args.incident) if args.incident else ALL_IDS
    built: list[dict] = []
    for incident_id in targets:
        print(f"\n=== build {incident_id} ===")
        built.append(BUILDERS[incident_id](args.limit_spans))

    if args.skip_diagnose:
        print(json.dumps({"built": [b["incident_id"] for b in built]}, indent=2))
        return 0

    results = []
    all_ok = True
    for item in built:
        iid = item["incident_id"]
        gt = item["gt"]
        verdict = lean_diagnose(iid)
        root_ok = verdict.get("root_ci") == gt["root_ci"]
        sig_ok = verdict.get("signature") == gt["signature"]
        ok = root_ok and sig_ok
        all_ok = all_ok and ok
        row = {
            "incident_id": iid,
            "root_ci": verdict.get("root_ci"),
            "signature": verdict.get("signature"),
            "root_match": root_ok,
            "signature_match": sig_ok,
            "pass": ok,
        }
        results.append(row)
        print(
            f"diagnose {iid}: root={verdict.get('root_ci')} "
            f"sig={verdict.get('signature')} "
            f"root_match={root_ok} sig_match={sig_ok}"
        )
        meta_path = INCIDENTS / iid / "incident_meta.json"
        meta = json.loads(meta_path.read_text())
        meta["diagnose"] = row
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    summary = {
        "incidents": results,
        "pass_count": sum(1 for r in results if r["pass"]),
        "total": len(results),
    }
    (OUT_ROOT / "broaden_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
