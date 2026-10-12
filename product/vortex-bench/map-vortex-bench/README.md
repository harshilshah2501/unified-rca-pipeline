# map-vortex-bench

Cold-load + hot adjacency experiment for Motadata **`map_nodes` / `map_edges`**.

This bench does **not** redesign the locked flat schema. It measures:

1. Full vs spine Vortex projections at load
2. Edge sort (`natural` vs `clustered`)
3. Estate shape (`uniform` vs `hubby` source skew)
4. Adjacency builder (`naive` HashMap::entry vs `sort-aware` source runs)
5. Light rebuild profile counters (source-key clones, HashMap ops, groups)
6. Time to build out-adjacency and run a small BFS (Scope-like)

Program hub and comparative report: [`../README.md`](../README.md) · [`../reports/02-map-load-adjacency.md`](../reports/02-map-load-adjacency.md)

## Load modes

| Mode | Meaning |
|------|---------|
| `full` | All node + edge columns |
| `spine` | Nodes `(entity_id,type)` · edges `(source_id,target_id,edge_type)` |
| `nodes_full_edges_spine` | Full nodes · edge spine |

## Density

Prefer fixed mean out-degree across scales:

```bash
--edges 500000 --fix-nodes-from-density --mean-out-degree 5
```

That sets `nodes = round(edges / 5)` so larger runs are bigger graphs with the same density.

## Run

```bash
cd pillar-ab-implementation/vortex-bench/map-vortex-bench

# Classic clustered publish lab
cargo run --release --bin map_vortex_bench -- \
  --edges 100000 --fix-nodes-from-density --mean-out-degree 5 \
  --edge-sort clustered --estate-shape uniform \
  --out out/run-100k-edges-clustered --warmup 1 --repeats 3

# Follow-up: naive vs sort-aware on hubby + clustered (spine load)
cargo run --release --bin map_vortex_bench -- \
  --edges 500000 --fix-nodes-from-density --mean-out-degree 5 \
  --estate-shape hubby --edge-sort clustered \
  --load-mode spine --adj-builder naive --adj-builder sort-aware \
  --out out/followup-500k-hubby-clustered --warmup 1 --repeats 3
```

Natural vs clustered scale sweep and builder×hubby matrix: [`../reports/02-map-load-adjacency.md`](../reports/02-map-load-adjacency.md) §5.1, §5.4, and §8.

Design v3 Stages 1–3 drivers:

```bash
./scripts/stage1_2x2.sh
./scripts/stage2_screen.sh
./scripts/stage3_layouts.sh
./scripts/stage3_5_fair.sh
```

Contracts: [`../design-v3/`](../design-v3/). Reports 04–07 under [`../reports/`](../reports/).

Results: `<out>/results.json`, per-cell `*-manifest.json`, optional `*-queries.jsonl`.
