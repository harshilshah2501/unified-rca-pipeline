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

**Normative map write/read detail:** [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md) — PoC `files.v1` (§3); Motadata **`vortex_s3.v1`** (§6): columnar `.vortex` parts (VTXF postscript + layout metadata), ObserveOps snapshot manifest, read caches, Rust action items. Walkthrough notes: [`pillar-b/docs/vortex_engineering_mystery_revised_v2.pdf`](../pillar-b/docs/vortex_engineering_mystery_revised_v2.pdf).

## Motadata profile: `vortex_s3.v1` (design; not wired in PoC)

| Tier | Job |
|------|-----|
| Hot | Vortex Arrays (columnar, often still encoded) + application adjacency for walks |
| Cold | Immutable `.vortex` files on S3; each file has its own layout metadata + postscript; ObserveOps `manifest.json` + `latest.json` index the snapshot |

Same logical keys as above. Pointer: `map/<tenant>/latest.json` → snapshot `version`.

**Footers:** Vortex writer owns per-file metadata/postscript; ObserveOps owns snapshot `manifest.json`. Details: [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md) §6.4.

## Logical keys (stable across profiles)

- Sketch: `(tenant, entity_id, metric_id, window, season_key, window_start)`
- Node: `(Dest tenant, entity_id)` — tenant from path / snapshot envelope only
- Edge: upsert `(source_id, edge_type, target_id)`; Motadata snowflake `edge_id`
- Snapshot: `(tenant, version)` packaged; PoC read convenience key = `graph_snapshot.json`; Motadata cold pointer = `latest.json`
- Change fact: `(tenant, change_id)` linked by ingest `ci_id` + `occurred_at`

## Independence

Pillar A and Pillar B share this dest interface via `ab_shared.dest`. Neither pillar imports the other. A Vortex / S3 adapter implements the same `Dest` protocol.
