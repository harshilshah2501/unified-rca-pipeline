# Pillar A/B contracts

Shared wire and Dest schemas for Motadata ObserveOps Pillar A (sketches → `history/`) and Pillar B (topology → `map/`).

## Writer fan-out (current)

| Artifact | Role |
|----------|------|
| [`schemas/writer_stream_v1.schema.json`](./schemas/writer_stream_v1.schema.json) | Common post-E2 stream — **no `fact_kind`**; optional `topology` / `metric` / `event` / `span` / `anomaly` blocks |
| [`schemas/graph_write_intent_v1.schema.json`](./schemas/graph_write_intent_v1.schema.json) | GraphRegulator → GraphWriter |
| [`schemas/sketch_admit_intent_v1.schema.json`](./schemas/sketch_admit_intent_v1.schema.json) | SketchRegulator → SketchWriter |
| [`WRITER_REGULATOR.md`](./WRITER_REGULATOR.md) | Presence predicates, dual-fire rules, supersession notes |
| [`RELATION_MAPPING.md`](./RELATION_MAPPING.md) | Fusion camelCase eleven ↔ Motadata Dest fifteen |
| [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md) | Legal `(src_type, relation, dst_type)` for all fifteen Motadata relations |
| [`../pillar-b/docs/MAP_VORTEX_S3_POC_PRIMER.md`](../pillar-b/docs/MAP_VORTEX_S3_POC_PRIMER.md) | Teaching entry — Vortex + S3 PoC |
| [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md) | Normative `map/` Dest keys (`files.v1` + `vortex_s3.v1`) |
| [`MAP_WRITER_VORTEX_COHESION.md`](./MAP_WRITER_VORTEX_COHESION.md) | Locked: separate writers, shared Vortex Dest; GraphWriter verbs; walk brief later |
| [`GATE_B_DEST_PROFILE.md`](./GATE_B_DEST_PROFILE.md) | Stub → MAP_WRITE_READ / primer |

## Legacy / Dest (still in use)

| Artifact | Role |
|----------|------|
| [`schemas/ingest_v1.schema.json`](./schemas/ingest_v1.schema.json) | **Deprecated** for writer routing — lab fixtures + stream→graph demo until migrated |
| `graph_node` / `graph_edge` / `graph_snapshot` | Dest `map/` row shapes (Motadata SCREAMING_SNAKE edges) |
| [`schemas/map_snapshot_manifest_v1.schema.json`](./schemas/map_snapshot_manifest_v1.schema.json) | Cold snapshot chunk index for `vortex_s3.v1` |

Schemas live only here. Package trees (`pillar-a|b/integration`) must **not** mirror this folder — validators load this path directly.