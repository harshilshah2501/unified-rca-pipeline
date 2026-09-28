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
| [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md) | Wave-1 legal `(src_type, relation, dst_type)` + why invalid |

## Legacy / Dest (still in use)

| Artifact | Role |
|----------|------|
| [`schemas/ingest_v1.schema.json`](./schemas/ingest_v1.schema.json) | **Deprecated** for writer routing — lab fixtures + stream→graph demo until migrated |
| `graph_node` / `graph_edge` / `graph_snapshot` | Dest `map/` publish shapes (Motadata SCREAMING_SNAKE edges) — Fusion Dest refresh is follow-on |

Schemas live only here. Package trees (`pillar-a|b/integration`) must **not** mirror this folder — validators load this path directly.