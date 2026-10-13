# Stage exit gates

## Stage 0

- [x] SLO worksheet, trace schema, run manifest schema, oracle, factor registry published under `design-v3/`.

## Stage 1

- [x] Reproduce Report 02 / follow-up **2×2** (order × builder) at 500k edges, uniform + hubby, spine, process_cold, N=20.
- [x] Manifests under `map-vortex-bench/out/design-v3/stage1/`.
- [x] Report 04 records main effects + interaction; no confounded natural+naive vs clustered+sort_aware-only comparison.

## Stage 2

- [x] Screening ranks material factors (order, builder×order, shape×query tails, load decode share).
- [x] Report 05 names which interactions deserve Stage 3 depth.
- [x] Per-query JSONL written for screened cells.

## Stage 3

- [x] All four layouts measured at 250k / 500k / 1M × uniform+hubby with correctness_ok.
- [x] Pareto of build_ms × query p95 × peak RSS documented in Report 06.
- [x] Explicit gate call: adopt clustered+sort_aware **hash** vs prototype CSR/CSC vs hybrid — synthetic-only caveat required.

## Stage 3.5 (critical-review remediation)

- [x] Bidirectional hash (`hash_bi`) measured against hash / CSR / CSR+CSC / hybrid.
- [x] Same reverse query mix for **every** layout; reverse algorithm documented per layout.
- [x] Per-class latency (forward / reverse / dependency_chain) in results + Report 07.
- [x] Hybrid occurrence-count delete semantics documented (not edge_id).
- [ ] Disk-cold / remote-cold (deferred — labels clarified only).

## Stage 4.0–4.2 (workload-informed synthetic)

- [x] 4.0 contracts + six estate generators + property validators + query-trace emitter.
- [x] 4.1 property reports for all families at 500k/1M/5M (Report 08).
- [x] 4.2 layout screen ≤5M with identical traces; Report 09 crossover candidates (not production lock). Full factorial at 500k/1M; thin 5M ladder (uniform+hubby × balanced).
- [x] Explicitly deferred: concurrency, mutation economics, 10M+, confirmation batches (4.6).

## Decision-validation sprint (post 4.2) — Milestone A

Program: [`decision-validation-sprint.md`](./decision-validation-sprint.md). Candidates frozen: `hash` · `hash_bi` · `csr_csc`.

- [x] Product success criteria / synthetic operating envelope explicitly approved for Milestone A (`motadata_like_hubby` + `scope_policy_mixed`; intake waiver 2026-10-13).
- [x] Action 1: independent typed-multigraph correctness oracle; all candidates pass (Report 12). Fixed sort_aware natural-order edge drop.
- [x] Action 2: approved synthetic envelope (Report 13; waiver path B — Harshil Shah §6).
- [x] Action 3: final 3-layout comparison with distributions / confidence (1M, 5M) — Report 14; envelope winner **`csr_csc`**.
- [x] Action 4: process-cold / disk-cold / remote-proxy `T_ready` (Report 15; Dest S3 remote-cold still deferred). Recovery winner **`hash`**.
- [x] Action 5: concurrency + peak memory under expected reader load (Report 16). Concurrent winner **`csr_csc`**.
- [x] Milestone A report: constraint-based winner for a **stated** operating envelope — [Report 17](../reports/17-milestone-a-close.md) (`csr_csc` baseline; `hash` wins T_ready only).

## Milestone A — **FROZEN** (2026-10-13)

Reference: [Report 17](../reports/17-milestone-a-close.md). Conventional baseline **`csr_csc`**; recovery reference **`hash`**. Benchmarks under `out/design-v3/action{1,3,4,5}` are the locked baseline.

## Milestone B (production architecture) — Action 6 **CLOSED (conditional)**

- [x] Action 6: mutation lifecycle — **CLOSED** ([Report 21](../reports/21-action6-milestone-b-close.md)): segmented CSR+CSC **conditionally retained** for localized mutations under approved synthetic mutation envelope; conventional `csr_csc` remains serve baseline.
  - [x] Locality ladder (Report 18)
  - [x] Atomic publish + dual-hold RSS (Report 19)
  - [x] Durability / replay — lab model (Report 20)
  - [x] Mutation envelope — synthetic waiver ([`action6-synthetic-mutation-envelope.md`](./action6-synthetic-mutation-envelope.md))
  - [x] 5M thin ladder (Report 21a)
