# Map write / read record (`files.v1` PoC)

**Status:** Normative for the Pillar A/B PoC destination profile.  
**Room:** `map/` (Pillar B / ObserveOps E3 Topology).  
**Encoding:** UTF-8 **JSON** (pretty document or JSON Lines).  
**Not in this PoC:** Motadata Vortex DDL, protobuf codecs, or live S3 APIs.

Vortex (hot) and S3 (cold) are **later encodings of the same logical fields and keys**. Changing the physical product must not invent a second node/edge schema.

Companion: [`GATE_B_DEST_PROFILE.md`](./GATE_B_DEST_PROFILE.md) · schemas under [`schemas/`](./schemas/) · samples [`GRAPH_NODE_EDGE_SAMPLES.md`](./GRAPH_NODE_EDGE_SAMPLES.md).

---

## 1. Logical artifacts (what a “record” is)

| Artifact | Schema id | Shape |
|----------|-----------|--------|
| Configuration-item vertex | `graph_node.v1` | One JSON object |
| Typed relationship | `graph_edge.v1` | One JSON object |
| Packaged estate map | `graph_snapshot.v1` | One JSON object: `tenant`, `version`, `nodes[]`, `edges[]` |

Logical identity keys (stable across dest profiles):

| Artifact | Logical key |
|----------|-------------|
| Node | `(tenant, ci_id)` |
| Edge | `(tenant, edge_id)` |
| Snapshot | `(tenant, version)` for a packaged generation; PoC also exposes a convenience key `latest` via fixed filename (below) |

Writers admit **`identity_status = resolved`** nodes only onto the production snapshot (same rule as Pillar A’s resolved-only sketch admit).

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
  "nodes": [ { "schema_version": "graph_node.v1", "tenant": "default", "ci_id": "checkout-api", "ci_type": "Service", "ci_name": "checkout-api", "identity_status": "resolved" } ],
  "edges": [ { "schema_version": "graph_edge.v1", "tenant": "default", "edge_id": "e1", "src_ci_id": "checkout-api", "dst_ci_id": "linux-server-app-01", "relation": "runs_on" } ]
}
```

Field name is **`version`** (string). Do not use `snapshot_id` in PoC or schema — older samples that used `snapshot_id` were illustrative and are obsolete.

---

## 5. Later profiles (same records, different temperature)

| Profile | What changes | What stays |
|---------|--------------|------------|
| **Vortex** (hot) | Physical columns / protobuf / query engine | Same logical JSON fields and keys |
| **S3** (cold) | Object layout, partition prefixes, compression | Same logical objects (often gzip JSON or frozen snapshot blobs) |
| **Lab dual-home** (optional stub) | Two folders standing in for hot vs cold | Still JSON payloads via `Dest` |

Rooms (`map/` vs `history/`) are **content**. Vortex vs S3 is **temperature**. Both rooms can live hot and age cold.

---

## 6. Independence

- Pillar B never writes sketch rows into `map/`.  
- Pillar A never writes nodes/edges into `history/` sketches.  
- A and B are **parallel writers** after Identity; diagnose **read-joins** by `tenant` + `ci_id` ≡ `entity_id` — not a merged writer product.

---

## 7. Acceptance checks

1. Every published node validates `graph_node_v1.schema.json`.  
2. Every published edge validates `graph_edge_v1.schema.json`.  
3. Envelope validates `graph_snapshot_v1.schema.json`.  
4. `load_snapshot(dest)` round-trips `publish_snapshot`.  
5. No Alert / Incident / ticket / Change-as-CI vertices on the snapshot.
