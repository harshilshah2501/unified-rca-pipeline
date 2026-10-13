# Report 12 — Action 1: independent typed-multigraph correctness oracle

**Priority:** P0 blocking for the decision-validation sprint.

This report replaces walk-checksum-only claims with an independent oracle that checks:

1. Edge counts (generator vs layout forward arcs).
2. Directed typed-edge **multiset** equality (including duplicates).
3. Forward/reverse adjacency symmetry (reverse reconstruction equals forward multiset).
4. Reachable-node equivalence vs **`hash_bi` reference** for p10/p50/p90/max_hub × hops {1,2,3} × {forward, reverse} (forward-only `hash` compares forward walks only — reverse expand is O(E) per step).
5. Both **clustered** and **natural** edge orders.

Frozen candidates: `hash` · `hash_bi` · `csr_csc`.

Source: `out/design-v3/action1` — 6 estate cells (100k + 500k × uniform / hubby / power_law).

## Critical defect found and fixed

**Bug:** `AdjBuilder::SortAware` used `HashMap::insert` per contiguous `source_id` run. On **natural** (non-clustered) order the same source reappears in many runs, so later runs **overwrote** earlier neighbor lists and dropped most arcs (e.g. 50k generated → ~9k retained on hash).

**Impact:** Any prior Stage 1–4.2 cell that built **hash / hash_bi with sort_aware on natural order** had an incomplete adjacency. Clustered cells were unaffected. CSR/CSC builds were unaffected (they materialize all triples).

**Fix:** `sort_aware` now **extends** the source bucket (`entry().or_default().extend(...)`) so reappearing sources accumulate arcs. See `map-vortex-bench/src/adj.rs`.

This is exactly why Action 1 exists: the weak walk-checksum path on Stage 4.2 did not catch the drop when the broken hash was also used as the reference.

## Degree-bin definition (confirmed)

out-degree percentiles among sources with ≥1 edge only (sources_with_edges=18434, nodes_table=20000, zero_out_approx=1566). p10/p50/p90 + max_hub for reverse-heavy. Not computed over all nodes including isolates.

## Results matrix

| Cell | Layout | Edge sort | All OK | Failed checks |
| ---- | ------ | --------- | ------ | ------------- |
| 100k-hubby | hash | clustered | PASS | — |
| 100k-hubby | hash_bi | clustered | PASS | — |
| 100k-hubby | csr_csc | clustered | PASS | — |
| 100k-hubby | hash | natural | PASS | — |
| 100k-hubby | hash_bi | natural | PASS | — |
| 100k-hubby | csr_csc | natural | PASS | — |
| 100k-power-law | hash | clustered | PASS | — |
| 100k-power-law | hash_bi | clustered | PASS | — |
| 100k-power-law | csr_csc | clustered | PASS | — |
| 100k-power-law | hash | natural | PASS | — |
| 100k-power-law | hash_bi | natural | PASS | — |
| 100k-power-law | csr_csc | natural | PASS | — |
| 100k-uniform | hash | clustered | PASS | — |
| 100k-uniform | hash_bi | clustered | PASS | — |
| 100k-uniform | csr_csc | clustered | PASS | — |
| 100k-uniform | hash | natural | PASS | — |
| 100k-uniform | hash_bi | natural | PASS | — |
| 100k-uniform | csr_csc | natural | PASS | — |
| 500k-hubby | hash | clustered | PASS | — |
| 500k-hubby | hash_bi | clustered | PASS | — |
| 500k-hubby | csr_csc | clustered | PASS | — |
| 500k-hubby | hash | natural | PASS | — |
| 500k-hubby | hash_bi | natural | PASS | — |
| 500k-hubby | csr_csc | natural | PASS | — |
| 500k-power-law | hash | clustered | PASS | — |
| 500k-power-law | hash_bi | clustered | PASS | — |
| 500k-power-law | csr_csc | clustered | PASS | — |
| 500k-power-law | hash | natural | PASS | — |
| 500k-power-law | hash_bi | natural | PASS | — |
| 500k-power-law | csr_csc | natural | PASS | — |
| 500k-uniform | hash | clustered | PASS | — |
| 500k-uniform | hash_bi | clustered | PASS | — |
| 500k-uniform | csr_csc | clustered | PASS | — |
| 500k-uniform | hash | natural | PASS | — |
| 500k-uniform | hash_bi | natural | PASS | — |
| 500k-uniform | csr_csc | natural | PASS | — |

## Exit gate

**PASSED** for the cells in this matrix: every frozen candidate passed the independent oracle on both clustered and natural order under the listed estates/scales.

## Notes

- Oracle builds layouts from the in-memory Arrow edge batch (same logical multiset); Vortex encode/decode is not on this path.
- After the sort_aware fix, **natural and clustered both PASS** for all frozen candidates in this matrix.
- Hybrid / segmented layouts are out of scope for Action 1 primary matrix.
- CLI: `--action1-oracle` · script: `map-vortex-bench/scripts/action1_oracle.sh`.
- Program: [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md).
- Contract update: [`../design-v3/correctness-oracle.md`](../design-v3/correctness-oracle.md).
