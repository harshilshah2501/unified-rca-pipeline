#!/usr/bin/env python3
"""Initialize Option-B convention GT drafts for the stratified OpenObserve sample."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "datasets" / "openobserve_incidents" / "v1"
GT_DIR = CORPUS / "ground_truth"
CMP = REPO / "benchmarking" / "results" / "openobserve" / "comparison.json"

# Diversified 12 — archetypes, not near-duplicates
SAMPLE: list[dict] = [
    {
        "id": "3GAjVpGX95c6Sr0X6kpdEn0YI9g",
        "stratum": "decoy_multi_cpu_title_storage",
    },
    {
        "id": "3GARI4ZcuhvZSBauIl4tLhBeH5N",
        "stratum": "decoy_multi_slo_title_dns_topo",
    },
    {
        "id": "3GARrIHDnfvHKz3jTKUoeQNwHjw",
        "stratum": "decoy_multi_lean_fed_disagree_oo",
    },
    {
        "id": "3GAYuTBAC1zaXtslES1iFWh5yKA",
        "stratum": "decoy_multi_slo_filesystem",
    },
    {
        "id": "3GAKkjsKwCe0m9Y9k6qzqN6hJ8N",
        "stratum": "multi_network_topo",
    },
    {
        "id": "3GAmXmWYoBO6IY4q1ji0QzCl3CG",
        "stratum": "multi_firewall_topo",
    },
    {
        "id": "3G8HsK79FfddyepBxqtx6OmeTIQ",
        "stratum": "single_no_narrative_cpu",
    },
    {
        "id": "3GA9Ehaso21qDpWNlx9B55mZWzZ",
        "stratum": "single_database_with_narrative",
    },
    {
        "id": "3GABGbdhy3cIOxLutKax6lC87qK",
        "stratum": "single_db_lean_fed_disagree_oo",
    },
    {
        "id": "3GAJqvDUEt9zeZqtY0hlZRDtIDy",
        "stratum": "single_app_surge_vs_db_layer",
    },
    {
        "id": "3GAShBeLwPjoysc3uGDATR5XAiZ",
        "stratum": "single_dns",
    },
    {
        "id": "3GAYvCuRe6l8hqwpyJIOncHvw0m",
        "stratum": "multi_app_slo_lean_fed_disagree_oo",
    },
]


def _blank_labeler() -> dict:
    return {
        "labeler_id": "",
        "root_layer": None,
        "root_alert": None,
        "confidence": None,
        "evidence_note": "",
        "labeled_at": "",
    }


def main() -> int:
    cmp_rows = {
        r["id"]: r for r in json.loads(CMP.read_text()).get("rows", [])
    }
    GT_DIR.mkdir(parents=True, exist_ok=True)
    sample_out = []

    for spec in SAMPLE:
        iid = spec["id"]
        inc_path = CORPUS / "incidents" / f"{iid}.json"
        if not inc_path.exists():
            raise SystemExit(f"missing incident {inc_path}")
        inc = json.loads(inc_path.read_text())
        peer = cmp_rows.get(iid) or {}
        triggers = sorted(
            {
                t.get("alert_name")
                for t in (inc.get("triggers") or [])
                if t.get("alert_name")
            }
        )
        draft = {
            "incident_id": iid,
            "title": inc.get("title"),
            "status": "pending",
            "stratum": spec["stratum"],
            "root_layer": None,
            "root_alert": None,
            "contributor_alerts": [],
            "confidence": None,
            "include_in_accuracy": False,
            "evidence_note": "",
            "labels": {"A": _blank_labeler(), "B": _blank_labeler()},
            "adjudication": {
                "resolved_by": "",
                "resolved_at": "",
                "notes": "",
            },
            "candidate_alerts": triggers,
            "peer_hints_not_gt": {
                "lean_layer": (peer.get("lean") or {}).get("layer"),
                "lean_root": (peer.get("lean") or {}).get("root_alert"),
                "federated_layer": (peer.get("federated") or {}).get("layer"),
                "federated_root": (peer.get("federated") or {}).get("root_alert"),
                "openobserve_layer": (peer.get("openobserve") or {}).get("layer"),
                "openobserve_root": (peer.get("openobserve") or {}).get("root_alert"),
                "openobserve_has_narrative": (peer.get("openobserve") or {}).get(
                    "has_narrative"
                ),
                "openobserve_snippet": (
                    (peer.get("openobserve") or {}).get("cause_snippet") or ""
                )[:240],
                "note": "Hints only — do not copy as GT without independent judgment.",
            },
        }
        out = GT_DIR / f"{iid}.json"
        if out.exists():
            existing = json.loads(out.read_text())
            if existing.get("status") in ("draft", "conflict", "final", "excluded"):
                # Preserve in-progress / finished labels; refresh peer hints only
                existing["peer_hints_not_gt"] = draft["peer_hints_not_gt"]
                existing["candidate_alerts"] = triggers
                existing["stratum"] = spec["stratum"]
                out.write_text(json.dumps(existing, indent=2) + "\n")
                sample_out.append(
                    {
                        "id": iid,
                        "title": existing.get("title"),
                        "stratum": spec["stratum"],
                        "status": existing.get("status"),
                        "path": str(out.relative_to(REPO)),
                    }
                )
                continue
        out.write_text(json.dumps(draft, indent=2) + "\n")
        sample_out.append(
            {
                "id": iid,
                "title": inc.get("title"),
                "stratum": spec["stratum"],
                "status": "pending",
                "path": str(out.relative_to(REPO)),
            }
        )
        print(f"wrote {out.name} ({spec['stratum']})")

    manifest = {
        "mode": "option_b_convention_gt",
        "sample_size": len(sample_out),
        "corpus": str(CORPUS),
        "rubric": "datasets/openobserve_incidents/v1/ground_truth/README.md",
        "items": sample_out,
    }
    (GT_DIR / "SAMPLE.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {GT_DIR / 'SAMPLE.json'} ({len(sample_out)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
