#!/usr/bin/env python3
"""Rebuild benchmarking/dashboard/data.json from latest comparison JSONs."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UC = REPO / "benchmarking" / "results" / "comparison" / "comparison.json"
OO = REPO / "benchmarking" / "results" / "openobserve" / "comparison.json"
OO_GT = REPO / "benchmarking" / "results" / "openobserve" / "gt_scoreboard.json"
OO_ENGINE = REPO / "benchmarking" / "results" / "openobserve" / "engine_scoreboard.json"
OUT = REPO / "benchmarking" / "dashboard" / "data.json"


def main() -> int:
    uc = json.loads(UC.read_text())
    oo = json.loads(OO.read_text())
    oo_rows = []
    for r in oo["rows"]:
        a = r.get("agree_layer") or {}
        p = r.get("picks_incident_title") or {}
        oo_eng = r.get("openobserve") or {}
        oo_rows.append(
            {
                "id": r["id"],
                "title": r["title"],
                "oo_layer": oo_eng.get("layer"),
                "lean_layer": r["lean"]["layer"],
                "fed_layer": r["federated"]["layer"],
                "lean_root": r["lean"].get("root_alert"),
                "fed_root": r["federated"].get("root_alert"),
                "oo_root": oo_eng.get("root_alert"),
                "oo_snippet": (oo_eng.get("cause_snippet") or "")[:160],
                "oo_has_narrative": oo_eng.get("has_narrative"),
                "agree_lf": a.get("lean_federated"),
                "agree_lo": a.get("lean_openobserve"),
                "agree_fo": a.get("federated_openobserve"),
                "triple": a.get("triple"),
                "triggers": r["trigger_count"],
                "lean_title_pick": p.get("lean"),
                "fed_title_pick": p.get("federated"),
                "oo_title_pick": p.get("openobserve"),
                "multi": r["multi_trigger"],
            }
        )
    uc_rows = []
    for r in uc.get("rows", []):
        uc_rows.append(
            {
                "uc_id": r.get("uc_id"),
                "gt": (r.get("ground_truth") or {}).get("root_ci"),
                "fed": (r.get("federated") or {}).get("root_ci"),
                "lean": (r.get("lean") or {}).get("root_ci"),
                "winner": r.get("winner"),
                "fed_obs": (r.get("federated") or {}).get("observations"),
                "lean_obs": (r.get("lean") or {}).get("observations"),
                "lean_tier": (r.get("lean") or {}).get("evidentiary_tier"),
                "fed_tier": (r.get("federated") or {}).get("evidentiary_tier"),
            }
        )
    oo_gt = json.loads(OO_GT.read_text()) if OO_GT.exists() else None
    oo_engine = json.loads(OO_ENGINE.read_text()) if OO_ENGINE.exists() else None
    payload = {
        "uc": {
            "generated_at": uc.get("generated_at"),
            "run_id": uc.get("run_id_filter"),
            "axes": uc.get("axes"),
            "summary": uc.get("summary"),
            "rows": uc_rows,
        },
        "openobserve": {
            "generated_at": oo.get("generated_at"),
            "evaluation": oo.get("evaluation"),
            "summary": oo.get("summary"),
            "behavioral_edge": oo.get("behavioral_edge_lean_vs_federated"),
            "closest_to_openobserve": oo.get("closest_to_openobserve_layer"),
            "overall_better": oo.get("overall_better"),
            "by_layer": oo.get("by_openobserve_layer") or oo.get("by_reference_layer"),
            "rows": oo_rows,
        },
        "openobserve_gt": {
            "generated_at": (oo_gt or {}).get("generated_at"),
            "evaluation": (oo_gt or {}).get("evaluation"),
            "summary": (oo_gt or {}).get("summary"),
            "excluded": (oo_gt or {}).get("excluded"),
            "rows": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "stratum": r.get("stratum"),
                    "eligible": r["include_in_accuracy"],
                    "gt_layer": r["gt"]["root_layer"],
                    "gt_root": r["gt"]["root_alert"],
                    "lean_layer_hit": r["lean"]["layer_hit"],
                    "lean_root_hit": r["lean"]["root_hit"],
                    "fed_layer_hit": r["federated"]["layer_hit"],
                    "fed_root_hit": r["federated"]["root_hit"],
                    "oo_layer_hit": r["openobserve"]["layer_hit"],
                    "oo_root_hit": r["openobserve"]["root_hit"],
                    "lean_root": r["lean"].get("root_alert"),
                    "fed_root": r["federated"].get("root_alert"),
                    "oo_root": r["openobserve"].get("root_alert"),
                }
                for r in ((oo_gt or {}).get("rows") or [])
            ],
        }
        if oo_gt
        else None,
        "openobserve_engine": {
            "generated_at": oo_engine.get("generated_at"),
            "run_id": oo_engine.get("run_id_filter"),
            "evaluation": oo_engine.get("evaluation"),
            "summary": oo_engine.get("summary"),
            "reproducibility_sources": oo_engine.get("reproducibility_sources"),
        }
        if oo_engine
        else None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    OUT.write_text(text)
    js = OUT.with_suffix(".js")
    js.write_text("window.RCA_DASHBOARD_DATA = " + json.dumps(payload) + ";\n")
    print(f"Wrote {OUT}")
    print(f"Wrote {js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
