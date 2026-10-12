# Report 05 — Design v3 Stage 2: factor screening

- **Program:** [`../design-v3/`](../design-v3/)
- **Artifacts:** `map-vortex-bench/out/design-v3/stage2/` (+ `stage2-summary.json`, `*-queries.jsonl`)
- **Layout:** hash only (CSR deferred to Stage 3)
- **Matrix:** edges ∈ {100k,500k,1M} × shape ∈ {uniform,hubby} × sort ∈ {natural,clustered} × load ∈ {spine,full} × builders {naive,sort_aware}; N=5; queries emitted (degree bins × hops 1–3, replicate 2)

## Ranked material effects

### 1. Edge order (largest)

Clustered vs natural **build** under spine (naive builder):

| Edges | Shape | Clustered % faster |
| ----- | ----- | -----------------: |
| 100k | uniform | 17% |
| 100k | hubby | 27% |
| 500k | uniform | **42%** |
| 500k | hubby | **43%** |
| 1M | uniform | **42%** |
| 1M | hubby | 28% |

Order remains the dominant rebuild lever as scale grows.

### 2. Builder × order interaction

Sort-aware on **clustered** (spine):

| Edges | Shape | Sort-aware % faster |
| ----- | ----- | ------------------: |
| 100k | uniform | 24% |
| 100k | hubby | 15% |
| 500k | uniform | 18% |
| 500k | hubby | 9% |
| 1M | uniform | 4% |
| 1M | hubby | 11% |

Positive on clustered; Stage 1 already showed natural+sort_aware is not a free win.

### 3. Load mode

Decode share of cold→walk on clustered spine is small (~5–14%) and shrinks with scale — adjacency still dominates. Full vs spine is a modest decode delta (map columns thin); keep spine as default for walk rebuild.

### 4. Shape × query tails

Forward BFS stays sub-millisecond at p50. **Reverse blast on hash** is expensive (full adjacency scan): p50 ~12–16 ms, p95 hundreds of ms. That motivates CSR+CSC in Stage 3. Hubby p90 seeds also widen forward tails vs p10 — sample degree bins, not a single seed.

## What Stage 3 should deepen

1. Hot **layout** (hash vs CSR vs CSR+CSC vs hybrid) under clustered publish (primary) + natural control  
2. Query mix with p10/p50/p90 seeds and reverse blast (CSC)  
3. Hybrid mutation microbench (inserts/deletes on delta)  
4. Peak RSS alongside build and query p95  

## Gate

Stage 2 **passed**: factors ranked; query JSONL present; CSR not required for screening conclusions.
