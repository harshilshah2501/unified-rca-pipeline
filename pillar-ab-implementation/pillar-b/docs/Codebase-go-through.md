# Codebase go-through — Pillar B map PoC (P1 / Increment 1)

**Doc job:** walk the **code and sample estate** so a cold reader knows which file does which job on the write path into `map/`.  
**Not this page:** stage eval matrix and admit terminology → [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md). Package I/O front door → [`../README.md`](../README.md). Doc map → [`README.md`](./README.md).

**What this PoC proves:** after Identity, Motadata can build and keep a `map/` knowledge graph from optional **estate bootstrap** + a `topo_update` stream, without writing sketches, without CaseSeed, and without implementing live discovery.

**Home package:** `pillar-ab-implementation/pillar-b/` · **Runnable lab:** `pillar-b/poc/`

```bash
cd pillar-ab-implementation/pillar-b/poc
make install && make test-all
make publish-map    # optional: write poc/out/<tenant>/map/
```

---

## 1. Runtime spine (follow this in code)

```mermaid
flowchart LR
  Boot["topology.bootstrap.json<br/>estate bootstrap optional"]
  Stream["stream.*.jsonl<br/>topo_update post-E2"]
  GW[GraphWriter]
  State[GraphState]
  Flush[publish_map]
  Map["map/ GraphSnapshot"]
  Maint["maintain_map<br/>E5 optional"]
  Reflush["re-publish_map<br/>version bump"]

  Boot --> GW
  Stream --> GW
  GW --> State --> Flush --> Map
  State -.-> Maint --> Reflush -.-> Map
```

![Same spine as PNG — use if Mermaid preview is off](./runtime-spine.png)

`GraphWriter` is a thin orchestrator: `load_estate_bootstrap` → `write_topo_stream` → `publish_map` → optional `maintain_map`. Lab CLI: [`../poc/graph/cli_publish_map.py`](../poc/graph/cli_publish_map.py) (`make publish-map`).

---

## 2. Package layout (what lives where)

```text
pillar-b/
├── README.md                 ← package front door (I/O + admit)
├── docs/                     ← PoC guides only (this page, MAP_P1, doc map)
├── contracts/schemas/        ← schema symlinks → slice SoT (required by tests)
├── references/               ← OPTIONAL product HTML (not PoC SoT)
└── poc/                      ← runnable code + sample estate + tests
    ├── ab_shared/            ← gate, dest, ingest, schema helpers
    ├── graph/                ← sole map writer path
    ├── sample_estate/customer_checkout/  ← teaching estate inputs (not live CMDB)
    └── out/                  ← FileDest after make publish-map
```

Do not confuse with:

- **`pillar-a/`** — sketches into `history/` (E4). GraphWriter NOOPs those lines.
- **`integration/`** — optional read-join only, not an A∪B merge product.

---

## 3. Shared glue — `poc/ab_shared/`

These modules are **not** the Topology writer. They are small utilities the writer (and tests) depend on so Pillar B can behave like a post-Identity consumer without reimplementing Collect or the full Identity LUT.

Pillar B sample-estate inputs already look like post-Identity `ingest.v1`. Collect is Done elsewhere; this package **simulates** its output.

### `identity_gate.py` — who may become map work

Identity (E2) stamps `identity.status` on each line. GraphWriter must not invent a second policy. `ResolvedOnlyGate.admit(record)` returns accepted only when status is `resolved`. Unresolved or synthesized lines become **DROP** reasons on the reject tape — they never silently create nodes or edges.

This is the hard door into E3. Full `telemetry_key_index` LUT is Design (named in MAP_P1); the PoC only enforces the resolved-only gate.

### `ingest_source.py` — how lines enter the writer

Abstracts “a stream of dict records.” Lab uses `JsonlIngestSource` (files under `sample_estate/customer_checkout/`). Unit tests use `ListIngestSource` so cases can inject one-off NOOP/DROP lines without new sample-estate files.

### `dest.py` — where `map/` lands

Gate B style destination: `put("map", filename, bytes)` / `get(...)`.

- **`MemoryDest`** — tests (no disk).
- **`FileDest`** — `make publish-map` writes under `poc/out/<tenant>/map/`.

GraphWriter never opens paths itself; snapshot publish always goes through Dest.

### `schema.py` — shape checks before publish

Loads mirrored JSON Schema from `pillar-b/contracts/schemas/` and validates nodes, edges, and `graph_snapshot.v1` on flush. Failed validation is a hard fail in tests — the PoC does not ship half-shaped map files.

### `reject_codes.py` — stable DROP strings

Single catalog of reason codes (`identity_unresolved`, `identity_synthesized`, `never_ci_vertex`, `unknown_relation`, …). GraphWriter appends `(record, reason)` pairs; SAMPLE_IO Case B asserts on these strings. Do not invent ad-hoc reject text in builder code.

### `paths.py` — sample estate root

`SAMPLE_ESTATE` points at `poc/sample_estate/customer_checkout/` so tests and CLI share one path constant.

### `clock.py` — lab time helper

`FrozenClock` exists for shared patterns with Pillar A. E5 maintain in this PoC currently takes an explicit `as_of` timestamp string (lab clock) rather than injecting `FrozenClock` everywhere — see `maintain.py`.

---

## 4. Map writer core — `poc/graph/`

Call order on the happy path: **`graph_writer`** orchestrates → **`graph_builder`** mutates `GraphState` → **`snapshot`** validates and publishes → optional **`maintain`** then re-flush.

### `graph_writer.py` — public API

The only class most callers need. Methods mirror the spine:

1. `load_estate_bootstrap(...)` — optional estate starting map (not CaseSeed).
2. `write_topo_stream(source)` — upsert admitted topo lines into GraphState via `apply_topo_stream`.
3. `publish_map(dest, version=...)` — validate + publish `graph_snapshot.v1` to Dest.
4. `maintain_map(as_of, ...)` — E5 pass on existing edges; does not create edges.

Rejects are exposed as `writer.rejects` (list of `(record, reason)`).

### `graph_builder.py` — in-memory estate + admit triage

Owns `GraphState` (`nodes`, `edges`, `rejects`).

- **`load_estate_bootstrap_state`** — reads `topology.bootstrap.json`, qualifies CI types, emits declared edges with provenance `topology.bootstrap`.
- **`apply_topo_stream`** — the E3 heart: for each line, choose NOOP / WRITE / DROP / phased skip. (“Admit” = that per-line triage — [terminology](./MAP_P1_FABRIC_EVAL.md#terminology-do-not-blur).)
- **`_make_node` / `_make_edge`** — after admit, shape `graph_node.v1` / `graph_edge.v1` objects (same helpers for bootstrap and stream; callers pass different provenance / `valid_from`).

```python
# apply_topo_stream outline:
# signal_class != topo_update → NOOP
# gate / never-CI / unknown relation → DROP
# classify_relation skip → phased map-NOOP
# classify_relation emit → WRITE via _make_node (endpoints) + _make_edge
```

Outcome table (NOOP / WRITE / DROP) lives in the [package README](../README.md#admit-actions-hub-language--code) — not duplicated here.

### `ci_qualify.py` — which vertex types may exist on the map

Configuration-item (CI) allow/deny. Alert, Change, Incident, tickets, and similar **never-CI** types return DROP (`never_ci_vertex`). Wave-1 service/host/runtime/database types may emit. Prevents case objects from becoming estate nodes.

### `edge_catalog.py` — relation names and wave-1 phasing

Fifteen Motadata relation names. `classify_relation` returns:

- **emit** — wave-1 WRITE (`runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`).
- **skip** — in catalog but not wave-1 yet (e.g. `mounts`) → phased map-NOOP, usually not a DROP.
- **reject** — unknown name → DROP `unknown_relation`.

### `provenance.py` — how an edge claims it was discovered

Builds `discovered_via` blocks: `authoritative` / `declared` / `corroborating`, plus confidence and telemetry source. Bootstrap edges are `declared` + `topology.bootstrap`. Stream bind sources (inventory, catalog, apm, …) map to evidence types via `evidence_for_source`. E5 uses evidence type when decaying corroborating or declared edges.

### `snapshot.py` — publish contract for `map/`

`build_snapshot` validates every node/edge and the snapshot envelope. `publish_snapshot` writes Dest keys `graph_snapshot.json`, `nodes.jsonl`, `edges.jsonl`. `load_snapshot` is the read side for tests and neighbors. Normative key meanings: slice [`MAP_WRITE_READ_RECORD`](../../contracts/MAP_WRITE_READ_RECORD.md).

### `maintain.py` — E5 validity (no new edges)

Runs against existing `GraphState`:

- Drop edges past `valid_to`.
- Drop stale **corroborating** edges older than a max age.
- Mark **declared** edges soft-stale (7d) or hard-downgraded (30d) — Design-numeric product defaults; fixture `as_of` drives the clock.

Hard-downgraded edges stay on the published map but leave `confidence_bearing_edges`. Details: [`LLD-E5-Maintain`](../../../docs/observeops/LLD-E5-Maintain.md).

### `neighbors.py` / `read_api.py` — walk a published snapshot

Outbound neighbor walks used in acceptance (“checkout-api reaches payments-db”). Diagnose-scale WorkingSet / leaf-path reads are **not** in this increment.

### `compare.py` — SAMPLE_IO spine equality

Compares expected vs actual on a **spine** of ids/types/relations so provenance display fields can grow without breaking Case A goldens.

### `cli_publish_map.py` — lab entrypoint

Wires bootstrap + resolved stream + `FileDest` (+ optional maintain). Invoked by `make publish-map`.

### Other files in `graph/` (secondary)

| File | When you need it |
|------|------------------|
| `change_fact.py` | Optional change-fact helper — **not** part of `publish_snapshot` |
| `compare.py` | Covered above (SAMPLE_IO) |

---

## 5. Sample estate — `poc/sample_estate/customer_checkout/`

| Artifact | Meaning |
|----------|---------|
| `topology.bootstrap.json` | Estate bootstrap (declared starting map) — **not** CaseSeed |
| `stream.resolved.jsonl` | Case A — five wave-1 `topo_update` WRITEs |
| `stream.reject.jsonl` | Case B — DROP mix + metric/event/trace/anomaly NOOPs |
| `cases/happy_path/` · `cases/reject_tape/` | Golden spines / reject expectations |
| [`SAMPLE_IO.md`](../poc/sample_estate/customer_checkout/SAMPLE_IO.md) | Human expected-vs-actual for Case A/B |
| [`estate README`](../poc/sample_estate/customer_checkout/README.md) | Why this folder exists + file inventory |

---

## 6. Tests — what proves what

| Test file | Focus |
|-----------|--------|
| **`test_p1_map_fabric.py`** | Full P1 matrix: E1 boundary, E2 gate, E3 triage, E4 orthogonality, E5 freshness |
| `test_graph_writer.py` | Happy path flush, silent skip, reject tape |
| `test_sample_io.py` | Case A/B spine equality |
| `test_maintain.py` | Expire / corroborating / declared soft unit cases |
| `test_edge_catalog.py` · `test_ci_qualify.py` · `test_provenance.py` | Catalog / CI / evidence helpers |
| `ab_shared/tests/` | Gate, dest, schemas, clock |

Eval narrative for those proofs: [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md).

---

## 7. Pipeline stages → this tree

| Stage | In this codebase | Look at |
|-------|------------------|---------|
| **E1 Collect** | Not implemented; simulated by sample-estate spine | `test_e1_*` in `test_p1_map_fabric.py` |
| **E2 Identity** | Gate only (`ResolvedOnlyGate`); no LUT | `ab_shared/identity_gate.py` |
| **E3 Topology** | Sole map writer | `graph_writer` → `graph_builder` → `snapshot` |
| **E4 Stores** | Absent by design here; non-topo lines NOOP | `test_e4_mixed_tape_*` |
| **E5 Maintain** | Validity on existing edges | `maintain.py` + `maintain_map` |

**Estate bootstrap** (`load_estate_bootstrap`) ≠ **CaseSeed** (P2/E7). Bootstrap fills `GraphState` before the stream; CaseSeed never writes `map/` in this PoC.

---

## 8. Hands-on path (15–20 minutes)

1. [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) — stage matrix once.  
2. Skim `topology.bootstrap.json` + first lines of `stream.resolved.jsonl`.  
3. Read `GraphWriter` then `apply_topo_stream` end-to-end.  
4. `make test-all` — if green, the contract holds.  
5. `make publish-map` — inspect `poc/out/default/map/graph_snapshot.json`.  
6. Skim `test_p1_map_fabric.py` section headers (E1→E5).  
7. Optional: [hub GraphWriter tab](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter).

---

## 9. Explicit non-goals

- No E6–E11 map **reads** (CaseSeed → WorkingSet → leaf path)  
- No eight use-case fixture packs  
- No live discovery crawler / `telemetry_key_index` LUT  
- No SketchWriter inside Pillar B  
- Vortex/S3 encodings deferred — PoC Dest is `files.v1` only  

This tree is the **P1 always-on fabric write path** only.

---

## Clarifications

### Who calls the public `GraphWriter` API?

`GraphWriter` is **not** an HTTP service and not called by Detect/Diagnose in this PoC. Callers today:

| Caller | Role |
|--------|------|
| [`cli_publish_map.py`](../poc/graph/cli_publish_map.py) (`make publish-map`) | Lab operator entry — bootstrap → write_topo_stream → publish_map → optional maintain_map |
| Unit / P1 tests under `poc/graph/tests/` | Acceptance proofs |
| [`integration/join/`](../../integration/join/) (optional) | Read-join smoke that builds a map then joins sketches |

**Product intent (not implemented here):** a **Topology writer** after Identity would call the same sequence on a continuous `topo_update` stream (plus optional CMDB/estate bootstrap). Diagnose stages (E6–E11) **read** `map/` via snapshot/neighbors — they do not call `write_topo_stream` / `publish_map`.

Internal helpers (`apply_topo_stream`, `may_emit_vertex`, …) are for `GraphWriter` and tests — not a second public surface.

### Python files by purpose and scope

These scopes match the **Pillar B map PoC navigator** canvas layers. They are file roles, not Motadata pipeline stages.

**How they relate (call / dependency direction):**

```mermaid
flowchart TB
  entry[Lab entry] -->|calls| orch[Public orchestrator]
  orch -->|uses| core[Write core]
  core -->|uses| shared[Shared glue]
  core -->|publish_map| dest((Dest map/))
  read[Read helpers] -->|reads| dest
```

**Spine** is the whole write story (not a separate package). **Production surfaces** encode Dest `map/` (plus the `ingest.v1` stream) — not a GraphWriter HTTP API.

**GraphWriter call sequence:**

```mermaid
flowchart LR
  boot[load_estate_bootstrap]
  stream[write_topo_stream]
  pub1[publish_map]
  maint[maintain_map<br/>optional E5]
  pub2[publish_map<br/>re-flush]

  boot --> stream --> pub1
  pub1 -.->|optional| maint --> pub2
```

**Cold-reader order** (same as the navigator):

1. **Spine** — one write story into `map/`  
2. **Public orchestrator** — only write API (`graph_writer.py`)  
3. **Lab entry** — `make publish-map` / CLI (PoC only)  
4. **Write core** — builder, catalog, qualify, snapshot, maintain  
5. **Shared glue** — `ab_shared` gate / Dest / ingest / schema  
6. **Read helpers** — neighbors / load snapshot after publish  
7. **Production surfaces** — Dest rooms + stream honesty (read last)

| Scope | Folder / file | Job | Who should import it |
|-------|---------------|-----|----------------------|
| **Public orchestrator** | `graph/graph_writer.py` | Sole write API for `map/` | CLI, Topology writer (future), tests |
| **Lab entry** | `graph/cli_publish_map.py` | Wire files → writer → Dest | Humans via `make publish-map` only |
| **Write core** | `graph_builder.py`, `ci_qualify.py`, `edge_catalog.py`, `provenance.py`, `snapshot.py` | Mutate/validate estate → publish | Only `graph_writer` (+ focused unit tests) |
| **Maintain (E5)** | `graph/maintain.py` | Validity on existing edges | `graph_writer.maintain_map` |
| **Read helpers** | `neighbors.py`, `read_api.py` | Walk a published snapshot | Tests; later Diagnose readers |
| **Test-only compare** | `compare.py` | Spine equality for SAMPLE_IO | Tests only |
| **Secondary** | `change_fact.py` | Optional change facts — not part of `publish_snapshot` | Ignore for P1 map path |
| **Shared utilities** | `ab_shared/*` | Gate, Dest, ingest sources, schemas, reject codes | Writer + tests (Pillar A–style shared patterns) |
| **Sample estate / paths** | `ab_shared/paths.py`, `sample_estate/` | Sample estate locations | CLI + tests |

Rough layering: **CLI/tests → `GraphWriter` → builder/catalog/qualify/provenance → snapshot/Dest**. Do not call builder from Diagnose.

### Method names → plain meaning

| Name you see | Plain meaning |
|--------------|---------------|
| `load_estate_bootstrap` | Load optional **starting estate** JSON into memory (not CaseSeed) |
| `write_topo_stream` | Admit-triage `topo_update` lines and **upsert into in-memory GraphState** (not Dest yet) |
| `publish_map` | **Validate** GraphState + **write** `graph_snapshot.v1` / nodes / edges to Dest `map/` |
| `maintain_map` | E5 pass: expire / stale-corroborating / declared soft·hard marks — **no new edges** |
| `rejects` | DROP tape: `(record, reason_code)` pairs from this run |
| `apply_topo_stream` | Per-line admit loop (NOOP / WRITE / DROP / phased skip) |
| `load_estate_bootstrap_state` | Bootstrap load returning a bare `GraphState` (builder-level) |
| `_make_node` / `_make_edge` | Shape `graph_node.v1` / `graph_edge.v1` after admit (bootstrap + stream) |
| `classify_relation` | Relation name → emit / skip / reject |
| `may_emit_vertex` | CI type allowed on map? else DROP |
| `build_snapshot` / `publish_snapshot` | Assemble validated snapshot / write Dest keys |
| `admit` (on `ResolvedOnlyGate`) | Identity gate check only — not GraphWriter’s full NOOP/WRITE/DROP table |

Renames above are the current public verbs (`load_estate_bootstrap` / `write_topo_stream` / `publish_map` / `maintain_map`).

### Production surfaces (HTTP / RPC / Dest) — what other subsystems use

Honest freeze vs Design (Motadata SoT: [`GATE_B_DEST_PROFILE`](../../contracts/GATE_B_DEST_PROFILE.md) · [`MAP_WRITE_READ_RECORD`](../../contracts/MAP_WRITE_READ_RECORD.md) · pipeline HLD):

| Surface | Audience | Purpose | Status |
|---------|----------|---------|--------|
| **Ingest stream** (`ingest.v1` after E2) | Topology writer (internal) | Continuous `topo_update` lines into GraphWriter `write_topo_stream` | PoC simulates; product Topology writer = Design |
| **Estate bootstrap load** | Topology / CMDB sync job | Optional starting map (`load_estate_bootstrap`) before stream | PoC file; product CMDB pull = Design |
| **Dest write protocol** `put("map", key, bytes)` | GraphWriter only | Publish `graph_snapshot` / nodes / edges into the `map/` room | **Frozen logical contract**; PoC encoding `files.v1` |
| **Dest read protocol** `get("map", "graph_snapshot.json")` | E5 maintain, E8 Scope, Diagnose | Load packaged snapshot; walk neighbors | **Frozen logical contract** |
| **Vortex (hot) + S3 (cold)** | Same Dest adapters | Production temperature encodings of the **same** logical keys/fields | Design / later — not a second schema |
| **Public REST/gRPC “GraphWriter API”** | External product callers | — | **Not frozen.** Product does not expose GraphWriter as a third-party CRUD HTTP API in current HLD; other Motadata stages talk via **rooms + Dest** (and later UI over those reads) |

What Diagnose / Scope need is **read access to `map/`** (snapshot + neighbor walk), not write RPCs into GraphWriter. What Collect/Identity provide is the **stream**, not an HTTP call into Pillar B.

### Interactive code navigation (Cursor)

No Motadata-specific navigator is required:

1. Open `pillar-ab-implementation/pillar-b/poc` (or repo root) in Cursor.  
2. Enable **Python** + **Pylance**.  
3. On a symbol: **Go to Definition** (F12), **References** (Shift+F12), **Call Hierarchy** (command palette).  
4. Start at `graph_writer.py` → F12 into `apply_topo_stream` → References on `GraphWriter` for CLI + tests.  
5. In chat: `@graph_writer.py` or ask for the call chain from `publish_map`.  

Editor navigation + this go-through + the in-repo canvas [`../reference/canvases/pillar-b-poc-navigator.canvas.tsx`](../reference/canvases/pillar-b-poc-navigator.canvas.tsx) (open beside chat) are the interactive maps for this PoC.
