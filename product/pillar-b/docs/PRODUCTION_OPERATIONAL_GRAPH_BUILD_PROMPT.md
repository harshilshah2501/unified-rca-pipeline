# Build prompt — production Motadata operational (knowledge) graph

**Purpose of this file:** Paste the block under **§ Prompt (copy from here)** into a fresh agent / Cursor chat (or a new private Rust repo) to scaffold a **production-grade** operational graph service. Everything above that section is orientation for humans; the prompt itself is self-contained.

**Foundation:** Unified-RCA ObserveOps Pillar B PoC (`map/` room) + Rust `map_vortex` + Vortex/S3 contracts.  
**Canonical tree on this machine:** `/root/Harshil-PoCs/Unified-RCA/product/`  
(`pillar-ab-implementation` → `product` symlink; `docs` → `knowledge` symlink.)

---

## Prompt (copy from here)

````markdown
# Mission

Build a **new, dedicated Rust project** for a **production-grade Motadata operational (knowledge) graph** — the ObserveOps **`map/`** room (Pillar B / Topology). Treat the existing Unified-RCA PoC as a **proven foundation to port and harden**, not as throwaway demo code and not as a second sketch/`history/` product.

This service owns **configuration-item (CI) vertices + typed edges**, hot in-process walk state, immutable cold **Vortex** checkpoints on **S3** (or S3-compatible object storage), admit/maintain/publish/load APIs, and Scope-ready adjacency walks. It does **not** own sketches, Detect, Curate, or Verdict packaging.

Suggested repo slug: `motadata-operational-graph` (or `map-vortex-prod`). Private Rust workspace. Commit early; README must state what it proves and how to run.

---

# Product definition (non-negotiable)

## What “operational graph” means here

- A **walkable dependency / topology map** of Motadata **configuration items** (services, hosts, databases, …) and **typed relationships**.
- Downstream ObserveOps stages (Scope / Localize / Identify) **read** this map; they must not open object storage once per neighbor hop.
- The graph is the localization moat: a detector without a map yields an alert; a detector **with** a fresh walkable map can defend a leaf.

## Three axes — never merge them

1. **Room (content):** `map/` = topology CIs + edges. `history/` = sketches / change facts (Pillar A). **Two writers, no continuous sync.** Join at read by Dest tenant + `entity_id`.
2. **Temperature:** **Hot** = in-process Arrow/Vortex Arrays + adjacency index (mutate on admit/maintain). **Cold** = immutable `.vortex` objects on Dest/S3 (new snapshot version only — never patch an old file).
3. **Dest profile (encoding):** Lab used `files.v1` (JSON/JSONL). Production target is **`vortex_s3.v1`** (columnar `.vortex` + ObserveOps manifest). Same logical row fields for both.

## Hard Motadata storage locks

| Lock | Rule |
|------|------|
| Tables | Exactly **two** columnar tables: `map_nodes`, `map_edges`. No Vortex table for `graph_snapshot.v1` (that envelope is lab/files packaging only). |
| Tenant | **Not** a column on node or edge rows. Tenant lives on Dest path / `latest` / snapshot envelope. |
| Join key | `entity_id` (Utf8) ≡ ingest `ci_id` ≡ sketch `entity_id` within Dest tenant. |
| Edge upsert key | `(source_id, edge_type, target_id)`. `edge_id` is a **UInt64 snowflake** allocated once per upsert key and **reused on refresh**. |
| Evidence | `evidence_event_id` UInt64 snowflake. **No** stored `discovered_via` on Motadata edges. |
| Edge types | Closed fifteen Motadata **SCREAMING_SNAKE** names only (see below). Ingest snake_case / Fusion camelCase map in; unknown relation → **DROP**. |
| Vertices | **CI-only**. Alert / incident / metric / trace / change / ticket are **never** vertices. |
| Clocks | **UInt64 Unix epoch milliseconds UTC**. Nullable only where schema allows (`valid_from` / `valid_to`). |
| Promoted tags | Closed **`attr_catalog.v1`** on nodes only: `env`, `region`, `owner`, `namespace`. No unbounded JSON `metadata` bag on cold Vortex. Edges have **no** tag columns. |
| Publish | Parts → `manifest.json` → `latest.json`. Incomplete generations stay invisible. |
| Walks | After `load_map` (or live upserts), walks hit **hot adjacency**. Never per-neighbor S3/Vortex open. |
| Maintain (E5 Level-1) | Validity / freshness on **existing** rows (expire `valid_to`, stale stream drop, declared soft/hard). Does **not** invent topology. |
| Explicit retire (Level-2) | Separate admin path: close edge or retire node (cascade incident active edges); then publish. Do **not** fold into E5. |

### Fifteen Motadata `edge_type` values (closed enum)

```
DEPENDS_ON
RUNS_ON
MOUNTS
CONNECTS_TO
BACKS
USES
HOSTED_ON
MEMBER_OF
PART_OF
ROUTES_THROUGH
AUTHENTICATES_VIA
MONITORED_BY
BACKED_UP_BY
CLUSTERED_WITH
COMMUNICATES_WITH
```

Illegal Motadata storage-type × relation pairs **DROP** (do not warn-and-write). Normative allowlist lives in the PoC contract `EDGE_TRIPLET_ALLOWLIST.md`.

### Admit gates (before any hot mutate)

| # | Gate | Fail |
|---|------|------|
| 1 | Complete claim (`src`, `dst`, `relation`) | **NOOP** |
| 2 | Identity resolved | **DROP** `identity_*` |
| 3 | Both ends are CI vertices | **DROP** `never_ci_vertex` |
| 4 | Fifteen relations + Motadata types + triplet allowlist | **DROP** catalog / triplet codes |

Outcomes: `NOOP` | `WRITE` | `DROP` only.

### Lifecycle stages (S0–S6) — implement in this order

| Step | Name | Behavior |
|------|------|----------|
| S0 | Stream line | Topology claim arrives (`writer_stream.v1` / topo line). |
| S1 | Admit | Gates 1→4; never mutate on fail. |
| S2 | Hot upsert | On WRITE: upsert nodes/edges + refresh adjacency. **No** cold PUT per line. |
| S3 | Publish checkpoint | Materialize **new** `map_nodes` / `map_edges` parts (`.arrow` lab optional; `.vortex` required for Motadata path). Prefer edge row order `source_id → edge_type → target_id` (clustered publish). |
| S4 | Cold visibility | Write `manifest.json`, then `latest.json`. |
| S5 | Load map | `latest` → manifest → Vortex parts → Arrow; rebuild hot Arrays + **adjacency from edge spine**. Prefer **spine projection** on walk rebuild. |
| S6 | Walk | `neighbors` / bounded BFS / WorkingSet against hot index. |

**Spine columns (first lookup / adj rebuild):**

- Nodes: `entity_id`, `type`
- Edges: `source_id`, `target_id`, `edge_type`

Defer tags, clocks, `edge_id`, `evidence_event_id` until filter/UI needs them.

### Dest object layout (`vortex_s3.v1`)

```text
map/<tenant>/snapshots/<version>/
  manifest.json                 # map_snapshot_manifest.v1
  nodes/part-NNNNN.vortex
  edges/part-NNNNN.vortex
map/<tenant>/latest.json        # { "version": "…" }
```

Two footer stories (do not confuse):

- **Inside each `.vortex`:** Vortex layout tree + postscript (`VTXF`) — owned by the Vortex writer.
- **Across Dest objects:** ObserveOps `manifest.json` + `latest.json`.

### Public service surface (minimum)

```text
Dest.put / Dest.get / Dest.list_keys          # FileDest + S3Dest
upsert_topo / write_topo_stream              # admit + hot mutate
maintain_map(as_of)                          # E5 Level-1
retire_edge / retire_node                    # Level-2 (wire explicitly)
publish_map(tenant) → version
load_map(tenant, version?)
neighbors / bfs_reach / paths                # hot walks
working_set(seed, hop_budget, relation_profile)
```

Read-cache ladder: L1 hot Arrays+adj → L2 WorkingSet (capped) → optional L3 query memo keyed by `(tenant, version, …)`. Invalidate on publish / restart.

### Columnar schemas (physical)

**`map_nodes`:** `entity_id` Utf8, `type` Utf8, `name` Utf8, `env`/`region`/`owner`/`namespace` Utf8 nullable, `last_seen` UInt64, `valid_from`/`valid_to` UInt64 nullable, `version` UInt32.

**`map_edges`:** `edge_id` UInt64, `source_id` Utf8, `target_id` Utf8, `edge_type` Utf8 (dict-friendly), `valid_from`/`valid_to` UInt64 nullable, `evidence_event_id` UInt64.

Generate Arrow `Schema` from physical overlays (do not hand-edit generated schema modules). Keep a `make check-map-physical`-style drift gate.

---

# What already exists in Unified-RCA (reuse / port)

**Workspace root:** `/root/Harshil-PoCs/Unified-RCA/`  
**Canonical product tree:** `product/` (alias `pillar-ab-implementation/`).

## A. Normative contracts (SoT — copy into the new repo’s `contracts/` or git-submodule / path dep)

| Artifact | Path under Unified-RCA |
|----------|------------------------|
| Map write/read + Dest §6 | `product/contracts/MAP_WRITE_READ_RECORD.md` |
| Hot/cold lifecycle + admit + removal | `product/contracts/MAP_HOT_COLD_LIFECYCLE.md` |
| Locked Vortex columns | `product/contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md` |
| Writer cohesion (map vs history) | `product/contracts/MAP_WRITER_VORTEX_COHESION.md` |
| Scope walk policy | `product/contracts/MAP_SCOPE_WALK_POLICY.md` |
| Triplet allowlist | `product/contracts/EDGE_TRIPLET_ALLOWLIST.md` |
| Relation mapping (ingest → SCREAMING) | `product/contracts/RELATION_MAPPING.md` |
| Reject codes | `product/contracts/IDENTIFIED_STREAM_REJECT.md` |
| Node/edge/snapshot/manifest JSON Schemas | `product/contracts/schemas/graph_node_v1.schema.json`, `graph_edge_v1.schema.json`, `graph_snapshot_v1.schema.json`, `map_snapshot_manifest_v1.schema.json` |
| Physical overlays | `product/contracts/schemas/graph_node_v1.physical.json`, `graph_edge_v1.physical.json`, `MAP_PHYSICAL_OVERLAY.md` |
| Samples / discussion brief | `product/contracts/GRAPH_NODE_EDGE_SAMPLES.md`, `GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`, `GRAPH_QNA.md` |
| Schema generate/check scripts | `product/scripts/map_physical_schema.py` (+ `make generate-map-arrow-schema` / `check-map-physical` from product Makefile) |

## B. Rust PoC crate to graduate (primary code foundation)

Path: `product/pillar-b/map-vortex/`

| Module / bin | Port as |
|--------------|---------|
| `admit`, `ci_qualify`, `edge_type` | Production admit library (gates 1–4) |
| `hot` (`HotMap`, `TopoLine`, snowflake) | Hot store; replace lab snowflake with Motadata ID service adapter |
| `schema` (generated), `tables`, `types`, `write` | Columnar materialize |
| `manifest`, `publish`, `load` | Cold checkpoint / rebuild |
| `snapshot_json` | Optional files-profile / fixture bridge only |
| bins `map_vortex_demo`, `map_vortex_cold` | Keep as CLI; add `map-graphd` service binary |

**Done in PoC:** Phase A (cold publish/load), Phase B (admit + hot upsert).  
**Must finish in production project:** Phase C (adjacency / neighbors), Phase D (`Dest` + real S3), Phase E (maintain + explicit retire wire), WorkingSet + cache policy, incomplete-publish tests, JSON Schema validation on admit edges.

**Pinned deps to start from:** `arrow` 59.3, `vortex` 0.86 (+tokio), `tokio`, `serde`/`serde_json`, `clap`, `anyhow`, `thiserror`. Add `aws-sdk-s3` (or `opendal`) for S3Dest; `jsonschema` or equivalent for gate validation; tracing/metrics; tokio graceful shutdown.

Docs for this crate: `product/pillar-b/map-vortex/README.md`, `product/pillar-b/docs/MAP_VORTEX_S3_POC_PRIMER.md`, `MAP_ARROW_VORTEX_PIPELINE.md`.

## C. Python PoC behavior reference (parity tests — do not ship Python as the Motadata cold path)

Path: `product/pillar-b/poc/graph/`

| Module | Why it matters |
|--------|----------------|
| `graph_builder.py` | In-memory GraphState + upsert semantics to match |
| `graph_writer.py` | Public verb surface |
| `maintain.py` | E5 Level-1 policy semantics |
| `neighbors.py` / `read_api.py` | Walk / WorkingSet-lite reference |
| `edge_catalog.py` / `edge_triplets.py` | Catalog + allowlist parity |
| `snowflake.py` | Lab ID semantics (replace in prod) |
| `snapshot.py` / `cold_vortex.py` | files.v1 vs vortex_s3.v1 profile switch; subprocess bridge pattern to retire once Rust owns Dest |
| `tests/unit/` | Golden admit/maintain/independence/vortex roundtrip cases |

## D. Sample estate fixtures (port as golden integration tests)

Path: `product/pillar-b/poc/sample_estate/customer_checkout/`

- `topology.bootstrap.json` — declared starting map
- `stream.resolved.jsonl` — post-E2 WRITE tape (Case A)
- `stream.reject.jsonl` — DROP/NOOP mix (Case B)
- `walk_chain.bootstrap.json` — multi-hop walk estate
- `cases/case_a_map_spine/expected_spine.json` — identity spine golden
- `cases/case_b_rejects/expected_rejects.json` — reject code golden
- `expected/graph_node.example.json`, `graph_edge.example.json` — human shape samples
- `SAMPLE_IO.md`, `README.md`

Integration twin (keep sync): `product/integration/sample_estate/customer_checkout/`.

## E. Vortex bench evidence (encode as production packing/load defaults)

Path: `product/vortex-bench/`

- Bench crate: `map-vortex-bench/` (`synth`, `write`, `load`, `adj`)
- Report: `reports/02-map-load-adjacency.md`
- Comparative: `reports/03-comparative-analysis.md`

**Bake into design:**

1. Keep flat two-table schema — do not invent nested map layouts.
2. Cold→hot **adjacency rebuild dominates** wall time; BFS after adj is cheap — optimize load/projection/packing, not walk micro-opts first.
3. Publish edges **clustered** by `source_id → edge_type → target_id` (~10–27% smaller parts; often ~28–55% faster cold→walk at 100k–1M edges in lab).
4. Prefer **spine projection** when rebuilding walks.
5. Test **hubby** (skewed degree) estates, not only uniform synth.

## F. Teaching / HLD context (read; do not re-implement as product features)

- HLD chapter: `knowledge/observeops/OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md` (+ `OBSERVEOPS_PIPELINE_HLD.md`)
- Fabric visuals: `knowledge/fabric/map-arrow-vortex-pipeline.html`, `vortex-s3-interaction.html`, `map-history-storage-blocks.html`, `graphwriter-io-walkthrough.html`, `pillar-b-stream-graph-demo.html`, `inventory-catalog-on-the-map.html`, `storage-formats-vortex-parquet-lance.html`
- Use-case narrative: `knowledge/fabric/KNOWLEDGE_GRAPH_USE_CASES.md`
- Unified film (pipeline context only): `knowledge/fabric/edge-platform-detect-simulation.html`, `SIMULATION_THREAD.md`

## G. Explicitly out of scope / do not port as Motadata DDL

- Pillar A sketch/`history/` writers and T-Digest layouts (`product/pillar-a/`, sketch vortex benches) — join at read only.
- Case-path stubs (`poc/graph/case_path/`, stub diagnose fixtures) — optional later consumers, not the graph core.
- Retired `discovered_via` / `provenance.py` as stored edge fields.
- Archived combined PoC under `archive/pillar-ab-combined-poc-2026-08/` — superseded.
- Live Motadata Vortex **cluster** product (this project targets **file-format Vortex objects on S3** + hot Arrays; cluster integration is a later adapter if Motadata mandates it).

---

# Target architecture for the new Rust project

```text
motadata-operational-graph/
  Cargo.toml                 # workspace
  crates/
    map-graph-core/          # types, admit, HotMap, adj, maintain, retire
    map-graph-vortex/        # Arrow↔Vortex write/load, schema (generated)
    map-graph-dest/          # Dest trait: FileDest, S3Dest, maybe memory
    map-graph-service/       # gRPC and/or HTTP admin + ingest API (tokio)
    map-graph-cli/           # publish/load/demo/bench harness
  contracts/                 # vendored or submodule copies of normative MD + JSON Schema + physical.json
  fixtures/                  # customer_checkout + hubby synth
  benches/                   # criterion: publish, load+adj, BFS
  deploy/                    # systemd unit, Dockerfile, example S3 config
  README.md
```

### Suggested implementation phases (production)

1. **Bootstrap workspace** — move/graduate `map_vortex` modules; CI (`cargo test`, schema drift check, clippy, fmt).
2. **Phase C — Adjacency** — build/rebuild index from edge spine; `neighbors`, hop-bounded BFS; WorkingSet builder; parity tests vs Python `neighbors.py` on fixtures.
3. **Phase D — Dest + S3** — `Dest` trait; FileDest (local path mirroring Motadata key layout); S3Dest (PUT/GET/list, conditional latest); incomplete-publish invisibility tests; IAM/env config.
4. **Phase E — Maintain + retire** — port `maintain.py` semantics; explicit retire API; publish after marks.
5. **Service surface** — durable ingest (NATS/Kafka/HTTP) for topo lines; admin publish/load; health/metrics (admit rates, adj rebuild ms, snapshot version, part sizes).
6. **Hardening** — multi-tenant Dest isolation; crash/restart load; version time-travel `load_map(version)`; property tests on upsert identity; load tests at ≥1M edges with hubby skew; document SLOs for cold→first-walk.

### Non-goals for v1

- Merging `map/` and `history/` stores.
- Graph database query language (Cypher/Gremlin) as the primary API — hot adjacency + typed filters first.
- Storing alerts/incidents as vertices.
- Patching cold `.vortex` files in place.
- Per-hop object-storage walks.

### Acceptance criteria (definition of done for v1)

1. Admit gates 1–4 match PoC reject codes on `stream.reject.jsonl`.
2. Case A spine golden matches after bootstrap + resolved stream + publish + load.
3. `publish_map` writes clustered Vortex parts + valid manifest + latest; crash before manifest leaves version unreadable.
4. Process restart: `load_map` → adj rebuild → BFS from `checkout-api` within hop budget equals Python lab walk on same fixture.
5. S3Dest round-trip on MinIO or real bucket with the Dest key layout above.
6. `maintain_map` expires `valid_to` and applies declared soft/hard without creating edges.
7. Bench gate: document cold→adj→BFS timings; adj ≫ BFS; clustered publish enabled by default.
8. README + runbook: local FileDest demo, MinIO demo, systemd example.

### Engineering standards

- Rust 2021+, edition consistent; `#![deny(unsafe_op_in_unsafe_fn)]`; minimize unsafe.
- `tracing` spans on admit/publish/load/adj_rebuild.
- Errors: typed (`thiserror`) at library boundary; anyhow only at CLI/service edge.
- Config via env + typed config file (tenant root, bucket, prefix, region, endpoint).
- Secrets never in git (`.env` example without keys).
- Physical schema generated from overlays; CI fails on drift.
- Plain language in docs: spell Motadata product terms once; no private Path A/B letter codes.

### How to use the PoC while building

1. Copy contracts + fixtures into the new repo (or path-dependency with clear version pin).
2. Prefer **porting** `map-vortex` modules over rewriting admit/hot/publish.
3. Keep Python lab green as a **behavioral oracle** until Rust parity tests pass, then freeze oracle fixtures.
4. Re-run `map-vortex-bench` ideas as criterion benches inside the new workspace.
5. Do not edit Unified-RCA archive trees; open PRs against the new dedicated repo.

---

# First concrete tasks for the agent

1. `mkdir` + `cargo init` workspace with the crate split above; vendor/copy contracts listed in §A.
2. Import `map_vortex` sources as `map-graph-core` + `map-graph-vortex`; fix paths; `cargo test` green.
3. Implement adjacency + neighbors (Phase C) with fixture parity tests.
4. Implement `Dest` + FileDest + S3Dest (MinIO docker-compose) and wire `publish_map`/`load_map`.
5. Port maintain + retire; add service binary skeleton + README runbook.
6. Stop and report: crate map, remaining gaps vs acceptance criteria, and exact commands to demo FileDest + MinIO.

Begin now. Ask clarifying questions only if a Motadata lock above conflicts with a concrete Motadata platform API you discover; otherwise implement to the locks in this prompt.
````

---

## End of copy block

### Quick pointer for humans

| Need | Open |
|------|------|
| Teaching entry | [`MAP_VORTEX_S3_POC_PRIMER.md`](./MAP_VORTEX_S3_POC_PRIMER.md) |
| Normative Dest / Vortex | [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md) §6 |
| Columns | [`../../contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md`](../../contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md) |
| Rust PoC | [`../map-vortex/`](../map-vortex/) |
| Bench evidence | [`../../vortex-bench/reports/02-map-load-adjacency.md`](../../vortex-bench/reports/02-map-load-adjacency.md) |
| Inventory agent notes | Explore pass in chat that produced this prompt (Pillar B / contracts / benches) |
