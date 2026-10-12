# Report 07 — Design v3 Stage 3.5: fair layout compare

- **Why:** Critical review of Stages 0–3 — Stage 3 mixed unequal reverse capability into one aggregate p95 and omitted `hash_bi`.
- **Artifacts:** `map-vortex-bench/out/design-v3/stage3_5/` · [`../design-v3/query-algorithms.md`](../design-v3/query-algorithms.md)
- **Protocol:** 250k + 500k; uniform + hubby; clustered + natural; spine; sort_aware; **same** query mix for every layout (forward + dependency_chain + reverse); N=5; query replicate 5 → 135 events/cell
- **Layouts:** `hash` · `hash_bi` · `csr` · `csr_csc` · `hybrid` (1000 inserts / 500 one-occurrence deletes)

## Reverse algorithms (explicit)

| Layout | Reverse algorithm |
| ------ | ----------------- |
| hash | scan all out-lists |
| hash_bi | in-HashMap lookup |
| csr | scan all CSR arcs |
| csr_csc | CSC predecessor lookup |
| hybrid | CSC + occurrence delta |

## 500k clustered — per-class (not aggregate-only)

| Shape | Layout | Build ms | Forward p95 ms | Reverse p95 ms |
| ----- | ------ | -------: | -------------: | -------------: |
| uniform | hash | **181** | 0.23 | **334** |
| uniform | hash_bi | 424 | 0.07 | **0.09** |
| uniform | csr | 370 | 0.14 | **55** |
| uniform | csr_csc | 479 | 0.05 | **0.06** |
| uniform | hybrid | 424 | 0.08 | **0.10** |
| hubby | hash | **146** | 0.08 | **287** |
| hubby | hash_bi | 331 | 0.007 | **0.07** |
| hubby | csr | 294 | 0.03 | **31** |
| hubby | csr_csc | 507 | 0.01 | **0.07** |
| hubby | hybrid | 463 | 0.015 | **0.07** |

## Interpretation (addresses review Findings 5–7)

1. **Aggregate Stage 3 p95 for CSR was misleading** — CSR reverse was previously excluded from the mix. With equal mix, CSR reverse p95 is tens of ms (scan), not sub-ms.
2. **`hash_bi` removes the reverse-index confounder.** Reverse p95 matches CSR+CSC (~0.06–0.09 ms) while build stays below CSR+CSC (and near hybrid).
3. **Forward-only Scope** can still prefer **hash** (fastest build). Reverse/blast needs either **hash_bi** or **CSR+CSC** — not forward-only hash.
4. **CSR alone is not a reverse solution**; CSR+CSC (or hash_bi) is.
5. Hybrid tracks CSR+CSC reverse with occurrence-count deletes (documented; still not `edge_id`).

## Revised gate (synthetic)

| Candidate | Role after Stage 3.5 |
| --------- | -------------------- |
| Clustered + sort-aware **hash** | Experimental **forward** cold→hot baseline |
| **hash_bi** | Preferred next baseline if reverse walks matter and hash ops are acceptable |
| CSR+CSC | Still a candidate when packed arrays / memory layout beat two HashMaps |
| Hybrid | Mutation candidate; expand bursts before product use |
| Adaptive selector | Still deferred (Stage 5+) |

**Do not treat Stage 3 Report 06 aggregate query p95 as architecture selection evidence.** Use this report’s per-class table instead.

## Coldness caveat

All cells are `process_cold` (fresh decode/build). OS page cache may still be warm. Disk-cold / remote-cold remain unmeasured.
