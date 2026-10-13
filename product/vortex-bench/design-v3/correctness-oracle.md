# Correctness oracle (Design v3 — Action 1 strengthened)

Rules for declaring two hot representations **equivalent** on the same logical Motadata map estate.

Walk-checksum-only comparison (Stages 1–4.2) is **necessary but not sufficient**. Action 1 adds an independent typed-multigraph oracle implemented in `map-vortex-bench/src/oracle.rs` (`--action1-oracle`).

## Logical identity

When comparing edge **order**, **builder**, or **layout**, keep:

- Same node set and `entity_id` strings
- Same multiset of directed edges `(source_id, edge_type, target_id)` including **duplicate occurrences**
- Same generator seed / dataset_id

Physical Vortex row order may differ; the logical graph must not.

## Action 1 checks (independent oracle)

| Check | Pass criterion |
| ----- | -------------- |
| `edge_count` | `len(generator edges) ==` sum of forward typed occurrences in the layout |
| `node_table_endpoints` | Every forward source id exists in the node table |
| `typed_edge_multiset` | Forward layout multiset equals generator multiset |
| `forward_reverse_symmetry` | Reconstructing edges via reverse expand yields the same directed typed multiset |
| `reachable_equivalence` | For seeds p10/p50/p90/max_hub × hops {1,2,3} × {forward, reverse}: reachable set size and checksum match the **hash** reference |

Run across **clustered** and **natural** sorts for frozen candidates `hash`, `hash_bi`, `csr_csc`.

CLI: `map_vortex_bench --action1-oracle --estate-family <fam> --edges N --fix-nodes-from-density …`  
Script: `scripts/action1_oracle.sh` → Report 12.

## Degree-bin definition (locked)

Out-degree percentiles are computed among **sources that emit at least one edge** (`p10` / `p50` / `p90`). Reverse-heavy traces also include the **max-hub**. Percentiles are **not** taken over all nodes including isolates. Action 1 records this string in every `action1_oracle.json`.

## Reachable-set checksum (legacy Stages 1–4.2)

For query type `forward_bfs` / `reverse_blast` / `dependency_chain`:

1. Run the **hash** layout (sort-aware builder) as the reference.
2. Canonicalize the reachable set as a sorted list of `entity_id` strings.
3. Checksum = stable hash of joined sorted ids (lab implementation uses `DefaultHasher`; Action 1 compares counts + that checksum).
4. Candidate layout must match `reachable` count and checksum.

## Edge semantics

| Case | Rule |
| ---- | ---- |
| Duplicate typed edges `(s,t,et)` | **Keep** all occurrences (multigraph); BFS still visits `t` once |
| Self-loops | Generator skips; if present, oracle treats as no progress for hop expand |
| Dangling `target_id` not in node table | **Do not drop** silently; index may still list the id; BFS may stop if no out-edges |
| Edge-type filter | Apply identically on reference and candidate |

## Hybrid / delta (Stage 3.5)

- **Insert** adds one occurrence to out/in delta lists (or cancels one pending delete count).
- **Delete** removes **one occurrence** of the typed triple `(source, target, edge_type)`.
- Effective neighbors = base arcs (with first N matching occurrences hidden) ∪ remaining inserts.
- Occurrence-count semantics, not `edge_id` deletion.
- Zero-churn cells: covered by Action 1 when layout is in the frozen set. Churn cells remain deferred for effective-graph oracle under mutation.

## Failures

Any Action 1 check failure → cell invalid for Milestone A performance claims until fixed or documented exclusion.
