# Map physical overlay (JSON Schema ↔ Arrow / Vortex)

- **Status:** Production Phase‑1 + Phase‑2 wiring (2026-10-07).
- **Logical SoT:** [`graph_node_v1.schema.json`](./graph_node_v1.schema.json) · [`graph_edge_v1.schema.json`](./graph_edge_v1.schema.json)
- **Physical overlay SoT:** [`graph_node_v1.physical.json`](./graph_node_v1.physical.json) · [`graph_edge_v1.physical.json`](./graph_edge_v1.physical.json)
- **Generated Rust:** [`../../pillar-b/map-vortex/src/schema.rs`](../../pillar-b/map-vortex/src/schema.rs)

## Why two (plus generated) artifacts

| Artifact | Role |
|----------|------|
| `*.schema.json` | Logical contract — Python / lab validate JSON rows |
| `*.physical.json` | Motadata **physical** Arrow types, nullability, walk spine, roles |
| `map-vortex/src/schema.rs` | **Generated** from physical overlays — Vortex write/load |

Do not hand-edit `schema.rs`. Change the physical overlay, then regenerate.

## Phase‑1 — hard sync check

```bash
cd pillar-ab-implementation
make check-map-physical
# or: python3 scripts/check_map_physical_schema.py
```

Asserts:

1. Cold column names in JSON Schema ≡ physical overlay (minus `envelope_only_fields` such as `schema_version`)
2. Nullability matches (JSON `type` includes `null` ↔ `nullable: true`; required fields are non-null)
3. Motadata role → Arrow type rules (`epoch_ms` / `snowflake` → `UInt64`, `id` → `Utf8`, …)
4. Checked-in `schema.rs` equals generator output (no drift)

## Phase‑2 — generator

```bash
make generate-map-arrow-schema
# or: python3 scripts/generate_map_arrow_schema.py
```

Rewrites `pillar-b/map-vortex/src/schema.rs` from the physical overlays (dictionary + plain schemas).

## Roles (Motadata mapping table)

| Role | Arrow plain | Notes |
|------|-------------|--------|
| `id` | `Utf8` | `entity_id`, `source_id`, `target_id` |
| `string` | `Utf8` | display `name` |
| `enum_like` | `Utf8` (+ optional dict) | `type`, `edge_type` |
| `promoted_tag` | `Utf8` (+ optional dict) | `attr_catalog.v1` |
| `epoch_ms` | `UInt64` | clocks |
| `snowflake` | `UInt64` | `edge_id`, `evidence_event_id` |
| `u32` | `UInt32` | node `version` |
