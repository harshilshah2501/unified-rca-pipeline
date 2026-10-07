# Motadata 3 pillars — implementation scope and requirements

**Date:** 2026-08-19  
**Status:** Draft for kickoff. Not an HLD rewrite. **D5 stays Review.**  
**Audience:** engineering (build) and management (what we will / will not ship).  
**Leadership source:** [`KR Plan/Motadata_Observability_3_Pillars_Architecture.pdf`](../../KR%20Plan/Motadata_Observability_3_Pillars_Architecture.pdf)  
**Our clock:** [`OBSERVEOPS_PIPELINE_HLD.md`](../../docs/OBSERVEOPS_PIPELINE_HLD.md) · [shift-left](../../docs/observeops-shift-left-architecture.html)  
**Conflicts / resolutions:** [`MOTADATA_3PILLARS_STUDY_QNA.md`](../../docs/MOTADATA_3PILLARS_STUDY_QNA.md) §10 · [hub](../../docs/motadata-3pillars-study-qna.html#register)  
**OKRs:** [`KR Plan/OKR_Harshil_Shah_Block-1 2026-27 (1).xlsx`](../../KR%20Plan/OKR_Harshil_Shah_Block-1%202026-27%20%281%29.xlsx) (also linked under `../deliverables/`)  
**Slice home:** [`pillar-ab-implementation/`](../README.md)  
**Hub:** [`motadata-3pillars-implementation-scope.html`](../../docs/motadata-3pillars-implementation-scope.html)

This work maps the Motadata PDF onto ObserveOps. It does **not** rebuild Motadata’s product. **This workstream is E3–E5** (Pillar B graph, Pillar A sketches in E4, E5 refresh). E1 Collect and E2 Identity are **already specified** (LLDs Done). We do **not** implement them here; we **consume** their output in a fixed format. Pillar C (ReAct) is **out of this block**. P2 has no Motadata pillar.

---

## 1. Answers we need before commencing

Do not start sketch writers or `GraphSnapshot` until these are written down (one owner, one date). Locked items are already decided; they still need a named owner so engineering does not re-litigate them.

### Already decided (do not re-open)

| # | Question | Answer |
|---|----------|--------|
| L1 | Is this a second pipeline? | No. Same E1–E11. |
| L2 | Where does the PDF sit? | SaaS-column requirements sketch. Node work is ours; the PDF is silent, not opposed. |
| L3 | Alert / Incident / ticket on the map? | No. CIs only. Alert = E6 `Signal`. |
| L4 | ReAct as default Package? | No. **D5 stays Review.** Operator E9–E11 with Layer I off. |
| L5 | Curate inside the agent? | No. E7 one `CaseSeed` first (**D3**). |
| L6 | ITSM / change as Collect? | No this pass. Reserved `fact_kind` only. |
| L7 | Vortex the only lake? | No. **Gate B:** one dest profile among others. Sketches = E4 modality. Graph = E3. |
| L8 | Sketches vs map? | Sketches = compact history (Grail-like, E4). Map = who-is-connected (Smartscape-like, E3). |

### Must answer before first sprint of A+B

| # | Question | Why it blocks | Who typically answers | Default if silent |
|---|---------|----------------|----------------------|-------------------|
| Q1 | **Lab sources:** which Kubernetes cluster and which VM/host emit the first streams? | E1 has nothing to admit. | Lab / platform | ObserveOps UC replay + one Motadata export path already in repo |
| Q2 | **`tenant` string** for lab (not `"default"` forever)? | Join key for graph + sketches. | Product | Keep `"default"` until a second tenant exists |
| Q3 | **CI types in v1 graph** (Service, Host, Pod, …)? Which Pods get a parent + validity window? | E3 schema freeze. | Architecture | Service + Host required; Pod optional with `scope_parent` |
| Q4 | **Gate A:** Node-first vs optional Gateway for this lab? | Where Collect/Identity run. | Architecture | Node-first; Gateway off |
| Q5 | **Gate B:** dest product for sketches + raw history (Vortex, ClickHouse, files, …)? At least one non-Vortex dest? | E4 writer. | Platform / Motadata infra | Files or existing Motadata dest for Q1; Vortex optional |
| Q6 | **Metric names** for first sketches (e.g. request p95, host CPU)? Window sizes (1m / 5m / 1h)? | Pillar A schema. | Detect + stores | PDF windows: 1m / 5m / 1h / 1d; start 1m+5m |
| Q7 | **Door C classes:** which two Detect classes prove sketch alerts (ERROR + SLOWDOWN, or one host class)? | Obj 3 exit. | Detect | ERROR + SLOWDOWN |
| Q8 | **Close classes:** which three classes get a `VerdictCard` with Layer I off? | Obj 4 exit. | RCA | ERROR, SLOWDOWN, one RESOURCE_CONTENTION flavor |
| Q9 | **Graph time field names:** Motadata `valid_from`/`valid_to` vs existing `refresh` + decay? | E3/E5 LLD. | Architecture | Adopt `valid_from`/`valid_to` **and** keep provenance (`authoritative` \| `declared` \| `corroborating`) |
| Q10 | **Seed topology:** snapshot file vs live `topo_update` lines vs both? | E3 writer. | Ingest | Start with `topology.json` + `topo_update` in `ingest.v1`; SaaS owns snapshot |
| Q11 | **E1/E2 process split:** keep Motadata converter as one script or split admit vs bind? | Stage boundary. | Ingest | Split before calling A/B “implemented” |
| Q12 | **Publish surface** for engineering artifacts vs the Block-2 management report? | Avoid two truths. | PM / docs | Hub `:8765` for specs; shared drive + 1 session for OKR obj 5 |
| Q13 | **Murphy / cyclic MRF** in this block? | Scope creep. | Architecture | **No.** P1 must still store a graph that *could* be cyclic later; Gibbs is P3 and out of Block-2 |

Q13 is explicit: extra *facts* (peer edges, time-aligned metrics) can land in P1; Murphy the *algorithm* is not this work.

---

## 2. Scope

### In (this workstream: E3–E5, plus later readers)

We **do not** build E1 or E2. We require their output (below). Block-2 OKR objective 1 (Node Collect/Identity) is a **sibling** fabric KR, not this stream.

1. **Consume** `ingest.v1` JSONL after E2 (`identity.status = resolved` for writers).  
2. **Pillar A** — T-Digest + buckets + seasonal baseline written to **E4**, refreshed by **E5**, keyed by `tenant`+`ci_id`.  
3. **Pillar B (hybrid CI graph)** — `GraphSnapshot`: CI vertices only; CI–CI edges with provenance **and** validity windows; **E3** write, **E5** versions. SaaS owns the snapshot.  
4. **E5 Maintain** — sketch season refresh; graph validity/decay; not Detect.  
5. **Readers (still this program, not E1/E2):** door C on sketches; E7/E8 case open; operator E9–E11 using the graph + sketches; LLD-E3/E4 Done; Gates B/C as they affect stores/Detect (Gate A is the E1/E2 team).

### Out (this block)

- Rust ReAct agent / Layer I on (Pillar C, Gate D, **D5**).  
- Remediation execution.  
- ITSM as Collect; `change_event` Collect.  
- Alert / Incident / Metric / Trace as E3 vertices.  
- Vortex as the mandatory lake.  
- Murphy Gibbs / Nezha as the localize engine.  
- Named ObserveOps lake SKU / numeric E4 NFRs beyond “query p95 without a raw scan.”  
- Flipping Curate into the agent.

---

## 3. What we expect from E1 (we do not build this)

Someone else (or existing converters) **Collects**. This workstream only **reads** well-formed envelopes.

**Contract:** [`LLD-E1-Collect.md`](../../docs/LLD-E1-Collect.md) (Done). Wire format: [`INGEST_DATA_FORMAT.md`](../../docs/INGEST_DATA_FORMAT.md).

### 3.1 What to send (sources)

| Need | Format | Notes |
|------|--------|--------|
| Metrics | As today: OTLP metrics, Prometheus scrape, or already-converted lines | Become `fact_kind: metric_sample` |
| Logs / structured events | OTLP logs, JSON, syslog | Become `event` |
| Traces (if door/leaf needs them) | OTLP / Jaeger / Zipkin | Become `trace_span` |
| Topology cues | `topo_update` lines **or** a sibling `topology.json` | E1 only carries `topo_update`; E3 interprets |
| Optional pre-marked crossings | `anomaly` | Replay may pre-tag; live Detect is E6 |

**Do not send to E1 this pass:** ServiceNow tickets, CMDB dumps, deploy tickets (`ticket`, `cmdb_sync`, `change_event` are reserved).

### 3.2 What E1 emits (the ingest we actually consume)

**Format:** UTF-8 **JSONL**, one JSON object per line, time-ordered.

**Envelope:** `schema_version` must be `"ingest.v1"`. Wrong version or unknown `fact_kind` → reject / dead-letter (not E2’s problem).

Minimum fields (see LLD-E1 §2):

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
  "threshold": 1000.0,
  "labels": { "source": "lab-node", "env": "rca-lab" }
}
```

At **E1**, `ci_id` / `ci_type` may be placeholders. Poison lines never become synthesized ids.

**Preferred delivery for a lab incident** ([`INGEST_DATA_FORMAT.md`](../../docs/INGEST_DATA_FORMAT.md) Option A):

```
datasets/ingest_samples/<suite>/<incident_id>/
  stream.jsonl       # ingest.v1
  topology.json      # nodes/edges for E3 (same family as ObserveOps corpus)
  ground_truth.json  # eval only
  manifest.json      # optional
```

Live Node: same JSON objects on a stream (Vector / OTLP converter → `ingest.v1`). There is no long-running E1 service in-repo yet; converters today are the stand-in.

---

## 4. What we expect from E2 (we do not build this)

Someone else **binds**. This workstream only **reads** identified lines. A and B writers ignore `identity.status != resolved`.

**Contract:** [`LLD-E2-Identity.md`](../../docs/LLD-E2-Identity.md) (Done).

**Input:** each `ingest.v1` line from E1.  
**Output:** the **same** line plus identity overlay (`IdentifiedRecord`):

```json
"identity": {
  "status": "resolved",
  "bind_source": "topology_lookup",
  "aliases": ["monitor-88"]
}
```

| `identity.status` | May be E9 leaf / ticket CI? |
|-------------------|------------------------------|
| `resolved` | Yes |
| `unattributed` | No (queue, FR-B1) |
| `synthesized` | No (**D-E2-1**) |

Until converters emit `identity.*`, Motadata `labels.bound` and ObserveOps `"Unknown"` `ci_type` are proxies — **follow-up is to emit the overlay** before A/B writers trust the key.

**What we need from the lab for E2:** a bind strategy — topology lookup (ObserveOps corpus) **or** Motadata-style `ci_bind.json` (object.name / hostname / plugin fallback). Do not invent a third identity namespace for sketches vs graph.

**Pillars A and B write only `identity.status = resolved` rows** (or equivalent proxy). Unresolved traffic stays queryable; it does not become graph vertices or sketch identity.

---

## 5. Output artifacts this work generates

| Artifact | Producer | Format | Consumer |
|----------|----------|--------|----------|
| Lab `stream.jsonl` | **Upstream E1+E2** (not this stream) | `ingest.v1` JSONL + `identity` | E3, E4, E6 |
| Bind table (Motadata path) | E2 | `ci_bind.json` | converter |
| **`GraphSnapshot`** | E3 + E5 | JSON (schema in LLD-E3 when Done): CIs, typed edges, provenance, `valid_from`/`valid_to` | E8, E9, E10 |
| **Sketch rows** | E4 + E5 | Store-native (files / dest table): `metric_id`, `ci_id`/`entity_id`, `window`, `season_key`, tdigest, buckets, baseline | Door C, dashboards, E10 `get_metric_baseline()` |
| Dest profile note | Gate B | Markdown | Ops |
| `Signal` samples | E6 door C (and A if in lab) | JSON matching HLD Detect | E7 |
| `CaseSeed` + merge rationale | E7 | JSON | E8 |
| `WorkingSet` | E8 | JSON: time, entity, hop, evidence budgets | E9–E10 |
| `VerdictCard` | E11 | JSON / hub render | Operator, OKR evidence |
| LLD-E3, LLD-E4 **Done** | Docs | Markdown | Engineering |
| Gate A/B/C note | Docs | Markdown | Engineering + management |
| Block-2 report + 1 session | Obj 5 | Shared-drive report | Management |

**How we publish**

| Audience | Where | What |
|----------|--------|------|
| Engineering (daily) | Docs hub `http://127.0.0.1:8765/` — this page, study QnA, job map, LLDs | Specs, schemas, examples. No `vscode://` links. |
| Engineering (code) | This repo: `ingestion-poc/`, `datasets/ingest_samples/`, LLD files | Replay + lab proof |
| Management (OKR) | Shared drive (same bar as Block-1 knowledge KR) + 1 knowledge-sharing session | Mapping story, conflict register, what we refused (D5, event vertices), demo of 3 classes closed |
| Leadership PDF | Do not rewrite it | Cite it; our resolutions live in the QnA register |

Eval-only files (`ground_truth.json`) are not product outputs; they stay in the dataset folder.

---

## 6. Documents to write for this implementation

### Already exist (use; do not duplicate)

| Doc | For | Role |
|-----|-----|------|
| Pipeline HLD | Both | Clock, D5, D3, D-E2-1 |
| LLD-E1, LLD-E2 | Engineering | Ingest + identity contracts |
| Shift-left page | Both | Node / Gateway / SaaS |
| Job map + explained + study QnA | Both | PDF mapping and conflict register |
| Operational-graph chapter | Engineering | Target E3 shape (Draft until merged into LLD-E3) |
| This file | Both | Kickoff scope |

### Must write during the work (engineering)

| Doc | When | Content |
|-----|------|---------|
| **LLD-E3 Topology vNext** | With GraphSnapshot | CI-only vertices; 15 edges; provenance; validity; who writes (SaaS); Gateway assist = non-canonical |
| **LLD-E4 Stores vNext** | With sketches | Sketch row schema; query API (`get_metric_baseline`); dest-agnostic; Gate B |
| **Gates A/B/C note** | Before / with lab | Node vs GW; dest product; which Detect classes are platform-only |
| **Sketch writer README** | With code | Windows, season_key, how to query p95 without raw scan |
| **Identified-stream contract** (short) | Kickoff | Exact ingest.v1 + identity fields E3/E4 will reject |
| **Case + verdict examples** | With obj 3–4 | One storm → one CaseSeed → VerdictCard (Layer I off) |
| **Test / acceptance list** | Before claiming Done | Matches Block-2 measurement criteria (p95 by ci_id; ≥1 hop on graph; 2 door-C classes; 3 closes) |

### Must write for management (short)

| Doc | Length | Content |
|-----|--------|---------|
| **One-pager: PDF → ObserveOps** | ≤2 pages | Three pillars mapped; P2 has no pillar; D5 not flipped |
| **Conflict register** | Already QnA §10 | Leadership vs us vs resolution — do not create a parallel spreadsheet |
| **Block-2 OKR evidence pack** | Folder | Links to hub + 3 VerdictCards + Gate notes + “out of scope” list |
| **Knowledge-sharing deck** | 1 session | Same story as the one-pager; demo not architecture archaeology |

Do **not** write a second HLD, a Motadata clone PRD, or an agent design doc in this block.

---

## 7. Suggested build order (unchanged)

Identity → dest land → Pillar A ∥ Pillar B → door C → Curate/Scope → operator VerdictCard → (later) optional Layer I.

Cyclic / Murphy-style correlation: **store** a graph+history in P1 that could support it; **run** it in P3 in a later block.

---

## 8. Related

- [Slice README](../README.md) · [Implementation scope HTML](../../docs/motadata-3pillars-implementation-scope.html) · [Graph contract brief](../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md)  
- [Study QnA](../../docs/motadata-3pillars-study-qna.html) · [Job map](../../docs/motadata-3pillars-vs-shift-left.html) · [Explained](../../docs/motadata-3pillars-architecture.html)  
- [`LLD-E1-Collect.md`](../../docs/LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](../../docs/LLD-E2-Identity.md) · [`LLD-E3-Topology.md`](../../docs/LLD-E3-Topology.md) · [`LLD-E4-Stores.md`](../../docs/LLD-E4-Stores.md)
