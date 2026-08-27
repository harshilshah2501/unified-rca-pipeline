# Gate B destination profile (PoC)

**Status:** File dest for the A/B PoC. Vortex and S3 are encodings of the same logical rooms, not a second schema.

## What Gate B is

ObserveOps Stores (E4) and Topology (E3) write through a destination profile. Vortex is **one** allowed profile among others (local files, existing Motadata dest, later S3 + Vortex). It is not mandatory as the only lake.

## PoC profile: `files.v1`

| Room | Logical artifacts | Path under `poc/out/<tenant>/` |
|------|-------------------|--------------------------------|
| Map | `graph_node.v1`, `graph_edge.v1`, `GraphSnapshot` | `map/` |
| History | `sketch.v1` | `history/sketches.jsonl` |
| Change facts (later) | `change_fact.v1` | `history/change_facts.jsonl` |

Interface: `Dest.put(room, key, bytes)` / `Dest.get(room, key)`.

`room` is `map` or `history`. Writers never write edges into sketch rows.

## Later profiles (not implemented in this PoC)

| Profile | Encoding | When |
|---------|----------|------|
| Vortex | Same JSON fields, columnar / protobuf later | After Signed field tables |
| S3 | Same objects, partitioned keys | Cold archive of the same rooms |

Logical keys do not change when the profile changes:

- Sketch: `(tenant, entity_id, metric_id, window, season_key, window_start)`
- Node: `(tenant, ci_id)`
- Edge: `(tenant, edge_id)`
- Change fact: `(tenant, change_id)` linked by `ci_id` + `occurred_at`

## Independence

Pillar A and Pillar B share this dest interface via `ab_shared.dest`. Neither pillar imports the other. A Vortex adapter would implement the same `Dest` protocol.
