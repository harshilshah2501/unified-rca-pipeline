# Pillar B PoC — team walkthrough (one stop)

**Audience:** teammates seeing this package for the first time (demo or review).  
**Package:** Motadata ObserveOps **Pillar B** — knowledge graph / topology writer and walk APIs under Dest room `map/`.  
**Sibling (not this demo):** Pillar A sketch writer → `history/` (same post-Identity stream, different `signal_class`).

If you only open one page before the meeting, make it **this file**. Open the navigator canvas beside chat for the interactive layer view: [Pillar B PoC Navigator](../reference/canvases/pillar-b-poc-navigator.canvas.tsx) (Command Palette → **Open Canvas** if click opens raw TSX).

---

## 1. What this PoC proves (two use cases only)

| Use case | Plain meaning | Proof in repo |
|----------|---------------|---------------|
| **1 · Build + maintain** | Admit topology facts → upsert nodes/edges → publish a packaged snapshot → optional E5 validity marks | `test_p1_map_fabric`, `test_maintain`, `test_graph_writer`, `test_sample_io` |
| **2 · Walk-through** | Read a published snapshot: hops, direction, filters, reachable set, paths, confidence-bearing | `test_map_walk` |

**Not the PoC mission** (stubbed or assumed): E1 Collect, E2 Identity, Detect/Curate/Identify/Package product stages, Pillar A sketches, live Vortex/S3, discovery crawler. Stub drivers under `poc/graph/case_path/` call walk APIs only so later stages have a harness — they are not a second product.

**Success bar:** (1) Case A/B map spines match SAMPLE_IO after build; (2) walk tests show multi-hop / inbound / confidence behavior; (3) maintain changes what a walk may see (expire / hard-downgrade).

---

## 2. Fifteen-minute demo script

1. **Spine story** — After Identity, Motadata fans out: Topology (Pillar B) ∥ Stores (Pillar A). Both read `ingest.v1`; B admits only `topo_update`.  
2. **Show sample tape** — `poc/sample_estate/customer_checkout/stream.resolved.jsonl` (WRITE) and `stream.reject.jsonl` (NOOP + DROP).  
3. **Run** — from `pillar-b/poc`: `make install && make test-all` (optional `make publish-map` → `out/default/map/`).  
4. **Open published map** — `graph_snapshot.json` + `nodes.jsonl` + `edges.jsonl`.  
5. **Walk** — point at `neighbors.py` / `read_api.py` and `test_map_walk.py`.  
6. **Call graphs** — [`pillar-b-callgraph.png`](./pillar-b-callgraph.png) (build) · [`pillar-b-walk-callgraph.png`](./pillar-b-walk-callgraph.png) (walk).  
7. **Navigator canvas** — layers + call sequences (build and walk).

---

## 3. How input reaches GraphWriter and SketchWriter

### Where the five `signal_class` values came from

They are **not** Motadata inventing five random labels. They come from freezing **one JSONL wire** that must feed both:

1. **ObserveOps stages** after Collect (Topology, Stores, Detect, Localize, Identify, …), and  
2. **Bakeoff / Lean / Federated** engines that already thought in metrics, anomalies, events, spans, and topology refresh.

So Collect normalizes raw MELTS-ish sources into a **closed enum of line kinds**. Writers then filter by that enum instead of each parsing every modality. Reserved names (`change_event`, `cmdb_sync`, `ticket`) exist so ServiceOps/CMDB can join later without colliding. Normative list: [`docs/INGEST_DATA_FORMAT.md`](../../../docs/INGEST_DATA_FORMAT.md) §2 · cheat sheet: [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md).

**Spoken name vs wire name:** the JSON field is still `signal_class`. In team talk, prefer **fact kind** (or **line kind**) — “what kind of fact this line is / which consumers should care.” It is a **router label**, not “an anomaly signal” and not MELTS letter codes. See §3.3 below before any wire rename.

**One shared wire format after E2:** every line is still `ingest.v1`. Identity adds an `identity` object; it does **not** invent a second schema. Writers **filter by fact kind (`signal_class`)**. Collect/adapters stamp it; GraphWriter does not guess it.

```text
                    post-E2 ingest.v1 stream
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   metric_sample         topo_update         event / anomaly / trace_span
          │                   │                   │
          ▼                   ▼                   ▼
   SketchWriter (A)     GraphWriter (B)      both pillars skip
   → history/ sketch    → map/ snapshot      (other stages later)
```

### 3.1 Consumer + fields table (every fact kind)

Spine on **every** line: `schema_version`, `ts`, `tenant`, `ci_id`, `ci_type`, `signal_class`, plus `identity` after E2.

| Fact kind (`signal_class`) | Who consumes it | Pillar A / B | Fields that matter for this kind |
|----------------------------|-----------------|--------------|----------------------------------|
| `metric_sample` | **E4 Stores** (sketches) · **E6 Detect** | A **admits** · B NOOP | `name` (metric id), `value`; optional `labels` (e.g. `trace_id` for exemplars) |
| `topo_update` | **E3 Topology** only | A NOOP · B **admits** | `relation`, `src_ci_id`, `dst_ci_id`; optional `dst_ci_type`; `name` often omitted |
| `anomaly` | **E6 Detect** · **E7 Curate** | Both skip | `name`, `value`, `threshold`, `severity` |
| `event` | **E4** evidence · **E10 Identify** | Both skip | `name` (event/**log** type), `value` (often `1.0`), `labels` — **logs land here; there is no separate `log` fact kind** |
| `trace_span` | **E9 Localize** · **E10 Identify** | Both skip | `name` (operation), `value` = duration ms; `labels` (`trace_id`, `span_id`, `peer.service`, …) |

Reserved (do not emit this pass): `change_event`, `cmdb_sync`, `ticket` — future ServiceOps / CMDB / change feeds.

### 3.2 Node bind vs edge provenance

| Concern | Lives on | Field | Meaning |
|---------|----------|-------|---------|
| **How did this CI get its id?** | Node / ingest line | `identity.bind_source` | Which binder/look-up attached `ci_id` (`topology_lookup`, `inventory`, `apm`, …) |
| **How strong is this relationship fact?** | Edge | `discovered_via` (provenance block) | `evidence_type` = `authoritative` \| `declared` \| `corroborating`, plus `confidence`, `telemetry_source`, … |

They are parallel ideas at different layers: **bind → identity of the vertex**; **provenance → trust of the edge**. In this PoC, GraphWriter copies `bind_source` into `discovered_via.telemetry_source` and maps it to `evidence_type` via `evidence_for_source` (`provenance.py`). E5 maintain later decays edges using `evidence_type`, not `bind_source` directly.

### 3.3 Better name for team discussion?

| Option | Pros | Cons |
|--------|------|------|
| Keep wire `signal_class`, say **fact kind** / **line kind** in meetings | No schema break; matches “router label” intent | Two names until muscle memory shifts |
| Rename wire to `fact_kind` | Matches spoken language | Breaks every fixture, schema, LLD, bakeoff sample — needs Motadata contract change |

**Recommendation:** do **not** rename the JSON field in this PoC yet. Use **fact kind** aloud (“this line’s fact kind is `topo_update` → Topology”). If leadership wants a wire rename, treat it as an I/O-1 contract change in `INGEST_DATA_FORMAT.md` + schema, not a Pillar B–only edit.

### Example — SketchWriter admits (`metric_sample`)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "metric_sample",
  "name": "request.latency_ms",
  "value": 92.1,
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

GraphWriter: NOOP. SketchWriter: folds into windowed history.

### Example — GraphWriter admits (`topo_update` → WRITE)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "topo_update",
  "relation": "runs_on",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "linux-server-app-01",
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

SketchWriter: NOOP. GraphWriter: upsert nodes + edge in memory; `publish_map` flushes Dest.

### Example — both skip (`trace_span`)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "trace_span",
  "name": "POST /checkout",
  "value": 210.0,
  "identity": { "status": "resolved", "bind_source": "apm" }
}
```

A future adapter may turn peer labels into a **new** `topo_update` line; this PoC does not derive edges from spans inside GraphWriter.

Full cheat sheet: [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md).  
Discussion (logs → `event`, spoken **fact kind**): [`../../../docs/fabric/INGEST_FACT_KINDS_DISCUSSION.md`](../../../docs/fabric/INGEST_FACT_KINDS_DISCUSSION.md).

---

## 4. How GraphWriter decides admit (NOOP / WRITE / DROP)

**Admit** = per-line triage inside `apply_topo_stream` — not auth, not Collect schema validation.

| Hub action | When | Effect |
|------------|------|--------|
| **NOOP** | Fact kind (`signal_class`) ≠ `topo_update` | Silent skip; no reject |
| **DROP** | Unresolved/synthesized identity, never-CI type (`Alert`…), unknown `relation` | Append reject reason; map unchanged |
| **WRITE** | Resolved + allowed CI type + wave-1 relation (`runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`) | Upsert node(s) + edge in `GraphState` |
| Phased skip | Relation in fifteen-name catalog but not wave-1 (e.g. `mounts`) | No write, usually not a DROP |

Code: `poc/graph/graph_builder.py` → `apply_topo_stream`. Lab tapes: `stream.resolved.jsonl` / `stream.reject.jsonl`.

---

## 5. `bind_source` (node) and `discovered_via` (edge)

See §3.2 for the side-by-side. Short version: **`bind_source` answers “who bound this CI?”**; **`discovered_via` answers “how trustworthy is this edge?”**

---

## 6. JSON contracts (input → output)

| Direction | Artifact | Schema / shape |
|-----------|----------|----------------|
| **In** | Stream lines | `ingest.v1` (`topo_update` for B) |
| **In** | Optional bootstrap | Lab `{nodes[], edges[]}` — not yet `graph_node.v1` on disk |
| **Out** | Packaged estate map | `graph_snapshot.v1` → Dest key `graph_snapshot.json` |
| **Out** | Side files | `nodes.jsonl` (`graph_node.v1`), `edges.jsonl` (`graph_edge.v1`) |

Normative map write/read: [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md).  
“Packaged estate map” = the published, versioned knowledge graph for that tenant generation — complete relative to what GraphWriter had admitted at publish time.

Lab publish path: `poc/out/<tenant>/map/`.

---

## 7. Where the files live

```text
pillar-b/
├── README.md                 ← package door
├── docs/
│   ├── TEAM_WALKTHROUGH.md   ← this page
│   ├── MAP_P1_FABRIC_EVAL.md ← eval criteria
│   ├── Codebase-go-through.md← module tour
│   └── pillar-b-*-callgraph.png
├── reference/canvases/       ← navigator (also under Cursor canvases/)
└── poc/
    ├── graph/                ← GraphWriter + walk + stubs
    ├── sample_estate/customer_checkout/
    │   ├── topology.bootstrap.json
    │   ├── stream.resolved.jsonl / stream.reject.jsonl
    │   ├── SAMPLE_IO.md
    │   └── cases/…
    └── out/default/map/      ← after make publish-map
```

---

## 8. Run commands

```bash
cd pillar-ab-implementation/pillar-b/poc
python3 -m venv .venv
make install
make test-all
make publish-map    # optional: write out/default/map/
```

---

## 9. Deeper links (after this page)

| Next | Why |
|------|-----|
| [Pillar B PoC Navigator canvas](../reference/canvases/pillar-b-poc-navigator.canvas.tsx) | Interactive layers + call sequences |
| [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) | What “done” means for build/walk |
| [`Codebase-go-through.md`](./Codebase-go-through.md) | File-by-file code tour |
| [`../poc/sample_estate/customer_checkout/SAMPLE_IO.md`](../poc/sample_estate/customer_checkout/SAMPLE_IO.md) | Case A/B goldens |
| [`INGEST_FACT_KINDS_DISCUSSION.md`](../../../docs/fabric/INGEST_FACT_KINDS_DISCUSSION.md) | Fact kinds discussion (logs → `event`) |
| [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md) | Every `signal_class` with examples |
| [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md) | Dest keys and snapshot schema |
| [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter) | Hub visual for NOOP / WRITE / DROP |

Optional stub harness notes (not core demo): [`MAP_P2_CASE_PATH.md`](./MAP_P2_CASE_PATH.md) · [`MAP_P3_DIAGNOSE_CLOSE.md`](./MAP_P3_DIAGNOSE_CLOSE.md).
