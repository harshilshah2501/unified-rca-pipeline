# Unified RCA — Documentation Navigation

**Start here** if you are opening the repo cold. This page is a **reading path**, not a dump of links. Deep dives stay in the linked files; follow the stages below in order until you have a mental model, then use [Quick routes](#10-quick-routes-lookup) as a lookup.

**Edit hygiene:** [`REPO_HYGIENE.md`](./REPO_HYGIENE.md) — canonical paths, do-not-edit trees, handoff zip policy.

**Where files live (so the folder does not look like one flat dump):**

| Folder | Open for |
|--------|----------|
| [`fabric/`](./fabric/) | E1–E5 / Pillar A∥B visuals + deep dive |
| [`observeops/`](./observeops/) | Our HLD, Fusion, LLDs |
| [`motadata/`](./motadata/) | 3-pillars teaching HTML + study notes |
| [`reference/`](./reference/) | Bakeoff / Lean–Federated history |
| [`vendors/`](./vendors/) | Dynatrace / Datadog / Edge Delta labs |
| Hub root | Reading path, ingest contracts, roadmap — see links below |

Flat `docs/<filename>` paths still work (symlinks). Prefer the folder paths when editing.

---

## Cognitive path (read this first)

```
Always-on fabric (E1–E5) → Pillar A∥B contracts → Detect onward → Reference bakeoff / vendors
```

| Stage | Question in your head | Go to |
|-------|----------------------|--------|
| **1. Orient** | Motadata fabric + graph/sketch freeze — where do I start? | §1 below |
| **2. Workflow** | Ingest → … → Verify — where do we sit? | §2 |
| **3. Demo** | Can I *see* it without reading every design doc? | §3 |
| **4. Evidence** | What was measured, on what corpus? | §4 |
| **5. Ingest** | How does telemetry become RCA-ready? | §5 |
| **6. Engines** | Lean vs Federated — **reference** evaluation track | §6 |
| **7. Code** | Where is the code, and what do I run? | §7 · [`CODE_GUIDE.md`](./CODE_GUIDE.md) |
| **8. Depth** | Study notes, PRDs, vendor context | §8 |
| **9. Next** | What is open *now*? | §9 |
| **10. Lookup** | I already know what I want | [Quick routes](#10-quick-routes-lookup) |

**One-line product contract (current stage):** ObserveOps **E1–E5 always-on fabric** with Motadata **Pillar A (sketches) ∥ Pillar B (graph)** after Identity; Detect onward reads those stores. Lean-vs-Federated bakeoff remains **evaluation history** (ADR-001), not the Motadata lock list.

---

## 1) Orient — Tier 1 only, then depth

**Locked Tier 1 list:** [`observeops/OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md) — six Tier-1 pages (everyone ×5, implementers ×1 entry) + Tier-2 **I/O chain** for wire records.

**Door:** [`observeops/observeops-pipeline-hld.html`](./observeops/observeops-pipeline-hld.html) (`:8765/observeops-pipeline-hld.html`) — one hub with **Overview · Workflow · GraphWriter · Diagnose** tabs. Old URLs (`motadata-unified-pipeline-workflow`, `graphwriter-io-walkthrough`, `checkout-diagnose-walkthrough`) redirect into this page.

| Band | Pages |
|------|--------|
| **A · Everyone** | Fusion · Pipeline HLD MD · Data shape journey · GRAPH_QNA · Glossary |
| **B · Implementers** | Pillar A+B README · [Pillar B TEAM_WALKTHROUGH](../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md) · Tier 2 I/O chain |

**Tier 2 (after Tier 1):** [`observeops/hld-archive.html`](./observeops/hld-archive.html) · [`fabric/README.md`](./fabric/README.md) · contract brief · LLDs · Motadata scope HTML.

<details>
<summary>Legacy orient table (full link dump — prefer Tier 1 doc above)</summary>

| Path | Document | Why |
|------|----------|-----|
| **1 · Try** | [`observeops/observeops-fusion-guide.html`](./observeops/observeops-fusion-guide.html) | Click a Detect class; walk E1–E11 in/out |
| **2 · Spec** | [`observeops/OBSERVEOPS_PIPELINE_HLD.md`](./observeops/OBSERVEOPS_PIPELINE_HLD.md) | Canonical written spec · ADRs · NFR |
| **3 · Fabric** | Hub [#fabric](observeops/observeops-pipeline-hld.html#fabric) · [`fabric/data-shape-journey.html`](./fabric/data-shape-journey.html) | Data shape, `map/`/`history/`, GRAPH_QNA |
| **4 · Build** | [`motadata/motadata-3pillars-implementation-scope.html`](./motadata-3pillars-implementation-scope.html) · [`observeops/observeops-shift-left-architecture.html`](./observeops/observeops-shift-left-architecture.html) | Kickoff scope · Node/Gateway/SaaS locus |
| **5 · Archive** | [`observeops/hld-archive.html`](./observeops/hld-archive.html) | Searchable deep dives (Motadata, LLDs, print) |

</details>

**Fabric visuals** (ordered): [`fabric/README.md`](./fabric/README.md) — film 1 (Node or Collector → SaaS → Detect) → film 2 (storm → CaseSeed → WorkingSet → LeafClaim) → data shape journey → E1–E5 architecture → map/history → exemplars.

**Pillar A∥B implementation** (contracts + code):

| Document | Why |
|----------|-----|
| [`pillar-ab-implementation/`](../pillar-ab-implementation/README.md) | Code slice — pillar-a / pillar-b / integration |
| [`pillar-b/docs/TEAM_WALKTHROUGH.md`](../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md) | **Pillar B PoC one-stop** — demo script, admit, run |
| [`pillar-b/docs/README.md`](../pillar-ab-implementation/pillar-b/docs/README.md) | Pillar B package doc map (reading order) |
| [`pillar-b/docs/MAP_P1_FABRIC_EVAL.md`](../pillar-ab-implementation/pillar-b/docs/MAP_P1_FABRIC_EVAL.md) | Build/maintain + walk eval criteria |
| [`pillar-b/docs/Codebase-go-through.md`](../pillar-ab-implementation/pillar-b/docs/Codebase-go-through.md) | Module tour of GraphWriter + walk |
| [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) | Sit-down lock list — CI catalog, fifteen edges, `sketch.v1` |
| [`GRAPH_QNA.md`](./GRAPH_QNA.md) | Fabric Q&A with table of contents |
| [`MAP_WRITE_READ_RECORD.md`](../pillar-ab-implementation/contracts/MAP_WRITE_READ_RECORD.md) | Pillar B map write/read JSON |
| [`fabric/INGEST_FACT_KINDS_DISCUSSION.md`](./fabric/INGEST_FACT_KINDS_DISCUSSION.md) | Fact kind discussion — logs → `event`; `signal_class` spoken alias |
| [`fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md`](./fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) | Pillar A deep dive |
| [`fabric/end-to-end-algorithm-walkthrough.md`](./fabric/end-to-end-algorithm-walkthrough.md) | Admit → Detect door C |

Hub doors: [Our HLD → Pillar B PoC](./observeops/observeops-pipeline-hld.html#pillar-b-poc) · [Archive → Pillar B PoC](./observeops/hld-archive.html#pillar-b-poc).

**Motadata teaching** (also on archive):

| Document | Why |
|----------|-----|
| [`motadata/motadata-3pillars-architecture.html`](./motadata/motadata-3pillars-architecture.html) | 3 pillars explained on E1–E11 |
| [`motadata/motadata-3pillars-vs-shift-left.html`](./motadata/motadata-3pillars-vs-shift-left.html) | Job map — PDF vs our pipeline |
| [`motadata/motadata-3pillars-study-qna.html`](./motadata/motadata-3pillars-study-qna.html) | Study Q&A · conflict register |
| [`MOTADATA_3PILLARS_MERGED_SCOPE.md`](./MOTADATA_3PILLARS_MERGED_SCOPE.md) | Merged implementation scope |

**Hygiene & terms:** [`REPO_HYGIENE.md`](./REPO_HYGIENE.md) · [`observeops/urca-glossary.html`](./observeops/urca-glossary.html) · [`observeops/OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./observeops/OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) (map chapter, Draft) · [`observeops/OBSERVEOPS_USE_CASES.md`](./observeops/OBSERVEOPS_USE_CASES.md)

**Reference (evaluation history — not the Motadata lock list):** [`reference/POC_BRIEFING.md`](./reference/POC_BRIEFING.md) · [`ROADMAP.md`](./ROADMAP.md) · [`reference/ADR-001-lean-primary-engine.md`](./reference/ADR-001-lean-primary-engine.md) · see [§ Reference](#reference-evaluation-history--vendors) below.

**Do not merge scoreboards:** ObserveOps UC bakeoff ≠ OpenObserve peer track ≠ Motadata L1 ≠ e-com checkout scenario.

**Superseded:** [`MOTADATA_3PILLARS_PILLAR_SPLIT_SCOPE_OKR.md`](./MOTADATA_3PILLARS_PILLAR_SPLIT_SCOPE_OKR.md) → use [`MOTADATA_3PILLARS_MERGED_SCOPE.md`](./MOTADATA_3PILLARS_MERGED_SCOPE.md).

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
| [`rca-pipeline-step-io.md`](./rca-pipeline-step-io.md) | Full step I/O reference (§3.2b) — Detect → Curate → Tailor sequencing, topology as sibling not gate |
| [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) | How we score *any* RCA method (4 axes + 5 roadblocks + provenance) |

Vendor landscape (context, not scoreboard): [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf) · [notes](./RCA_Vendor_Comparison_NOTES.md) · [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) · [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md)

---

## 3) See it — demo & PoC console

Best cold-start surface after you know the five stages.

| Document / surface | Purpose |
|--------------------|---------|
| [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) | Walkthrough: console hashes, 15–20 min demo script, bakeoff / Motadata / lab commands |
| [`../benchmarking/dashboard/README.md`](../benchmarking/dashboard/README.md) | PoC console — `http://127.0.0.1:8765/` |

Suggested console order: `#guide` → `#incident` (human report) → `#samples` → `#conduct` / `#overview` / `#verdict`. Optional: [`rca-workflow-sim.html`](./rca-workflow-sim.html) (`:8765/rca-workflow-sim.html`) if they ask *how* Localize differs.

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
| [`index.html`](./index.html) | **Browser docs hub** — [`:8765/docs.html`](http://127.0.0.1:8765/docs.html) |
| [`COMPARABLE_PIPELINE_DT_DD.md`](./COMPARABLE_PIPELINE_DT_DD.md) | **DT vs DD after independent unveils** (same-scenario lab) · [HTML](./comparable-pipeline-dt-dd.html) · [`:8765`](http://127.0.0.1:8765/comparable-pipeline-dt-dd.html) · §0 geometry includes Edge Delta (not a third lab) · [ED hub](./ed-ai-team-hub.html) |
| [`DT_DD_COMPARATIVE_STUDY.md`](./DT_DD_COMPARATIVE_STUDY.md) | **Inception, philosophy, and terminology** — company history, why each vendor's vocabulary exists, narrated 11-stage walkthrough |
| [`observability-generations-dt-dd.html`](./observability-generations-dt-dd.html) | **Obs 1.0 / 2.0 / 3.0 must-pass criteria** · why DD/DT are hybrids (not clean 2.0/3.0) · [`:8765`](http://127.0.0.1:8765/observability-generations-dt-dd.html) |
| [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) | **Thesis (MD):** Clock A → OneAgent/Smartscape/Grail · Phase 2 glossary · [HTML](./dynatrace-production-pipeline.html) · [`:8765`](http://127.0.0.1:8765/dynatrace-production-pipeline.html) |
| [`FEDERATED_VS_DT_PIPELINE_GAPS.md`](./FEDERATED_VS_DT_PIPELINE_GAPS.md) | **Gap map:** Federated Part 1 vs DT 5+3+3 · [HTML](./federated-vs-dt-pipeline-gaps.html) · [`:8765`](http://127.0.0.1:8765/federated-vs-dt-pipeline-gaps.html) · §8 Motadata FR/AC alignment |
| [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](./multi-telemetry-rca-functional-and-acceptance-criteria.md) | Motadata ObserveOps **acceptance** FRs/ACs · [visual HTML](./multi-telemetry-rca-fac.html) · [`:8765`](http://127.0.0.1:8765/multi-telemetry-rca-fac.html) · architecture in gap map §2/§8 |
| [`dt-davis-category-hub.html`](./dt-davis-category-hub.html) | **DT hub:** Davis event categories · Thesis / Breakdown / Dual-track / Timeline per category · [`:8765`](http://127.0.0.1:8765/dt-davis-category-hub.html) |
| [`dynatrace-production-pipeline.html`](./dynatrace-production-pipeline.html) | Dynatrace **Thesis** (shared; `?cat=`) · [`:8765`](http://127.0.0.1:8765/dynatrace-production-pipeline.html) |
| [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) | Dynatrace **Breakdown** canvas (shared; `?cat=`) · [`:8765`](http://127.0.0.1:8765/eleven-subsystem-mechanisms.html) |
| [`eleven-subsystem-mechanisms-storyboard.html`](./eleven-subsystem-mechanisms-storyboard.html) | Storyboard variant of the Breakdown canvas — mechanisms along the flow, sequential panels · [`:8765`](http://127.0.0.1:8765/eleven-subsystem-mechanisms-storyboard.html) |
| [`dt-e2e-smartscape-grail.html`](./dt-e2e-smartscape-grail.html) | **Dual-track** Smartscape ∥ Grail journey (shared; `?cat=`) · [`:8765`](http://127.0.0.1:8765/dt-e2e-smartscape-grail.html) |
| [`dt-lab-timeline-code-level.html`](./dt-lab-timeline-code-level.html) | **ERROR Timeline** Observed · P-260817 · [`:8765`](http://127.0.0.1:8765/dt-lab-timeline-code-level.html) |
| [`dt-lab-timeline-slowdown.html`](./dt-lab-timeline-slowdown.html) | **SLOWDOWN Timeline** Observed · P-260820 · [`:8765`](http://127.0.0.1:8765/dt-lab-timeline-slowdown.html) |
| [`dt-cat-monitoring-unavailable-lab.html`](./dt-cat-monitoring-unavailable-lab.html) | **MONITORING_UNAVAILABLE** Timeline · **Observed P-260826** · [prompt](./agent-tasks/dt-monitoring-unavailable.md) |
| [`dt-cat-availability-lab.html`](./dt-cat-availability-lab.html) | **AVAILABILITY** Timeline · **Observed P-260831** · organic cascade **P-260854** · [prompt](./agent-tasks/dt-availability.md) |
| [`dt-cat-resource-contention-lab.html`](./dt-cat-resource-contention-lab.html) | **RESOURCE_CONTENTION** Timeline · **Observed (negative Detect)** · [prompt](./agent-tasks/dt-resource-contention.md) |
| [`dt-agent-tasks.html`](./dt-agent-tasks.html) | Agent-task archive (all five Observed) · [`:8765`](http://127.0.0.1:8765/dt-agent-tasks.html) |
| [`dd-detect-category-hub.html`](./dd-detect-category-hub.html) | **DD hub:** Detect categories — ERROR · SLOWDOWN full depth (Thesis/Breakdown/Three-rail/Timeline/MTL/Bits) + RESOURCE_CONTENTION/AVAILABILITY/MONITORING_UNAVAILABLE Timeline-only (local, MCP pending) · shared Method/IPO/Doors guide · [`:8765`](http://127.0.0.1:8765/dd-detect-category-hub.html) |
| [`dd-lab-timeline-resource-contention.html`](./dd-lab-timeline-resource-contention.html) | **RESOURCE_CONTENTION** Timeline · **Observed (local, negative Detect)** · [prompt](./agent-tasks/dd-resource-contention.md) |
| [`dd-lab-timeline-availability.html`](./dd-lab-timeline-availability.html) | **AVAILABILITY** Timeline · **Observed (local)** · caller 502 · [prompt](./agent-tasks/dd-availability.md) |
| [`dd-lab-timeline-monitoring-unavailable.html`](./dd-lab-timeline-monitoring-unavailable.html) | **MONITORING_UNAVAILABLE** Timeline · **Observed (local)** · HTTP stays 200 · [prompt](./agent-tasks/dd-monitoring-unavailable.md) |
| [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) | **Datadog Thesis (MD):** Agent → Metrics/APM/Logs · Monitors+Watchdog · [HTML](./datadog-production-pipeline.html) (`?cat=`) |
| [`datadog-production-pipeline.html`](./datadog-production-pipeline.html) | Same — browser / [`:8765/datadog-production-pipeline.html`](http://127.0.0.1:8765/datadog-production-pipeline.html) |
| [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html) | Datadog **Breakdown** · bifurcated step cards under each animation · [`:8765`](http://127.0.0.1:8765/datadog-subsystem-mechanisms.html) (`?cat=`) |
| [`dd-e2e-metrics-traces-logs.html`](./dd-e2e-metrics-traces-logs.html) | **Three-rail journey** — animated how M∥APM∥Logs write along stages (shared) · [`:8765`](http://127.0.0.1:8765/dd-e2e-metrics-traces-logs.html) |
| [`dd-error-mtl-dissection.html`](./dd-error-mtl-dissection.html) | **ERROR · MTL workbook** — emit · queries · MCP counts · leaf (not the journey) · [`:8765`](http://127.0.0.1:8765/dd-error-mtl-dissection.html?cat=error) |
| [`dd-behind-the-scenes-error.html`](./dd-behind-the-scenes-error.html) | **Behind the scenes** ERROR — screenshot Metrics∥Logs∥Traces → lean 8-stage IPO → Bits · [`:8765`](http://127.0.0.1:8765/dd-behind-the-scenes-error.html?cat=error) |
| [`dd-bits-error-review.html`](./dd-bits-error-review.html) | **Bits** peer tab (ERROR packaging · Hypothesis Tree · 500 vs 502) · [`:8765`](http://127.0.0.1:8765/dd-bits-error-review.html?cat=error) |
| [`dd-lab-timeline-error.html`](./dd-lab-timeline-error.html) | **ERROR Timeline** Observed · KeyError 500 · `env:rca-lab-e3` · MCP 2026-08-10 · [`:8765`](http://127.0.0.1:8765/dd-lab-timeline-error.html) |
| [`dd-lab-timeline-slowdown.html`](./dd-lab-timeline-slowdown.html) | **SLOWDOWN Timeline** Observed · ledger-scan · [`:8765`](http://127.0.0.1:8765/dd-lab-timeline-slowdown.html) |
| [`datadog-lab-evidence-mtl-error-2026-08-10.md`](./datadog-lab-evidence-mtl-error-2026-08-10.md) | **Primary** ERROR MTL MCP appendix (e3) · [HTML](./datadog-lab-evidence-mtl-error-2026-08-10.html) · [`:8765`](http://127.0.0.1:8765/datadog-lab-evidence-mtl-error-2026-08-10.html) |
| [`datadog-lab-evidence-mtl-error-2026-08-07.md`](./datadog-lab-evidence-mtl-error-2026-08-07.md) | Prior ERROR MTL appendix (retired env) · [HTML](./datadog-lab-evidence-mtl-error-2026-08-07.html) |
| [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md) | ERROR lab APM appendix · [HTML](./datadog-lab-evidence-2026-08-04.html) · [`:8765`](http://127.0.0.1:8765/datadog-lab-evidence-2026-08-04.html) |
| [`datadog-tenant-evidence-2026-08-03.md`](./datadog-tenant-evidence-2026-08-03.md) | Dated MCP snapshot grounding Observed claims |
| [`ed-ai-team-hub.html`](./ed-ai-team-hub.html) | **ED hub:** Thesis → Breakdown → Dual-layer → Timeline · 10 use-case switcher (not ERROR/SLOWDOWN) · [`:8765`](http://127.0.0.1:8765/ed-ai-team-hub.html) |
| [`edgedelta-production-pipeline.html`](./edgedelta-production-pipeline.html) | **01 Thesis** — dual-layer fabric map (no `?uc=`) · [`:8765`](http://127.0.0.1:8765/edgedelta-production-pipeline.html) |
| [`edgedelta-subsystem-mechanisms.html`](./edgedelta-subsystem-mechanisms.html) | **02 Breakdown** — native stage IPO canvas · [`:8765`](http://127.0.0.1:8765/edgedelta-subsystem-mechanisms.html) |
| [`ED_CANVASES.md`](./ED_CANVASES.md) | **ED canvas subset** — E1–E11 scenarios · production deploy · AI Team use cases · parent catalog [`CANVASES.md`](./CANVASES.md) |
| [`ed-e2e-pipelines-team.html`](./ed-e2e-pipelines-team.html) | **03 Dual-layer** — Pipelines ∥ AI Team journey · [`:8765`](http://127.0.0.1:8765/ed-e2e-pipelines-team.html) |
| [`ed-lab-timeline.html`](./ed-lab-timeline.html) | **04 Timeline** — 14 Aug empty fabric · 17 Aug Node lab · [`:8765`](http://127.0.0.1:8765/ed-lab-timeline.html) |
| [`ed-portal-walkthrough.html`](./ed-portal-walkthrough.html) | **Portal** — numbered `app.edgedelta.com` clicks per use case · [`:8765`](http://127.0.0.1:8765/ed-portal-walkthrough.html) |
| [`ed-supported-scenarios.html`](./ed-supported-scenarios.html) | **ED catalogs:** Packs shape → monitors notice → use cases investigate · [MD](./EDGEDELTA_SUPPORTED_SCENARIOS.md) · [`:8765`](http://127.0.0.1:8765/ed-supported-scenarios.html) |
| [`ed-lab-setup.html`](./ed-lab-setup.html) | **ED lab setup:** Node lab 2026-08-17 · [run note](./edgedelta-lab-run-2026-08-17.md) · [MD](./EDGEDELTA_LAB_SETUP.md) · [`:8765`](http://127.0.0.1:8765/ed-lab-setup.html) |
| [`edgedelta-uc9-github-2026-08-17.md`](./edgedelta-uc9-github-2026-08-17.md) | **UC9 Observed:** Daily GitHub Engineering Risk Report 2026-08-17 |
| [`edgedelta-lab-run-2026-08-17.md`](./edgedelta-lab-run-2026-08-17.md) | **Node lab 2026-08-17:** WSL k3d ingest · RTX · analysis |
| [`EDGEDELTA_PRODUCTION_PIPELINE.md`](./EDGEDELTA_PRODUCTION_PIPELINE.md) | **Edge Delta Thesis (MD):** Pipelines ∥ AI Team · Overview/Issues · [HTML](./edgedelta-production-pipeline.html) |
| [`edgedelta-tenant-evidence-2026-08-14.md`](./edgedelta-tenant-evidence-2026-08-14.md) | Dated UI snapshot grounding Observed claims |
| [`RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md`](./RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md) | **Team reference:** Clock A/B · classes A–E · Grail/Smartscape/Vector · [HTML](./rca-data-lake-brainstorm.html) · [Clock A/B cards](./clock-ab-stage-reference.html) |
| [`rca-data-lake-brainstorm.html`](./rca-data-lake-brainstorm.html) | Same — browser / [`:8765/rca-data-lake-brainstorm.html`](http://127.0.0.1:8765/rca-data-lake-brainstorm.html) |

### Benchmarking & scoreboards

| Document | Purpose |
|----------|---------|
| [`../benchmarking/README.md`](../benchmarking/README.md) | Runners, two corpora, how to reproduce |
| [`../benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) | **ObserveOps scoreboard** (cite `adr001-rerun-20260723`) |
| [`../benchmarking/results/comparison/DECISION.md`](../benchmarking/results/comparison/DECISION.md) | Decision memo |
| [`../benchmarking/results/comparison/RUN_IDS.md`](../benchmarking/results/comparison/RUN_IDS.md) | Which run IDs to cite vs ignore |
| [`../benchmarking/results/openobserve/COMPARISON.md`](../benchmarking/results/openobserve/COMPARISON.md) | OO peer agreement — do **not** merge with UC 5/5 |
| [`../_archive/_adhoc/ecom-gold-report-compare/COMPARISON.md`](../_archive/_adhoc/ecom-gold-report-compare/COMPARISON.md) | E-com pack scoreboard (ad-hoc) — analysis in [`ECOM_CHECKOUT_RCA_ANALYSIS.md`](./ECOM_CHECKOUT_RCA_ANALYSIS.md) |
| [`../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md`](../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md) | L0 vs F1 cost / EPS (pro6000) |

Task trackers (optional): [`TASKS.md`](../benchmarking/benchmark/TASKS.md) · [`AGENTS.md`](../benchmarking/benchmark/AGENTS.md) · [`FULLFLEDGED.md`](../benchmarking/benchmark/FULLFLEDGED.md)

Symlinks at repo root: [`../rca-use-cases-only.md`](../rca-use-cases-only.md), [`../ROADMAP.md`](../ROADMAP.md) → this folder.

---

## 5) Ingest — telemetry → RCA-ready artifacts

Conceptual boundary: **ingestion is not RCA**. Shared fabric feeds both engines.

**Vendor-first (production reference, no Lean/Fed):** read Dynatrace then Datadog before designing our Vector/sinks analogue — same Clock A skeleton, different Localize philosophy. Edge Delta is a **third independent lens** (edge pipelines + AI Team); do not treat it as a Vector drop-in.

| Topic | Where |
|-------|--------|
| **Dynatrace Clock A map + walkthroughs** | [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) · [HTML](./dynatrace-production-pipeline.html) |
| **Datadog Detect hub + native map** | [`dd-detect-category-hub.html`](./dd-detect-category-hub.html) · [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) · [HTML](./datadog-production-pipeline.html) · [mechanisms](./datadog-subsystem-mechanisms.html) · [three-rail](./dd-e2e-metrics-traces-logs.html) · [Behind the scenes](./dd-behind-the-scenes-error.html) · [ERROR MTL](./dd-error-mtl-dissection.html) · [ERROR Bits](./dd-bits-error-review.html) · [ERROR timeline](./dd-lab-timeline-error.html) · [SLOWDOWN timeline](./dd-lab-timeline-slowdown.html) |
| **Edge Delta AI Team hub + native map** | [`ed-ai-team-hub.html`](./ed-ai-team-hub.html) · [Thesis](./edgedelta-production-pipeline.html) · [Breakdown](./edgedelta-subsystem-mechanisms.html) · [Dual-layer](./ed-e2e-pipelines-team.html) · [Timeline](./ed-lab-timeline.html) · [Portal](./ed-portal-walkthrough.html) · [MD](./EDGEDELTA_PRODUCTION_PIPELINE.md) — independent third lens; geometry compare on [DT vs DD §0](./comparable-pipeline-dt-dd.html) |
| Dynatrace lab (stages 0–5, P-26076) | [`../labs/dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md`](../labs/dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md) |
| Datadog lab (FE→product→inventory) | [`../labs/datadog-rca-lab/DATADOG_RCA_REFERENCE.md`](../labs/datadog-rca-lab/DATADOG_RCA_REFERENCE.md) · [ERROR](./dd-lab-timeline-error.html) · [MTL](./dd-error-mtl-dissection.html) · [SLOWDOWN](./dd-lab-timeline-slowdown.html) |
| [`COMPARABLE_PIPELINE_DT_DD.md`](./COMPARABLE_PIPELINE_DT_DD.md) · [HTML](./comparable-pipeline-dt-dd.html) | DT vs DD after independent unveils · P-26084 lab · §0 Edge Delta geometry |
| **Hosted docs index (browser hub)** | [`index.html`](./index.html) · [`:8765/docs.html`](http://127.0.0.1:8765/docs.html) — [Our HLD hub](http://127.0.0.1:8765/observeops-pipeline-hld.html) · DT / DD / ED / compare |
| Vector design (shared fabric → Lean / Federated artifacts) | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) |
| PoC plan (M1–M3, hardware, weekly gates) | [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) |
| `ingest.v1` contract + converters | [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) |
| Collect LLD (E1) | [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) — **Done** |
| Normalize / Identity LLD (E2) | [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) — **Done** |
| Topology LLD (E3) + graph HLD | [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) (Draft) · [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) · [Fusion guide](./observeops-fusion-guide.html) |
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
| [`learning/README.md`](./learning/README.md) | Learning-folder index (non-authoritative — points back here for canonical numbers) |
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
| **Know what to edit where** | [`REPO_HYGIENE.md`](./REPO_HYGIENE.md) |
| **Fabric Q&A (E1–E5)** | [`GRAPH_QNA.md`](./GRAPH_QNA.md) |
| **Graph/sketch sit-down brief** | [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) |
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
| **Understand our HLD** | [Our HLD hub (Overview · Workflow · GraphWriter · Diagnose)](http://127.0.0.1:8765/observeops-pipeline-hld.html) → [Fusion](http://127.0.0.1:8765/observeops-fusion-guide.html) → [Pipeline HLD](./observeops/OBSERVEOPS_PIPELINE_HLD.md) → [Data shape journey](http://127.0.0.1:8765/data-shape-journey.html) → [#fabric](http://127.0.0.1:8765/observeops-pipeline-hld.html#fabric). [shift-left](http://127.0.0.1:8765/observeops-shift-left-architecture.html) · [archive](http://127.0.0.1:8765/hld-archive.html) · [GRAPH_QNA](./GRAPH_QNA.md) |
| **Demo Motadata Pillar B PoC** (knowledge graph) | [Our HLD → Pillar B PoC](http://127.0.0.1:8765/observeops-pipeline-hld.html#pillar-b-poc) · [`TEAM_WALKTHROUGH.md`](../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md) · [`make test-all`](../pillar-ab-implementation/pillar-b/poc/) |
| **Understand Datadog production fabric** | [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) · [HTML `:8765`](http://127.0.0.1:8765/datadog-production-pipeline.html) · [mechanisms](http://127.0.0.1:8765/datadog-subsystem-mechanisms.html) · [evidence](./datadog-tenant-evidence-2026-08-03.md) |
| **Understand Edge Delta (third independent lens)** | [`ed-ai-team-hub.html`](./ed-ai-team-hub.html) · [Thesis](http://127.0.0.1:8765/edgedelta-production-pipeline.html) · [Breakdown](http://127.0.0.1:8765/edgedelta-subsystem-mechanisms.html) · [Portal](http://127.0.0.1:8765/ed-portal-walkthrough.html) · [`ed-lab-setup.html`](./ed-lab-setup.html) · [evidence](./edgedelta-tenant-evidence-2026-08-14.md) |
| Ingestion PoC plan (hardware + gates) | [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) |
| `ingest.v1` format / converters | [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) |
| Fair Lean vs Federated (shared Detect) | [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) |
| **Incident Analysis** (human report UI) | PoC console [`#incident`](http://127.0.0.1:8765/#incident) — ObserveOps UC + Motadata L1 |
| **RCA workflow sim** (Detect → Lean / Fed Localize) | [`rca-workflow-sim.html`](./rca-workflow-sim.html) → `:8765/rca-workflow-sim.html` |
| Fault buckets vs Dynatrace/Datadog | [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) · [`fault_taxonomy.py`](../benchmarking/benchmark/fault_taxonomy.py) |
| Vendor RCA public eval (DD/DT) | [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) |
| L0 vs F1 cost report (pro6000) | [`cost_report.md`](../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md) |
| Two-step RCA white space | [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) |
| Learn Lean vs Federated | [`learning/RCA-learning-cheatsheet.md`](./learning/RCA-learning-cheatsheet.md) |
| Run lean diagnose / API | [`../lean-pipeline/README.md`](../lean-pipeline/README.md) |
| Run bakeoff / scoreboard | [`../benchmarking/README.md`](../benchmarking/README.md) → [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) |
| Open PoC console | [`dashboard/README.md`](../benchmarking/dashboard/README.md) → `:8765` (`#guide` · `#incident` · `#samples` · `#conduct` · [`rca-workflow-sim`](./rca-workflow-sim.html)) |
| Evaluate any RCA method fairly | [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) |
| Resolve terminology drift | [`urca-glossary.html`](./urca-glossary.html) · [`GLOSSARY.md`](./GLOSSARY.md) |
| Vendor landscape survey (PDF) | [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf) · [notes](./RCA_Vendor_Comparison_NOTES.md) |

---

## Hub publish (edit here only)

| Location | Role |
|----------|------|
| [`docs/`](./) | Canonical hub HTML / MD / CSS / JS |
| [`../pillar-ab-implementation/`](../pillar-ab-implementation/README.md) | Pillar A+B contracts, discussion, PoCs |
| [`../KR Plan/`](../KR Plan/) | Management PDFs / OKRs (binaries) |
| [`../benchmarking/dashboard/`](../benchmarking/dashboard/) | HTTP host on `:8765` — **symlinks only**, never a content fork |

Do **not** edit under `_archive/` or regenerate frozen export trees for day-to-day hub work.

---

## Repo map (folders)

```
Unified-RCA/
├── docs/                       ← hub HTML/MD (canonical) · NAVIGATION · GRAPH_QNA · REPO_HYGIENE
├── pillar-ab-implementation/   ← Motadata Pillar A+B (contracts SoT, pillar-a/b packages, integration)
├── KR Plan/                    ← management PDFs + OKR xlsx
├── labs/                       ← edgedelta + datadog-rca-lab + dynatrace-rca-lab
├── ingestion-poc/              ← Vector / detect / replay / adapters
├── lean-pipeline/              ← evaluation engine (reference)
├── federated-pipeline/         ← comparator + optional hybrid track (reference; Nezha is large)
├── benchmarking/               ← runners, results, thin dashboard host (:8765)
├── datasets/                   ← observeops corpus + ingest_samples (large dumps local)
└── _archive/                   ← parked — do not edit for live hub
```

---

## Conventions (read once)

- **Canonical scoreboard:** `adr001-rerun-20260723` → [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) (ADR-era snapshot: `bakeoff-phase-b-002`)
- **Corpus v1.1.0:** UC-3b + `events.json` on UC-2/4/3b
- **Verdict phrase:** primary **evaluation** engine on ObserveOps; **not** a finalized GTM commitment
- **Two corpora:** ObserveOps UC vs OpenObserve — **never merge** accuracy headlines
- **Ingest progress:** Motadata L1 **7/7** · cost_report · Samples — [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) · [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md)

### Reference — evaluation history / vendors

These docs stay in the repo. They are **not** the Motadata graph/sketch lock list.

| Document | Note |
|----------|------|
| [`POC_BRIEFING.md`](./POC_BRIEFING.md) · [`ROADMAP.md`](./ROADMAP.md) | Bakeoff journey narrative |
| [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) | Lean favored on ObserveOps — evaluation finding |
| [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) · [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) | Shared Detect + fault buckets vs DT/DD |
| [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) · [`FEDERATED_VS_DT_PIPELINE_GAPS.md`](./FEDERATED_VS_DT_PIPELINE_GAPS.md) | Engine PRD / gap maps |
| [`GLOSSARY.md`](./GLOSSARY.md) · vendor lab MD/HTML under `docs/` | Bakeoff + lab teaching |
| [`lean_rca_prd_insights_ae5f991e.plan.md`](../lean-pipeline/docs/lean_rca_prd_insights_ae5f991e.plan.md) | Early PRD plan — superseded by ROADMAP + ARCHITECTURE |
| [`_archive/`](../_archive/) | Parked — do not edit for live `:8765` |

---

*Last indexed: 2026-08-27 (Motadata E1–E5 / GRAPH_QNA / REPO_HYGIENE; bakeoff demoted to Reference; package docs are symlinks).*
