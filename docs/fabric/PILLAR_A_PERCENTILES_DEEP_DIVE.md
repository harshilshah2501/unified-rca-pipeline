# Pillar A (Percentiles) — deep dive for cold readers

**Audience:** Anyone who needs to understand Motadata’s **Pillar A** (the percentile / sketch store) without having sat in prior chats.  
**Status:** Teaching + implementation guide. Aligns with the locked leanings in the graph/sketch contract brief; not a Signed LLD by itself.  
**Date:** 2026-08-26  
**Also called:** Motadata “Pillar 1” in the teammate ownership split (same store: statistics + sketch rows).

**Read this page if you need:** what goes in, how it is processed, what comes out, who consumes it, and a full numeric example.

**PoC / hand-off package:** [`pillar-ab-implementation/pillar-a/`](../../pillar-ab-implementation/pillar-a/) (zip for teammate: `pillar-ab-implementation/pillar-a-handoff-2026-08-27.zip`).  
**Related pages (open when you need the freeze or visuals):**

| Page | Role |
|------|------|
| [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) | Locked sketch row shape (`sketch.v1`) |
| [`GRAPH_QNA.md`](../GRAPH_QNA.md) | Full graph/sketch fabric Q&A (E1–E5) — fan-outs, rooms, sketches, Detect, merge/raw |
| [`MOTADATA_3PILLARS_MERGED_SCOPE.md`](../MOTADATA_3PILLARS_MERGED_SCOPE.md) | Part C kickoff What/Why/How (shorter) |
| [`end-to-end-algorithm-walkthrough.md`](./end-to-end-algorithm-walkthrough.md) | Step-by-step algorithm with season helpers |
| [`sketch-exemplars-visual.html`](./sketch-exemplars-visual.html) | Picture of digest / buckets / baseline / exemplars |
| [`e1-e5-pipeline-architecture.html`](./e1-e5-pipeline-architecture.html) | E1→E2 fan-out: Pillar B `map/` ∥ Pillar A `history/`; E5 baseline sidecar |
| [`vortex-s3-interaction.html`](./vortex-s3-interaction.html) | How Vortex (hot query) and S3 (cold durable) interact |
| [`pillar-ab-implementation/contracts/schemas/sketch_v1.schema.json`](../../pillar-ab-implementation/contracts/schemas/sketch_v1.schema.json) | Machine schema |

---

## 1) What Pillar A is (in one plain story)

Motadata leadership materials describe **three pillars**. This page covers only the first of them:

| Motadata name | Everyday meaning | This page? |
|---------------|------------------|------------|
| **Pillar A — Percentiles** | Compact history of metrics (digests, histograms, seasonal “what is normal”) | **Yes** |
| **Pillar B — Knowledge graph** | Configuration items and typed relationships (who runs on whom, who depends on whom) | No — see contract brief |
| **Pillar C — Rust ReAct agent** | Optional diagnose agent that *reads* stores; does not write sketches | No |

**ObserveOps mapping (pipeline stages):** Pillar A is written on the always-on fabric path:

1. **Collect (E1)** admits telemetry.  
2. **Identity (E2)** binds each sample to a stable configuration-item id.  
3. **Stores (E4)** writes compact **sketch** rows.  
4. **Maintain (E5)** refreshes seasonal baselines over time.  
5. Later, **Detect (E6, door C)** *reads* sketches to decide if a window is abnormal.  
6. Investigation stages after Detect *read* buckets / optional exemplars — they do not rewrite Pillar A’s job.

Pillar A does **not** invent topology edges. It does **not** open tickets. It does **not** name the root cause leaf. It stores **“how this metric looked for this entity in this time window, and what is usual for this calendar slot.”**

---

## 2) Terms used on this page

| Term | Meaning on this page |
|------|----------------------|
| **Configuration item (CI)** | A durable estate noun with a stable id (for example a Service named `checkout-api`). After Identity bind, sketch field `entity_id` is the **same string** as graph `ci_id`. |
| **Sample** | One numeric observation (for example latency = 145.3 ms at a timestamp), already bound to a CI. |
| **Window** | A fixed-length time slice over which we summarize samples (for example five minutes). |
| **Sketch (`sketch.v1`)** | One JSON row that holds three summaries for one key: T-Digest, buckets, seasonal baseline. |
| **T-Digest** | A compressed approximate distribution → answers p50 / p95 / p99 without keeping every raw sample. |
| **Buckets** | A fixed-bin histogram (counts in ranges you defined ahead of time). |
| **Seasonal baseline** | Expected percentiles for a calendar slot (for example every Thursday 09:00 hour), built from **past** windows. |
| **`season_key`** | Label for that calendar slot, e.g. `Thu-09:00` (hour-of-week in a timezone-aware timestamp). |
| **Exemplar** | Optional pointer from a histogram bin to one real `trace_id` for investigation. Not required to Detect. |
| **Hot-bin** | The bucket where abnormal mass sits (often the high-count or high-latency bin after Detect fires). |
| **Vortex** | Hot analytical query surface over sketch (and graph) data — interactive lookups without scanning raw history. |
| **S3** | Cold durable object store — long retention for sketch blobs so history does not evaporate. |
| **E4 destination (Motadata-shaped)** | For production Motadata Pillar A, **both** jobs are required: S3 (cold) **and** Vortex (hot). Labs may temporarily write JSON files; that is a stand-in, not a second product design. |
| **Door C** | Platform Detect that reads Pillar A sketches (digest vs baseline). Not Pillar C (the agent). |

---

## 3) Why this store exists

Raw metric lakes grow forever. Detect and dashboards cannot re-scan weeks of every latency sample on every alert.

Without a **seasonal** expectation, busy Thursday mornings look like outages every week.

So Pillar A keeps:

1. **What happened this window** (T-Digest percentiles + bucket counts).  
2. **What is usual for this hour-of-week** (baseline).  
3. Optionally later: **which request to open** (exemplar on a hot bin).

**Detect rule we teach:** compare this window’s digest p95 to the seasonal baseline’s expected p95. Buckets and exemplars help **after** Detect fires; they are not required to fire.

---

## 4) End-to-end picture

```text
  Agents / APM / collectors
           │
           ▼
   ┌───────────────────┐
   │ E1 Collect        │  admit raw telemetry
   └─────────┬─────────┘
             ▼
   ┌───────────────────┐
   │ E2 Identity       │  stamp tenant + entity_id (= ci_id)
   └─────────┬─────────┘
             │  only identity.status = resolved
             ▼
   ┌───────────────────────────────────────────────┐
   │ Pillar A sketch writer (E4 Stores + E5 later) │
   │  • assign window(s)                           │
   │  • derive season_key                          │
   │  • update T-Digest + buckets (+ optional      │
   │    exemplars)                                 │
   │  • attach baseline for that season_key        │
   │  • emit sketch.v1 row                         │
   └─────────┬─────────────────────┬───────────────┘
             │                     │
             ▼                     ▼
      Cold durable             Hot analytical
      S3 (retain / rebuild)    Vortex (Detect, dashboards)
             │                     │
             └──────────┬──────────┘
                        ▼
              Readers use hot / retrieval (not S3 dumps):
              • dashboards (latest p95)
              • E6 Detect door C (digest vs baseline)
              • E8 / E10 after fire (buckets, exemplars)
              • optional agent tools (get_metric_baseline)
```

**Rooms vs temperature:** “sketch history” is one **content room**. Inside the Motadata-shaped lake it still needs **two temperatures**: S3 (cold retention) and Vortex (hot lookup). Diagnose should use retrieval into a bounded working set — not open S3 as a dump. Visual: [`vortex-s3-interaction.html`](./vortex-s3-interaction.html).

---

## 5) Inputs — what, format, from where

### 5.1 Upstream stages that must already have run

| Stage | What it must have done before Pillar A writes |
|-------|-----------------------------------------------|
| **Collect (E1)** | Admitted a metric (or a span-derived latency) into the shared ingest envelope. |
| **Identity (E2)** | Bound that line to `tenant` + `entity_id`, with `identity.status = resolved`. |

Unbound / unattributed / synthesized identity rows are **not** sketch-writer eligible. Sketch rows must join cleanly to the knowledge graph later.

### 5.2 Logical input: one metric sample

Minimum fields the sketch writer needs (names may appear as nested `identity` on `ingest.v1` lines — see [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md)):

| Field | Example | Required? | Notes |
|-------|---------|-----------|-------|
| `tenant` | `"default"` | Yes | Never cross tenants. |
| `entity_id` | `"checkout-api"` | Yes | Same string as graph `ci_id`. |
| `entity_type` | `"Service"` | Recommended | Display / filter; not the join key. |
| `metric_id` | `"request.latency_ms"` | Yes | Normalized name family. |
| `timestamp` | `2026-08-20T03:32:14Z` | Yes | Timezone-aware. |
| `value` | `145.3` | Yes | Numeric sample. |
| `trace_id` | `"abc123…"` | Optional | Needed only if you want exemplars. |

**Where samples come from in practice:**

| Source class | Typical path into Pillar A |
|--------------|----------------------------|
| Application latency / error-rate gauges | Metric exporters or APM → Collect → Identity → sketch writer |
| Span-derived latency | Trace spans reduced to a numeric sample per request (or per batch), then same path |
| Host CPU / similar | Host metrics with host as the bound entity |

Pillar A does **not** read CMDB catalogs or topology edges as inputs. Those belong to Pillar B / Topology.

### 5.3 Example input lines (teaching)

Three latency samples for the same service in one five-minute window (abbreviated):

```json
{"tenant":"default","entity_id":"checkout-api","metric_id":"request.latency_ms","timestamp":"2026-08-20T03:31:02Z","value":88.0,"identity":{"status":"resolved"}}
{"tenant":"default","entity_id":"checkout-api","metric_id":"request.latency_ms","timestamp":"2026-08-20T03:32:14Z","value":145.3,"trace_id":"tr_slow_01","identity":{"status":"resolved"}}
{"tenant":"default","entity_id":"checkout-api","metric_id":"request.latency_ms","timestamp":"2026-08-20T03:33:40Z","value":410.0,"trace_id":"tr_slow_02","identity":{"status":"resolved"}}
```

### 5.4 Admission decision tree (inputs)

```text
                    Incoming ingest line
                            │
                            ▼
                 Is signal a numeric metric
                 (or span reduced to a number)?
                     │              │
                    no             yes
                     │              │
                     ▼              ▼
                  skip Pillar A   identity.status
                  (not a sketch     == resolved?
                   candidate)      │         │
                                  no        yes
                                   │         │
                                   ▼         ▼
                         skip (non-resolved);     admit into
                         Identity may quarantine  sketch writer
                         raw samples — not A
                                           │
                                           ▼
                                  metric_id in allowed
                                  catalog for this tenant?
                                     │           │
                                    no          yes
                                     │           │
                                     ▼           ▼
                                  reject /     proceed to
                                  map name     windowing
```

---

## 6) Processing — how a sketch row is built

### 6.1 Logical key (what makes one row unique)

One `sketch.v1` row exists for each unique combination of:

`(tenant, entity_id, metric_id, window, season_key, window_start)`

| Part | Example | Why it is in the key |
|------|---------|----------------------|
| `tenant` | `default` | Isolation |
| `entity_id` | `checkout-api` | Join to graph |
| `metric_id` | `request.latency_ms` | Latency ≠ CPU |
| `window` | `5m` | Same samples may also feed a parallel `1m` row |
| `season_key` | `Thu-09:00` | Which baseline family |
| `window_start` | `2026-08-20T03:30:00Z` | Which concrete slice |

**Time-boundary rule:** `window_start` is mandatory. Store **exactly one of** `window` (duration string such as `"5m"`) **or** `window_end` (RFC3339 end timestamp) — not three independent truths. The teaching examples use `window` and omit `window_end`.

### 6.2 Processing flowchart

```text
  Admitted samples for one entity + metric
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ For each configured resolution       │
  │ (start with 1m and 5m)               │
  │   floor timestamp → window_start     │
  │   derive season_key from timestamp   │
  │   (HourOfWeekSeason → e.g. Thu-09:00)│
  └──────────────────┬───────────────────┘
                     ▼
  ┌──────────────────────────────────────┐
  │ Update THIS WINDOW bodies            │
  │   1) T-Digest ← each value           │
  │   2) Buckets  ← increment one bin    │
  │   3) Optional exemplars ← if         │
  │      (value, trace_id) present,      │
  │      attach to that bin              │
  └──────────────────┬───────────────────┘
                     ▼
  ┌──────────────────────────────────────┐
  │ Attach baseline for season_key       │
  │   Look up past windows' percentiles  │
  │   for same tenant+entity+metric+     │
  │   season_key (E5 maintains this)     │
  │   Do NOT build baseline only from    │
  │   this window's raw list             │
  └──────────────────┬───────────────────┘
                     ▼
  ┌──────────────────────────────────────┐
  │ Emit / upsert sketch.v1 for the key  │
  │ Persist cold (S3) + index hot        │
  │ (Vortex). Lab may use files as a     │
  │ stand-in for cold; Motadata-shaped   │
  │ production needs both temperatures.  │
  └──────────────────────────────────────┘
```

### 6.3 Step details

#### Step A — Window assignment

Example: windows `1m` and `5m` both enabled.

- Sample at `03:32:14Z` → `1m` row starting `03:32:00Z` **and** `5m` row starting `03:30:00Z`.  
- Those are **two different sketch rows** (different `window` and/or `window_start`).

#### Step B — `season_key`

PoC helper `HourOfWeekSeason`: timezone-aware timestamp → `strftime('%a')` + floored hour → `"Thu-09:00"`.

The current timestamp only **selects** which baseline family to attach. It does not invent the expected p95 from this window alone.

#### Step C — T-Digest (this window)

- Feed each `value` into the digest for this key.  
- Digests do **not** store `trace_id`.  
- Later readers ask for approximate p50 / p95 / p99.  
- **Mergeable:** digests from adjacent minutes can merge into a longer rollup without replaying raw samples.

#### Step D — Explicit buckets (same samples)

- Choose a versioned policy, e.g. `latency_v1` with bounds  
  `[0, 50, 100, 200, 500, 1000, 2000]`.  
- Each sample increments **exactly one** bin.  
- Never mix two `bucket_schema_version` values under the same logical key.  
- Values outside the top bound still update T-Digest; they may be omitted from configured bins (documented gap — fix by extending bounds or an overflow bin).

#### Step E — Optional exemplars

- Need events shaped like `(latency, trace_id)`.  
- Policy example: keep the first (or a few) `trace_id`s that land in a bin.  
- **Not** “Detect on a 1% metric sample.” Detect still uses digest + baseline.

#### Step F — Seasonal baseline attach

- Input: history of prior windows’ percentiles for the same `season_key`.  
- Output fields on the row: `expected_p50`, `expected_p95`, `expected_p99`, plus a `baseline_version`.  
- E5 Maintain refreshes / accumulates this over days of traffic.

### 6.4 Decision tree — Detect vs investigate (readers of the artifact)

This tree is **not** the sketch writer. It is how **downstream** jobs use the row. Included here so writers know why each body exists.

```text
                 sketch.v1 available for entity+metric+window
                                    │
                                    ▼
                    E6 Detect (door C) needs fire decision?
                                    │
                                   yes
                                    │
                                    ▼
              Read digest p95  vs  baseline expected_p95
                          │                    │
                     abnormal               normal
                          │                    │
                          ▼                    ▼
                    emit Signal            no Detect fire
                    (ERROR/SLOWDOWN…)      (stop or keep watching)
                          │
                          ▼
              Investigate / WorkingSet / UI
                          │
                          ▼
              Read buckets → find hot-bin
                          │
                          ▼
              Exemplars present on that bin?
                     │              │
                    yes            no
                     │              │
                     ▼              ▼
              open trace_id    search traces/logs
              for that request  by entity+time (slower)
```

---

## 7) Artifacts — what is generated

### 7.1 Primary artifact: `sketch.v1` JSON row

**Format:** JSON object conforming to `sketch.v1` (see schema path at top of this page).  
**Cardinality:** one row per logical key (§6.1).  
**Bodies inside one row:**

| Body | Field | Built from | Answers |
|------|-------|------------|---------|
| T-Digest | `tdigest` | This window’s values | Approx p50/p95/p99 |
| Buckets | `buckets` | Same values | Counts per fixed range |
| Baseline | `baseline` | Past same-season windows | Expected p50/p95/p99 |
| Exemplars | optional side field / UI export | `(value, trace_id)` events | Which request in a bin |

### 7.2 Full example row (teaching)

Twenty-three latency samples landed in the five-minute window starting `2026-08-20T03:30:00Z` for `checkout-api`. The writer emits:

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
    "bounds": [0, 50, 100, 200, 500, 1000, 2000],
    "counts": [12, 19, 5, 1, 0, 0]
  },
  "baseline": {
    "baseline_version": "seasonal_v1",
    "expected_p50": 88.0,
    "expected_p95": 170.0,
    "expected_p99": 320.0
  },
  "sample_count": 23,
  "ingest_trace": {
    "writer": "pillar-a-sketch-writer",
    "written_at": "2026-08-20T03:35:05Z"
  }
}
```

**How to read this example:**

- Digest centroids summarize the window (lab-readable JSON; production may use opaque digest bytes under the same logical field).  
- Buckets: 12 samples in `[0,50)`, 19 in `[50,100)`, 5 in `[100,200)`, 1 in `[200,500)`.  
- Baseline says a normal Thursday-09:00 p95 is about **170 ms**.  
- If digest p95 for this window were **400 ms**, Detect would treat it as abnormal for this season.  
- Optional exemplar (not shown as a fourth frozen body in v1): e.g. bin `[200,500)` → `trace_id: "tr_slow_02"`.

### 7.3 Cold durable store (S3) — keep history so Detect tomorrow still works

Pillar A needs a **cold** place that can hold sketch history for days or weeks without becoming a mutable raw-sample swamp. In the Motadata-shaped destination that place is **S3** (object storage). Vortex (next section) does **not** replace S3: Vortex is for fast interactive reads; S3 is for durable retention and rebuild/replay.

**Why cold exists at all.** The sketch writer finishes a five-minute window and emits a `sketch.v1` row. If that row lives only in memory (or only in a short-lived cache), tomorrow’s Detect cannot compare “this Thursday 09:00” to last month’s Thursdays. Builders are useless if results evaporate. So every completed window should land as a durable object.

**Why we do not store forever-growing raw lakes and UPDATE them.** One alternative is to keep every latency sample forever and rewrite old partitions when tags change or history is corrected. That pattern is expensive in object storage (rewrite, re-scan, compaction of huge raw sets). Pillar A instead stores **compact sketch rows** and **appends** a new object per window. You are not choosing “UPDATE is cheaper than insert”; you are choosing “write a small immutable summary for this window” instead of “mutate a giant raw history.”

**Teaching partition layout.** A cold object path might look like:

```text
tenant=default/
  metric_id=request.latency_ms/
    window=5m/
      date=2026-08-20/
        <key-hash>__window_start=2026-08-20T03:30:00Z.json
```

Reading that path: tenant isolation first, then which metric, then which window length, then the calendar day for lifecycle/retention jobs, then one object for one concrete `window_start`. The `<key-hash>` folds the rest of the logical key (`entity_id`, `season_key`, …) so the object name stays short and stable.

**Write rules that matter in practice.**

| Rule | What it means for operators and writers |
|------|-----------------------------------------|
| **Append immutable rows** | When the `03:30`–`03:35` window closes, write (or overwrite by the same name) that window’s sketch object. Do not open yesterday’s raw point file and edit samples. |
| **Idempotent naming** | The same logical key must map to the same object name. If the writer retries after a crash, it replaces or skips that object — it does not create `…_retry2.json` duplicates that Detect might double-count. |
| **Optional rollups later** | A daily job may compact many five-minute sketches into coarser rollups. That is still append/replace of summary objects, not in-place UPDATE of a raw sample table. |

**What diagnose must not do with S3.** Interactive RCA should not open S3 as a dump and scan cold objects ad hoc. Cold is for retention, rebuild, and backfill into the hot index. Live Detect and investigation read through the hot analytical surface (Vortex) or a retrieval layer that fills a bounded WorkingSet.

**Lab note.** Early PoCs may write the same `sketch.v1` JSON to a local folder. That folder is playing the **cold** role. It does not mean production Motadata Pillar A can skip durable storage.

### 7.4 Hot analytical surface (Vortex) — answer Detect and dashboards without raw scans

Pillar A also needs a **hot** place that can answer “what is p95 for checkout-api right now?” and “how does it compare to this season?” in interactive time. In the Motadata-shaped destination that place is **Vortex**. S3 alone is not enough: listing and deserializing cold objects for every Detect tick does not scale for the query patterns below.

**Cold and hot are one lake with two temperatures, not two optional products.** Same sketch rows; different jobs:

| Job | Store | Typical clock |
|-----|-------|---------------|
| Remember history; survive restarts; retain weeks | **S3 (cold)** | Write at window close; read for backfill / rebuild |
| Fast key lookup for Detect, dashboards, trends | **Vortex (hot)** | Continuous read; kept current from writers / loaders |

Visual of that split: [`vortex-s3-interaction.html`](./vortex-s3-interaction.html).

**How a reader finds one sketch.** Vortex (or an equivalent analytical index) should treat this as the primary lookup key:

`(tenant, entity_id, metric_id, window, season_key, window_start)`

That matches the uniqueness key of `sketch.v1`. A Detect or dashboard call is “fetch this key → deserialize digest + baseline,” not “scan all latency samples since Monday.”

**Four query patterns to optimize first** (same order as the merged scope):

1. **Latest p95 for entity + metric** — dashboards and health views. Resolve the newest `window_start` for the entity/metric/window, read digest percentiles.  
2. **Current window vs seasonal baseline** — this **is** Phase-2 **E6 Detect (door C)**. Compare digest p95 to `baseline.expected_p95` for the row’s `season_key`. Buckets are not required for this fire decision.  
3. **Prior N windows for trend** — “was p95 climbing for the last hour?” Same entity/metric, ordered `window_start` values. Digests may also merge across windows for longer rollups.  
4. **Hot-bin + exemplar (optional)** — **after** Detect fires. Read `buckets`, find the hot range, follow an exemplar `trace_id` if present. This is investigation drill-down, not the Detect fire itself.

**What “O(1)” means here.** Cost should **not** grow with how many raw samples ever existed for that service. Fetching one sketch is still work (key lookup + deserialize), but it stays bounded by sketch size, not by years of raw points.

**Who hits Vortex.** Dashboards, E6 Detect door C, WorkingSet / retrieval for E8–E10, and optional agent tools such as `get_metric_baseline()`. They all consume the **same** sketch contract; they do not each invent a private percentile store.

### 7.5 What is *not* an artifact of Pillar A

| Not produced by Pillar A | Where it lives instead |
|--------------------------|------------------------|
| Topology edges (`depends_on`, `runs_on`, …) | Pillar B / Topology (`graph_edge.v1`) |
| Alert / Incident / ticket vertices | Never CI nodes; Detect emits signals; Package emits tickets |
| Root-cause leaf decision | Localize / Identify (E9 / E10) |
| Case correlation (`CORRELATED_WITH`) | Curate (event/case graph), not sketch store |

---

## 8) Who can use the artifacts, and how

| Consumer | What they read | Purpose |
|----------|----------------|---------|
| **Dashboards / operators** | Latest digest percentiles | “What is p95 now?” |
| **E6 Detect (door C)** | Digest p95 + baseline expected p95 | Fire / no-fire for platform Detect |
| **E7 Curate / E8 Scope** | Indirectly (via Signal → case → WorkingSet) | Case packaging; WorkingSet may pull sketch snippets |
| **E10 Identify** | `get_metric_baseline()` style reads | Corroborate class with season-aware numbers |
| **Optional Pillar C agent** | Same retrieval tools, bounded WorkingSet | Must not open S3 as a dump |
| **E5 Maintain** | Prior sketch history | Refresh seasonal baselines |

**Access policy (minimum intent):** diagnose path goes **retrieval → WorkingSet**, with role-based limits. Unrestricted lake dumps are out of scope for interactive RCA.

---

## 9) Worked numeric story (same estate, one incident window)

**Setup**

- Service `checkout-api`, metric `request.latency_ms`, window `5m`.  
- Window start `2026-08-20T03:30:00Z` → `season_key = Thu-09:00`.  
- Baseline for Thu-09:00: expected p95 = **170 ms**.  
- Digest for this window: p95 ≈ **400 ms**.  
- Buckets show a spike in `[200,500)` and `[500,1000)`.  
- Exemplar on `[500,1000)`: `tr_checkout_9f3a`.

**What happens**

1. Sketch writer already wrote the `sketch.v1` row at E4 (and baseline was attached from E5 history).  
2. **E6 Detect** compares 400 vs 170 → abnormal → emits a SLOWDOWN-class signal on `checkout-api`.  
3. Operator / WorkingSet opens buckets → hot-bin high latency → clicks exemplar → opens trace `tr_checkout_9f3a`.  
4. Topology (Pillar B) is used separately to walk `depends_on` / `communicates_with` neighbors — **not** stored inside the sketch row.

**Same p95, different season (why baseline matters)**

- Tuesday 14:00 baseline p95 ~ 200 ms and digest p95 = 180 ms → **normal**.  
- Sunday 02:00 baseline p95 ~ 40 ms and digest p95 = 180 ms → **abnormal**.  
Same digest number; different `season_key`.

---

## 10) Simplifying lines that used to confuse readers

| Dense line (older docs) | Plain meaning |
|-------------------------|---------------|
| “Builders are useless if results evaporate” | Persist sketch rows in **cold** storage (S3); memory-only digests cannot feed Detect tomorrow. |
| “Historical UPDATE of raw sample lakes is expensive” | Do **not** keep forever-growing raw points and rewrite old partitions. **Append** compact sketch objects per window instead. This is not “UPDATE beats insert.” |
| “compare current window vs seasonal baseline (**Detect**)” | Exactly **Phase-2 E6 Detect (door C)** on the **hot** index — not Curate, not hot-bin drill-down. |
| “hot-bin + exemplar for drill-down” | **After** Detect: which latency range + which `trace_id`. |
| “when S3 / when Vortex is part of E4” | Misleading hedge. Motadata-shaped Pillar A needs **both** cold (S3) and hot (Vortex). Labs may fake cold with files; that does not drop the hot-query job. |

---

## 11) Non-goals and common mistakes

| Mistake | Correction |
|---------|------------|
| Treating exemplars as required for Detect | Detect = digest + baseline only |
| Treating buckets as a second Detect algorithm by default | Primary door C is quantile-vs-season; bin-vs-season is a different design |
| Putting `src_ci_id` / `relation` on sketch rows | Edges belong on the knowledge graph |
| Building baseline from this window’s raw list alone | Baseline comes from **past** same-`season_key` windows |
| Equating Door C with Pillar C | Door C = Detect entry that reads sketches; Pillar C = optional ReAct agent |
| Assuming Vortex alone or S3 alone is enough | Motadata-shaped Pillar A needs **both**: cold retention (S3) and hot lookup (Vortex) |
| Treating lab JSON files as “no cold store needed” | Files are a stand-in for the cold role in early PoCs |

---

## 12) Implementation checklist (Pillar A owner)

1. Admit only resolved-identity numeric samples.  
2. Normalize `metric_id`; publish `bucket_schema_version` before writers start.  
3. Write `sketch.v1` with T-Digest + buckets + baseline under the logical key.  
4. Enforce time-boundary rule (`window_start` + exactly one of `window` / `window_end`).  
5. Persist sketches to **cold** (S3 append) and keep them queryable on **hot** (Vortex index). Lab files may stand in for cold only.  
6. Optimize the four priority queries in §7.4 on the hot surface.  
7. Keep exemplars optional; document enablement per high-traffic service.  
8. Hand Detect a stable read API: current digest percentiles + baseline for `season_key`.

---

## 13) Where to go next

| If you need… | Open |
|--------------|------|
| Locked edge/node contract | [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) |
| Fabric Q&A | [`GRAPH_QNA.md`](../GRAPH_QNA.md) |
| Shorter What/Why/How kickoff Part C | [`MOTADATA_3PILLARS_MERGED_SCOPE.md`](../MOTADATA_3PILLARS_MERGED_SCOPE.md) |
| Algorithm walk with season helper | [`end-to-end-algorithm-walkthrough.md`](./end-to-end-algorithm-walkthrough.md) |
| Picture of digest / buckets / baseline / exemplars | [`sketch-exemplars-visual.html`](./sketch-exemplars-visual.html) |
| PoC code | [`pillar-ab-implementation/pillar-a/poc/`](../../pillar-ab-implementation/pillar-a/poc/) |
| Stores LLD draft | [`LLD-E4-Stores.md`](../observeops/LLD-E4-Stores.md) |

---

*This page is the elaborative Pillar A deep dive. Prefer updating this file for teaching detail; keep the contract brief as the freeze source of truth for field locks.*
