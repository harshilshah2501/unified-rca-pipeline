# Report 04 — Design v3 Stage 1: 2×2 reproduce (order × builder)

- **Program:** [`../design-v3/`](../design-v3/)
- **Artifacts:** `map-vortex-bench/out/design-v3/stage1/` (+ `stage1-summary.json`)
- **Protocol:** 500k edges, `--fix-nodes-from-density --mean-out-degree 5`, spine load, process_cold, warmup 1, **N=20** timed repeats, hash layout only
- **Shapes:** uniform · hubby (1% hubs → 50% of edge sources)

## Objective

Reproduce Report 02 / follow-up without confounding: measure **edge order** and **adj builder** as a full 2×2 factorial.

## Build_ms median cells (from N=20 medians of total path; build component shown)

### Uniform

| | Naive | Sort-aware |
| -- | -----: | ---------: |
| Natural | 246.1 ms | 275.2 ms |
| Clustered | 159.1 ms | **147.0 ms** |

- Order effect (naive): clustered **35.4%** faster than natural
- Builder on clustered: sort-aware **7.6%** faster
- Builder on natural: sort-aware **11.8% slower** (groups ≈ E; extra loop overhead)

### Hubby

| | Naive | Sort-aware |
| -- | -----: | ---------: |
| Natural | 255.5 ms | 192.9 ms |
| Clustered | 165.4 ms | **154.7 ms** |

- Order effect (naive): clustered **35.3%** faster
- Builder on clustered: **6.5%** faster
- Builder on natural: **24.5%** faster (hubby natural still has some source locality)

## Cold→walk p50 / p95 (spine, total)

| Shape | Sort | Builder | p50 total ms | p95 total ms |
| ----- | ---- | ------- | -----------: | -----------: |
| uniform | natural | naive | 260.4 | 323.3 |
| uniform | natural | sort_aware | 291.4 | 435.4 |
| uniform | clustered | naive | 177.1 | 323.3 |
| uniform | clustered | sort_aware | **160.6** | **171.6** |
| hubby | natural | naive | 271.6 | 303.4 |
| hubby | natural | sort_aware | 209.0 | 265.4 |
| hubby | clustered | naive | 180.8 | 202.2 |
| hubby | clustered | sort_aware | **168.4** | **177.1** |

Key clones: naive always 500k; sort-aware on clustered ≈ 99k (uniform) / 92k (hubby).

## Interpretation

1. **Main effect = clustered order** (~35% build) on both shapes — reproduces Report 02 direction.
2. **Sort-aware helps on clustered**; do not pair it with natural as a “win.”
3. Hubby does not erase the clustering benefit.
4. p95 can be noisy at N=20 (see uniform clustered naive p95) — use for screening, not SLO lock.

## Gate

Stage 1 **passed**: factorial attribution recorded; manifests written; correctness_ok on all cells.
