# Report 21a — Action 6 priority 5: 5M thin ladder

**Envelope:** approved [`../design-v3/action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md).
Milestone A remains frozen. Consolidated decision: [Report 21](./21-action6-milestone-b-close.md).

Source: `/root/Harshil-PoCs/Unified-RCA/product/vortex-bench/map-vortex-bench/out/design-v3/action6-5m` — 3 cells.

| Cell | Segs | Ins/Del | T_cold conv | T_cold seg | Conv T_mut p50 | Seg T_mut p50 | Mean segs rebuilt | Seg/Conv ratio |
| ---- | ---: | ------- | ----------: | ---------: | -------------: | ------------: | ----------------: | -------------: |
| 5M-hubby-seg256-i10-d2 | 256 | 10/2 | 4805.85 | 12207.10 | 4390.07 | 1679.39 | 22.6 | 0.38 |
| 5M-hubby-seg64-i10-d2 | 64 | 10/2 | 4955.07 | 5718.36 | 4480.21 | 1838.51 | 20.6 | 0.41 |
| 5M-hubby-seg64-i1000-d200 | 64 | 1000/200 | 6547.84 | 6176.03 | 6813.16 | 6930.99 | 64.0 | 1.02 |

## Gate notes

Ratio < 1.0 means segmented mutation visibility is faster than conventional full rebuild.

**Priority 5 call:** Under approved `mut_localized`, 5M hubby shows segmented T_mut p50 at **~0.38–0.41×** conventional (win). Under `mut_medium` (1000/200, all 64 segments), ratio **~1.02** (no win). Matches Report 18 locality pattern at larger scale.

**Status:** Priority 5 **PASSED** for the thin ladder. Consolidated decision: [Report 21](./21-action6-milestone-b-close.md).

## Links

- Envelope: [`../design-v3/action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md)
- Prior: [Report 18](./18-action6-mutation-lifecycle.md)

