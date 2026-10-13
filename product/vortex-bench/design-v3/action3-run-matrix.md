# Action 3 — Run matrix (Milestone A)

**Envelope:** [`action2-synthetic-operating-envelope.md`](./action2-synthetic-operating-envelope.md)  
**Script:** [`../map-vortex-bench/scripts/action3_compare.sh`](../map-vortex-bench/scripts/action3_compare.sh)  
**Report:** [`../reports/14-action3-final-compare.md`](../reports/14-action3-final-compare.md)

## Frozen layouts

`hash` · `hash_bi` · `csr_csc` (CLI: `hash`, `hash-bi`, `csr-csc`)

## Factors

| Factor | Levels |
| ------ | ------ |
| Scales | **1M** full; **5M** thin ladder |
| Estates | `uniform`, `hubby` (`motadata_like_hubby` = hubby) |
| Edge order | clustered (primary); natural control at 1M hubby × `scope_policy_mixed` |
| Workloads | `forward_dominant`, `balanced`, `reverse_heavy`, **`scope_policy_mixed`** |
| Build repeats | 1M: **20**; 5M: **10** |
| Trace | identical JSONL per prep cell; `trace_len=200`; mixed profile uses **hops=2** |

## Primary decision cells

`hubby` × `scope_policy_mixed` × {1M, 5M} × clustered × three layouts.

Sensitivity: other profiles and `uniform` at 1M; natural-order control at 1M.

## Scoring

Envelope-weighted class p95: `0.7 × forward + 0.2 × reverse + 0.1 × dependency`.  
Also report build p50/p95, peak RSS, steady index bytes.
