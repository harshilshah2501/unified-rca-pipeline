# Factor registry (Stages 1–3)

| Factor | Levels | Stage |
| ------ | ------ | ----- |
| `edge_sort` | `natural`, `clustered` | 1–3 |
| `adj_builder` | `naive`, `sort_aware` | 1–2 (hash); Stage 3 hash path |
| `layout` | `hash`, `hash_bi`, `csr`, `csr_csc`, `hybrid` | 3 / 3.5 |
| `load_mode` | `full`, `spine`, `nodes_full_edges_spine` | 1–2 |
| `estate_shape` | `uniform`, `hubby` | 1–3 |
| `edges` | 100k, 250k, 500k, 1M | 2–3 (Stage 1 fixed 500k) |
| `mean_out_degree` | **5** (fixed density) | all |
| `coldness` | `process_cold`, `page_cache_warm` | 1+ |
| `query.type` | `forward_bfs`, `reverse_blast`, `dependency_chain` | 2–3 |
| `seed_degree_bin` | `p10`, `p50`, `p90` | 2–3 |
| `hops` | 1, 2, 3 | 2–3 |
| `churn` | 0 (Stages 1–2); Stage 3 hybrid: synthetic inserts/deletes | 3 |

Hubby defaults: `hub_fraction=0.01`, `hub_edge_share=0.50`.
