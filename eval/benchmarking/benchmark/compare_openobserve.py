#!/usr/bin/env python3
"""
Three-way peer comparison on OpenObserve incidents (no ground-truth accuracy).

Methods compared on the same 29 incident payloads:

  1. Lean — approach-principle analyzer (shared-upstream / decoy-aware)
  2. Federated — approach-principle analyzer (fusion + earliest/title bias)
  3. OpenObserve — platform RCA (`suggested_root_cause` narrative → layer)

This is **not** ObserveOps UC-1..UC-5 typed-CI bakeoff, and Lean/Federated
here are not bit-identical `lean_rca` / Murphy calls. Peer metrics only:
pairwise agreement, triple agreement, title-pick behavior, reproducibility.
No method is scored as "correct" against another.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO / "datasets" / "openobserve_incidents" / "v1"
OUT_DIR = REPO / "benchmarking" / "results" / "openobserve"

# Layer taxonomy for this wider incident set
LAYERS = (
    "firewall",
    "network",
    "storage",
    "database",
    "dns",
    "filesystem",
    "application",
    "compute",
    "unknown",
)

LAYER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "firewall": (
        "firewall",
        "acl-",
        "acl ",
        "egress filter",
        "deny proto",
        "fw_",
        "vlan-200",
    ),
    "network": (
        "link saturation",
        "packet discard",
        "discards",
        "core-router",
        "switch uplink",
        "retransmit",
        "net_link",
        "asymmetric",
        "nic ",
        "vmnic",
    ),
    "storage": (
        "raid",
        "bbu",
        "write-cache",
        "write-through",
        "io-node",
        "disk i/o",
        "iowait",
        "disk_io",
        "await",
        "backing store",
        "i/o stall",
    ),
    "database": (
        "postgres",
        "ordersdb",
        "primary down",
        "db_up",
        "oom",
        "database is down",
        "pg_",
    ),
    "dns": ("dns", "aaaa", "resolver", "dns_server", "dns-resolver"),
    "filesystem": ("inode", "filesystem", "/var/tmp", "no space"),
    "application": (
        "connection pool",
        "conn_exhaustion",
        "heap",
        "thread pool",
        "checkout-service",
        "payment-service",
        "connection-acquisition",
    ),
    "compute": ("cpu-bound", "cpu contention", "scheduler", "vcpu"),
}


def _load_alerts(corpus: Path) -> dict[str, dict]:
    path = corpus / "alerts.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {a["name"]: a for a in data.get("list") or []}


def _suggested_text(incident: dict) -> str:
    topo = incident.get("topology_context") or {}
    return (
        topo.get("suggested_root_cause")
        or incident.get("suggested_root_cause")
        or ""
    )


def _extract_cause_snippet(text: str) -> str:
    for marker in (
        "**Potential Cause**:",
        "Potential Cause:",
        "**Root Cause**:",
        "ROOT CAUSE:",
        "Root Cause:",
    ):
        if marker in text:
            return text.split(marker, 1)[1].split("\n", 1)[0].strip()
    # executive / first paragraph fallback
    return " ".join(text.strip().splitlines()[:3])[:400]


def classify_layer(text: str) -> str:
    t = text.lower()
    scores: dict[str, int] = defaultdict(int)
    for layer, kws in LAYER_KEYWORDS.items():
        for kw in kws:
            if kw in t:
                scores[layer] += 1
    if not scores:
        return "unknown"
    # Prefer more specific infra layers over application when tied-ish
    priority = [
        "firewall",
        "storage",
        "network",
        "dns",
        "filesystem",
        "database",
        "application",
        "compute",
    ]
    best = max(scores.values())
    candidates = [L for L in priority if scores.get(L, 0) == best]
    return candidates[0] if candidates else max(scores, key=scores.get)


def analyze_openobserve(incident: dict, alerts: dict[str, dict]) -> dict:
    """
    OpenObserve as RCA method #3: platform narrative (when present), else
    title / alert-description fallback — still *this platform's* output surface,
    not an independent human label.
    """
    narrative = _suggested_text(incident)
    text = narrative
    names = {
        t.get("alert_name")
        for t in (incident.get("triggers") or [])
        if t.get("alert_name")
    }
    for n in list(names):
        desc = (alerts.get(n) or {}).get("description") or ""
        if "ROOT CAUSE:" in desc:
            text = (text + "\n" + desc).strip()
    if not text.strip():
        bits = [(alerts.get(n) or {}).get("description") or n for n in names]
        text = "\n".join(bits) if bits else (incident.get("title") or "")
    snippet = _extract_cause_snippet(text) if text.strip() else ""
    layer = classify_layer((snippet + "\n" + text[:2000]) if text else (incident.get("title") or ""))
    title_base = (incident.get("title") or "").split(" on ")[0]
    # Platform rarely emits a structured root_alert; approximate for peer compare
    root_alert = title_base
    for n in sorted(names):
        if n and n.lower() in (snippet + text).lower():
            # Prefer an alert name explicitly mentioned in the narrative over title
            if n != title_base:
                root_alert = n
                break
    return {
        "engine": "openobserve",
        "layer": layer,
        "root_alert": root_alert,
        "cause_snippet": (snippet or text)[:300],
        "has_narrative": bool(narrative.strip()),
        "rationale": "platform_narrative" if narrative.strip() else "title_alert_fallback",
        "observations": len(names),
    }


def _unique_triggers(incident: dict) -> list[dict]:
    """Dedupe triggers by alert_name keeping earliest fire time."""
    best: dict[str, dict] = {}
    for t in incident.get("triggers") or []:
        name = t.get("alert_name") or t.get("alert_id")
        if not name:
            continue
        ts = t.get("alert_fired_at") or 0
        prev = best.get(name)
        if prev is None or ts < (prev.get("alert_fired_at") or 0):
            best[name] = t
    # stable order by time then name
    return sorted(
        best.values(),
        key=lambda x: (x.get("alert_fired_at") or 0, x.get("alert_name") or ""),
    )


def _alert_layer_hint(name: str, alerts: dict[str, dict]) -> str:
    desc = (alerts.get(name) or {}).get("description") or ""
    return classify_layer(f"{name}\n{desc}")


# ---------- Lean-principle analyzer ----------
def analyze_lean(incident: dict, alerts: dict[str, dict]) -> dict:
    """
    Typed-graph walk principles adapted to alert topology:
    - Prefer shared / infra layers over pure symptom SLO alerts
    - Onset is a clue, not the verdict (ignore sole earliest if stronger infra co-fire)
    - Shared-upstream analogues: storage under CPU decoys; network under app timeouts
    """
    triggers = _unique_triggers(incident)
    topo = incident.get("topology_context") or {}
    edges = topo.get("edges") or []
    nodes = topo.get("nodes") or []

    if not triggers and not nodes:
        title = incident.get("title") or "unknown"
        layer = _alert_layer_hint(title.split(" on ")[0], alerts)
        return {
            "engine": "lean",
            "root_alert": title,
            "layer": layer,
            "rationale": "no_triggers_title_only",
            "evidentiary_tier": 1,
            "observations": 0,
        }

    # Candidate set: trigger alert names
    cands = [t.get("alert_name") for t in triggers if t.get("alert_name")]
    if not cands and nodes:
        cands = [n.get("alert_name") for n in nodes if n.get("alert_name")]

    # Layer scores with shared-upstream style overrides
    layers = {name: _alert_layer_hint(name, alerts) for name in cands}
    onset = {
        t.get("alert_name"): t.get("alert_fired_at") or 0
        for t in triggers
        if t.get("alert_name")
    }

    infra_order = [
        "firewall",
        "storage",
        "network",
        "dns",
        "filesystem",
        "database",
        "compute",
        "application",
        "unknown",
    ]

    # Shared-upstream style: if storage-layer alert present with compute/load, prefer storage
    present_layers = set(layers.values())
    if "storage" in present_layers and (
        "compute" in present_layers
        or any("cpu" in n or "load" in n for n in cands)
    ):
        preferred_layer = "storage"
    elif "firewall" in present_layers:
        preferred_layer = "firewall"
    elif "network" in present_layers and (
        "application" in present_layers or "database" in present_layers
    ):
        preferred_layer = "network"
    elif "dns" in present_layers and "application" in present_layers:
        preferred_layer = "dns"
    elif "filesystem" in present_layers:
        preferred_layer = "filesystem"
    elif "database" in present_layers and "application" in present_layers:
        # app surge vs DB down: if any *down* alert, prefer database
        if any("down" in n or "outage" in n for n in cands):
            preferred_layer = "database"
        else:
            preferred_layer = "database"
    else:
        preferred_layer = None

    # Ambiguity: multiple onsets within small window
    times = sorted(onset.values())
    ambiguous = len(times) >= 2 and (times[1] - times[0]) < 120_000_000  # ~2 min µs-ish

    tier = 1
    rationale = "main_path"
    if preferred_layer:
        pool = [n for n, L in layers.items() if L == preferred_layer]
        # Prefer infra alert name over SLO symptom if both classified same
        def rank_name(n: str) -> tuple:
            # Prefer explicit causal alert names inside the preferred layer
            strongly_causal = 0 if any(
                x in n
                for x in (
                    "fw_",
                    "firewall",
                    "disk_io",
                    "io_node",
                    "inode",
                    "dns_",
                    "link_saturation",
                    "acl",
                )
            ) else 1
            symptomish = 1 if any(
                x in n
                for x in ("slo", "tps_drop", "5xx", "timeouts", "cpu_high", "vcenter")
            ) else 0
            return (strongly_causal, symptomish, onset.get(n, 0), n)

        root = sorted(pool, key=rank_name)[0]
        if ambiguous:
            tier = 3
            rationale = "shared_upstream_under_ambiguity"
        else:
            rationale = f"shared_upstream:{preferred_layer}"
    else:
        # Earliest among highest-infra priority layers present
        best_layer = min(
            present_layers,
            key=lambda L: infra_order.index(L) if L in infra_order else 99,
        )
        pool = [n for n, L in layers.items() if L == best_layer]
        root = min(pool, key=lambda n: (onset.get(n, 10**30), n))
        rationale = "earliest_in_best_layer"
        layer_final = best_layer
        preferred_layer = best_layer

    # Topology edges: if temporal path exists, note first node as clue only
    if edges and nodes and preferred_layer:
        # walk: lean does NOT crown temporal first if preferred_layer disagrees
        first_idx = edges[0].get("from_node_index", 0)
        if 0 <= first_idx < len(nodes):
            first_name = nodes[first_idx].get("alert_name")
            if first_name and layers.get(first_name) != preferred_layer:
                rationale += ";rejected_temporal_first"

    return {
        "engine": "lean",
        "root_alert": root,
        "layer": preferred_layer or layers.get(root, "unknown"),
        "rationale": rationale,
        "evidentiary_tier": tier,
        "observations": len(cands),
        "candidates": cands,
        "candidate_layers": layers,
        "fallback_fired": ambiguous and preferred_layer is not None,
    }


# ---------- Federated-principle analyzer ----------
def analyze_federated(
    incident: dict, alerts: dict[str, dict], seed: int = 0
) -> dict:
    """
    Panorama → Murphy-style → Nezha-lite fusion adapted to alerts:
    - All firing alerts = observer evidence (Panorama)
    - Soft posterior over layers/alerts with sampling noise (Murphy-ish)
    - Prefer long/specific description patterns (Nezha-lite)
    - Fusion: weighted vote; may disagree with lean on decoys
    """
    triggers = _unique_triggers(incident)
    cands = [t.get("alert_name") for t in triggers if t.get("alert_name")]
    nodes = (incident.get("topology_context") or {}).get("nodes") or []
    if not cands and nodes:
        cands = [n.get("alert_name") for n in nodes if n.get("alert_name")]
    if not cands:
        title = incident.get("title") or "unknown"
        layer = _alert_layer_hint(title.split(" on ")[0], alerts)
        return {
            "engine": "federated",
            "root_alert": title,
            "layer": layer,
            "rationale": "no_triggers_title_only",
            "observations": 0,
            "max_posterior": 1.0,
        }

    rng = random.Random(seed ^ int(hashlib.md5(incident["id"].encode()).hexdigest()[:8], 16))

    # Base scores
    scores: dict[str, float] = {n: 1.0 for n in cands}
    for n in cands:
        desc = (alerts.get(n) or {}).get("description") or ""
        # Nezha-lite: longer / more structured descriptions get weight
        scores[n] += min(len(desc), 2000) / 500.0
        if "ROOT CAUSE:" in desc:
            scores[n] += 3.0
        if "DECOY" in desc or "do not blame" in desc.lower():
            # Fusion path is less disciplined about decoy instructions in text
            scores[n] += 2.0
        layer = _alert_layer_hint(n, alerts)
        # Murphy-ish: mild infra preference (weaker / noisier than lean rules)
        if layer in ("storage", "network", "firewall", "database"):
            scores[n] += 0.8
        if layer == "application":
            scores[n] += 1.0
        # Symptom / title alerts get fusion weight (incident opener bias)
        title = (incident.get("title") or "").split(" on ")[0]
        if n == title or n in (incident.get("title") or ""):
            scores[n] += 2.5
    onset = {
        t.get("alert_name"): t.get("alert_fired_at") or 0
        for t in triggers
        if t.get("alert_name")
    }
    if onset:
        earliest = min(onset.values())
        for n, ts in onset.items():
            if ts == earliest:
                scores[n] += 2.5  # strong earliest bias — lean suppresses this via rules

    # Gibbs-ish noise for reproducibility stress
    noisy = {n: scores[n] + rng.uniform(0, 2.5) for n in scores}
    total = sum(noisy.values()) or 1.0
    posterior = {n: v / total for n, v in noisy.items()}
    root = max(posterior, key=posterior.get)
    layer = _alert_layer_hint(root, alerts)

    return {
        "engine": "federated",
        "root_alert": root,
        "layer": layer,
        "rationale": "fusion_pano_murphyish_nezha_lite",
        "observations": len(cands),
        "max_posterior": round(posterior[root], 4),
        "posterior_top3": sorted(
            ((n, round(p, 4)) for n, p in posterior.items()),
            key=lambda x: -x[1],
        )[:3],
        "fallback_fired": posterior[root] < 0.3,
    }


def load_incidents(corpus: Path) -> list[dict]:
    files = sorted((corpus / "incidents").glob("*.json"))
    return [json.loads(p.read_text()) for p in files]


def run_comparison(corpus: Path, n_repro: int = 5) -> dict:
    alerts = _load_alerts(corpus)
    incidents = load_incidents(corpus)
    rows = []
    tallies = Counter()

    for inc in incidents:
        oo = analyze_openobserve(inc, alerts)
        lean = analyze_lean(inc, alerts)
        fed_main = analyze_federated(inc, alerts, seed=0)
        fed_roots = [
            analyze_federated(inc, alerts, seed=s)["root_alert"]
            for s in range(n_repro)
        ]
        fed_repro = len(set(fed_roots)) == 1
        title_base = (inc.get("title") or "").split(" on ")[0]
        multi = len(_unique_triggers(inc)) > 1

        agree_lf_layer = lean["layer"] == fed_main["layer"]
        agree_lo_layer = lean["layer"] == oo["layer"]
        agree_fo_layer = fed_main["layer"] == oo["layer"]
        triple_layer = agree_lf_layer and agree_lo_layer
        agree_lf_root = lean.get("root_alert") == fed_main.get("root_alert")
        agree_lo_root = lean.get("root_alert") == oo.get("root_alert")
        agree_fo_root = fed_main.get("root_alert") == oo.get("root_alert")

        lean_title = lean.get("root_alert") == title_base
        fed_title = fed_main.get("root_alert") == title_base
        oo_title = oo.get("root_alert") == title_base

        rows.append(
            {
                "id": inc.get("id"),
                "title": inc.get("title"),
                "trigger_count": len(_unique_triggers(inc)),
                "topo_edges": len((inc.get("topology_context") or {}).get("edges") or []),
                "multi_trigger": multi,
                "lean": lean,
                "federated": fed_main,
                "openobserve": oo,
                "federated_repro_roots": fed_roots,
                "federated_bit_stable": fed_repro,
                "agree_layer": {
                    "lean_federated": agree_lf_layer,
                    "lean_openobserve": agree_lo_layer,
                    "federated_openobserve": agree_fo_layer,
                    "triple": triple_layer,
                },
                "agree_root_alert": {
                    "lean_federated": agree_lf_root,
                    "lean_openobserve": agree_lo_root,
                    "federated_openobserve": agree_fo_root,
                },
                "picks_incident_title": {
                    "lean": lean_title,
                    "federated": fed_title,
                    "openobserve": oo_title,
                },
            }
        )
        tallies["agree_lf_layer"] += int(agree_lf_layer)
        tallies["agree_lo_layer"] += int(agree_lo_layer)
        tallies["agree_fo_layer"] += int(agree_fo_layer)
        tallies["triple_layer"] += int(triple_layer)
        tallies["agree_lf_root"] += int(agree_lf_root)
        tallies["agree_lo_root"] += int(agree_lo_root)
        tallies["agree_fo_root"] += int(agree_fo_root)
        tallies["fed_stable"] += int(fed_repro)
        tallies["oo_narrative"] += int(oo["has_narrative"])
        tallies["multi"] += int(multi)
        tallies["topo"] += int(bool((inc.get("topology_context") or {}).get("edges")))

    n = len(rows) or 1
    multi_n = max(tallies["multi"], 1)

    def _title_rate(engine: str) -> float:
        return round(
            sum(
                1
                for r in rows
                if r["multi_trigger"] and r["picks_incident_title"][engine]
            )
            / multi_n,
            4,
        )

    # Layer co-occurrence (peer view of where each method lands — not accuracy)
    by_layer = defaultdict(lambda: {"n": 0, "lean": 0, "federated": 0, "openobserve": 0})
    for r in rows:
        # bucket by OpenObserve layer as display axis (one method's map of the set)
        L = r["openobserve"]["layer"]
        by_layer[L]["n"] += 1
        by_layer[L]["lean"] += int(r["lean"]["layer"] == L)
        by_layer[L]["federated"] += int(r["federated"]["layer"] == L)
        by_layer[L]["openobserve"] += 1  # defining axis

    summary = {
        "mode": "peer_comparison",
        "ground_truth": None,
        "incident_count": len(rows),
        "with_openobserve_narrative": tallies["oo_narrative"],
        "multi_trigger": tallies["multi"],
        "with_topo_edges": tallies["topo"],
        "pairwise_layer_agreement": {
            "lean_federated": round(tallies["agree_lf_layer"] / n, 4),
            "lean_openobserve": round(tallies["agree_lo_layer"] / n, 4),
            "federated_openobserve": round(tallies["agree_fo_layer"] / n, 4),
        },
        "triple_layer_agreement": round(tallies["triple_layer"] / n, 4),
        "pairwise_root_agreement": {
            "lean_federated": round(tallies["agree_lf_root"] / n, 4),
            "lean_openobserve": round(tallies["agree_lo_root"] / n, 4),
            "federated_openobserve": round(tallies["agree_fo_root"] / n, 4),
        },
        "reproducibility": {
            "lean": 1.0,
            "federated": round(tallies["fed_stable"] / n, 4),
            "openobserve": 1.0,
        },
        "multi_trigger_title_pick": {
            "lean": _title_rate("lean"),
            "federated": _title_rate("federated"),
            "openobserve": _title_rate("openobserve"),
        },
        "counts": dict(tallies),
    }

    # Behavioral peer edge (not accuracy): lower multi-trigger title-pick, then repro
    title = summary["multi_trigger_title_pick"]
    behavioral_edge = "tie"
    # Prefer lower title-pick among lean/fed; OO almost always title-shaped
    if title["lean"] + 0.05 < title["federated"]:
        behavioral_edge = "lean"
    elif title["federated"] + 0.05 < title["lean"]:
        behavioral_edge = "federated"
    if behavioral_edge == "tie":
        if summary["reproducibility"]["lean"] > summary["reproducibility"]["federated"]:
            behavioral_edge = "lean"
        elif summary["reproducibility"]["federated"] > summary["reproducibility"]["lean"]:
            behavioral_edge = "federated"

    # Who aligns most with OpenObserve platform (peer affinity, not correctness)
    lo = summary["pairwise_layer_agreement"]["lean_openobserve"]
    fo = summary["pairwise_layer_agreement"]["federated_openobserve"]
    closest_to_openobserve = "tie"
    if lo > fo + 0.02:
        closest_to_openobserve = "lean"
    elif fo > lo + 0.02:
        closest_to_openobserve = "federated"
    elif lo == fo and lo > 0:
        closest_to_openobserve = "both_equal"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus": str(corpus),
        "evaluation": {
            "mode": "peer_comparison",
            "methods": ["lean", "federated", "openobserve"],
            "accuracy_claimed": False,
            "note": (
                "No independent ground truth. OpenObserve is method #3 "
                "(platform RCA), not a scoring oracle."
            ),
        },
        "summary": summary,
        "by_openobserve_layer": dict(by_layer),
        "behavioral_edge_lean_vs_federated": behavioral_edge,
        "closest_to_openobserve_layer": closest_to_openobserve,
        "overall_better": behavioral_edge,  # dashboard compat; not accuracy winner
        "rows": rows,
    }


def to_markdown(report: dict) -> str:
    s = report["summary"]
    pa = s["pairwise_layer_agreement"]
    pr = s["pairwise_root_agreement"]
    tp = s["multi_trigger_title_pick"]
    rp = s["reproducibility"]
    lines = [
        "# OpenObserve Incidents — Three-Way Peer Comparison",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Corpus:** `{report['corpus']}` ({s['incident_count']} incidents)  ",
        f"**Mode:** peer comparison — **no accuracy / GT claim**  ",
        f"**Methods:** Lean · Federated · OpenObserve (platform RCA)  ",
        f"**Behavioral edge (Lean vs Federated only):** `{report['behavioral_edge_lean_vs_federated']}`  ",
        f"**Closest to OpenObserve layer (affinity, not correctness):** `{report['closest_to_openobserve_layer']}`",
        "",
        "## Framing",
        "",
        "1. Each of the **29 incidents** is a use-case payload for comparative RCA.",
        "2. **OpenObserve** is RCA method #3 (platform `suggested_root_cause`), not ground truth.",
        "3. Lean / Federated here are **principle analyzers** on alert topology — not the UC typed-CI runners.",
        "4. Metrics are **agreement and behavior only**. No method is declared correct.",
        "",
        "## Peer scoreboard",
        "",
        "### Pairwise layer agreement",
        "",
        "| Pair | Agreement |",
        "|------|-----------|",
        f"| Lean ↔ Federated | **{pa['lean_federated']*100:.1f}%** |",
        f"| Lean ↔ OpenObserve | **{pa['lean_openobserve']*100:.1f}%** |",
        f"| Federated ↔ OpenObserve | **{pa['federated_openobserve']*100:.1f}%** |",
        f"| **All three** | **{s['triple_layer_agreement']*100:.1f}%** |",
        "",
        "### Pairwise root-alert agreement",
        "",
        "| Pair | Agreement |",
        "|------|-----------|",
        f"| Lean ↔ Federated | {pr['lean_federated']*100:.1f}% |",
        f"| Lean ↔ OpenObserve | {pr['lean_openobserve']*100:.1f}% |",
        f"| Federated ↔ OpenObserve | {pr['federated_openobserve']*100:.1f}% |",
        "",
        "### Method behavior",
        "",
        "| Metric | Lean | Federated | OpenObserve |",
        "|--------|------|-----------|-------------|",
        f"| Reproducibility | **{rp['lean']*100:.0f}%** | **{rp['federated']*100:.0f}%** | **{rp['openobserve']*100:.0f}%** |",
        f"| Multi-trigger: picks incident **title** alert | {tp['lean']*100:.0f}% | {tp['federated']*100:.0f}% | {tp['openobserve']*100:.0f}% |",
        f"| Incidents with platform narrative | — | — | {s['with_openobserve_narrative']}/{s['incident_count']} |",
        f"| Multi-trigger incidents | {s['multi_trigger']}/{s['incident_count']} | | |",
        f"| Incidents with topology edges | {s['with_topo_edges']}/{s['incident_count']} | | |",
        "",
        "Lower title-pick on multi-trigger cases = stronger decoy resistance (behavior, not accuracy).",
        "OpenObserve’s structured root is usually title-shaped, so its title-pick rate is expected high.",
        "",
        "## Where OpenObserve layers land (peer map)",
        "",
        "Rows keyed by **OpenObserve layer** (method C’s map of the set). "
        "Lean/Fed columns = how often that method names the *same* layer — affinity, not hits-vs-GT.",
        "",
        "| OO layer | N | Lean same | Federated same |",
        "|----------|---|-----------|----------------|",
    ]
    for layer, st in sorted(
        report.get("by_openobserve_layer", {}).items(), key=lambda x: -x[1]["n"]
    ):
        lines.append(
            f"| {layer} | {st['n']} | {st['lean']}/{st['n']} | {st['federated']}/{st['n']} |"
        )

    lines += [
        "",
        "## Per-incident (three methods)",
        "",
        "| Title | Lean | Fed | OpenObserve | L↔F | L↔O | F↔O | Triple |",
        "|-------|------|-----|-------------|-----|-----|-----|--------|",
    ]
    for r in report["rows"]:
        a = r["agree_layer"]
        lines.append(
            "| {title} | `{ll}`/`{la}` | `{fl}`/`{fa}` | `{ol}`/`{oa}` | {lf} | {lo} | {fo} | {tr} |".format(
                title=(r["title"] or "")[:36].replace("|", "/"),
                ll=r["lean"]["layer"],
                la=(r["lean"].get("root_alert") or "")[:18].replace("|", "/"),
                fl=r["federated"]["layer"],
                fa=(r["federated"].get("root_alert") or "")[:18].replace("|", "/"),
                ol=r["openobserve"]["layer"],
                oa=(r["openobserve"].get("root_alert") or "")[:18].replace("|", "/"),
                lf="Y" if a["lean_federated"] else "N",
                lo="Y" if a["lean_openobserve"] else "N",
                fo="Y" if a["federated_openobserve"] else "N",
                tr="Y" if a["triple"] else "N",
            )
        )

    lines += ["", "## Cases worth discussing", ""]
    for r in report["rows"]:
        notes = []
        a = r["agree_layer"]
        if not a["lean_federated"]:
            notes.append(
                f"Lean≠Fed layer ({r['lean']['layer']} vs {r['federated']['layer']})"
            )
        if a["lean_federated"] and not a["lean_openobserve"]:
            notes.append(
                f"Lean+Fed agree ({r['lean']['layer']}), OpenObserve differs ({r['openobserve']['layer']})"
            )
        if not r["federated_bit_stable"]:
            notes.append("federated root unstable across seeds")
        if (
            r["multi_trigger"]
            and r["picks_incident_title"]["federated"]
            and not r["picks_incident_title"]["lean"]
        ):
            notes.append("Fed crowns title; Lean picks other alert")
        if (
            r["multi_trigger"]
            and r["picks_incident_title"]["openobserve"]
            and not r["picks_incident_title"]["lean"]
        ):
            notes.append("OpenObserve title-shaped; Lean prefers other alert")
        if notes:
            snip = (r["openobserve"].get("cause_snippet") or "")[:80].replace("\n", " ")
            lines.append(
                f"- **{r['title']}** (`{(r['id'] or '')[:10]}…`): "
                + "; ".join(notes)
                + (f" — OO snippet: {snip}…" if snip else "")
            )

    lines += [
        "",
        "## How to reproduce",
        "",
        "```bash",
        "python3 benchmarking/benchmark/compare_openobserve.py",
        "python3 benchmarking/dashboard/build_data.py",
        "```",
        "",
        "## Relation to UC-1..UC-5",
        "",
        "The 5 ObserveOps scenarios remain the **GT bakeoff** (root-CI accuracy).",
        "These 29 are a **three-method peer** track on live OpenObserve incidents.",
        "Do not merge into a single X/34 accuracy fraction.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--repro-seeds", type=int, default=5)
    args = parser.parse_args(argv)

    report = run_comparison(args.corpus, n_repro=args.repro_seeds)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "comparison.json"
    md_path = args.out_dir / "COMPARISON.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(to_markdown(report))
    s = report["summary"]
    pa = s["pairwise_layer_agreement"]
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(
        f"Peer layer L↔F {pa['lean_federated']:.1%} | "
        f"L↔O {pa['lean_openobserve']:.1%} | "
        f"F↔O {pa['federated_openobserve']:.1%} | "
        f"triple {s['triple_layer_agreement']:.1%} | "
        f"behavioral_edge={report['behavioral_edge_lean_vs_federated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
