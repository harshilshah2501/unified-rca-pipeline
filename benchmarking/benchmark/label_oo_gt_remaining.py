#!/usr/bin/env python3
"""Solo dual-pass Option-B labels for the remaining 17 OpenObserve incidents."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "openobserve_incidents" / "v1"
GT_DIR = CORPUS / "ground_truth"
CMP = REPO / "benchmarking" / "results" / "openobserve" / "comparison.json"
TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

LABELS: list[dict] = [
    {
        "id": "3GA722SK2226oe0RDhuWzg6QYxI",
        "stratum": "single_no_narrative_cpu",
        "root_layer": "compute",
        "root_alert": "starter_high_cpu",
        "contributor_alerts": [],
        "confidence": "ambiguous",
        "include_in_accuracy": False,
        "evidence_note": "Single stub alert (mock CPU>80); no co-firing signals, topology, or narrative. Convention root = title alert only — too thin for accuracy scoring.",
        "pass_a": "Only signal is starter_high_cpu → compute, but evidence is stub-quality.",
        "pass_b": "No corroboration; mark ambiguous / exclude from accuracy.",
        "adj": "Solo Option-B exercise: dual-pass by same reviewer. Both thin; finalize as compute/title but include_in_accuracy=false.",
    },
    {
        "id": "3GA7yKK8vUcMNfiX8tld1EhfiUR",
        "stratum": "single_no_narrative_cpu",
        "root_layer": "compute",
        "root_alert": "starter_high_cpu",
        "contributor_alerts": [],
        "confidence": "ambiguous",
        "include_in_accuracy": False,
        "evidence_note": "Duplicate starter stub; same as sibling starter_high_cpu — exclude from accuracy.",
        "pass_a": "Stub CPU alert only.",
        "pass_b": "No causal chain; ambiguous.",
        "adj": "Solo dual-pass; twin stub excluded from accuracy.",
    },
    {
        "id": "3GAAEIzEzDuWjRmlZygujenDU8i",
        "stratum": "single_database_with_narrative",
        "root_layer": "database",
        "root_alert": "db_primary_down",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single db_primary_down trigger with alert payload; primary DB unavailable is the declared root.",
        "pass_a": "Alert name and text identify primary database failure.",
        "pass_b": "No decoy co-triggers; title matches root.",
        "adj": "Solo dual-pass; agreed database / db_primary_down.",
    },
    {
        "id": "3GAAWBIAL515hv5Np5DNmiMDVxd",
        "stratum": "single_database_with_narrative",
        "root_layer": "database",
        "root_alert": "db_primary_down",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "db_primary_down co-fired with trigger payload (unlike empty-payload sibling); confident database root.",
        "pass_a": "Trigger present with db_primary_down alert.",
        "pass_b": "No upstream decoys in triggers.",
        "adj": "Solo dual-pass; agreed database / db_primary_down.",
    },
    {
        "id": "3GAD6Wqr33nxPmYw8ZMwjoqNUlz",
        "stratum": "single_database_variant",
        "root_layer": "database",
        "root_alert": "pg_ordersdb_outage",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single pg_ordersdb_outage trigger; orders DB outage is the root.",
        "pass_a": "Alert name declares orders DB outage.",
        "pass_b": "Title-only variant; no decoy chain.",
        "adj": "Solo dual-pass; agreed database / pg_ordersdb_outage.",
    },
    {
        "id": "3GAF072FrsFAkgeTlEhF8awO01z",
        "stratum": "single_database_variant",
        "root_layer": "database",
        "root_alert": "pg_ordersdb_down",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single pg_ordersdb_down trigger; Postgres orders DB down is the root.",
        "pass_a": "Database down alert is sole co-fired signal.",
        "pass_b": "No competing infra alerts.",
        "adj": "Solo dual-pass; agreed database / pg_ordersdb_down.",
    },
    {
        "id": "3GAFg9p5QarIXejxbg6thp1LV0w",
        "stratum": "single_database_variant",
        "root_layer": "database",
        "root_alert": "pg_ordersdb_outage3",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single pg_ordersdb_outage3 trigger; orders DB outage variant is the root.",
        "pass_a": "Alert declares DB outage.",
        "pass_b": "No decoy co-triggers.",
        "adj": "Solo dual-pass; agreed database / pg_ordersdb_outage3.",
    },
    {
        "id": "3GAG0DL5e6rz6616PSXYZ8sCOjW",
        "stratum": "single_database_variant",
        "root_layer": "database",
        "root_alert": "pg_svc_down",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single pg_svc_down trigger; Postgres service down is the root.",
        "pass_a": "pg_svc_down is sole signal.",
        "pass_b": "Database layer root; no upstream chain.",
        "adj": "Solo dual-pass; agreed database / pg_svc_down.",
    },
    {
        "id": "3GAG6ZcHySa0WJOfxvG1EzBnZLa",
        "stratum": "single_database_variant",
        "root_layer": "database",
        "root_alert": "pg_svc_down2",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single pg_svc_down2 trigger; Postgres service down variant is the root.",
        "pass_a": "Alert name is explicit DB service failure.",
        "pass_b": "No decoy alerts.",
        "adj": "Solo dual-pass; agreed database / pg_svc_down2.",
    },
    {
        "id": "3GAINIkn1ovFoFzmkJbmUapDMY0",
        "stratum": "single_database_variant",
        "root_layer": "database",
        "root_alert": "pg_db_down_dim",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single pg_db_down_dim trigger; dimensional Postgres DB down is the root.",
        "pass_a": "DB down alert is only co-fired signal.",
        "pass_b": "Confident database root.",
        "adj": "Solo dual-pass; agreed database / pg_db_down_dim.",
    },
    {
        "id": "3GAJqzTd0VQcpliTMIhK40HHQGo",
        "stratum": "single_database_with_narrative",
        "root_layer": "database",
        "root_alert": "pg_primary_down",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "pg_primary_down on pg-prod-01; primary Postgres failure is the root (host in title is scope, not decoy).",
        "pass_a": "pg_primary_down trigger with host context.",
        "pass_b": "Do not crown host name; alert is DB primary down.",
        "adj": "Solo dual-pass; agreed database / pg_primary_down.",
    },
    {
        "id": "3GANb9ArhD5rRUIg5VudmColh9n",
        "stratum": "multi_network_topo",
        "root_layer": "network",
        "root_alert": "net_link_saturation",
        "contributor_alerts": ["gateway_5xx_spike", "checkout_db_timeouts"],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Twin of labeled net_link_saturation case: core-router link saturation drives gateway 5xx and checkout DB timeouts.",
        "pass_a": "Network link is upstream of gateway and DB symptoms.",
        "pass_b": "Title matches infra root; do not crown gateway or DB timeout.",
        "adj": "Solo dual-pass; agreed network / net_link_saturation.",
    },
    {
        "id": "3GASgKbtYcY7fqRBrAosCdWjOZK",
        "stratum": "single_slo_title_only",
        "root_layer": "application",
        "root_alert": "ecom_checkout_slo_breach",
        "contributor_alerts": [],
        "confidence": "ambiguous",
        "include_in_accuracy": False,
        "evidence_note": "Only ecom_checkout_slo_breach co-fired; no DNS/payment upstream alerts in triggers despite narrative hints. SLO title is symptom-only — exclude from accuracy.",
        "pass_a": "Single SLO alert; no upstream chain in triggers.",
        "pass_b": "Decoy-title risk without co-fired infra alerts.",
        "adj": "Solo dual-pass; ambiguous SLO-only; exclude from accuracy.",
    },
    {
        "id": "3GASgjYJR4SG2aTMdpysOhLiZ4U",
        "stratum": "single_app_conn_exhaustion",
        "root_layer": "application",
        "root_alert": "ecom_payment_conn_exhaustion",
        "contributor_alerts": [],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Single ecom_payment_conn_exhaustion trigger; payment connection pool exhaustion is the declared co-fired root (DNS not in triggers for this incident).",
        "pass_a": "Sole co-fired alert is payment pool exhaustion.",
        "pass_b": "Narrative mentions DNS but DNS alert absent from triggers; score declared alert.",
        "adj": "Solo dual-pass; agreed application / ecom_payment_conn_exhaustion.",
    },
    {
        "id": "3GAWT8nVjUE2rA95CZmtyiQcVri",
        "stratum": "decoy_multi_slo_title_dns",
        "root_layer": "dns",
        "root_alert": "ecom_dns_aaaa_numa",
        "contributor_alerts": ["ecom_payment_conn_exhaustion", "ecom_checkout_slo_breach"],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Multi-trigger ecom chain: DNS AAAA NUMA issue drives payment exhaustion and checkout SLO drop. Title is symptom.",
        "pass_a": "Prefer DNS over application SLO title.",
        "pass_b": "Payment exhaustion is mid-chain; DNS is upstream root.",
        "adj": "Solo dual-pass; agreed dns / ecom_dns_aaaa_numa.",
    },
    {
        "id": "3GAYvuQPMJgdDYeyZKXiyCcIF4Z",
        "stratum": "decoy_multi_slo_tls",
        "root_layer": "network",
        "root_alert": "sd_tls_fail",
        "contributor_alerts": ["sd_notif_slo"],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "sd_tls_fail (TLS handshake failures from expired mTLS cert) is upstream of sd_notif_slo push success-rate breach. Title SLO is symptom.",
        "pass_a": "TLS failure alert is causal; cert expiry drives SLO drop.",
        "pass_b": "Do not crown sd_notif_slo title; sd_tls_fail is infra root.",
        "adj": "Solo dual-pass; agreed network / sd_tls_fail.",
    },
    {
        "id": "3GAnUjT7PiQmxyjX6uU4Grwc5qn",
        "stratum": "multi_firewall_topo",
        "root_layer": "firewall",
        "root_alert": "pgw_fw_443_denies",
        "contributor_alerts": [
            "pgw_router_egress_down",
            "pgw_switch_443_asymmetric",
            "pgw_esxi_443_no_return",
            "pgw_syn_sent_pileup",
            "pgw_vcenter_net_alarm",
            "pgw_checkout_tps_drop",
        ],
        "confidence": "confident",
        "include_in_accuracy": True,
        "evidence_note": "Twin of labeled pgw_checkout_tps_drop: firewall ACL denying 443 is ROOT; switch/router/ESXi/SYN/TPS alerts are downstream symptoms.",
        "pass_a": "pgw_fw_443_denies states ROOT bad ACL.",
        "pass_b": "Title TPS drop is business symptom; firewall is cause.",
        "adj": "Solo dual-pass; agreed firewall / pgw_fw_443_denies.",
    },
]


def _peer_hints(iid: str, cmp_rows: dict) -> dict:
    peer = cmp_rows.get(iid) or {}
    return {
        "lean_layer": (peer.get("lean") or {}).get("layer"),
        "lean_root": (peer.get("lean") or {}).get("root_alert"),
        "federated_layer": (peer.get("federated") or {}).get("layer"),
        "federated_root": (peer.get("federated") or {}).get("root_alert"),
        "openobserve_layer": (peer.get("openobserve") or {}).get("layer"),
        "openobserve_root": (peer.get("openobserve") or {}).get("root_alert"),
        "openobserve_has_narrative": (peer.get("openobserve") or {}).get("has_narrative"),
        "openobserve_snippet": ((peer.get("openobserve") or {}).get("cause_snippet") or "")[:240],
        "note": "Hints only — do not copy as GT without independent judgment.",
    }


def _triggers(inc: dict) -> list[str]:
    return sorted({t.get("alert_name") for t in (inc.get("triggers") or []) if t.get("alert_name")})


def main() -> int:
    cmp_rows = {r["id"]: r for r in json.loads(CMP.read_text()).get("rows", [])}
    written = 0
    for spec in LABELS:
        iid = spec["id"]
        inc_path = CORPUS / "incidents" / f"{iid}.json"
        inc = json.loads(inc_path.read_text())
        gt = {
            "incident_id": iid,
            "title": inc.get("title"),
            "status": "final",
            "stratum": spec["stratum"],
            "root_layer": spec["root_layer"],
            "root_alert": spec["root_alert"],
            "contributor_alerts": spec["contributor_alerts"],
            "confidence": spec["confidence"],
            "include_in_accuracy": spec["include_in_accuracy"],
            "evidence_note": spec["evidence_note"],
            "labels": {
                "A": {
                    "labeler_id": "unified-rca-solo-passa",
                    "root_layer": spec["root_layer"],
                    "root_alert": spec["root_alert"],
                    "confidence": spec["confidence"],
                    "evidence_note": spec["pass_a"],
                    "labeled_at": TS,
                },
                "B": {
                    "labeler_id": "unified-rca-solo-passb",
                    "root_layer": spec["root_layer"],
                    "root_alert": spec["root_alert"],
                    "confidence": spec["confidence"],
                    "evidence_note": spec["pass_b"],
                    "labeled_at": TS,
                },
            },
            "adjudication": {
                "resolved_by": "unified-rca-solo",
                "resolved_at": TS,
                "notes": spec["adj"] + " NOT independent human dual-label.",
            },
            "candidate_alerts": _triggers(inc),
            "peer_hints_not_gt": _peer_hints(iid, cmp_rows),
            "labeling_mode": "solo_dual_pass",
        }
        out = GT_DIR / f"{iid}.json"
        out.write_text(json.dumps(gt, indent=2) + "\n")
        written += 1
        print(f"wrote {out.name} ({spec['stratum']}, accuracy={spec['include_in_accuracy']})")

    # Refresh SAMPLE.json with all 29 incidents
    items = []
    for p in sorted(GT_DIR.glob("*.json")):
        if p.name in {"SAMPLE.json", "schema.json"}:
            continue
        d = json.loads(p.read_text())
        items.append({
            "id": d["incident_id"],
            "title": d.get("title"),
            "stratum": d.get("stratum"),
            "status": d.get("status"),
            "include_in_accuracy": d.get("include_in_accuracy"),
            "path": str(p.relative_to(REPO)),
        })
    manifest = {
        "mode": "option_b_convention_gt",
        "sample_size": len(items),
        "corpus": str(CORPUS),
        "rubric": "datasets/openobserve_incidents/v1/ground_truth/README.md",
        "items": items,
    }
    (GT_DIR / "SAMPLE.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Updated SAMPLE.json ({len(items)} items); wrote {written} new labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
