# Report 06 — Design v3 Stage 3: hot layout deep compare

- **Program:** [`../design-v3/`](../design-v3/)
- **Artifacts:** `map-vortex-bench/out/design-v3/stage3/` (+ `stage3-summary.json`)
- **Layouts:** `hash` · `csr` · `csr_csc` · `hybrid` (CSR/CSC base + HashMap delta; 1000 inserts / 500 deletes)
- **Scales:** 250k · 500k · 1M edges; shapes uniform + hubby; orders clustered (primary) + natural; spine; sort_aware hash path; N=5; ≥ query events via replicate 5 × bins × hops
- **Caveat:** synthetic only — not a Motadata production lock

## Pareto snapshot (clustered publish)

Build_ms = layout construction after spine decode. Query p50/p95 mix forward, dependency_chain, and reverse (hash reverse scans all arcs).

### 500k edges

| Shape | Layout | Build ms | Query p50 ms | Query p95 ms | Peak RSS MB | Correct |
| ----- | ------ | -------: | -----------: | -----------: | ----------: | ------- |
| uniform | hash | **164** | 0.18 | **314** | 391 | yes |
| uniform | csr | 311 | 0.010 | 0.22 | 391 | yes |
| uniform | csr_csc | 427 | 0.010 | **0.17** | 406 | yes |
| uniform | hybrid | 427 | 0.026 | 0.41 | 406 | yes |
| hubby | hash | **170** | 0.07 | **305** | 387 | yes |
| hubby | csr | 366 | 0.002 | 0.05 | 387 | yes |
| hubby | csr_csc | 546 | 0.003 | **0.05** | 409 | yes |
| hubby | hybrid | 528 | 0.004 | 0.09 | 415 | yes |

### 1M edges

| Shape | Layout | Build ms | Query p95 ms | Peak RSS MB |
| ----- | ------ | -------: | -----------: | ----------: |
| uniform | hash | **386** | **319** | 715 |
| uniform | csr | 745 | 0.20 | 730 |
| uniform | csr_csc | 1042 | **0.12** | 754 |
| uniform | hybrid | 1223 | 0.26 | 754 |
| hubby | hash | **362** | **375** | 752 |
| hubby | csr | 804 | 0.37 | 752 |
| hubby | csr_csc | 1165 | **0.10** | 765 |
| hubby | hybrid | 1272 | 0.26 | 765 |

## Interpretation

1. **Hash wins cold rebuild time** (roughly 2–3× faster build than CSR family) — matches prioritizing failover / `load_map` latency when Scope is forward-only after index exists.
2. **Hash reverse blast dominates query p95** (hundreds of ms) because predecessors require a full scan. Forward-only Scope stays cheap on hash.
3. **CSR / CSR+CSC collapse reverse query tails** to sub-ms–low-ms p95 at the cost of longer build and slightly higher RSS.
4. **Hybrid** tracks CSR+CSC build cost and keeps mutation without full rebuild; small query overhead vs packed CSR+CSC.
5. Hubby vs uniform does not change the layout ranking.

## Gate recommendation (synthetic)

| Decision | Call |
| -------- | ---- |
| Adopt clustered publish + sort-aware **hash** for Motadata cold→hot forward Scope path | **Yes** (Stages 1–3 reinforce Report 02) |
| Prototype **CSR+CSC** in GraphWriter | **Yes, if** reverse / blast-radius walks are on the critical product path |
| Deploy hybrid delta | **Candidate** when mutation rate or freshness SLO forbids full CSR rebuilds — not required for read-mostly publish cycles |
| Adaptive layout selector | Deferred (Stage 5); not established here |

## Gate

Stage 3 **passed** for synthetic estates: four layouts measured with correctness_ok; Pareto documented; production generalization still requires real estates (Design v3 Stages 4–6).
