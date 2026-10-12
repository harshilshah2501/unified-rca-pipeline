# Map Vortex Graph Architecture Decision Record

**Status:** discussion synthesis — proposed architecture, **not** a production-approved implementation.

This Markdown companion mirrors and clarifies
[`Map_Vortex_Graph_Architecture_Decision_Record.docx`](./Map_Vortex_Graph_Architecture_Decision_Record.docx)
after soft-spot follow-ups aligned with Design v3 evidence.

**Measured baseline (read screen):** [`10-design-v3-comprehensive.md`](./10-design-v3-comprehensive.md) · stage reports [07](./07-design-v3-stage3_5-fair.md)–[09](./09-design-v3-stage4_2-screen.md).

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

Architectural discussion: substantially complete for the **hypothesis**. Chosen direction to **test next:** adaptive node-group segmented bidirectional adjacency with incremental copy-on-write reconstruction, atomic publication, snapshot-pinned queries, and bounded reader lifetimes. **Do not** present this as the winning architecture until the distinct segmented candidate is measured on lifecycle metrics against the Design v3 baselines.
