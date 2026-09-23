# Gate B destination profile (PoC)

**Status:** File dest for the A/B PoC. Vortex and S3 are encodings of the same logical rooms, not a second schema.

**Shared rule (rooms vs temperature vs encoding):** Logical rooms (`map/` · `history/`) are content. **Vortex + S3** is the Motadata-shaped **production temperature** pair (hot query + cold retain) when that dest is chosen. **`files.v1`** is the PoC **encoding** of the same keys — not a second product design and not “Vortex forever” vs “files forever.” See also [`docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) §7.3–7.4 and [`docs/fabric/vortex-s3-interaction.html`](../../docs/fabric/vortex-s3-interaction.html).

## What Gate B is

ObserveOps Stores (E4) and Topology (E3) write through a destination profile. Vortex is **one** allowed profile among others (local files, existing Motadata dest, later S3 + Vortex). It is not mandatory as the only lake.

## PoC profile: `files.v1`

| Room | Logical artifacts | Dest keys under `poc/out/<tenant>/` |
|------|-------------------|-------------------------------------|
| Map | `graph_node.v1`, `graph_edge.v1`, `graph_snapshot.v1` | `map/graph_snapshot.json`, `map/nodes.jsonl`, `map/edges.jsonl` |
| History | `sketch.v1` | `history/sketches.jsonl` |
| Change facts (optional) | `change_fact.v1` | `history/change_facts.jsonl` — only when a change-fact writer runs; **not** part of Topology `publish_snapshot` |

Interface: `Dest.put(room, key, bytes)` / `Dest.get(room, key)`.

`room` is `map` or `history`. Writers never write edges into sketch rows.

**Normative map write/read detail:** [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md) (JSON encoding, keys, Vortex/S3 later).

## Later profiles (not implemented in this PoC)

| Profile | Encoding | When |
|---------|----------|------|
| Vortex | Same JSON fields, columnar / protobuf later | After Signed field tables |
| S3 | Same objects, partitioned keys | Cold archive of the same rooms |

Logical keys do not change when the profile changes:

- Sketch: `(tenant, entity_id, metric_id, window, season_key, window_start)`
- Node: `(Dest tenant, entity_id)` — tenant from path / snapshot envelope only
- Edge: upsert `(source_id, edge_type, target_id)`; Motadata snowflake `edge_id`
- Snapshot: `(tenant, version)` packaged; PoC read convenience key = `graph_snapshot.json`
- Change fact: `(tenant, change_id)` linked by ingest `ci_id` + `occurred_at`

## Independence

Pillar A and Pillar B share this dest interface via `ab_shared.dest`. Neither pillar imports the other. A Vortex adapter would implement the same `Dest` protocol.
