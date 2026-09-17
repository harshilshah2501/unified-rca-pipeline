# Pillar B — Knowledge graph (owner package)

**Owner:** Harshil / Pillar B (entities + edges + GraphSnapshot)  
**Sibling:** [`../pillar-a/`](../pillar-a/) (percentiles / sketches)  
**Join:** [`../integration/`](../integration/) — optional **read-join** only (not an A∪B product merge)

A and B are **parallel writers** after Identity (E2). Pillar B owns the `map/` room. Pillar A owns `history/` sketches from `metric_sample` only — GraphWriter silent-skips those lines.

---

## Reading order

1. This README (I/O + spine)  
2. Hub walkthrough: [`http://127.0.0.1:8765/graphwriter-io-walkthrough.html`](http://127.0.0.1:8765/graphwriter-io-walkthrough.html) (NOOP / WRITE / DROP)  
3. Post-E2 ingest map: [`../E2_INPUT_FIXTURES.md`](../E2_INPUT_FIXTURES.md)  
4. Map output contract: [`../contracts/MAP_WRITE_READ_RECORD.md`](../contracts/MAP_WRITE_READ_RECORD.md)  
5. Lab expected vs actual: [`poc/fixtures/lab_checkout/SAMPLE_IO.md`](./poc/fixtures/lab_checkout/SAMPLE_IO.md)  
6. Run: `cd poc && make install && make test-all` (optional `make flush`)  
7. Deeper fabric: [`docs/GRAPH_QNA.md`](./docs/GRAPH_QNA.md) · product briefs: [`references/README.md`](./references/README.md)

---

## Quick start

```bash
cd pillar-b/poc
python3 -m venv .venv
make install
make test-all
make flush    # optional lab: seed + topo stream → map/
```

Expected: shared + graph unit tests pass (no sketch package import).

---

## Inputs / outputs (I/O)

| | Pillar B |
|--|----------|
| **Stage** | E3 Topology (parallel to E4 sketch writer) |
| **Room** | `map/` |
| **Input** | `ingest.v1` with `signal_class=topo_update` (and seed topology), `identity.status=resolved` |
| **Rejects (DROP)** | unresolved / synthesized identity; never-CI types; unknown `relation` |
| **Silent skip (NOOP)** | Non-topo lines: `metric_sample`, `event`, `trace_span`, `anomaly`, … |
| **Phased map-NOOP** | Relation in the fifteen-name catalog but not wave-1 (e.g. `mounts`) — no write, usually not a DROP |
| **Output (WRITE → flush)** | `Dest.put("map", …)` → `graph_snapshot.json`, `nodes.jsonl`, `edges.jsonl` |
| **Logical keys** | Node `(tenant, ci_id)` · Edge `(tenant, edge_id)` · Snapshot `(tenant, version)` |
| **Encoding** | UTF-8 **JSON** / JSON Lines — see [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md) |
| **Must not** | Write sketches into `map/`; put Alert / Incident / ticket / Change-as-CI on the snapshot |
| **Read helpers** | `load_snapshot(dest)`; `neighbors(ci_id)` over in-memory / loaded graph |

### Admit actions (hub language ↔ code)

| Hub action | Code path | Effect |
|------------|-----------|--------|
| **NOOP** | `signal_class != "topo_update"` → `continue` | No state change, no reject |
| **WRITE** | gate + `may_emit_vertex` + `classify_relation` → `emit` | Upsert node(s) + edge in `GraphState` |
| **DROP** | gate fail / never-CI / `unknown_relation` | Append `writer.rejects`; map unchanged |
| Phased NOOP | `classify_relation` → `skip` | Catalog relation, not wave-1 yet |

Wave-1 emit set: `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`.

Optional later: `history/change_facts.jsonl` via change-fact helper — **not** part of `publish_snapshot`.

Vortex / S3: same logical records later; PoC dest is **`files.v1`** only.

---

## Layout

```text
pillar-b/
├── README.md
├── docs/
│   ├── graphwriter-io-walkthrough.html  ← symlink → ../../../docs/fabric/ (hub Site tab)
│   └── GRAPH_*.md / MAP_*               ← symlinks to shared contracts
├── references/   ← Motadata OneOps / Fusion SaaS HTML briefs (product; not PoC SoT)
│   └── README.md
├── contracts/
│   ├── schemas/                 ← symlinks → ../../contracts/schemas/ (SoT)
│   ├── MAP_WRITE_READ_RECORD.md
│   ├── GATE_B_DEST_PROFILE.md
│   └── IDENTIFIED_STREAM_REJECT.md
└── poc/
    ├── ab_shared/     ← identity gate, dest, ingest, schema
    ├── graph/         ← qualify, edges, builder, snapshot, graph_writer, maintain, neighbors
    ├── fixtures/lab_checkout/
    ├── Makefile
    └── requirements.txt
```

---

## PoC code spine

```text
ingest.v1 topo_update (identity resolved) + topology.seed.json
  → GraphWriter (ci_qualify / edge_catalog / provenance / graph_builder)
  → build_snapshot → validate graph_snapshot.v1
  → publish_snapshot → Dest map/{graph_snapshot.json,nodes.jsonl,edges.jsonl}
  → load_snapshot / neighbors
  → maintain_graph_validity (E5 stub: expire valid_to, drop stale corroborating)
```

Lab CLI: `make flush` or `python -m graph.cli_flush` (topo-only `fixtures/lab_checkout/stream.resolved.jsonl`).  
Mixed metric + topo tape lives under `integration/fixtures/lab_checkout/` for read-join only.

---

## Related

- GraphWriter I/O walkthrough: [`docs/graphwriter-io-walkthrough.html`](./docs/graphwriter-io-walkthrough.html) → [`:8765/graphwriter-io-walkthrough.html`](http://127.0.0.1:8765/graphwriter-io-walkthrough.html)  
- Post-E2 fixtures (what A and B consume): [`../E2_INPUT_FIXTURES.md`](../E2_INPUT_FIXTURES.md)  
- Lab SAMPLE_IO: [`poc/fixtures/lab_checkout/SAMPLE_IO.md`](./poc/fixtures/lab_checkout/SAMPLE_IO.md)  
- Product references (OneOps / Fusion HTML briefs): [`references/README.md`](./references/README.md)  
- Map write/read (SoT): [`../contracts/MAP_WRITE_READ_RECORD.md`](../contracts/MAP_WRITE_READ_RECORD.md)  
- Fabric Q&A: [`docs/GRAPH_QNA.md`](./docs/GRAPH_QNA.md)  
- Reject codes: [`contracts/IDENTIFIED_STREAM_REJECT.md`](./contracts/IDENTIFIED_STREAM_REJECT.md)  
- Raw / Identity LUT discussion: [`../discussion/04-raw-data-identity-lut-open-questions.md`](../discussion/04-raw-data-identity-lut-open-questions.md)  
- Implementation plan: [`../IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md)
