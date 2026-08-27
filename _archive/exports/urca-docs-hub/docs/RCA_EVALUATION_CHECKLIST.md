# Standard Evaluation Checklist for RCA Methods

**Scope:** Common project documentation — applies to **any** RCA method (academic, commercial, lean, federated, or proposed internally), now or in the future.  
**Not** limited to the lean engine. Lean-specific architecture stays in [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md).

**Purpose:** Evaluate every method with the **same fixed questions** used for Panorama, Murphy, Nezha, CARE, Dynatrace, and Netdata — not ad hoc.  
**Motivation:** Dynatrace’s causal claim and Netdata’s ranked-list accuracy story are both real product statements, but neither sits correctly next to peer-reviewed academic numbers unless you ask the **same** questions of all systems.

Apply this checklist to any new method **before** comparing it to anything already scored in this repo.

**What this checklist produces:** a provenance-tagged profile across four independent axes and five roadblocks — **not** a single winner score and **not** a universal ranking of “best RCA.”

---

## Cross-cutting requirement: Evidence Provenance

Every score under the four axes and five roadblocks must carry a **provenance tag**. This is what catches unverified vendor claims early (e.g. Dynatrace “causal AI” without an independent accuracy figure).

| Provenance tag | Definition | Example |
|----------------|------------|---------|
| **Peer-reviewed / academically published** | Claim appears in a published, peer-reviewed paper (or equivalently citable study) with a stated methodology | Panorama’s 15/15 gray-failure detection [OSDI’18]; Nezha’s ~89.77% average top-1 [FSE’23] |
| **Vendor self-reported** | Claim comes from company docs or marketing; no independent third-party verification found | Dynatrace Davis “causal reasoning” claim |
| **Internally measured** | Produced by this project’s own benchmarking (bakeoff, N-run reproducibility, etc.) | ObserveOps lean vs federated 5/5 accuracy; lean 100% reproducibility |
| **Estimated, not measured** | Calculation or projection that was never actually tested | Federated design node-count / cost projections that were never instrumented |

**Plain term — top-1 accuracy:** On a fixed evaluation set with a known correct root cause, how often the system’s **first-ranked or single chosen** answer matches that truth. Nezha’s ~89.77% top-1 means the primary suggested region was correct about nine times in ten **on that paper’s corpus**. It is a **paper metric**, not automatically an ObserveOps bakeoff score.

---

## Part 1 — Four-axis diagnostic questions

Do **not** average or collapse these four scores into one number. They are independent (see [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) Appendix D).

| Axis | Diagnostic questions | Scoring scale |
|------|----------------------|---------------|
| **Reproducibility** | Given identical input, does the method produce identical output? Does it use random sampling or stochastic optimization — and if so, is a fixed seed enough? Has this been **tested** across repeated runs, or only assumed from the method description? | **High** (tested, deterministic) / **Partial** (deterministic only under fixed conditions, e.g. seeded) / **Low** (materially different outputs across runs) / **Untested** |
| **Verifiability** | Can a human reconstruct *why* the method reached its output using only what the method **emits** — not its source code? Is the reasoning a plain evidence trail, or does it need statistical/ML expertise? Is the output **one explained verdict**, or an unranked / loosely ranked list that still needs human triage? | **High** (direct trail, single verdict) / **Medium — expert-dependent** (inspectable but needs ML/stats literacy) / **Medium — ranked list** (many candidates; human must finish the job) / **Low** (no inspectable reasoning). Prefer stating *which* Medium failure mode applies. |
| **Accuracy** | Is there a published figure (top-1, top-k, precision/recall, error reduction)? Measured on production data, a synthetic benchmark, or not measured? Figure for this method alone, or for a full deployed pipeline? | Report the **actual figure** + **provenance tag**. Do **not** compress to High/Medium/Low alone — the precision of the claim is part of the evaluation. If unmeasured, say **Untested**. |
| **Causal Validity** | Does the method’s own documentation claim to establish **causation**, not merely correlation? What mechanism (if any) tests causal structure — counterfactual check, conditional independence, intervention — versus ranking by association or temporal proximity alone? Do the authors acknowledge incompleteness? | **No claim** (correlation / temporal only, stated) / **Implicit correlation dressed as causation** (says “root cause” with no causal test) / **Partial** (some causal mechanism; self-acknowledged incomplete) / **Tested** (interventional / counterfactual / independence-tested, with evidence) |

**Alignment note:** In *this* project’s lean engine, Causal Validity may only be claimed at **evidentiary Tier 3** (CARE + scoped causal check). That Tier 1/2/3 scheme is lean-specific; when scoring Dynatrace, Netdata, Murphy, etc., use the Causal Validity row above — do not force foreign products into lean tier labels.

---

## Part 2 — Five-roadblock diagnostic questions

Roadblock **Category A / B / C** means **ownership status**, not “how bad” the method is:

| Category | Meaning (from project PRD) |
|----------|----------------------------|
| **A** | Built and measured |
| **B** | Proposed / partially measured |
| **C** | No known architectural solution (often field-wide) |

| Roadblock | Diagnostic questions | Typical category |
|-----------|----------------------|------------------|
| **1a. Instrumentation blind spots** | Defined behavior when the method hits a component it cannot see — explicit halt-and-flag, or silent guess past the boundary? Is full instrumentation coverage a baked-in assumption? | A / B / C |
| **1b. Cross-domain fragmentation** | Assume one unified data source, or explicitly bridge separate organizational stores (network NMS, app tracing, security tooling)? | Almost always **C** at org scale; a joined corpus graph can still be **A** *for that corpus* |
| **2. Non-stationary topology** | Rebuild topology live per incident, or rely on a cached/stale snapshot? Defined behavior for a component with no history yet? | A / B / C |
| **3. Ephemeral entity identity** | Unit of identity — raw instance ID, or stable logical identity? If raw instance ID, how much history per instance, and does it survive realistic churn? | A / B / C (often out of scope for classic long-lived infra) |
| **4. No standardized ground truth** | What benchmark/dataset? Community-standard (e.g. DeathStarBench / TrainTicket) or proprietary/undisclosed? | Field-wide almost always **C**; **corpus-local** shared GT + matched bakeoff can be **A** for *that* bakeoff only |
| **5. Compute / cost ceiling** | Actual measured infrastructure footprint at claimed scale? Measured or estimated? Load concentrated centrally, or distributed (e.g. edge)? | A / B / C — “distributed architecture” alone is **not** proof of low cost |

Expect Roadblocks **1b** and **4** to fail field-wide for nearly every method, including future ones. A method that claims to solve either should get **extra scrutiny**, not automatic credit. Do **not** treat Category C as “this method is worse” — it often means “the field has not solved this.”

---

## How to use this checklist

1. Score every axis and roadblock using the questions above.
2. Tag **every** score with Evidence Provenance.
3. Keep the four axis scores **visibly separate** — never average them into one number.
4. For Accuracy: always keep **figure + provenance** (or Untested).
5. Apply the same checklist to commercial and academic methods before placing them on the same table.
6. Optional: apply an **ObserveOps deployment profile** on top (e.g. Reproducibility + Verifiability mandatory; Causal Validity only when claimed; Roadblocks 1b + 4 mandatory *as corpus convention*). That profile is product-specific; this checklist remains general.

### Worked examples already in this repo (templates)

| Example | Where | What it illustrates |
|---------|-------|---------------------|
| Panorama / Murphy / Nezha on four axes | [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) Appendix D | Peer-reviewed methods; axes kept separate |
| Dynatrace / Netdata vs papers | [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) Appendix E | Vendor self-reported vs peer-reviewed; ranked-list vs top-1 |
| Lean vs federated bakeoff | [`../benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md) | Internally measured Accuracy + Reproducibility |
| Qualities & roadblocks for ObserveOps | [`README.md`](./README.md) | How Mandatories map onto this checklist for one product path |

### Blank scoring sheet (copy for a new method)

```text
Method: ____________________
Date: ____________________
Scorer: ____________________

Provenance legend: peer-reviewed | vendor self-reported | internally measured | estimated

Axis                  Score              Provenance    Notes
Reproducibility       High/Partial/Low/Untested
Verifiability         High / Medium-expert / Medium-list / Low
Accuracy              <figure or Untested>
Causal Validity       No claim / Implicit / Partial / Tested

Roadblock             Category A/B/C     Provenance    Notes
1a Instrumentation
1b Cross-domain
2  Non-stationary topology
3  Ephemeral identity
4  Ground truth
5  Compute/cost
```

---

## Related docs

| Doc | Role |
|-----|------|
| [`README.md`](./README.md) | Four qualities + five roadblocks for ObserveOps |
| [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) | Lean architecture; Appendix D/E are *applications* of this checklist |
| [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md) | Plain-language roadblocks |
| [`POC_BRIEFING.md`](./POC_BRIEFING.md) | Stakeholder narrative |
| [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) | Engine choice for ObserveOps corpus (not a universal RCA ranking) |

---

*Added 2026-07-16 as common evaluation protocol for all RCA methods in Unified RCA.*
