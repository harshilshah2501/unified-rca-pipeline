# Report 14 — Action 3: final three-layout comparison

**Envelope:** approved Action 2 `motadata_like_hubby` + `scope_policy_mixed` (70% forward / 20% reverse / 10% dependency; hops=2 on the mixed profile). Winners are **envelope-conditional**, not Motadata-wide locks.

Frozen candidates: `hash` · `hash_bi` · `csr_csc`.

Source: `/root/Harshil-PoCs/Unified-RCA/product/vortex-bench/map-vortex-bench/out/design-v3/action3` — 33 scenario rows.

## Coverage

- **1M:** `uniform` + `hubby` × `forward_dominant` / `balanced` / `reverse_heavy` / `scope_policy_mixed` × 3 layouts (clustered; build repeats ≥ 20).
- **1M natural control:** `hubby` × `scope_policy_mixed` × 3 layouts.
- **5M thin ladder:** `uniform` + `hubby` × `scope_policy_mixed` × 3 layouts (build repeats ≥ 10).

## Per-cell metrics

| Cell | Layout | N | Build p50 | Build p95 | Fwd p95 | Rev p95 | Dep p95 | Env score | Peak RSS | Steady idx B | OK |
| ---- | ------ | -: | --------: | --------: | ------: | ------: | ------: | --------: | -------: | -----------: | -- |
| 1M-hubby-clustered-balanced-csr-csc | csr_csc | 20 | 1138.307 | 1234.158 | 0.483 | 0.105 | 0.558 | 0.415 | 375771136 | 96455904 | True |
| 1M-hubby-clustered-balanced-hash | hash | 20 | 399.747 | 449.763 | 1.113 | 882.027 | 1.190 | 177.303 | 382836736 | 111558069 | True |
| 1M-hubby-clustered-balanced-hash-bi | hash_bi | 20 | 871.505 | 998.869 | 0.524 | 0.113 | 0.537 | 0.443 | 511488000 | 209592388 | True |
| 1M-hubby-clustered-forward-dominant-csr-csc | csr_csc | 20 | 1249.447 | 1394.043 | 0.017 | 0.102 | 0.222 | 0.055 | 375742464 | 96455904 | True |
| 1M-hubby-clustered-forward-dominant-hash | hash | 20 | 367.851 | 517.388 | 0.059 | 330.502 | 0.503 | 66.192 | 397156352 | 111558069 | True |
| 1M-hubby-clustered-forward-dominant-hash-bi | hash_bi | 20 | 833.911 | 1023.599 | 0.016 | 0.084 | 0.218 | 0.050 | 530554880 | 209592388 | True |
| 1M-hubby-clustered-reverse-heavy-csr-csc | csr_csc | 20 | 1194.206 | 2024.590 | 1.612 | 0.110 | 12.376 | 2.388 | 376049664 | 96455904 | True |
| 1M-hubby-clustered-reverse-heavy-hash | hash | 20 | 374.315 | 468.531 | 4.965 | 503.219 | 20.766 | 106.196 | 391540736 | 111558069 | True |
| 1M-hubby-clustered-reverse-heavy-hash-bi | hash_bi | 20 | 826.122 | 907.432 | 3.300 | 0.108 | 23.127 | 4.644 | 508080128 | 209592388 | True |
| 1M-hubby-clustered-scope-policy-mixed-csr-csc | csr_csc | 20 | 1232.546 | 1748.799 | 0.235 | 0.028 | 0.228 | 0.193 | 379789312 | 96455904 | True |
| 1M-hubby-clustered-scope-policy-mixed-hash | hash | 20 | 372.842 | 402.225 | 1.323 | 155.592 | 1.482 | 32.193 | 388550656 | 111558069 | True |
| 1M-hubby-clustered-scope-policy-mixed-hash-bi | hash_bi | 20 | 863.904 | 1053.868 | 0.381 | 0.051 | 0.408 | 0.318 | 511303680 | 209592388 | True |
| 1M-hubby-natural-scope-policy-mixed-csr-csc | csr_csc | 20 | 1453.954 | 1532.147 | 0.335 | 0.030 | 0.261 | 0.267 | 382754816 | 96455904 | True |
| 1M-hubby-natural-scope-policy-mixed-hash | hash | 20 | 754.301 | 841.024 | 1.336 | 138.565 | 0.736 | 28.722 | 398389248 | 127042437 | True |
| 1M-hubby-natural-scope-policy-mixed-hash-bi | hash_bi | 20 | 1299.973 | 1511.655 | 0.412 | 0.030 | 0.381 | 0.332 | 537096192 | 225076756 | True |
| 1M-uniform-clustered-balanced-csr-csc | csr_csc | 20 | 1162.212 | 1724.128 | 0.063 | 0.056 | 0.357 | 0.091 | 372629504 | 96461388 | True |
| 1M-uniform-clustered-balanced-hash | hash | 20 | 392.403 | 421.530 | 0.284 | 699.586 | 1.246 | 140.240 | 388263936 | 103464718 | True |
| 1M-uniform-clustered-balanced-hash-bi | hash_bi | 20 | 982.032 | 1102.082 | 0.072 | 0.042 | 0.489 | 0.108 | 505892864 | 201512138 | True |
| 1M-uniform-clustered-forward-dominant-csr-csc | csr_csc | 20 | 1123.771 | 1277.430 | 0.087 | 0.107 | 0.651 | 0.147 | 377438208 | 96461388 | True |
| 1M-uniform-clustered-forward-dominant-hash | hash | 20 | 630.847 | 980.158 | 0.242 | 930.707 | 1.049 | 186.415 | 393986048 | 103464718 | True |
| 1M-uniform-clustered-forward-dominant-hash-bi | hash_bi | 20 | 1011.929 | 1217.800 | 0.126 | 0.243 | 1.103 | 0.247 | 504455168 | 201512138 | True |
| 1M-uniform-clustered-reverse-heavy-csr-csc | csr_csc | 20 | 1092.720 | 1645.530 | 0.088 | 0.064 | 0.530 | 0.128 | 374870016 | 96461388 | True |
| 1M-uniform-clustered-reverse-heavy-hash | hash | 20 | 458.148 | 614.986 | 0.471 | 750.390 | 2.117 | 150.619 | 391053312 | 103464718 | True |
| 1M-uniform-clustered-reverse-heavy-hash-bi | hash_bi | 20 | 926.276 | 1077.997 | 0.149 | 0.112 | 1.212 | 0.248 | 505831424 | 201512138 | True |
| 1M-uniform-clustered-scope-policy-mixed-csr-csc | csr_csc | 20 | 1017.559 | 1170.826 | 0.031 | 0.034 | 0.025 | 0.031 | 373972992 | 96461388 | True |
| 1M-uniform-clustered-scope-policy-mixed-hash | hash | 20 | 384.495 | 439.960 | 0.125 | 166.824 | 0.060 | 33.459 | 385269760 | 103464718 | True |
| 1M-uniform-clustered-scope-policy-mixed-hash-bi | hash_bi | 20 | 852.884 | 909.373 | 0.019 | 0.038 | 0.017 | 0.022 | 504385536 | 201512138 | True |
| 5M-hubby-clustered-scope-policy-mixed-csr-csc | csr_csc | 10 | 11055.960 | 14599.965 | 1.004 | 0.033 | 1.007 | 0.810 | 1826988032 | 509861254 | True |
| 5M-hubby-clustered-scope-policy-mixed-hash | hash | 10 | 2426.088 | 3544.086 | 5.283 | 1033.679 | 3.688 | 210.803 | 1748213760 | 584911429 | True |
| 5M-hubby-clustered-scope-policy-mixed-hash-bi | hash_bi | 10 | 5800.653 | 6998.068 | 4.489 | 0.063 | 4.200 | 3.575 | 2424647680 | 1075337790 | True |
| 5M-uniform-clustered-scope-policy-mixed-csr-csc | csr_csc | 10 | 8519.590 | 9356.769 | 0.018 | 0.019 | 0.018 | 0.018 | 1790279680 | 509889449 | True |
| 5M-uniform-clustered-scope-policy-mixed-hash | hash | 10 | 3123.534 | 3590.221 | 0.168 | 927.214 | 0.131 | 185.573 | 1665740800 | 544938152 | True |
| 5M-uniform-clustered-scope-policy-mixed-hash-bi | hash_bi | 10 | 6976.276 | 7505.365 | 0.022 | 0.019 | 0.021 | 0.022 | 2443309056 | 1035319387 | True |

## Rankings by regime (lowest envelope-weighted p95)

### 1M × hubby × balanced × clustered

1. `csr_csc` — env=0.415 fwd_p95=0.483 rev_p95=0.105 build_p50=1138.307 rss=375771136 idx=96455904
2. `hash_bi` — env=0.443 fwd_p95=0.524 rev_p95=0.113 build_p50=871.505 rss=511488000 idx=209592388
3. `hash` — env=177.303 fwd_p95=1.113 rev_p95=882.027 build_p50=399.747 rss=382836736 idx=111558069

### 1M × hubby × forward_dominant × clustered

1. `hash_bi` — env=0.050 fwd_p95=0.016 rev_p95=0.084 build_p50=833.911 rss=530554880 idx=209592388
2. `csr_csc` — env=0.055 fwd_p95=0.017 rev_p95=0.102 build_p50=1249.447 rss=375742464 idx=96455904
3. `hash` — env=66.192 fwd_p95=0.059 rev_p95=330.502 build_p50=367.851 rss=397156352 idx=111558069

### 1M × hubby × reverse_heavy × clustered

1. `csr_csc` — env=2.388 fwd_p95=1.612 rev_p95=0.110 build_p50=1194.206 rss=376049664 idx=96455904
2. `hash_bi` — env=4.644 fwd_p95=3.300 rev_p95=0.108 build_p50=826.122 rss=508080128 idx=209592388
3. `hash` — env=106.196 fwd_p95=4.965 rev_p95=503.219 build_p50=374.315 rss=391540736 idx=111558069

### 1M × hubby × scope_policy_mixed × clustered

1. `csr_csc` — env=0.193 fwd_p95=0.235 rev_p95=0.028 build_p50=1232.546 rss=379789312 idx=96455904
2. `hash_bi` — env=0.318 fwd_p95=0.381 rev_p95=0.051 build_p50=863.904 rss=511303680 idx=209592388
3. `hash` — env=32.193 fwd_p95=1.323 rev_p95=155.592 build_p50=372.842 rss=388550656 idx=111558069

### 1M × hubby × scope_policy_mixed × natural

1. `csr_csc` — env=0.267 fwd_p95=0.335 rev_p95=0.030 build_p50=1453.954 rss=382754816 idx=96455904
2. `hash_bi` — env=0.332 fwd_p95=0.412 rev_p95=0.030 build_p50=1299.973 rss=537096192 idx=225076756
3. `hash` — env=28.722 fwd_p95=1.336 rev_p95=138.565 build_p50=754.301 rss=398389248 idx=127042437

### 1M × uniform × balanced × clustered

1. `csr_csc` — env=0.091 fwd_p95=0.063 rev_p95=0.056 build_p50=1162.212 rss=372629504 idx=96461388
2. `hash_bi` — env=0.108 fwd_p95=0.072 rev_p95=0.042 build_p50=982.032 rss=505892864 idx=201512138
3. `hash` — env=140.240 fwd_p95=0.284 rev_p95=699.586 build_p50=392.403 rss=388263936 idx=103464718

### 1M × uniform × forward_dominant × clustered

1. `csr_csc` — env=0.147 fwd_p95=0.087 rev_p95=0.107 build_p50=1123.771 rss=377438208 idx=96461388
2. `hash_bi` — env=0.247 fwd_p95=0.126 rev_p95=0.243 build_p50=1011.929 rss=504455168 idx=201512138
3. `hash` — env=186.415 fwd_p95=0.242 rev_p95=930.707 build_p50=630.847 rss=393986048 idx=103464718

### 1M × uniform × reverse_heavy × clustered

1. `csr_csc` — env=0.128 fwd_p95=0.088 rev_p95=0.064 build_p50=1092.720 rss=374870016 idx=96461388
2. `hash_bi` — env=0.248 fwd_p95=0.149 rev_p95=0.112 build_p50=926.276 rss=505831424 idx=201512138
3. `hash` — env=150.619 fwd_p95=0.471 rev_p95=750.390 build_p50=458.148 rss=391053312 idx=103464718

### 1M × uniform × scope_policy_mixed × clustered

1. `hash_bi` — env=0.022 fwd_p95=0.019 rev_p95=0.038 build_p50=852.884 rss=504385536 idx=201512138
2. `csr_csc` — env=0.031 fwd_p95=0.031 rev_p95=0.034 build_p50=1017.559 rss=373972992 idx=96461388
3. `hash` — env=33.459 fwd_p95=0.125 rev_p95=166.824 build_p50=384.495 rss=385269760 idx=103464718

### 5M × hubby × scope_policy_mixed × clustered

1. `csr_csc` — env=0.810 fwd_p95=1.004 rev_p95=0.033 build_p50=11055.960 rss=1826988032 idx=509861254
2. `hash_bi` — env=3.575 fwd_p95=4.489 rev_p95=0.063 build_p50=5800.653 rss=2424647680 idx=1075337790
3. `hash` — env=210.803 fwd_p95=5.283 rev_p95=1033.679 build_p50=2426.088 rss=1748213760 idx=584911429

### 5M × uniform × scope_policy_mixed × clustered

1. `csr_csc` — env=0.018 fwd_p95=0.018 rev_p95=0.019 build_p50=8519.590 rss=1790279680 idx=509889449
2. `hash_bi` — env=0.022 fwd_p95=0.022 rev_p95=0.019 build_p50=6976.276 rss=2443309056 idx=1035319387
3. `hash` — env=185.573 fwd_p95=0.168 rev_p95=927.214 build_p50=3123.534 rss=1665740800 idx=544938152

## Envelope decision table (`hubby` × `scope_policy_mixed`)

- **1M latency winner (env score):** `csr_csc` (env=0.193; N=20).
- **1M leanest steady index:** `csr_csc` (96455904 B).
- **1M fastest build p50:** `hash` (372.842 ms).
- **5M latency winner (env score):** `csr_csc` (env=0.810; N=10).
- **5M leanest steady index:** `csr_csc` (509861254 B).
- **5M fastest build p50:** `hash` (2426.088 ms).

## Gate call

Relative performance and memory trade-offs among `hash` / `hash_bi` / `csr_csc` are reported with build-repeat distributions (p50/p95) under the **approved** Action 2 envelope. Query latency uses one identical replayed trace per cell (last build); build uncertainty comes from N repeats. All **33/33** cells `correctness_ok=true`.

### Constraint-based winner (envelope-conditional)

Under **`motadata_like_hubby` + `scope_policy_mixed`**:

| Constraint | Winner | Why |
| ---------- | ------ | --- |
| Envelope-weighted query p95 | **`csr_csc`** | Best (or tied-best) at 1M and clearly best at 5M; reverse p95 stays ~0.03 ms while `hash` reverse p95 is hundreds–thousands of ms |
| Steady index bytes | **`csr_csc`** | ~½ of `hash_bi` at 1M; ~½ of `hash_bi` at 5M |
| Build p50 | **`hash`** | Fastest rebuild, but **fails the approved mix** on reverse latency |
| Runner-up latency | `hash_bi` | Close to `csr_csc` at 1M hubby mixed (0.32 vs 0.19 env); loses on memory and widens at 5M |

**Milestone A read-layout pick under this envelope: `csr_csc`.**  
`hash` remains a build-speed / forward-only hypothesis only if Motadata later proves reverse share ≈ 0 (contradicts current Scope policy). `hash_bi` stays viable if engineering prefers hash mutability semantics and accepts ~2× index bytes.

**Status:** Action 3 **PASSED** (2026-10-13). Not a Motadata-wide production lock; Actions 4–5 still required before Milestone A closes.

## Links

- Program: [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md)
- Envelope: [`../design-v3/action2-synthetic-operating-envelope.md`](../design-v3/action2-synthetic-operating-envelope.md)
- Prior: [Report 13](./13-action2-operating-envelope.md)

