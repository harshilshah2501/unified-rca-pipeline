# map-vortex-bench

Cold-load + hot adjacency experiment for Motadata **`map_nodes` / `map_edges`**.

This bench does **not** redesign the locked flat schema. It measures:

1. Full vs spine Vortex projections at load
2. Edge sort (`natural` vs `clustered`)
3. Time to build out-adjacency and run a small BFS (Scope-like)

Program hub and comparative report: [`../README.md`](../README.md) · [`../reports/02-map-load-adjacency.md`](../reports/02-map-load-adjacency.md)

## Load modes

| Mode | Meaning |
|------|---------|
| `full` | All node + edge columns |
| `spine` | Nodes `(entity_id,type)` · edges `(source_id,target_id,edge_type)` |
| `nodes_full_edges_spine` | Full nodes · edge spine |

## Run

```bash
cd pillar-ab-implementation/vortex-bench/map-vortex-bench
cargo run --release --bin map_vortex_bench -- \
  --nodes 20000 --edges 100000 --edge-sort clustered \
  --out out/run-100k-edges-clustered --warmup 1 --repeats 3
```

Results: `<out>/results.json` plus a cold→walk summary on stdout.
