# Unified RCA — Documentation Navigation

**Start here.** One map for the whole repo. Canonical deep dives stay in linked files; this page is the index only.

---

## Quick routes (pick your goal)

| I want to… | Go to |
|------------|--------|
| Understand the whole PoC in one read | [`POC_BRIEFING.md`](./POC_BRIEFING.md) |
| See current status and phases | [`ROADMAP.md`](./ROADMAP.md) |
| Design **ingestion** (Vector → graphs for RCA) | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) |
| Learn Lean vs Federated (study notes) | [`RCA-learning-cheatsheet.md`](../RCA-learning-cheatsheet.md) |
| Run lean diagnose / API | [`../lean-pipeline/README.md`](../lean-pipeline/README.md) |
| Run bakeoff or read scoreboard | [`../benchmarking/README.md`](../benchmarking/README.md) → [`../benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) |
| Open comparative dashboard | [`../benchmarking/dashboard/README.md`](../benchmarking/dashboard/README.md) |
| Evaluate any RCA method fairly | [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) |
| Resolve terminology drift | [`GLOSSARY.md`](./GLOSSARY.md) |

---

## 1) PoC narrative & decisions (common)

| Document | Purpose |
|----------|---------|
| [`POC_BRIEFING.md`](./POC_BRIEFING.md) | End-to-end briefing (objective → design → bakeoff → conclusion); NotebookLM / slides |
| [`ROADMAP.md`](./ROADMAP.md) | Phases A–E, milestones, what is done vs deferred |
| [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) | Evaluation finding: lean favored on ObserveOps corpus (**not** a finalized product commitment) |
| [`README.md`](./README.md) | Four qualities, five roadblocks, **lean vs federated decision guide** (long-form) |
| [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) | Standard checklist for any RCA method (4 axes + 5 roadblocks + provenance) |
| [`GLOSSARY.md`](./GLOSSARY.md) | Tier namespaces, corpus names, verifiability vs main-path % |

**Product / algorithm depth (canonical Markdown):**

| Document | Purpose |
|----------|---------|
| [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) | Lean PRD (+ Appendix E: Dynatrace/Netdata placement) · [PDF](./Lean_RCA_PRD.pdf) · [DOCX](./Lean_RCA_PRD.docx) |
| [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md) | Plain-language lean guide · [PDF](./Lean_RCA_Simple_Guide.pdf) · [DOCX](./Lean_RCA_Simple_Guide.docx) |

---

## 2) Learning & study notes (repo root)

| Document | Purpose |
|----------|---------|
| [`RCA-learning-cheatsheet.md`](../RCA-learning-cheatsheet.md) | **Side-by-side revision** + ingestion cost PoC plan |
| [`Lean-decoded.md`](../Lean-decoded.md) | Lean study notes ([Implemented] / [Simulated] / [Aspirational]) |
| [`Federated-decoded.md`](../Federated-decoded.md) | Federated study notes (same tag system) |
| [`UC_LEARNING_BRAINSTORM.md`](./UC_LEARNING_BRAINSTORM.md) | UC-1..UC-5 + UC-3b learning frames (**not** bakeoff GT) |

**Visual simulation (sub-step guides):**

| Engine | Guide |
|--------|--------|
| Lean | [`../lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md`](../lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md) |
| Federated | [`../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md`](../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md) |

---

## 3) Corpus & use-cases

| Document | Purpose |
|----------|---------|
| [`rca-use-cases-only.md`](./rca-use-cases-only.md) | **Sole ObserveOps eval spec** (UC-1..UC-5, UC-3b, events schema) |
| [`../datasets/observeops/README.md`](../datasets/observeops/README.md) | Frozen bundle layout, v1.1.0, workflow |
| [`../datasets/observeops/COMPARISON_BENCHMARK.md`](../datasets/observeops/COMPARISON_BENCHMARK.md) | Bakeoff metric contract |
| [`../datasets/README.md`](../datasets/README.md) | Dataset area overview |
| [`../datasets/openobserve_incidents/README.md`](../datasets/openobserve_incidents/README.md) | OpenObserve incident corpus (separate from ObserveOps UC) |
| [`../datasets/openobserve_incidents/v1/ground_truth/README.md`](../datasets/openobserve_incidents/v1/ground_truth/README.md) | Option B GT convention |

Symlinks: [`../rca-use-cases-only.md`](../rca-use-cases-only.md), [`../ROADMAP.md`](../ROADMAP.md) → this folder.

---

## 4) Benchmarking & results

| Document | Purpose |
|----------|---------|
| [`../benchmarking/README.md`](../benchmarking/README.md) | Runners, two corpora, how to reproduce |
| [`../benchmarking/benchmark/TASKS.md`](../benchmarking/benchmark/TASKS.md) | ObserveOps benchmark task status |
| [`../benchmarking/benchmark/AGENTS.md`](../benchmarking/benchmark/AGENTS.md) | Agent continuation notes |
| [`../benchmarking/benchmark/FULLFLEDGED.md`](../benchmarking/benchmark/FULLFLEDGED.md) | Full-fledged benchmark checklist |

**ObserveOps UC bakeoff (canonical: `bakeoff-phase-b-002`):**

| Document | Purpose |
|----------|---------|
| [`../benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) | **Scoreboard** |
| [`../benchmarking/results/comparison/DECISION.md`](../benchmarking/results/comparison/DECISION.md) | Decision memo |
| [`../benchmarking/results/comparison/RUN_IDS.md`](../benchmarking/results/comparison/RUN_IDS.md) | Which run IDs to cite vs ignore |

**OpenObserve (do not merge with ObserveOps 5/5):**

| Document | Purpose |
|----------|---------|
| [`../benchmarking/results/openobserve/COMPARISON.md`](../benchmarking/results/openobserve/COMPARISON.md) | Peer agreement (Lean · Fed · OpenObserve) |
| [`../benchmarking/results/openobserve/GT_SCOREBOARD.md`](../benchmarking/results/openobserve/GT_SCOREBOARD.md) | Option B accuracy |
| [`../benchmarking/results/openobserve/ENGINE_SCOREBOARD.md`](../benchmarking/results/openobserve/ENGINE_SCOREBOARD.md) | Engine-pack bakeoff |
| [`../benchmarking/results/openobserve/GT_ANALYSIS.md`](../benchmarking/results/openobserve/GT_ANALYSIS.md) | GT methodology write-up |

**Dashboard:** [`../benchmarking/dashboard/README.md`](../benchmarking/dashboard/README.md) · serve on `:8765`

---

## 5) Lean pipeline

| Document | Purpose |
|----------|---------|
| [`../lean-pipeline/README.md`](../lean-pipeline/README.md) | CLI, HTTP API, layout, quick commands |
| [`../lean-pipeline/docs/README.md`](../lean-pipeline/docs/README.md) | Doc index for lean tree |
| [`../lean-pipeline/docs/ARCHITECTURE.md`](../lean-pipeline/docs/ARCHITECTURE.md) | Architecture, workflow, components |
| [`../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md`](../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md) | Limits, non-goals, deferred work |
| [`../lean-pipeline/core_engine/observeops/README.md`](../lean-pipeline/core_engine/observeops/README.md) | Engine-local quick reference |
| [`../lean-pipeline/deploy/README.md`](../lean-pipeline/deploy/README.md) | systemd / deploy |

---

## 6) Federated pipeline

| Document | Purpose |
|----------|---------|
| [`../federated-pipeline/README.md`](../federated-pipeline/README.md) | Repo layout, learning UI |
| [`../federated-pipeline/docs/README.md`](../federated-pipeline/docs/README.md) | Doc index for federated tree |
| [`../federated-pipeline/docs/ARCHITECTURE.md`](../federated-pipeline/docs/ARCHITECTURE.md) | Panorama → Murphy → Nezha architecture |
| [`../federated-pipeline/docs/ORCHESTRATOR.md`](../federated-pipeline/docs/ORCHESTRATOR.md) | Hop contracts, fusion, open decisions |
| [`../federated-pipeline/docs/STORAGE_TIERS.md`](../federated-pipeline/docs/STORAGE_TIERS.md) | Speed vs structural tier **design vision** |
| [`../federated-pipeline/docs/CAPACITY.md`](../federated-pipeline/docs/CAPACITY.md) | PoC EPS measurements |
| [`../federated-pipeline/docs/REQUIREMENTS.md`](../federated-pipeline/docs/REQUIREMENTS.md) | Federated PoC goals / status |
| [`../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md`](../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md) | Limits, Phase C/E deferrals |
| [`../federated-pipeline/docs/ARCHITECTURE_RATIONALE.md`](../federated-pipeline/docs/ARCHITECTURE_RATIONALE.md) | Novelty / paper gaps |

**Algorithm dissections:**

| Algorithm | Doc |
|-----------|-----|
| Panorama | [`../federated-pipeline/docs/dissections/Panorama_dissection.md`](../federated-pipeline/docs/dissections/Panorama_dissection.md) |
| Murphy | [`../federated-pipeline/docs/dissections/Murphy_dissection.md`](../federated-pipeline/docs/dissections/Murphy_dissection.md) |
| Nezha | [`../federated-pipeline/docs/dissections/Nezha-dissection.md`](../federated-pipeline/docs/dissections/Nezha-dissection.md) |
| Papers (PDFs) | [`../federated-pipeline/docs/papers/README.md`](../federated-pipeline/docs/papers/README.md) |

**Upstream algorithm READMEs:** [`murphy/`](../federated-pipeline/murphy/README.md) · [`Nezha/`](../federated-pipeline/Nezha/README.md) · [`panorama/`](../federated-pipeline/panorama/README.md)

---

## 7) Ingestion vs RCA (conceptual boundary)

| Topic | Where |
|-------|--------|
| **Vector ingestion design** (shared fabric → Lean / Federated artifacts) | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) |
| Skeleton configs (L0 lean-only / F1 dual-sink) | [`../ingestion-poc/vector/`](../ingestion-poc/vector/) |
| PoC uses **frozen bundles**, not full live ingest (today) | [`../datasets/observeops/README.md`](../datasets/observeops/README.md), [`Federated-decoded.md`](../Federated-decoded.md) §11, [`Lean-decoded.md`](../Lean-decoded.md) §4 |
| Federated ingest vision (Phase C deferred) | [`../federated-pipeline/docs/STORAGE_TIERS.md`](../federated-pipeline/docs/STORAGE_TIERS.md), [`LIMITATIONS_AND_FUTURE.md`](../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md) |
| Planned **ingestion cost comparison PoC** | [`RCA-learning-cheatsheet.md`](../RCA-learning-cheatsheet.md) §3 |
| **Learning links** (algorithms / papers / ingest primers) | [`RCA-learning-cheatsheet.md`](../RCA-learning-cheatsheet.md) §1d |

---

## 8) Historical / archive (do not use for current status)

| Document | Note |
|----------|------|
| [`../lean-pipeline/docs/lean_rca_prd_insights_ae5f991e.plan.md`](../lean-pipeline/docs/lean_rca_prd_insights_ae5f991e.plan.md) | Early PRD plan — superseded by ROADMAP + ARCHITECTURE |

---

## Repo map (folders)

```
Unified-RCA/
├── docs/NAVIGATION.md          ← you are here
├── docs/                       ← common PoC docs
├── Lean-decoded.md             ← study notes
├── Federated-decoded.md
├── RCA-learning-cheatsheet.md
├── datasets/observeops/        ← ObserveOps frozen corpus
├── datasets/openobserve_incidents/
├── lean-pipeline/              ← primary evaluation engine packaging
├── federated-pipeline/         ← comparator + optional hybrid track
├── benchmarking/               ← runners, results, dashboard
└── RCA-MANIM-Generator-System/ ← visual compiler (if present)
```

---

## Conventions (read once)

- **Canonical scoreboard:** `bakeoff-phase-b-002` → [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md)
- **Corpus v1.1.0:** UC-3b + `events.json` on UC-2/4/3b
- **Verdict phrase:** primary **evaluation** engine on ObserveOps corpus; **not** a finalized GTM commitment
- **Two corpora:** ObserveOps UC vs OpenObserve — **never merge** accuracy headlines

*Last indexed: 2026-07-16*
