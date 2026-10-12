# Query execution algorithms per hot layout (Stage 3.5)

Every Stage 3.5 cell runs the **same** query mix: forward_bfs, dependency_chain, and reverse_blast for each seed×hops. Layouts differ only in how neighbors are resolved.

| Layout | Forward | Reverse |
| ------ | ------- | ------- |
| `hash` | `HashMap<source, Vec<(target,et)>>` lookup | Scan **all** out-lists for targets matching seed |
| `hash_bi` | Same out HashMap | `HashMap<target, Vec<(source,et)>>` lookup |
| `csr` | CSR offsets → targets | Scan **all** CSR arcs for targets matching seed |
| `csr_csc` | CSR | CSC offsets → sources |
| `hybrid` | CSR + occurrence delta inserts − delete counts | CSC + delta (same occurrence rules) |

## Hybrid mutation semantics (Stage 3.5)

- Effective multigraph = packed base arcs ∪ delta inserts, minus **occurrence** tombstones.
- `delete_one_occurrence(src,tgt,et)` removes **one** matching insert if present; otherwise increments `delete_counts[(src,tgt,et)]` by 1.
- Expanding a CSR/CSC neighbor list skips the first `delete_counts` occurrences of each typed triple, then emits the rest.
- This is **not** edge_id-based deletion. Product Motadata still needs an explicit edge identity model before production hybrid.

## Coldness labels

| Label | Meaning in this bench |
| ----- | --------------------- |
| `process_cold` | Fresh decode+build each timed repeat; **OS page cache may still be warm** |
| `page_cache_warm` | Untimed preload, then timed repeats |

Disk-cold / remote-cold (drop caches / object-store path) are **not** measured in Stage 3.5.
