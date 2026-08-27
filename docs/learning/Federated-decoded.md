> **Study notes — not a scoreboard.** Canonical numbers: `benchmarking/results/comparison/` and `docs/`.

Federated RCA Study v2 (Repo-Aligned)

Purpose: Correct my learning notes by separating what is implemented in this repo versus what is conceptual from papers or future architecture.

**Doc map:** [`docs/NAVIGATION.md`](../NAVIGATION.md)

Tag legend:
- [Implemented] Present and used in current repo flows.
- [Simulated] Present in PoC/eval adapters, not full live production ingestion.
- [Aspirational] Architecture vision or paper-level capability not fully realized here.

## 1) What Federated Means in This Repo

- Federated stack = Panorama -> Murphy -> Nezha orchestrated flow for comparison and optional hybrid path.
- For ObserveOps UC corpus, federated is not the default shipping path.
- Current decision posture: lean is primary evaluation engine on this corpus; not a finalized product commitment.

Status tags:
- Federated as comparator for ObserveOps bakeoff: [Implemented]
- Federated as always-on production default brain for ObserveOps: [Not true here]
- Federated as optional hybrid track for microservice/code-path future scope: [Aspirational]

## 2) Data Substrates and Tiers

My earlier note overstated live tier operations. Correct view:

- Speed tier style data structures for high-velocity event-like signals: [Simulated]
- Structural/topology graph usage for dependency reasoning: [Implemented]
- Dual-tier large-scale storage vision (throughput-heavy speed tier + structural persistence): [Aspirational]

Important nuance:
- In ObserveOps eval runs, adapters and bundled corpus artifacts stand in for full fleet telemetry ingestion.
- Treat "1B EPS" type claims as capacity vision context, not a guaranteed end-to-end deployed behavior in this repo.

## 3) Algorithm Pillars: Confidence Level by Reality

### Panorama
- Role: symptom/anomaly trigger style detection and observer-inspired logic.
- In repo context: used in federated narrative and PoC flow, often adapterized.
- Tag: [Simulated]/[Implemented-lite]

### Murphy
- Role: macro causal/statistical localization on graph-structured dependencies.
- In repo context: central federated macro reasoning component.
- Tag: [Implemented]

### Nezha
- Role: fine-grained event/trace drift style micro-localization.
- In repo context: available in federated pipeline, but ObserveOps classic-infra corpus does not always require full microservice-style path mining.
- Tag: [Implemented], with many paper-strength behaviors still [Aspirational] in this specific corpus.

## 4) Orchestrator Timeline (Corrected)

High-level sequence (teaching model):
1. Trigger/symptom intake
2. Build suspect context (topology slice + anomaly context)
3. Murphy macro ranking/gating
4. Optional Nezha micro step (if gate/conditions justify)
5. Fusion/resolve/fallback -> verdict

What to avoid in my interpretation:
- Do not assume every incident always runs full Panorama+Murphy+Nezha path.
- Do not assume fixed global thresholds from chat examples are canonical unless verified in code/config.

Timeline confidence:
- Stage orchestration and gating/fallback: [Implemented]
- Hard-coded universal thresholds exactly as chat examples: [Needs verification]

## 5) Schema Reality Check

My earlier note invented overly rigid universal fields (example `confidence_score` semantics and strict tier meaning).

Correct approach:
- Use actual output artifacts (`verdict.json`, comparison outputs) as source of truth.
- Treat chat-proposed payload names (`DetectionFlag`, `MurphyRequest`, `NezhaRequest`) as conceptual unless directly mapped in code.

Tag:
- Cross-engine verdict + comparison artifacts in benchmark results: [Implemented]
- One universal strict schema exactly matching my earlier pseudo-JSON: [Aspirational/teaching shorthand]

## 6) Causal Validity Claim Discipline

I previously wrote this like full counterfactual certainty is always available.
Corrected:
- Murphy contributes stronger causal-style reasoning than pure temporal heuristics.
- But in this repo/docs, structural counterfactual strength is treated as partial/expensive context-dependent benefit.
- For ObserveOps corpus decision, that strength did not translate to better top-1 accuracy versus lean on the canonical bakeoff.

Tag:
- "Murphy has causal edge in principle": [Implemented intent + paper alignment]
- "Global always-on counterfactual proof at fleet scale in this repo": [Aspirational]

## 7) ObserveOps-Specific Ground Truth to Remember

- Canonical ObserveOps scoreboard run: `adr001-rerun-20260723` (ADR-era snapshot: `bakeoff-phase-b-002`).
- Corpus version: v1.1.0 with UC-3b and events extension.
- Federated and lean both hit strong accuracy on core UC set; other axes drive the decision posture.

Tag:
- Canonical scoreboard and corpus contract: [Implemented]

## 8) What I Now Understand (Self-Check)

I can now explain:
- Why federated is valuable but not default for this corpus.
- Why adapterized/simulated data flow matters when interpreting claims.
- Why I must separate "paper capability" from "repo-verified behavior."
- Why verdict language is corpus-scoped and not a finalized product commitment.

## 9) Open Questions for Next Learning Session

1. Where exactly in code are Murphy gate conditions configured?
2. Which parts of Nezha output are actively used in final resolver for ObserveOps UC runs?
3. What are the precise verdict field contracts consumed by `compare.py`?
4. Which federated steps are bypassed on specific UCs and why?
5. What minimal additional corpus would best test federated strengths fairly (microservice/code-path)?

## 10) Fast Verification Checklist (Hands-on)

- Read:
  - `benchmarking/results/comparison/COMPARISON.md`
  - `benchmarking/results/comparison/DECISION.md`
  - `federated-pipeline/docs/ARCHITECTURE.md`
  - `federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md`
- Inspect:
  - Sample federated `verdict.json` artifacts under `benchmarking/results/federated/`
- Confirm:
  - Which fields are truly emitted vs assumed.

---

Note to self: when learning via LLM explanations, always annotate statements with [Implemented], [Simulated], or [Aspirational] immediately to prevent mixing design vision with verified system behavior.

## 11) Comprehensive Clarification: Ingestion Pipeline vs RCA Pipeline (Federated)

This is the most important system boundary for this PoC.

### A) Ingestion pipeline (data-plane plumbing)

What ingestion does:
- Collect telemetry (metrics, events/logs/traces, topology updates).
- Normalize schemas and timestamps.
- Maintain hot/cold data windows.
- Materialize/queryable stores (speed-tier style event substrate + structural graph substrate).
- Handle reliability concerns (late data, missing data, retries, backpressure, TTL).

Federated ingestion posture in this repo:
- ObserveOps bakeoff does not depend on full live production ingest.
- Adapters plus frozen corpus bundles stand in for live fleet streams.
- Some ingest/storage pieces exist as stubs/PoC approximations; full production flow remains deferred.

Tag summary:
- Full live federated ingest for ObserveOps production: [Aspirational]
- Adapterized corpus-based ingest for fair engine comparison: [Implemented]/[Simulated]

### B) RCA pipeline (reasoning-plane logic)

What RCA does:
- Start from symptom/anomaly context.
- Build candidate dependency context.
- Score/rank suspects (Murphy macro).
- Optionally refine with micro signal/drift (Nezha step, when justified).
- Fuse evidence and resolve a root CI/verdict with rationale fields.

Federated RCA posture in this repo:
- This is what the benchmark is actively comparing against lean on the same frozen bundles.
- The main question answered by the PoC is engine behavior on a fixed corpus, not ingest maturity.

Tag summary:
- Federated RCA logic path for benchmark/comparison: [Implemented]
- Universal always-on full-depth federated flow for every incident: [Not guaranteed here]

### C) Why this separation matters for cost

Even if RCA math is correct, ingestion can dominate real-world cost and risk:
- Engineering cost: connectors, schema evolution, topology identity joins.
- Ops cost: storage tier tuning, retention policy, queue fanout, observability.
- Reliability cost: replay/idempotency, out-of-order windows, partial outages.
- Governance cost: access control, PII handling, tenant isolation.

Therefore:
- "Engine wins on frozen corpus" does not automatically mean "lowest total cost to operate live."
- For this ObserveOps PoC, ingest complexity was intentionally reduced so engine comparison is fair.

### D) Practical read of the current repo decision

- Lean was favored as the primary evaluation engine on this corpus partly because it provides strong reproducibility/verifiability with lower default complexity burden.
- Federated remains valuable where deeper microservice/code-path/correlation behavior is worth extra ingestion + orchestration overhead.
- This is corpus-scoped and evaluation-scoped, not a final product/GTM lock.

### E) Personal learning checkpoint

When I describe federated behavior in future notes, I should always specify:
1. What is assumed from ingestion (live vs bundled)?
2. Which tier/data substrate is real vs simulated in the run?
3. Whether the claim is benchmark-proven here or paper-level capability.

--------------------------------------------
