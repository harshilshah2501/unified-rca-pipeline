# Pillar B — Knowledge graph (owner package)

**Owner:** Harshil / Pillar B (entities + edges + GraphSnapshot)  
**Sibling:** [`../pillar-a/`](../pillar-a/) (percentiles / sketches)  
**Join:** [`../integration/`](../integration/) — optional **read-join** only (not an A∪B product merge)

A and B are **parallel writers** after Identity (E2). Pillar B owns the `map/` room. Pillar A owns `history/` sketches from `metric_sample` only — GraphWriter silent-skips those lines.

**Doc map:** [`docs/README.md`](./docs/README.md)

---

## Reading order

1. **This README** — I/O + admit + quick start  
2. [`docs/MAP_P1_FABRIC_EVAL.md`](./docs/MAP_P1_FABRIC_EVAL.md) — E1–E5 eval, terminology  
3. [`docs/Codebase-go-through.md`](./docs/Codebase-go-through.md) — how the code is wired  
4. [`poc/sample_estate/customer_checkout/SAMPLE_IO.md`](./poc/sample_estate/customer_checkout/SAMPLE_IO.md) — Case A/B goldens  
5. Run: `cd poc && make install && make test-all` (optional `make publish-map`)  
6. Hub visual: [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter)

**Increment lock:** P1 (E1–E5) for `map/` only. P2/P3 use-case map reads are the next increment.

---

## Quick start

```bash
cd pillar-b/poc
python3 -m venv .venv
make install
make test-all
make publish-map    # optional lab: bootstrap + topo stream → map/
```

Lab-only notes: [`poc/README.md`](./poc/README.md).

---

## Inputs / outputs (I/O)

| | Pillar B |
|--|----------|
| **Stage** | E3 Topology (parallel to E4 sketch writer) |
| **Room** | `map/` |
| **Input** | `ingest.v1` with `signal_class=topo_update` (and optional estate bootstrap), `identity.status=resolved` |
| **Rejects (DROP)** | unresolved / synthesized identity; never-CI types; unknown `relation` |
| **Silent skip (NOOP)** | Non-topo lines: `metric_sample`, `event`, `trace_span`, `anomaly`, … |
| **Phased map-NOOP** | Relation in the fifteen-name catalog but not wave-1 (e.g. `mounts`) — no write, usually not a DROP |
| **Output (WRITE → flush)** | `Dest.put("map", …)` → `graph_snapshot.json`, `nodes.jsonl`, `edges.jsonl` |
| **Logical keys** | Node `(tenant, ci_id)` · Edge `(tenant, edge_id)` · Snapshot `(tenant, version)` |
| **Encoding** | UTF-8 **JSON** / JSON Lines — [`../contracts/MAP_WRITE_READ_RECORD.md`](../contracts/MAP_WRITE_READ_RECORD.md) (slice SoT) |
| **Must not** | Write sketches into `map/`; put Alert / Incident / ticket / Change-as-CI on the snapshot |
| **Read helpers** | `load_snapshot(dest)`; `neighbors(ci_id)` over in-memory / loaded graph |

### Admit actions (hub language ↔ code)

**What “admit” means:** GraphWriter’s **per-line triage** of an incoming `ingest.v1` record — choose NOOP / WRITE / DROP (or phased skip). Not authentication, Collect schema validation, or a named E-stage. Fuller terminology: [`docs/MAP_P1_FABRIC_EVAL.md`](./docs/MAP_P1_FABRIC_EVAL.md).

| Hub action | Code path | Effect |
|------------|-----------|--------|
| **NOOP** | `signal_class != "topo_update"` → `continue` | No state change, no reject |
| **WRITE** | gate + `may_emit_vertex` + `classify_relation` → `emit` | Upsert node(s) + edge in `GraphState` |
| **DROP** | gate fail / never-CI / `unknown_relation` | Append `writer.rejects`; map unchanged |
| Phased NOOP | `classify_relation` → `skip` | Catalog relation, not wave-1 yet |

Wave-1 emit set: `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`.

Vortex / S3: same logical records later; PoC dest is **`files.v1`** only.

---

## Layout (PoC-minimal)

```text
pillar-b/
├── README.md
├── docs/                     ← PoC guides only (see docs/README.md)
├── contracts/schemas/        ← symlinks → ../contracts/schemas/ (SoT; required by tests)
├── references/               ← OPTIONAL product HTML library (not PoC SoT)
└── poc/                      ← code, sample estate, tests
```

Normative map write/read, reject codes, Gate B dest, and fabric Q&A live under the **slice** tree [`../contracts/`](../contracts/) — not duplicated here.

---

## PoC code spine (one line)

Estate bootstrap + resolved `topo_update` → GraphWriter → `GraphState` → flush → `map/` → optional E5 maintain → re-flush.  
Diagram + modules: [`docs/Codebase-go-through.md`](./docs/Codebase-go-through.md).

P1 proofs: `poc/graph/tests/unit/test_p1_map_fabric.py`.

---

## Related

- Post-E2 signal router: [`../E2_INPUT_FIXTURES.md`](../E2_INPUT_FIXTURES.md)  
- Map write/read (SoT): [`../contracts/MAP_WRITE_READ_RECORD.md`](../contracts/MAP_WRITE_READ_RECORD.md)  
- Fabric Q&A (SoT): [`../contracts/GRAPH_QNA.md`](../contracts/GRAPH_QNA.md)  
- Reject codes (SoT): [`../contracts/IDENTIFIED_STREAM_REJECT.md`](../contracts/IDENTIFIED_STREAM_REJECT.md)  
- Optional product briefs: [`references/README.md`](./references/README.md)
