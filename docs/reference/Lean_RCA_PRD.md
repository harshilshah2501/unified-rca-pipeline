# Lean RCA Architecture

**Product Requirements Document — evaluation-aligned revision (canonical Markdown; PDF regenerated 2026-07-16)**

> **Source of truth:** this `.md` file. [`Lean_RCA_PRD.pdf`](./Lean_RCA_PRD.pdf) is an export for slides/NotebookLM.

*BFS + Temporal Ordering, Information-Gain Search, Spectrum-Based Fallback (CARE), Typed Classic-Infra Rules*

Synthetic / simulated evaluation environments only. No production customer data.

---

## Document Purpose & Scope

This document specifies a lean Root Cause Analysis (RCA) architecture, scored explicitly against four distinct reliability axes rather than a single loose "deterministic" label. It supersedes an earlier design that federated three independently published academic systems (Panorama, Nezha, and Murphy) via a heavy orchestration layer. That federated design is retained in Section 5 as prior work considered - bridging three heterogeneous algorithms was the primary source of its cost and complexity, not a necessary property of a reliable RCA architecture.

**Status (corrected 2026-07-13):**

| Track | Status |
|-------|--------|
| **ObserveOps (classic infra typed CI graph)** | **Primary evaluation engine** per bakeoff ([ADR-001](./ADR-001-lean-primary-engine.md)); **not a finalized product commitment**. Journey **Compare → Deepen → Ship** exercised: `bakeoff-phase-a-001`, `bakeoff-phase-b-001`, `bakeoff-phase-b-002` (ADR-era); current cite **`adr001-rerun-20260723`**. |
| **Microservice / DeathStarBench-style PoC (original Sections 3 + Appendix B)** | **Deferred / optional.** Still a valid research track for Roadblocks 1a / 2 / 3; not the primary evaluation engine packaging path. |
| **Federated pipeline** | **Optional hybrid** for microservice code-path / gray-failure / pair-mining once a dedicated microservice corpus is in scope. |

Earlier proposal language ("nothing described has been built"; "no decision to move away from federated") is **obsolete for classic ObserveOps classic infra**. Architecture sections below remain the product requirements for lean; ObserveOps callouts mark what was shipped vs what stays deferred.

Companion narrative: [`POC_BRIEFING.md`](./POC_BRIEFING.md); plain-language: [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md); corpus: [`rca-use-cases-only.md`](../rca-use-cases-only.md).

### Core mechanism (unchanged intent)

One coherent core: search over an **invocation / typed inventory graph** combined with **temporal ordering of anomaly onset**, augmented with **information-gain-driven** (best-first) traversal, and a shared **CARE** fallback when onset windows are ambiguous. On ObserveOps classic infra, the same core is extended with **typed CI identity**, **fault signatures**, **shared-upstream preference**, and **contributor** fields (Section 2.9) - temporal earliest is a **candidate clue**, not an automatic verdict.

No LLM-based reasoning in the causal deduction path. An LLM may optionally narrate an already-computed verdict.

### Four reliability axes

Earlier revisions used "deterministic" as an umbrella. That term only means "same input, same output." This document uses four independent axes:

1. **Reproducibility** - same input produces the same output  
2. **Verifiability** - a human can inspect and check why a given output was produced  
3. **Accuracy** - the output is empirically correct against ground truth (Mandatory to measure; threshold-gated - not "must be 100% forever")  
4. **Causal Validity** - the output reflects actual causation, not merely correlation or temporal precedence (Recommended; claim only on Tier 3)

A system can be fully reproducible and still be unverifiable, inaccurate, or merely correlational.

---

## ObserveOps Alignment Summary (read first)

| Original PRD claim | ObserveOps reality |
|--------------------|------------------|
| Proposal; nothing built; federated still default | Primary evaluation engine per ADR-001; not a finalized product commitment |
| PoC targets Roadblocks **1a / 2 / 3** | Live Mandatories: **1b** (joined typed multi-domain graph) + **4** (shared GT + same-bundle bakeoff) |
| **1b** out of scope; **4** convention-only / field-wide C | Org silos still C; **joined-graph 1b** and **corpus GT 4** are Mandatory and demonstrated |
| Section 2.9 classic infra = "next planned extension" | **Shipped** as primary evaluation engine path |
| Earliest anomaly = leading root-cause candidate | Earliest is a **hint**; ObserveOps prefers **shared-upstream + signatures**; UC-3b proves early unrelated switch is not root |
| Scenarios = DeathStarBench cascading / blind spot / pod churn | Primary eval = ObserveOps **UC-1..UC-5** (+ **UC-3b**); microservice scenarios deferred |
| No log/event fusion on main path | ObserveOps ingests **structured synthetic events** (`events.json`) on UC-2/UC-4/UC-3b for evidence - not full Nezha free-text mining |
| Appendix C: no matched accuracy figures yet | Bakeoff **5/5** both engines; lean **100%** repro vs federated **~40%**; primary evaluation engine (ADR-001) |

---

## 1. Roadblocks Targeted by This Design

Roadblock 1 (blind spots) and cross-domain organizational fragmentation are treated as two subtypes of "visibility boundaries" - both can produce an unreachable neighbor at the graph level, but they differ in cause and solvability.

| # | Roadblock | Why it resists solving |
|---|-----------|------------------------|
| **1a** | Instrumentation blind spots | Telemetry does not exist even in principle (third-party / black-box). Honest mitigation: detect-and-flag. |
| **1b** | Cross-domain fragmentation | Telemetry exists but is siloed across teams/platforms (Conway's Law). Org silos have no pure algorithm fix. **Where data is already joined** into one typed multi-domain graph, architecture can reduce 1b - that is ObserveOps. |
| **2** | Non-stationary topology | Deployments change dependency graphs continuously; graph must be live, not stale-cached. |
| **3** | Ephemeral entity identity (pod churn) | Pod restarts explode identity cardinality; per-entity history methods degrade. |
| **4** | No standardized ground truth / benchmark | Field-wide: still Category C. **Corpus-local:** solved by convention (shared labeled GT + matched bakeoff) - Mandatory for classic ObserveOps Accuracy. |
| **5** | Compute / cost ceiling | Full always-on hyperscale analysis is expensive. Lean addresses this structurally (cheap main path; scoped CV only). |

### Two PoC emphases (do not conflate)

| Emphasis | Targets | Status |
|----------|---------|--------|
| **Original microservice PoC** (Sections 3.1-3.2, Appendix B Phase 0-6) | **1a, 2, 3** directly | Deferred |
| **ObserveOps** ([`rca-use-cases-only.md`](../rca-use-cases-only.md)) | **1b** (joined classic-infra graph) + **4** (shared GT) Mandatory; **5** by design; **1a/2/3** Optional / out of scope | **Complete** — primary evaluation engine (ADR-001) |

Roadblocks 2 and 3 are related but not nested: 2 is structural graph change; 3 is instance-identity churn under a stable logical graph. Workload-level keying (Section 2.4) lifts 3 to the abstraction layer where 2 already operates - relevant to the deferred microservice track, not ObserveOps VMs/hosts.

---

## 2. Architecture

**Terminology:** event graph, invocation graph, dependency graph, and causal graph are distinct.

| Term | Granularity | What an edge means | Used where |
|------|-------------|--------------------|------------|
| Event graph | Finest - events within one trace | Ordering within a request | Nezha's original mechanism (Section 5) - not lean's main path |
| Invocation / inventory graph | Service-to-service **or** typed CI relations | A interacts with / hosts / stores / uplinks to B - **no causal claim** | What Section 2.1 builds and search walks |
| Dependency graph | Loose umbrella | Ambiguous | Avoided; prefer "invocation graph" or "typed CI graph" |
| Causal graph | Formal SCM | Parent change produces child change - tested | Only approximated for CARE-triggered Tier 3 (Section 2.6) |

ObserveOps classic infra walks a **typed CI inventory graph** (Network -> Host -> VM -> OS -> App + Datastore). That is the Section 2.9 extension of the microservice "invocation graph" idea - inventory CIs, not ephemeral pod identities.

### 2.1 Core: Search + Temporal Ordering (+ ObserveOps rules)

On anomaly detection, the engine searches backward from the symptomatic node over confirmed edges, isolating the active propagation subgraph. The frontier is scored by expected information gain (Section 2.2), making traversal **best-first over the BFS frontier**, not strict FIFO BFS once that layer is active.

Within the discovered subgraph, nodes are ranked by anomaly-onset timestamps. Temporal precedence is a **necessary but not sufficient** condition for causation:

- An earlier anomaly can be an independent unrelated event (common-cause confound).  
- Clock skew can invert fine-grained order - CARE's Delta-t trigger uses a skew-aware window.  
- **Therefore:** the earliest-crossing node is a **leading candidate for verification**, never an automatic ObserveOps verdict.

**ObserveOps classic-infra addition (shipped):** when multiple CIs share the same pain class (CPU ready, disk latency, etc.), apply **shared-upstream preference** and name a **fault signature** (e.g. `storage_contention`, `cpu_contention`, `link_failure`). A noisy-neighbor VM is typically the **contributor**; the shared datastore/host is the **root**. This is how lean rejects "Batch VM started I/O first => Batch is root" and "switch blipped earlier => switch is root" (UC-3 / UC-3b).

**Reproducibility:** same graph + same timestamps (+ same rules) => same ranking. No claim of Causal Validity on the main path alone.

**Graph granularity:**

- **Microservice track:** nodes = workload/Deployment identity (not raw pod ID); map pod->workload at graph construction time (Section 2.4).  
- **ObserveOps track:** nodes = typed CIs (switch port, ESXi host, VM, guest OS, app, datastore) keyed by stable inventory IDs.

**Ingestion:** microservice track uses trace span parent/child edges. ObserveOps track uses CMDB/discovery-style typed edges plus metric anomalies and optional structured events (Section 2.7 / 2.9). Main path does **not** run full Nezha Drain free-text log mining.

### 2.2 Efficiency Layer: Information-Gain-Driven Traversal

Rather than exhaustively walking the full active subgraph, the engine selects the next observation by expected reduction in Shannon entropy of the belief distribution over candidates (boolean anomaly status + onset if crossed). Highest expected gain expands first.

This is a PoC-implementable instantiation, not a claim of a universal externally validated formula. ObserveOps Phase B measured best-first vs naive BFS observation counts on the ObserveOps corpus (lean avg best-first ~2.4 vs naive ~2.8 on `bakeoff-phase-b-001` / similar on b-002).

Sections 2.1 and 2.2 are **search strategies over a non-causal graph**. They do not construct a causal graph. Only Section 2.6's scoped check does that, and only for the CARE-triggered subset.

### 2.3 Shared Fallback: CARE Weighted Spectrum + Scoped Causal Verification

When search + temporal ordering cannot cleanly separate cause from bystander - typically multiple threshold crossings inside Delta-t - the engine falls back to CARE-style spectrum risk scoring (active in abnormal traces more than normal) plus topology-weighted prioritization, to avoid blaming innocent downstream bystanders.

**ObserveOps under CARE:** still prefer a fitting **shared-upstream / signature** winner over crowning the earliest CI in the ambiguous window (UC-3b).

**Scoped causal verification:** when CARE fires, and only then, apply a lightweight causal check on CARE's top candidates before returning Tier 3 (Section 2.6). On the main path (no fallback), output remains Tier 1 - temporal + reachability (+ ObserveOps rules) - **no Causal Validity claim**. Reporting must preserve this distinction.

### 2.4 Entity Identity & Blind-Spot Handling

- **Workload-level keying (microservice track):** required so CARE spectrum does not fragment across short-lived pod IDs, and so a rotating root is one continuous cause. Precedent: AWS Container Insights aggregates at service/task-definition level [9].  
- **Blind spots (1a):** when traversal hits a node with no internal telemetry, halt and flag `bounded_by_uninstrumented_dependency` rather than blaming the last visible node. ObserveOps evaluation path UCs do not exercise true 1a (frozen bundles expose decisive signals); UC-5 is anti-FP (healthy infra), not missing telemetry.  
- **ObserveOps identity:** long-lived hosts/VMs/ports/datastores - Roadblock 3 out of scope.

### 2.5 Infrastructure Footprint

Single lightweight service holding the live graph and a short rolling window of metrics/events - not a dual-tier federated storage fleet. This is a structural consequence of one coherent algorithm family. ObserveOps packaging: `lean_rca` CLI/HTTP API and `lean-rca.service` (Phase D).

Not Murphy Tier-2 Vortex/Arrow infrastructure. Invocation/inventory graph, not a causal graph (Section 2.6).

### 2.6 Invocation Graph vs Causal Graph; Three Evidentiary Tiers

Chain of claims:

1. An edge asserts interaction / inventory relation - not causation.  
2. Temporal ordering asserts precedence - necessary for causation, vulnerable to common-cause confounds.  
3. CARE spectrum + topology weighting - stronger correlation, still not causal structure testing.

CARE scores well on Reproducibility, Verifiability, and published Accuracy (72-89% top-1 [1]) but **does not** provide Causal Validity.

**Decision:** do not run universal causal discovery on every incident (fails under churn / cost). Apply a **scoped** causal check only when CARE has fired. Mechanisms: constraint-based discovery on the small candidate set, or counterfactual-style verification. ObserveOps PoC Tier 3 is intentionally lightweight (topology + onset plausibility after CARE), not fleet-wide Gibbs.

**Three tiers (mandatory in reporting):**

| Tier | Meaning | Causal Validity claim? |
|------|---------|------------------------|
| **1** | Main path: reachability + temporal (+ ObserveOps rules/signatures) | **No** |
| **2** | CARE fallback: stronger correlational ranking | **No** |
| **3** | CARE + scoped causal check | **Yes** (bounded; ObserveOps: UC-1 / UC-3 / UC-3b) |

Universal causal-graph construction on the main path remains out of scope. Continuous causal memory (Section 2.8) is optional later (roadmap B5).

### 2.7 Multi-Modal Signal Scope

Nezha reasoned jointly over metrics, logs, and traces. Lean's original main path: topology + metric thresholds only.

**ObserveOps correction:** structured synthetic **events** (`events.json` - SNMP/syslog-style lines with `ci_id`, `timestamp`, `message`, optional `signal`) are required on UC-2 / UC-4 / UC-3b and may be cited in the evidence trail. This is **not** full Nezha free-text Drain mining. Deeper multimodal log RCA remains optional (federated / Nezha track).

### 2.8 Continuous Causal Learning (Future Work)

Move causal-structure learning off the per-incident path: background learner updated from healthy traffic and past incidents; incident-time verification becomes a cheap lookup. Requires persistent model store, update cadence, and invalidation under Roadblock 2. **Not required** for primary evaluation engine packaging (optional B5).

### 2.9 Classic Infrastructure Topology - ObserveOps Primary (SHIPPED)

**Original PRD framing:** next major planned extension after a Kubernetes/microservice PoC.

**Corrected framing:** ObserveOps **implemented and adopted** this extension as the **primary evaluation engine** path (ADR-001; not a finalized product commitment). Microservice scenarios remain the deferred research track.

| Part | Requirement | ObserveOps status |
|------|-------------|-----------------|
| Typed-node identity | Service / Host-VM / NetworkDevice / Datastore with type-appropriate keys | **Shipped** in `datasets/observeops/` + lean engine |
| Dual / alternate edge construction | Trace spans **or** CMDB/discovery / flow-derived edges into one walkable graph | **Shipped** typed inventory edges for classic stack |
| ObserveOps rules | Shared-upstream preference, fault signatures, contributor | **Shipped**; UC-3b adversarial early-switch fixture |
| Roadblock 1b honesty | Closes gap only where data sources are accessible to one system | **Demonstrated** on joined corpus graph; org silos still unsolved |

---

## 3. Evaluation Corpora

### 3.1 Corpus A - Microservice algorithm PoC (deferred)

Original PRD scenarios on DeathStarBench / TrainTicket synthetic base (Roadblock 4 convention):

| Scenario | Mechanism under test | Primary metric | Roadblocks |
|----------|----------------------|----------------|------------|
| Cascading latency | BFS + temporal + info-gain; CARE on simultaneous crossings | Top-1 accuracy; observations to convergence | Baseline (none directly) |
| Third-party blind spot | Boundary detect + flag | Correct blind-spot flag rate | **1a** |
| Ephemeral pod churn | Workload vs pod keying | Accuracy delta under HPA churn | **3** (primary), **2** (secondary) |

These scenarios are **not** ObserveOps’ acceptance gate. Appendix B Phases 0-6 remain the plan **if** Corpus A is prioritized.

### 3.2 Corpus B - ObserveOps (primary; complete)

Frozen typed CI corpus from [`rca-use-cases-only.md`](../rca-use-cases-only.md) in `datasets/observeops/` (v1.1.0+):

| UC | Layer / story | Qualities stressed |
|----|---------------|--------------------|
| UC-1 | Host CPU contention | Accuracy, Verifiability; Tier 3 possible |
| UC-2 | Network uplink / link failure (+ events) | Accuracy, Verifiability |
| UC-3 | Datastore contention + noisy neighbor | Accuracy, Verifiability; Tier 3 |
| UC-3b | UC-3 + early unrelated switch (adversarial) | Proves earliest != root |
| UC-4 | Guest OS exhaustion (+ events) | Narrow blast radius |
| UC-5 | App-only / false infra blame | Anti-FP vs healthy infra |

**Mandatory roadblocks for this corpus:** **1b** + **4**. Primary bakeoff `--all` = UC-1..UC-5; UC-3b via `--uc UC-3b`.

### 3.3 Roadblock ownership (honest categories)

| Cat. | Meaning |
|------|---------|
| **A** | Built and measured |
| **B** | Proposed / partially measured |
| **C** | No known architectural solution (field-wide) |

| Roadblock | Lean / ObserveOps stance |
|-----------|------------------------|
| 1a | Category B targeting A on Corpus A Scenario 2; Optional on ObserveOps |
| 1b | Org-wide: **C**. Joined typed graph: **A** on ObserveOps corpus |
| 2 | Category B on live reconstruction; Optional on ObserveOps (frozen topology) |
| 3 | Category B targeting A on Corpus A Scenario 3; out of scope ObserveOps |
| 4 | Field-wide: **C**. Corpus GT convention: **A** on ObserveOps bakeoff |
| 5 | Structural lean design; ObserveOps main path respects it; capacity benchmark optional |

---

## 4. Design Principles

- Accuracy and reliability take priority over speed, decomposed into Reproducibility, Verifiability, Accuracy, and (where claimed) Causal Validity.  
- No LLM in the causal deduction path - frozen temperature does not fix Verifiability or hallucination Accuracy. Optional narrator only.  
- Philosophy precedent: Dynatrace Davis separates causation engine from generative recommendations [4] - cited as philosophy, not as a reusable component.  
- Every hop is a graph traversal, timestamp comparison, or deterministic rule - basis for auditability.  
- Prototyping uses synthetic/simulated environments only.

---

## 5. Prior Work Considered (Federated Design)

An earlier design federated three non-interoperating academic systems via orchestration. ObserveOps **did not** adopt it as the primary classic-infra engine after matched bakeoffs.

- **Panorama (OSDI '18)** - distributed observer / gray-failure. Observer idea reusable; not an ObserveOps classic-infra component.  
- **Murphy (SIGCOMM '23)** - MRF + Gibbs for cyclic / structural diagnosis. Stronger Causal Validity profile; weaker Reproducibility/Verifiability; higher infra cost. Retained as optional hybrid for microservice/cyclic workloads.  
- **Nezha (FSE '23)** - expected-vs-actual event patterns. Value largely subsumed for classic ObserveOps by CARE + structured events + signatures; full multimodal depth optional later.

This is a deliberate scope reduction for classic ObserveOps: prioritize Reproducibility, Verifiability, lean cost, and classic-infra Accuracy over Murphy's richer (still partial) Causal Validity as the **default** brain.

---

## Appendix A: Roadblock Coverage in the Prior Federated Design

| Roadblock | How federated addressed it | Caveat |
|-----------|----------------------------|--------|
| 1a | Panorama neighbor observation | Only where interaction occurs |
| 1b | Not addressed | Left open; LLM/agentic proposals rejected for deduction path |
| 2 | Murphy live graph + online retrain | Fixes staleness; not blind spots / brand-new entities |
| 3 | Proposed workload keying | Never validated in old federated plan |
| 4 | Synthetic injection + labels | Field convention, not industry standard |
| 5 | Proposed sampling / edge filters | Often estimated, not measured |

Pattern: distinguish Category A (paper-validated) from Category B (proposed adaptations). Do not summarize as "5 of 6 solved."

---

## Appendix B: Implementation Plan Status

### ObserveOps critical path (COMPLETE)

| Phase | Intent | Status |
|-------|--------|--------|
| **A** | Bakeoff close; four-axis compare; fusion fix; decision | **Done** — primary evaluation engine (ADR-001) |
| **B** | Lean PRD depth: tiers 1/2/3, CARE->causal, signatures, best-first vs BFS | **Done** (`bakeoff-phase-b-001` / `b-002`) |
| **D** | Package lean CLI/HTTP/SRE report/systemd | **Done** (`lean_rca`, `lean-rca.service`) |
| B5 | Continuous causal memory (Section 2.8) | Optional later |
| C* / E* | Federated ingest / capacity | Deferred - microservice track |

### Corpus A algorithm PoC (DEFERRED - original PRD Phases 0-7)

| Phase | Intent |
|-------|--------|
| 0 | DeathStarBench/TrainTicket harness + blind-spot + HPA fixtures |
| 1 | Core BFS + temporal + reproducibility N-run |
| 2 | Info-gain layer + naive BFS baseline log |
| 3 | Shared CARE fallback + causal-verification log |
| 4 | Workload vs pod keying; blind-spot flag rate |
| 4b | Optional cyclic-dependency stress (known lean limit) |
| 5 | Reproducibility N=20 evidence chains |
| 6 | EVAL.md with tier-separated reporting |
| 7 | Matched comparison vs federated on same fixtures |

Do not treat Corpus A phases as ObserveOps blockers.

---

## Appendix C: Lean vs Federated - Measured ObserveOps Comparison

Original PRD Appendix C was structural only ("no matched figures yet"). **Superseded** by ObserveOps bakeoffs.

Latest matched report: [`../benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) · decision: [`DECISION.md`](../benchmarking/results/comparison/DECISION.md) · ADR: [`ADR-001`](./ADR-001-lean-primary-engine.md).

| Dimension | Federated (Panorama + Murphy + Nezha) | Lean (BFS/best-first + temporal + CARE + ObserveOps rules) |
|-----------|----------------------------------------|----------------------------------------------------------|
| Core | Three heterogeneous algorithms + fusion | One coherent family + shared CARE + signatures |
| Accuracy (UC-1..UC-5) | **5/5** root + signature | **5/5** root + signature |
| Reproducibility (N=20) | **~40%** (multi-hash on some UCs) | **100%** bit-stable |
| Verifiability | Fusion path + overrides | Tier labels + CARE/causal log + SRE report |
| Causal Validity | Murphy partial (costly if global) | Recommended only on CARE->Tier 3 |
| Efficiency | Higher avg observations; heavier stack | Fewer observations; best-first gains |
| Infra | Multi-component federated stack | Single lean service / API |
| ObserveOps decision | Optional hybrid later | **Primary** |

UC-3 note: federated sometimes uses fewer raw observations while accuracy ties; lean may spend budget reaching Tier 3 - acceptable under Recommended CV, not a reason to change primary engine.

---

## Appendix D: Prior Work on Four Axes

| System | Reproducibility | Verifiability | Accuracy | Causal Validity |
|--------|-----------------|---------------|----------|-----------------|
| **Panorama** | High - bounded voting, no stochastic step | High - observer reports | 15/15 gray failures in eval, under 7s [6] | Low - correlational neighbor evidence |
| **Murphy** | Lowest of three - Gibbs; seed-dependent | Medium - posterior needs model unpacking | ~1.35x / 4.7x+ error reduction by setting [7] | Highest of three, still partial / correlational concession |
| **Nezha** | High - closed-form pattern scoring | Highest - readable expected-vs-actual diffs | 89.77% avg top-1 code-region level [8] | Low - baseline comparison, not causal modeling |

**Net reading:** no single system is strong on all four axes. Lean main path inherits the high Reproducibility/Verifiability profile; Murphy-style depth is reserved for scoped Tier 3 (and optional federated hybrid), not the ObserveOps default ticket path.

---

## Appendix E: Dynatrace and Netdata vs academic methods (and this design)

**Protocol:** This appendix is a *worked example* of the project-wide checklist in [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) (common docs — not lean-only). Use that checklist for any new method.

Comparing two widely deployed commercial products to Panorama, Murphy, Nezha, CARE, and this lean design. Read Section 2.6 first if the Tier 1 / 2 / 3 labels are unfamiliar.

### Terms (plain language)

| Term | Meaning here |
|------|----------------|
| **Top-1 accuracy** | On a fixed evaluation set with a known correct root cause, how often the system’s **first-ranked / single chosen** answer matches that truth. Example: Nezha’s paper reports **89.77% average top-1** at code-region level [8] — meaning the primary suggested region was correct about nine times in ten on that corpus. CARE reports **72–89% top-1** [1] on its published evaluations. These are **paper metrics**, not ObserveOps bakeoff scores. |
| **Published / peer-reviewed number** | An accuracy (or related) figure that appears in a refereed paper or similarly citable study, and can be re-checked against that paper’s protocol. |
| **Self-reported claim** | Vendor marketing or product docs (e.g. “causal AI”) with **no independent published accuracy figure** we can cite the same way. |
| **Evidentiary Tier 1 / 2 / 3** | *This design’s* labels for how strong the claim is (Section 2.6). They are **not** Dynatrace or Netdata product tiers. |

**What our tiers mean (reminder):**

| Our tier | What the engine did | May we say “A caused B”? |
|----------|---------------------|---------------------------|
| **Tier 1** | Main path: topology reachability + temporal onset (+ ObserveOps rules/signatures). One leading candidate + evidence trail. | **No** |
| **Tier 2** | CARE fired because onset times among candidates were ambiguous. Stronger **correlation / ranking** over a small set. Still one reportable lead. | **No** |
| **Tier 3** | CARE + a **scoped** causal check on that small set. | **Yes** (bounded; ObserveOps PoC: when CARE escalates, e.g. UC-1 / UC-3 / UC-3b) |

Do **not** read “Tier” below as Netdata’s UI ranking length or Dynatrace’s product packaging. When we relate a commercial product to a tier, we mean: *its public mechanism resembles the kind of reasoning we put in that row of the table above*.

### Placement of Netdata and Dynatrace

| System | Closest likeness in *our* terms | Accuracy story | Causal story |
|--------|----------------------------------|----------------|--------------|
| **Netdata** | Correlational ranking — similar in **spirit** to diagnosing without a causal check (our Tier 1 without a hard single-candidate contract, or CARE-style ordering without Tier 3). Netdata’s own docs describe **correlation analysis**, not causation, and state that the root cause typically surfaces somewhere in the **top 30–50** ranked results, not as one verified verdict. | Product docs: soft ranked list. **Looser** success bar than CARE’s or Nezha’s published top-1 figures. | Explicitly **not** causation. |
| **Dynatrace (Davis)** | Rhetorically closest to **Murphy / our Tier 3**: product material claims **causal**, not merely correlational, reasoning [4]. | **Self-reported.** No independently published, third-party-verifiable top-1 (or equivalent) number found that we can put next to [1]/[6]/[7]/[8]. | Claims causal AI; **cannot be scoreboarded** against paper numbers until independently measured. |
| **Panorama** | Symptom / observer consensus | Peer-reviewed eval [6] | Correlation of local views — not structural cause. |
| **CARE** | Ambiguity ranking (feeds our Tier 2) | Peer-reviewed ~72–89% top-1 [1] | Correlation / context ranking — not Causal Validity in our sense. |
| **Nezha** | Pattern drift (expected vs actual) | Peer-reviewed ~89.77% avg top-1 [8] | Baseline comparison — not causal modeling. |
| **Murphy** | Counterfactual intervention on metrics | Peer-reviewed error-reduction figures [7] | Partial causal screening (strongest of the three papers). |
| **This design (lean)** | Tier 1 by default; CARE → Tier 2; scoped check → Tier 3 | ObserveOps bakeoff: measured (e.g. 5/5 root+signature on UC-1..UC-5); bit-stable main path | Causal Validity **only** when Tier 3 is emitted. |

### Takeaway (market vs evaluation)

1. The **commercial product bar** (especially Netdata’s “find it in a long ranked list”) is **measurably looser** than the **academic top-1 bar** used in CARE / Nezha papers.
2. That is **not** a reason to lower this design’s own contract: main-path outputs remain a **single leading candidate** with an **inspectable evidence trail**, not a 30–50 item triage dump.
3. It **is** fair to note that shipping something weaker than this design’s own targets can still be a real product improvement over a widely deployed correlational ranked-list baseline (Netdata’s documented framing).
4. Dynatrace’s causal claim is a useful **design philosophy** precedent (separate diagnosis engine from generative fluff) [4], but **must not** be treated as a measured competitor until independent accuracy exists. Cite it as philosophy, not as a reusable component or as a win/loss on top-1.

**ObserveOps implications:** Prefer lean Tier 1 when signals and Δt are clean; escalate CARE/Tier 3 only under ambiguity; never market every ticket as “causal” the way a brochure might. Accuracy comparisons to Dynatrace stay out of bakeoff tables until someone runs a fair, frozen corpus against it.

---

## References

1. CARE: Context-Aware Root Cause Identification Using Distributed Traces and Profiling Metrics. Top-1 accuracy 72%-89%. ResearchGate.  
2. TORAI: Multi-Source Root Cause Analysis for Blind Spots in Microservice Service Call Graph. FSE 2026.  
3. Mastering Kubernetes Observability. ClickHouse Engineering Blog, 2026.  
4. What is Causal AI? Dynatrace, 2024.  
5. Why Cross-Domain Root-Cause Analysis is Still Unsolved. ODSC, March 2026.  
6. Huang et al. Panorama. OSDI 2018.  
7. Harsh et al. Murphy. ACM SIGCOMM 2023.  
8. Yu et al. Nezha. ESEC/FSE 2023.  
9. Amazon CloudWatch Container Insights documentation.  
10. Netdata documentation on anomaly / root-cause ranking (correlation analysis; root often among top 30–50 ranked results) — product docs, not a peer-reviewed top-1 study.

Note: "BFS + temporal ordering" and "information-gain-driven traversal" are described as established engineering / decision-theoretic techniques, not a single paper's contribution.

---

*Corrected 2026-07-13 for ObserveOps + ADR-001; Appendix E (Dynatrace / Netdata placement) added 2026-07-15. Prefer [`POC_BRIEFING.md`](./POC_BRIEFING.md) for stakeholder narrative; this PRD remains the lean architecture / requirements source.*
