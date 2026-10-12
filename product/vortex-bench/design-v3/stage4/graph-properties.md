# Graph properties (must validate before timing)

After generation, compute and persist `properties.json`. Benchmarking is **refused** if family checks fail.

## Always recorded

| Metric | Definition |
| ------ | ---------- |
| `nodes`, `edges` | Counts |
| `mean_out_degree`, `mean_in_degree` | edges / nodes |
| `out_p50/p90/p99/max`, `in_p50/p90/p99/max` | Among nodes with degree > 0 |
| `sources_with_edges`, `sinks_with_edges` | Non-zero degree counts |
| `top1pct_sources_edge_share` | Edges from top 1% sources by out-degree |
| `weak_component_count` | Undirected connected components |
| `reciprocity` | Fraction of directed edges that have a reverse twin |
| `edge_type_histogram` | Counts by Motadata edge type |
| `reachable_hops_2_sample` | Median reachable set size for 16 random seeds at hops=2 |

## Family gates

See [`estate-families.md`](./estate-families.md). Failures abort Stage 4.1/4.2 for that cell with `validation_ok=false`.
