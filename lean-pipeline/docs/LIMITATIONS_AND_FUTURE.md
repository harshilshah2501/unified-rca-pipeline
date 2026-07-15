# Lean ObserveOps RCA — Limitations & Future Work

Companion to [`ARCHITECTURE.md`](./ARCHITECTURE.md). This document states what lean **does not** claim today, and what is intentionally deferred.

ObserveOps decision context: lean is **primary** for classic infra ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)). Federated remains an optional hybrid for microservice / code-path work.

---

## 1. Limitations (current shipping engine)

### 1.1 Temporal earliest ≠ root cause (by design)

Onset ranking is a clue. Without ObserveOps **shared-upstream / signature / contributor** rules, lean would mis-blame earliest noise (e.g. UC-3b early switch). Operators must not simplify the product story to “who got sick first.”

### 1.2 CARE is a PoC approximation

PRD Section 2.3 describes CARE spectrum scoring + PageRank. The ObserveOps implementation ranks by **severity sum** (`value/threshold`) under Δt ambiguity, then still prefers shared-upstream when applicable. Published CARE 72–89% figures are **not** ObserveOps bakeoff claims.

### 1.3 Tier-3 causal check is scoped and lightweight

`verify_care_root` checks topology reachability + onset order on a tiny candidate set. It is **not**:

- Pearl-style fleet counterfactuals  
- Murphy MRF / Gibbs sampling  
- PC/FCI causal discovery over historical edge populations  

Causal Validity is **Recommended**, claimed only on Tier 3. Most ObserveOps tickets correctly stay Tier 1.

### 1.4 Circular / mutual dependency graphs

True A ↔ B microservice cycles weaken temporal “who first.” lean path under evaluation UCs use a **layered classic-infra** graph, not call cycles. Cyclic stress is an explicit non-goal for this corpus ([`rca-use-cases-only.md`](../../docs/rca-use-cases-only.md)); optional honesty fixtures may document the limit later.

### 1.5 No full multimodal log mining

Lean does **not** run Nezha Drain free-text log mining. Structured synthetic **`events.json`** lines (UC-2 / UC-4 / UC-3b) are cited in evidence. Deeper log/code-path RCA belongs to the optional federated / Nezha track.

### 1.6 Frozen-bundle evaluation only

Runtime today diagnoses by **corpus UC id** against `datasets/observeops/`. Live SNMP / vCenter inject, streaming alert buses, and alert suppression (UC narrative step (d)) are **not** implemented in the lean package. HTTP `POST` with an inline `bundle` returns **501**.

### 1.7 Remediation is advisory

`remediation` strings are signature-keyed operator hints. Automated change execution is out of scope.

### 1.8 No LLM in the deduction path

An LLM may narrate an already-computed verdict. It must not select `root_ci` / `signature` (Verifiability + hallucination Accuracy).

### 1.9 Roadblock honesty (ObserveOps split)

| Roadblock | Lean ObserveOps reality |
|-----------|----------------------|
| **1a** Blind spots | Optional; frozen bundles expose decisive signals. Boundary-flagging for true third-party opacity is Corpus A / deferred. |
| **1b** Cross-domain silos | **Org silos unsolved.** Joined typed multi-domain graph **demonstrated** on this corpus. |
| **2** Non-stationary topology | Optional here (topology frozen per bundle). |
| **3** Pod churn | Out of scope (classic VMs/hosts). |
| **4** Ground truth | Field-wide still open. **Corpus GT convention Mandatory** and implemented. |
| **5** Cost ceiling | Respected by cheap main path; do not run fleet Gibbs on every ticket. |

### 1.10 Accuracy floor vs tiny corpus

UC-1..UC-5 **5/5** is a useful smoke bar, not a universal Accuracy product bar. Prefer a declared floor on a larger corpus over equating “Mandatory Accuracy” with “always 100% forever.”

### 1.11 Upstream-healthy gate and GT

`upstream_healthy.gate` can honor a `ground_truth.upstream_healthy` flag when present, in addition to runtime “no infra crossed” logic. Bakeoff fairness assumes the ObserveOps GT contract; do not treat that flag as a free production oracle.

---

## 2. Future work

Ordered by ObserveOps relevance. Phases A/B/D are **complete** ([`ROADMAP.md`](../../docs/ROADMAP.md)).

### 2.1 Near-term product hardening (optional)

| Item | Intent |
|------|--------|
| Larger classic-infra corpus | Raise Accuracy measurement beyond 5 synthetic UCs; keep Reproducibility Mandatory |
| Inline / live bundle API | Lift HTTP 501; accept topology+anomalies+events without pre-frozen UC folders |
| Richer CARE | Spectrum + topology weighting closer to PRD §2.3 if ObserveOps needs it for ambiguous multi-tenant storage |
| Alert-bus integration | Wire verdicts to suppress symptom alerts (UC step (d)) without changing root selection |
| Operator UX | Persist SRE reports, compare incidents (bit-stable diffs), export evidence packs |

### 2.2 Continuous causal memory — roadmap **B5** (Section 2.8)

Background learner accumulates structure from healthy traffic and past incidents so incident-time CV becomes a cheap lookup rather than only CARE-triggered verification.

**Requires:** persistent model store, update/retrain cadence, invalidation under topology change (Roadblock 2).  
**Not required** for lean path under evaluation packaging today.

### 2.3 Microservice / federated hybrid — roadmap **C\***

When ObserveOps scopes code-path / gray-failure / pair-mining:

| Workload | Engine |
|----------|--------|
| Classic infra (this path) | **Lean** (unchanged primary) |
| Microservice code-path / cycles / Nezha depth | Federated optional hybrid |

Corpus A (DeathStarBench / TrainTicket / pod churn / true 1a blind-spot) remains a **deferred research track**, not an ObserveOps acceptance gate.

### 2.4 Scale / capacity — roadmap **E\***

Event encoding size, structural tier at large entity counts, fleet sizing. Explicitly **not** PoC-blocking; measure before claiming hyperscale economics.

### 2.5 Explicitly out of lean path under evaluation path

- Replacing ObserveOps eval with Nezha Online Boutique / TrainTicket accuracy claims  
- DeathStarBench harness as an ObserveOps gate  
- 1B EPS deployment work before measured capacity inputs  
- Universal causal-graph construction on every ticket  
- LLM-as-reasoner for root cause  

---

## 3. What “done” means for classic ObserveOps lean

| Capability | Status |
|------------|--------|
| Typed classic-infra walk + ObserveOps rules | **Shipped** |
| Tiers 1/2/3 + CARE → scoped causal | **Shipped** |
| Signatures + contributors + events evidence | **Shipped** |
| UC-3b early-noise resistance | **Shipped** |
| CLI / HTTP / SRE report / systemd | **Shipped** |
| Same-corpus bakeoff vs federated; lean primary | **Done** (ADR-001) |
| B5 / live ingest / microservice corpus / E\* | **Deferred** |

---

## 4. Related documents

| Document | Role |
|----------|------|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Components and diagnose workflow |
| [`../../docs/Lean_RCA_PRD.md`](../../docs/Lean_RCA_PRD.md) | Requirements (incl. ObserveOps corrections) |
| [`../../docs/POC_BRIEFING.md`](../../docs/POC_BRIEFING.md) | Stakeholder / NotebookLM narrative |
| [`lean_rca_prd_insights_ae5f991e.plan.md`](./lean_rca_prd_insights_ae5f991e.plan.md) | **Historical** early plan — prefer ROADMAP + this file |

---

*Limitations & future work for lean-pipeline. ObserveOps shipping state (2026-07-13).*
