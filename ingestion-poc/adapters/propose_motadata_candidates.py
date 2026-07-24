#!/usr/bin/env python3
"""A1 helper: scan Motadata metric lake for threshold-crossing candidates.

Does **not** invent ground truth. Emits ranked candidate windows so a human
can pick stories (step 2) and later write GT (step 6).

Output (default):
  datasets/ingest_samples/motadata-ingest/candidate_windows.json
  datasets/ingest_samples/motadata-ingest/candidate_windows.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ingestion-poc" / "adapters"))

from motadata_to_ingest_v1 import (  # noqa: E402
    load_ci_bind,
    load_threshold_catalog,
    resolve_monitor_ci,
    resolve_threshold,
)

DEFAULT_METRICS = (
    REPO / "datasets" / "ingest_samples" / "jsonl_resolved" / "metric_numeric.jsonl"
)
DEFAULT_OUT_DIR = REPO / "datasets" / "ingest_samples" / "motadata-ingest"

# Already labeled Motadata L1 packs — exclude from "new" shortlist.
KNOWN_PACKS = {
    "422": {"incident_id": "motadata-ping-001", "ci_id": "dlink-48", "class": "ping"},
    "421": {"incident_id": "motadata-ping-002", "ci_id": "Netgear Switch", "class": "ping"},
    "129": {"incident_id": "motadata-ping-003", "ci_id": "proxmox-ve-129", "class": "ping"},
    "24": {
        "incident_id": "motadata-ping-004",
        "ci_id": "localhost.localdomain",
        "class": "ping",
    },
    "27": {"incident_id": "motadata-cpu-001", "ci_id": "Fluentbit", "class": "cpu"},
    "391": {
        "incident_id": "motadata-multi-001",
        "ci_id": "HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com",
        "class": "multi",
    },
}

# Metric families we care about for PoC pack cutting (exact / safe prefixes only).
# Do NOT use bare "system.cpu" — Motadata also emits system.cpu.cache.bytes etc.
INTERESTING_EXACT = {
    "ping.latency.ms",
    "ping.max.latency.ms",
    "ping.packet.lost.percent",
    "system.cpu.percent",
    "system.1min.avg.cpu.percent",
    "system.memory.used.percent",
    "system.overall.memory.used.percent",
    "http.error_rate",
    "http.error_rate_4xx",
    "http.error_rate_5xx",
}


def _interesting(name: str) -> bool:
    return name in INTERESTING_EXACT


def _anomaly_class(name: str) -> str:
    if name.startswith("ping.") or "packet.lost" in name:
        return "network"
    if "memory" in name:
        return "resource"
    if "cpu" in name:
        return "resource"
    if "error_rate" in name:
        return "error_rate"
    return "other"


def _bucket_hint(anomaly_class: str) -> str:
    if anomaly_class == "error_rate":
        return "1_symptom / 3_app"
    if anomaly_class == "network":
        return "2_infra_network"
    if anomaly_class == "resource":
        return "2_infra_resource"
    return "unknown"


def scan_metrics(
    path: Path,
    *,
    catalog: dict[str, Any],
    bind: dict[str, dict[str, Any]],
    limit_lines: int | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Aggregate crossings keyed by (monitor_id, metric_name)."""
    agg: dict[tuple[str, str], dict[str, Any]] = {}
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            if limit_lines is not None and n > limit_lines:
                break
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            mid_raw = row.get("id")
            if mid_raw is None:
                continue
            mid = str(mid_raw)
            ts = str(row.get("timestamp") or "")
            fields = row.get("fields") or {}
            for name_raw, val in fields.items():
                name = str(name_raw)
                if not _interesting(name):
                    continue
                thr = resolve_threshold(name, catalog)
                if thr is None:
                    continue
                if isinstance(val, bool):
                    fval = 1.0 if val else 0.0
                elif isinstance(val, (int, float)):
                    fval = float(val)
                else:
                    continue
                if fval <= thr:
                    continue
                key = (mid, name)
                slot = agg.get(key)
                if slot is None:
                    ci_id, ci_type = resolve_monitor_ci(mid, bind)
                    slot = {
                        "monitor_id": mid,
                        "metric_name": name,
                        "ci_id": ci_id,
                        "ci_type": ci_type,
                        "threshold": thr,
                        "anomaly_class": _anomaly_class(name),
                        "bucket_hint": _bucket_hint(_anomaly_class(name)),
                        "crossing_count": 0,
                        "peak_value": fval,
                        "first_ts": ts,
                        "last_ts": ts,
                        "already_packed": mid in KNOWN_PACKS,
                        "known_pack": KNOWN_PACKS.get(mid),
                    }
                    agg[key] = slot
                slot["crossing_count"] += 1
                if fval > float(slot["peak_value"]):
                    slot["peak_value"] = fval
                if ts:
                    if not slot["first_ts"] or ts < slot["first_ts"]:
                        slot["first_ts"] = ts
                    if not slot["last_ts"] or ts > slot["last_ts"]:
                        slot["last_ts"] = ts
    return agg


def collapse_by_ci(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One candidate card per CI: merge metrics, prefer strongest signal."""
    by_ci: dict[str, dict[str, Any]] = {}
    for r in rows:
        ci = r["ci_id"]
        cur = by_ci.get(ci)
        if cur is None:
            by_ci[ci] = {
                "ci_id": ci,
                "ci_type": r["ci_type"],
                "monitor_ids": {r["monitor_id"]},
                "metrics": [
                    {
                        "metric_name": r["metric_name"],
                        "crossing_count": r["crossing_count"],
                        "peak_value": r["peak_value"],
                        "threshold": r["threshold"],
                    }
                ],
                "anomaly_classes": {r["anomaly_class"]},
                "bucket_hints": {r["bucket_hint"]},
                "crossing_count": r["crossing_count"],
                "peak_score": r["crossing_count"],
                "first_ts": r["first_ts"],
                "last_ts": r["last_ts"],
                "already_packed": r["already_packed"],
                "known_pack": r.get("known_pack"),
                "primary_metric": r["metric_name"],
                "primary_monitor_id": r["monitor_id"],
                "primary_anomaly_class": r["anomaly_class"],
            }
            continue
        cur["monitor_ids"].add(r["monitor_id"])
        cur["metrics"].append(
            {
                "metric_name": r["metric_name"],
                "crossing_count": r["crossing_count"],
                "peak_value": r["peak_value"],
                "threshold": r["threshold"],
            }
        )
        cur["anomaly_classes"].add(r["anomaly_class"])
        cur["bucket_hints"].add(r["bucket_hint"])
        cur["crossing_count"] += r["crossing_count"]
        cur["peak_score"] = max(cur["peak_score"], r["crossing_count"])
        if r["crossing_count"] > next(
            m["crossing_count"]
            for m in cur["metrics"]
            if m["metric_name"] == cur["primary_metric"]
        ):
            cur["primary_metric"] = r["metric_name"]
            cur["primary_monitor_id"] = r["monitor_id"]
            cur["primary_anomaly_class"] = r["anomaly_class"]
        if r["first_ts"] and (not cur["first_ts"] or r["first_ts"] < cur["first_ts"]):
            cur["first_ts"] = r["first_ts"]
        if r["last_ts"] and (not cur["last_ts"] or r["last_ts"] > cur["last_ts"]):
            cur["last_ts"] = r["last_ts"]
        cur["already_packed"] = cur["already_packed"] or r["already_packed"]
        if r.get("known_pack"):
            cur["known_pack"] = r["known_pack"]

    out: list[dict[str, Any]] = []
    for ci, cur in by_ci.items():
        out.append(
            {
                "ci_id": ci,
                "ci_type": cur["ci_type"],
                "monitor_ids": sorted(cur["monitor_ids"]),
                "primary_monitor_id": cur["primary_monitor_id"],
                "primary_metric": cur["primary_metric"],
                "primary_anomaly_class": cur["primary_anomaly_class"],
                "bucket_hint": sorted(cur["bucket_hints"])[0]
                if len(cur["bucket_hints"]) == 1
                else "mixed",
                "anomaly_classes": sorted(cur["anomaly_classes"]),
                "crossing_count": cur["crossing_count"],
                "metrics": sorted(
                    cur["metrics"], key=lambda m: -m["crossing_count"]
                )[:6],
                "first_ts": cur["first_ts"],
                "last_ts": cur["last_ts"],
                "already_packed": cur["already_packed"],
                "known_pack": cur.get("known_pack"),
                "poc_role_hint": _poc_role(cur),
            }
        )
    out.sort(key=lambda c: (-(not c["already_packed"]), -c["crossing_count"]))
    return out


def _poc_role(cur: dict[str, Any]) -> str:
    if cur["already_packed"]:
        return "already_L1_pack"
    classes = cur["anomaly_classes"]
    if len(classes) > 1:
        return "harder_multi_signal"  # ambiguous / multi-metric on same CI
    if "error_rate" in classes:
        return "app_or_symptom"
    if "network" in classes:
        return "infra_network_variant"
    if "resource" in classes:
        return "infra_resource_variant"
    return "other"


def shortlist(cards: list[dict[str, Any]], *, top_n: int) -> list[dict[str, Any]]:
    """Human-facing A1 picks: force class diversity (network / resource / multi)."""
    fresh = [c for c in cards if not c["already_packed"]]
    buckets = {
        "infra_network_variant": [],
        "infra_resource_variant": [],
        "harder_multi_signal": [],
        "app_or_symptom": [],
        "other": [],
    }
    for c in sorted(fresh, key=lambda x: -x["crossing_count"]):
        buckets.get(c["poc_role_hint"], buckets["other"]).append(c)

    picked: list[dict[str, Any]] = []
    # Quotas: network×3, resource×2, multi×3, then fill
    quotas = (
        ("infra_network_variant", 3),
        ("infra_resource_variant", 2),
        ("harder_multi_signal", 3),
        ("app_or_symptom", 2),
        ("other", 2),
    )
    for role, n in quotas:
        for c in buckets[role][:n]:
            if c not in picked:
                picked.append(c)
            if len(picked) >= top_n:
                return picked
    for c in fresh:
        if c not in picked:
            picked.append(c)
        if len(picked) >= top_n:
            break
    return picked


def curated_poc_picks(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Opinionated 4-pack PoC shortlist with rationale (still no GT)."""
    fresh = {c["ci_id"]: c for c in cards if not c["already_packed"]}
    want_ids = [
        # Clear network variants (not dlink-48)
        "Netgear Switch",
        "proxmox-ve-129",
        "localhost.localdomain",
        # Pure chronic resource — flag carefully
        "linux-host-2",
        # Harder: CPU + network on same host
        "HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com",
    ]
    rationale = {
        "Netgear Switch": (
            "Clear infra network variant (packet loss) — same class as ping-001, "
            "different CI. Good regression breadth."
        ),
        "proxmox-ve-129": (
            "Clear ping/packet-loss host — second network smoke if Netgear topology is thin."
        ),
        "localhost.localdomain": (
            "Highest pure-network crossing count — may be noisy/lab; verify before GT."
        ),
        "linux-host-2": (
            "Only pure high-CPU CI besides Fluentbit — check if chronic (bad GT) vs episodic."
        ),
        "HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com": (
            "Harder multi-signal (CPU + network) — leaves comfort zone; GT may need contributors."
        ),
    }
    out = []
    for cid in want_ids:
        c = fresh.get(cid)
        if not c:
            continue
        item = dict(c)
        item["pick_rationale"] = rationale.get(cid, "")
        out.append(item)
    return out


def render_md(
    *,
    cards: list[dict[str, Any]],
    picks: list[dict[str, Any]],
    curated: list[dict[str, Any]],
    scanned_lines: int | None,
    metric_path: Path,
) -> str:
    lines = [
        "# Motadata candidate windows (A1 — no GT yet)",
        "",
        "Automation **proposed** these from threshold crossings. "
        "A human must pick a story and write `ground_truth.json`.",
        "",
        f"- Source: `{metric_path}`",
        f"- Lines scanned: {scanned_lines if scanned_lines is not None else 'all'}",
        f"- CI cards with ≥1 crossing: {len(cards)}",
        f"- Already packed: "
        + ", ".join(
            f"`{c['ci_id']}`→{c['known_pack']['incident_id']}"
            for c in cards
            if c.get("already_packed") and c.get("known_pack")
        ),
        "",
        "## PoC curated picks (start here)",
        "",
        "Aim: **1 clear network variant** + **1 harder multi-signal** "
        "(leave the 3-smoke comfort zone). Skip chronic-only hosts for GT.",
        "",
        "| Priority | CI | Why | Caution |",
        "|----------|----|-----|---------|",
    ]
    for i, c in enumerate(curated, 1):
        caution = ""
        if c["ci_id"] == "linux-host-2":
            caution = "Likely **chronic** CPU (~24h hot) — weak as a discrete incident"
        elif c["ci_id"] == "localhost.localdomain":
            caution = "Short 2h window at 100% loss — verify story before GT"
        elif "HB1-" in c["ci_id"]:
            caution = "Multi-cause possible — GT may need `contributor_cis`"
        lines.append(
            f"| {i} | `{c['ci_id']}` | {c.get('pick_rationale', '')} | {caution} |"
        )
    lines += [
        "",
        "### Suggested first cut (eng after you confirm GT draft)",
        "",
        "1. **`Netgear Switch`** → `motadata-ping-002` — signature draft `ping_degradation` "
        "(packet loss; root=`Netgear Switch` if you agree).",
        "2. **`HB1-…-735.hb1.com`** → `motadata-multi-001` — harder pack; draft root + "
        "contributors after you inspect peaks (CPU/mem/ping).",
        "",
        "**Hold:** `linux-host-2` until you confirm it is not chronically pegged junk.",
        "",
        "## Diversity shortlist",
        "",
        "| # | CI | Class | Role hint | Crossings | Primary metric | Monitors | Window |",
        "|---|----|-------|-----------|-----------|----------------|----------|--------|",
    ]
    for i, c in enumerate(picks, 1):
        lines.append(
            f"| {i} | `{c['ci_id']}` | {c['primary_anomaly_class']} | "
            f"{c['poc_role_hint']} | {c['crossing_count']} | "
            f"`{c['primary_metric']}` | {','.join(c['monitor_ids'])} | "
            f"{c['first_ts'][:19] if c['first_ts'] else '?'} → "
            f"{c['last_ts'][:19] if c['last_ts'] else '?'} |"
        )
    lines += [
        "",
        "### Your next actions",
        "",
        "1. Confirm **1–2** curated picks (or swap from diversity table).",
        "2. For each: draft `root_ci` + `signature` (+ optional `contributor_cis`).",
        "3. Eng cuts packs → Motadata bakeoff → you verify on `#samples`.",
        "",
        "## Top fresh CI cards (by crossings)",
        "",
        "| CI | Crossings | Classes | Primary metric | Role |",
        "|----|-----------|---------|----------------|------|",
    ]
    for c in [x for x in cards if not x["already_packed"]][:25]:
        lines.append(
            f"| `{c['ci_id']}` | {c['crossing_count']} | "
            f"{','.join(c['anomaly_classes'])} | `{c['primary_metric']}` | "
            f"{c['poc_role_hint']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--limit-lines", type=int, default=None)
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    catalog = load_threshold_catalog(None)
    bind = load_ci_bind(None)
    if not args.metrics.is_file():
        print(f"missing metrics: {args.metrics}", file=sys.stderr)
        return 1

    print(f"scanning {args.metrics} …", flush=True)
    agg = scan_metrics(
        args.metrics,
        catalog=catalog,
        bind=bind,
        limit_lines=args.limit_lines,
    )
    raw = list(agg.values())
    cards = collapse_by_ci(raw)
    picks = shortlist(cards, top_n=args.top)
    curated = curated_poc_picks(cards)

    payload = {
        "schema_version": "motadata_candidate_windows.v1",
        "note": "Candidates only — no ground truth. Human picks + labels (A1).",
        "source_metrics": str(args.metrics),
        "limit_lines": args.limit_lines,
        "known_packs": KNOWN_PACKS,
        "ci_card_count": len(cards),
        "metric_key_count": len(raw),
        "curated_poc_picks": curated,
        "shortlist": picks,
        "ci_cards": cards,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "candidate_windows.json"
    md_path = args.out_dir / "candidate_windows.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    md_path.write_text(
        render_md(
            cards=cards,
            picks=picks,
            curated=curated,
            scanned_lines=args.limit_lines,
            metric_path=args.metrics,
        )
    )
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"CI cards={len(cards)} shortlist={len(picks)} curated={len(curated)}")
    print("CURATED:")
    for i, c in enumerate(curated, 1):
        print(
            f"  {i}. {c['ci_id']}  crossings={c['crossing_count']}  "
            f"{c['poc_role_hint']}  {c['primary_metric']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
