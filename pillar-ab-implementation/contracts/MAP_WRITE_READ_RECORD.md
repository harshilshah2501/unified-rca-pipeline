# Map write / read record (`files.v1` PoC)

**Status:** Normative for the Pillar A/B PoC destination profile (Motadata-aligned node/edge rows).  
**Tier:** Tier 2 implementer I/O (**I/O-3**) — see [`docs/observeops/OUR_HLD_TIER1.md`](../../docs/observeops/OUR_HLD_TIER1.md). Pillar writer **input**: [`../E2_INPUT_FIXTURES.md`](../E2_INPUT_FIXTURES.md) (**I/O-2**).
**Room:** `map/` (Pillar B / ObserveOps E3 Topology).  
**Encoding:** UTF-8 **JSON** (pretty document or JSON Lines).  
**Not in this PoC:** Motadata Vortex DDL, protobuf codecs, or live S3 APIs.

Vortex (hot) and S3 (cold) are **later encodings of the same logical fields and keys**. Changing the physical product must not invent a second node/edge schema.

Companion: [`GATE_B_DEST_PROFILE.md`](./GATE_B_DEST_PROFILE.md) · schemas under [`schemas/`](./schemas/) · samples [`GRAPH_NODE_EDGE_SAMPLES.md`](./GRAPH_NODE_EDGE_SAMPLES.md).

---

## 1. Logical artifacts (what a “record” is)

| Artifact | Schema id | Shape |
|----------|-----------|--------|
| Configuration-item vertex | `graph_node.v1` | One JSON object (Motadata columns; **no `tenant`**) |
| Typed relationship | `graph_edge.v1` | One JSON object (Motadata columns; **no `tenant`**, no `discovered_via`) |
| Packaged estate map | `graph_snapshot.v1` | One JSON object: `tenant`, `version`, `nodes[]`, `edges[]` |

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
      "metadata": "{\"env\":\"rca-lab\"}",
      "last_seen": "2026-08-20T03:30:00Z",
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
      "valid_from": "2026-08-20T03:30:00Z",
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
| labels / tags | node `metadata` (JSON string) |
| `src_ci_id` / `dst_ci_id` | `source_id` / `target_id` |
| `relation` (snake_case) | `edge_type` (SCREAMING_SNAKE) |
| (none) | `edge_id` + `evidence_event_id` snowflakes |
| (none) | node `last_seen` + bump `version` on upsert |

Edge upsert: look up `(source_id, edge_type, target_id)`; reuse snowflake `edge_id` or allocate once.

---

## 6. Later profiles (same records, different temperature)

| Profile | What changes | What stays |
|---------|--------------|------------|
| **Vortex** (hot) | Physical columns / protobuf / query engine | Same logical JSON fields and keys |
| **S3** (cold) | Object layout, partition prefixes, compression | Same logical objects (often gzip JSON or frozen snapshot blobs) |
| **Lab dual-home** (optional stub) | Two folders standing in for hot vs cold | Still JSON payloads via `Dest` |

Rooms (`map/` vs `history/`) are **content**. Vortex vs S3 is **temperature**. Both rooms can live hot and age cold.

---

## 7. Independence

- Pillar B never writes sketch rows into `map/`.  
- Pillar A never writes nodes/edges into `history/` sketches.  
- A and B are **parallel writers** after Identity; diagnose **read-joins** by Dest `tenant` + map `entity_id` ≡ sketch `entity_id` (ingest still says `ci_id`) — not a merged writer product.

---

## 8. Acceptance checks

1. Every published node validates `graph_node_v1.schema.json` (Motadata fields; no `tenant`).  
2. Every published edge validates `graph_edge_v1.schema.json` (snowflake ids; no `discovered_via`).  
3. Envelope validates `graph_snapshot_v1.schema.json` (tenant on envelope).  
4. `load_snapshot(dest)` round-trips `publish_snapshot`.  
5. No Alert / Incident / ticket / Change-as-CI / metric / trace vertices on the snapshot.  
6. Neighbor walks use `source_id` / `target_id`.
