# Pillar B — Knowledge graph (owner package)

**Owner:** Harshil / Pillar B (entities + edges + GraphSnapshot)  
**Sibling:** [`../pillar-a/`](../pillar-a/) (percentiles / sketches)  
**Join:** [`../integration/`](../integration/) — optional **read-join** only (not an A∪B product merge)

A and B are **parallel writers** after Identity (E2). Pillar B owns the `map/` room. Pillar A owns `history/` sketches from `metric_sample` only — GraphWriter silent-skips those lines.

**This PoC has two use cases only:** (1) **build + maintain** the knowledge graph, (2) **walk-through** a published `map/`. Detect / Curate / Identify / Package / sketches are assumed or stubbed. Framing lives on the [Pillar B PoC hub](../../docs/fabric/pillar-b-poc-hub.html) ([`:8765/pillar-b-poc-hub.html`](http://127.0.0.1:8765/pillar-b-poc-hub.html)); optional Cursor canvas beside chat.

**Doc map:** [`docs/README.md`](./docs/README.md) · **Team walkthrough:** [`docs/TEAM_WALKTHROUGH.md`](./docs/TEAM_WALKTHROUGH.md)

---

## Reading order

1. **This README** — I/O + admit + quick start  
2. [`docs/TEAM_WALKTHROUGH.md`](./docs/TEAM_WALKTHROUGH.md) — team demo (fact_kind, admit, run)  
3. [Pillar B PoC hub](../../docs/fabric/pillar-b-poc-hub.html) — what is in vs stubbed (two use cases; `:8765/pillar-b-poc-hub.html`)  
4. [`docs/MAP_P1_FABRIC_EVAL.md`](./docs/MAP_P1_FABRIC_EVAL.md) — build/maintain + walk eval  
5. [`docs/Codebase-go-through.md`](./docs/Codebase-go-through.md) — how the code is wired  
6. [`poc/sample_estate/customer_checkout/SAMPLE_IO.md`](./poc/sample_estate/customer_checkout/SAMPLE_IO.md) — Case A/B goldens  
7. Run: `cd poc && make install && make test-all` (optional `make publish-map`)  
8. Hub visual: [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter)

**Focus lock:** knowledge graph build/maintain + walk. Case-path modules under `case_path/` are **stubs/harnesses** that drive walks, not the PoC mission.

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
| **Input** | `ingest.v1` with `fact_kind=topo_update` (and optional estate bootstrap), `identity.status=resolved` |
| **Rejects (DROP)** | unresolved / synthesized identity; never-CI types; unknown `relation`; missing endpoint type; illegal triplet |
| **Silent skip (NOOP)** | Non-topo lines: `metric_sample`, `event`, `trace_span`, `anomaly`, … |
| **Output (WRITE → flush)** | `Dest.put("map", …)` → `graph_snapshot.json`, `nodes.jsonl`, `edges.jsonl` |
| **Logical keys** | Node `(tenant, ci_id)` · Edge `(tenant, edge_id)` · Snapshot `(tenant, version)` |
| **Encoding** | UTF-8 **JSON** / JSON Lines — [`../contracts/MAP_WRITE_READ_RECORD.md`](../contracts/MAP_WRITE_READ_RECORD.md) (slice SoT) |
| **Must not** | Write sketches into `map/`; put Alert / Incident / ticket / Change-as-CI on the snapshot |
| **Read helpers** | `load_snapshot(dest)`; `neighbors` / `reachable_ci_ids` / `find_paths` (Part B walk — see [`docs/MAP_P1_FABRIC_EVAL.md`](./docs/MAP_P1_FABRIC_EVAL.md)) |

### Admit actions (hub language ↔ code)

**What “admit” means:** GraphWriter’s **per-line triage** of an incoming `ingest.v1` record — choose NOOP / WRITE / DROP. Not authentication, Collect schema validation, or a named E-stage. Fuller terminology: [`docs/MAP_P1_FABRIC_EVAL.md`](./docs/MAP_P1_FABRIC_EVAL.md).

| Hub action | Code path | Effect |
|------------|-----------|--------|
| **NOOP** | `fact_kind != "topo_update"` → `continue` | No state change, no reject |
| **WRITE** | gate + `may_emit_vertex` + `classify_relation` emit + triplet allowlist → `emit` | Upsert node(s) + edge in `GraphState` |
| **DROP** | gate fail / never-CI / `unknown_relation` / `missing_endpoint_type` / `illegal_edge_triplet` | Append `writer.rejects`; map unchanged |

All fifteen Motadata relation names may emit; pairing: [`../contracts/EDGE_TRIPLET_ALLOWLIST.md`](../contracts/EDGE_TRIPLET_ALLOWLIST.md).

Vortex + S3 (`vortex_s3.v1`): columnar `.vortex` + ObserveOps manifest — [`../contracts/MAP_WRITE_READ_RECORD.md`](../contracts/MAP_WRITE_READ_RECORD.md) §6 (metadata/footer in §6.4; Rust action items). PoC dest remains **`files.v1`**. Notes: [`docs/vortex_engineering_mystery_revised_v2.pdf`](./docs/vortex_engineering_mystery_revised_v2.pdf).

---

## Layout (PoC-minimal)

```text
pillar-b/
├── README.md
├── docs/                     ← PoC guides only (see docs/README.md)
├── reference/canvases/       ← Cursor canvas copies (hub door: pillar-b-poc-hub.html)
├── archived-docs/            ← OPTIONAL product HTML library (not PoC SoT)
└── poc/                      ← code, sample estate, tests
```

JSON schemas and map write/read prose live only under the **slice** tree [`../contracts/`](../contracts/) — validators load that path; do not add a package-local `contracts/` mirror.

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
- Optional product briefs: [`archived-docs/README.md`](./archived-docs/README.md)
