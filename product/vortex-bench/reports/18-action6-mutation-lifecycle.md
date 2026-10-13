# Report 18 — Action 6: mutation lifecycle (Milestone B) — first ladder

**Milestone A is frozen.** This report does not reopen `hash` / `hash_bi` / `csr_csc` selection.

**Central question:** Can **segmented CSR+CSC** preserve conventional CSR+CSC query advantages while reducing \(T_{\mathrm{mutation\text{-}visible}}\) vs full rebuild?

**Status:** Superseded by later Action 6 reports; first 1M hubby ladder complete. Final decision: [Report 21](./21-action6-milestone-b-close.md).

Source: `map-vortex-bench/out/design-v3/action6` — 5 cells.

## Timings kept separate

| Symbol | Measured here |
| ------ | ------------- |
| \(T_{\mathrm{cold\text{-}ready}}\) | Initial conventional vs segmented build |
| \(T_{\mathrm{mutation\text{-}visible}}\) | Per-batch rebuild + publish |
| \(T_{\mathrm{query}}\) | Forward/reverse hops=2 on pinned segmented snapshot after each batch |

## Per-cell summary

| Cell | Segs | Batch (ins/del) | T_cold conv | T_cold seg | Conv T_mut p50 | Seg T_mut p50 | Mean segs rebuilt |
| ---- | ---: | --------------- | ----------: | ---------: | -------------: | ------------: | ----------------: |
| 1M-hubby-seg16 | 16 | 1000/200 | 580.61 | 519.68 | 741.18 | 796.83 | **16.0 (all)** |
| 1M-hubby-seg64 | 64 | 1000/200 | 581.76 | 845.67 | 740.22 | 1060.31 | **64.0 (all)** |
| 1M-hubby-seg256 | 256 | 1000/200 | 2286.43 | 3304.64 | 820.06 | 2204.33 | **256.0 (all)** |
| 1M-hubby-seg64-smallbatch | 64 | **10/2** | 650.57 | 824.48 | 627.05 | **355.86** | ~20.3 |
| 1M-hubby-seg256-smallbatch | 256 | **10/2** | 615.76 | 2077.58 | 592.56 | **275.08** | ~22.6 |

## Findings

1. **Large mutation batches that touch every segment lose.** With 1000 inserts + 200 deletes on 1M hubby, every segment is rebuilt; segmented \(T_{\mathrm{mutation\text{-}visible}}\) is **worse** than conventional full rebuild (extra publish/clone overhead, no skipped work).

2. **Small batches that touch a subset win.** With 10 inserts + 2 deletes, ~20–23 of 64/256 segments rebuild; segmented p50 visibility is roughly **1.8–2.2× faster** than conventional full rebuild (356 vs 627 ms at 64 segs; 275 vs 593 ms at 256 segs).

3. **\(T_{\mathrm{cold\text{-}ready}}\) for segmented is not free.** Higher segment counts cost more initial build (256 segs: ~3.3 s vs ~0.6–2.3 s conventional depending on cell). Cold path remains a separate constraint from mutation path.

4. **Pinned \(T_{\mathrm{query}}\) on segmented snapshots stays in the sub-ms–few-ms class** for hops=2 samples in these cells (forward ~0.8–1.6 ms, reverse ~0.02 ms on the seed CI) — not a full Action 5 concurrency re-proof, but no immediate collapse.

5. **v0 implementation limits:** segments rebuild by rescanning the authoritative edge list filtered by segment membership (not yet per-segment edge journals). Overlapping readers during rebuild+publish and crash/durability are **not** measured yet.

## Gate call (partial)

| Question | Answer so far |
| -------- | ------------- |
| Can segmented reduce \(T_{\mathrm{mutation\text{-}visible}}\)? | **Yes, when mutation batches touch a minority of segments** |
| Does large-batch churn help segmented? | **No — converges to (or loses to) full rebuild** |
| Is segmented ready to replace conventional `csr_csc` in production? | **Not yet** — need Motadata-realistic mutation sizes, overlap under pinned readers, durability/replay, and memory amplification during publish |

**Implication for architecture:** Milestone B remains conditional on **mutation locality**. If Motadata topology churn is fine-grained (few endpoints per publish window), segmented CSR+CSC is promising. If publishes routinely rewrite large fractions of the estate, conventional full rebuild may remain simpler and faster.

## Later closed (Action 6 residual)

Priorities 1–5 and consolidated close: Reports [19](./19-action6-atomic-publish.md)–[21](./21-action6-milestone-b-close.md); mutation envelope [`../design-v3/action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md).

## Links

- Spec: [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md)  
- Milestone A freeze: [Report 17](./17-milestone-a-close.md)  
- Final close: [Report 21](./21-action6-milestone-b-close.md)  
- ADR: [`Map_Vortex_Graph_Architecture_Decision_Record.md`](./Map_Vortex_Graph_Architecture_Decision_Record.md)
