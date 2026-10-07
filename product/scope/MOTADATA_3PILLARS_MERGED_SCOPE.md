# Motadata 3 pillars - merged implementation guide

**Date:** 2026-08-20 (Parts C–F refreshed 2026-08-25 with sketch Detect-vs-investigate, season_key, exemplars, hybrid graph schema, Vortex/S3 orthogonality)  
**Audience:** engineering + management  
**Status:** Draft for kickoff. Not an HLD rewrite. **D5 stays Review.**  
**Merged from:**
1. Gaps / What-Why-How deep-dive (`Motadata_3Pillars_Implementation_Scope_Gaps.pdf`)
2. Explained architecture (`Motadata_Observability_3_Pillars_Architecture_Explained.pdf`)
3. Kickoff scope hub page (`motadata-3pillars-implementation-scope.html`)

**Companion docs:** `OBSERVEOPS_PIPELINE_HLD.md`, `MOTADATA_3PILLARS_STUDY_QNA.md`, `MOTADATA_3PILLARS_VS_SHIFT_LEFT.md`, `GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`, `end-to-end-algorithm-walkthrough.md`, `sketch-exemplars-visual.html`, `vortex-s3-interaction.html`  
**Pillar A cold-reader deep dive (inputs → process → artifacts):** [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md)  
**Slice home:** [`pillar-ab-implementation/`](../README.md) · **Contract brief:** [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md)

---

## 0) How to read this document

This is one merged guide. It is not three stapled PDFs.

| Section | Purpose |
|---------|---------|
| Part A | Context: what Motadata drew, how it maps onto ObserveOps |
| Part B | Kickoff scope: locked decisions, open questions, in/out, E1/E2 contracts |
| Part C | Pillar 1 deep-dive (teammate): statistics + sketch store |
| Part D | Pillar 2 deep-dive (you): entities + edges + changes |
| Part E | Shared lake, readers, build order |
| Part F | Gap register and candidate resolutions |

Every technical claim is written as **What / Why / How** so short Motadata labels do not become riddles.

### Two ownership tracks (implementation split)

- **Pillar 1 owner (teammate):** T-Digest + explicit buckets + seasonal baselines + graph-builder *write path* into the store (schema, S3, Vortex indexing, who-reads-it)
- **Pillar 2 owner (you):** entities + edges + changes graph *semantics* (CI taxonomy, edge catalog, validity, change facts)

OKRs stay only in `KR Plan/OKR_Harshil_Shah_Block-1 2026-27 (1).xlsx` (not duplicated here).

---

# Part A - Motadata stack mapped onto ObserveOps

## A1) One-sentence purpose

The Motadata PDF is a **SaaS-side** design: centralize telemetry, keep compact statistics and a typed map, then diagnose with bounded evidence. It is **not** a second ObserveOps pipeline. Same eleven steps (E1-E11). Pillars are *what* SaaS stores (and optionally how P3 reasons). Shift-left is *where* E1-E6 may run.

## A2) Quick orientation cards

| Box | Meaning |
|-----|---------|
| **A + B** | P1 stores (always-on write) |
| **C** | Optional P3 diagnose (Layer I / ReAct) |
| **P2** | Reads A+B - not a fourth Motadata pillar |
| **D5** | Stays Review. Operator path must work with agent off |

## A3) Stack picture (write, then diagnose)

Read top to bottom. Left = Motadata names. Right = our pipeline.

1. **Telemetry in** (logs, metrics, APM, eBPF, events) -> **E1 Collect** (admit raw; telemetry only this pass; no CI bind; PDF also lists ITSM here - we do **not**)
2. Streaming bus (NATS) - not a pipeline stage; sits between Collect and Stores
3. **A Percentile engine** || **B Graph builder** -> **E4+E5 || E3+E5** after identity exists. Windowing is not Node E2.
4. **Vortex + S3** durable lake -> **E4 Stores** (one dest profile among others; not the only lake)
5. Case opens - P2 has no Motadata pillar
6. **RCA retrieval layer** -> **E8 Scope** (`WorkingSet`; do not scan the lake)
7. **C Rust RCA agent** -> **E9 -> E10 -> E11** (Layer I opt-in)
8. Explain / ITSM / Remediate -> **E11 Package** (required `VerdictCard`; ticket is egress; remediation is outside E1-E11)
9. Outcome writeback -> **E5 Maintain + E3 version**

**Important gap in the Motadata picture:** Identity (E2) is assumed on every sketch and node, but never drawn as a step. We still bind on the Node.

**Same clock, SaaS column only.** Motadata does not specify OTel Node Collect/Identity, mask/Drain, Detect door A, or optional Gateway door B.

## A4) Which phase owns each pillar

A pillar is not a phase. A and B are always-on P1 stores. P2/P3 only read them. C is Clock B (diagnose/close), optional Layer I.

| Pillar | Owns (write path) | Read by | Does not own |
|--------|-------------------|---------|--------------|
| **A Percentiles** | P1 E4 sketch store; P1 E5 seasonal refresh | P2 E6 door C; P3 E10 `get_metric_baseline()` | E1/E2; E9 leaf rule |
| **B Knowledge graph** | P1 E3 `GraphSnapshot`; P1 E5 versions/changes/writeback | P2 E8 hop/time; P3 E9 walk; P3 E10 `query_graph()` | E6 Detect; E11 executor |
| **C Rust ReAct** | P3 E9 Localize; P3 E10 Identify; P3 E11 Package (explain/ticket) | Tools read A+B via E8 | P1 fabric; P2 E7 Curate; remediation |

## A5) Take vs do not copy

**Take:**
- mergeable percentile sketches as an E4 modality
- typed RCA graph with `valid_from`/`valid_to` and confidence as E3
- bounded retrieval as E8
- hypothesis-plus-evidence language for E10
- LLM never owns authorization if Layer I ships

**Do not copy:**
- skipping Node E1-E2
- treating NATS+Vortex as the whole product
- folding Curate into the agent
- making ReAct the default Package path
- calling ITSM or remediation Collect
- **Do not flip D5** because the PDF is agentic

---

# Part B - Kickoff scope (from implementation-scope HTML)

## B1) Workstream boundary

This work maps Motadata onto ObserveOps. It does **not** rebuild Motadata's product.

**This workstream is E3-E5** (Pillar B graph, Pillar A sketches in E4, E5 refresh).

- E1 Collect and E2 Identity are already specified (LLDs Done). We **consume** their output; we do not implement them here.
- Pillar C (ReAct) is **out of this block**.
- P2 has no Motadata pillar.

## B2) Already decided (do not re-open)

| # | Question | Answer |
|---|----------|--------|
| L1 | Second pipeline? | No. Same E1-E11. |
| L2 | Where does the PDF sit? | SaaS-column requirements. Node work is ours; PDF is silent, not opposed. |
| L3 | Alert / Incident / ticket on the map? | No. CIs only. Alert = E6 `Signal`. |
| L4 | ReAct as default Package? | No. D5 stays Review. Operator E9-E11 with Layer I off. |
| L5 | Curate inside the agent? | No. E7 one `CaseSeed` first (D3). |
| L6 | ITSM / change as Collect? | No this pass. Reserved `fact_kind` only. |
| L7 | Vortex the only lake? | No. One E4 dest among others. Sketches = E4. Graph = E3. |
| L8 | Sketches vs map? | Sketches = Grail-like history (E4). Map = Smartscape-like graph (E3). |

## B3) Must answer before first A+B sprint

| # | Question | Why it blocks | Default if silent |
|---|----------|---------------|-------------------|
| Q1 | Which k8s cluster and which VM emit first streams? | E1 has nothing to admit | UC replay + existing Motadata export path |
| Q2 | Lab tenant string? | Join key | `default` |
| Q3 | CI types in v1 graph? Pods with parent + validity? | E3 schema | Service + Host required; Pod optional |
| Q4 | Gate A: Node-first vs Gateway? | Where Collect runs | Node-first; Gateway off |
| Q5 | Gate B: dest for sketches (Vortex or not)? | E4 writer | Files or existing dest; Vortex optional |
| Q6 | First metric names and windows? | Pillar A schema | PDF 1m/5m/1h/1d; start 1m+5m |
| Q7 | Two Detect classes for door C? | case-open exit | ERROR + SLOWDOWN |
| Q8 | Three classes for VerdictCard, Layer I off? | close exit | ERROR, SLOWDOWN, one host-contention flavor |
| Q9 | Graph time field names? | E3/E5 | `valid_from`/`valid_to` plus provenance types |
| Q10 | Seed topology: file, `topo_update`, or both? | E3 writer | Both; SaaS owns snapshot |
| Q11 | Split Motadata admit vs bind scripts? | E1/E2 boundary | Split before calling A/B implemented |
| Q12 | Publish: hub vs shared drive? | two truths | Hub for specs; drive + 1 session for management report |
| Q13 | Murphy / cyclic MRF this block? | scope | No. Store a graph that could be cyclic; Gibbs is later P3 |

## B4) In scope / out of scope

**In (this stream):**
1. Consume `ingest.v1` JSONL after E2 (`identity.status = resolved` for writers)
2. Pillar A sketches in E4, refreshed by E5, keyed by `tenant`+`ci_id`
3. Hybrid CI `GraphSnapshot` in E3 (CI vertices only; provenance + validity); E5 versions; SaaS owns snapshot
4. E5 Maintain (season refresh; graph validity/decay) - not Detect
5. Readers: door C on sketches; E7/E8 case open; operator E9-E11; LLD-E3/E4 Done; Gate B/C

**Out (this block):**
- Rust ReAct / Layer I on (Pillar C, Gate D, D5)
- Remediation execution
- ITSM as Collect; `change_event` Collect
- Alert / Incident / Metric / Trace as E3 vertices
- Vortex as the mandatory lake
- Murphy Gibbs / Nezha as the localize engine
- Second HLD / Motadata clone PRD / agent design doc

## B5) What we expect from E1 (we do not build this)

**What:** E1 admits telemetry into UTF-8 JSONL (`schema_version: "ingest.v1"`).  
**Why:** Writers must not invent their own ingest dialect.  
**How:** Send metrics / logs-events / optional traces / topology cues. Do not send tickets or CMDB this pass.

Example envelope:

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-19T12:00:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.p95_latency_ms",
  "value": 1450.0,
  "labels": { "source": "lab-node" }
}
```

Admitted `fact_kind`: `metric_sample`, `anomaly`, `event`, `trace_span`, `topo_update`.  
Reserved (do not emit): `change_event`, `cmdb_sync`, `ticket`.

Preferred lab folder:

```
datasets/ingest_samples/<suite>/<incident_id>/
  stream.jsonl
  topology.json
  ground_truth.json   # eval only
```

## B6) What we expect from E2 (we do not build this)

**What:** Same `ingest.v1` line plus identity overlay.  
**Why:** One identity namespace for sketches and graph. Unresolved ids must not become localize/ticket roots.  
**How:**

```json
"identity": {
  "status": "resolved",
  "bind_source": "topology_lookup",
  "aliases": ["monitor-88"]
}
```

| `identity.status` | May be E9 leaf / ticket CI? |
|-------------------|-----------------------------|
| `resolved` | Yes |
| `unattributed` | No |
| `synthesized` | No (D-E2-1) |

Pillars A and B write **resolved rows only**.

## B7) Output artifacts this work generates

| Artifact | Format | From |
|----------|--------|------|
| Lab stream | `ingest.v1` JSONL + identity | Upstream E1+E2 |
| `GraphSnapshot` | JSON: CIs, edges, provenance, `valid_from`/`valid_to` | E3/E5 |
| Sketch rows | Dest table/files: window, season_key, tdigest, buckets, baseline | E4/E5 |
| Signal / CaseSeed / WorkingSet / VerdictCard | JSON | E6-E11 |
| LLD-E3 / LLD-E4 Done, Gates A/B/C | Markdown on hub | Docs |

**Publish:** engineering specs on hub (`http://127.0.0.1:8765/`); code/datasets in repo; management evidence on shared drive + one knowledge-sharing session. Do not rewrite the leadership PDF.

## B8) Documents to write during the work

Engineering:
- LLD-E3 Topology (CI-only graph, provenance, validity)
- LLD-E4 Stores (sketch schema + `get_metric_baseline`, Gate B)
- Gates A/B/C note
- Identified-stream contract: fields E3/E4 will reject
- CaseSeed + VerdictCard examples; acceptance list

Management (short):
- One-pager: PDF mapped onto E1-E11; D5 not flipped
- Conflict register (study QnA section 10 - do not fork a spreadsheet)
- Evidence pack: 3 VerdictCards, Gate notes, out-of-scope list
- One knowledge-sharing session

---

# Part C - Pillar 1 deep-dive (Owner: Teammate)

**Elaborative teaching page (recommended for cold readers):** [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md) — inputs (what / format / from where), processing flowcharts, artifacts (who reads them), S3/Vortex layout, and a full numeric example. Part C below stays the short What/Why/How kickoff slice.

## C0) Pillar A in Motadata language (context before implementation)

**What:** One job, three parts in one `sketch.v1` row: keep a mergeable percentile (T-Digest), keep a cheap histogram (explicit buckets), keep a usual range for this calendar slot (seasonal baseline). Optional exemplars (trace ids on bins) help investigation; they are not a fourth Detect algorithm.

**Why:** Weeks of samples cannot be scanned on every alert. Monday 9am traffic is not an outage. Without mergeable summaries and a calendar-aware expected range, Detect lies. Without buckets/exemplars, Detect can still fire but investigation stays blind.

**How (Motadata write path):**
samples (start with 1m + 5m) -> T-Digest + explicit buckets (+ optional exemplars on bins) + seasonal baseline (hour-of-week `season_key`) -> one sketch row per metric + entity + window + season_key + window_start -> E4 dest (Vortex/S3 is one option)

**Who reads it (Motadata / ours):**
- dashboards (O(1) p95 lookup)
- E6 door C Detect (**digest p95 vs seasonal expected** — buckets not required to fire)
- E8 / E10 after Detect (buckets + exemplars for “which range / which request”)
- E10 Identify (`get_metric_baseline()`)

**Example.** Checkout p95 = 180 ms. Tuesday 14:00 baseline p95 ~ 200 ms -> normal. Sunday 02:00 baseline p95 ~ 40 ms -> 180 ms is abnormal. Same number; different `season_key`.

**Our pipeline mapping:**
- writes E4 Stores; writes E5 Maintain (seasonal refresh)
- read by E6 door C; read by E10 Identify
- not E1/E2 (needs identity first; windowing != Node Normalize)
- not E9 leaf rule (percentiles do not name the root CI)

### C0.1 Detect vs investigate (locked teaching)

| Job | Uses | Does not need |
|-----|------|----------------|
| **Detect** — “is this window wrong for this season?” | **T-Digest** (current p95) + **seasonal baseline** (expected p95) | Buckets, exemplars |
| **Investigate after fire** — “which latency range / which request?” | **Buckets** (+ **exemplars** on a hot bin → `trace_id`) | Baseline for the click-through itself |

General rule (not demo-only): *digest + baseline → fire; buckets → where the mass is; exemplars → which request in that mass.* Visual: [`sketch-exemplars-visual.html`](../../docs/fabric/sketch-exemplars-visual.html). Walkthrough: [`end-to-end-algorithm-walkthrough.md`](../../docs/fabric/end-to-end-algorithm-walkthrough.md).

**Why both T-Digest and buckets if Detect only needs digest?** Same raw latencies, different leftovers: digest = mergeable percentiles; buckets = fixed-bin histogram for heatmaps, bin rules, and a place to hang exemplars. They are not duplicates. See contract brief §5.2 / FAQ Q15–Q16.

---

## C1) How samples are chosen?

**What**  
Choose metric samples by deterministic keys:
- `tenant`
- `entity_id` (same string as graph `ci_id` after E2 identity)
- `metric_id`
- `window` (start with `1m` + `5m`; allow `1h` / `1d`)
- `window_start` (mandatory)
- `season_key` (hour-of-week from timestamp)
- timestamp of each sample

Only resolved identity rows are sketch-writer eligible.

**Why**  
Without deterministic sample admission, percentile and baseline outputs become non-reproducible across runs and teams.

**How**  
1. Admit only `ingest.v1` metric lines with `identity.status = resolved`.
2. Normalize metric naming (`request.latency_ms`, `cpu.utilization_pct`, etc.).
3. Assign each point to one or more configured windows (multi-resolution allowed).
4. Derive `season_key` from the window timestamp (timezone-aware hour-of-week), e.g. `Thu-09:00` from `strftime('%a')` + floored hour (`HourOfWeekSeason` in the PoC).
5. Feed **this window’s latency values** into:
   - T-Digest state for the key
   - explicit bucket histogram for the key
   - optional exemplar pick per bin when the event carries a `trace_id`
6. Attach **seasonal baseline** for that `season_key` from **past** windows (not from this window’s raw list). E5 refreshes / accumulates baselines.

**Time-boundary rule:** `window_start` is mandatory. Store **exactly one of** `window` (duration string) **or** `window_end` — not all three as independent sources of truth (contract brief §5.4).

---

## C2) What does T-Digest do? What is "mergeable p50/p95/p99"?

**What**  
T-Digest is a compressed representation of a value distribution. It supports fast quantile queries (`p50`, `p95`, `p99`) without storing all raw samples.

**Why**  
Raw history scans become too expensive at scale. T-Digest gives near-real-time percentile lookup with bounded storage. **Detect** reads current-window quantiles from the digest.

**How**  
1. Each key `(tenant, entity_id, metric_id, window, season_key, window_start)` has a digest state for that slice (rollups merge digests across windows).
2. New values update centroids (compression step). Trace ids are **not** stored in the digest.
3. Query asks for quantile `q` and returns estimate from digest.
4. **Mergeable** means digest A + digest B -> digest AB:
   - merge per host -> per service
   - merge per minute -> per 5-minute rollup
   - merge shard results -> tenant/global aggregate

Operational meaning:
- `p50`: median behavior (normal center)
- `p95`: high-tail service behavior (SLO-sensitive) — primary Detect compare vs baseline
- `p99`: rare tail stress/spike behavior

---

## C3) How explicit bucketing is done? Where do exemplars fit?

**What**  
Explicit bucketing is a fixed histogram with predefined boundaries. **Exemplars** (optional) attach a real `trace_id` to a bin so an operator can open one request after Detect fires.

**Why**  
Buckets make thresholding, heatmaps, and “which range dominates?” deterministic. They are **not** required to compute the p95-vs-season Detect ratio. Exemplars are **not** another statistical summary — they need identity-bearing events `(latency, trace_id)`, not T-Digest centroids.

**How**  
1. Define bucket sets per metric family:
   - latency: `[0-50), [50-100), [100-200), ...`
   - CPU%: `[0-20), [20-40), [40-60), ...`
2. For each sample, increment exactly one bucket count.
3. Optionally keep one (or a few) exemplar `trace_id`s per bin (demo: first event in bin).
4. Version bucket policy (`bucket_schema_version`) to prevent silent drift.
5. Never mix bucket versions in one logical sketch key.
6. Values outside the top bound still update T-Digest; they may be omitted from configured bins (walkthrough notes this gap).

**Exemplars vs “sampled data”:** exemplars do not mean “Detect on a 1% metric sample.” Detect still uses digest + baseline. Exemplars hang on bins for **investigation** (same family as Google Cloud / OpenTelemetry exemplars).

---

## C4) Sketch row format: one row per metric + entity + window + season_key -> E4 dest

**What**  
Each row is a compact statistical state for one logical key.

**Why**  
This shape is the contract that allows:
- durable archival in S3 (when that dest is used)
- analytical read/index in Vortex (when that dest is used)
- reproducible E6/E10 retrieval without raw re-scan

**How (recommended schema v1)** — note: example keeps `window` and omits `window_end` (time-boundary rule).

```json
{
  "schema_version": "sketch.v1",
  "tenant": "default",
  "entity_id": "checkout-api",
  "entity_type": "Service",
  "metric_id": "request.latency_ms",
  "window": "5m",
  "window_start": "2026-08-20T03:30:00Z",
  "season_key": "Thu-09:00",
  "tdigest": {
    "compression": 100,
    "encoding": "centroids_json",
    "centroids": [
      {"m": 92.1, "w": 14},
      {"m": 145.3, "w": 9}
    ]
  },
  "buckets": {
    "bucket_schema_version": "latency_v1",
    "counts": [12, 19, 5, 1, 0, 0],
    "bounds": [0, 50, 100, 200, 500, 1000, 2000]
  },
  "baseline": {
    "expected_p50": 88.0,
    "expected_p95": 170.0,
    "expected_p99": 320.0,
    "baseline_version": "seasonal_v1"
  },
  "sample_count": 23,
  "ingest_trace": {
    "writer": "pillar-a-sketch-writer",
    "written_at": "2026-08-20T03:35:05Z"
  }
}
```

Optional later: exemplar refs on bucket export/UI (not required as a fourth frozen body in v1 unless the room adds them).

### S3 write model (cold / durable)

**What:** S3 holds cold/large objects and long retention for sketch blobs and history.  
**Why:** Builders are useless if results evaporate. Rewriting a giant **raw sample** lake’s history in place is expensive — prefer **append** of compact sketch rows per window (not “UPDATE is cheaper than insert”).  
**How:**
- Partition: `tenant=.../metric_id=.../window=.../date=YYYY-MM-DD/`
- Write mode: append immutable rows; idempotent object naming using key hash + window identity
- Rollups: optional periodic compaction by day/week

Full cold-reader expansion (inputs → process → partition example): [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md) §7.3 and §10.

### Vortex indexing/read model (hot / analytical)

**What:** Vortex is the analytical query engine on top of durable data when Vortex/S3 is the chosen E4 dest.  
**Why:** Interactive RCA must answer p95 / baseline / trend without scanning raw history.  
**How:**
- Primary lookup index: `(tenant, entity_id, metric_id, window, season_key, window_start)`
- Secondary filters: `entity_type`, date range
- First query patterns to optimize:
  1. latest p95 for entity+metric
  2. compare current window vs seasonal baseline (**this is Phase-2 E6 Detect, door C**)
  3. retrieve N prior windows for trend
  4. (optional) hot-bin + exemplar for drill-down (**after** Detect — not part of the fire decision)

"O(1)" means cost does not grow with historical **sample count**. It is still a bounded key lookup + deserialize a sketch.

See also: [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md) §7.4.

**E4 destination:** Vortex/S3 may be **one** allowed dest among others (lab file dest, existing Motadata store). This guide freezes **row shapes**, not “Vortex is the only lake forever.” Visual: [`vortex-s3-interaction.html`](../../docs/fabric/vortex-s3-interaction.html).

---

## C5) How "WHO READS IT" is handled?

**What**  
A role-based read policy for sketch data. Diagnose path reads via **retrieval → `WorkingSet`**, not by dumping Vortex or opening S3.

**Why**  
Different consumers need different access levels; unrestricted reads risk data leakage and noisy operations.

**How (minimum RBAC plan)**

| Role | May do |
|------|--------|
| `role_observability_reader` | Read sketch rows and baselines; no policy changes |
| `role_detect_engine` | Read for door-C thresholding (service account only) — digest + baseline |
| `role_rca_engine` | Read for E10 evidence / bucket+exemplar drill-down |
| `role_admin_data` | Manage retention, index configs, schema versions |

Controls:
1. tenant-scoped authorization mandatory
2. audit log for each read query (who/what/when)
3. deny-by-default for cross-tenant reads
4. schema-version compatibility checks before query execution

Optional Motadata **Rust ReAct agent** (Pillar C) is one client of retrieval — not every caller, and not allowed to open S3 raw. Operator path must work with that agent off.
# Part D - Pillar 2 deep-dive (Owner: You)

## D0) Pillar B in Motadata language (context before implementation)

**What:** Continuously maintain a typed picture of the estate: what exists, how it connects, and what recently changed. This is an RCA map, not a generic enterprise knowledge graph. Output object name on our side: **`GraphSnapshot`** (ObserveOps / E3 contract — not a vendor library term).

**Why:** A detector without a map produces an alert. A detector with a map can say which neighbor sits under the symptom, whether a deploy landed, and how sure we are that the link is real.

**How (Motadata walk recipe):** Incident -> Service (symptom CI) -> deps (`CALLS` / `RUNS_ON`) -> Change (`CHANGED_BY`) -> candidates + abnormal metrics.

Motadata product edge words map **into** our closed **fifteen-relation** storage enum (aliases, not a second vocabulary). Examples we store: `depends_on`, `runs_on`, `communicates_with`, `part_of`, `hosted_on`, … Full catalog and field tables: [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) §4.

**Not topology edges:** `CORRELATED_WITH` (Curate), `RESOLVED_BY` (Package), blast-radius `AFFECTS` as a stored map fact — those are case / investigation words, not E3 `graph_edge.v1`.

Every edge carries provenance (`discovered_via`, including `evidence_type`) and `valid_from` / `valid_to` as **siblings** of `relation` (not nested only inside provenance).

**Example.** Pain shows on `checkout-api`. Walk `depends_on` / `communicates_with` -> `checkout-db`. A change fact landed 12 minutes ago on the db. API p95 is high; db p95 is worse. Leaf candidate is the database, not the API.

**Our mapping (hybrid, not Motadata copy):**
- writes E3 Topology `GraphSnapshot` (SaaS owns it; Gateway only assists)
- writes E5 Maintain (versions, change feed, outcome writeback)
- read by E8 Scope, E9 Localize, E10 `query_graph()`
- not E6 Detect (storing an Alert != firing Detect)
- **CI vertices only.** Alert/Incident/ticket are not map nodes. Change is a fact, not a CI.

**Schema rich on day one; writers grow:** lock all fifteen relation names in the schema now; lab writers may emit only wave-1 relations until sources exist (`runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of` first).

---

## D1) Entities

**What**  
CIs with stable identity (`tenant + ci_id`) and typed class (`Service`, `Host`, optional `Pod` with validity window). Sketch `entity_id` is the **same string** as `ci_id` after bind — not a second root key.

**Why**  
Localize/package must point to durable operational targets, not transient noise objects. If Alert is a vertex, Curate/Detect leak into E3.

**How**
- allow only `identity_status = resolved` for GraphSnapshot vertices
- enforce `ci_type` as a versioned closed enum (richer catalog than Service/Host-only — see contract brief §3)
- carry aliases as metadata, not alternative primary keys
- ephemeral runtime (Pod/Container) allowed only with `scope_parent` + real `valid_from` / `valid_to`
- no Alert, Incident, ITSMTicket, Metric, Trace, LogPattern vertices
- **Hybrid spine:** required fields (`schema_version`, `tenant`, `ci_id`, `ci_type`, `ci_name`, `identity_status`) are strict; type-specific extras / `labels` are flexible (`additionalProperties: true`). Identity and types are rigid; decorations are not (brief §6.1).

---

## D2) Edges

**What**  
Typed CI-CI relationships with provenance and validity (`graph_edge.v1`).

**Why**  
E8/E9 walk quality depends on relationship semantics and freshness. Half a real graph is inference; without provenance, confidence is decoration.

**How**  
Each edge stores at minimum:
- `tenant`, `edge_id`, `src_ci_id`, `dst_ci_id`, `relation` (fifteen-name enum)
- `discovered_via` (at least `evidence_type`)
- `valid_from` / `valid_to` as sibling fields on the edge

| `evidence_type` | Meaning |
|-----------------|---------|
| **`authoritative`** | System of record **owns** the fact (inventory, K8s API, …) |
| **`declared`** | Human/config **asserted** it (CMDB, catalog, Helm, …) |
| **`corroborating`** | Telemetry **suggests** it (spans, logs, eBPF) — weaker alone |

Strength order: authoritative > declared > corroborating. This is **how Topology learned the edge**, not Identify/Verify “RCA proved.”

Structure edges (`part_of`, `runs_on`, …) belong on E3.  
Case edges (`CORRELATED_WITH`, `RESOLVED_BY`, stored blast-radius `AFFECTS`) do **not**.

Same hybrid rule as nodes: required spine strict; optional provenance fields (`signal_fields`, `endpoint_binding`, …) flexible.

---

## D3) Changes

**What**  
Time-bound facts linked to CIs (deploy/config/release/change-ticket references) — later `change_fact.v1`.

**Why**  
Change context improves root-cause explainability ("deps -> recent changes -> abnormal metrics") without polluting CI topology.

**How**
- store change as fact records, not CI vertices
- link by CI identity and time overlap (`CHANGED_BY` as hitch, not as a ticket root)
- keep change ingestion out of E1 for this block; attach via reserved path/future phase
- do not invent a second identity namespace for changes

# Part E - Shared lake, retrieval, build order

## E1) Vortex + S3 — two orthogonal axes

Do **not** collapse “two rooms” with “Vortex vs S3.”

| Axis | What it partitions | Share | Do not share |
|------|--------------------|-------|--------------|
| **Rooms (content)** | Map (`graph_node` / `graph_edge`) vs sketches (`sketch.v1`) | Same `tenant` + `ci_id` / `entity_id` | Different row shapes and facts |
| **Temperature (dest)** | Hot analytical engine vs cold object store **when** Vortex/S3 is chosen | Same kinds of rows as they age (spill / federated scan) | Latency tier |

**What:** When Motadata-shaped dest is used: Vortex = hot query surface; S3 = durable cold cellar. Both rooms can live in Vortex while hot and age into S3.

**Why:** Builders are useless if results evaporate. RCA must not mutate history in place.

**How:** Percentile engine and graph builder write in parallel after identity exists. Diagnose never opens the lake as a dump: **retrieval → bounded `WorkingSet`**. Vortex may federate S3; Localize / Identify / optional ReAct consume the WorkingSet.

**Our resolution:** Keep rooms logically separate (E3 map || E4 evidence). Vortex/S3 may be **one** E4 destination among others (lab files, existing Motadata store). Node/Gateway only buffer — they are not the lake. Visual: [`vortex-s3-interaction.html`](../../docs/fabric/vortex-s3-interaction.html).

**“Agent” here:** Motadata Pillar C Rust ReAct (optional Layer I) is one client of retrieval — not Collect/Topology writers, not “any HTTP caller.” Operator E9–E11 must work with ReAct off.

## E2) RCA retrieval layer (P2 reader, not a pillar)

**What:** A bounded index in front of the lake: give me these evidence kinds for this seed under these limits. In our language: `WorkingSet`.

**Why:** Unscoped RCA walks the estate and hallucinates. Cost, latency, and wrong neighbors explode.

**How:** Start from curated seed (not raw alert storm). Expand k hops. Pull baselines (digest vs season), events, changes inside time window; optionally hot bins / exemplars for drill-down. Stop when budget spent. Then Localize.

Four kinds in: baseline (A), graph (B), events (Detect storm), changes.  
Four knobs: time window, entity scope, hop count, evidence budget.

**Example.** Seed = `checkout-api` at 14:02. Budget: 30 minutes, 2 hops, 40 evidence items. You get the API, its db, last deploy, p95 vs Tuesday baseline - not the whole cluster.

E7 Curate still runs first - one `CaseSeed`. Retrieval does not merge the storm (D3).

## E3) Pillar C note (out of this block, but needed for context)

Motadata default closer is a Rust ReAct agent with typed tools and a policy engine.  
We keep it as optional Layer I (D5 Review). Operator E9-E11 on A+B must work with agent off. Do not fold Curate into the agent. Remediation is outside E1-E11.

## E4) Recommended implementation order

Do **not** ship A -> B -> C as three products. A and B are parallel P1 writers after E2 keys exist. C is last and opt-in.

| Seq | Build | HLD steps | Exit |
|-----|-------|-----------|------|
| 0 | Edge admit + identity (PDF silent) | E1 · E2 (Node) | `ingest.v1` with `tenant`+`ci_id` |
| 1 | Ingest path into SaaS (NATS optional) | E1 SaaS · E4 write | Stream lands; Vortex/S3 may be one dest |
| 2 | Pillar A \|\| Pillar B | A: E4+E5 · B: E3+E5 | p95 by entity without raw scan; graph walkable; Detect can compare digest vs baseline |
| 3 | Platform Detect on sketches | E6 door C | Digest+baseline fire; doors A/B still ours |
| 4 | Case open without an LLM | E7 · E8 | One CaseSeed; WorkingSet with budget |
| 5 | Deterministic diagnose + close | E9 · E10 · E11 | Operator path on A+B; buckets/exemplars aid investigate |
| 6 | Pillar C as Layer I (opt-in) | same E9-E11 | Default off |
| 7 | Remediation (later) | outside E1-E11 | Reuse policy; not Package |

For **this workstream**, the immediate build is sequence 2 (A || B) after consuming E1/E2 output.

---

# Part F - Gap register and candidate resolutions

## F1) Pillar 1 gaps (Teammate)

1. **Metric catalog not frozen**  
   Resolution: approve initial metric shortlist + naming standard (start from Q6 defaults: latency + CPU).
2. **Bucket boundaries undefined per metric family**  
   Resolution: publish `bucket_schema_version` per family before writers start. Buckets required for investigate/exemplars; not for the p95-vs-season Detect fire itself.
3. **Season-key policy**  
   Resolution: **hour-of-week** string (`Thu-09:00`) via timezone-aware timestamp — treat as locked lean unless version bump. PoC: `HourOfWeekSeason`.
4. **Time-boundary fields**  
   Resolution: `window_start` mandatory; exactly one of `window` or `window_end` (do not author all three independently).
5. **Baseline vs current window**  
   Resolution: baseline from **past** windows with same `season_key`; never rebuild expected p95 from the incident window’s raw samples alone.
6. **Exemplars (optional)**  
   Resolution: v1 may omit as a frozen sketch body; if added, attach to bins from identity-bearing events `(latency, trace_id)` — not from digest centroids. Document in dest/export note.
7. **S3 partition / idempotency policy not frozen**  
   Resolution: define path template + deterministic object key when Vortex/S3 dest is chosen.
8. **Vortex index plan**  
   Resolution: lock priority queries: (1) latest p95, (2) current vs seasonal baseline Detect, (3) prior-window trend, (4) optional hot-bin/exemplar.
9. **Reader roles not codified**  
   Resolution: publish RBAC matrix; diagnose via retrieval → WorkingSet only.
10. **E4 dest for first lab**  
   Resolution: files or existing Motadata dest for Q1; Vortex/S3 optional; document dest profile (avoid treating Vortex as the only lake).

## F2) Pillar 2 gaps (You)

1. **Entity type taxonomy not frozen for wave 1**  
   Resolution: whiteboard closed `ci_type` enum; Service + Host required; Pod/Container only with `scope_parent` + validity (contract brief open Q).
2. **Edge catalog**  
   Resolution: **schema carries all fifteen relations day one**; writers emit lab wave 1 first (`runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`). Motadata names map in as aliases. Defer case edges off E3.
3. **Edge freshness / validity**  
   Resolution: `valid_from`/`valid_to` as edge siblings + `discovered_via.evidence_type` (`authoritative` | `declared` | `corroborating`).
4. **Hybrid attribute policy**  
   Resolution: strict spine + flexible extras (`additionalProperties`); promote fields onto spine only when Localize/Retrieval filter them often (brief §6.1).
5. **Change-fact model not contractually defined**  
   Resolution: define `change_fact.v1` + CI/time link rules; no Change-as-CI.
6. **Graph write ownership and publication cadence**  
   Resolution: SaaS owns `GraphSnapshot`; define E3 writer owner + E5 refresh cadence/SLA.
7. **Seed topology path**  
   Resolution: start with `topology.json` + `topo_update`; SaaS owns canonical snapshot (Q10).

## F3) Shared / kickoff gaps (both)

1. Lab sources and tenant string (Q1/Q2)
2. Publish surface discipline (hub for specs; shared drive for management evidence) (Q12)
3. Explicit "no Murphy this block" boundary (Q13)
4. Keep Gate A–D vocabulary on Motadata ↔ shift-left build-order pages; in this A/B freeze prefer plain **E4 destination** / **Node vs Gateway** wording so cold readers are not blocked

---

## Closing summary

| Track | Build now | Do not build now |
|-------|-----------|------------------|
| Pillar 1 (teammate) | Sample policy, T-Digest, buckets, seasonal baseline, sketch.v1, E4 dest write, Vortex index when chosen, RBAC; Detect = digest vs baseline; buckets/exemplars for investigate | Agent-owned Detect; mandatory Vortex-only lake; inventing exemplars from digests |
| Pillar 2 (you) | CI entities, fifteen-relation schema (phased writers), provenance/validity, hybrid spine, change facts (not vertices) | Alert/Incident vertices, Curate-as-edge, ReAct default |
| Shared | Consume E1/E2 contracts; E5 refresh; door C / CaseSeed / operator VerdictCard; rooms ⊥ temperature tiers | Flip D5; remediation; ITSM Collect |

Formal contracts remain on the Pipeline HLD and [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md). This merged guide is the SaaS-column implementation map for Motadata pillars A/B onto ObserveOps E3-E5.
