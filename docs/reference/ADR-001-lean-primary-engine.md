# ADR-001: Lean vs Federated on the ObserveOps Corpus

## Status

**Evaluation finding** (2026-07-16; measurement refreshed 2026-07-23) — bakeoff recommendation for the classical ObserveOps UC corpus. **Current scoreboard cite:** `adr001-rerun-20260723` ([`COMPARISON.md`](../../benchmarking/results/comparison/COMPARISON.md)). **ADR-era decision evidence:** `bakeoff-phase-b-002` (corpus v1.1.0). **Lean is the primary evaluation engine on this corpus; not a finalized product or GTM commitment.**

## Context

This workspace evaluates two RCA approaches against the frozen UC-1..UC-5 corpus
derived from [`rca-use-cases-only.md`](../rca-use-cases-only.md) in
`datasets/observeops/`. That corpus enforces **Roadblock 4** by convention
(shared `ground_truth.json` + same-bundle bakeoff) and **Roadblock 1b** as a
joined typed multi-domain CI graph. The matched bakeoffs `bakeoff-phase-a-001`
and `bakeoff-phase-b-001` / **`bakeoff-phase-b-002`** established the ADR decision;
current measurement continues on **`adr001-rerun-20260723`** (parity shared-detect)
for accuracy, reproducibility, evidence depth, and efficiency.

## Evaluation recommendation (corpus-scoped)

On **classic infrastructure** paths in this corpus (network → host → VM → OS → app),
bakeoff evidence **favors the lean engine** as the stronger default for further
evaluation (reproducibility, verifiability, cost).

Keep the **federated** engine in scope as a comparator and as a candidate for
microservice / code-path / gray-failure / pair-mining workloads once a dedicated
microservice evaluation corpus is defined.

Nothing here freezes a go-to-market or shipping decision.

## Consequences (evaluation)

Packaging artifacts exist so the lean path can be exercised end-to-end
(`lean_rca` CLI/HTTP, SRE report fields, `lean-rca.service`). Federated **Later · Federate**
ingest/stores and **Later · Scale** work stay deferred until a microservice track
(or renewed bakeoff criteria) is prioritized. Optional later: B5 continuous
causal memory.

| Evidence axis | `bakeoff-phase-b-002` result | Evaluation impact |
|---|---|---|
| Accuracy | Both engines: 5/5 root-CI and 5/5 signature matches | No accuracy penalty for lean on this corpus |
| Reproducibility | Lean: 100% (5/5); federated: 40% | Lean is more repeatable on these bundles |
| Evidence tiers | Lean: Tier 3 on UC-1 and UC-3; Tier 1 on UC-2, UC-4, and UC-5 | Lean covers the intended depth range |
| Efficiency | Lean: 5.00 avg observations vs federated 5.60; best-first 2.40 vs naive BFS 2.80 | Lean is lighter on the evaluated paths |
| Verifiability | Federated: 100% main-path; lean: 60% main-path with explicit tier/CARE/causal audit trail | Lean favored for SRE audit narrative despite lower main-path % |

Evidence: [`COMPARISON.md`](../../benchmarking/results/comparison/COMPARISON.md)
and [`DECISION.md`](../../benchmarking/results/comparison/DECISION.md).

**Rerun (2026-07-23):** matched run `adr001-rerun-20260723` — both engines still **5/5** root+signature; overall better: lean. Per-UC comprehensive reports (no OO gold): [`comparison/reports/`](../../benchmarking/results/comparison/reports/README.md).

Related: [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) ([`.pdf`](./Lean_RCA_PRD.pdf)) · [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md) ([`.pdf`](./Lean_RCA_Simple_Guide.pdf)).

Cost–benefit and “what to choose when”: see [Lean vs federated — design choice & decision guide](../README.md#lean-vs-federated--design-choice--decision-guide) in [`docs/README.md`](../README.md).
