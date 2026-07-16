# Unified RCA PoC — End-to-End Briefing

**Audience:** brainstorming, stakeholder reviews, NotebookLM → slide decks  
**Date:** 2026-07-16  
**Status:** ObserveOps critical path **complete** (Phases A → B → D)  
**Evaluation finding (not a finalized product commitment):** On the classic ObserveOps UC corpus, bakeoff evidence **favors lean** as the primary evaluation engine ([ADR-001](./ADR-001-lean-primary-engine.md); matched run **`bakeoff-phase-b-002`**)  
**Corpus:** ObserveOps UC-1..UC-5 primary bakeoff (classic infra typed CI graph). Spec + corpus also include **UC-3b** (adversarial early network noise) and synthetic **`events.json`** (required on UC-2/UC-4/UC-3b) — see [`rca-use-cases-only.md`](./rca-use-cases-only.md).

---

## 1. Executive summary (one slide)

ObserveOps needs automatic root-cause analysis across a VMware-style stack:

**Network → ESXi host → VM → Guest OS → Application (+ shared Datastore).**

We built and compared **two engines on the exact same frozen corpus**:

| Approach | What it is | ObserveOps role |
|----------|------------|---------------|
| **Federated** | Panorama (detect) → Murphy (macro causal) → Nezha (micro patterns) | Optional / future microservice & gray-failure track |
| **Lean** | Best-first + temporal + info-gain walk; CARE when Δt is ambiguous; scoped Tier-3 causal only when needed | **Primary evaluation engine** (ADR-001; not a finalized GTM commitment) |

**Bakeoff headline (`bakeoff-phase-b-002`, corpus v1.1.0):**

| Axis | Federated | Lean | Winner |
|------|-----------|------|--------|
| Accuracy (root CI + signature) | 5/5 | 5/5 | Tie |
| Reproducibility (N=20) | ~40% | **100%** | **Lean** |
| Verifiability | Fusion path (no lean-rule rescue on this run); weaker SRE audit trail | Explicit Tier 1/2/3 + CARE/causal log + SRE report | **Lean** (audit narrative)* |
| Efficiency (avg observations) | 5.60 | **5.00** | **Lean** |
| Causal Validity | Stronger (Murphy / costly if global) | Scoped Tier 3 only (UC-1, UC-3) | Design tradeoff |

\*Do **not** read “main path” as lean’s Tier 1/2/3 — that ladder is **lean-only**. The bakeoff’s shared `main_path %` only means `fallback_fired: false` for both engines: for lean = CARE did not fire; for federated = fusion did not fall back to lean rules. On `b-002`, federated is 5/5 “no-fallback” while lean fires CARE on UC-1/UC-3 (intentional Tier 2→3 depth). **Verifiability still favors lean** for SRE auditability of the evidence chain. See [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) and [`GLOSSARY.md`](./GLOSSARY.md).

**Conclusion:** On ObserveOps classic-infra tickets, lean wins the cost–benefit. Murphy’s causal edge is real but does not buy extra accuracy on this corpus, and it loses on reproducibility, auditability, and compute/ops cost. Ship lean first; keep federated for a hybrid later if microservice/code-path RCA is in scope.

---

## 2. Objective

### 2.1 Product objective

Deliver ObserveOps RCA that:

1. Localizes the **correct root CI** (not the loudest symptom app).
2. Names a **fault signature** SRE teams recognize.
3. Produces an **auditable evidence chain** (signals, topology path, blast radius, remediation hints).
4. Is **bit-stable** on the same incident inputs (same answer every rerun).
5. Stays **cheap enough** to run as monitoring-adjacent logic — not a continuous causal-inference cluster.

### 2.2 PoC objective

Decide, with evidence, which pipeline should be ObserveOps’ **primary brain** for classic infrastructure RCA:

- Run **both** engines on **identical** UC-1..UC-5 bundles.
- Score them with a shared contract (accuracy, reproducibility, verifiability, efficiency, causal stance).
- Harden the winner to a callable API/CLI with SRE report fields.
- Document an explicit hybrid boundary (when federated still makes sense).

### 2.3 Success criteria (ObserveOps critical path)

| Criterion | Target | Result |
|-----------|--------|--------|
| Same-corpus bakeoff | Both engines run UC-1..UC-5 | Done |
| Accuracy floor (tiny corpus smoke) | Correct root CI + signature; UC-5 no infra false-blame | Both **5/5** |
| Reproducibility | Lean bit-stable preferred | Lean **100%**; federated **~40%** |
| Engine decision recorded | ADR + decision memo | ADR-001 accepted |
| Product packaging | CLI + HTTP + SRE fields + systemd | `lean_rca` on `:8780` |

---

## 3. Problem framing

### 3.1 The ObserveOps failure mode we care about

App owners often see **application symptoms** (latency, errors, “CPU 100% in guest”) while the true root sits in a **shared upstream layer**:

- Host CPU Ready starvation (UC-1)
- Switch uplink / linkDown (UC-2)
- Shared datastore noisy neighbor (UC-3)
- Guest OS disk/OOM (UC-4)
- Or genuinely the app — with healthy infra (UC-5 anti-FP)

Without topology-aware RCA, tools either:

- Blame the symptom app, or
- Flood the board with every correlated metric, or
- Return stochastic “AI” answers that change on rerun.

### 3.2 What “good RCA” means here (four qualities)

Aligned with the Lean RCA PRD / Simple Guide:

| Quality | Meaning | ObserveOps stance for this corpus |
|---------|---------|----------------------------------|
| **Reproducibility** | Same bundle → same verdict | **Mandatory** (bit-stable) |
| **Verifiability** | Human can replay the evidence chain | **Mandatory** |
| **Accuracy** | Correct vs ground-truth root/signature | **Mandatory to measure; threshold-gated** — not “must always be 100% forever” |
| **Causal Validity** | Claim “A caused B,” not only Δt/correlation | **Recommended** — claim only on Tier 3 |

**Design preference:** Prefer a slightly lower-accuracy engine that is bit-identical and checkable over a higher-accuracy stochastic engine that changes evidence paths and occasionally hallucinates a switch. Raise accuracy with better rules/signals/topology — do not buy accuracy by killing reproducibility.

### 3.3 Five roadblocks — what this PoC proves

| # | Roadblock | For UC-1..UC-5 |
|---|-----------|----------------|
| **1a** Instrumentation blind spots | Optional (frozen corpus exposes decisive signals) |
| **1b** Cross-domain fragmentation (net/host/storage/app) | **Mandatory** as a joined typed multi-domain graph |
| **2** Non-stationary topology | Optional (topology frozen per bundle) |
| **3** Ephemeral entity identity (pods) | Out of scope (classic VMs/hosts) |
| **4** No standardized ground truth | **Mandatory by convention** (shared GT + same-bundle bakeoff) |
| **5** Compute / cost ceiling | **Recommended** to respect by design |

**Do not skip Roadblock 4.** The Lean PRD often lists PoC targets as 1a/2/3 and calls 4 a field-wide open problem. For ObserveOps, **4 is Mandatory at corpus scope**: every UC has `ground_truth.json`, both engines are scored on the same contract, and UC-5’s false-infra-blame rule is part of that GT convention. We are not claiming a universal industry benchmark — we are requiring a fair bakeoff.

**Per-UC stress:** all five UCs → **4**; UC-1..UC-3 also → **1b**; UC-5’s anti-FP rule is GT enforcement (still **4**), not true **1a**.

---

## 4. Scope of this PoC

### 4.1 In scope

- Classic infra typed CI graph (inventory CIs, not K8s pod call graphs).
- Five synthetic but realistic ObserveOps use-cases (UC-1..UC-5).
- Two runnable engines + matched bakeoff.
- Lean packaging: diagnose CLI, HTTP API, SRE report, systemd unit.
- Explicit primary-engine ADR.

### 4.2 Out of scope (intentionally)

- DeathStarBench / TrainTicket / Online Boutique as ObserveOps acceptance gates.
- Live SNMP/NetFlow/APM ingest into ObserveOps production.
- Automated remediation / runbook execution.
- Fleet-wide Pearl-style counterfactuals on every metric.
- 1B EPS production sizing as an ObserveOps gate (capacity measured partially on laptop only).

### 4.3 Optional later (not blocking)

| Item | Why later |
|------|-----------|
| B5 continuous causal memory | Learning loop after packaging |
| Phase C federated ingest/stores | Microservice track only |
| Phase E capacity / 1B EPS vision | Needs server-class measurement |
| Corpus A (microservices) | Different topology class |

---

## 5. Evaluation corpus (UC-1..UC-5)

**Topology model:** classic infrastructure typed CI graph  
Network device → ESXi → VM → Guest OS → App (+ Datastore)  
Edges like `uplink_to` / `hosted_by` / `stored_on` / `runs_on`.

**Not** a microservice deployment-identity invocation graph (pod-to-pod call edges from traces).

| UC | Root-cause layer | Ground-truth root CI | Signature | Trap avoided |
|----|------------------|----------------------|-----------|--------------|
| UC-1 | Hypervisor CPU | `esxi-host-01` | `cpu_contention` | Blaming app / individual VMs |
| UC-2 | Network | `switch-core-01:GigE0/2` | `link_failure` | Blaming app or server |
| UC-3 | Storage | `datastore-01` | `storage_contention` | Blaming slow DB app only |
| UC-4 | Guest OS | `guest-os-vm-app-01` | `os_resource_exhaustion` | Blaming app code |
| UC-5 | Application | `orders-api` | `app_resource_exhaustion` | **False-blaming healthy infra** |

Each UC specifies: fault injection idea, decisive telemetry thresholds, per-layer symptoms, correlation logic, and auto-RCA output (root, chain, evidence, blast radius, remediation).

**Corpus packaging:** frozen bundles under `datasets/observeops/` (topology, anomalies, ground truth, metrics, schema + manifest). Both engines consume the **same** bundles.

---

## 6. Two approaches — architecture comparison

### 6.1 Federated pipeline (Panorama → Murphy → Nezha)

**Idea:** Synthesize three research systems that were never designed to interoperate.

| Hop | System | Job | Core algorithm | Graph / data |
|-----|--------|-----|----------------|--------------|
| 1 Detection | **Panorama** | Flag gray / hard-to-see unhealthiness | Bounded look-back majority voting | Observer→subject LOS evidence |
| 2 Macro | **Murphy** | Rank which entity caused the symptom | Counterfactual MRF + Gibbs sampling | Dependency/knowledge graph + metrics |
| 3 Micro | **Nezha** | Rank code/event pattern drift inside a service | Expected vs actual pattern scoring | Per-trace event / pair graph |

**Orchestrator** (new glue): trigger routing, schema translation between hops, narrowing Murphy output for Nezha, confidence fusion.

**Storage sketch:** structural tier (topology, LOS, Murphy metrics) + speed tier (Nezha events / Dragonfly).

**Strengths**

- Murphy offers **partial structural / counterfactual-style** Causal Validity.
- Strong fit for microservice gray failures + code-path drift once that corpus is in scope.
- Novel synthesis vs literature (papers leave handoff gaps).

**Costs**

- Multi-engine ops complexity.
- Gibbs / sampling → weaker reproducibility unless tightly seeded.
- Harder SRE audit (“posterior 0.57”).
- Expensive if run broadly/frequently (Roadblock 5).

### 6.2 Lean pipeline (primary)

**Idea:** One typed CI graph *is* the reasoner. Walk upstream from the symptom with information gain + temporal onset; escalate only when ambiguous.

**Diagnosis flow**

1. Build invocation graph from topology.
2. Best-first upstream walk from symptom seed (info-gain scoring).
3. If onset Δt is ambiguous among candidates → **CARE** (Tier 2).
4. If CARE fires → **scoped causal check** on a tiny candidate set → Tier 3 if verified.
5. Else remain Tier 1 (temporal / shared-upstream / clear winner) — **no Causal Validity claim**.
6. UC-5: upstream-healthy gate blocks infra false-blame.
7. Infer fault signature from crossed signals (hardened AND-matchers; no GT leak).
8. Emit SRE fields: causal chain, blast radius, remediation.

**Evidentiary tiers**

| Tier | Meaning |
|------|---------|
| 1 | Main path — temporal / rules / clear winner |
| 2 | CARE fired; not yet causally verified |
| 3 | CARE + scoped causal check passed |

**PoC tier outcomes:** UC-1 & UC-3 → Tier 3; UC-2, UC-4, UC-5 → Tier 1.

**Strengths**

- Bit-stable by design.
- Easy to audit (signals + chain + tier).
- Cheap per incident (monitor-shaped).
- Matches ObserveOps classic CI inventory.

**Limits**

- Weaker Causal Validity on the main path (by policy).
- Not a substitute for Nezha-depth code-path mining.
- PoC Tier 3 is lightweight (topology + onset plausibility), not full fleet Gibbs.

### 6.3 Same inputs, different questions

| | Lean asks | Federated asks |
|--|-----------|----------------|
| Core question | What failed first / highest info-gain upstream of the symptom? | Who is unhealthy → which entity has highest causal posterior → which patterns shifted? |
| Graph role | One CI graph *is* reasoning | Several substrates coordinated by orchestrator |
| Default causal stance | Temporal + reachability | Murphy structural/counterfactual-style on macro hop |

---

## 7. Design choices & reasoning

### 7.1 Why not mandate Causal Validity everywhere?

**Temporal precedence** (“what failed first among reachable CIs?”) is cheap and enough for many ObserveOps tickets (linkDown, filesystem full, heap with healthy infra).

**Structural causation** (“If ESXi CPU had *not* spiked, would the app still be slow?”) is a different mathematical class — typically interventions + heavy sampling. Running that **globally** across thousands of VMware metrics turns RCA into an inference cluster and violates Roadblock 5.

**Policy:** ration CV — escalate only when Δt is ambiguous (CARE → Tier 3). Do not abolish CV; do not make it the heartbeat.

### 7.2 Why Accuracy is threshold-gated, not “always 100%”

Accuracy is a hard product KPI. Perfect **5/5 on five synthetic UCs** is a useful smoke bar, not a universal forever bar. Prefer a declared floor on larger corpora (e.g. ≥80%) over chasing stochastic peaks that destroy trust.

### 7.3 Why lean wins ObserveOps cost–benefit

| | Federated / Murphy | Lean |
|--|--------------------|------|
| Benefit — Causal Validity | Stronger (partial) | Scoped Tier 3 only |
| Benefit — soft ranking | Posterior over candidates | Single root + evidence (+ CARE) |
| Cost — compute | High if broad | Low |
| Cost — reproducibility | Weaker (~40% here) | Bit-stable (100%) |
| Cost — verifiability | Harder | Easy |
| Cost — ops | Three algos + tiers | One engine |
| Accuracy on this corpus | 5/5 | 5/5 (**no accuracy premium for Murphy CV**) |

Net: lean wins for classic infran ObserveOps. Federated wins when you **explicitly need** deeper structural CV or microservice event/code-path RCA and will pay for it.

### 7.4 Decision guide (what to choose when)

| Situation | Choose |
|-----------|--------|
| Classic infran ObserveOps RCA | **Lean** |
| Same incident must always yield same verdict | **Lean** |
| SRE must explain answer in minutes from metrics/topology | **Lean** |
| Clear Δt + hard signals | **Lean Tier 1** |
| Ambiguous Δt (noisy neighbor, multi-VM host) | **Lean CARE → Tier 3** |
| Tight compute ceiling | **Lean** |
| Strongest structural/counterfactual localization | **Federated / Murphy** |
| Microservice gray failure + code-path drift | **Federated** |
| Hybrid product roadmap | **Primary evaluation engine (ADR-001) + federated optional** |

---

## 8. PoC method & journey

```
Use-case spec (UC-1..UC-5)
        ↓
Frozen corpus datasets/observeops/
        ↓
   ┌────┴────┐
   ↓         ↓
Federated   Lean
   └────┬────┘
        ↓
Matched bakeoff + four-axis compare
        ↓
ADR-001: primary evaluation engine
        ↓
Package lean_rca (CLI / HTTP / SRE / systemd)
```

### Phases completed

| Phase | What | Status |
|-------|------|--------|
| **A** Bakeoff close | Fix federated fusion; four-axis compare; matched runs; decision memo | Done |
| **B** Lean PRD depth | Tiers 1/2/3; CARE→causal; signatures; best-first vs naive BFS efficiency | Done |
| **D** Packaging | ADR-001; `lean_rca`; SRE report; `lean-rca.service` | Done |

### Key technical fixes that made comparison fair

- Federated: Murphy posterior recovery on UC-2/UC-3 — removed lean-heuristic fallback from the fusion path.
- Lean: evidentiary tiers correctly labeled; scoped causal only after CARE; signatures hardened to use-case AND-conditions.
- Compare harness: identical ground truth, reproducibility N=20, observation efficiency metrics.

### What we shipped (primary evaluation engine)

```bash
# SRE report
PYTHONPATH=lean-pipeline:. python -m lean_rca diagnose UC-1 --format report

# HTTP API :8780
./lean-pipeline/scripts/serve-rca.sh
# GET /health  ·  GET /v1/diagnose/UC-1  ·  POST /v1/diagnose
```

Fields on every verdict include causal chain, blast radius, and remediation hints aligned with UC section (e).

---

## 9. Benchmarking contract

Scored **identically** for both engines against `datasets/observeops/*/ground_truth.json`.

| Metric | Definition |
|--------|------------|
| Root-CI accuracy | `verdict.root_ci == ground_truth.root_ci` |
| Signature match | Fault signature matches GT |
| UC-5 false infra blame | Automatic **fail** if app fault blamed on host/switch/datastore |
| Reproducibility | % of N=20 runs with bit-identical verdict |
| Verifiability | Evidence cites decisive signals; lean also reports tier / CARE / causal |
| Efficiency | Observations to verdict; lean also reports best-first vs naive BFS |

**Winner policy (per UC):** accuracy first (with UC-5 guard), then fewer observations, then explicit latency; else tie.

**Matched run ids:** `bakeoff-phase-a-001` (decision call), **`bakeoff-phase-b-002`** (latest scoreboard; corpus v1.1.0). Historical: `bakeoff-phase-b-001`.

---

## 10. Results (`bakeoff-phase-b-002`)

### 10.1 Overall scoreboard

| Metric | Federated | Lean |
|--------|-----------|------|
| Root-CI accuracy | **5/5** | **5/5** |
| Signature match | 5/5 | 5/5 |
| UC-5 infra false-positive | 0 | 0 |
| Reproducibility | **40%** | **100%** |
| Avg observations | 5.60 | **5.00** |
| Lean best-first vs naive BFS (avg) | — | 2.40 vs 2.80 (ratio **1.12**) |
| Verifiability (main path %) | **100%** (5/5 main) | 60% (3/5 main; 2 CARE→Tier 3) |

**Overall better on this corpus: lean.**

### 10.2 Per use-case

| UC | Ground truth | Both correct? | Repro F / L | Lean tier | Per-UC winner* |
|----|--------------|---------------|-------------|-----------|----------------|
| UC-1 | `esxi-host-01` | Yes | 100% / 100% | Tier 3 (CARE + causal) | Tie |
| UC-2 | `switch-core-01:GigE0/2` | Yes | 0% / 100% | Tier 1 | **Lean** |
| UC-3 | `datastore-01` | Yes | 0% / 100% | Tier 3 (CARE + causal) | Federated† |
| UC-4 | `guest-os-vm-app-01` | Yes | 100% / 100% | Tier 1 | Lean |
| UC-5 | `orders-api` | Yes | 0% / 100% | Tier 1 | Lean |

\*Winner after accuracy uses observation-count / tie-break rules.  
†UC-3: federated used fewer observations (5 vs lean 6) despite lean’s Tier-3 depth — accuracy tied.

### 10.3 Efficiency detail

| UC | Fed obs | Lean obs | Lean best-first | Lean naive BFS | Ratio |
|----|---------|----------|-----------------|----------------|-------|
| UC-1 | 6 | 6 | 3 | 3 | 1.00 |
| UC-2 | 6 | 5 | 4 | 5 | 1.25 |
| UC-3 | 5 | 6 | 3 | 4 | 1.33 |
| UC-4 | 6 | 4 | 1 | 1 | 1.00 |
| UC-5 | 5 | 4 | 1 | 1 | 1.00 |

### 10.4 How to read reproducibility

Federated multi-hash on UC-2/3/5 shows stochastic / path-variance on the federated stack even when top-1 root CI is often correct. Lean is bit-identical across N=20 on all five UCs — the operational property ObserveOps needs for incident compare/diff and change control.

---

## 11. Analysis — what the numbers mean

### 11.1 Accuracy tied — so other axes decide

Both engines hit every ObserveOps root and signature on this corpus. That is important: **Murphy’s CV advantage did not translate into higher accuracy here.** Paying federated’s cost does not buy a correctness premium on classic infra UC-1..UC-5.

### 11.2 Reproducibility is the decisive ObserveOps gap

40% vs 100% is not a rounding error. Ops teams need:

- Same ticket → same answer after redeploy of the RCA service.
- Diffable verdicts across time.
- Trust in demos and customer PoCs.

Lean satisfies this by construction. Federated needs heavy gating/seeding to approach it.

### 11.3 Verifiability favors lean for SRE narrative

Lean emits explicit tiers, CARE flags, causal logs, and SRE report fields. Federated fusion + posteriors can be correct but are harder to explain under time pressure. On **`bakeoff-phase-b-002`**, federated has a higher **main-path %** (no CARE fallback) while lean fires CARE on UC-1/UC-3 — that is intentional depth, not weaker evidence. The bakeoff still scores **Verifiability** to lean for auditability of the chain.

### 11.4 Efficiency — lean lighter overall; not uniformly on every UC

Lean averages fewer observations and shows modest best-first gains vs naive BFS. UC-3 is the counterexample on raw observation count (federated 5 vs lean 6) while lean spends budget on CARE→Tier 3 — acceptable for Recommended CV, not a reason to switch primary engines.

### 11.5 Causal Validity — keep as Recommended, not Mandatory

UC-1/UC-3 exercise the Recommended Tier-3 path. UC-2/4/5 correctly stay Tier 1 with hard signals / clear stops / anti-FP. This matches the ObserveOps ticket mix: most incidents should not pay for structural CV.

### 11.6 Limits of the evidence

- Corpus size is **five** synthetic UCs — smoke, not a fleet study.
- Federated ObserveOps path is an adapter over the research stack, not a full ObserveOps production ingest.
- Capacity (~21K EPS on 2-core WSL Dragonfly) is **not** an ObserveOps acceptance metric and is not a 64-core production estimate.
- Lean Tier 3 ≠ full Murphy-quality counterfactuals.

---

## 12. Conclusion

### 12.1 Decision (ADR-001)

**Bakeoff evaluation finding:** Use **lean as the primary evaluation engine** for ObserveOps classic infrastructure paths (network → host → VM → OS → app). **Not a finalized GTM or product commitment.**

**Keep federated** as an optional future hybrid component for microservice code-path, gray-failure, and pair-mining workloads — once a dedicated microservice evaluation corpus is in scope.

### 12.2 Why this is the right ObserveOps call

1. Accuracy is tied on the declared corpus (**Roadblock 4** GT contract makes that comparison fair).
2. Reproducibility and verifiability — corpus Mandatories — strongly favor lean.
3. Roadblock **1b** (joined typed CI graph) is what lean walks; Roadblock **5** (cost) favors lean’s temporal-first design.
4. Murphy’s CV edge is real but misaligned as the *default* brain for classic infra tickets.
5. Lean is already packaged as a product-shaped CLI/API with SRE outputs.

### 12.3 One-sentence story for stakeholders

> We compared a research-grade three-algorithm federated stack to a lean topology walk on the same ObserveOps use-cases; both were accurate, but only lean was bit-stable, auditable, and cheap enough to **favor as the primary evaluation engine** (not yet a finalized shipping decision).

---

## 13. Suggested NotebookLM / slide outline

Use these as generation prompts or section titles:

1. **Title** — Unified RCA PoC: Lean vs Federated for ObserveOps  
2. **Problem** — Symptom apps hide upstream infra roots  
3. **Objective** — Pick primary engine with same-corpus evidence  
4. **Corpus** — Five layers, five traps (UC-1..UC-5 table)  
5. **Qualities & roadblocks** — Repro + Verifiability Mandatory; Accuracy thresholded; CV Recommended; Mandatories **1b** + **4** (do not skip GT)  
6. **Approach A** — Federated Panorama→Murphy→Nezha  
7. **Approach B** — Lean walk + CARE + scoped Tier 3  
8. **Design choice** — Why not fleet-wide counterfactuals  
9. **Method** — Frozen bundles → matched bakeoff → ADR  
10. **Results scoreboard** — 5/5 vs 5/5; 40% vs 100% repro  
11. **Per-UC story** — Host / net / storage / OS / app anti-FP  
12. **Cost–benefit** — Murphy CV vs ObserveOps ops fit  
13. **Decision** — Primary evaluation engine (ADR-001); federated optional hybrid  
14. **Shipped** — `lean_rca` CLI/API/SRE report  
15. **Open questions** — brainstorming (next section)  
16. **Ask** — Align on hybrid boundary + next corpus size

---

## 14. Brainstorming prompts (open questions)

Use these in NotebookLM chat or workshop discussions:

1. What is the **accuracy floor** we will publish for the next (larger) ObserveOps corpus — 80%? 90%? How do we expand UCs without overfitting rules? (**Roadblock 4** stays corpus-local convention unless we join an external benchmark.)
2. Should ObserveOps UI **expose evidentiary tiers** to customers, or only internally?
3. When (if ever) do we **invoke Murphy** from lean as a paid Tier-3/4 escalation on ambiguous tickets?
4. How do we productize **blast radius + remediation** into ObserveOps incident workflows without auto-remediation?
5. What is the first **non-synthetic** ObserveOps customer topology we should freeze as Corpus B.1?
6. Do we need a **microservice corpus** this year, or is classic infra enough for the ObserveOps roadmap?
7. How should reproducibility be **regression-tested in CI** (N=20 harness on every engine change)?
8. Is lightweight Tier 3 “good enough” CV messaging, or do we risk overclaiming “causal” in marketing?
9. Where does **log/event multimodal** fusion fit if lean misses OS signals that Nezha would catch?
10. What capacity SLO (EPS / p99 diagnose latency) makes lean “production-adjacent” without Phase E fantasy numbers?

---

## 15. Glossary (quick)

| Term | Meaning |
|------|---------|
| CI | Configuration Item (host, switch port, datastore, OS, app, …) |
| CARE | Ambiguity fallback when onset Δt among candidates is unclear |
| Tier 1/2/3 | Lean **evidentiary** depth labels (ours): Tier 1 = main path, no causal claim; Tier 2 = CARE correlational ranking under Δt ambiguity; Tier 3 = CARE + scoped causal check. Not Netdata/Dynatrace product tiers. |
| Top-1 accuracy | How often the system’s **first / single chosen** root matches ground truth on a fixed eval set (paper metric; e.g. Nezha ~89.77% avg top-1 [FSE’23]) |
| Federated | Panorama + Murphy + Nezha + orchestrator |
| Lean | Single-engine typed-graph RCA (primary evaluation engine per ADR-001; not finalized) |
| Corpus B | ObserveOps UC-1..UC-5 (+ UC-3b adversarial in v1.1.0) |
| Corpus A | Optional microservice / DeathStarBench-style track (deferred) |
| ADR-001 | Evaluation finding: lean favored on ObserveOps corpus (not a finalized product commitment) |
| Netdata (placement) | Product docs: correlation ranking; root often in top **30–50** results — looser bar than paper top-1 / our single-candidate contract. See Lean PRD Appendix E. |
| Dynatrace Davis (placement) | Claims causal AI; no independent published top-1 we can scoreboard — philosophy precedent only. See Lean PRD Appendix E. |

---

## 16. Source map (if you need deeper detail)

| Topic | Canonical doc |
|-------|----------------|
| This briefing | `docs/POC_BRIEFING.md` (you are here) |
| Qualities / decision guide | `docs/README.md` |
| Roadmap / phases | `docs/ROADMAP.md` |
| Engine ADR | `docs/ADR-001-lean-primary-engine.md` |
| Use-cases | `docs/rca-use-cases-only.md` |
| Bakeoff numbers | `benchmarking/results/comparison/COMPARISON.md` |
| Decision memo | `benchmarking/results/comparison/DECISION.md` |
| Benchmark contract | `datasets/observeops/COMPARISON_BENCHMARK.md` |
| Federated design | `federated-pipeline/docs/ARCHITECTURE.md` (+ limitations / storage tiers) |
| Lean engine notes | `lean-pipeline/core_engine/observeops/README.md` |
| Lean PRD / Simple Guide | `docs/Lean_RCA_PRD.md` (canonical) · [`Lean_RCA_PRD.pdf`](./Lean_RCA_PRD.pdf) · `docs/Lean_RCA_Simple_Guide.md` · [`Lean_RCA_Simple_Guide.pdf`](./Lean_RCA_Simple_Guide.pdf) — regenerated 2026-07-16 from MD |
| Standard RCA evaluation checklist (any method) | `docs/RCA_EVALUATION_CHECKLIST.md` |
| Dynatrace / Netdata vs papers + lean Tier 1/2/3 | `docs/Lean_RCA_PRD.md` **Appendix E** (worked example of the checklist) |

---

*End of briefing. Upload this file to NotebookLM as the primary source for slide generation; add the Lean PRD / Simple Guide **Markdown** (or regenerated PDFs) for deeper algorithm/product language.*
