# Report 19 — Action 6 residual: atomic publish + dual-hold memory

**Milestone A remains frozen.** This does not reopen the three-layout selection.

Priorities covered: (1) atomic publication with pinned readers; (2) memory amplification during publication.
Still deferred: durability/replay, Motadata mutation realism, 5M thin ladder.

Source: `/root/Harshil-PoCs/Unified-RCA/product/vortex-bench/map-vortex-bench/out/design-v3/action6-overlap` — 4 cells.

## Results

| Cell | Segs | Ins/Del | Readers | Atomic OK | Overlap OK | Gen mismatch | Sym fail | Reader ops | Single RSS | Max dual-hold RSS | Final RSS |
| ---- | ---: | ------- | ------: | --------- | ---------- | -----------: | -------: | ---------: | ---------: | ----------------: | --------: |
| 1M-seg256-i10-d2-r16 | 256 | 10/2 | 16 | True | True | 0 | 0 | 2242106 | 1073815552 | 1943007232 | 5654224896 |
| 1M-seg256-i10-d2-r8 | 256 | 10/2 | 8 | True | True | 0 | 0 | 1071549 | 1073774592 | 1939013632 | 3761213440 |
| 1M-seg64-i10-d2-r8 | 64 | 10/2 | 8 | True | True | 0 | 0 | 1067314 | 767807488 | 1324654592 | 3078660096 |
| 1M-seg64-i1000-d200-r8 | 64 | 1000/200 | 8 | True | True | 0 | 0 | 1395515 | 767782912 | 1329704960 | 3064057856 |

## Gate call

### Priority 1 — Atomic publication with pinned readers

| Check | Result |
| ----- | ------ |
| Generation stable within a single pin across forward+reverse walks | **0 mismatches** across all cells (~1M–2.2M reader ops) |
| Old pin remains CSR⇔CSC symmetric after publish | **true** on every batch |
| New pin CSR⇔CSC symmetric | **true** on every batch |
| Overlap readers final symmetry sample | **0 failures** |

Readers observe either the complete old snapshot or the complete new snapshot via `Arc` swap — not a mixture of generations. **PASSED** for this lab model.

### Priority 2 — Memory amplification during publication

| Cell | Single-snapshot RSS | Max dual-hold RSS | Approx amplification |
| ---- | ------------------: | ----------------: | -------------------: |
| 64 segs, small batch, 8 readers | ~0.77 GB | ~1.32 GB | ~1.7× |
| 256 segs, small batch, 8–16 readers | ~1.07 GB | ~1.94 GB | ~1.8× |

Dual-hold peak is measured while the pre-publish pin and the newly built snapshot both live. Process `VmHWM` at end-of-run can climb higher under sustained concurrent readers (allocator high-water) — use **dual-hold** as the publication amplification signal, not final RSS alone.

**Bound:** for these 1M cells, publication amplification stays under ~2× retained single-snapshot RSS. Not yet a Motadata production memory SLO.

### Still deferred

3. Failure / durability / replay  
4. Motadata-realistic mutation sizes and locality  
5. 5M thin ladder  

Per-segment edge journals remain a **separate** optimization hypothesis (not measured here).

**Residual status:** priorities **1–2 PASSED** on the 1M overlap ladder. Action 6 overall: [Report 21](./21-action6-milestone-b-close.md).

## Links

- Spec: [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md)
- Prior: [Report 18](./18-action6-mutation-lifecycle.md)
- Final close: [Report 21](./21-action6-milestone-b-close.md)

