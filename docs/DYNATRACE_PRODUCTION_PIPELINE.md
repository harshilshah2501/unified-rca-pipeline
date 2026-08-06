# Dynatrace production pipeline — Clock A map & walkthroughs

**Audience:** engineers who need Dynatrace’s always-on fabric clear **before** comparing any other RCA engine.  
**Status:** teaching / design reference from public product framing + black-box lab observation.  
**Date:** 2026-08-03  

**Honesty labels used below**

| Label | Meaning |
|-------|---------|
| **Observed (lab)** | Seen in `dynatrace-rca-lab` / controlled tenant runs |
| **Public framing** | Dynatrace product docs / marketing-shaped architecture |
| **Inferred** | Reasonable model; not a Dynatrace-internal spec |
| **Teaching** | Simplified name/model for the storyboard (not vendor vocabulary or a measured SKU) |

**Browser:** [`dynatrace-production-pipeline.html`](./dynatrace-production-pipeline.html)  
**Lab depth:** [`../dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md`](../dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md)  
**Datadog unveil (separate):** [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) · [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html) · [`datadog-tenant-evidence-2026-08-03.md`](./datadog-tenant-evidence-2026-08-03.md)  
**Same-scenario lab compare:** [`COMPARABLE_PIPELINE_DT_DD.md`](./COMPARABLE_PIPELINE_DT_DD.md)  
**Out of scope here:** Lean vs Federated, L0/F1, CARE / Murphy / Nezha.

---

## 1. Mental model (one page)

Dynatrace is best understood as:

```text
OneAgent ──writes in parallel──► Smartscape (map)
         └─────────────────────► Grail (evidence)
                                      │
                                      ▼
                               Detectors → Events
                                      │
                                      ▼
                         Davis (uses Events + Smartscape walk + Grail pull)
```

**How to read that:** `∥` was meant as **parallel fan-out**, not “Smartscape then Grail→Detectors.”

| Path | Meaning |
|------|---------|
| OneAgent → **Smartscape** | Topology / entity graph updates (containment + call edges) |
| OneAgent → **Grail** | Metrics, traces, logs (and later events) indexed by entity + time |
| **Grail → Detectors** | Detectors score entity-keyed series (baselines/thresholds) and emit **Events** |
| Events + Smartscape + Grail → **Davis** | Merge/rank/package Problem (thin layer) |

It is **not**:

```text
Alert fires → RCA wakes → pulls raw MELT from scratch for the whole estate
```

And it is **not** a single chain `OneAgent → Smartscape → Grail → Detectors`.

**Public framing / inferred:** Davis is a **thin** ranking and packaging layer. Most of the hard work is continuous preprocessing keyed by **entity + time**.

```text
OneAgent ─┬─► Smartscape   (map: entities + relationships)
          └─► Grail        (evidence: metrics · traces · logs · events)

Read path: Events → Davis → expand Smartscape neighborhood → pull Grail (DQL) → Problem
```

**Myth to drop:** Smartscape does **not** stay fresh by querying Grail with DQL. Map and lake stay aligned via a **shared entity model**, not lake→map rebuilds.

### 1.1 How `entityId` keeps map and lake consistent (complex estate)

**Claim:** the same string (teaching: `SERVICE-INV`) is both (a) the **Smartscape node id** and (b) the **Grail partition key** on evidence. Nothing “syncs the map from the lake.” Both sides were stamped from the **same bind result**.

Using Walkthrough B’s inventory failure:

```text
BEFORE bind (Collect/Normalize) — three dialects, three raw labels, NO shared id
  span t3:   service.name=inventory   GET /stock 500   failed_call=true
  metric:    service.errors{service="inventory"} 0.92
  log:       token=inventory  ERROR pool exhausted

LUT HIT:  "inventory" | container=c8e91a  →  SERVICE-INV
          (SERVICE-INV is already / becomes the Smartscape node for inventory)

AFTER stamp + Fan-out
  Smartscape node:   SERVICE-INV  (on HOST-B; edges API--calls-->INV--calls-->DB)
  Grail rows:        entityId=SERVICE-INV + time  →  failed span, error%, pool ERROR log
```

| Store | What “SERVICE-INV” means | How it got there |
|-------|--------------------------|------------------|
| **Smartscape** | A **node** you can walk (neighbors: API, DB; not BATCH) | Discovery / CI graph upsert |
| **Grail** | Key on **evidence documents** for DQL / detectors | Bind stamped the envelope, then lake write |
| **Later Davis** | Seed/walk this **node**, then `fetch` Grail where `entityId == SERVICE-INV` | Same id string — no DQL rebuild of Smartscape |

**Consistency check (same minute):**

```text
Smartscape walk from SERVICE-API
  → neighbor SERVICE-INV   ← map says “checkout path”
  → neighbor SERVICE-PAY   ← healthy side branch
  → (no edge to SERVICE-BATCH even though BATCH is on HOST-B)

Grail pull for entityId=SERVICE-INV in the fault window
  → span t3 500 + error-rate 0.92 + pool ERROR
  → does NOT pull batch CPU (that is entityId=SERVICE-BATCH)
```

If bind were wrong (soft-match `inv-svc-v2` → PAY by mistake), **both** map-facing stamps and lake evidence would lie together — identity alignment amplifies alias errors; it does not mean lake refreshes map.

---

## 2. Clock A stages → Dynatrace technology

We use **our Clock A vocabulary** against **Dynatrace product names**. “Fan-out” here means **parallel write to map + lake**, not a cost-tier bakeoff.

| Clock A stage | Dynatrace technology | What it does |
|---------------|----------------------|--------------|
| **Collect** | **OneAgent** (or OTLP into the tenant) | Edge capture: spans/PurePaths, process/host metrics, log cues; continuous export |
| **Normalize** | **Enrichment + failure rules + entity preparation** | Uniform meaning (e.g. 5xx → failed call); raw identity fields ready for bind |
| **Topology bind** | **Smartscape** + **entity resolution (bind LUT role)** | Live CI/relationship graph **and** stamp each record with stable `entityId` |
| **Fan-out** | **Parallel write: Smartscape + Grail** | Same capture stream → map (relationships) and lake (evidence) |
| **Maintain** | **Grail lifecycle + Smartscape freshness** | Retention/sampling/indexing; continuous topo updates |
| **Detect** | **Detectors → Events** | Async thresholds/baselines on indexed series. **Event ≠ Problem** |
| **Curate** | **Davis event merge (partial)** | Nearby Events → one Problem narrative / primary seed story |
| **Tailor** | **Smartscape neighborhood + Grail scoped pull (DQL)** | Case-triggered: related entities + time window — not whole-lake diagnosis |

**After Tailor (one line, not Clock A detail here):** Davis ranks and packages a **Problem** (`rootCauseEntity`, evidence list, impact).

### Clock A step I/O (our vocabulary)

Same stages as a contract table. Dynatrace product names are in the map above; this is the abstract I/O we use across the repo.

| Step | Input | Process | Output |
|------|--------|---------|--------|
| **Collect** | Agents, scrapes, OTel, traps, APIs… | Receive/pull raw telemetry | Raw streams (vendor-shaped) |
| **Normalize** | Raw streams | Map to joinable envelope: `ci_id`, signal, `ts`, value… | Normalized stream |
| **Topology bind** | Discovery / CMDB / service map | Build CI relationship/dependency graph (nodes + typed edges) + bind LUT (hostname→`ci_id`) | Graph + bind table |
| **Fan-out** | Normalized envelopes | Parallel write to map + lake (Dynatrace: Smartscape ∥ Grail) — **not** a second Detect; **not** Lean/Fed | Populated stores |
| **Maintain** | Sinks + graph | Keep Smartscape edges fresh + Grail rows accumulating (lab timeline below) | Usable map + lake for Detect/Davis |
| **Detect** | Streams/stores | Thresholds / anomalies — noisy by design | Raw alert storm |
| **Curate** | Detect’s raw alerts + humans | Storm→one seed, GT, quality flags, no coaching | One honest seed `(CI, signal, t0)` |
| **Tailor** | Seed + graph + stores | Cut space/time/modality | Working set → Clock B |

**Dynatrace reading of Fan-out / Maintain:** parallel write is **Smartscape ∥ Grail** — but **not twin dumps**. Topology bind **reads/stamps** identity (`entityId`; auto-create may add a node). Fan-out then writes **different facets** of the same stream: Smartscape **relationship/property upserts** and Grail **evidence** (metrics/traces/logs/events). Lean/Fed and L0/F1 are **out of scope** on this unveil; the mechanisms page phase 3 is **Davis** (walk → Grail rank → Problem), not Lean/Fed.

#### Maintain as one checkout timeline (lab)

Maintain is **not** “split a timeseries into shaded vs pulse.” It is housekeeping while the inventory fault story runs. Animated: [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) (Maintain step).

| Beat | Smartscape (same graph as Topology) | Grail |
|------|--------------------------------------|-------|
| ① Healthy `07:25` | HOST-A/B · `FE→API→INV` (+ PAY, BATCH, DB) live | `SERVICE-INV /stock 200`, low error_rate |
| ② Fault `07:40–07:52` | **Same shape** — INV highlighted on checkout path | Rows **accumulate**: INV `500`, `error_rate 0.92`, API cascade |
| ③ Problem `07:52` | Davis **walks this same map** | Davis **pulls** INV rows → **P-26084**, `rootCauseEntity=inventory` |
| ④ Cleared `07:53` | Topology unchanged | New INV `/stock 200` — Problem can close |

Maintain does **not** pick the root cause and does **not** build a different map than Topology. It only keeps that Smartscape fresh while Grail fills.

### Lab stages 0–5 ↔ Clock A

| Lab ref stage | Clock A slot |
|---------------|--------------|
| 0 Capture | Collect (OneAgent) |
| 1 Label | Normalize (failure labeling) |
| 2 Topology | Topology (Smartscape) |
| 3 Metricize | Fan-out / Maintain (rollups into Grail) |
| 4 Eventize | Detect (Events) |
| 5 Index | Maintain (Grail entity+time); Tailor **reads** via DQL |

---

## 3. Subsystem I/O contracts

Each Dynatrace building block as **Input → Process → Output**. Labels: mostly **public framing / inferred**; lab-confirmed where noted.

### 3.1 OneAgent (edge collect)

| | |
|--|--|
| **Input** | Running processes / containers / hosts; inbound & outbound calls; local logs/metrics sensors |
| **Process** | Inject/hook; intercept HTTP (and tech-specific calls); attach resource attributes; sample/limit paths; export continuously |
| **Output** | Raw-ish telemetry streams: spans/PurePaths, process/host metrics, log cues, topology fingerprints (service name, host, PG, container, release tags) |

**Observed (lab):** Python/Flask hooks + OTLP fallback; `service.name` / `DT_CLUSTER_ID` / release tags on paths.

#### Collect is not Normalize

At Collect you **receive/pull** vendor-shaped bytes. Optional light edge work (drop noise, TLS) is fine. You do **not** yet build a joinable envelope (`entityId` / `ci_id`, `failed_call`, shared schema). That starts at **Normalize** (§5.4).

In the mechanisms storyboard, **shape + color = source dialect only** (not severity):

| Glyph | Source | Example raw (still unjoined) |
|-------|--------|------------------------------|
| ○ circle | Agents | `system.cpu.user{host:DESKTOP-1} 5.2` |
| □ square | OTel / OTLP | `resourceSpans` → `service.name=inventory`, `http.status_code=500` |
| △ triangle | SNMP traps | `snmpTrapOID=…` + `clogHistMsgText="Gi0/1 down"` |
| ◇ diamond | Vendor APIs | `{"alert_id":"A-9182","device":"fw-edge-03",…}` |

**Agent-shaped (metrics):**

```text
system.cpu.user{host:DESKTOP-1} 5.2
process.cpu{pid:4421,exe:python} 0.12
```

**OTel-shaped (span excerpt):**

```json
{
  "resource": {"attributes": [{"key": "service.name", "value": "inventory"}]},
  "spans": [{
    "name": "GET /api/stock",
    "attributes": [{"key": "http.status_code", "value": 500}]
  }]
}
```

**SNMP-shaped:**

```text
SNMPv2-Trap
  snmpTrapOID.0 = 1.3.6.1.4.1.9.9.41.2.0.1
  clogHistMsgText = "Interface GigabitEthernet0/1 down"
```

**Vendor API-shaped:**

```json
{
  "alert_id": "A-9182",
  "device": "fw-edge-03",
  "severity": "critical",
  "msg": "tunnel peer unreachable"
}
```

All four can sit in the same Collect bag. They only become comparable after Normalize (+ Topology bind for stable ids).

**Animated:** [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) · Collect step.

### 3.2 Enrichment + failure labeling (normalize family)

| | |
|--|--|
| **Input** | OneAgent (or OTLP) streams — still vendor/OTel-shaped |
| **Process** | Three related jobs — **enrichment**, **failure labeling** (when applicable), **entity preparation** — see **§5.4–5.5** |
| **Output** | Enriched envelopes with optional `failed_call`, signal, ts, raw identity keys — **not** yet a Problem; often **not** yet final `entityId` |

**Why:** later failure-rate series and detectors prefer labeled calls when they exist; continuous signals still Detect without a binary fail flag.

### 3.3 Entity resolution (bind LUT role)

| | |
|--|--|
| **Input** | Raw identity keys on envelopes (`service.name`, hostname, container id, `DT_CLUSTER_ID`, …) + discovery cues |
| **Process** | Resolve / create stable entity ids; maintain flat lookup `raw key → entityId`; auto-create when discovery-first |
| **Output** | Stamped stream: every record carries canonical **`entityId`** (and usually host/PG ids); LUT updated |

**This is not Smartscape.** It only answers “which entity does this record belong to?”

### 3.4 Smartscape (topology / CI graph)

| | |
|--|--|
| **Input** | Topology cues from OneAgent/discovery; call peers from traces; process-group / service detection rules |
| **Process** | Upsert entities; maintain **vertical** containment (HOST→PG→…→SERVICE; teaching name ≈ **`runsOn`**) and **horizontal** `calls` edges; keep graph fresh |
| **Output** | Live **property graph**: stable nodes (`SERVICE-…`, `HOST-…`, …) + **typed** edges — the map Davis expands |

**Does not:** store full metric history (that’s Grail). **Not** refreshed by DQL against Grail.

**Graph shape (teaching / public framing)**

| Question | Answer |
|----------|--------|
| Is it a DAG? | **No requirement.** FE→API→INV looks like a chain in the lab, but real Smartscape is a **directed property graph** (cycles, fan-in/out, multiple edge types are normal). |
| Are edges weighted? | **Not in our teaching RCA walk.** Davis uses **typed** topology (`calls`, containment). Failure *strength* lives in **Grail** (`failed_call`, `error_rate`, spans) by `entityId`+time — not as Smartscape edge weights. |
| Persistence job | Keep the **current** who-graph true (`lastSeen` / upserts). Semantics = “present map,” not a full telemetry archive. |

#### Smartscape on Grail (product evolution note)

**Observed (tenant UI, 2026-08):** Apps may show a banner: *“This app now uses Smartscape on Grail”* and prefer **`dt.smartscape.*`** attributes over classic **`dt.entity.*`**.

| Classic teaching | What the banner adds |
|------------------|----------------------|
| Map plane ∥ lake plane, joined by shared `entityId` | Topology/entity **semantics** are also becoming **Grail-queryable** (`dt.smartscape.*`) |
| Filter still often works as `dt.entity.service = SERVICE-…` | Legacy form; migrate toward `dt.smartscape.*` |

**Read carefully:** this does **not** mean “delete the who-graph job” or “Smartscape is rebuilt by DQL every minute.” Map vs evidence **jobs** remain. Collaboration moves from **link-by-id across backends** toward **more shared persistence/query substrate**. See also persistence note under §3.5.

### 3.5 Grail (unified lake + DQL)

| | |
|--|--|
| **Input** | Entity-stamped metrics, traces, logs, and (later) events from the platform write path |
| **Process** | Index / retain / make queryable by **`(entityId, timeRange)`**; serve DQL (and UI) reads |
| **Output** | On write: durable multimodal evidence store. On read: series, exemplars, logs, events for scoped queries |

**Write = continuous. DQL = on-demand read.** Grail is not the topology map.

**Persistence job:** remember **what happened** (hot/warm/cold retention, sampling). Detect/Tailor/Davis **pull** history; they do not walk Grail as a neighbor graph.

| Plane | Persistence style (teaching) |
|-------|------------------------------|
| Smartscape | Upsert **current** who-graph |
| Grail | Append / tier **history** by entity + time |

### 3.6 Detectors → Events (detect)

| | |
|--|--|
| **Input** | Entity-keyed series in **Grail** (error rate, response time, restarts, availability, …) + baselines/thresholds |
| **Process** | Async evaluation; change-point / threshold / anomaly style checks (**inferred** exact algos). **Does not walk Smartscape** to raise an Event |
| **Output** | **Events** — e.g. `SERVICE_ERROR_RATE_INCREASED`, `PROCESS_RESTART` — keyed by entity + time. **Event ≠ Problem** |

**Observed (lab):** inventory fault → nearby service error-rate Events before Problem packaging.

**Teaching threshold:** mechanisms canvas uses gold line **`0.30`** so INV `0.92` / API `0.78` / FE `0.71` clearly breach. That number is **Teaching**, not a lab-fitted Dynatrace SKU. Real tenants often use baselines/anomaly; our fault is hard 5xx so almost any modest line would fire.

**Where Events live:** raised **independently per entity**, but written into a **shared platform Event store** (teaching: one common Event stream/index), roughly `{ type, entityId, ts, signal, value, … }`. INV/API/FE Events are not private silos — Curate/Davis read the **same** store.

#### Phase 2 teaching glossary (Detect → Curate → Tailor)

| Term | What it is | Dynatrace product term? |
|------|------------|-------------------------|
| **Cascade** | Failure spreads along `FE→API→INV` because callers depend on INV | Everyday word — not a Detect object |
| **Event** | One Detect record: this entity’s series breached | Yes (Events) |
| **Storm** | Pile of raw Events after Detect (INV+API+FE + maybe BATCH) | **Teaching** for “many Events, not yet one Problem” |
| **Beat** | UI step on the mechanisms storyboard (① Watch … ④ Storm) | **No** — navigation only |
| **Seed** | Curate handoff `(entityId, t0)` for Tailor | **Teaching** handle — not `rootCauseEntity` |
| **Alert** (everyday) | One fused “checkout down” notification | **Detect does not** emit that fused object |
| **Problem** | Packaged RCA card after Curate→Tailor→Davis | Yes (Problems) |

**Cascade ≠ one alert.** Cascade is the topology/business story; Detect still emits **separate Events** (e.g. INV≈07:48, API≈07:49, FE≈07:50 — each series scored **on its own**).

Animated: [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) · Phase 2 Case opens. **Event ≠ Problem.**

```text
Grail series (Maintain’d)
  → Detect  → raw Events (per entity) → common Event store
  → Curate  → one case seed (entityId, t0)   // Tailor expands t0 → time corridor
  → Tailor  → working set {entities[], timeRange}
  → Phase 3 Davis → Problem P-26084
```

**Detect — how Events are raised**

| Order | Teaching Event | entityId | Why |
|-------|----------------|----------|-----|
| 1 | `SERVICE_ERROR_RATE_INCREASED` | `SERVICE-INV` | leaf 5xx / `failed_call` series breaches threshold (**teaching** line 0.30) |
| 2 | same class | `SERVICE-API` | cascade caller — **its own** detector |
| 3 | same class | `SERVICE-FE` | edge symptom — **its own** detector |
| (noise) | e.g. `PROCESS_CPU_HIGH` | `SERVICE-BATCH` | co-timed; **no** checkout `calls` edge |

Detectors score **entity-keyed Grail series** asynchronously. One breach → one Event. Cascade is many Events, not one fused alert. Smartscape is used later (**Curate** neighborhood, **Tailor** expand, **Davis** walk) — not to score the breach.

**Curate — correlate / group (inferred)**

| Beat | What happens |
|------|----------------|
| Storm in | INV + API + FE (+ BATCH noise) Events from the common store |
| Group | Merge by **time proximity** + **Smartscape neighborhood** on FE→API→INV |
| Drop noise | BATCH out / weak (no checkout edge) |
| Seed out | `(entityId≈SERVICE-INV, t0≈07:52)` for Tailor — **not yet** `rootCauseEntity`. Seed pins **one** time; Tailor builds `[t0−pre, t0+post]` |

**Tailor — space + time cut**

| Cut | Teaching result |
|-----|-----------------|
| Space | Same Smartscape as Topology; expand from seed → `{FE, API, INV, DB}`; dim PAY / BATCH |
| Time | Corridor around t0 ≈ `[07:40, 07:52]` (includes Grail evidence from **before** t0) |
| Out | Working set → Phase 3 Localize / Identify / Package |

Tailor does **not** rank the root. It scopes what Davis may read.

### 3.7 Davis → Problems (curate + localize package)

| | |
|--|--|
| **Input** | Recent Events; Smartscape neighborhood; scoped Grail evidence (metrics/traces/logs) |
| **Process** | Merge by time + topology; score `rootCauseRelevant`; pick root / affected / impact; attach evidence list (**inferred** scoring) |
| **Output** | **Problem** card — e.g. rootCauseEntity, affected entities, evidence package (lab: P-26076 style) |

**Does not:** own primary capture, topology freshness, or full-lake scan at ticket time. Thin correlator / packager.

### 3.8 Compact I/O chain

| Subsystem | In | Out |
|-----------|----|-----|
| OneAgent | Workloads / OS / calls | Raw streams + topo fingerprints |
| Enrichment / failure label | Raw streams | Enriched envelopes (`failed_call`, raw ids) |
| Entity resolution | Raw ids + discovery | `entityId`-stamped stream + LUT |
| Smartscape | Discovery + call edges | CI / relationship graph |
| Grail | Stamped multimodal writes | Indexed evidence; DQL read results |
| Detectors | Grail series | Events |
| Davis | Events + Smartscape + Grail pull | Problem |

```text
Workloads
   → OneAgent
   → Enrichment / failure label
   → Entity resolution ─┬─► Smartscape (graph upserts)
                        └─► Grail (evidence writes)
                              → Detectors → Events
                                   → Davis → Problem
```

---

## 4. Dynatrace stores — what gets updated when

| Store | Holds | Touched at |
|-------|-------|------------|
| **OneAgent (edge)** | Hooks, local buffers, export | Collect (continuous) |
| **Smartscape** | Entities + relationships | Topology bind / discovery / call-edge materialization |
| **Grail** | Metrics, traces, logs, events by `entityId` + time | After identity exists — continuous write; **DQL = read** |
| **Detectors → Events** | Normalized “something changed” records | Detect (after series exist) |
| **Davis → Problems** | Ranked package for operators | After Events (thin correlator) |

---

## 5. Normalize & bind LUT — why they matter

**Animated illustrations:** [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) · Normalize (three jobs) · Topology bind (graph ∥ LUT + miss policies) · also embedded figures in [`dynatrace-production-pipeline.html`](./dynatrace-production-pipeline.html) §5.2 / §5.4.

### 5.1 Normalize is not “pretty JSON”

Normalize makes later joins possible. Collect dumps vendor-shaped blobs; Detect, Tailor, and Davis need **`(entityId, time)`**.

| Later stage | Needs | If unbound |
|-------------|-------|------------|
| Grail write | entity-keyed series | Orphan series |
| Smartscape edges | endpoints are entityIds | Call edge floats |
| Detect → Event | `Event.entityId` | Wrong or unknown entity |
| Tailor / Davis | neighborhood + Grail pull | Cannot name `rootCauseEntity` honestly |

### 5.2 Topology bind = two independent things

“Topology bind” is a **teaching umbrella** for two sibling outputs that share discovery-era inputs. They are **not** one algorithm.

```text
Discovery / OneAgent cues  ──►  CI Graph (Smartscape)     nodes + typed edges
Telemetry stream           ──►  Bind LUT → stamp entityId on each envelope
```

| | CI Graph (Smartscape) | Bind LUT (entity resolution) |
|--|----------------------|------------------------------|
| Shape | Nodes + edges | Flat `raw key → entityId` |
| Purpose | Relationship **traversal** (k-hop / Davis neighborhood) | Identity on each record |
| Access | Neighbors / paths | Point lookup per ingest record |

**“Pin on the map”** (informal) = the stable **entity / `entityId` / Smartscape node** (e.g. `SERVICE-INV`). Prefer those exact terms in engineering talk.

#### Does Bind LUT help CI graph traversal?

**No.** Traversal walks **Smartscape edges**. The LUT only answers “which `entityId` does this raw label belong to?”

LUT helps traversal **indirectly**: once an Event is stamped `entityId=SERVICE-INV`, Davis knows **which node** to start the walk from. The walk itself uses `calls` / containment edges, not the LUT.

#### Walkthrough (complex estate) — both products in play

**CI Graph (relationships):**

```text
HOST-B: SERVICE-INV, SERVICE-BATCH, SERVICE-DB
FE --calls--> API --calls--> INV --calls--> DB
               API --calls--> PAY
```

Davis can walk INV’s neighborhood on this graph. BATCH shares HOST-B but is **not** on the checkout path — that distinction is **graph structure**, not LUT.

**Bind LUT (identity):**

```text
"inventory" | container=c8e91a  →  SERVICE-INV
"batch-job"                     →  SERVICE-BATCH
"inventory-db"                  →  SERVICE-DB
"payments"                      →  SERVICE-PAY
```

| Record | After LUT |
|--------|-----------|
| failed span GET /stock | `entityId=SERVICE-INV` |
| error-rate metric | `entityId=SERVICE-INV` |
| pool ERROR log | `entityId=SERVICE-INV` |
| batch CPU metric | `entityId=SERVICE-BATCH` |

Same failing process’s span, metric, and log now share one node id so Grail joins them; the graph still decides who is upstream/downstream.

#### Why encapsulate both under one Clock A step?

| Reason | Detail |
|--------|--------|
| Shared upstream | Both fed by discovery / OneAgent cues in the same pipeline era |
| Shared vocabulary | Both answer “who is this entity in the estate?” |
| Teaching convenience | One stage means “we now have a map **and** stamped streams” |

Prefer naming them explicitly when precision matters: **Topology (Smartscape)** and **Entity resolution (LUT)** — sibling outputs of “Topology bind,” not one fused mechanism.

### 5.3 Discovery-built graph vs CMDB as “ultimate truth”

**Question:** When the CI graph is created from raw telemetry, does Dynatrace verify it against CMDB because CMDB holds predefined truth?

**Answer (public framing / lab):** **Usually no.** Dynatrace Smartscape is **discovery-first**. Observed processes/services/call edges become graph nodes without waiting for a CMDB row. The lab’s `frontend` / `product` / `inventory` appear from OneAgent/OTLP observation even with almost no ServiceNow-style inventory.

| Source | Role |
|--------|------|
| Live discovery (OneAgent) | Primary: create/update HOST / PG / SERVICE + `calls` edges from what is *seen* |
| CMDB / provisioned inventory | Optional: enrich, merge, tag — **not** required for Smartscape to exist |

**CMDB-first designs** (classic infra / strict “provisioned CIs only”) flip this: graph nodes come from inventory first; telemetry must **bind** to those CIs; unresolved streams orphan or wait. That is a different philosophy than Dynatrace’s default.

### 5.3.1 Unresolved streams — three conditional actions

**Trigger:** a record’s identity keys (e.g. `service.name=inv-svc-v2`) **miss** the Bind LUT — no known `entityId` yet.

```text
raw service.name="inv-svc-v2"  →  LUT lookup  →  MISS
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
        (1) Auto-create         (2) Orphan              (3) Soft-match
            new entity              quarantine              alias to existing
```

#### (1) Auto-create entity (Dynatrace-like default for many cases)

| | |
|--|--|
| **What happens** | Platform creates a new Smartscape node (e.g. `SERVICE-NEWxxxx`), adds LUT rows for the raw keys, stamps the stream with that id, writes evidence to Grail under it |
| **Why** | Don’t drop live traffic; microservices churn; discovery-first products assume “seen ⇒ exists” |
| **Risk** | Splits: same real service under two names (`inventory` vs `inv-svc-v2`) → two nodes, fractured metrics/Problems |
| **Reflect in CMDB?** | **No, not automatically.** Auto-create updates the **observability graph** (Smartscape) and LUT. CMDB is a separate system of record. Syncing a new CI *into* ServiceNow/CMDB is an optional integration / ITSM workflow — Dynatrace does not imply “every discovered service becomes a CMDB CI.” |

**Lab-shaped example:** first time OneAgent sees `inventory`, there is no prior LUT row → auto-create `SERVICE-INV` in Smartscape. No CMDB ticket required.

#### (2) Orphan / quarantine (`unbound=true`) — stricter CMDB designs

| | |
|--|--|
| **What happens** | Keep the telemetry (or a sample) but **do not** attach a production `entityId`; flag `unbound=true` / park in an orphan bucket; Detect/Tailor/Davis often **ignore** or show as “unmonitored” |
| **Why it exists** | CMDB/governance says: only **approved** CIs are first-class. Auto-creating graph nodes would pollute topology, tickets, and chargeback with shadow services, typos, and one-off test traffic |
| **When to use** | Regulated estates, classic infra with a frozen CI list, “unknown hostname must not become a root-cause candidate” |
| **Tradeoff** | You **don’t lose bytes**, but you **lose joinability** until a human/rule adds the CI and bind mapping |

**Example:** scrape arrives as `service.name=inv-svc-v2`. Policy forbids auto-create. Record stored with `unbound=true`. No Smartscape node, no Davis root on that name, until CMDB adds the CI and LUT maps `inv-svc-v2 → SERVICE-INV`.

#### (3) Soft-match / alias — risky if wrong

| | |
|--|--|
| **What happens** | Heuristic or configured alias maps the unknown key onto an **existing** entity (`inv-svc-v2` → `SERVICE-INV`) without creating a new node |
| **Why it exists** | Renames, env suffixes (`inventory-prod` vs `inventory`), IP↔hostname, temporary dual naming during cutover — you want **one** node so series don’t split |
| **Risk** | Wrong alias **coaches the wrong root**: noise from service B stamped as service A; Davis blames the wrong CI |
| **When to use** | Explicit alias tables, high-confidence rules (same cluster id + port), never blind fuzzy match on production RCA path without review |

**Example (good):** rule `inv-svc-v2` alias of `inventory` → stamp `SERVICE-INV` (merge).  
**Example (bad):** fuzzy match `inv*` → `SERVICE-INV` also catches an unrelated `invoice-api` → corrupted join.

#### Choosing among the three

| Goal | Prefer |
|------|--------|
| Don’t miss new services; discovery-first SaaS | **(1) Auto-create** |
| Don’t invent CIs; CMDB is gate | **(2) Orphan** until approved |
| Known rename / dual name, keep one pin | **(3) Soft-match** with explicit aliases |
| Avoid silent wrong roots | Never rely on aggressive fuzzy **(3)** alone |

**Dynatrace default leaning:** **(1)** for many process/service discoveries; CMDB sync is optional and **one-way or mediated**, not “auto-create ⇒ CMDB row.” Our ObserveOps-style kits can choose **(2)** when the CI list is frozen for fair bakeoffs.

### 5.4 Enrichment · failure labeling · entity preparation (three Normalize jobs)

These are three **Normalize-family** jobs — not synonyms. Using the complex checkout raw scrap:

```text
span: GET /stock  status=500  service.name=inventory  container=c8e91a
metric: http_requests{service="inventory",status="500"} 40
log: [inventory] ERROR connection pool exhausted
span: POST /charge status=200  service.name=payments   (healthy side branch)
```

#### Enrichment — shape + context

Add fields so the record is usable later (modality, units, host/container hints, tech fingerprints). IDs may still be **raw**.

```text
{ ts, modality=trace, signal=http.request, value=500,
  raw_ids=[service.name=inventory, container=c8e91a],
  host_hint=k8s-node-b, tech=python/flask }
```

#### Failure labeling — meaning of “bad call” (when applicable)

Apply rulesets so request-shaped telemetry gets a discrete outcome flag.

```text
status=500  →  failed_call=true    (e.g. INV stock span)
status=200  →  failed_call=false   (e.g. PAY charge span)
```

Later failure-rate series and detectors prefer this flag over re-parsing “HTTP 500” strings. See **§5.5** — this is **not** always possible or always `status!=200`.

#### Entity preparation — identity keys ready to bind

Normalize name tokens / cluster ids / aliases so entity resolution can stamp a stable id.

```text
raw:  service.name="inventory", DT_CLUSTER_ID=inventory, container=c8e91a
prep: lookup keys ready → LUT → entityId=SERVICE-INV
```

| Piece | Job in one line |
|-------|-----------------|
| Enrichment | Shape + context |
| Failure labeling | Discrete success/fail when the modality has one |
| Entity preparation | Identity keys ready for the bind LUT |

#### Normalize as a fork (teaching)

STEP 1 builds **one envelope**, then two jobs use **different fields** from it:

```text
STEP 1 Enrichment
  envelope = { status=500, raw_ids=[service.name=inventory, container.id=c8e91a], … }
       │
       ├── status ──────────► STEP 2 Failure label ──► failed_call=true
       │                         (Detect / failure-rate later — NOT used by LUT)
       │
       └── raw_ids ─────────► STEP 3 Entity prep ──► lookup_keys=["inventory","c8e91a"]
                                 (Bind path — STEP 3 does not read failed_call)
```

**Bind LUT preview** (what Topology tries next — flat table, not a graph):

| lookup_key | entityId | notes |
|------------|----------|-------|
| `inventory` | `SERVICE-INV` | HIT · primary |
| `c8e91a` | `SERVICE-INV` | HIT · same Smartscape node |
| `orders-api` | `SERVICE-API` | HIT |
| `payments` | `SERVICE-PAY` | HIT · healthy side branch |
| `batch-job` | `SERVICE-BATCH` | HIT · red herring (no checkout edge) |
| `inv-svc-v2` | — | MISS → auto-create / orphan / soft-match |

First HIT among `lookup_keys[]` stamps `entityId` on the record. Animated storyboard: [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) (Normalize step).

### 5.5 Failure labeling is not always binary

**Question:** Is it always possible to flag failures as binary (`status=200` vs everything else)? What if there is no status?

**Answer:** No. Failed-call labeling is a **convenience for request-shaped telemetry with a clear outcome**, not a universal Normalize law. It is **ruleset-driven**, not a naive `status!=200`.

| Case | Typical rule |
|------|----------------|
| HTTP 5xx / many exceptions | `failed_call=true` |
| HTTP 2xx (sometimes 3xx) | `failed_call=false` |
| HTTP 4xx | Often **not** counted as *server* failure (client error) |
| Timeouts / cancels | Own rules — not the same as 500 |

**When there is no status** — do **not** invent a fake HTTP failure bit. Use other signals; leave `failed_call` unset:

| Situation | What to use instead |
|-----------|---------------------|
| All 200s but slow | Response-time / SLO Detect — no `failed_call` |
| Process crash / OOM / restart | Process / availability Events |
| Queue depth / pool exhaustion | Saturation metrics + thresholds |
| DB lock wait, disk full | Infra/DB metrics + logs |
| Gray / soft unhealth | Baselines / LOS-style Detect |
| Metrics-only (CPU, memory) | Entity-level anomaly — never a per-call `failed_call` |

```text
Has discrete outcome?  (HTTP status, exception, explicit error code)
  → yes: apply failure ruleset → failed_call true/false (or unknown)
  → no:  enrich only → Detect on metrics / events / baselines
```

**Dynatrace-shaped:** failed-call labeling feeds **failure-rate** on services with request paths; many Problems still start from **other** Events (restarts, response-time increase, mixed error signals) when status is not the story.

In the complex walkthrough: INV’s 500 span is a classic `failed_call=true`; BATCH high CPU and DB lock waits are **not** HTTP failure labels — they become Detect inputs as continuous series.

---

## 6. Walkthrough A — simple lab (`dynatrace-rca-lab`)

### 6.1 Prerequisites

1. Topology up: `frontend → product → inventory`  
2. Capture on: OneAgent Python injection **or** OTLP (`OTEL_SERVICE_NAME` / `DT_CLUSTER_ID` in compose)  
3. Optional fault: `inventory.fail` → HTTP 500  
4. Shared UTC (ignore skew for teaching)  
5. Discovery-first (not full CMDB preload) — §5.3  
6. Teaching IDs only (not a real tenant dump)  
7. Logical order; in production Topology runs **beside** Collect  
8. This section stops after Topology bind (+ Grail land)  
9. Applies §5.2–5.5: three Normalize jobs; graph ∥ LUT; non-binary failure labels; unresolved-stream policies

### 6.2 Raw bag

**Traces**

```text
span-1  07:19:30.010  GET /           service.name=frontend   200  → product
span-2  07:19:30.040  GET /product    service.name=product    200  → inventory
span-3  07:19:30.080  GET /inventory  service.name=inventory  500
```

**Metrics**

```text
http_requests{service="inventory",status="500"} 40
process_cpu{container="c8e91a"} 0.12
```

**Logs**

```text
07:19:30.081 inventory ERROR GET /inventory 500
```

**Discovery**

```text
host=docker-desktop container=c8e91a :8082 python → name_hint=inventory
(+ similar for product, frontend)
```

### 6.3 Collect

**Dynatrace:** OneAgent/OTLP exports raw shapes. No join yet. No CMDB check required (discovery-first — §5.3).

| Store | Update |
|-------|--------|
| OneAgent buffers | Yes |
| Smartscape | Not coherently for this moment yet (or only stale prior state) |
| Grail | May receive bytes; not one RCA join story yet |
| Events / Davis | No |
| CMDB | Untouched |

### 6.4 Normalize — three jobs on the raw bag

Apply **enrichment**, **failure labeling** (only where a discrete outcome exists), and **entity preparation** (§5.4–5.5). IDs still **raw**.

#### Enrichment

```text
span-3 → {ts, modality=trace, signal=http.request, value=500,
          raw_ids=[service.name=inventory, container=c8e91a], tech=python}
metric http → {modality=metric, signal=http.requests, value=40,
               raw_ids=[service=inventory, status=500]}
metric cpu  → {modality=metric, signal=process.cpu, value=0.12,
               raw_ids=[container=c8e91a]}          ← no HTTP status
log         → {modality=log, level=ERROR, raw_ids=[token=inventory],
               message="GET /inventory 500"}
```

#### Failure labeling (not universal binary)

| Record | Has discrete outcome? | Label |
|--------|----------------------|--------|
| span-3 status=500 | Yes | `failed_call=true` (5xx ruleset — not merely `!=200`) |
| span-1/2 status=200 | Yes | `failed_call=false` |
| process_cpu metric | **No status** | **No** `failed_call` — leave unset; Detect later if needed |
| ERROR log | Corroboration text | Not a substitute for span failure rules |

#### Entity preparation

```text
keys ready for LUT: "inventory", container=c8e91a, DT_CLUSTER_ID=inventory, …
```

| Store | Update |
|-------|--------|
| In-stream / failure rulesets | Yes (on request-shaped spans) |
| Smartscape / Grail / Davis | Not the main write |

### 6.5 Topology bind — two sibling outputs (§5.2)

Not one fused step: **(A) CI Graph** then/alongside **(B) Bind LUT**, then stamp → Grail.

#### A) CI Graph (Smartscape) — relationships only

Discovery observes processes; call peers from spans. **Auto-create** entities if first sighting (§5.3.1) — **does not** write CMDB.

```text
HOST-DD001
  ├─ SERVICE-FE7A00  (frontend)
  ├─ SERVICE-PRD4C1B (product)
  └─ SERVICE-INV9F2A (inventory)

FE --calls--> PRD --calls--> INV
```

**Traversal** (later Tailor/Davis) walks these edges. The LUT is not used for neighbor expansion.

#### B) Bind LUT — identity only

```text
"inventory" | service.name=inventory | container=c8e91a → SERVICE-INV9F2A
"product"   | …                                         → SERVICE-PRD4C1B
"frontend"  | …                                         → SERVICE-FE7A00
```

**Unresolved?** If a typo `service.name=inventroy` arrived: lab/Dynatrace-like → **auto-create** a *second* node (split risk); CMDB-strict → **orphan**; known alias table → **soft-match** to `SERVICE-INV9F2A` (§5.3.1).

#### C) Stamp stream → Grail

| Record | `entityId` | Notes |
|--------|------------|--------|
| span-3 (`failed_call=true`) | `SERVICE-INV9F2A` | Request failure joins here |
| 500-count metric | `SERVICE-INV9F2A` | |
| CPU on `c8e91a` | `SERVICE-INV9F2A` | Same node via container key — **no** `failed_call` |
| ERROR log | `SERVICE-INV9F2A` | |

| Store | Update |
|-------|--------|
| **Smartscape** | Nodes + call edges (graph) |
| **Bind LUT** | raw→entityId rows |
| **Grail** | Entity-keyed spans/metrics/logs |
| CMDB | Still untouched unless a separate sync job exists |
| Events / Davis | Not yet |

**End fact:** at 07:19:30, **`SERVICE-INV9F2A`** has failed span + elevated 500s + ERROR log on path FE→PRD→INV. CPU shares the same entity via LUT, not via graph traversal.

---

## 7. Walkthrough B — complex multi-host estate

### 7.1 Estate

```text
HOST-A (k8s-node-a)
  SERVICE-FE    frontend
  SERVICE-API   orders-api
  SERVICE-PAY   payments          ← healthy side branch

HOST-B (k8s-node-b)
  SERVICE-INV   inventory         ← failing (pool / 500s)
  SERVICE-BATCH batch-job         ← high CPU (red herring)
  SERVICE-DB    inventory-db      ← lock waits (shared dependency)

Calls:  FE → API → INV → DB
        FE → API → PAY
```

**Prerequisites:** OneAgent on both hosts; UTC; **discovery-first** (no CMDB gate); teaching ids `SERVICE-FE` … `SERVICE-DB`. Insights from §5.2–5.5 applied below.

### 7.2 Raw bag (same ~minute)

**Traces**

```text
# Broken checkout
t1 FE    GET /checkout     200  → API
t2 API   POST /order       200  → INV, also → PAY
t3 INV   GET /stock        500  → DB (timeout)
t4 PAY   POST /charge      200     (side branch OK)

# Noise
t5 BATCH run-job           200

# Unresolved name (teaching) — dual labeling during a rename
t6 INV   GET /stock        500  service.name=inv-svc-v2   ← not yet in LUT
```

**Metrics**

```text
service.errors{service="inventory"}           ↑
service.responsetime{service="orders-api"}    p95 ↑
cpu{service="batch-job"}                      0.88   ← red herring; no HTTP status
db.lock_wait{service="inventory-db"}          ↑       ← no HTTP status
cpu{host="k8s-node-b"}                        ↑
```

**Logs**

```text
INV   ERROR  connection pool exhausted
DB    WARN   lock wait timeout
API   WARN   upstream inventory 500
BATCH INFO   job progress 80%
```

### 7.3 Collect → what Dynatrace updates

Hooks on HOST-A/B; export spans/metrics/logs + process fingerprints. No CMDB verification.

| Store | Update |
|-------|--------|
| OneAgent | Yes |
| Smartscape / Grail | Not yet a coherent joined incident view |
| Events / Davis / CMDB | No |

### 7.4 Normalize — enrichment · failure label · entity prep

Normalize does **not** assign `entityId`. It builds a joinable *envelope* with **raw identity cues** so Topology bind can look them up.

#### Where do `raw_ids` come from?

`raw_ids` = the **identity-bearing fields already present on the vendor record** (or lightly copied from resource attributes / metric labels / log parse). Teaching name only — Dynatrace does not require this exact JSON key.

| Source dialect | Typical fields copied into `raw_ids` |
|----------------|--------------------------------------|
| **Trace / span** | `service.name`, optional `service.namespace`, `container.id` / `k8s.pod.name`, `dt.entity.process_group` cues, peer service on client spans |
| **Metric** | Label set used for the series: `service=…`, `host=…`, `dt.entity.service=…` if already enriched |
| **Log** | Parsed tokens: service/app name from structured field, or a **token** scraped from the message / MDC (teaching: `token=inventory`) — not a Dynatrace product type named “token” |
| **Discovery** | Process exe, listen ports, host name, k8s workload name |

**“token”** in log examples = “whatever string we extracted as a *candidate identity key*” (structured `service=` field preferred; message scrape is fallback and fragile).

#### Concrete envelopes after Normalize (still **raw** ids)

```text
# span t3 — broken INV call
{
  ts: "…T12:00:03Z",
  modality: "trace",
  signal: "http.request",
  value: 500,
  failed_call: true,                    // failure labeling (has HTTP status)
  raw_ids: [
    "service.name=inventory",
    "container.id=c8e91a",
    "k8s.pod.name=inventory-7f2…"
  ],
  host_hint: "k8s-node-b",
  tech: "python/flask"
}

# metric — same service, different dialect
{
  ts: "…T12:00:00Z",
  modality: "metric",
  signal: "service.errors",
  value: 0.92,
  failed_call: unset,                   // rate series — not a per-call bit
  raw_ids: ["service=inventory"]        // from metric labels {service="inventory"}
}

# log INV — identity from structured field or message token
{
  ts: "…T12:00:04Z",
  modality: "log",
  level: "ERROR",
  msg: "connection pool exhausted",
  raw_ids: ["token=inventory"]          // teaching: extracted name candidate
}

# metric BATCH — red herring (no HTTP status)
{
  signal: "cpu", value: 0.88,
  failed_call: unset,
  raw_ids: ["service=batch-job"]
}

# span t6 — rename dual-write (will MISS LUT unless alias exists)
{
  failed_call: true,
  raw_ids: ["service.name=inv-svc-v2"]
}
```

#### How are `lookup_keys` prepared? (entity preparation)

Entity prep **canonicalizes** `raw_ids` into an ordered list of keys the Bind LUT will try (first HIT wins). It still does **not** invent `entityId`.

```text
raw_ids:  service.name=inventory, container.id=c8e91a, k8s.pod.name=inventory-7f2…
     │
     ▼  entity preparation (normalize case, strip env suffixes if configured,
        prefer stable keys, drop junk)
lookup_keys[] (ordered):
  1. "inventory"              ← from service.name (primary)
  2. "c8e91a"                 ← container (secondary; often already maps to same SERVICE)
  3. "inventory-7f2…"         ← pod (optional; may auto-create PG/pod entities in real DT)
```

| Prep step | Example |
|-----------|---------|
| Lowercase / trim | `"Inventory "` → `"inventory"` |
| Prefer service over ephemeral | Use `service.name` before pod hash for *service*-level RCA |
| Alias hints (optional) | Config says `inv-svc-v2` is a rename of `inventory` → emit both keys, or only the canonical |
| Host keys | `k8s-node-b` → lookup key for `HOST-B` |

```text
Known keys after prep: inventory, orders-api, payments, batch-job, inventory-db, k8s-node-a, …
Unknown key:           inv-svc-v2  →  LUT MISS in §7.5 unless alias/auto-create/orphan policy
```

#### Failure labeling — only where status/exception exists (§5.5)

| Record | `failed_call`? |
|--------|----------------|
| span t3 INV 500 | `true` |
| span t4 PAY 200 | `false` |
| span t5 BATCH 200 | `false` (job OK — CPU issue is separate) |
| span t6 `inv-svc-v2` 500 | `true` (has status) — identity still unresolved |
| `cpu{batch-job}` | **unset** — no status; continuous signal only |
| `db.lock_wait` | **unset** — Detect on metric later, not a failed HTTP call |
| pool ERROR log | text corroboration, not a span failure bit |

| Store | Update |
|-------|--------|
| Pipeline / failure rules | Yes (on HTTP spans only) |
| Smartscape | Not primary |
| Grail | Clean join waits on bind |

### 7.5 Topology bind — CI Graph ∥ Bind LUT → Grail

#### A) CI Graph (Smartscape) — for traversal

```text
HOST-A: FE, API, PAY
HOST-B: INV, BATCH, DB

FE --calls--> API --calls--> INV --calls--> DB
               API --calls--> PAY
```

Davis/Tailor **walk** INV→API→FE and INV→DB on these edges. BATCH shares HOST-B but has **no** checkout `calls` edge — graph structure, not LUT, separates the red herring.

#### B) Bind LUT — for identity (not traversal)

```text
LUT (teaching):
  "inventory" | "c8e91a" | …     → SERVICE-INV
  "orders-api"                   → SERVICE-API
  "payments"                     → SERVICE-PAY
  "batch-job"                    → SERVICE-BATCH
  "inventory-db"                 → SERVICE-DB
  "frontend"                     → SERVICE-FE
  "k8s-node-a" / "k8s-node-b"  → HOST-A / HOST-B
```

**HIT path:** try `lookup_keys[]` in order → first match → stamp `entityId` on the record → Fan-out may write **Grail** under that id (and Smartscape edge/property upserts).

#### Unresolved keys — three MISS policies (§5.3.1)

**Important:** Grail’s *clean* join needs an `entityId`. **Not all three policies provide one.**

```text
lookup_keys → LUT → MISS (e.g. service.name=inv-svc-v2)
                      │
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
 (1) Auto-create  (2) Orphan      (3) Soft-match
     NEW entityId     NO entityId     EXISTING entityId
     → Grail yes      → Grail no*     → Grail yes
```

\*Orphan may still store bytes in a quarantine / unbound bucket; they are **not** first-class Grail evidence under a production `entityId` for Detect/Davis.

| Policy | Guarantees `entityId`? | What happens | Grail / Davis |
|--------|------------------------|--------------|---------------|
| **(1) Auto-create** | **Yes** — brand-new id (e.g. `SERVICE-NEWxxxx`) | Create Smartscape node + LUT rows for the raw keys; stamp stream | Writes under the **new** id. Risk: **split** from real `SERVICE-INV` if this was only a rename |
| **(2) Orphan** | **No** | Keep/sample telemetry with `unbound=true`; **do not** invent a production entity | **Not** joinable for normal Detect/Davis until a human/CMDB adds a LUT row. Does **not** “discard bytes” by default — it discards **joinability** |
| **(3) Soft-match** | **Yes** — maps onto an **existing** id | Alias/heuristic: `inv-svc-v2` → `SERVICE-INV` | Writes under existing pin. Risk: **wrong** alias coaches the wrong root |

##### 4.1 Auto-create — creates a new entity?

**Yes.** First time the platform sees an unknown key under discovery-first policy, it **creates** a Smartscape service/host/PG node, adds LUT entries, stamps that new `entityId`, then Grail can accept the write. **Does not** auto-create a CMDB CI.

##### 4.2 Orphan — simply discards?

**No (usually).** Bytes can be kept as unbound/unmonitored; what you “discard” is eligibility as a root-cause entity until bind exists. Stricter estates may sample/drop — teaching default = quarantine, not delete.

##### 4.3 Soft-match — maps any entity-id?

**No.** It maps the unknown key to **one chosen existing** `entityId` via **explicit alias or high-confidence rule** — not “any” id, and not blind fuzzy match on the RCA path.

Teaching default in this walkthrough: treat **(3)** as rename cutover so t6 joins `SERVICE-INV`; call out **(1)/(2)** as alternatives.

#### C) Stamp → Grail (Fan-out evidence facet)

| Record | `lookup_keys` (abbrev.) | Policy / HIT | `entityId` |
|--------|-------------------------|--------------|------------|
| span t3, INV errors, pool ERROR | `inventory`, `c8e91a` | HIT | `SERVICE-INV` |
| span t6 `inv-svc-v2` | `inv-svc-v2` | soft-match → INV | `SERVICE-INV` |
| lock_wait + DB WARN | `inventory-db` | HIT | `SERVICE-DB` |
| batch CPU | `batch-job` | HIT | `SERVICE-BATCH` |
| span t4 | `payments` | HIT | `SERVICE-PAY` |

| Store | Update |
|-------|--------|
| **Smartscape** | Full neighborhood + call graph |
| **LUT** | Known keys (+ alias if soft-match; + new rows if auto-create) |
| **Grail** | Joinable multimodal evidence **only for stamped records** |
| CMDB | Untouched by auto-create / soft-match unless separate sync |
| Detectors | *Next* — INV error-rate Event; DB lock_wait Event; BATCH cpu Event (**no** failed_call required) |
| Davis | *Later* — walk **graph** from seed entity; pull **Grail** |

### 7.6 Why complexity matters

After bind (still before Davis):

```text
SERVICE-INV   failed spans (failed_call) + error% + pool logs
SERVICE-DB    lock waits + WARN     ← continuous Detect, not HTTP fail bit
SERVICE-BATCH high CPU only         ← same HOST-B, not on call path (graph)
SERVICE-PAY   healthy side branch
inv-svc-v2    resolved only if soft-match/orphan/auto-create policy says so
```

- **Graph** keeps BATCH/PAY from being confused with INV’s call-chain role.  
- **LUT** makes span/metric/log for INV share one `entityId`.  
- **Failure label** applies to INV 500 spans; BATCH CPU and DB locks rely on Detect without `failed_call`.

### 7.7 Timing honesty

Production is continuous and async:

```text
OneAgent ──async──► Smartscape updates     (continuous; auto-create entities)
OneAgent ──async──► Grail writes           (continuous; after/with entity ids)
Detectors ─async──► Events                 (continuous; series ± failed_call rates)
Davis ────react──► Problem open/update    (event-driven; walk graph + pull Grail)
UI drill-down ──query──► Grail DQL         (on-demand)
CMDB sync (optional) ──mediated──► not implied by Smartscape auto-create
```

Teaching order Collect → Normalize (3 jobs) → Topology bind (graph ∥ LUT) remains the right **logical** sequence.

---

## 8. Concrete record examples (bind in one glance)

Teaching LUT after discovery stabilized:

```text
"inventory"               →  SERVICE-INV9F2A
"product"                 →  SERVICE-PRD4C1B
"frontend"                →  SERVICE-FE7A00
hostname "docker-desktop" →  HOST-DD001
container "c8e91a…"       →  SERVICE-INV9F2A
```

### Trace

**Raw Collect**

```json
{
  "ts": "2026-07-28T07:19:30.120Z",
  "name": "GET /inventory",
  "http.status_code": 500,
  "service.name": "inventory",
  "net.host.name": "c8e91a3f2b1d",
  "process.pid": 17
}
```

**After Normalize + LUT**

```json
{
  "ts": "2026-07-28T07:19:30.120Z",
  "signal": "http.request",
  "value": 500,
  "failed_call": true,
  "entityId": "SERVICE-INV9F2A"
}
```

### Metric

**Raw:** `http_server_requests{service="inventory",status="500"} 42`  

**Grail:** `(entityId=SERVICE-INV9F2A, metric=service.errors.server.rate, t=07:19) → 100%`

### Log

**Raw:** `2026-07-28T07:19:30Z [inventory] ERROR: "GET /inventory" 500`  

**Bound:** `{ entityId: "SERVICE-INV9F2A", hostId: "HOST-DD001", level: "ERROR", … }`

### Unknown stream

```json
{ "service.name": "inv-svc-v2", "http.status_code": 500 }
```

LUT miss → auto-create new service entity, orphan, or configured alias (dangerous if wrong).

---

## 9. Beyond bind (short) — Detect → Tailor → Davis

Still Dynatrace-only; detail deferred to the lab reference for algorithm internals.

| Step | Dynatrace | Store touch |
|------|-----------|-------------|
| Detect | Detectors on Grail series | **Events** written (often also queryable via Grail) |
| Curate | Merge storm of nearby Events | Feeds one Problem narrative |
| Tailor | Expand Smartscape neighborhood; pull Grail for those ids + time | **Read** Smartscape + Grail (DQL) |
| Package | Davis ranks `rootCauseRelevant`, opens Problem | **Problem** card (e.g. lab P-26076) |

**Inferred selection sketch** (lab ref): seed Event entity(ies) → expand Smartscape → collect evidence in a time halo → score → package Problem.

---

## 10. Known unknowns

| Topic | Status |
|-------|--------|
| Exact Davis scoring internals | Not published; black-box + lab inference |
| Grail retention / sampling SKUs | Not specified in this repo |
| Full detector catalog | Environment-dependent |
| Automated Step-2 path-diff fused into Problem | **Not verified** — see [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) |
| Public top-1 RCA accuracy scoreboard | Self-reported / absent — see [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) |

---

## 11. Related reading

| Doc | Use |
|-----|-----|
| [`../dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md`](../dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md) | Stages 0–5, Events vs Problems, lab P-26076 |
| [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) | Separate Datadog unveil — MCP-grounded, correlational Detect/Localize |
| [`RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md`](./RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md) §4.2 · §6 | Grail vs Smartscape vs Vector (broader design context) |
| [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) | Step-1 vs Step-2 automation boundary |

---

## 12. Takeaway

1. Dynatrace’s advantage is mostly the **always-on fabric**, not a fat RCA engine.  
2. **Normalize + bind** create the shared **`entityId`** that Smartscape walks and Grail stores.  
3. **Smartscape = map; Grail = evidence; Davis = thin packager.**  
4. Complex estates need bind so side branches (PAY) and noisy neighbors (BATCH) do not collapse into the wrong root story.
