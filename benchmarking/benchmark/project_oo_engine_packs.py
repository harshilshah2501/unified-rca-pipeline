#!/usr/bin/env python3
"""Project OpenObserve incidents into ObserveOps-shaped engine packs.

Each pack under datasets/openobserve_incidents/v1/engine_packs/<id>/ has:
  topology.json, anomalies.json, symptom_seed.json, ground_truth.json

Lean/Federated load these via the same load_bundle contract as ObserveOps UCs.
CI ids are alert names so Accuracy vs Option B is root_ci == root_alert.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from compare_openobserve import LAYER_KEYWORDS, classify_layer

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "openobserve_incidents" / "v1"
PACKS = CORPUS / "engine_packs"
GT_DIR = CORPUS / "ground_truth"

LAYER_TO_CI_TYPE = {
    "firewall": "NetworkPort",
    "network": "NetworkPort",
    "storage": "Datastore",
    "database": "Service",
    "dns": "Service",
    "filesystem": "GuestOS",
    "application": "Service",
    "compute": "HypervisorHost",
    "unknown": "Service",
}

LAYER_TO_SIGNATURE = {
    "firewall": "link_failure",
    "network": "link_failure",
    "storage": "storage_contention",
    "database": "app_resource_exhaustion",
    "dns": "app_resource_exhaustion",
    "filesystem": "os_resource_exhaustion",
    "application": "app_resource_exhaustion",
    "compute": "cpu_contention",
    "unknown": "unknown",
}


def _us_to_iso(us: int | float | None) -> str:
    if us is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # OpenObserve timestamps are microseconds since epoch
    sec = float(us) / 1_000_000.0
    return datetime.fromtimestamp(sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_alerts() -> dict[str, dict]:
    path = CORPUS / "alerts.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {a["name"]: a for a in data.get("list") or []}


def _title_base(title: str | None) -> str:
    return (title or "").split(" on ")[0].strip()


def _alert_layer(name: str, alert_defs: dict[str, dict]) -> str:
    desc = (alert_defs.get(name) or {}).get("description") or ""
    return classify_layer(f"{name}\n{desc}")


def _unique_triggers(incident: dict) -> list[dict]:
    """Dedupe by alert_name keeping earliest fire time."""
    best: dict[str, dict] = {}
    for t in incident.get("triggers") or []:
        name = t.get("alert_name")
        if not name:
            continue
        fired = t.get("alert_fired_at") or 0
        prev = best.get(name)
        if prev is None or fired < (prev.get("alert_fired_at") or 0):
            best[name] = dict(t)
    return sorted(best.values(), key=lambda x: x.get("alert_fired_at") or 0)


def _project_topology(incident: dict, triggers: list[dict], alert_defs: dict[str, dict]) -> dict:
    names = [t["alert_name"] for t in triggers]
    if not names:
        title = _title_base(incident.get("title")) or "unknown_title"
        names = [title]

    nodes = []
    for name in names:
        layer = _alert_layer(name, alert_defs)
        ctx = (alert_defs.get(name) or {}).get("context_attributes") or {}
        display = ctx.get("service_name") or ctx.get("host") or name
        nodes.append(
            {
                "id": name,
                "type": LAYER_TO_CI_TYPE.get(layer, "Service"),
                "name": display,
            }
        )

    # Index topo nodes by position for temporal edges
    topo = incident.get("topology_context") or {}
    topo_nodes = topo.get("nodes") or []
    topo_names: list[str] = []
    for n in topo_nodes:
        an = n.get("alert_name")
        if an:
            topo_names.append(an)

    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()
    raw_edges = topo.get("edges") or []
    if raw_edges and topo_names:
        for e in raw_edges:
            fi = e.get("from_node_index")
            ti = e.get("to_node_index")
            if fi is None or ti is None:
                continue
            if not (0 <= fi < len(topo_names) and 0 <= ti < len(topo_names)):
                continue
            earlier, later = topo_names[fi], topo_names[ti]
            # OO temporal: earlier→later. Lean: from=effect(later) → to=cause(earlier)
            if earlier in names and later in names and earlier != later:
                key = (later, earlier)
                if key not in seen:
                    seen.add(key)
                    edges.append(
                        {"from": later, "to": earlier, "relation": "depends_on"}
                    )
    elif len(triggers) >= 2:
        # Fall back: fire-order chain, Lean direction
        ordered = [t["alert_name"] for t in triggers]
        for i in range(len(ordered) - 1):
            earlier, later = ordered[i], ordered[i + 1]
            key = (later, earlier)
            if key not in seen:
                seen.add(key)
                edges.append(
                    {"from": later, "to": earlier, "relation": "depends_on"}
                )

    return {"version": "1.0.0", "nodes": nodes, "edges": edges}


def _project_anomalies(
    incident: dict, triggers: list[dict], alert_defs: dict[str, dict]
) -> dict:
    if not triggers:
        title = _title_base(incident.get("title")) or "unknown_title"
        ts = _us_to_iso(incident.get("first_alert_at"))
        return {
            "incident_start": ts,
            "anomalies": [
                {
                    "ci": title,
                    "signal": title,
                    "value": 1.0,
                    "threshold": 0.0,
                    "crossed": True,
                    "timestamp": ts,
                }
            ],
        }

    anomalies = []
    for t in triggers:
        name = t["alert_name"]
        adef = alert_defs.get(name) or {}
        # Prefer embedded incident alert, then catalog
        stream = adef.get("stream_name") or name
        for emb in incident.get("alerts") or []:
            if emb.get("name") == name and emb.get("stream_name"):
                stream = emb["stream_name"]
                break
        ts = _us_to_iso(t.get("alert_fired_at"))
        anomalies.append(
            {
                "ci": name,
                "signal": stream,
                "value": 1.0,
                "threshold": 0.0,
                "crossed": True,
                "timestamp": ts,
            }
        )
    start = anomalies[0]["timestamp"] if anomalies else _us_to_iso(None)
    return {"incident_start": start, "anomalies": anomalies}


def _project_seed(incident: dict, triggers: list[dict], anomalies: dict) -> dict:
    title = _title_base(incident.get("title"))
    by_ci = {a["ci"]: a for a in anomalies["anomalies"]}
    if title and title in by_ci:
        a = by_ci[title]
        return {"ci": a["ci"], "signal": a["signal"], "timestamp": a["timestamp"]}
    if triggers:
        # Latest-fired as symptom tip
        latest = max(triggers, key=lambda t: t.get("alert_fired_at") or 0)
        a = by_ci[latest["alert_name"]]
        return {"ci": a["ci"], "signal": a["signal"], "timestamp": a["timestamp"]}
    a = anomalies["anomalies"][0]
    return {"ci": a["ci"], "signal": a["signal"], "timestamp": a["timestamp"]}


def _project_gt(incident_id: str, incident: dict) -> dict:
    gt_path = GT_DIR / f"{incident_id}.json"
    if gt_path.exists():
        gt = json.loads(gt_path.read_text())
        layer = gt.get("root_layer") or "unknown"
        root = gt.get("root_alert") or _title_base(incident.get("title")) or "unknown"
        return {
            "root_ci": root,
            "signature": LAYER_TO_SIGNATURE.get(layer, "unknown"),
            "contributor_cis": list(gt.get("contributor_alerts") or []),
            "blast_radius": [],
            "include_in_accuracy": bool(gt.get("include_in_accuracy")),
            "root_layer": layer,
            "option_b_source": str(gt_path.relative_to(REPO)),
        }
    root = _title_base(incident.get("title")) or "unknown"
    return {
        "root_ci": root,
        "signature": "unknown",
        "contributor_cis": [],
        "blast_radius": [],
        "include_in_accuracy": False,
        "root_layer": "unknown",
        "option_b_source": None,
    }


def project_one(incident_id: str, alert_defs: dict[str, dict]) -> dict:
    inc = json.loads((CORPUS / "incidents" / f"{incident_id}.json").read_text())
    triggers = _unique_triggers(inc)
    topology = _project_topology(inc, triggers, alert_defs)
    anomalies = _project_anomalies(inc, triggers, alert_defs)
    seed = _project_seed(inc, triggers, anomalies)
    gt = _project_gt(incident_id, inc)

    out = PACKS / incident_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "topology.json").write_text(json.dumps(topology, indent=2) + "\n")
    (out / "anomalies.json").write_text(json.dumps(anomalies, indent=2) + "\n")
    (out / "symptom_seed.json").write_text(json.dumps(seed, indent=2) + "\n")
    (out / "ground_truth.json").write_text(json.dumps(gt, indent=2) + "\n")
    return {
        "id": incident_id,
        "title": inc.get("title"),
        "nodes": len(topology["nodes"]),
        "edges": len(topology["edges"]),
        "anomalies": len(anomalies["anomalies"]),
        "root_ci": gt["root_ci"],
        "include_in_accuracy": gt["include_in_accuracy"],
    }


def main() -> int:
    # Silence unused import lint for LAYER_KEYWORDS (re-export check)
    _ = LAYER_KEYWORDS
    alert_defs = _load_alerts()
    # Prefer catalog alerts but overlay per-incident embedded alerts later via stream
    items = []
    for path in sorted((CORPUS / "incidents").glob("*.json")):
        # Merge embedded alert defs into catalog for layer/stream
        inc = json.loads(path.read_text())
        merged = dict(alert_defs)
        for a in inc.get("alerts") or []:
            if a.get("name"):
                merged[a["name"]] = {**(merged.get(a["name"]) or {}), **a}
        meta = project_one(path.stem, merged)
        items.append(meta)
        print(
            f"pack {meta['id'][:12]}… nodes={meta['nodes']} edges={meta['edges']} "
            f"acc={meta['include_in_accuracy']} root={meta['root_ci']}"
        )

    manifest = {
        "corpus_version": "oo-engine-packs-v1",
        "source_corpus": str(CORPUS.relative_to(REPO)),
        "pack_count": len(items),
        "note": (
            "Projected alert-centric packs for Lean/Federated engines. "
            "Accuracy target is Option B root_alert as root_ci. "
            "No metrics/ series in v1."
        ),
        "items": items,
    }
    PACKS.mkdir(parents=True, exist_ok=True)
    (PACKS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {PACKS / 'manifest.json'} ({len(items)} packs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
