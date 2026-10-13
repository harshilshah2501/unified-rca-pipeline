# Actions 4 & 5 — Run matrix (Milestone A close)

**Envelope:** approved `motadata_like_hubby` + `scope_policy_mixed`  
**Layouts:** frozen `hash` · `hash_bi` · `csr_csc` (no expansion)  
**Scripts:** [`../map-vortex-bench/scripts/action4_recovery.sh`](../map-vortex-bench/scripts/action4_recovery.sh), [`../map-vortex-bench/scripts/action5_concurrency.sh`](../map-vortex-bench/scripts/action5_concurrency.sh)

## Action 4 — Cold-to-hot recovery

\[
T_{\mathrm{ready}} = T_{\mathrm{remote\_fetch}} + T_{\mathrm{decode}} + T_{\mathrm{build}} + T_{\mathrm{publish}}
\]

| Factor | Levels |
| ------ | ------ |
| Estate | `hubby` (envelope) |
| Scales | 1M (N=15 builds), 5M (N=8 builds) |
| Layouts | 3 frozen |
| Coldness | `process_cold`, `disk_cold`, `page_cache_warm`, `remote_proxy` (lab copy proxy — **not** Motadata Dest S3) |
| Publish | lab ready-marker write (stub for atomic pointer swap) |

**Exit:** which layout reaches query-ready fastest under each coldness tier.

## Action 5 — Concurrency and memory

| Factor | Levels |
| ------ | ------ |
| Estate / profile | `hubby` × `scope_policy_mixed` |
| Scales | 1M primary; 5M thin (`csr_csc` vs `hash_bi` vs `hash`) |
| Readers | 1, 4, 16 shared-graph concurrent trace replay |
| Dual-index hold | on at 1M (peak RSS with old+new coexisting) |
| Coldness | `process_cold` (isolation from Action 4) |

**Exit:** every remaining candidate satisfies concurrent p95/p99 and peak-memory under the envelope.
