# Report 17 — Milestone A close: conventional hot-index selection

**Status:** **FROZEN** (2026-10-13) — do not reopen `hash` / `hash_bi` / `csr_csc` unless production evidence contradicts the approved operating envelope.  
**Date:** 2026-10-13  
**Envelope:** approved Action 2 `motadata_like_hubby` + `scope_policy_mixed` (70/20/10, hops=2).  
**Candidates frozen:** `hash` · `hash_bi` · `csr_csc`.  
**Not in scope:** segmented CSR+CSC / mutation lifecycle (Milestone B / Action 6).

**Architectural distinction locked here:** the fastest graph to **reconstruct** (`hash`) is not the fastest graph to **serve** under the approved mix (`csr_csc`).

## Actions 1–5 status

| Action | Status | Key outcome |
| ------ | ------ | ----------- |
| 1 Correctness oracle | PASSED | Fixed sort-aware natural-order edge loss; all candidates green ([Report 12](./12-action1-correctness-oracle.md)) |
| 2 Operating envelope | PASSED | Waiver-approved synthetic hubby + Scope mix ([Report 13](./13-action2-operating-envelope.md)) |
| 3 Final layout compare | PASSED | Query + retained-index winner **`csr_csc`** ([Report 14](./14-action3-final-compare.md)) |
| 4 Cold-to-hot recovery | PASSED | T_ready winner **`hash`** on all lab coldness tiers ([Report 15](./15-action4-cold-recovery.md)) |
| 5 Concurrency + memory | PASSED | Concurrent QPS/tails winner **`csr_csc`**; `hash` reverse collapses ([Report 16](./16-action5-concurrency.md)) |

## Constraint-based decision (envelope-conditional)

| Primary product constraint | Preferred layout |
| -------------------------- | ---------------- |
| Steady-state Scope walks (mixed forward/reverse) + retained index size | **`csr_csc`** |
| Concurrent Scope-like readers | **`csr_csc`** |
| Fastest cold→query-ready reconstruction | **`hash`** |
| Mutable hash semantics with reverse index | `hash_bi` (latency OK; ~2× index bytes) |

**Milestone A recommendation for the approved synthetic workload:** adopt **`csr_csc` as the conventional hot-index baseline** for read/query and concurrency, accepting slower rebuild / T_ready than `hash`.

Do **not** treat this as:

- a Motadata production lock without real Dest remote-cold and measured Scope traffic, or  
- proof that segmented CSR+CSC with incremental reconstruction is the production architecture (Action 6 / Milestone B).

## Qualifications carried forward

1. Action 3 latency ranks used one identical trace replay per cell (build N≥10–20); Action 5 adds concurrent multi-reader evidence but not independent multi-trace Monte Carlo.  
2. `remote_proxy` ≠ Motadata Dest S3 remote-cold.  
3. Dual-index hold is a coarse RSS observation, not a full atomic-publish simulator.

## Next

- **Milestone B / Action 6** — **CLOSED** ([Report 21](./21-action6-milestone-b-close.md)): segmented CSR+CSC retained as a conditional candidate for localized mutations; conventional `csr_csc` remains serve baseline.  
- Optional: true Dest remote-cold measurement; multi-trace confirmation batches.  
- Preserve Action 1–5 outputs under `map-vortex-bench/out/design-v3/action{1,3,4,5}` as the **reference baseline**.

## Links

- Program one-stop (cold readers): [Report 22](./22-program-one-stop.md)  
- Program: [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md)  
- Stage‑4.2 eng brief: [`./11-map-vortex-engineering-brief.md`](./11-map-vortex-engineering-brief.md)
