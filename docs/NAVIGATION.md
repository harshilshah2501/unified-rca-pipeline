# Unified RCA — Documentation Navigation

**Start here** if you are opening the repo cold. This page is a **reading path**, not a dump of links. Deep dives stay in the linked files; follow the stages below in order until you have a mental model, then use [Quick routes](#10-quick-routes-lookup) as a lookup.

---

## Cognitive path (read this first)

```
What is this? → How does RCA work here? → See it run → What evidence exists?
      → Shared ingest fabric → Two engines → Code map → Where next? → Lookup
```

| Stage | Question in your head | Go to |
|-------|----------------------|--------|
| **1. Orient** | What does this PoC claim? | §1 below |
| **2. Workflow** | Ingest → … → Verify — where do we sit? | §2 |
| **3. Demo** | Can I *see* it without reading every design doc? | §3 |
| **4. Evidence** | What was measured, on what corpus? | §4 |
| **5. Ingest** | How does telemetry become RCA-ready? | §5 |
| **6. Engines** | Lean vs Federated — roles and docs | §6 |
| **7. Code** | Where is the code, and what do I run? | §7 · [`CODE_GUIDE.md`](./CODE_GUIDE.md) |
| **8. Depth** | Study notes, PRDs, vendor context | §8 |
| **9. Next** | What is open *now*? | §9 |
| **10. Lookup** | I already know what I want | [Quick routes](#10-quick-routes-lookup) |

**One-line product contract:** same incidents, two engines; shared Detect; Lean primary on classic infra; human GT stays authoritative.

---

## 1) Orient — what this PoC is

Read these before diving into folders.

| Document | Why first |
|----------|-----------|
| [`POC_BRIEFING.md`](./POC_BRIEFING.md) | End-to-end story: objective → design → bakeoff → conclusion (slides / NotebookLM) |
| [`ROADMAP.md`](./ROADMAP.md) | PoC **journey**: Compare → Deepen → Ship → Transfer → Connect (+ later Federate/Scale) |
| [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) | Lean favored on ObserveOps — **evaluation finding**, not a finalized GTM lock |
| [`GLOSSARY.md`](./GLOSSARY.md) | Tier namespaces, corpus names, verifiability vs “main-path %” — stop terminology drift early |
| [`README.md`](./README.md) | Four qualities, five roadblocks, lean vs federated decision guide (long-form) |

**Do not merge scoreboards:** ObserveOps UC bakeoff ≠ OpenObserve peer track ≠ Motadata L1 ≠ e-com checkout scenario. Treat them as separate surfaces.

---

## 2) Workflow — the mental model to keep

Canonical stages (product + PoC):

```
Ingest → Detect → Localize → Identify → Verify
```

| Document | Purpose |
|----------|---------|
| [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) | Workflow stages + stage readiness + **current next** (`LIVE` → `CHANGE`) |
| [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) | Fair compare: shared Detect, then engines diverge on Localize/Identify |
| [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) | Vendor gap: Step 1 “where” vs Step 2 “what happened there” (path / signature depth) |
| [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) | How we score *any* RCA method (4 axes + 5 roadblocks + provenance) |

Vendor landscape (context, not scoreboard): [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf) · [notes](./RCA_Vendor_Comparison_NOTES.md) · [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) · [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md)

---

## 3) See it — demo & PoC console

Best cold-start surface after you know the five stages.

| Document / surface | Purpose |
|--------------------|---------|
| [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) | Walkthrough: console hashes, 15–20 min demo script, bakeoff / Motadata / lab commands |
| [`../benchmarking/dashboard/README.md`](../benchmarking/dashboard/README.md) | PoC console — `http://127.0.0.1:8765/` |

Suggested console order: `#guide` → `#incident` (human report) → `#samples` → `#conduct` / `#overview` / `#verdict`. Optional: [`rca-workflow-sim.html`](../benchmarking/dashboard/rca-workflow-sim.html) if they ask *how* Localize differs.

```bash
.venv/bin/python benchmarking/dashboard/server.py
# → http://127.0.0.1:8765/
```

---

## 4) Evidence — corpora, bakeoffs, results

Understand **what** was measured before reading engine internals.

### Corpora

| Document | Purpose |
|----------|---------|
| [`rca-use-cases-only.md`](./rca-use-cases-only.md) | **Sole ObserveOps eval spec** (UC-1..UC-5, UC-3b, events schema) |
| [`../datasets/observeops/README.md`](../datasets/observeops/README.md) | Frozen bundle layout (v1.1.0) |
| [`../datasets/observeops/COMPARISON_BENCHMARK.md`](../datasets/observeops/COMPARISON_BENCHMARK.md) | Bakeoff metric contract |
| [`../datasets/README.md`](../datasets/README.md) | Dataset area overview |
| [`../datasets/ingest_samples/README.md`](../datasets/ingest_samples/README.md) | Ingest streams — ObserveOps replay + Motadata (local dumps) |
| [`../datasets/openobserve_incidents/README.md`](../datasets/openobserve_incidents/README.md) | OpenObserve corpus (**separate** from ObserveOps UC) |
| [`../datasets/openobserve_incidents/v1/ground_truth/README.md`](../datasets/openobserve_incidents/v1/ground_truth/README.md) | Option B GT convention |
| [`../datasets/scenario.md`](../datasets/scenario.md) | E-com cross-NUMA checkout scenario (design + Postgres dump) |
| [`ECOM_CHECKOUT_RCA_ANALYSIS.md`](./ECOM_CHECKOUT_RCA_ANALYSIS.md) | **Lean vs Federated write-up** for `ecom-numa-001` |
| [`RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md`](./RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md) | **Team reference:** Clock A/B · classes A–E · Grail/Smartscape/Vector · solution path |
| [`rca-data-lake-brainstorm.html`](./rca-data-lake-brainstorm.html) | Same — browser / [`:8765/rca-data-lake-brainstorm.html`](http://127.0.0.1:8765/rca-data-lake-brainstorm.html) |

### Benchmarking & scoreboards

| Document | Purpose |
|----------|---------|
| [`../benchmarking/README.md`](../benchmarking/README.md) | Runners, two corpora, how to reproduce |
| [`../benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) | **ObserveOps scoreboard** (cite `adr001-rerun-20260723`) |
| [`../benchmarking/results/comparison/DECISION.md`](../benchmarking/results/comparison/DECISION.md) | Decision memo |
| [`../benchmarking/results/comparison/RUN_IDS.md`](../benchmarking/results/comparison/RUN_IDS.md) | Which run IDs to cite vs ignore |
| [`../benchmarking/results/openobserve/COMPARISON.md`](../benchmarking/results/openobserve/COMPARISON.md) | OO peer agreement — do **not** merge with UC 5/5 |
| [`../_adhoc/ecom-gold-report-compare/COMPARISON.md`](../_adhoc/ecom-gold-report-compare/COMPARISON.md) | E-com pack scoreboard (ad-hoc) — analysis in [`ECOM_CHECKOUT_RCA_ANALYSIS.md`](./ECOM_CHECKOUT_RCA_ANALYSIS.md) |
| [`../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md`](../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md) | L0 vs F1 cost / EPS (pro6000) |

Task trackers (optional): [`TASKS.md`](../benchmarking/benchmark/TASKS.md) · [`AGENTS.md`](../benchmarking/benchmark/AGENTS.md) · [`FULLFLEDGED.md`](../benchmarking/benchmark/FULLFLEDGED.md)

Symlinks at repo root: [`../rca-use-cases-only.md`](../rca-use-cases-only.md), [`../ROADMAP.md`](../ROADMAP.md) → this folder.

---

## 5) Ingest — telemetry → RCA-ready artifacts

Conceptual boundary: **ingestion is not RCA**. Shared fabric feeds both engines.

| Topic | Where |
|-------|--------|
| Vector design (shared fabric → Lean / Federated artifacts) | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) |
| PoC plan (M1–M3, hardware, weekly gates) | [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) |
| `ingest.v1` contract + converters | [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) |
| Motadata → `ingest.v1` adapter | [`../ingestion-poc/adapters/`](../ingestion-poc/adapters/) |
| Shared threshold Detect | [`../ingestion-poc/detect/`](../ingestion-poc/detect/) |
| Vector skeletons (L0 / F1) | [`../ingestion-poc/vector/`](../ingestion-poc/vector/) |
| ObserveOps → `ingest.v1` replay | [`../ingestion-poc/replay/`](../ingestion-poc/replay/) |
| F1 smoke (sinks + shared detect) | [`../ingestion-poc/pipeline/f1_run.py`](../ingestion-poc/pipeline/f1_run.py) |
| N4/N5 writers (Fed stores + Lean bundles) | [`../ingestion-poc/builders/`](../ingestion-poc/builders/) |
| Federated justification / data gates | [`FEDERATED_JUSTIFICATION_REPORT.md`](./FEDERATED_JUSTIFICATION_REPORT.md) |

**Status snapshot:** Motadata L1 **7/7** · pro6000 cost/soak · Samples — details in [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md).

---

## 6) Engines — Lean (primary) & Federated (comparator)

### Lean

| Document | Purpose |
|----------|---------|
| [`../lean-pipeline/README.md`](../lean-pipeline/README.md) | CLI, HTTP API, quick commands |
| [`../lean-pipeline/docs/ARCHITECTURE.md`](../lean-pipeline/docs/ARCHITECTURE.md) | Architecture & workflow |
| [`../lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md`](../lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md) | Visual simulation of tiers |
| [`../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md`](../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md) | Limits & deferred work |
| [`../lean-pipeline/docs/README.md`](../lean-pipeline/docs/README.md) | Lean doc index |
| [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) | Product requirements · [PDF](./Lean_RCA_PRD.pdf) · [DOCX](./Lean_RCA_PRD.docx) |
| [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md) | Plain-language guide · [PDF](./Lean_RCA_Simple_Guide.pdf) · [DOCX](./Lean_RCA_Simple_Guide.docx) |

### Federated

| Document | Purpose |
|----------|---------|
| [`../federated-pipeline/README.md`](../federated-pipeline/README.md) | Layout, learning UI |
| [`../federated-pipeline/docs/ARCHITECTURE.md`](../federated-pipeline/docs/ARCHITECTURE.md) | Panorama → Murphy → Nezha |
| [`../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md`](../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md) | Visual simulation |
| [`../federated-pipeline/docs/ORCHESTRATOR.md`](../federated-pipeline/docs/ORCHESTRATOR.md) | Hop contracts, fusion |
| [`../federated-pipeline/docs/STORAGE_TIERS.md`](../federated-pipeline/docs/STORAGE_TIERS.md) | Speed vs structural tier (design vision) |
| [`../federated-pipeline/docs/CAPACITY.md`](../federated-pipeline/docs/CAPACITY.md) | PoC EPS measurements |
| [`../federated-pipeline/docs/README.md`](../federated-pipeline/docs/README.md) | Federated doc index |

**Algorithm dissections:** [Panorama](../federated-pipeline/docs/dissections/Panorama_dissection.md) · [Murphy](../federated-pipeline/docs/dissections/Murphy_dissection.md) · [Nezha](../federated-pipeline/docs/dissections/Nezha-dissection.md) · [papers](../federated-pipeline/docs/papers/README.md)

Upstream READMEs: [`murphy/`](../federated-pipeline/murphy/README.md) · [`Nezha/`](../federated-pipeline/Nezha/README.md) · [`panorama/`](../federated-pipeline/panorama/README.md)

Also useful: [`REQUIREMENTS.md`](../federated-pipeline/docs/REQUIREMENTS.md) · [`LIMITATIONS_AND_FUTURE.md`](../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md) · [`ARCHITECTURE_RATIONALE.md`](../federated-pipeline/docs/ARCHITECTURE_RATIONALE.md)

---

## 7) Code — where to look and what to run

Newcomers who will *change or run* code: start here after §§1–3 (or jump straight if you already know the product story).

| Document | Purpose |
|----------|---------|
| [`CODE_GUIDE.md`](./CODE_GUIDE.md) | **Code map** — folders, data→verdict flow, first-5 files per area, task recipes, env, pitfalls |

Area READMEs (after the guide): [`lean-pipeline/README.md`](../lean-pipeline/README.md) · [`federated-pipeline/README.md`](../federated-pipeline/README.md) · [`benchmarking/README.md`](../benchmarking/README.md) · [`ingestion-poc/*/README.md`](../ingestion-poc/)

---

## 8) Depth — learning & study notes

After the path above, these fill algorithm intuition (not status).

| Document | Purpose |
|----------|---------|
| [`RCA-learning-cheatsheet.md`](./learning/RCA-learning-cheatsheet.md) | Side-by-side revision + ingest cost PoC notes (study only) |
| [`Lean-decoded.md`](./learning/Lean-decoded.md) | Lean study notes (`[Implemented]` / `[Simulated]` / `[Aspirational]`) |
| [`Federated-decoded.md`](./learning/Federated-decoded.md) | Federated study notes (same tags) |
| [`UC_LEARNING_BRAINSTORM.md`](./UC_LEARNING_BRAINSTORM.md) | UC learning frames — **not** bakeoff GT |

---

## 9) Where next

| Document | Purpose |
|----------|---------|
| [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3 | **`LIVE`** (runbook ready — execute next week) → **`CHANGE`** · Motadata Bucket-3 `motadata-deps-001` authored |

Parked / stretch (same doc): gray-failure Panorama corpus, I2 path-diff, V1 maintain-only.

Also: [`LIVE_INGEST_RUNBOOK.md`](./LIVE_INGEST_RUNBOOK.md) · [`SLICE_A_OO_UC_FAIRNESS.md`](./SLICE_A_OO_UC_FAIRNESS.md) · [`OO_UC_FAIRNESS_CHECKLIST.md`](./OO_UC_FAIRNESS_CHECKLIST.md) · Lean/Fed/OO UC compare [`../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md)

---

## 10) Quick routes (lookup)

Use this **after** you have the map — or when you already know the goal.

| I want to… | Go to |
|------------|--------|
| **Understand the code layout** | [`CODE_GUIDE.md`](./CODE_GUIDE.md) |
| Explore / demo the PoC | [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) |
| Understand the whole PoC in one read | [`POC_BRIEFING.md`](./POC_BRIEFING.md) |
| See current status and phases | [`ROADMAP.md`](./ROADMAP.md) (journey stages) |
| RCA workflow + next actions | [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) |
| **LIVE ingest runbook** | [`LIVE_INGEST_RUNBOOK.md`](./LIVE_INGEST_RUNBOOK.md) |
| **Slice A OO UC fairness** | [`SLICE_A_OO_UC_FAIRNESS.md`](./SLICE_A_OO_UC_FAIRNESS.md) |
| **OO UC fairness checklist** | [`OO_UC_FAIRNESS_CHECKLIST.md`](./OO_UC_FAIRNESS_CHECKLIST.md) |
| Lean × Fed × OO UC compare | [`../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) |
| Design ingestion (Vector → graphs) | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) |
| Ingestion PoC plan (hardware + gates) | [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) |
| `ingest.v1` format / converters | [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) |
| Fair Lean vs Federated (shared Detect) | [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) |
| **Incident Analysis** (human report UI) | PoC console [`#incident`](http://127.0.0.1:8765/#incident) — ObserveOps UC + Motadata L1 |
| **RCA workflow sim** (Detect → Lean / Fed Localize) | [`../benchmarking/dashboard/rca-workflow-sim.html`](../benchmarking/dashboard/rca-workflow-sim.html) → `:8765/rca-workflow-sim.html` |
| Fault buckets vs Dynatrace/Datadog | [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) · [`fault_taxonomy.py`](../benchmarking/benchmark/fault_taxonomy.py) |
| Vendor RCA public eval (DD/DT) | [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) |
| L0 vs F1 cost report (pro6000) | [`cost_report.md`](../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md) |
| Two-step RCA white space | [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) |
| Learn Lean vs Federated | [`learning/RCA-learning-cheatsheet.md`](./learning/RCA-learning-cheatsheet.md) |
| Run lean diagnose / API | [`../lean-pipeline/README.md`](../lean-pipeline/README.md) |
| Run bakeoff / scoreboard | [`../benchmarking/README.md`](../benchmarking/README.md) → [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) |
| Open PoC console | [`dashboard/README.md`](../benchmarking/dashboard/README.md) → `:8765` (`#guide` · `#incident` · `#samples` · `#conduct` · [`rca-workflow-sim`](../benchmarking/dashboard/rca-workflow-sim.html)) |
| Evaluate any RCA method fairly | [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) |
| Resolve terminology drift | [`GLOSSARY.md`](./GLOSSARY.md) |
| Vendor landscape survey (PDF) | [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf) · [notes](./RCA_Vendor_Comparison_NOTES.md) |

---

## Repo map (folders)

```
Unified-RCA/
├── docs/NAVIGATION.md          ← you are here (doc path)
├── docs/CODE_GUIDE.md          ← code path for newcomers
├── docs/                       ← common PoC docs
├── docs/learning/              ← study notes (not scoreboards)
├── datasets/observeops/        ← ObserveOps frozen corpus (bakeoff)
├── datasets/ingest_samples/    ← ingest.v1 streams (UC replay + Motadata)
├── datasets/openobserve_incidents/
├── ingestion-poc/              ← Vector / detect / replay / adapters
├── lean-pipeline/              ← primary evaluation engine packaging
├── federated-pipeline/         ← comparator + optional hybrid track
└── benchmarking/               ← runners, results, dashboard
```

---

## Conventions (read once)

- **Canonical scoreboard:** `adr001-rerun-20260723` → [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) (ADR-era snapshot: `bakeoff-phase-b-002`)
- **Corpus v1.1.0:** UC-3b + `events.json` on UC-2/4/3b
- **Verdict phrase:** primary **evaluation** engine on ObserveOps; **not** a finalized GTM commitment
- **Two corpora:** ObserveOps UC vs OpenObserve — **never merge** accuracy headlines
- **Ingest progress:** Motadata L1 **7/7** · cost_report · Samples — [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) · [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md)

### Historical / archive (do not use for current status)

| Document | Note |
|----------|------|
| [`lean_rca_prd_insights_ae5f991e.plan.md`](../lean-pipeline/docs/lean_rca_prd_insights_ae5f991e.plan.md) | Early PRD plan — superseded by ROADMAP + ARCHITECTURE |

*Last indexed: 2026-07-28 (Incident Analysis · Motadata L1 in `#incident` · plain L0/F1 / Detect gloss)*
