# Correctness oracle (Design v3)

Rules for declaring two hot representations **equivalent** on the same logical Motadata map estate.

## Logical identity

When comparing edge **order**, **builder**, or **layout**, keep:

- Same node set and `entity_id` strings
- Same multiset of directed edges `(source_id, edge_type, target_id)`
- Same generator seed / dataset_id

Physical Vortex row order may differ; the logical graph must not.

## Reachable-set oracle

For query type `forward_bfs` / `reverse_blast` / `dependency_chain`:

1. Run the **hash** layout (sort-aware builder) as the reference.
2. Canonicalize the reachable set as a sorted list of `entity_id` strings.
3. Checksum = SHA-256 of `join("\n", sorted_ids)` (UTF-8).
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
- **Delete** removes **one occurrence** of the typed triple `(source, target, edge_type)`: prefer popping a matching insert; else increment an occurrence tombstone count applied when reading the packed base.
- Effective neighbors = base arcs (with first N matching occurrences hidden) ∪ remaining inserts.
- This is **occurrence-count** semantics, not `edge_id` deletion. Duplicate typed edges require N deletes to hide N base occurrences.
- Oracle for zero-churn cells: reachable-set checksum vs `hash` reference. Churn cells are timed only (logical effective-graph oracle deferred to edge_id model).

## Failures

Any checksum mismatch → `correctness_ok=false` on the run manifest; Stage 3 cell is invalid for performance claims.
