# Pillar B PoC — team walkthrough

**Audience:** teammates seeing this package for the first time (demo or review).  
**Package:** Motadata ObserveOps **Pillar B** — knowledge graph / topology writer and walk APIs under Dest room `map/`.  
**Sibling (not this demo):** Pillar A sketch writer → `history/` (same post-Identity stream; SketchRegulator projects metric blocks).

**Wire supersession (2026-09-23):** New writer fan-out uses **`writer_stream.v1`** (optional `topology` / `metric` / … blocks, **no `fact_kind`**) plus per-writer regulators → `graph_write_intent.v1` / `sketch_admit_intent.v1`. See [`../../contracts/WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md). Lab tapes and the stream→graph demo still show legacy `ingest.v1` + `fact_kind` until migrated.

If you only open one page before the meeting, make it **this file**. Framing + layers on the hub: [`pillar-b-poc-hub.html`](../../../docs/fabric/pillar-b-poc-hub.html) ([`:8765/pillar-b-poc-hub.html`](http://127.0.0.1:8765/pillar-b-poc-hub.html)). Optional Cursor panel: Command Palette → **Open Canvas** → `pillar-b-poc-navigator`.

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

1. **Spine story** — After Identity, Motadata fans out: Topology (Pillar B) ∥ Stores (Pillar A). Target wire is `writer_stream.v1` (regulators, no `fact_kind`); lab demo still shows legacy `ingest.v1` admit. Identity / validity / provenance: §5.  
2. **Stream → graph demo** — open [`pillar-b-stream-graph-demo.html`](http://127.0.0.1:8765/pillar-b-stream-graph-demo.html); step Forward/Back through the interleaved tape (left = current line, right = `map/`). Note the banner: demo tape is still `fact_kind` teaching until migrated.  
3. **Show sample tape** — `poc/sample_estate/customer_checkout/stream.resolved.jsonl` (WRITE) and `stream.reject.jsonl` (NOOP + DROP).  
4. **Run** — from `pillar-b/poc`: `make install && make test-all` (optional `make publish-map` → `out/default/map/`).  
5. **Open published map** — `graph_snapshot.json` + `nodes.jsonl` + `edges.jsonl` (note Motadata `entity_id` / `edge_type` / Snowflake `edge_id`; tenant on the snapshot envelope only).
6. **Walk** — point at `neighbors.py` / `read_api.py` and `test_map_walk.py`.  
7. **Call graphs** — [`pillar-b-callgraph.png`](./pillar-b-callgraph.png) (build) · [`pillar-b-walk-callgraph.png`](./pillar-b-walk-callgraph.png) (walk).  
8. **Pillar B PoC hub** — layers + call sequences (build and walk).

---

## 3. How input reaches GraphWriter and SketchWriter

### Contract vs lab tape

| Layer | What it is |
|-------|------------|
| **`writer_stream.v1` (current)** | Common post-E2 stream — **no `fact_kind`**; optional blocks; regulators infer ([`WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md), [`writer_stream_v1.schema.json`](../../contracts/schemas/writer_stream_v1.schema.json)) |
| **`ingest.v1` (legacy)** | Deprecated wire with required `fact_kind` — still used by lab JSONL + stream→graph demo until migrated |
| **Production stream** | Continuous post-E2 feed (bus product choice — NATS optional; HLD does not lock the brand) |
| **This PoC’s stand-in** | Files under `poc/sample_estate/customer_checkout/` — especially `stream.resolved.jsonl` (Case A WRITE) and `stream.reject.jsonl` (Case B DROP/NOOP) |

Estate layout and every file’s job: [`../poc/sample_estate/customer_checkout/README.md`](../poc/sample_estate/customer_checkout/README.md).

### Lab vs target wire (short)

**Target (new writer work):** [`WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md) — `writer_stream.v1` optional blocks; GraphRegulator / SketchRegulator; **no `fact_kind`**.

**Lab PoC today:** fixtures and the stream→graph demo still use deprecated `ingest.v1` with `fact_kind`. GraphWriter admits `topo_update`; SketchWriter admits `metric_sample`; other kinds NOOP. Logs land as `event` on that legacy enum ([`INGEST_DATA_FORMAT.md`](../../../docs/INGEST_DATA_FORMAT.md) §5). Cheat sheet for lab lines: [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md).

```text
                writer_stream.v1   (target — no fact_kind)
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  GraphRegulator   SketchRegulator   (other sinks later)
```

### Node bind vs edge provenance (preview)

| Concern | Lives on | Field | Meaning |
|---------|----------|-------|---------|
| **How did this CI get its id?** | Ingest / stream line | `identity` (esp. `bind_source`) | Which binder attached `ci_id` |
| **How was this relationship proved?** | Edge | `evidence_event_id` (+ optional PoC provenance) | Proving event; E5 uses validity, not `discovered_via` on Motadata Dest |
| **How long is the edge believed?** | Edge | `valid_from` / `valid_to` (lab) or Fusion `ttl` / `lastObserved` (intent) | Validity for Maintain |

Full Identity / validity: **§5**.

### Sample estate folders (Case A/B vs stubs)

| Folder under `cases/` | Meaning |
|-----------------------|---------|
| `case_a_map_spine/` | **PoC core** — golden map spine after `stream.resolved.jsonl` |
| `case_b_rejects/` | **PoC core** — golden DROP codes from `stream.reject.jsonl` |
| `stub_case_path/` | Optional Detect→Localize harness — not map build |
| `stub_diagnose_close/` | Optional Identify/Package harness — not map build |

Full tree: [`customer_checkout/README.md`](../poc/sample_estate/customer_checkout/README.md).

---

## 4. How GraphWriter decides admit (NOOP / WRITE / DROP)

**Admit** = per-line triage inside `apply_topo_stream` — not auth, not Collect schema validation.

| Hub action | When | Effect |
|------------|------|--------|
| **NOOP** | No complete topology claim (lab: `fact_kind` ≠ `topo_update`) | Silent skip; no reject |
| **DROP** | Fail resolved / CI-on-map / known relation / types / allowlisted pair — see [`EDGE_TRIPLET_ALLOWLIST.md`](../../contracts/EDGE_TRIPLET_ALLOWLIST.md) §2 | Append reject reason; map unchanged |
| **WRITE** | All four admit checks pass (any of the fifteen Motadata relations) | Upsert node(s) + edge in `GraphState` |

Code: `poc/graph/graph_builder.py` → `apply_topo_stream`. Lab tapes: `stream.resolved.jsonl` / `stream.reject.jsonl`.

### Relation types on a WRITE

An edge is not “A → B” alone. The wire field **`relation`** is the typed link. Motadata catalog has **fifteen** names; pairing rules for each are in [`EDGE_TRIPLET_ALLOWLIST.md`](../../contracts/EDGE_TRIPLET_ALLOWLIST.md). Lab Case A uses:

| `relation` | Plain meaning | Case A example |
|------------|---------------|----------------|
| `runs_on` | A executes on B (process / runtime on host) | `app-runtime-jvm` --`runs_on`→ `linux-server-app-01` · `checkout-api` --`runs_on`→ `linux-server-app-01` |
| `hosted_on` | Guest / VM on hypervisor (same family as hosting) | (available; not in the five-line Case A tape) |
| `depends_on` | A **needs** B to function (declared dependency) | `checkout-api` --`depends_on`→ `payments-db` (service catalog) |
| `part_of` | A is a **child / component** of parent B (composition) | `checkout-api` --`part_of`→ `bs-checkout` (business service) |
| `communicates_with` | A **calls / talks to** B (observed traffic) | `checkout-api` --`communicates_with`→ `payments-db` (APM) |

**Admit reminder:** every `topo_update` line is **SketchWriter NOOP** (wrong kind for sketches) and **GraphWriter** triage (WRITE / DROP). Never omit `relation` when describing a WRITE.

Full fifteen-name catalog: [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) §4.2.

---

## 5. Identity, bind, provenance, and edge validity

### 5.1 The `identity` object (after E2)

**E2 Identity** stamps an `identity` overlay on every `ingest.v1` line. GraphWriter and SketchWriter do **not** invent it. Collect/adapters + Identity bind LUT own it.

```json
"identity": {
  "status": "resolved",
  "bind_source": "topology_lookup",
  "aliases": ["svc:checkout-api", "monitor-88"]
}
```

| Subfield | What it answers | Allowed / typical values | Who cares |
|----------|-----------------|--------------------------|-----------|
| **`status`** (required) | Did bind succeed enough for production join? | `resolved` · `unattributed` · `synthesized` | Pillar A/B admit **only** `resolved`. Unresolved/synthesized → GraphWriter **DROP** (or Sketch skip). Not E9 leaf / ServiceOps ticket targets (D-E2-1) |
| **`bind_source`** | Which binder attached this `ci_id`? | Free string today: e.g. `topology_lookup`, `inventory`, `apm`, `service-catalog`, `object.name`, `plugin_fallback`, `unbound` | Audit on the **node/line**. PoC also copies it into edge `discovered_via.telemetry_source` → maps to `evidence_type` |
| **`aliases`** | Source-native names for later CMDB/ServiceOps match | Array of strings (monitor id, hostname, IP, …) | Matching aids — **not** competing primary keys. Join key remains `(tenant, ci_id)` |

Related spine fields Identity helps set (outside the nested object):

| Field | Role |
|-------|------|
| `tenant` + ingest `ci_id` ≡ map `entity_id` | Primary join key within Dest tenant for map, sketches, localize, tickets |
| `ci_type` | Vertex type after bind (`Service`, `Host`, `Runtime`, …) |
| `labels.bound` | Older Motadata proxy until `identity.status` is always emitted |

Normative: [`LLD-E2-Identity.md`](../../../docs/observeops/LLD-E2-Identity.md).

### 5.2 `bind_source` (ingest) vs `evidence_event_id` (edge)

| Concern | Lives on | Field | Meaning |
|---------|----------|-------|---------|
| **How did this CI get its id?** | Ingest line | `identity.bind_source` | Which binder attached `ci_id` (admit-time only) |
| **How was this relationship proved?** | Edge on `map/` | `evidence_event_id` | Snowflake; optional PoC `origin` = `declared` \| `stream` for E5 |

Parallel layers: **bind → identity of the vertex (ingest)**; **evidence_event_id → proving event of the edge**. Stored edges no longer carry `discovered_via`. E5 Maintain decays using **`valid_to`**, stream vs declared **`origin`**, and node **`last_seen` / `version`**.

| `evidence_type` | Means | Closer wording |
|-----------------|-------|----------------|
| **`authoritative`** | A system of record **owns** the fact (agent inventory / cgroup, Kubernetes API, …) | Owned by inventory |
| **`declared`** | Human or config **asserted** it (CMDB, service catalog, Helm, Terraform) | Asserted in config |
| **`corroborating`** | Telemetry **suggests** it (APM spans, logs, eBPF peers) | Inferred from live data |

Strength order: authoritative > declared > corroborating. See [`GRAPH_QNA.md`](../../contracts/GRAPH_QNA.md) G8–G11.

### 5.3 Edge validity (`valid_from` / `valid_to`)

**Yes — edges should carry a validity window.** On Motadata `graph_edge.v1` these are **sibling fields** next to `edge_type` (not nested inside a provenance block):

| Field | Role |
|-------|------|
| `valid_from` | When Topology started believing this edge |
| `valid_to` | When belief ends (`null` = open-ended until Maintain changes it) |

Schema: [`graph_edge_v1.schema.json`](../../contracts/schemas/graph_edge_v1.schema.json). Contract note: [`GRAPH_QNA.md`](../../contracts/GRAPH_QNA.md) G9.

**This PoC:** GraphWriter sets `valid_from` from the ingest line’s `ts` and leaves `valid_to` null on WRITE. **E5 Maintain** (`maintain.py`) later:

- expires edges whose `valid_to` is past `as_of`;
- drops stale **corroborating** edges by age when no `valid_to` was set;
- soft-stales / hard-downgrades **declared** edges (product defaults ~**7 days** / ~**30 days** without catalog re-sync or corroboration).

Walk implication: after Maintain, some edges leave confidence-bearing paths even though the CI ids still exist. Product stub: [`LLD-E5-Maintain.md`](../../../docs/observeops/LLD-E5-Maintain.md).

### 5.4 Implications of various `bind_source` values

`bind_source` does **not** set the validity clock by itself. In the PoC it feeds `evidence_type`, which **does** change Maintain / lifetime feel:

| Typical `bind_source` | Mapped `evidence_type` (PoC) | Validity / Maintain feel |
|-----------------------|------------------------------|---------------------------|
| `inventory`, agent, cgroup, kubernetes | **authoritative** | Strongest; keep long-lived / open `valid_to` until inventory withdraws the hosting fact |
| `service-catalog`, `cmdb`, terraform, helm | **declared** | Soft-stale ~7d without refresh; hard-downgrade ~30d; CMDB re-sync resets the clock |
| `apm`, traces, weak / generic telemetry | **corroborating** | Shortest life; often nearer `valid_to` or age-out from `valid_from` if peers stop appearing |

Same estate can hold **both** catalog `depends_on` (declared, longer) and APM `communicates_with` (corroborating, shorter) to `payments-db` — different `relation` and provenance, not duplicates of one fact.

Mapping code: `evidence_for_source` in `poc/graph/provenance.py` (substring heuristics on the source string).

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
├── reference/canvases/       ← Cursor canvas copies (hub: pillar-b-poc-hub.html)
├── archived-docs/            ← optional OneOps / Fusion product HTML (not PoC SoT)
└── poc/
    ├── graph/                ← GraphWriter + walk + stubs
    ├── sample_estate/customer_checkout/
    │   ├── topology.bootstrap.json      ← optional starting map
    │   ├── stream.resolved.jsonl        ← Case A: ingest.v1 topo WRITE tape
    │   ├── stream.reject.jsonl          ← Case B: DROP + NOOP tape
    │   ├── SAMPLE_IO.md
    │   └── cases/
    │       ├── case_a_map_spine/        ← golden map spine
    │       ├── case_b_rejects/          ← golden DROP codes
    │       ├── stub_case_path/          ← optional Detect→Localize harness
    │       └── stub_diagnose_close/     ← optional Identify/Package harness
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
| [Pillar B PoC hub](../../../docs/fabric/pillar-b-poc-hub.html) | Framing · layers · call sequences · canvas → hub map |
| [`PILLAR_B_POC_CHAT_QNA.md`](./PILLAR_B_POC_CHAT_QNA.md) | Session Q&A — stream, admit, writer_stream supersession |
| [`../../contracts/WRITER_REGULATOR.md`](../../contracts/WRITER_REGULATOR.md) | Current post-E2 writer fan-out (no `fact_kind`) |
| [Stream → graph demo](../../../docs/fabric/pillar-b-stream-graph-demo.html) | Legacy `ingest.v1` tape · `map/` grows on WRITE ([`:8765`](http://127.0.0.1:8765/pillar-b-stream-graph-demo.html)) |
| [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) | What “done” means for build/walk |
| [`Codebase-go-through.md`](./Codebase-go-through.md) | File-by-file code tour |
| [`../poc/sample_estate/customer_checkout/SAMPLE_IO.md`](../poc/sample_estate/customer_checkout/SAMPLE_IO.md) | Case A/B goldens |
| [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md) | Legacy lab `ingest.v1` / `fact_kind` examples |
| [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md) | Dest keys and snapshot schema |
| [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter) | Hub visual for NOOP / WRITE / DROP |

Optional stub harness notes (not core demo): [`MAP_P2_CASE_PATH.md`](./MAP_P2_CASE_PATH.md) · [`MAP_P3_DIAGNOSE_CLOSE.md`](./MAP_P3_DIAGNOSE_CLOSE.md).
