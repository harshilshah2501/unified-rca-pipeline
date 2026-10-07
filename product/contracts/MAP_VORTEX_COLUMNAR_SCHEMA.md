# Map Vortex columnar tables — nodes + edges

- **Status:** **Re-locked** Motadata `vortex_s3.v1` physical columns (2026-09-30). Supersedes the 2026-09-29 PoC lock (Utf8 ISO times + JSON `metadata` bag).
- **Logical wire SoT:** [`graph_node_v1.schema.json`](./schemas/graph_node_v1.schema.json) · [`graph_edge_v1.schema.json`](./schemas/graph_edge_v1.schema.json) — **same flat shape** as Vortex (promoted tags + epoch-ms integers).
- **Physical overlay SoT:** [`graph_node_v1.physical.json`](./schemas/graph_node_v1.physical.json) · [`graph_edge_v1.physical.json`](./schemas/graph_edge_v1.physical.json) — see [`MAP_PHYSICAL_OVERLAY.md`](./schemas/MAP_PHYSICAL_OVERLAY.md). Regenerates Rust via `make generate-map-arrow-schema`; drift blocked by `make check-map-physical`.
- **Dest prose:** [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md) §6
- **Code (Rust):** [`pillar-b/map-vortex/`](../pillar-b/map-vortex/) (`src/schema.rs` is **generated** — do not hand-edit)
- **Visual pipeline:** [`../pillar-b/docs/MAP_ARROW_VORTEX_PIPELINE.md`](../pillar-b/docs/MAP_ARROW_VORTEX_PIPELINE.md)
- **Lifecycle:** [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md)

**Basics**

- Two tables only: `map_nodes` and `map_edges`.
- Tenant is on Dest path / snapshot pointer — **not** a column on either table.
- **Physical rule:** typed scalar / dictionary columns that Vortex can zone-prune. **No** nested JSON document column on the cold path.

---

## 1. Design locks (2026-09-30)

| Choice | Lock |
|--------|------|
| Table count | **2** — `map_nodes` and `map_edges` |
| Physical model | Columnar Struct (one stream per field) |
| Implementation | **Rust** `map_vortex`; Arrow `RecordBatch` → Vortex writer |
| Timestamps | **UInt64** Unix epoch **milliseconds** (UTC). Null allowed only where the column is nullable |
| CI join ids | **`entity_id` / `source_id` / `target_id` stay Utf8** (same string as ingest `ci_id` / sketch `entity_id`). Numeric CI surrogates are **not** in this lock — Identity + sketch must move together later |
| Snowflakes | `edge_id`, `evidence_event_id` as **UInt64** |
| Flexible attrs | **No** `metadata` Utf8 JSON bag on cold Vortex |
| Promoted tags | **Closed, versioned** columns on nodes only — see §2.1 (`attr_catalog.v1`) |
| Unbounded tags / nested arrays | **Not** cold columns. Do not `ALTER` the table for every inventory key. Display-only or wait for the next attr-catalog version |
| Edges | **No** tag columns; audit = snowflakes + validity |
| `schema_version` | Not a data column — table / file convention |

**Why this re-lock**

- Utf8 ISO timestamps and JSON-in-a-string block useful **zone-map prune** (min/max on time; equality on `env`).
- “Flat” means **no nested document in one cell for query/prune**, not “ban every variable-length Utf8.” `entity_id` and `name` remain Utf8.

---

## 2. Table `map_nodes` (← `graph_node.v1` at publish)

| Column | Arrow / Vortex DType | Nullable | Notes |
|--------|----------------------|----------|-------|
| `entity_id` | Utf8 | no | Join key within tenant |
| `type` | Utf8 (dict-encode friendly) | no | Motadata lowercase: `service`, `host`, … |
| `name` | Utf8 | no | Display name |
| `env` | Utf8 (dict-friendly) | yes | Promoted tag `attr_catalog.v1` |
| `region` | Utf8 (dict-friendly) | yes | Promoted tag |
| `owner` | Utf8 (dict-friendly) | yes | Promoted tag |
| `namespace` | Utf8 (dict-friendly) | yes | Promoted tag (often K8s) |
| `last_seen` | UInt64 | no | Epoch ms UTC; refreshed on upsert |
| `valid_from` | UInt64 | yes | Epoch ms UTC; null = open start |
| `valid_to` | UInt64 | yes | Epoch ms UTC; null = open end |
| `version` | UInt32 | no | Monotonic per `entity_id` |

**Primary key (logical):** `(tenant, entity_id)` — tenant from Dest path.  
**Typical walk projection:** `entity_id`, `type` (defer promoted tags and clocks until filter / UI needs them).

### 2.1 Promoted tag catalog — `attr_catalog.v1`

| Tag column | When to set | Not for |
|------------|-------------|---------|
| `env` | Deploy environment (`rca-lab`, `prod`, …) | Free-form dump of all labels |
| `region` | Cloud / geo region when known | Nested region objects |
| `owner` | Team / owning service string | ACL documents |
| `namespace` | K8s / logical namespace when known | Arbitrary hierarchy trees |

**Versioning:** Adding or renaming a promoted tag is a **new catalog version** (e.g. `attr_catalog.v2`) and a columnar schema bump — not per-key DDL at runtime.

**Out of `attr_catalog.v1` (examples):** `aliases[]`, `monitored_via[]`, one-off inventory keys. Those stay on the wire/`files.v1` bag if needed for humans; they are **not** Vortex prune columns until promoted in a later catalog version.

---

## 3. Table `map_edges` (← `graph_edge.v1` at publish)

| Column | Arrow / Vortex DType | Nullable | Notes |
|--------|----------------------|----------|-------|
| `edge_id` | UInt64 | no | Snowflake; stable for upsert |
| `source_id` | Utf8 | no | = node `entity_id` |
| `target_id` | Utf8 | no | = node `entity_id` |
| `edge_type` | Utf8 (dict-encode friendly) | no | Fifteen SCREAMING Motadata names |
| `valid_from` | UInt64 | yes | Epoch ms UTC |
| `valid_to` | UInt64 | yes | Epoch ms UTC |
| `evidence_event_id` | UInt64 | no | Snowflake of proving event |

**Upsert key (logical):** `(tenant, source_id, edge_type, target_id)`.  
**Typical walk projection:** `source_id`, `target_id`, `edge_type` (defer `evidence_event_id`).

No tag / `metadata` column on edges.

`edge_type` closed set: `DEPENDS_ON`, `RUNS_ON`, `MOUNTS`, `CONNECTS_TO`, `BACKS`, `USES`, `HOSTED_ON`, `MEMBER_OF`, `PART_OF`, `ROUTES_THROUGH`, `AUTHENTICATES_VIA`, `MONITORED_BY`, `BACKED_UP_BY`, `CLUSTERED_WITH`, `COMMUNICATES_WITH`.

---

## 4. Wire ↔ physical (aligned 2026-09-30)

`graph_node.v1` / `graph_edge.v1` **JSON Schemas are flat** and match Vortex columns: promoted tags + **UInt64-as-JSON-integer** epoch ms. Publish no longer rewrites a nested `metadata` bag.

| Concern | Rule |
|---------|------|
| Clocks | JSON integers (epoch ms) ↔ Arrow/Vortex `UInt64` |
| Tags | Sibling fields `env` / `region` / `owner` / `namespace` only (`attr_catalog.v1`) |
| CI ids | Utf8 strings on wire and cold |
| Stream input | Still `writer_stream.v1` / lab `topo_update` — GraphWriter **builds** flat node/edge rows |

Ingest `ts` may arrive as ISO-8601 on the stream; GraphWriter converts to epoch ms before upsert.
---

## 5. Cold object naming (unchanged)

```text
map/<tenant>/snapshots/<version>/
  manifest.json
  nodes/part-00000.vortex
  edges/part-00000.vortex
map/<tenant>/latest.json
```

---

## 6. Lab construction (Rust)

```bash
cd pillar-ab-implementation/pillar-b/map-vortex
cargo test
cargo run --bin map_vortex_demo -- --demo /tmp/map-vortex-demo
```

See crate [`README.md`](../pillar-b/map-vortex/README.md).
