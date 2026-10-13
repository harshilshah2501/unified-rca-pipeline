# Map Vortex Graph Architecture Decision Record

**Status:** Milestone B **conditionally closed** ([Report 21](./21-action6-milestone-b-close.md)) — segmented CSR+CSC is a locality-conditional candidate, **not** a Motadata-wide production lock.

This Markdown companion mirrors and clarifies
[`Map_Vortex_Graph_Architecture_Decision_Record.docx`](./Map_Vortex_Graph_Architecture_Decision_Record.docx)
after soft-spot follow-ups aligned with Design v3 evidence.

**Milestone A (frozen):** conventional hot-index baseline = **`csr_csc`** under approved envelope — [Report 17](./17-milestone-a-close.md). Do not reopen `hash` / `hash_bi` / `csr_csc` selection here.

**Measured conventional baseline:** [Report 17](./17-milestone-a-close.md) · [14](./14-action3-final-compare.md)–[16](./16-action5-concurrency.md); earlier screen [`10-design-v3-comprehensive.md`](./10-design-v3-comprehensive.md).

**Action 6 program:** [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md).

---

## Executive summary

Discussion converged on an **incrementally reconstructed, bidirectional, segmented** graph index backed by Vortex cold storage: mutations accumulate under a **bounded-staleness** contract; affected **node-group segments** rebuild with copy-on-write and publish as an **atomic snapshot**; queries **pin** one snapshot; old segments reclaim after readers release them (with query lifetime limits).

This is a **design hypothesis**. Stages 4.0–4.2 screened conventional `hash`, `hash_bi`, `csr`, `csr_csc`, and `hybrid` — **not** segmented CSR+CSC. No bench yet establishes the proposed design as fastest or cheapest.

## Decision register

| Topic | Decision / rationale |
| ----- | -------------------- |
| Mutation pattern | Assume relatively infrequent topology mutations; validate with production traces later. |
| Mutation economics | Prefer complete lifecycle cost, not insertion microbenchmark alone. |
| Visibility | Bounded staleness; actual budget still undecided. |
| Update method | Incremental reconstruction rather than full rebuild or always-queryable overlay. |
| Partitioning | Adaptive node-group segments, constrained by edge/memory budgets. |
| Publication | Atomic graph-wide snapshot publication for cross-group changes. |
| Reader retention | Reference counting plus maximum query lifetime. |
| Durability | **Open:** durable acceptance, journal/replay, recovery semantics. |

## Evidence boundaries

| Stage | Evidence / next action |
| ----- | ---------------------- |
| 4.0–4.2 (done) | Synthetic estates, property gates, fair read-oriented layout screen ≤5M. **No architecture lock.** |
| Existing baselines | `hash_bi`, conventional `csr_csc`, `hybrid` (hybrid zero-churn ≠ mutation proof). |
| Evidence hygiene | Stage 4.2 recorded **no** `correctness_ok=false` cells. Degree bins = out-degree percentiles among sources with edges (**p10/p50/p90**; reverse-heavy also **max-hub**). Re-check natural-order only if a future run fails checksum vs hash. |
| Later mutation study | Benchmark **`segmented_csr_csc`** as a **distinct** candidate vs `hash_bi`, conventional `csr_csc`, hybrid. |
| Lifecycle study | Mutation-to-visibility, incremental rebuild, atomic publish, retention, persistence, replay, compaction/recovery. |
| Production validation | Real distributions, traces, mutation rates, explicit SLOs. |

## Soft-spot follow-ups (closed in this pass)

1. **Report 10 link** — measured conventional-layout envelope is Report 10, not this ADR’s segmented proposal.
2. **Degree-bin definition** — pinned above; do not redefine per layout.
3. **Natural-order “anomalies”** — narrowed: Stage 4.2 has no correctness failures; investigate only on future checksum fail.

## Still open (correctly unresolved)

- Bounded-staleness budget (1 / 10 / 60 s are **sensitivity candidates only**, not SLOs).
- Durability / replay / recovery contract.
- Partition thresholds and hub isolation rules.
- Query timeout / cancellation semantics under memory pressure.
- Economics of **segmented_csr_csc** itself.

## Final status

Architectural discussion: complete for the **lab hypothesis** under the approved synthetic mutation envelope ([Report 21](./21-action6-milestone-b-close.md)). Milestone A selected conventional **`csr_csc`** as the serve baseline. Action 6 measured adaptive node-group segmented bidirectional adjacency with incremental reconstruction, atomic publication, and snapshot-pinned queries. **Outcome:** segmented CSR+CSC is a **conditional** candidate for localized mutations — not a Motadata-wide winning architecture, and not validated against measured production churn.
