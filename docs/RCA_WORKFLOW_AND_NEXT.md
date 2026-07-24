# RCA Workflow & Next Actions

**Doc ownership (read this first)**

| Doc | Owns |
|-----|------|
| **This file** | Product **workflow stages** + **current next** (`LIVE`, `CHANGE`) — Connect stage |
| [`ROADMAP.md`](./ROADMAP.md) | PoC **journey** (Compare → Deepen → Ship → Transfer → Connect) |
| [`POC_BRIEFING.md`](./POC_BRIEFING.md) | Engine-decision narrative → [`ADR-001`](./ADR-001-lean-primary-engine.md) |
| [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) · [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) | Ingest design deep-dives |

**Naming:** `LIVE` / `CHANGE` are Connect-stage actions here. They are **not** old “Phase A” bakeoff IDs (retired — see ROADMAP [legacy map](./ROADMAP.md#legacy-map-old-letter-phases)).

**Related:** [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) · [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) · [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) · [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md)

*Last synced: 2026-07-24 — LIVE prep (runbook + Vector live configs); Motadata `motadata-deps-001` Bucket-3; OO fairness checklist; ecom WARN→events closed. Connect execute: `LIVE` next week → `CHANGE`.*

---

## 1. Canonical workflow (stable)

```
Ingest → Detect → Localize → Identify → Verify
```

| Stage | Job (one sentence) | Lean path (current) | Federated path (current / optional) |
|-------|--------------------|---------------------|-------------------------------------|
| **Ingest** | Collect & normalize telemetry into RCA-ready artifacts | Bundle / Vector L0 | Same stream → F1 speed + structural sinks |
| **Detect** | Decide *something is wrong* and raise a seed | Threshold / events / alerts → `A-ANOM` + `A-SEED` | Shared detect **or** Panorama gray-failure |
| **Localize** | Decide *which CI / service* | Best-first walk + rules | Murphy (+ fusion) |
| **Identify** | Name *what kind of failure* (and optionally *which path*) | Signature / rules | Signature + optional **Nezha / execution-pattern diff** (Step 2) |
| **Verify** | Decide how strongly we claim cause | Evidentiary Tier 1/2/3 + CARE → scoped causal | Murphy posterior / fusion confidence; bakeoff GT |

**Vendor survey:** most commercial tools automate **Detect + Localize** well; deep **Identify** (execution-path) stays partly manual — [`two-step-rca-white-space.md`](./two-step-rca-white-space.md).

| Two-step language | Five-stage stages |
|-------------------|-------------------|
| Step 1 “where” | Detect → Localize |
| Step 2 “what happened there” | Identify → (optional deep path) Verify |

**Decision rules**

1. **Lean-primary** for classic infra until data says otherwise ([ADR-001](./ADR-001-lean-primary-engine.md)).
2. **Same ingest stream / F1 sinks** for both engines ([PIPELINE_PARITY.md](./PIPELINE_PARITY.md)).
3. **Federated / Step-2 path diff** only after [`FEDERATED_JUSTIFICATION_REPORT.md`](./FEDERATED_JUSTIFICATION_REPORT.md) gates.
4. Prefer **Detect cheap wins** before expensive Identify depth.

---

## 2. Stage readiness (workflow lens only)

How ready each **workflow stage** is — not a duplicate of the ROADMAP journey. For Compare → Connect status → [`ROADMAP.md`](./ROADMAP.md).

| Stage | Ready? | One-line evidence |
|-------|--------|-------------------|
| **Localize + Identify** (UC) | **Yes (PoC)** | UC 5/5 both engines; Lean packaged; ADR-001 |
| **Verify** (UC tiers / GT) | **Yes (PoC)** | Bakeoff + CARE / Tier-3; maintain run IDs |
| **Detect** | **Partial** | Shared threshold + change/error-rate classes; live collectors → **LIVE**; Panorama → data-gated |
| **Ingest** | **Partial (lab strong)** | `ingest.v1` + F1/N4/N5 + Motadata L1 **7/7** human-confirmed; live non-replay → **LIVE** |
| **Identify Step-2** (path diff) | **No (stretch)** | Needs traces + baselines — see ROADMAP deferred / white-space doc |

**Motadata L1** (separate from UC): 7 packs · Lean/Fed **7/7** · GT confirmed on `#samples`. Do not merge with UC 5/5.

---

## 3. Next actions (open only)

| ID | Action | Verify | Exit |
|----|--------|--------|------|
| **LIVE** | Live ingest smoke — syslog or Prometheus → Vector → same F1 sinks | Lab once; seed + sink counts | Noted in Conduct / lab artifact · **prep Done** — [`LIVE_INGEST_RUNBOOK.md`](./LIVE_INGEST_RUNBOOK.md); execute next week |
| **CHANGE** | Real change feed → `change_near_onset` (D2 product gap) | Human confirms `change_context` on ≥1 pack | Bucket 4 usable on Motadata or UC-linked sample |

**Prep closed 2026-07-24 (not LIVE itself):** LIVE runbook + Vector live configs · OO fairness checklist · ecom WARN→events guard · Motadata Bucket-3 pack `motadata-deps-001` (authored GT; confirm on `#samples`).

**Already met (do not re-plan here):** Motadata network breadth + harder multi GT (ping-002/003/004 + multi-001). Optional further Bucket-3 packs remain stretch after Samples confirm on deps-001.

**Blocked on data (listed in ROADMAP as deferred / stretch):** Panorama gray-failure · path-diff Identify · cyclic deps · fleet Nezha · 1B EPS.

```bash
.venv/bin/python benchmarking/dashboard/server.py   # → :8765/#samples
```
