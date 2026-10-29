# Report 15 — Action 4: cold-to-hot recovery (T_ready)

**Envelope:** approved `motadata_like_hubby` + `scope_policy_mixed`.
Frozen layouts only. `remote_proxy` is a **lab copy+disk-cold proxy**, not Motadata Dest S3.

$T_{\mathrm{ready}} = T_{\mathrm{remote\_fetch}} + T_{\mathrm{decode}} + T_{\mathrm{build}} + T_{\mathrm{publish}}$

Source: `/root/Harshil-PoCs/Unified-RCA/product/vortex-bench/map-vortex-bench/out/design-v3/action4` — 18 scenario rows.

## Per-cell T_ready

| Cell | Layout | Coldness | N | T_ready p50 | T_ready p95 | Build p50 | Decode n+e (med) | Remote fetch (med) | Peak RSS | OK |
| ---- | ------ | -------- | -: | ----------: | ----------: | --------: | ---------------: | -----------------: | -------: | -- |
| 1M-hubby-disk-cold-csr-csc | csr_csc | disk_cold | 15 | 1203.43 | 1265.54 | 1177.96 | 25.25 | 0.00 | 377049088 | True |
| 1M-hubby-disk-cold-hash | hash | disk_cold | 15 | 450.00 | 507.48 | 423.57 | 26.21 | 0.00 | 370544640 | True |
| 1M-hubby-disk-cold-hash-bi | hash_bi | disk_cold | 15 | 942.90 | 980.61 | 914.54 | 28.05 | 0.00 | 503492608 | True |
| 1M-hubby-page-cache-warm-csr-csc | csr_csc | page_cache_warm | 15 | 1335.16 | 1470.01 | 1307.92 | 26.95 | 0.00 | 372031488 | True |
| 1M-hubby-page-cache-warm-hash | hash | page_cache_warm | 15 | 414.94 | 447.01 | 387.52 | 27.02 | 0.00 | 379428864 | True |
| 1M-hubby-page-cache-warm-hash-bi | hash_bi | page_cache_warm | 15 | 900.02 | 960.71 | 873.21 | 26.68 | 0.00 | 494542848 | True |
| 1M-hubby-process-cold-csr-csc | csr_csc | process_cold | 15 | 1316.04 | 1339.67 | 1282.61 | 48.38 | 0.00 | 376979456 | True |
| 1M-hubby-process-cold-hash | hash | process_cold | 15 | 450.21 | 513.60 | 420.64 | 29.40 | 0.00 | 390967296 | True |
| 1M-hubby-process-cold-hash-bi | hash_bi | process_cold | 15 | 925.15 | 1080.78 | 896.19 | 28.98 | 0.00 | 507928576 | True |
| 1M-hubby-remote-proxy-csr-csc | csr_csc | remote_proxy | 15 | 1320.80 | 1407.57 | 1283.95 | 30.08 | 7.68 | 372355072 | True |
| 1M-hubby-remote-proxy-hash | hash | remote_proxy | 15 | 464.36 | 723.63 | 394.43 | 27.53 | 7.70 | 387223552 | True |
| 1M-hubby-remote-proxy-hash-bi | hash_bi | remote_proxy | 15 | 992.45 | 1116.43 | 947.75 | 28.52 | 7.75 | 503160832 | True |
| 5M-hubby-disk-cold-csr-csc | csr_csc | disk_cold | 8 | 9793.57 | 10690.98 | 9672.95 | 120.45 | 0.00 | 1742114816 | True |
| 5M-hubby-disk-cold-hash | hash | disk_cold | 8 | 3178.16 | 3499.19 | 3033.56 | 144.44 | 0.00 | 1653968896 | True |
| 5M-hubby-disk-cold-hash-bi | hash_bi | disk_cold | 8 | 6902.31 | 8176.55 | 6777.37 | 124.74 | 0.00 | 2366603264 | True |
| 5M-hubby-process-cold-csr-csc | csr_csc | process_cold | 8 | 9957.78 | 22434.45 | 9815.96 | 141.67 | 0.00 | 1741684736 | True |
| 5M-hubby-process-cold-hash | hash | process_cold | 8 | 2399.88 | 2489.21 | 2271.02 | 128.69 | 0.00 | 1623486464 | True |
| 5M-hubby-process-cold-hash-bi | hash_bi | process_cold | 8 | 5646.53 | 5919.47 | 5533.34 | 112.98 | 0.00 | 2384224256 | True |

## Fastest T_ready by scale × coldness

### 1M × disk_cold

1. `hash` — t_ready_p50=450.00 build_p50=423.57 rss=370544640
2. `hash_bi` — t_ready_p50=942.90 build_p50=914.54 rss=503492608
3. `csr_csc` — t_ready_p50=1203.43 build_p50=1177.96 rss=377049088

### 1M × page_cache_warm

1. `hash` — t_ready_p50=414.94 build_p50=387.52 rss=379428864
2. `hash_bi` — t_ready_p50=900.02 build_p50=873.21 rss=494542848
3. `csr_csc` — t_ready_p50=1335.16 build_p50=1307.92 rss=372031488

### 1M × process_cold

1. `hash` — t_ready_p50=450.21 build_p50=420.64 rss=390967296
2. `hash_bi` — t_ready_p50=925.15 build_p50=896.19 rss=507928576
3. `csr_csc` — t_ready_p50=1316.04 build_p50=1282.61 rss=376979456

### 1M × remote_proxy

1. `hash` — t_ready_p50=464.36 build_p50=394.43 rss=387223552
2. `hash_bi` — t_ready_p50=992.45 build_p50=947.75 rss=503160832
3. `csr_csc` — t_ready_p50=1320.80 build_p50=1283.95 rss=372355072

### 5M × disk_cold

1. `hash` — t_ready_p50=3178.16 build_p50=3033.56 rss=1653968896
2. `hash_bi` — t_ready_p50=6902.31 build_p50=6777.37 rss=2366603264
3. `csr_csc` — t_ready_p50=9793.57 build_p50=9672.95 rss=1742114816

### 5M × process_cold

1. `hash` — t_ready_p50=2399.88 build_p50=2271.02 rss=1623486464
2. `hash_bi` — t_ready_p50=5646.53 build_p50=5533.34 rss=2384224256
3. `csr_csc` — t_ready_p50=9957.78 build_p50=9815.96 rss=1741684736

## Gate call

Action 4 distinguishes process-cold (cache may be warm), disk-cold (best-effort page-cache drop), page-cache-warm, and remote_proxy (local copy proxy). Choose recovery winner by **T_ready**, not build-only. All **18/18** cells `correctness_ok=true`.

### Constraint-based recovery finding

| Constraint | Winner | Evidence |
| ---------- | ------ | -------- |
| Fastest T_ready (all coldness tiers at 1M and 5M) | forward-only **`hash`** | ~0.4–0.5 s (1M) / ~2.4–3.2 s (5M). Skips reverse index — recovery-speed **reference**, not the fair bidirectional opponent |
| Like-for-like bidirectional recovery | **`hash_bi`** ahead of `csr_csc` | Disk-cold: 943 vs 1203 ms at 1M (~1.3×); 6902 vs 9794 ms at 5M (~1.4×). Do **not** quote ~3× (hash vs csr_csc) as the cost of a reverse-capable index |
| Slowest recovery | `csr_csc` | Build dominates T_ready; decode and remote_proxy fetch are small vs build |

**Implication:** Action 3’s query/index winner (`csr_csc`) is **not** the recovery-time winner. Milestone A must state both constraints, and must separate the forward-only recovery reference from the bidirectional gap. Real Motadata Dest remote-cold remains **unmeasured** (`remote_proxy` is a local copy proxy only).

Fair rebuild / recovery framing for cold readers: [Report 11 §5.2](./11-map-vortex-engineering-brief.md).

**Status:** Action 4 **PASSED** (2026-10-13) under lab coldness tiers.

## Links

- Matrix: [`../design-v3/action4-5-run-matrix.md`](../design-v3/action4-5-run-matrix.md)
- Prior: [Report 14](./14-action3-final-compare.md)

