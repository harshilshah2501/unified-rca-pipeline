# Pillar B PoC — comprehensive session Q&A

**Purpose:** Full reference capture of the Pillar B knowledge-graph PoC working chat (2026-09-22 and the pillar-b thread recovered into it). A teammate who did not sit in the conversation should be able to reconstruct **what was decided, why, what changed in the repo, and what remains stubbed**.

**Scope:** Motadata ObserveOps **Pillar B** — topology / Dest room `map/` (build + maintain + walk). Pillar A (`history/` sketches) appears wherever the shared post-Identity ingest stream matters.

**Status:** Living session record. Normative schemas and eval criteria remain in their source-of-truth pages; this file is the **discussion + decision trail**.

**Companions**

| Page | Job |
|------|-----|
| [`TEAM_WALKTHROUGH.md`](./TEAM_WALKTHROUGH.md) | Fifteen-minute demo script |
| [Pillar B PoC hub](../../../docs/fabric/pillar-b-poc-hub.html) | Framing, layers, canvas → `:8765` doors |
| [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) | What “done” means for build/walk |
| [`MAP_P2_CASE_PATH.md`](./MAP_P2_CASE_PATH.md) · [`MAP_P3_DIAGNOSE_CLOSE.md`](./MAP_P3_DIAGNOSE_CLOSE.md) | Optional stub harnesses (not core mission) |
| [`../../contracts/WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md) | **Current** post-E2 writer fan-out — `writer_stream.v1`, no `fact_kind` |
| [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md) | Legacy lab `ingest.v1` / `fact_kind` examples |
| [`../../../docs/observeops/LLD-E4-Stores.md`](../../../docs/observeops/LLD-E4-Stores.md) | Motadata `history/` = metrics sketches; dual-path E4 |
| [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md) | Dest `map/` write/read |
| [`../../contracts/GRAPH_QNA.md`](../../contracts/GRAPH_QNA.md) | Broader fabric contract Q&A (E1–E5) |

---

## Contents

1. [How this session started (context restore)](#1-how-this-session-started-context-restore)
2. [Mission: two use cases only](#2-mission-two-use-cases-only)
3. [Increments, stubs, and fabric films](#3-increments-stubs-and-fabric-films)
4. [Call graphs (build vs walk)](#4-call-graphs-build-vs-walk)
5. [Wire contract, production stream, and sample estate](#5-wire-contract-production-stream-and-sample-estate)
6. [GraphWriter input/output contracts and all JSON/JSONL files](#6-graphwriter-inputoutput-contracts-and-all-jsonjsonl-files)
7. [Lab `fact_kind` (legacy) vs writer_stream](#7-lab-fact_kind-legacy-vs-writer_stream)
8. [Admit triage: NOOP / WRITE / DROP / phased skip](#8-admit-triage-noop--write--drop--phased-skip)
9. [Production: other kinds that imply topology](#9-production-other-kinds-that-imply-topology)
10. [Interleaved multi-kind stream (worked example)](#10-interleaved-multi-kind-stream-worked-example)
11. [Nodes, edges, bind, provenance, packaged map](#11-nodes-edges-bind-provenance-packaged-map)
12. [Tests vs the two use cases](#12-tests-vs-the-two-use-cases)
13. [Docs hub, canvases, naming hygiene, package layout](#13-docs-hub-canvases-naming-hygiene-package-layout)
14. [Editor / IDE notes from the same chat](#14-editor--ide-notes-from-the-same-chat)
15. [Consumers of `event` / `anomaly` / `trace_span` (Triage + Diagnose)](#15-consumers-of-event--anomaly--trace_span-triage--diagnose)
16. [Writer stream supersession (no `fact_kind`)](#16-writer-stream-supersession-no-fact_kind)
17. [Chronological topic index](#17-chronological-topic-index)

---

## 1. How this session started (context restore)

### Q1. Chat history “vanished” — was work lost?

**A.** The open thread lost prior turns, but **local agent transcripts** for this workspace remained on disk. The operator asked to reinstate non–Edge Delta context, then specifically to recover **pillar-b / pillar-ab implementation** history (not a separate HLD/Identity deep dive as the primary track).

### Q2. What Identity / HLD locks were restated while recovering context?

**A.** When an HLD/Identity resume was briefly started (then redirected to Pillar B), these locks were restated so they are not reopened casually:

| Item | Decision |
|------|----------|
| HLD | v1.1 — ServiceOps-joinable identity namespace |
| E1 Collect / E2 Identity | LLD **Done** |
| Join key | `(tenant, ci_id)` |
| Tags | `service` / `env` / `version` stay optional `labels` |
| Bind miss | Synthesize + flag; never localize or ticket target |
| After E2 | Identity Index → **topology bind ∥ store fan-out** |
| Tenant | Customer/org isolation — **not** modality, **not** Datadog `env` |

Pillar B assumes Identity already stamped `identity.*` on ingest lines. Writers do not own the bind look-up table.

### Q3. Code vs docs gap found while resuming Pillar B?

**A.** An API rename had left call sites as `_node_from_bootstrap` while the helper was `_make_node` — docs matched intent; code was broken. That was fixed as part of resuming the Codebase-go-through / GraphWriter thread before call-graph work.

---

## 2. Mission: two use cases only

### Q4. What does this PoC prove?

**A.** After Identity (assumed upstream), Motadata can **build and keep** a knowledge graph under Dest room `map/` from optional estate bootstrap plus a `topo_update` stream, **maintain** edge validity (E5), and **walk** the published snapshot. It does **not** own Collect, Identity, Detect product stages, Pillar A sketches, live Vortex/S3, or ServiceOps ticket create.

### Q5. Why frame the PoC as exactly two use cases?

**A.** Operator lock (mid-session): *“we are just focusing on Knowledge graph/topology PoC… (1) building, maintaining (2) walk-through. So we can assume or stub the other things.”*

| Use case | Plain meaning | Success proof |
|----------|---------------|---------------|
| **1 · Build + maintain** | Bootstrap → admit `topo_update` → upsert → publish `GraphSnapshot` → optional E5 validity marks | Case A/B spines + maintain tests |
| **2 · Walk-through** | Read published snapshot: hops, direction, filters, reachable set, paths, confidence-bearing | `test_map_walk` matrix |

**Stub / assume (not the mission):** Collect/Identity live path, sketches, Detect storm, CaseSeed → VerdictCard product pipeline. Thin harnesses under `poc/graph/case_path/` may **call walk APIs** so later stages have a driver — they are not a second product. Success = map spines + walk proofs, not a full diagnose product.

### Q6. Do we need a standalone `POC_TWO_USE_CASES.md`?

**A.** **No.** Operator asked to consolidate framing into the **Pillar B PoC Navigator** canvas (and later the HTML hub). The standalone markdown was **removed** so there is not a third copy of the same story. Live framing: [Pillar B PoC hub](../../../docs/fabric/pillar-b-poc-hub.html) + Cursor Open Canvas → `pillar-b-poc-navigator`.

### Q7. Why remove “Happy path (required)” from the navigator?

**A.** It duplicated the build story without teaching anything new. Replaced with a **Call sequences** block:

1. **GraphWriter** — `load_estate_bootstrap` → `write_topo_stream` → `publish_map` → `maintain_map`
2. **Walk-through** — `load_snapshot` → `get_neighbors` → `get_reachable` → `get_paths`

### Q8. Why remove “one-stop” from the walkthrough title?

**A.** “One-stop” was only a requirement phrase in chat. Hub/README titles are now plain **Pillar B PoC — team walkthrough** (no marketing adjective).

---

## 3. Increments, stubs, and fabric films

### Q9. What were Increments 1 / 2 / 3 in this chat?

**A.** Lab depth slices — **not** Motadata product release numbers:

| Increment | What landed | Core mission? |
|-----------|-------------|---------------|
| **1** | Build/maintain map spine + light walk smoke | **Yes** (use case 1; walk thin) |
| Walk depth (requested after Q on Part B) | Multi-hop / inbound / confidence / paths → `test_map_walk.py` | **Yes** (use case 2 depth) |
| **2** | Case-path harness: CaseSeed → WorkingSet → LeafClaim **reading** `map/` only | **Stub** — see `MAP_P2_CASE_PATH.md`, folder `cases/stub_case_path/` |
| **3** | Identify `EvidenceBundle` + Package `VerdictCard` after LeafClaim | **Stub** — see `MAP_P3_DIAGNOSE_CLOSE.md`, folder `cases/stub_diagnose_close/` |

Increment 3 teaching golden still ends on **`payments-db`** (tier 2 because lab has no change evidence). Still out of scope: live ServiceOps ticket create; fabric HTML film for E10/E11.

### Q10. What is “fabric film 2”? Is it the same as Increment 2?

**A.** **No.** Fabric film 2 is a **docs hub teaching animation**, not a PoC folder name.

| | Film 1 | Film 2 |
|--|--------|--------|
| **File** | `docs/fabric/edge-platform-detect-simulation.html` | `docs/fabric/edge-platform-case-simulation.html` |
| **Hub** | `:8765/edge-platform-detect-simulation.html` | `:8765/edge-platform-case-simulation.html` |
| **Story** | Data in → always-on `map/`∥`history/` → Detect raises a Signal | Warm rooms → signal **storm** → one CaseSeed → WorkingSet → LeafClaim |
| **Stops before** | Curate / Scope / Localize | Identify / Package |

Locks: [`docs/fabric/SIMULATION_THREAD.md`](../../../docs/fabric/SIMULATION_THREAD.md). Saying Increment 2 “aligns with film 2” only means the **case-path stub** uses the same stage object names film 2 teaches — it does not make the film a Pillar B deliverable.

### Q11. Why rename `happy_path` / `increment2` / `increment3` estate folders?

**A.** Casual names hid whether a folder was **PoC core** or a **stub**. Renames:

| Old | New | Role |
|-----|-----|------|
| `happy_path/` | `case_a_map_spine/` | PoC core — golden map spine after `stream.resolved.jsonl` |
| `reject_tape/` (or similar) | `case_b_rejects/` | PoC core — golden DROP codes (`expected_rejects.json`) |
| `increment2/` | `stub_case_path/` | Optional Detect→Localize harness — **not** map build |
| `increment3/` | `stub_diagnose_close/` | Optional Identify/Package harness — **not** map build |

---

## 4. Call graphs (build vs walk)

### Q12. How do we generate a call graph for the Python PoC?

**A.** Three practical ways discussed:

1. **Cursor Call Hierarchy** — caret on `publish_map` / `write_topo_stream` / `maintain_map` → Command Palette → **Calls: Show Call Hierarchy** (needs a working Python language server; see §14).
2. **Static (`code2flow` + Graphviz)** — from `pillar-b/poc` venv, root at `cli_publish_map.main`, include `graph/*.py` + `ab_shared`, exclude tests / `.venv` / `out/`. `code2flow` 2.x needs `--downstream-depth` / `--upstream-depth` when using `--target-function`.
3. **Dynamic** — `python -m trace` or `pycallgraph2` around one `make publish-map` run (happy path only unless you drive reject tape).

Expected write spine (same idea as Codebase-go-through Mermaid):  
`main` → `load_estate_bootstrap` → `write_topo_stream` / `apply_topo_stream` → `publish_map` → Dest `map/` (+ optional `maintain_map`).

### Q13. Why was the first PNG “clutter,” and what changed?

**A.** Auto `code2flow` many-to-many helper fan-out was unreadable. Curated layered graphs were rebuilt under `pillar-b/docs/` with **one-liner descriptions on every node and every edge**.

### Q14. Why two call-graph images?

**A.** The first graph was **use case 1 only**. Operator asked: *“This call graph doesn't include walk-through functions?”* Answer: add a matching walk graph.

| Use case | Asset |
|----------|-------|
| Build + maintain | `pillar-b/docs/pillar-b-callgraph.png` (+ `.svg` / `.dot`) |
| Walk-through | `pillar-b/docs/pillar-b-walk-callgraph.png` |

Walk graph covers `load_snapshot` → `get_*` / `neighbors` / `reachable_ci_ids` / `find_paths` (+ optional stub callers).

### Q15. Codebase-go-through images too huge in HTML?

**A.** Operator reported oversized rendering. Constrained image CSS / sizing for those call-graph assets in the markdown HTML render path so the doc stays usable.

---

## 5. Wire contract, production stream, and sample estate

### Q16. What is `ingest.v1`? Where is the “ingest.v1 file”?

**A.** There is **no** file named `ingest.v1`. It is a **schema id** — the string `"schema_version": "ingest.v1"` on every wire line.

| What you open | Path |
|---------------|------|
| Schema | Slice `contracts/schemas/ingest_v1.schema.json` (validators load this path; no package mirror) |
| Normative prose | [`docs/INGEST_DATA_FORMAT.md`](../../../docs/INGEST_DATA_FORMAT.md) |
| Lab GraphWriter input | `…/customer_checkout/stream.resolved.jsonl` · `stream.reject.jsonl` |
| One-of-each examples | `…/expected/ingest.example.json` (all five kinds) |

### Q17. Production intent — where does the stream come from? Is it NATS?

**A.** Production intent is a **continuous post-E2 `ingest.v1` feed** after Collect + Identity. The **bus brand is not locked**.

1. **Sources** — agents / OTLP / logs / APM / inventory / catalog adapters (later topology crawlers).
2. **E1 Collect** — admit well-formed `ingest.v1`.
3. **E2 Identity** — same line with `identity.*` (`tenant` + `ci_id`).
4. **Fan-out** — Topology (Pillar B) ∥ Stores (Pillar A) filter by `fact_kind`.

Leadership sketches may draw **NATS** on the SaaS side (telemetry → NATS → percentile engine ∥ graph builder). That is **optional depiction**, not an HLD lock. Vector, Kafka, or an internal Motadata bus are fine. Pillar B only requires that post-E2 `topo_update` lines arrive (plus optional estate bootstrap). This PoC does **not** run a live bus.

### Q18. So is `stream.resolved.jsonl` the ingest stream?

**A.** Nuance: **`ingest.v1` = schema/contract**; **`stream.resolved.jsonl` = this PoC’s file stand-in** for the production post-E2 **topo subset** (Case A WRITE). `stream.reject.jsonl` stands in for mixed DROP/NOOP lines (Case B). Production would be continuous; the lab reads files via `JsonlIngestSource`.

### Q19. Full sample estate layout?

**A.** Under `poc/sample_estate/customer_checkout/` (also clarified in that folder’s README):

```text
customer_checkout/
├── topology.bootstrap.json      ← optional starting nodes/edges (not CaseSeed)
├── walk_chain.bootstrap.json    ← longer chain for walk-only tests (not Case A spine)
├── stream.resolved.jsonl        ← Case A: five topo_update WRITE lines
├── stream.reject.jsonl          ← Case B: DROP + NOOP mix
├── SAMPLE_IO.md                 ← Case A/B expected vs actual narrative
├── README.md
├── expected/                    ← shape samples (not asserted goldens)
│   ├── ingest.example.json      ← all five fact_kind examples
│   ├── graph_node.example.json
│   ├── graph_edge.example.json
│   └── change_fact.example.json
└── cases/
    ├── case_a_map_spine/        ← PoC core golden spine
    ├── case_b_rejects/          ← PoC core golden DROP reasons
    ├── stub_case_path/          ← NOT PoC core
    └── stub_diagnose_close/     ← NOT PoC core
```

`ingest.example.json` was expanded mid-session so it includes **all five** kinds (not only topo/metric), with `_note` on who admits each; mirrored to pillar-a / integration estates; schema tests validate every example.

### Q20. Was `linux-server-ci-telemetry.json` part of this?

**A.** Removed on request. It was a separate CI-telemetry teaching artifact (and a blind rename briefly mangled nested keys). Live links now point at hub teaching pages such as [`observeops-ci-graph.html`](http://127.0.0.1:8765/observeops-ci-graph.html). `_archive/` copies left alone.

---

## 6. GraphWriter input/output contracts and all JSON/JSONL files

### Q21. What is the JSON contract for GraphWriter input and output?

**A.** Normative SoT: [`MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md). Schemas under slice `contracts/schemas/` only (no `pillar-b/contracts/` mirror).

#### Input (two shapes)

| What | Schema / shape | How it arrives |
|------|----------------|----------------|
| **Topo stream** | `ingest.v1` with `fact_kind=topo_update`, `identity.status=resolved`, plus `relation` / `src_ci_id` / `dst_ci_id` | Lab: `stream.*.jsonl` |
| **Optional estate bootstrap** | Lab compact `{nodes[{id,type,name}], edges[{from,to,relation}]}` — **not** `graph_node.v1` on disk | `topology.bootstrap.json` / `walk_chain.bootstrap.json` |

#### Output (Dest room `map/`)

| Dest key | Format | Schema |
|----------|--------|--------|
| `graph_snapshot.json` | Pretty JSON | `graph_snapshot.v1` (`tenant`, `version`, `nodes[]`, `edges[]`) |
| `nodes.jsonl` | JSON Lines | one `graph_node.v1` per line |
| `edges.jsonl` | JSON Lines | one `graph_edge.v1` per line |

Lab publish path: `poc/out/<tenant>/map/` (e.g. after `make publish-map`). Prefer reading the snapshot document; JSONL is for inspection. Vortex (hot) / S3 (cold) are **later encodings of the same logical fields** — not a second schema.

Logical keys: node `(tenant, ci_id)`; edge `(tenant, edge_id)`; snapshot `(tenant, version)`.

### Q22. Inventory of JSON/JSONL across the PoC?

**A.**

| Stage | Files / objects |
|-------|-----------------|
| Wire contract | `ingest_v1.schema.json`, `graph_node.v1`, `graph_edge.v1`, `graph_snapshot.v1` |
| Lab input | `stream.*.jsonl`, bootstrap JSON, `expected/*.example.json` |
| In memory | `GraphState` (nodes, edges, rejects) |
| Publish | `graph_snapshot.json`, `nodes.jsonl`, `edges.jsonl` under Dest `map/` |
| Rejects | Reason codes ([`IDENTIFIED_STREAM_REJECT.md`](../../contracts/IDENTIFIED_STREAM_REJECT.md)); Case B `expected_rejects.json` |
| Goldens | `cases/case_a_map_spine/expected_spine.json`, `cases/case_b_rejects/…` |
| Optional history | `history/change_facts.jsonl` is **not** a map key (separate room when used) |

### Q23. What is “Package estate map”? Is it the complete knowledge graph?

**A.** **Packaged estate map** = `graph_snapshot.v1`: one versioned JSON document wrapping **all nodes and edges GraphWriter currently has in memory for a tenant**, flushed to Dest as `graph_snapshot.json`.

| It is | It is not |
|-------|-----------|
| The full **admitted** graph at publish time | A live crawler dump of every CI in the world |
| The packaged read unit for walk APIs | Sketches, metrics, tickets, or `history/` |
| What Case A/B spine checks load | Forever-complete without E5 refresh / new `topo_update`s |

For Motadata Pillar B it **is** the topology / knowledge-graph **artifact** readers use. Diagnose stages **read** it; they do not call `write_topo_stream` / `publish_map`.

### Q24. Is “v1” the in-memory estate and JSON the published graph?

**A.** Almost — naming nuance:

| Piece | What it is |
|-------|------------|
| **`GraphState`** | In-memory estate (nodes / edges / rejects) while building |
| **`graph_snapshot.v1`** | **Schema id** of the published JSON package |
| **`nodes.jsonl` / `edges.jsonl`** | Same publish, one object per line |
| Snapshot field **`version`** | Generation string on the object (e.g. `"1"`) — **not** the same as schema `.v1` |

Flow: **memory `GraphState` → `publish_map` → JSON on Dest.** Do not use obsolete `snapshot_id`.

---

## 7. Lab `fact_kind` (legacy) vs writer_stream

> **Superseded for new writer work** by [`WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md) (`writer_stream.v1`, no router enum). Lab fixtures and GraphWriter/SketchWriter code still filter `fact_kind` until migration — see also **§16**.

### Q25–Q32 (collapsed). What was `fact_kind`, and what remains true for the lab?

**A.** On deprecated `ingest.v1`, `fact_kind` was the Collect-stamped router label (`metric_sample` | `topo_update` | `anomaly` | `event` | `trace_span`). GraphWriter admits only `topo_update`; SketchWriter admits only `metric_sample`; logs land as `event` ([`INGEST_DATA_FORMAT.md`](../../../docs/INGEST_DATA_FORMAT.md) §5). The field was renamed from `signal_class` in a hard cut (session history). **Target wire does not stamp it** — regulators infer from optional blocks.

Lab enum cheat sheet: [`E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md). How `event` / `anomaly` / `trace_span` are consumed later: **§15**.

---

## 8. Admit triage: NOOP / WRITE / DROP / phased skip

### Q33. What three admit outcomes does `apply_topo_stream` handle?

**A.** Hub triage (not auth, not Collect schema validation). Code: `poc/graph/graph_builder.py`.

| Hub action | When | Effect |
|------------|------|--------|
| **NOOP** | `fact_kind` ≠ `topo_update` | Silent skip; **no** reject row |
| **DROP** | Topo line but gate fails (unresolved/synthesized identity, never-CI type, unknown relation, …) | Append `(rec, reason)`; map unchanged |
| **WRITE** | Resolved + allowed CI type + wave-1 relation | Upsert node(s) + edge in `GraphState` |

**Phased skip (quieter fourth):** relation is in the fifteen-name catalog but **not wave-1 yet** (e.g. `mounts`) — no write; usually not a DROP. Feels like NOOP but only after the line already passed as `topo_update`.

Unknown / reserved `fact_kind` on the wire is a **Collect** concern. GraphWriter treats non-`topo_update` as **NOOP**, not DROP.

Hub visual: [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter).

### Q34. Concrete NOOP / DROP / WRITE examples?

**WRITE** (from Case A tape):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "runs_on",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "linux-server-app-01",
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

**NOOP** (wrong kind — GraphWriter skips; SketchWriter may admit metrics):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "orphan-metric",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.latency_ms",
  "value": 10.0,
  "identity": { "status": "unattributed" }
}
```

(Same NOOP class for `event`, `trace_span`, `anomaly` regardless of identity — GraphWriter never admits them.)

**DROP** (topo line, identity not resolved — from Case B tape):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "unresolved-topo",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "depends_on",
  "src_ci_id": "unresolved-topo",
  "dst_ci_id": "checkout-api",
  "identity": { "status": "unattributed" }
}
```

Reason codes include `identity_unresolved`, `identity_synthesized`, never-CI types, unknown relation — see `SAMPLE_IO.md` / `expected_rejects.json`.

---

## 9. Production: other kinds that imply topology

### Q35. Can metrics / spans / events / anomalies cause topology updates? How is that captured?

**A.** They may **suggest** relationships. They do **not** become edges inside GraphWriter.

**Capture pattern:** an **upstream adapter / Topology emitter** (APM service-map, inventory, catalog sync, designed log parser, …) writes a **second** `ingest.v1` line with `fact_kind: "topo_update"`. GraphWriter only admits that second line.

```text
  APM / logs / inventory / catalog / Detect
              │
              ▼
     Collect + Identity  →  shared ingest.v1 stream
              │
    ┌─────────┼──────────────┬────────────────┐
    ▼         ▼              ▼                ▼
 metric_   topo_update    event /          anomaly
 sample    (edge facts)   trace_span
    │         │              │                │
    ▼         ▼              ▼                ▼
 Sketch    GraphWriter    (A/B skip;         (A/B skip;
 Writer    → map/         emitters may       Detect may
                          emit topo later)   read map later)
```

| Source kind | Typical path to `map/` |
|-------------|-------------------------|
| `trace_span` | Peer / service-map adapter → e.g. `communicates_with` |
| `event` | Rare; only if a designed parser emits edges |
| `metric_sample` | Usually **no** edges; join by `ci_id` |
| `anomaly` | Detect / CaseSeed later **reads** `map/`; does not write it |
| Inventory / catalog | Direct `topo_update` — often stronger evidence |

**Span (measurement — GraphWriter NOOP):**

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:10Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "trace_span",
  "name": "POST /checkout",
  "value": 210.0,
  "labels": {
    "trace_id": "abc123",
    "peer.service": "payments-db"
  },
  "identity": { "status": "resolved", "bind_source": "apm" }
}
```

**Separate edge fact later (GraphWriter WRITE):**

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:20Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "communicates_with",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "payments-db",
  "identity": { "status": "resolved", "bind_source": "apm" }
}
```

This PoC simulates the second kind of line in `stream.resolved.jsonl`. It does **not** implement the span→edge adapter. Evidence strength on the edge may be **corroborating** until inventory/catalog confirms (see fabric inventory/catalog teaching pages and GRAPH_QNA).

---

## 10. Interleaved multi-kind stream (worked example)

### Q36. What does a realistic mixed production tape look like?

**A.** Full worked story (timeline, relation-named WRITEs, SketchWriter NOOP on every topo line, sample JSON for each step):

→ [Stream → graph demo](../../../docs/fabric/pillar-b-stream-graph-demo.html) (legacy interleaved tape)

Short index of that tape:

```text
03:29:50  topo_update       runs_on            JVM → host              GraphWriter WRITE · SketchWriter NOOP
03:30:00  metric_sample     latency 92ms                               SketchWriter admit · GraphWriter NOOP
03:30:05  metric_sample     error_rate                                 SketchWriter admit · GraphWriter NOOP
03:30:08  topo_update       part_of            api → bs-checkout       GraphWriter WRITE · SketchWriter NOOP
03:30:08  topo_update       depends_on         api → payments-db       GraphWriter WRITE · SketchWriter NOOP
03:30:10  trace_span        POST /checkout     peer=payments-db        A/B NOOP (emitter may watch)
03:30:11  event             log.error                                  A/B NOOP
03:30:12  metric_sample     latency 980ms                              SketchWriter admit · GraphWriter NOOP
03:30:15  anomaly           latency high                               Detect · A/B NOOP
03:30:20  topo_update       communicates_with  api → payments-db       GraphWriter WRITE · SketchWriter NOOP
03:30:22  topo_update       runs_on            api → host              GraphWriter WRITE · SketchWriter NOOP
```

Always state **`relation` + endpoints** on a WRITE. Catalog `depends_on` and APM `communicates_with` can both exist with different provenance. Wave-1 glossary: [`TEAM_WALKTHROUGH.md`](./TEAM_WALKTHROUGH.md) §4.

---

## 11. Nodes, edges, bind, provenance, packaged map

### Q37. What is `bind_source`? What is edge provenance?

**A.** Parallel ideas at different layers:

| Concern | Lives on | Field | Meaning |
|---------|----------|-------|---------|
| How did this CI get its id? | Node / ingest line | `identity.bind_source` | Which binder attached `ci_id` (`topology_lookup`, `inventory`, `apm`, `service-catalog`, …) |
| How strong is this relationship? | Edge | `discovered_via` | `evidence_type` = `authoritative` \| `declared` \| `corroborating`, plus confidence / telemetry source |

GraphWriter may copy `bind_source` into `discovered_via.telemetry_source` and map to `evidence_type` via `provenance.py` / `evidence_for_source`. E5 maintain decays edges using `evidence_type`, not `bind_source` alone.

Bootstrap provenance must **not** be confused with Detect CaseSeed (tested: `test_e3_bootstrap_provenance_not_caseseed`).

### Q38. Navigator “relate how” only showed build — walk missing?

**A.** Fixed mid-session: Dest → Read helpers now show **`load_snapshot · walk`**, captions call out use case 1 and 2, Dest labeled as publish hub for UC1 and walk hub for UC2. Hub SVG later needed the same fix when `load_snapshot` walk text was overshadowed behind Dest.

---

## 12. Tests vs the two use cases

### Q39. How do tests address build/maintain vs walk?

**A.** Early in the chat: **A heavy, B light** (Increment 1). Operator asked for **comprehensive depth for B** — walk API + `test_map_walk.py` landed.

#### Use case A — Building & maintaining `map/`

| Concern | What tests prove | Where |
|---------|------------------|-------|
| Bootstrap | Starting estate loads; never-CI dropped; bootstrap provenance ≠ CaseSeed | `test_builder_snapshot`, `test_e3_bootstrap_provenance_not_caseseed` |
| Stream admit | NOOP / WRITE / DROP / phased skip / upsert replay | `test_p1_map_fabric` E3 + `test_graph_writer` + `test_sample_io` Case A/B |
| Identity gate | Unresolved/synthesized never silent-write | E2 block in `test_p1_map_fabric` |
| Policy helpers | Fifteen relations, CI qualify, provenance | `test_edge_catalog`, `test_ci_qualify`, `test_provenance` |
| Publish | Valid `graph_snapshot.v1` to Dest | `test_snapshot_schema_and_dest`, graph writer flush tests |
| Maintain E5 | Expire `valid_to`; stale corroborating; declared windows; **no new edges** | `test_maintain` + E5 in `test_p1_map_fabric` |
| Maintain handoff | Maintain then version-bump re-publish | `test_writer_maintain_and_reflush`, `test_e5_version_bump_reflush_still_walkable` |

Goldens: Case A / Case B in `SAMPLE_IO.md`.

#### Use case B — Walking the published map

After depth work (bands B1–B3 in `test_map_walk.py`):

| Band | Covers |
|------|--------|
| **B1** | 1-hop, filters, inbound to DB/host, missing seed |
| **B2** | Multi-hop, WorkingSet-lite (`reachable_ci_ids`), leaf paths, relation-scoped path, undirected from leaf |
| **B3** | Dest roundtrip, expire removes edge from walk, hard-downgrade confidence filter, maintain re-flush |

Walk API (`neighbors.py` / `read_api.py`): direction `out` / `in` / `both`; hop budget; relation filters; `find_paths`; `confidence_bearing_only` (skips E5 hard-downgraded edges). Fixture `walk_chain.bootstrap.json`: `storefront-web → checkout-api → payments-db → db-host-01` (multi-hop without touching Case A spine).

**Still deferred (honest):** CaseSeed as product object, sketch-joined WorkingSet, E9 localize packaging — not required for map-only walk depth.

Run: `cd pillar-ab-implementation/pillar-b/poc && make install && make test-all` (optional `make publish-map`).

---

## 13. Docs hub, canvases, naming hygiene, package layout

### Q40. Docs hub audit — was Pillar B integrated?

**A.** Audit found PoC docs mostly off-hub and some broken `/docs/pillar-ab-implementation/` URLs. Work done: clear PoC demo path on Overview / archive / NAVIGATION; fix links; add GraphWriter / fact-kinds / walkthrough doors; later a dedicated **Pillar B PoC hub** HTML for canvas → `:8765` mappings.

### Q41. What are Hub Tier 1 / Band A/B / Door A/B/C — and what did we drop?

**A.** Operator: *“so many classifications… avoid clutter.”*

| Keep | Meaning |
|------|---------|
| **Pillar A / B / C** | Motadata product (sketches · knowledge graph · optional agent) |
| **Hub Tier 1 / 2 / 3** | Docs **reading depth** only (must-read · depth · archive) — on `OUR_HLD_TIER1.md`, **not** stamped on every PoC card |

| Drop from hub navigation | Replace with |
|--------------------------|--------------|
| **Band A / Band B** | Plain **Everyone** / **Implementers** |
| **“Next hop”** as a special label | Just “continue to TEAM_WALKTHROUGH” |
| **Tier chips on PoC demo cards** | Cards say Demo · Eval · Code · Goldens · Hub · Discussion only |

**Do not mix into Motadata hub talks:** Detect **Door A/B/C** (Node / Gateway / platform) — keep in Detect/shift-left docs; prefer those words so Door C ≠ Pillar C. Datadog Door A/B (Monitors / Watchdog) is unrelated.

### Q42. Canvas links 404 / don’t open — how should canvases be integrated?

**A.** Several related issues:

1. **Markdown / `:8765` links to `.canvas.tsx`** often do nothing or 404 — Cursor does not treat them like normal file links; the docs server does not execute TSX.
2. **Fix pattern:** HTML **hub doors** on `:8765` (e.g. [`pillar-b-poc-hub.html`](http://127.0.0.1:8765/pillar-b-poc-hub.html)) mapping each canvas id to a live teaching page; flat + dashboard **symlinks** to `docs/fabric/…`.
3. **Live Open Canvas** files live under the Cursor project `canvases/` folder. Repo copies under `pillar-b/reference/canvases/` are for git sync/diff.
4. Opening: Command Palette → **Open Canvas** → `pillar-b-poc-navigator` (or Agents file-change **Open**). Clicking the repo `.tsx` opens **source**, not the live panel (product behavior).
5. Interim: Navigator markdown links retargeted to `reference/canvases/README.md` as a reliable door before the HTML hub was complete.

### Q43. `reference/` vs `references/` — two directories?

**A.** Accidental plural/singular clash. Clarified then renamed:

| Path | Job |
|------|-----|
| **`pillar-b/reference/canvases/`** | Cursor teaching canvas **copies** for this PoC |
| **`pillar-b/archived-docs/`** (was `references/`) | Optional Motadata OneOps / Fusion / ED comparator HTML — **not** wire SoT, not required to run tests |

PoC truth stays under `poc/` + slice `contracts/`.

### Q44. Navigator layers-relate image missing / Dest overshadowed walk label?

**A.** Fixed: canvas SVG label overlap (walk text under Dest button) and hub page missing layers diagram — gap widened, labels placed above, hub SVG added.

### Q45. Reference canvas TypeScript “Problems”?

**A.** False alarms on the **git reference copy** — workspace TS server does not know Cursor’s `cursor/canvas` SDK there. Live Open Canvas file typechecks clean. Added `//@ts-nocheck` on reference copies so Problems stay quiet. Use Open Canvas for the real panel.

---

## 14. Editor / IDE notes from the same chat

These are **not** Motadata product locks, but they were part of the same working session and blocked demos.

### Q46. Call Hierarchy missing?

**A.** Needs a Python language server with call analysis. Windows had Pylance; **WSL/Cursor remote** had **BasedPyright** without Call Hierarchy for Python. Install/enable language support **on the remote**, select interpreter `pillar-b/poc/.venv`, Command Palette → **Calls: Show Call Hierarchy** (often `Alt+Shift+H`). Fallbacks: References, code2flow.

### Q47. BasedPyright Problems on GraphWriter imports?

**A.** Not runtime bugs — analyzer lacked `poc/` on `PYTHONPATH` (same as `pytest.ini` / `make test-all`). Added `pillar-b/poc/pyrightconfig.json` (basic mode, venv) and workspace BasedPyright path settings. Reload window; **Python: Select Interpreter** via Command Palette if status bar hidden (View → Appearance → Status Bar). Remaining strict/`all`-mode noise was overridden for this PoC.

### Q48. How to wrap long JSONL lines for reading?

**A.** Editor word wrap only (`Alt+Z` / View → Word Wrap). **Do not** Format Document into multi-line JSON objects — that breaks JSONL for `JsonlIngestSource`. Pretty-print one line: `sed -n '1p' stream.resolved.jsonl | python3 -m json.tool`.

### Q49. Markdown / canvas click doesn’t open preview?

**A.** Cursor open-path for canvases opens **source** by default; markdown is source-first unless you open Preview explicitly. Use Open Canvas / Markdown: Open Preview from Command Palette — not a project misconfiguration of default actions alone.

---

## 15. Consumers of `event` / `anomaly` / `trace_span` (Triage + Diagnose)

**Context (2026-09-23):** Operator asked who consumes `event`, `anomaly`, and `trace_span` — clarifying that the question is **not** whether SketchWriter / GraphWriter admit them. Follow-up: won’t those kinds be stored in E4 “evidence history” because Triage + Diagnose use them?

**Normative companions:** [`TEAM_WALKTHROUGH.md`](./TEAM_WALKTHROUGH.md) §3 · [`../../contracts/WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md) · [`../../../docs/INGEST_DATA_FORMAT.md`](../../../docs/INGEST_DATA_FORMAT.md) §2 · [`../../../docs/observeops/LLD-E4-Stores.md`](../../../docs/observeops/LLD-E4-Stores.md) §0 · [`../../../docs/fabric/SIMULATION_THREAD.md`](../../../docs/fabric/SIMULATION_THREAD.md)

### Q50. Who consumes `event`, `anomaly`, and `trace_span` — and **how**? (Not “do A/B writers skip them?”)

**A.** Pillar A SketchWriter and Pillar B GraphWriter **skip** these three kinds (NOOP). That is true but **not** the answer to this question. The router label points at **later ObserveOps stages**. How each is used:

#### `anomaly`

| | |
|--|--|
| **Who** | **E6 Detect** · **E7 Curate** |
| **How** | The wire line is already a *pre-marked* crossing (`name`, `value`, `threshold`, `severity`). Detect turns it into a **`Signal`** (same *role* as Door C firing from sketches, but the fire arrived already stamped on the wire). Curate merges Signals into a **`CaseSeed`**. An `anomaly` line is **not** a root-cause claim by itself. |
| **Film lock** | [`SIMULATION_THREAD.md`](../../../docs/fabric/SIMULATION_THREAD.md): “A wire `anomaly` line also becomes a Signal.” |

#### `event` (includes logs — there is no separate `log` fact kind)

| | |
|--|--|
| **Who** | **E4** evidence lane · **E10 Identify** |
| **How** | Persisted / cited as a discrete occurrence (`name` like `log.error`, often `value: 1.0`, rich `labels`). Identify later **cites** matching events into an **`EvidenceBundle`** for the leaf CI (corroboration: “here is the error log near the leaf”). An `event` is **not** a second Detect engine and **not** a GraphWriter edge. |
| **Why “E4” in the consumer table** | Means the **Stores / evidence consumer path** for discrete occurrences — see Q51 for what Motadata `history/` actually writes today. |

#### `trace_span`

| | |
|--|--|
| **Who** | **E9 Localize** · **E10 Identify** |
| **How** | Localize uses span timing / peer labels (and may **read** `map/`) toward a **`LeafClaim`**. Identify attaches span/trace evidence to the **`EvidenceBundle`** (path, duration, `trace_id`). Spans do **not** become graph edges inside GraphWriter; an upstream adapter may emit a separate **`topo_update`** if peers imply topology (see §9). |

```text
anomaly     →  E6 Signal  →  E7 CaseSeed
event       →  evidence store path  →  E10 cite in EvidenceBundle
trace_span  →  E9 Localize (LeafClaim)  →  E10 cite in EvidenceBundle
                 (span bodies live in a trace/APM store; see Q51)
```

**Join key** across Triage / Diagnose remains **`tenant` + `ci_id` (+ time window)** with the case **WorkingSet** — same post-E2 wire, different consumers.

**Fields that matter (kind-specific), from the TEAM_WALKTHROUGH consumer table:**

| Fact kind | Kind-specific fields |
|-----------|----------------------|
| `anomaly` | `name`, `value`, `threshold`, `severity` |
| `event` | `name` (event / **log** type), `value` (often `1.0`), `labels` |
| `trace_span` | `name` (operation), `value` = duration ms; `labels` (`trace_id`, `span_id`, `peer.service`, …) |

Spine on every line still includes `schema_version`, `ts`, `tenant`, `ci_id`, `ci_type`, `fact_kind`, plus `identity` after E2.

### Q51. Won’t `anomaly` and `trace_span` (and `event`) be stored in E4 “evidence history” because Triage + Diagnose use them?

**A.** **Partially yes on intent; no on Motadata’s current `history/` room.**

**Operator instinct (correct for Triage + Diagnose):** Identify / Localize / Curate need those facts **available later** — you cannot only “see them once on the live stream” and expect E10 to cite them. Something queryable must retain them (or a pointer to them).

**Nuance — Motadata E4 today ≠ “all MELTS evidence in one sketch store.”** From [`LLD-E4-Stores.md`](../../../docs/observeops/LLD-E4-Stores.md) §0:

| Path | What it persists | Modalities |
|------|------------------|------------|
| **Motadata Pillar A (E4)** | `sketch.v1` rows under Dest **`history/`** | **Metrics-only** (`metric_sample`). Detect door C and WorkingSet joins read digests / baselines. |
| **Bakeoff Lean / Federated** | UC bundles / structural + speed stores | **Multi-modality** reference (events, anomalies, …) — not the Motadata A/B freeze room layout |

Explicit LLD lock:

- Do **not** equate “E4 Stores” with “all MELTS in one sketch.”
- Logs (`event`) and traces (`trace_span`) still matter for Identify on bakeoff / reference paths; they **silent-skip** at Pillar A SketchWriter (GRAPH_QNA G31).
- Future Motadata log / trace / anomaly history would be **other history row types or sibling stores**, **not** an expansion of `sketch.v1`.

So TEAM_WALKTHROUGH’s phrase **“E4 evidence”** for `event` means the **Stores / evidence consumer lane**, **not** “this line is written into Motadata `history/sketches.jsonl` today.”

#### How each modality is supposed to stay available for Triage + Diagnose

| Kind | Persist / surface (intent) | How Triage–Diagnose uses it |
|------|----------------------------|-----------------------------|
| **`anomaly`** | Often becomes an E6 **`Signal`** (and/or an anomaly index such as bakeoff `A-ANOM`); **not** a `sketch.v1` row | E7 Curate → **CaseSeed**; later cited as “why we opened the case” |
| **`event`** (logs) | **Evidence store** path (consumer table: E4 evidence · E10). Motadata PoC does **not** yet write these into sketch `history/` | E10 Identify **cites** into **`EvidenceBundle`** |
| **`trace_span`** | **Trace / APM store** with its **own retention**. A sketch may keep only an optional **`trace_id` exemplar** as a *pointer* into that store ([`sketch-exemplars-visual.html`](../../../docs/fabric/sketch-exemplars-visual.html)) | E9 / E10 **look up** the span by id — they do **not** read span bodies from metric `history/` |

**Short verdict captured in chat:**

1. Yes — for Identify / Localize you need anomaly / event / span evidence **stored somewhere queryable**.  
2. No — that somewhere is **not** Motadata’s current E4 sketch `history/`.  
3. Calling `event` “E4 evidence” names the **consumer lane**, not “lands in `sketch.v1` today.”  
4. Motadata A/B freeze layout: **`history/` = sketches**, **`map/` = graph**, traces / logs / anomalies live on **sibling evidence surfaces** (or CaseSeed / Signal objects on the case path). Bakeoff Lean is the multi-modality UC-bundle picture.

### Q52. How does this relate to Pillar A/B admit and the interleaved demo?

**A.** Unchanged admit rules:

| Writer | Admits | Skips (NOOP) |
|--------|--------|--------------|
| SketchWriter (A) | `metric_sample` | `topo_update`, `event`, `trace_span`, `anomaly`, … |
| GraphWriter (B) | `topo_update` | `metric_sample`, `event`, `trace_span`, `anomaly`, … |

The [stream → graph demo](../../../docs/fabric/pillar-b-stream-graph-demo.html) shows A/B NOOP for those three kinds on purpose. Downstream Detect / Diagnose consumption is **out of Pillar B map mission** (P2/P3 stub harnesses optional). Topology implied by spans / logs still requires a **separate `topo_update`** emitter (§9) — GraphWriter never invents that line from an `event` or `trace_span`.

---

## 16. Writer stream supersession (no `fact_kind`)

### Q53. What replaced `ingest.v1` + `fact_kind` for writer fan-out?

**A.** Locked 2026-09-23 — **superseding**, not a parallel draft:

| Lock | Decision |
|------|----------|
| Common wire | One post-E2 JSON stream: **`writer_stream.v1`** |
| Router enum | **No `fact_kind`** — writers infer from optional blocks present |
| Shape | Explicit optional blocks: `topology`, `metric`, `event`, `span`, `anomaly` |
| Regulators | Per-writer orchestrator projects an intent (`graph_write_intent.v1` / `sketch_admit_intent.v1`) |
| Graph admit | `topology.relation` + `src_ci_id` + `dst_ci_id` **and** `identity.status = resolved` (MUST) |
| Dual line | One object may carry both `topology` and `metric` — **both regulators fire** |
| Vocabulary | Fusion **eleven** camelCase on the wire + [`RELATION_MAPPING.md`](../../contracts/RELATION_MAPPING.md) → Motadata Dest fifteen |
| Deliverable | Wire + intents now; Dest `graph_*.v1` Fusion refresh is follow-on |
| Lab / demo | Still teach legacy `fact_kind` until fixtures migrate |

Normative: [`WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md) · schemas under [`../../contracts/schemas/`](../../contracts/schemas/).

### Q54. Does this break today’s PoC GraphWriter?

**A.** Not yet at runtime. Code and JSONL still admit on `fact_kind == topo_update`. Contracts mark `ingest.v1` **deprecated**; TEAM_WALKTHROUGH and the stream→graph demo call out the supersession so docs do not fight the new wire. Fixture + writer code migration is the next implementation step; Dest Motadata SCREAMING_SNAKE edges stay until Dest schemas are refreshed.

---

## 17. Chronological topic index

Use this to verify coverage against the chat. Numbers are approximate order in the recovered session.

| # | Topic | Captured in |
|---|--------|-------------|
| 1 | Transcript restore; ignore Edge Delta | §1 |
| 2 | HLD/Identity locks restated; redirect to Pillar B history | §1 |
| 3 | `_make_node` / bootstrap rename bugfix | §1 |
| 4 | Call graph how-to (`code2flow`, hierarchy, dynamic) | §4 |
| 5 | `code2flow` depth flags; clean curated graphs + one-liners | §4 |
| 6 | Tests A vs B; expand walk depth (B1–B3) | §12 |
| 7 | Fabric film 2 explained | §3 |
| 8 | Increments 2–3 as stubs; MAP_P2 / MAP_P3 | §3 |
| 9 | Two-use-case framing; remove `POC_TWO_USE_CASES.md` | §2 |
| 10 | Happy path → dual call sequences on navigator | §2 |
| 11 | Admit NOOP/WRITE/DROP (+ phased skip) with examples | §8 |
| 12 | Who stamps line kind; telemetry may imply topo via emitters | §7 · §9 |
| 13 | Where `stream.*.jsonl` lives | §5 |
| 14 | Full GraphWriter I/O + file inventory | §6 |
| 15 | Packaged estate map; GraphState vs `graph_snapshot.v1` | §6 |
| 16 | JSONL word wrap | §14 |
| 17 | Canvas preview / Open Canvas behavior | §13 · §14 |
| 18 | Team walkthrough; writers + admit; bind_source; navigator walk relate | §2 · §7 · §8 · §11 |
| 19 | No bare `ingest.v1` file; expand `ingest.example.json` to five kinds | §5 |
| 20 | Origin of kinds; bind vs provenance; consumer table; rename discussion | §7 · §11 |
| 21 | Logs → `event`; hub discussion note | §7 |
| 22 | Link fact-kinds note on Our HLD Overview | §13 |
| 23 | Docs hub audit + PoC integration | §13 |
| 24 | Tier/Band/Door clutter → Everyone/Implementers | §13 |
| 25 | `INGEST_DATA_FORMAT.md` consistency audit | §7 |
| 26 | Remove Tier chips / “one-stop” from PoC hub copy | §2 · §13 |
| 27 | Canvas 404s → Pillar B PoC hub doors + symlinks | §13 |
| 28 | `reference/` vs `references/` → `archived-docs` | §13 |
| 29 | Oversized Codebase-go-through images; layers SVG / Dest overlap | §4 · §13 |
| 30 | Rename radius; reject `telemetry_kind`; hard-cut to `fact_kind` | §7 |
| 31 | Remove `linux-server-ci-telemetry.json` | §5 |
| 32 | Reference canvas `//@ts-nocheck` | §13 |
| 33 | Production stream vs NATS | §5 |
| 34 | Estate rename + fact_kind nomenclature stance | §3 · §5 · §7 |
| 35 | Production topo from other kinds + interleaved JSON scenario | §9 · §10 |
| 36 | This Q&A document | (this file) |
| 37 | Who consumes `event` / `anomaly` / `trace_span` and **how** (not A/B NOOP) | §15 |
| 38 | Do anomaly / span land in E4 “evidence history” for Triage + Diagnose? | §15 |
| 39 | `writer_stream.v1` supersedes `fact_kind`; regulators + intents; Fusion camelCase map | §16 |

---

## Document history

| When | What |
|------|------|
| 2026-09-22 | Initial session Q&A (shorter) |
| 2026-09-22 | **Expanded to comprehensive capture** — restore/Identity context, increments/films, call graphs, full I/O inventory, rename radius + `telemetry_kind` rejection, hub/canvas hygiene, walk test bands, interleaved stream, chronological index |
| 2026-09-23 | **§15** — who consumes `event` / `anomaly` / `trace_span` and **how**; E4 sketch `history/` vs sibling evidence stores for Triage + Diagnose (Q50–Q52) |
| 2026-09-23 | **§16** — `writer_stream.v1` / regulator / intent supersession of `fact_kind` (Q53–Q54); chronological renumbered to §17 |
| 2026-09-23 | Removed redundant fact_kind teaching pages (discussion notes, interleaved MD, fan-out art); §7 collapsed to legacy pointer |
