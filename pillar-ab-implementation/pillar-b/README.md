# Pillar B — Knowledge graph (owner package)

**Owner:** Harshil / Pillar B (entities + edges + GraphSnapshot)  
**Sibling:** [`../pillar-a/`](../pillar-a/) (percentiles / sketches)  
**Join:** [`../integration/`](../integration/) — optional **read-join** only (not an A∪B product merge)

A and B are **parallel writers** after Identity (E2). Pillar B owns the `map/` room.

---

## Quick start

```bash
cd pillar-b/poc
python3 -m venv .venv
make install
make test-all
```

Expected: shared + graph unit tests pass (no sketch package import).

---

## Inputs / outputs (I/O)

| | Pillar B |
|--|----------|
| **Stage** | E3 Topology (parallel to E4 sketch writer) |
| **Room** | `map/` |
| **Input** | `ingest.v1` with `signal_class=topo_update` (and seed topology), `identity.status=resolved` |
| **Rejects** | unresolved / synthesized identity; never-CI types; unknown `relation` |
| **Silent skip** | Non-topo lines (`metric_sample`, …) |
| **Output** | `Dest.put("map", …)` → `graph_snapshot.json`, `nodes.jsonl`, `edges.jsonl` |
| **Logical keys** | Node `(tenant, ci_id)` · Edge `(tenant, edge_id)` · Snapshot `(tenant, version)` |
| **Encoding** | UTF-8 **JSON** / JSON Lines — see [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md) |
| **Must not** | Write sketches into `map/`; put Alert / Incident / ticket / Change-as-CI on the snapshot |
| **Read helpers** | `load_snapshot(dest)`; `neighbors(ci_id)` over in-memory / loaded graph |

Optional later: `history/change_facts.jsonl` via change-fact helper — **not** part of `publish_snapshot`.

Vortex / S3: same logical records later; PoC dest is **`files.v1`** only.

---

## Layout

```text
pillar-b/
├── README.md
├── contracts/
│   ├── schemas/
│   │   ├── ingest_v1.schema.json
│   │   ├── graph_node_v1.schema.json
│   │   ├── graph_edge_v1.schema.json
│   │   ├── graph_snapshot_v1.schema.json
│   │   └── change_fact_v1.schema.json
│   ├── MAP_WRITE_READ_RECORD.md   ← normative map JSON keys + encoding
│   ├── GATE_B_DEST_PROFILE.md
│   └── IDENTIFIED_STREAM_REJECT.md
├── docs/   ← symlinks to shared brief, samples, GRAPH_QNA, map write/read
└── poc/
    ├── ab_shared/     ← identity gate, dest, ingest, schema
    ├── graph/         ← qualify, edges, builder, snapshot, neighbors
    ├── fixtures/lab_checkout/
    ├── Makefile
    └── requirements.txt
```

---

## PoC code spine

```text
ingest.v1 topo_update (identity resolved) + topology.seed.json
  → ci_qualify / edge_catalog / provenance
  → graph_builder
  → build_snapshot → validate graph_snapshot.v1
  → publish_snapshot → Dest map/{graph_snapshot.json,nodes.jsonl,edges.jsonl}
  → load_snapshot / neighbors
```

There is not yet a `make flush` / GraphWriter CLI (planned harden). Tests call `build_snapshot` + `publish_snapshot` directly.

---

## Related

- Map write/read: [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md)  
- Fabric Q&A: [`docs/GRAPH_QNA.md`](./docs/GRAPH_QNA.md)  
- Raw / Identity LUT discussion: [`../discussion/04-raw-data-identity-lut-open-questions.md`](../discussion/04-raw-data-identity-lut-open-questions.md)  
- Implementation plan: [`../IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md)
