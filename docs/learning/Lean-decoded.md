> **Study notes — not a scoreboard.** Canonical numbers: `benchmarking/results/comparison/` and `docs/`.

# Lean RCA Study v2 (Repo-Aligned)

Purpose: Build a comprehensive learning note for Lean that uses the same evidence tags as `Federated-decoded.md`.

**Doc map:** [`docs/NAVIGATION.md`](docs/NAVIGATION.md)

Tag legend:
- [Implemented] Present and used in current repo flows.
- [Simulated] Present in PoC/eval adapters / frozen bundles, not full live production ingestion.
- [Aspirational] Architecture vision or future capability not fully realized here.
- [Corrected] Coach/LLM claim that was wrong or incomplete — corrected below.

---

## 1) What Lean Means in This Repo

- Lean is the primary **evaluation** engine for ObserveOps classic-infra UC corpus.
- Decision is corpus-scoped (ADR-001): **not** a finalized product commitment.
- Lean is optimized for reproducible, auditable inference on a typed CI graph.

Status tags:
- Lean as primary evaluation engine for current ObserveOps corpus: [Implemented]
- Lean as finalized global product decision: [Not true here]

---

## 2) Corrected one-liner (keep this)

> Lean walks a typed CI graph upstream with **best-first + info-gain**, applies **ObserveOps rules**, uses **CARE only under onset ambiguity**, and claims causal validity only on **scoped Tier 3** — on **frozen corpus inputs** in this PoC, not a full live ingest stack.

---

## 3) Motivation (why Lean exists) — tagged

| Coach claim | Verdict | Tag |
|-------------|---------|-----|
| Federated three-algo + dual-tier is expensive (CPU/ops) | Directionally true as cost posture | [Implemented] as design rationale; full dual-tier prod cost still [Aspirational] |
| Federated reproducibility ~40% vs lean 100% on ObserveOps bakeoff | Accurate for this corpus | [Implemented] (`bakeoff-phase-b-002`) |
| Classic infra often has clear layered chains | Accurate for ObserveOps UCs | [Implemented] |
| Lean matches 5/5 accuracy at lower cost/complexity | Accurate **on this corpus** | [Implemented] |
| Therefore Lean is always better everywhere | Too absolute | [Corrected] — corpus-scoped evaluation finding only |

---

## 4) Ingestion vs RCA (Lean)

### A) Ingestion (data plane)

| Coach claim | Correction | Tag |
|-------------|------------|-----|
| Lean “deletes” the event-graph speed tier | Lean does **not** require federated-style dual-tier speed store for classic infra | [Implemented] contrast vs federated vision |
| Lean needs zero ingestion | Wrong — still needs topology + anomalies (+ events on some UCs) | [Corrected] |
| Graph is Switch → Host → Pod | ObserveOps stack is **Network → ESXi → VM → Guest OS → App (+ Datastore)** | [Corrected] / [Implemented] |
| On-demand live metric sampling at incident time | Teaching idea; PoC reads **frozen bundles** | [Simulated] for PoC; live sampling [Aspirational] |
| 1B EPS comparison | Capacity vision for federated, not lean requirement | [Aspirational] (federated); not lean default |

PoC reality:
- Bundle ingest from `datasets/observeops/`: [Implemented] / [Simulated]
- Full enterprise collectors/connectors around lean: [Aspirational]

### B) RCA (reasoning plane)

Lean RCA on ObserveOps corpus: [Implemented]

---

## 5) Algorithms — what Lean actually runs

### Correct sequence (not “CARE framework”)

CARE is **not** the whole engine. Correct order: [Implemented]

1. **Best-first walk** upstream from symptom CI (priority by score — **not** FIFO BFS).
2. **Info-gain / temporal** cues prioritize which upstream neighbors to check.
3. **ObserveOps rules** decide/refine root: `shared_upstream`, signatures, contributors, `upstream_healthy`.
4. **CARE** only if ≥2 candidate onsets fall within Δt window (~10s).
5. **Tier-3 scoped causal** (`verify_care_root`) only on the CARE path when verification passes.

| Coach claim | Correction | Tag |
|-------------|------------|-----|
| Lean = CARE framework | CARE is ambiguity **fallback** only | [Corrected] |
| “Best-First Search (BFS)” | Best-first ≠ BFS; naive BFS is bakeoff efficiency baseline | [Corrected] / [Implemented] |
| `Score = Onset Primacy + Severity` | Teaching shorthand; real scorer is richer | [Corrected] (approx) / [Implemented] (info-gain module exists) |
| CARE always runs | False — UC-2/4/5 often stay Tier 1 | [Corrected] |
| Δt≤10s → CARE | Matches PoC window | [Implemented] |

### ObserveOps rules (often under-taught by coach)

| Rule | Role | Tag |
|------|------|-----|
| `shared_upstream` | Multi-VM same pain → host (CPU) or datastore (storage); beats earliest CI on UC-3b | [Implemented] |
| Signatures | Name fault class (`cpu_contention`, `link_failure`, …) | [Implemented] |
| `upstream_healthy` | Anti-FP gate (esp. UC-5): don’t blame healthy infra when app is root | [Implemented] |

---

## 6) Evidentiary tiers — corrected

| Tier | When | Causal claim? | Tag |
|------|------|---------------|-----|
| **1** | Main path; no CARE | No | [Implemented] |
| **2** | CARE fired; correlational / severity ranking (shared-upstream may still win) | No | [Implemented] |
| **3** | CARE fired **and** `verify_care_root` passed | Yes — scoped, lightweight | [Implemented] |

| Coach claim | Correction | Tag |
|-------------|------------|-----|
| Tier 3 = “topology paths break down” | Too dramatic — Tier 3 = CARE + scoped verify | [Corrected] |
| Same-second DB+API on shared host → always Tier 2 | CARE **path** starts; may promote to **Tier 3** if causal verifies; shared-upstream can dominate CARE severity | [Corrected] |
| Higher tier always better product | No — Tier 1 is correct when evidence is decisive | [Corrected] |

UC snapshot (canonical bakeoff pattern):
- UC-1 / UC-3: often Tier 3 after CARE — [Implemented]
- UC-2 / UC-4 / UC-5: often Tier 1 — [Implemented]
- UC-3b: CARE fires; **shared datastore wins** over early switch — [Implemented]

---

## 7) Graph walk & `upstream_healthy` — corrected

### What the walk does [Implemented]

1. Start at symptomatic CI (effect).
2. Expand **upstream** neighbors by best-first / info-gain.
3. Apply rules + temporal / CARE as needed.
4. Emit root, signature, evidence, tier.

### What coach got wrong about `upstream_healthy`

| Coach claim | Correction | Tag |
|-------------|------------|-----|
| Walk until upstream is healthy → that node is always root | Oversimplified “end of broken trail” teaching story | [Corrected] |
| `upstream_healthy` is the main root finder | Primary use is **anti-false-positive** (keep app root when infra healthy — UC-5) | [Corrected] / [Implemented] |
| Healthy disk ⇒ database is always root | Plausible teaching analogy; real engine also uses shared-upstream, signatures, CARE | [Corrected] |

Useful intuition to keep:
- Failures often look like a **trail of abnormal CIs**; healthy upstream means “don’t keep blaming further infra.”
- That intuition ≠ the full root-selection policy.

Power-outage / breaker analogy: good for **search direction**, weak as the complete rooting algorithm.

---

## 8) Self-check (true / false)

1. CARE runs on every diagnose. → **False**  
2. Best-first == BFS. → **False**  
3. `upstream_healthy` mainly stops false infra blame (esp. UC-5). → **True**  
4. Shared-upstream can beat “earliest CI” under CARE (UC-3b). → **True**  
5. Lean needs zero ingestion in production. → **False** (lighter, not zero)  
6. ADR-001 is a finalized shipping decision. → **False**

---

## 9) Where Lean is strong / limited

Strong [Implemented]:
- Reproducibility on corpus reruns
- Verifiable tiers + CARE/causal trail
- Efficiency posture vs Roadblock 5 on classic infra
- Explicit anti-FP behavior

Limited:
- Not a full microservice code-path miner on this corpus — [Implemented] as non-goal
- Not fleet-wide counterfactual proof — [Implemented] as non-goal; continuous causal memory [Aspirational] (B5)
- Cyclic / pod-identity worlds under-tested here — [Aspirational] as future corpus

---

## 10) Lean vs Federated learning frame

- Lean: default for classic infra when repro + audit + cost dominate.
- Federated: optional when deeper micro/path/causal depth is worth ingest + orchestration cost.

Both can be right by workload; total cost = **ingestion + RCA + ops**.

Ingestion cost comparison plan: [`RCA-learning-cheatsheet.md`](./RCA-learning-cheatsheet.md) §3.

---

## 11) Verification checklist (hands-on)

Read:
- `docs/ADR-001-lean-primary-engine.md`
- `lean-pipeline/docs/ARCHITECTURE.md`
- `lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md`
- `benchmarking/results/comparison/COMPARISON.md`

Inspect:
- `benchmarking/results/lean/*/run-bakeoff-phase-b-002/verdict.json`

Confirm:
1. Which UCs have `fallback_fired` / Tier 2–3?
2. Does UC-5 keep app root with healthy infra?
3. Does UC-3b prefer datastore over early switch?

---

## 12) Personal learning checkpoint

Before claiming something about lean, mark it:
- [Implemented] — point to code or `verdict.json`
- [Simulated] — depends on frozen bundles / adapters
- [Aspirational] — production-scale ingest or B5-style future
- [Corrected] — was a coach oversimplification I already fixed above

Raw coach transcript that prompted these corrections lived in an earlier draft of this file (lines after the study sections); treat that transcript as **untrusted** unless tagged.
