# Map write / read record

- **Status:** Normative for Pillar B `map/`.
- **PoC encoding:** `files.v1` (UTF-8 JSON / JSON Lines).
- **Motadata dest design:** `vortex_s3.v1` (this file §6).
- **Tier:** Tier 2 implementer I/O (**I/O-3**) — [`docs/observeops/OUR_HLD_TIER1.md`](../../docs/observeops/OUR_HLD_TIER1.md).
- **Writer input:** [`../E2_INPUT_FIXTURES.md`](../E2_INPUT_FIXTURES.md) (**I/O-2**).
- **Room:** `map/` (Pillar B / ObserveOps E3 Topology).
- **Not in this PoC yet:** live Motadata Vortex cluster, protobuf codecs, or production S3 APIs (layout and APIs are still specified in §6 for implementers, including Rust).

**Same schema rule:** Vortex (in-memory / hot Arrays) and S3 (immutable cold objects) encode the **same** logical fields and keys. Do not invent a second node/edge schema when changing the physical product.

**Companion docs**

- [`../pillar-b/docs/MAP_VORTEX_S3_POC_PRIMER.md`](../pillar-b/docs/MAP_VORTEX_S3_POC_PRIMER.md) — start here for exploration
- [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md) — hot vs cold; admit gates; removal
- [`MAP_VORTEX_COLUMNAR_SCHEMA.md`](./MAP_VORTEX_COLUMNAR_SCHEMA.md) — locked columns
- [`schemas/`](./schemas/) — JSON Schemas
- [`GRAPH_NODE_EDGE_SAMPLES.md`](./GRAPH_NODE_EDGE_SAMPLES.md) — sample rows

Dest profile (`files.v1` vs `vortex_s3.v1`): this file §3 + §6 (former Gate B page is a stub).

### Document map

Short path: **primer → lifecycle → this file §6 → columnar schema → `map-vortex/`**.

| Hub doors |
|-----------|
| [docs index §4](../../docs/index.html) · [Fabric README](../../docs/fabric/README.md) · [Pillar B PoC hub](http://127.0.0.1:8765/pillar-b-poc-hub.html) |

---

## 1. Logical artifacts (what a “record” is)

| Artifact | Schema id | Shape |
|----------|-----------|--------|
| Configuration-item vertex | `graph_node.v1` | One JSON object (Motadata columns; **no `tenant`**) → columnar table **`map_nodes`** |
| Typed relationship | `graph_edge.v1` | One JSON object (Motadata columns; **no `tenant`**, no `discovered_via`) → columnar table **`map_edges`** |
| Packaged estate map | `graph_snapshot.v1` | One JSON object: `tenant`, `version`, `nodes[]`, `edges[]` — **not** a columnar Vortex table (PoC envelope) |
| Cold snapshot index | `map_snapshot_manifest.v1` | Lists `.vortex` part keys for one version — **not** a columnar table |

Logical identity keys (stable across dest profiles):

| Artifact | Logical key |
|----------|-------------|
| Node | `(Dest tenant, entity_id)` — tenant from path / snapshot envelope, not on the row |
| Edge | Upsert key `(source_id, edge_type, target_id)`; Motadata `edge_id` is a snowflake allocated once per upsert key |
| Snapshot | `(tenant, version)` for a packaged generation; PoC also exposes a convenience key `latest` via fixed filename (below) |

```text
ingest.v1 (tenant + ci_id) ──map──► node/edge (no tenant)
                                    ▲
Dest path poc/out/<tenant>/map/ ────┘
graph_snapshot.v1 still has tenant + version
sketch.v1 still has entity_id (join within tenant Dest)
```

Writers admit ingest lines only when **`identity.status = resolved`**. That gate is admit-time only — status is **not** stored on `graph_node.v1`.

---

## 2. Destination interface

```text
Dest.put(room, key, payload_bytes)
Dest.get(room, key) → bytes | None
Dest.list_keys(room) → list[str]
```

For Pillar B map writes, `room` is always `"map"`. Payload bytes are UTF-8 JSON (or JSONL).

---

## 3. PoC on-disk keys (`files.v1`)

Under `poc/out/<tenant>/map/`:

| Dest key | Format | Contents | Write mode (PoC) |
|----------|--------|----------|------------------|
| `graph_snapshot.json` | Pretty JSON document | Full `graph_snapshot.v1` | Overwrite on each publish |
| `nodes.jsonl` | JSON Lines | One full `graph_node.v1` per line | Overwrite on each publish |
| `edges.jsonl` | JSON Lines | One full `graph_edge.v1` per line | Overwrite on each publish |

Implemented by `publish_snapshot` / `load_snapshot` in `pillar-b/poc/graph/snapshot.py`.

**Read path (PoC):** prefer `Dest.get("map", "graph_snapshot.json")` → parse → validate `graph_snapshot_v1.schema.json`. JSONL files are convenient for inspection and incremental tooling; the snapshot document is the packaged read unit.

**Not a map key:** `history/change_facts.jsonl` lives in the **history** room when change facts are appended; it is optional and separate from Topology snapshot publish.

---

## 4. Envelope example (`graph_snapshot.v1`)

```json
{
  "schema_version": "graph_snapshot.v1",
  "tenant": "default",
  "version": "1",
  "nodes": [
    {
      "schema_version": "graph_node.v1",
      "entity_id": "checkout-api",
      "type": "service",
      "name": "checkout-api",
      "env": "rca-lab",
      "region": null,
      "owner": null,
      "namespace": null,
      "last_seen": 1787196600000,
      "valid_from": null,
      "valid_to": null,
      "version": 1
    }
  ],
  "edges": [
    {
      "schema_version": "graph_edge.v1",
      "edge_id": 7146828800000001,
      "source_id": "checkout-api",
      "target_id": "linux-server-app-01",
      "edge_type": "RUNS_ON",
      "valid_from": 1787196600000,
      "valid_to": null,
      "evidence_event_id": 7146828800000101
    }
  ]
}
```

Field name is **`version`** (string) on the snapshot. Do not use `snapshot_id`. Node `version` is a separate Motadata integer on each vertex.

---

## 5. Writer boundary mapping

[`graph_builder.py`](../pillar-b/poc/graph/graph_builder.py) is the single translator. **Do not** change `ingest.v1` field names.

| Ingest / bootstrap | Stored Motadata field |
|--------------------|------------------------|
| `ci_id` | node `entity_id` |
| `ci_type` (PascalCase) | node `type` (lowercase) |
| labels / tags | node `env` / `region` / `owner` / `namespace` (`attr_catalog.v1`) |
| `src_ci_id` / `dst_ci_id` | `source_id` / `target_id` |
| `relation` (snake_case) | `edge_type` (SCREAMING_SNAKE) |
| (none) | `edge_id` + `evidence_event_id` snowflakes |
| (none) | node `last_seen` + bump `version` on upsert |

Edge upsert: look up `(source_id, edge_type, target_id)`; reuse snowflake `edge_id` or allocate once. Same endpoints may hold **multiple** edges only when `edge_type` differs — see [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md) §4.

---

## 5.1 Hot mutate vs cold publish (summary)

Full teaching page: [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md).

| Concern | Lock |
|---------|------|
| `upsert_topo` / `write_topo_stream` | Mutate **hot** Arrays + adjacency only — no new cold `.vortex` per line |
| `publish_map` | New immutable cold parts + ObserveOps manifest + `latest` |
| `maintain_map` | Validity / freshness on clocks (`valid_from` / `valid_to`, stale policy) — **not** explicit admin delete |
| Explicit retire / remove | Separate verb; node retire **cascades** close of incident active edges; then publish |
| `graph_snapshot.v1` | Packaged PoC read unit — not a third columnar table |

---

## 6. Motadata dest: Vortex columnar + S3 (immutable `.vortex` objects)

- **Profile name:** `vortex_s3.v1` (design locked; not wired in the Python PoC — PoC stays `files.v1`).
- **Vortex meaning here:** the compressed columnar stack (DType · Array · Encoding · Layout · `.vortex` / VTXF).
- **Owner notes:** [`pillar-b/docs/vortex_engineering_mystery_revised_v2.pdf`](../pillar-b/docs/vortex_engineering_mystery_revised_v2.pdf)
- **Upstream concepts:** [docs.vortex.dev/concepts](https://docs.vortex.dev/concepts/)
- **Visual companion:** [`docs/fabric/vortex-s3-interaction.html`](../../docs/fabric/vortex-s3-interaction.html) (rooms vs temperature)

**Axes (do not confuse)**

- **Rooms** (`map/` vs `history/`) are **content**.
- **S3** holds durable `.vortex` objects (cold).
- **Process memory** holds Vortex **Arrays** plus an optional **adjacency index** for walks (hot).
- Same logical row kinds: `graph_node.v1`, `graph_edge.v1`. Do not invent a second node/edge schema.

**Case rule (Vortex walkthrough):** prune early → retrieve selectively → compute compactly → materialize late.

### 6.1 What we store — columns (hybrid spine)

Two columnar tables (Struct layout = one physical column stream per spine field).

- **Normative columns + Arrow / Vortex dtypes:** [`MAP_VORTEX_COLUMNAR_SCHEMA.md`](./MAP_VORTEX_COLUMNAR_SCHEMA.md)
- **Implementation:** Rust crate [`pillar-b/map-vortex/`](../pillar-b/map-vortex/) (`map_vortex`)

| Table | Spine columns (strict) | Promoted / flexible |
|-------|------------------------|---------------------|
| **Nodes** (`map_nodes`) | `entity_id`, `type`, `name`, `last_seen` (**UInt64** epoch ms), `valid_from` / `valid_to` (**UInt64** epoch ms), `version` | Closed **`attr_catalog.v1`** columns: `env`, `region`, `owner`, `namespace` (nullable Utf8). **No** JSON `metadata` bag on cold Vortex |
| **Edges** (`map_edges`) | `edge_id`, `source_id`, `target_id`, `edge_type`, `valid_from` / `valid_to` (**UInt64**), `evidence_event_id` | extras only if a later catalog promotes them |

Wire / `files.v1` lab JSON uses the **same flat fields** (epoch-ms integers + promoted tags). Stream `ts` may still be ISO on ingest lines; GraphWriter converts before upsert ([`MAP_VORTEX_COLUMNAR_SCHEMA.md`](./MAP_VORTEX_COLUMNAR_SCHEMA.md) §4).

### 6.2 Roles

| Layer | Role for `map/` |
|-------|-----------------|
| **Hot (process)** | Vortex **Arrays** for current node/edge tables (may stay encoded). Application **adjacency index** for `neighbors` / walks (built from projected edge spine columns). Mutate on admitted WRITE. |
| **Cold (S3)** | Immutable `.vortex` files for nodes and edges per snapshot `version`, plus ObserveOps **snapshot footer** (`manifest.json` + `latest.json`). Rebuild hot Arrays + adjacency after restart. |

Mutate ≠ persist. Stream upserts update hot Arrays / adjacency. `publish_map` writes **new** cold objects (never patch an old `.vortex` file).

### 6.3 Physical organization inside a `.vortex` file

Default Vortex layout strategy (walkthrough): **Struct → Zoned → Chunked → Compressor → Buffered → Flat**.

| Layer | Job for our map tables |
|-------|-------------------------|
| **Struct** | Separate spine columns (`entity_id` vs `env`, `source_id` vs `edge_type`, …) so walks project only needed columns |
| **Zoned** | Per-zone statistics for predicate pruning (e.g. skip zones that cannot contain `edge_type = RUNS_ON` or `last_seen` outside a window) |
| **Chunked** | Manageable pieces (~2 MB uncompressed default in Vortex docs) — access granularity |
| **Compressor / Encoding** | Dictionary / bit-pack / … on repetitive columns (`type`, `edge_type`, `env`, …) while keeping Arrays computable |
| **Flat + segments** | Serialized array chunks as data segments |

A walk that only needs `(source_id, target_id, edge_type)` should **not** pull promoted tags or `evidence_event_id` until materialization needs them.

### 6.4 Metadata / footer — two levels (do not confuse)

There are **two** “footer” stories: (A) inside each Vortex file, (B) ObserveOps snapshot index across files.

#### A. Inside each `.vortex` file (Vortex file format)

A Vortex file is **not** “read all bytes.” Structure (simplified from the walkthrough / [file format](https://docs.vortex.dev/concepts/file-format)):

```text
┌─────────────────────────────────────────────┐
│  DATA SEGMENTS                              │
│  encoded array buffers / column chunks      │
├─────────────────────────────────────────────┤
│  METADATA (layout tree)                     │
│  DType + Layout hierarchy + statistics      │
│  + segment byte locations / encodings       │
├─────────────────────────────────────────────┤
│  POSTSCRIPT (footer pointer)                │
│  points to metadata; magic VTXF             │
└─────────────────────────────────────────────┘
```

| Piece | Who writes it | Who reads it | Mutate? |
|-------|---------------|--------------|---------|
| **Data segments** | Vortex writer on `publish_map` | Scan after pruning says “fetch this segment” | No — immutable object |
| **Layout metadata** | Same write (schema/DType, zone stats, encodings, segment offsets) | Open file → reconstruct layout tree **before** bulk I/O | No |
| **Postscript** | Trailer of the file | First seek on open: find metadata location + `VTXF` magic | No |

**Open path:** read postscript → load metadata/layout tree → **project** columns + **prune** zones using statistics → retrieve only surviving segments → keep **encoded Arrays** in compute when possible → **late-materialize** full values only for survivors.

We do **not** hand-edit Vortex footers. The Vortex writer owns segment + layout + postscript. ObserveOps only decides *which* `.vortex` objects exist at which snapshot version.

#### B. ObserveOps snapshot footer (across objects on S3)

Vortex’s internal footer does not list “all map files for tenant X.” That is our Dest-level index:

| Object | Role |
|--------|------|
| `map/<tenant>/snapshots/<version>/manifest.json` | **Snapshot footer** — lists node/edge `.vortex` object keys, counts, version (`map_snapshot_manifest.v1`) |
| `map/<tenant>/latest.json` | Tiny pointer `{ "version": "…" }` — full PUT overwrite (still a new object write, not an in-place edit of an old snapshot) |

```text
map/<tenant>/snapshots/<version>/
  manifest.json              # ObserveOps footer (our schema)
  nodes/part-00000.vortex    # each file has its own VTXF postscript + layout metadata
  nodes/part-NNNNN.vortex
  edges/part-00000.vortex
  edges/part-NNNNN.vortex
map/<tenant>/latest.json
```

| Concern | Vortex file metadata | ObserveOps manifest |
|---------|----------------------|---------------------|
| Column DTypes / encodings / zone stats | Yes | No |
| Which parts belong to snapshot `version` | No | Yes |
| Crash-safe “publish complete?” | File is complete when postscript is valid | Version is readable only when `manifest.json` exists |
| Diagnose walks | After load into hot Arrays | Used only by `load_map` / rebuild |

**Publish order (footer last):** write all `.vortex` parts → write `manifest.json` → write `latest.json`. Readers ignore a version without a complete manifest. Never rewrite an old part to “fix metadata.”

Lab may still use JSONL parts; production Motadata path targets `.vortex` with the same logical columns and the same ObserveOps manifest.

### 6.5 End-to-end write

Lifecycle detail: [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md).

1. **Admit** (complete claim → resolved → CI on map → catalog + triplet). [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md). Outcome: NOOP / WRITE / DROP.
2. **Mutate hot** — under WRITE: new node+edge, new edge only, or refresh existing upsert key; under maintain / explicit retire: validity or cascade close. Upsert into node/edge Arrays + refresh adjacency. **No S3 / cold `.vortex` call.**
3. **Persist (`publish_map`)** — new `version`; build Arrow/columnar tables for nodes and edges; Vortex write each part (segments + layout metadata + postscript); PUT `manifest.json`; PUT `latest.json`; invalidate version-keyed memos.
4. Never patch an old `.vortex` or an old manifest. Next checkpoint = new version.

### 6.6 End-to-end read

1. **`load_map`** — GET `latest.json` → GET `manifest.json` → open each listed `.vortex` (postscript → layout) → selective scan into hot Arrays → rebuild adjacency from edge spine columns.
2. **Walk** — `neighbors` / paths against adjacency (+ optional query memo keyed by snapshot `version`). Project only needed columns when refreshing from cold.
3. **WorkingSet** — bounded per-case neighborhood for Scope/Localize.
4. Diagnose does **not** open S3 per hop; S3 is rebuild / time-travel / audit.

### 6.7 Dest façade

```text
Dest.put(room, key, payload_bytes)
Dest.get(room, key) → bytes | None
Dest.list_keys(room) → list[str]
```

| API | Behavior |
|-----|----------|
| `upsert_topo` / `write_topo_stream` | Admit + mutate **hot** Arrays / adjacency (not a cold `.vortex` PUT) |
| `maintain_map(as_of)` | Validity / freshness (expire `valid_to`, stale policy, declared marks) — not explicit admin delete |
| Explicit retire / remove *(product lock; wire TBD)* | Close edge or node; node retire cascades incident active edges; then publish |
| `publish_map(tenant) → version` | New `.vortex` parts + ObserveOps manifest + `latest` |
| `load_map(tenant, version?)` | Manifest-driven rebuild from S3 |
| `neighbors` / walks | Hot adjacency after load |

### 6.8 Read-cache ladder

| Layer | Caches | Invalidate |
|-------|--------|------------|
| **L1 hot Arrays + adjacency** | Current estate walk surface | Restart → `load_map`; newer published version → reload |
| **L2 WorkingSet** | Bounded neighborhood for one case | Case ends / hop budget changes |
| **L3 query memo (optional)** | Recent `neighbors(…)` by `(tenant, version, …)` | Snapshot `version` bump |
| **Pointer** | `latest` → version | After successful `latest.json` PUT |
| **Layout metadata cache (optional)** | Parsed Vortex postscript/layout for open files | Object replaced (new version path) — never stale in-place footer |

Rules: S3 is not a diagnose cache; WorkingSet stays capped; prefer invalidate-on-publish for topology.

### 6.9 Schema — required (especially for Rust)

Logical JSON Schemas under [`schemas/`](./schemas/) and Vortex **physical DTypes** share the flat lock in [`MAP_VORTEX_COLUMNAR_SCHEMA.md`](./MAP_VORTEX_COLUMNAR_SCHEMA.md) (UInt64 clocks + promoted tags).

| Schema | Job |
|--------|-----|
| `graph_node.v1` / `graph_edge.v1` | Logical row / column set |
| `map_snapshot_manifest.v1` | ObserveOps snapshot footer across `.vortex` parts |
| `graph_snapshot.v1` | Optional packaged PoC view (envelope — **not** a columnar table) |
| `ingest.v1` / `writer_stream.v1` | Admit input |
| Vortex file DType / Layout | Physical; owned by Vortex writer — must encode the same spine |

### 6.10 Rust implementation action items

Crate start: [`pillar-b/map-vortex/`](../pillar-b/map-vortex/) — see [`IMPLEMENTATION.md`](../pillar-b/map-vortex/IMPLEMENTATION.md) for phase status.

1. **Schemas → types** — `serde` for node/edge/manifest (done); CI validate against JSON Schema (remaining).
2. **`Dest` trait** — FileDest + S3Dest (`put`/`get`/`list_keys`) — Phase D.
3. **Hot store** — `HotMap` upsert done; columnar Arrays + adjacency for walks — Phase C.
4. **Admit** — identity, CI qualify, fifteen relations, triplet allowlist — **done** (`admit`, `ci_qualify`).
5. **Publish** — parts → `manifest.json` → `latest.json` — **done**; incomplete-publish test — remaining.
6. **Load** — open Vortex → Arrow batches — **done**; project spine on load + adjacency rebuild — Phase C.
7. **WorkingSet + cache policy** — version-keyed invalidation — Phase D/E.
8. **Integration tests** — publish/load + admit/hot P1-shaped — **partial**; full estate + retire cascade — remaining.
9. **Defer** — Motadata cluster wiring; treat [docs.vortex.dev](https://docs.vortex.dev/) as authoritative for API/layout defaults as versions evolve.
10. **Explicit retire wire** — writer-stream or Dest admin path separate from `maintain_map` (product lock in lifecycle doc §5).

### 6.11 Lab note

- PoC `files.v1` (JSON / JSONL under `pillar-b/poc/`) still proves logical admit / GraphWriter records.
- Column layout for Motadata parts: [`MAP_VORTEX_COLUMNAR_SCHEMA.md`](./MAP_VORTEX_COLUMNAR_SCHEMA.md).
- Rust builders + Vortex write: [`pillar-b/map-vortex/`](../pillar-b/map-vortex/).
- Hot vs cold lifecycle: [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md).
- `vortex_s3.v1` targets `.vortex` parts + ObserveOps manifest.

---

## 7. Independence

- Pillar B never writes sketch rows into `map/`.  
- Pillar A never writes nodes/edges into `history/` sketches.  
- A and B are **parallel writers** after Identity; diagnose **read-joins** by Dest `tenant` + map `entity_id` ≡ sketch `entity_id` (ingest still says `ci_id`) — not a merged writer product.

---

## 8. Acceptance checks

1. Every published node validates `graph_node_v1.schema.json` (Motadata fields; no `tenant`).  
2. Every published edge validates `graph_edge_v1.schema.json` (snowflake ids; no `discovered_via`).  
3. Envelope validates `graph_snapshot_v1.schema.json` (tenant on envelope) when using the packaged PoC key.  
4. Cold checkpoint validates `map_snapshot_manifest_v1.schema.json` when using `vortex_s3.v1` layout.  
5. `load_snapshot(dest)` / `load_map` round-trips publish.  
6. No Alert / Incident / ticket / Change-as-CI / metric / trace vertices on the snapshot.  
8. Neighbor walks use `source_id` / `target_id` against Vortex (or PoC in-memory state), not per-hop S3.  
9. Hot upsert never writes cold `.vortex`; only `publish_map` does.  
10. Node retire closes all active incident edges before / with the same hot mutation that removes the node from the live walk surface.
