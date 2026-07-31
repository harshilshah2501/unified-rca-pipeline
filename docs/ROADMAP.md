# Unified RCA — End-to-End Roadmap

**Doc ownership**

| Doc | Owns |
|-----|------|
| **This file** | The **journey** of the PoC (named stages below) + what’s done / deferred |
| [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) | Product workflow (`Ingest→…→Verify`) + **today’s next** (`LIVE`, `CHANGE`) |
| [`POC_BRIEFING.md`](./POC_BRIEFING.md) | Stakeholder narrative (UC decision + Motadata story) |

**How to read this page:** follow the stages top → bottom. Names are the story. Old letter codes (Phase A/B/C/D/E) are retired; a [legacy map](#legacy-map-old-letter-phases) is at the bottom if you hit them in older notes.

**Corpora (do not merge scoreboards):** UC-1..UC-5 → [`rca-use-cases-only.md`](./rca-use-cases-only.md). Motadata L1 → briefing §5.2 · WORKFLOW §2.

**Status (2026-07-27):** **Compare → Deepen → Ship → Transfer** ✅. **Fair Lean×Fed×OO** on UC: Lean/Fed **5/5**, OO **1/5** ([`LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md)). **Connect:** LIVE **prep Done** ([`LIVE_INGEST_RUNBOOK.md`](./LIVE_INGEST_RUNBOOK.md)) — **execute lab smoke next week**; then **CHANGE**. Lean = primary evaluation engine ([ADR-001](./ADR-001-lean-primary-engine.md)). Optional later: Federate · Scale · Step-2 path diff · Panorama.

---

## Cognitive journey (the whole PoC)

```
 1 COMPARE     Fair Lean vs Federated on frozen UC tickets
       ↓
 2 DEEPEN      Make Lean’s evidence path PRD-grade (tiers / CARE / sigs)
       ↓
 3 SHIP        Package the winner (CLI / HTTP / systemd)
       ↓
 4 TRANSFER    Same engines on real Motadata export packs (human GT)
       ↓
 5 CONNECT     Live collectors + real change feed   ← you are here (WORKFLOW)
       │
       ├─► later: FEDERATE   (microservice / dual-store path — optional)
       └─► later: SCALE      (hyperscaler EPS vision — not PoC-blocking)
```

| # | Stage | Question it answers | Status |
|---|-------|---------------------|--------|
| 1 | **Compare** | Which engine wins a *fair* UC bakeoff? | **Done** → ADR-001 |
| 2 | **Deepen** | Is Lean’s verdict path deep enough to trust? | **Done** |
| 3 | **Ship** | Can we call Lean as a product-shaped API? | **Done** |
| 4 | **Transfer** | Does it still work on *real* Motadata packs? | **Done** (L1 7/7) |
| 5 | **Connect** | Can live telemetry / change feeds enter the same fabric? | **Open** → [`WORKFLOW`](./RCA_WORKFLOW_AND_NEXT.md) |
| — | **Federate** *(optional)* | Do we need the full Federated ingest/store track? | Deferred |
| — | **Scale** *(optional)* | What does 1B EPS sizing need? | Deferred |

---

## 1. Compare — fair engine bakeoff ✅

**Goal:** Same frozen UC-1..UC-5 bundles → score Lean vs Federated → pick a primary *evaluation* engine.

| Work | Status | Exit |
|------|--------|------|
| Fix Federated fusion gaps (UC-2/UC-3 Murphy posteriors) | Done | No lean-heuristic rescue on fusion path |
| Four-axis compare + reproducibility (N=20) | Done | Scoreboard in COMPARISON.md |
| Matched re-run | Done | `bakeoff-phase-a-001` → later `bakeoff-phase-b-002` |
| Record verdict | Done | [`DECISION.md`](../benchmarking/results/comparison/DECISION.md) · [ADR-001](./ADR-001-lean-primary-engine.md) |

**Headline:** accuracy **5/5** both; Lean wins repro / audit / cost.

---

## 2. Deepen — Lean evidence path ✅

**Goal:** On the *same* UC corpus, bring Lean to PRD-shaped Localize → Identify → Verify (not a shallow smoke).

| Work | Status | Exit |
|------|--------|------|
| Evidentiary tiers labeled 1 / 2 / 3 | Done | UC-1/UC-3 → Tier 3; UC-2/4/5 → Tier 1 |
| Scoped causal only when CARE fires | Done | `lean/causal.py` |
| Signatures match use-case AND-rules | Done | Negative tests |
| Observation efficiency vs naive BFS | Done | Fields on verdict + compare |
| Continuous causal memory | Deferred | Optional after Ship |

**Canonical scoreboard:** `adr001-rerun-20260723` — [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md). ADR-era decision snapshot: `bakeoff-phase-b-002`.

---

## 3. Ship — package Lean ✅

**Goal:** Primary evaluation engine is callable and deployable.

| Work | Status | Exit |
|------|--------|------|
| ADR-001 recorded | Done | [`ADR-001`](./ADR-001-lean-primary-engine.md) |
| CLI + HTTP API | Done | `python -m lean_rca diagnose\|serve` |
| SRE report fields | Done | Chain / blast / remediation on verdicts |
| systemd unit | Done | `lean-pipeline/deploy/systemd/lean-rca.service` |

```bash
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report
./lean-pipeline/scripts/serve-rca.sh   # :8780
```

---

## 4. Transfer — real Motadata export ✅

**Goal:** After the UC engine call, prove Localize/Identify on packs cut from a real Motadata dump (human GT; separate scoreboard).

| Work | Status | Exit |
|------|--------|------|
| Motadata → `ingest.v1` + F1 / N4 / N5 | Done | Lab fabric |
| Motadata L1 bakeoff | Done | Lean **7/7** · Federated **7/7** |
| Human confirm on `#samples` | Done | ping breadth + multi-001 (+ APM/CPU) |

Details: [`POC_BRIEFING.md`](./POC_BRIEFING.md) §5.2 · [`results/motadata/COMPARISON.md`](../benchmarking/results/motadata/COMPARISON.md).

---

## 5. Connect — live front door (current)

**Goal:** Non-replay collectors and a real change signal into the same Detect fabric.

Owned as **open next** in [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3:

| ID | Meaning | Prep |
|----|---------|------|
| **LIVE** | Syslog or Prometheus → Vector → F1 sinks | Runbook + live Vector/compose **ready** — run next week |
| **CHANGE** | CI/CD or config audit → `change_near_onset` | After LIVE |

Do not duplicate task tables here — WORKFLOW is canonical for Connect.

---

## Later · Federate *(optional / deferred)*

Only if a microservice / code-path track is prioritized (not classic ObserveOps).

| Work | Exit |
|------|------|
| Live normalizer dual-stream (speed + structural) | Write path proven |
| Stable Nezha live path | No silent Drain3 fallback on reference |
| Open orchestrator decisions written | ORCHESTRATOR.md |
| Server-class EPS measurement | Measured E_node |
| ~100K EPS sustained PoC | p99 SLO on Dragonfly |

---

## Later · Scale *(explicitly not PoC-blocking)*

| Work | Exit |
|------|------|
| Event size / encoding measured | Bytes/event |
| Structural tier capacity model | Real entity counts |
| 1B EPS fleet sizing | Formula from measured E_node only |

---

## Foundation milestones (repo / corpus)

Supporting “plumbing” completed along the journey (not a second roadmap):

| Milestone | Status |
|-----------|--------|
| Repo layout (`lean` / `federated` / `datasets` / `benchmarking`) | Done |
| UC corpus frozen (schema + manifest) | Done |
| Federated PoC orchestrator + demos | Done |
| Lean ObserveOps engine core | Done |
| Docs consolidation under `docs/` | Done |
| Laptop / lab EPS samples (WSL + pro6000 cost soak) | Partial / measured — not production sizing |

---

## Non-goals

- Treating Nezha boutique / TrainTicket accuracy as ObserveOps acceptance
- DeathStarBench as an ObserveOps gate
- 1B EPS build-out before server-class measurement
- Auto-remediation
- Merging Motadata % into the UC ADR scoreboard

---

## Quick pointers

| Need | Where |
|------|-------|
| Docs home | [`NAVIGATION.md`](./NAVIGATION.md) |
| Briefing | [`POC_BRIEFING.md`](./POC_BRIEFING.md) |
| Workflow + **current next** | [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) |
| Ingest design | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) |
| Use-cases | [`rca-use-cases-only.md`](./rca-use-cases-only.md) |
| ADR | [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) |

---

## Legacy map (old letter phases)

Older docs said “Phase A/B/C/D/E” and “A1/B2…”. Prefer the names above.

| Old letter | New stage name |
|------------|----------------|
| Phase A (+ A1–A4) | **Compare** |
| Phase B (+ B1–B4; B5 deferred) | **Deepen** (B5 still deferred under Deepen) |
| Phase D (+ D1–D4) | **Ship** |
| *(Motadata work / M10)* | **Transfer** |
| *(WORKFLOW LIVE/CHANGE)* | **Connect** |
| Phase C | **Later · Federate** |
| Phase E | **Later · Scale** |
