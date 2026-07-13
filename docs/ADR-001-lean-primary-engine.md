# ADR-001: Lean as the Primary ObserveOps RCA Engine

## Status

Accepted (2026-07-13)

## Context

Motadata ObserveOps is evaluated only against the frozen UC-1..UC-5 corpus
derived from [`rca-use-cases-only.md`](./rca-use-cases-only.md) in
`datasets/observeops/`. That corpus enforces **Roadblock 4** by convention
(shared `ground_truth.json` + same-bundle bakeoff) and **Roadblock 1b** as a
joined typed multi-domain CI graph. The matched bakeoffs `bakeoff-phase-a-001`
and `bakeoff-phase-b-001` established the engine decision and lean's PRD depth.

## Decision

Use the **lean engine** as the primary RCA engine for classic ObserveOps
infrastructure paths (network → host → VM → OS → app).

Keep the federated engine as an optional future hybrid component for
microservice code-path, gray-failure, and pair-mining workloads, once a
dedicated microservice evaluation corpus is in scope.

## Consequences

Phase D packaging is complete: lean CLI/HTTP API (`lean_rca`), SRE report
fields (chain / blast radius / remediation), and systemd unit
`lean-rca.service`. Defer Phase C federated production ingest/stores and
Phase E scale/capacity work until a microservice evaluation track is
prioritized. Optional later: B5 continuous causal memory.

| Evidence axis | `bakeoff-phase-b-001` result | Decision impact |
|---|---|---|
| Accuracy | Both engines: 5/5 root-CI and 5/5 signature matches | No accuracy penalty for lean |
| Reproducibility | Lean: 100% (5/5); federated: 40% | Lean is operationally more repeatable |
| Evidence tiers | Lean: Tier 3 causal verification on UC-1 and UC-3; Tier 1 on UC-2, UC-4, and UC-5 | Lean supports the required evidence-depth range |
| Efficiency | Lean: 5.00 average observations vs federated 5.40; best-first 2.40 vs naive BFS 2.80 | Lean is lighter on the evaluated paths |

Evidence: [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md)
and [`DECISION.md`](../benchmarking/results/comparison/DECISION.md).

Related: [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) ([`.pdf`](./Lean_RCA_PRD.pdf)) · [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md) ([`.pdf`](./Lean_RCA_Simple_Guide.pdf)).

Cost–benefit and “what to choose when”: see [Lean vs federated — design choice & decision guide](./README.md#lean-vs-federated--design-choice--decision-guide) in [`README.md`](./README.md).
