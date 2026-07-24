# Unified RCA — Common documentation

PoC-wide, objective-oriented docs live here. Pipeline-specific docs stay under
`federated-pipeline/docs/` and `lean-pipeline/docs/`.

**Full repo doc map:** [`NAVIGATION.md`](./NAVIGATION.md) — **start here** if you are lost.

## Index (common docs only)

| Document | Purpose |
|----------|---------|
| [`POC_BRIEFING.md`](./POC_BRIEFING.md) | **End-to-end PoC briefing** (objective → design → bakeoff → conclusion) for NotebookLM / slides |
| [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) | **Explore & demo** the PoC console, bakeoffs, ingest/lab |
| [`CODE_GUIDE.md`](./CODE_GUIDE.md) | **Code map for newcomers** — folders, flow, first files, task recipes |
| [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) | Canonical stages + **current next actions** (Ingest → … → Verify) |
| [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) | Fault-type buckets vs Dynatrace/Datadog (coverage gaps) |
| [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) | Datadog/Dynatrace: no public RCA scoreboard; our GT contract |
| [`rca-use-cases-only.md`](./rca-use-cases-only.md) | Sole evaluation corpus spec (ObserveOps UC-1..UC-5; UC-3b + events schema specified) |
| [`UC_LEARNING_BRAINSTORM.md`](./UC_LEARNING_BRAINSTORM.md) | **Learning / brainstorm** — simplified UC frames (problem → RCA output); not bakeoff GT |
| [`ROADMAP.md`](./ROADMAP.md) | End-to-end phases and status |
| [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) | Bakeoff evaluation finding (lean favored on this corpus; not a finalized product decision) |
| [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) | **Standard evaluation checklist** for any RCA method (4 axes + 5 roadblocks + evidence provenance) — not lean-only |
| [`GLOSSARY.md`](./GLOSSARY.md) | Disambiguates **tier** namespaces, corpus names, and verifiability vs main-path % |
| [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) | **Ingestion design** — Vector shared fabric; RCA-ready artifacts for Lean vs Federated |
| [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) | Ingestion PoC milestones, hardware, weekly checklist |
| [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) | `ingest.v1` contract + ObserveOps/Motadata converters |
| [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) | Fair Lean vs Federated compare (shared detect) |
| Visual simulation guides | Lean: [`../lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md`](../lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md) · Federated: [`../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md`](../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md) |
| [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) | Lean RCA product requirements (**canonical**; includes Appendix E) · [`.pdf`](./Lean_RCA_PRD.pdf) export · [`.docx`](./Lean_RCA_PRD.docx) |
| [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md) | Lean RCA simple guide (**canonical**) · [`.pdf`](./Lean_RCA_Simple_Guide.pdf) export · [`.docx`](./Lean_RCA_Simple_Guide.docx) |

## Two evaluation corpora (do not merge scoreboards)

| Corpus | Location | Ground truth | Typical accuracy headline |
|--------|----------|--------------|---------------------------|
| **ObserveOps UC** (Corpus B) | `datasets/observeops/` v1.1.0 | Shared `ground_truth.json` per UC | **5/5** root-CI on UC-1..UC-5 (`bakeoff-phase-b-002`) |
| **OpenObserve incidents** | `datasets/openobserve_incidents/v1/` | Alert-heuristic labels (Option B) | Peer GT ~**88%** layer (n=24); engine-pack bakeoff **62.5%** root-alert — **different surfaces** |

**Ingest streams (not bakeoff scoreboards):** `datasets/ingest_samples/` — ObserveOps → `ingest.v1` replay + Motadata derived stream (large Motadata dumps local/gitignored). See [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md).

Reports: ObserveOps → [`benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md); OpenObserve → [`benchmarking/results/openobserve/`](../benchmarking/results/openobserve/). See [`benchmarking/README.md`](../benchmarking/README.md).

See also: **[Lean vs federated — design choice & decision guide](#lean-vs-federated--design-choice--decision-guide)** below.

Root also keeps convenience symlinks: `ROADMAP.md`, `rca-use-cases-only.md` → this folder.

## What topology does the ObserveOps corpus use?

[`rca-use-cases-only.md`](./rca-use-cases-only.md) (and `datasets/observeops/`) use a **classic infrastructure typed CI graph**, not a microservice deployment-identity invocation graph.

| Model | Meaning | This corpus? |
|-------|---------|--------------|
| Classic infra typed CI graph | Network device → ESXi host → VM → guest OS → application (+ shared datastore), with edges like `uplink_to` / `hosted_by` / `stored_on` / `runs_on` | **Yes** — UC-1..UC-5 |
| Deployment-identity invocation graph | Service/pod call edges from traces (who calls whom at runtime) | **No** — Lean PRD microservice / Corpus A track |

Lean still *walks* that typed graph upstream (best-first / temporal / CARE), which is the §2.9 classic-infra extension of the PRD “invocation graph” idea — inventory CIs, not ephemeral pod identities.

## ObserveOps UCs vs four qualities & five roadblocks

**Project-wide protocol** for scoring any RCA method (academic, commercial, lean, federated, future): [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) — four axes, five roadblocks, evidence provenance. The ObserveOps Mandatories below are a **deployment profile** applied on top of that checklist for classic-infra tickets.

Definitions match the Lean PRD / Simple Guide.

### Four qualities — how hard should this corpus insist on each?

| Quality | Meaning | For UC-1..UC-5 | Why |
|---------|---------|----------------|-----|
| **Reproducibility** | Same bundle → same verdict | **Mandatory** (bit-stable) | Frozen corpus + ObserveOps ops need the same incident → same answer; no “lucky” runs |
| **Verifiability** | Human can check the evidence chain | **Mandatory** | UC tables (b)/(e) require signal-cited evidence + SRE report; auditor must replay the path |
| **Accuracy** | Correct vs ground-truth root/signature | **Mandatory to measure; threshold-gated — not “must be 100%”** | Accuracy is a hard product KPI, but perfect score on 5 synthetic UCs is a PoC convenience, not a universal bar. Prefer a declared floor (e.g. ≥4/5 or ≥80% on a larger set) over chasing stochastic peaks |
| **Causal Validity** | Claims “A caused B,” not only correlation/Δt | **Recommended** (claim only on Tier 3) | See below — temporal precedence ≠ structural causation; absolute Pearl-style proof is too costly for the main path |

**Accuracy vs Reproducibility (engine A vs B):** Prefer Engine B’s profile for classic ObserveOps classic-infra RCA. A 92% stochastic/LLM engine that changes evidence paths and occasionally hallucinates a switch is worse in production than an 82% lean walk that is bit-identical and checkable — because SRE trust, change control, and incident compare/diff need stable verdicts. Raise Accuracy with better rules/signals/topology, not by relaxing Reproducibility. On this small UC-1..UC-5 set, 5/5 is a useful smoke bar; on a larger corpus, treat Accuracy as **Mandatory ≥ threshold**, Reproducibility as **Mandatory = 100% of reruns**.

### Why Causal Validity is Recommended, not Mandatory

**Temporal precedence** (what failed first among reachable CIs) is cheap: onset timestamps + typed upstream walk. It is enough for many ObserveOps tickets (linkDown, filesystem full, app heap with healthy infra).

**Structural causation** (Pearl-style / counterfactual: “If ESXi CPU had *not* spiked, would the VM app still be slow?”) is a different mathematical class. Absolute proof typically needs interventions and heavy sampling (e.g. Murphy Gibbs) over alternate worlds. Running that **globally** across thousands of VMware metrics breaks **Roadblock 5** (compute/cost) and turns a lean monitor into a continuous causal-inference cluster.

Lean policy (aligned with the PRD):

1. **Default (Tier 1):** temporal + reachability + rules → Reproducible, Verifiable, Accuracy-gated — **no Causal Validity claim**.
2. **Escalate (Tier 2→3):** only when Δt is ambiguous (CARE), run a **scoped** check on a tiny candidate set; only then may CV be claimed.
3. **Never:** fleet-wide counterfactuals on every metric as the heartbeat of RCA.

PoC Tier 3 today is intentionally lightweight (topology + onset plausibility after CARE), not full fleet Gibbs — ration CV, don’t abolish it. UC-1/UC-3 exercise the Recommended path; UC-2/4/5 correctly omit a CV claim.

### Five roadblocks — what ObserveOps should prove

| # | Roadblock | For this corpus | Why |
|---|-----------|-----------------|-----|
| **1a** | Instrumentation blind spots (no telemetry even in principle) | **Optional** | Frozen bundles expose all decisive signals; no third-party black box. UC-5 is a weak cousin (infra *healthy*, not missing) — anti-FP, not true 1a |
| **1b** | Cross-domain fragmentation (net / host / storage / app silos) | **Mandatory** *(as typed multi-domain graph where data is already joined)* | Entire UC set is Network→Host→VM→OS→App(+Datastore). §2.9 reduces 1b only where data is accessible — that is exactly this PoC. Full org silo fix remains unsolved (PRD C) |
| **2** | Non-stationary topology (deps change with deploys) | **Optional** | Topology is frozen per bundle; no live redeploy churn in ObserveOps eval |
| **3** | Ephemeral entity identity (pod churn) | **Optional / out of scope** | Classic long-lived VMs/hosts/ports — not K8s pod identity. Belongs to PRD Scenario 3 / microservice track |
| **4** | No standardized ground truth | **Mandatory** *(by convention)* | Shared GT + same-bundle bakeoff is required practice; inventing a field-wide standard is out of scope |
| **5** | Compute / cost ceiling | **Recommended** to respect by design; measure later | Lean main path stays cheap (temporal + graph walk). Global structural-causation sampling would violate this roadblock — another reason CV stays Recommended/scoped, not Mandatory everywhere |

**ObserveOps vs original Lean PRD emphasis:** The PRD’s microservice PoC text often says it targets **1a / 2 / 3** directly, and treats **4** as “field convention only.” For **this** ObserveOps corpus the live Mandatories are **1b** (joined typed multi-domain graph) and **4** (shared GT + same-bundle bakeoff). Roadblock 4 is not optional here — without a shared ground-truth convention, Accuracy and the federated-vs-lean bakeoff are undefined. We still do **not** claim to invent a field-wide industry benchmark (PRD Category C); we **do** require a corpus-local GT contract.

### Per use-case emphasis

Every UC also exercises **Roadblock 4** (shared `ground_truth.json` + bakeoff contract). Layer-specific stress:

| UC | Layer | Qualities stressed | Roadblocks stressed |
|----|-------|--------------------|---------------------|
| UC-1 | Host CPU | Accuracy + Verifiability; CV if Tier 3 | **4** (GT); **1b** (host↔VM↔app); baseline shared-upstream |
| UC-2 | Network uplink | Accuracy + Verifiability | **4** (GT); **1b** (network↔host↔app) |
| UC-3 | Datastore / noisy neighbor | Accuracy + Verifiability; CV if Tier 3 | **4** (GT); **1b** (storage↔VM↔app) |
| UC-4 | Guest OS | Accuracy + Verifiability; narrow blast radius | **4** (GT); layer stop (OS vs infra below) |
| UC-5 | App only | Accuracy + Verifiability; anti-FP | **4** (GT + false-infra-blame fail rule); upstream-healthy gate (not true **1a**) |

**Bottom line:** For ObserveOps, treat **Reproducibility (bit-stable)** and **Verifiability** as hard Mandatories. Treat **Accuracy** as Mandatory to measure against a declared floor (5/5 is fine as a tiny-corpus smoke bar; do not equate “Mandatory” with “must always be 100% forever”). Treat **Causal Validity** as Recommended only on ambiguous CARE→Tier 3 paths — temporal-first by default; do not mandate fleet-wide structural/counterfactual proof (Roadblock 5). Treat roadblock **1b (joined classic-infra graph)** and **4 (shared GT convention)** as Mandatory for this corpus; **1a, 2, 3** as Optional or deferred; **5** as a design constraint the lean main path must honor.

## Lean vs federated — design choice & decision guide

Formal record: [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md). Bakeoff evidence: [`../benchmarking/results/comparison/DECISION.md`](../benchmarking/results/comparison/DECISION.md).

### Two different “graphs”

On ObserveOps both engines can ingest the **same** typed CI inventory — but they are not the same architecture.

| | **Lean** | **Federated (Panorama → Murphy → Nezha)** |
|--|----------|------------------------------------------|
| Graph role | **One** CI invocation graph *is* the reasoner | **Several** substrates: Murphy relationship/knowledge graph + Panorama LOS + Nezha event/pair graph |
| Core question | What failed first / highest info-gain upstream of the symptom? | Who is unhealthy → which entity has highest causal posterior → which code-path patterns shifted? |
| Causal stance | Temporal + reachability by default; scoped CV only after CARE (Tier 3) | Murphy brings **partial structural / counterfactual-style** inference (MRF + Gibbs) on the localization hop |
| Cost shape | Cheap per incident (walk + rules) | Heavier (multi-hop pipeline + sampling + dual storage tiers) |

Murphy’s **Causal Validity edge is real**. It is not automatically the better *product* when Reproducibility, Verifiability, and Roadblock 5 dominate.

### Cost–benefit

| | Murphy / federated | Lean |
|--|--------------------|------|
| **Benefit — Causal Validity** | Stronger (partial): “if this entity were healthy, would the symptom ease?” | Weaker on the main path; scoped Tier 3 only |
| **Benefit — soft ranking** | Posterior over candidates | Single root + evidence trail (+ optional CARE ranking) |
| **Cost — compute (Roadblock 5)** | Gibbs/sampling and multi-engine hops; expensive if broad or frequent | Low; scales as a monitor, not an inference cluster |
| **Cost — Reproducibility** | Often weaker unless tightly seeded/gated (ObserveOps bakeoff ~40% federated vs 100% lean) | Bit-stable by design |
| **Cost — Verifiability** | Harder to audit (“posterior 0.57”) | Easy to audit (signals + chain + tier) |
| **Cost — ops complexity** | Orchestrator + three algos + structural/speed tiers | One engine + typed topology |
| **Accuracy on UC-1..UC-5** | 5/5 | 5/5 (no extra accuracy paid for by Murphy CV on this corpus) |

**Net for classic ObserveOps classic infra:** Lean wins the cost–benefit. Federated/Murphy wins when you explicitly need deeper causal localization and will pay for compute + stochasticity.

### Decision guide — what to choose when?

Use this as a product/architecture checklist (not a per-ticket router unless you build a hybrid later).

| If your situation is… | Choose | Why |
|------------------------|--------|-----|
| Classic infra RCA (network / ESXi / VM / OS / app), ObserveOps-style | **Lean** | Matches typed CI stack; Reproducibility + Verifiability are Mandatories |
| Same incident must always yield the same verdict + evidence | **Lean** | Bit-identical main path |
| SRE must explain the answer from metrics/topology in minutes | **Lean** | Checkable trail beats opaque posteriors |
| Decisive hard signals (linkDown, disk full, OOM, heap) with clear Δt | **Lean (Tier 1)** | Temporal precedence is enough; don’t pay for CV |
| Δt ambiguous among candidates (noisy neighbor vs datastore, multi-VM host) | **Lean (CARE → Tier 3)** | Scoped CV budget only when needed |
| Compute/cost ceiling is tight; RCA must stay “monitoring-cheap” | **Lean** | Avoids fleet-wide Gibbs (Roadblock 5) |
| You need the strongest available structural/counterfactual localization | **Federated / Murphy** | Real CV edge — accept repro/cost tradeoffs |
| Microservice gray failure + code-path drift (ZooKeeper / Boutique / TrainTicket) | **Federated** (Panorama + Nezha depth; Murphy as macro) | Event/observer graphs matter; classic CI walk is not the whole story |
| Accuracy is the only KPI and you accept different answers across reruns | **Federated or LLM/stochastic** | Not ObserveOps’ preferred profile — raise Accuracy without killing Reproducibility when possible |
| Hybrid roadmap | **Primary evaluation engine + federated optional** | ADR-001: ObserveOps → lean (not a finalized product commitment); microservice track → federated when in scope |

### Quick chooser

```text
Need bit-stable + SRE-auditable RCA on classic infra?
  └─ YES → Lean (default)
       └─ Δt ambiguous? → CARE / Tier 3 (scoped CV)
  └─ NO — need deep structural CV or microservice event/code-path RCA?
       └─ YES → Federated (Murphy ± Panorama/Nezha)
       └─ Still ObserveOps VMware stack? → Prefer Lean; don’t buy Murphy for CV alone
```

**PoC decision:** Lean is the **primary evaluation engine** for [`rca-use-cases-only.md`](./rca-use-cases-only.md) per ADR-001 (**not a finalized product commitment**). Federated remains available for comparison and for a future microservice hybrid — not as the ObserveOps default brain.

## Pipeline-specific docs (not moved)

| Location | Contents |
|----------|----------|
| [`federated-pipeline/docs/ARCHITECTURE.md`](../federated-pipeline/docs/ARCHITECTURE.md) | Federated architecture, components, workflow · [limitations](../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md) |
| [`lean-pipeline/docs/ARCHITECTURE.md`](../lean-pipeline/docs/ARCHITECTURE.md) | Lean architecture, components, workflow · [limitations & future](../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md) |
| [`benchmarking/`](../benchmarking/) | Bakeoff runners + comparison reports |
| [`datasets/observeops/`](../datasets/observeops/) | Frozen corpus + comparison contract |
