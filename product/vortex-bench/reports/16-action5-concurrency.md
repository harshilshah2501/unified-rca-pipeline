# Report 16 — Action 5: concurrency and memory

**Envelope:** approved `motadata_like_hubby` + `scope_policy_mixed`.
Shared-graph concurrent trace replay; dual-index hold on 1M × readers=1 cells.

Source: `/root/Harshil-PoCs/Unified-RCA/product/vortex-bench/map-vortex-bench/out/design-v3/action5` — 15 scenario rows.

## Per-cell concurrency

| Cell | Layout | Readers | QPS | Lat p50 | Lat p95 | Lat p99 | Peak RSS | Dual-hold RSS | Steady idx | OK |
| ---- | ------ | ------: | --: | ------: | ------: | ------: | -------: | ------------: | ---------: | -- |
| 1M-hubby-r1-csr-csc | csr_csc | 1 | 24138.2 | 0.003 | 0.178 | 0.201 | 607358976 | 607965184 | 96455904 | True |
| 1M-hubby-r1-hash | hash | 1 | 50.7 | 0.020 | 111.839 | 115.045 | 618680320 | 618143744 | 111558069 | True |
| 1M-hubby-r1-hash-bi | hash_bi | 1 | 13419.8 | 0.005 | 0.347 | 0.550 | 904892416 | 904892416 | 209592388 | True |
| 1M-hubby-r16-csr-csc | csr_csc | 16 | 75150.1 | 0.005 | 0.371 | 0.494 | 377159680 | None | 96455904 | True |
| 1M-hubby-r16-hash | hash | 16 | 152.3 | 0.039 | 603.874 | 681.221 | 366395392 | None | 111558069 | True |
| 1M-hubby-r16-hash-bi | hash_bi | 16 | 41932.5 | 0.007 | 0.648 | 4.638 | 468881408 | None | 209592388 | True |
| 1M-hubby-r4-csr-csc | csr_csc | 4 | 54382.9 | 0.004 | 0.342 | 0.404 | 360873984 | None | 96455904 | True |
| 1M-hubby-r4-hash | hash | 4 | 96.2 | 0.034 | 230.519 | 281.187 | 352829440 | None | 111558069 | True |
| 1M-hubby-r4-hash-bi | hash_bi | 4 | 31457.6 | 0.007 | 0.621 | 0.869 | 476405760 | None | 209592388 | True |
| 5M-hubby-r1-csr-csc | csr_csc | 1 | 5924.6 | 0.006 | 0.916 | 1.312 | 1764487168 | None | 509861254 | True |
| 5M-hubby-r1-hash | hash | 1 | 8.9 | 0.028 | 716.929 | 747.147 | 1626603520 | None | 584911429 | True |
| 5M-hubby-r1-hash-bi | hash_bi | 1 | 3354.3 | 0.008 | 1.889 | 2.607 | 2368774144 | None | 1075337790 | True |
| 5M-hubby-r16-csr-csc | csr_csc | 16 | 18919.6 | 0.008 | 2.091 | 12.209 | 1765838848 | None | 509861254 | True |
| 5M-hubby-r16-hash | hash | 16 | 28.7 | 0.049 | 3370.302 | 4048.282 | 1531158528 | None | 584911429 | True |
| 5M-hubby-r16-hash-bi | hash_bi | 16 | 15358.8 | 0.009 | 3.055 | 14.029 | 2361217024 | None | 1075337790 | True |

## Rankings (highest QPS, then lowest p95)

### 1M × 1 readers

1. `csr_csc` — qps=24138.2 p95=0.178 p99=0.201 rss=607358976 dual=607965184
2. `hash_bi` — qps=13419.8 p95=0.347 p99=0.550 rss=904892416 dual=904892416
3. `hash` — qps=50.7 p95=111.839 p99=115.045 rss=618680320 dual=618143744

### 1M × 4 readers

1. `csr_csc` — qps=54382.9 p95=0.342 p99=0.404 rss=360873984 dual=None
2. `hash_bi` — qps=31457.6 p95=0.621 p99=0.869 rss=476405760 dual=None
3. `hash` — qps=96.2 p95=230.519 p99=281.187 rss=352829440 dual=None

### 1M × 16 readers

1. `csr_csc` — qps=75150.1 p95=0.371 p99=0.494 rss=377159680 dual=None
2. `hash_bi` — qps=41932.5 p95=0.648 p99=4.638 rss=468881408 dual=None
3. `hash` — qps=152.3 p95=603.874 p99=681.221 rss=366395392 dual=None

### 5M × 1 readers

1. `csr_csc` — qps=5924.6 p95=0.916 p99=1.312 rss=1764487168 dual=None
2. `hash_bi` — qps=3354.3 p95=1.889 p99=2.607 rss=2368774144 dual=None
3. `hash` — qps=8.9 p95=716.929 p99=747.147 rss=1626603520 dual=None

### 5M × 16 readers

1. `csr_csc` — qps=18919.6 p95=2.091 p99=12.209 rss=1765838848 dual=None
2. `hash_bi` — qps=15358.8 p95=3.055 p99=14.029 rss=2361217024 dual=None
3. `hash` — qps=28.7 p95=3370.302 p99=4048.282 rss=1531158528 dual=None

## Gate call

Action 5 checks whether the Action 3 provisional winner (`csr_csc`) retains advantage under concurrent Scope-like replays and dual-index memory pressure. All **15/15** cells `correctness_ok=true`.

### Constraint-based concurrency finding

| Constraint | Winner | Evidence |
| ---------- | ------ | -------- |
| Concurrent QPS / p95 / p99 under envelope mix | **`csr_csc`** | 1M×16: ~75k qps, p95 0.37 ms; 5M×16: ~19k qps, p95 2.1 ms |
| Runner-up | `hash_bi` | Competitive tails; lower QPS; ~2× steady index |
| Concurrent reverse tails | **`hash` fails** | 1M×16 p95 ~604 ms; 5M×16 p95 ~3370 ms |
| Dual-index hold (1M) | All feasible | Peak RSS rises vs single-index steady cells; `hash_bi` highest (~0.9 GB process) |

**Implication:** Under concurrent Scope-like load, **`csr_csc` retains and widens** its Action 3 advantage. `hash` is not viable for the approved reverse share. Dual-hold does not flip the ranking.

**Status:** Action 5 **PASSED** (2026-10-13).

## Links

- Matrix: [`../design-v3/action4-5-run-matrix.md`](../design-v3/action4-5-run-matrix.md)
- Prior: [Report 15](./15-action4-cold-recovery.md)

