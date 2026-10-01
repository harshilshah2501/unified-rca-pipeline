# map_vortex — Motadata map/ columnar tables (Rust)

- **Primer:** [`../docs/MAP_VORTEX_S3_POC_PRIMER.md`](../docs/MAP_VORTEX_S3_POC_PRIMER.md)
- **Rows → Arrow → Vortex:** [`../docs/MAP_ARROW_VORTEX_PIPELINE.md`](../docs/MAP_ARROW_VORTEX_PIPELINE.md)
- **Columns:** [`../../contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md`](../../contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md)
- **Lifecycle:** [`../../contracts/MAP_HOT_COLD_LIFECYCLE.md`](../../contracts/MAP_HOT_COLD_LIFECYCLE.md)

**Role**

Motadata **`vortex_s3.v1`** map path in Rust. Python GraphWriter remains the **`files.v1`** lab.

| Phase | Status |
|-------|--------|
| A — cold parts + manifest + `publish_map` / `load_map` | **Done** |
| B — admit gates + `HotMap::apply_topo_line` | **Done** |
| C — adjacency / `neighbors` | Not started |
| D — `Dest` + S3 | Not started |
| E — maintain / explicit retire wire | Not started |

(Phase stub [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) only redirects here.)

## Build / test

```bash
cd pillar-ab-implementation/pillar-b/map-vortex
cargo test
cargo run --bin map_vortex_demo -- --tenant-root /tmp/map-tenant --version lab-1 --verify-load
```

## Modules

| Module | Job |
|--------|-----|
| `ci_qualify` / `admit` | Gates 1→4 + triplet allowlist |
| `hot` | `TopoLine` → upsert → `publish` |
| `schema` / `tables` / `types` / `edge_type` | Arrow builders + Motadata rows |
| `write` / `manifest` / `publish` / `load` | Cold checkpoint round-trip |

## Dependencies

- `arrow` 59.3 (matches `vortex` 0.86)
- `vortex` 0.86 with `tokio`
