# Dynatrace RCA Lab — Reference Guide

A minimal three-service system for observing how Dynatrace builds topology, detects faults, and packages root-cause analysis (RCA).

---

## 1. Purpose

This lab is not an application demo. Its purpose is to generate controlled telemetry so Dynatrace’s RCA behavior can be observed as a black box.

For each injected fault, record:

| Fault | First Signal | Problem Card | Root Cause | Service Flow | Trace | Logs | Metrics |
| ----- | ------------ | ------------ | ---------- | ------------ | ----- | ---- | ------- |

After enough controlled experiments, Dynatrace’s pipeline can be compared with systems such as Panorama, Murphy, and Nezha.

---

## 2. Lab Topology

```text
            curl
              │
              ▼
      frontend:8080
              │
              ▼
       product:8081
              │
              ▼
     inventory:8082
```

Every request traverses all three services.

Workspace layout:

```text
dynatrace-rca-lab/
├── docker-compose.yml
├── faults/                  # live fault-injection flags
├── scripts/
│   ├── fault.sh
│   ├── enable_python_feature.sh
│   └── verify_telemetry.sh
├── frontend/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── product/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
└── inventory/
    ├── app.py
    ├── requirements.txt
    └── Dockerfile
```

Host access:

```bash
curl http://localhost:18080
```

Expected healthy response:

```json
{
  "product": "MacBook",
  "inventory": {
    "stock": 100
  }
}
```

> Note: host port **18080** is used because **8080** was already occupied on this machine. Inside Docker the services still listen on 8080 / 8081 / 8082.

---

## 3. Mental Model

Dynatrace is best understood as:

```text
Always-on telemetry fabric
        ↓
   Event generators
        ↓
Davis problem correlator
(ranking + packaging over pre-indexed data)
```

It is **not**:

```text
Alert fires → RCA service wakes up → RCA pulls raw MELT from scratch
```

RCA is mainly a **ranking and packaging layer** over data that preprocessing already made queryable by entity ID and time.

### 3.1 Implication for Lean / Federated RCA

Your reading is correct: what Lean or federated RCA typically implement is only the **last slice** of this puzzle.

| Work | Where it lives in Dynatrace | Relative weight |
| ---- | --------------------------- | --------------- |
| Capture, label, topology, metrics, events, indexing | Preprocessing fabric (always on) | **Major** |
| Detector / event generation | Continuous, async | **Major** |
| Correlate + rank root cause + package Problem | Davis | **Small but visible** |

That fabric behaves like a **deeply coherent web**, not a synchronous request/response pipeline:

- Most stages are **continuous and async**
- Hand-offs are via **indexes and streams** (entity graph, time series, events), not blocking RPC “please give me MELT now”
- When Davis opens a Problem, much of the hard work is already done; Davis mostly **selects, merges, ranks, and packages**

So comparing Lean/federated “RCA engines” to Dynatrace Problems alone understates Dynatrace: you are comparing your **correlator** to their **correlator**, while their advantage is often the **pre-curated substrate** underneath.

---

### 3.2 Platform building blocks: OneAgent, Smartscape, Grail, Davis

> Note: “OneEvent” is not a Dynatrace product name. Below, **OneAgent** is the capture agent. **Events** are the normalized detector outputs Davis consumes. **Grail** is the unified data lake / query plane.

#### What each piece owns

| Building block | Role in the ecosystem | Maps to our stages |
| -------------- | --------------------- | ------------------ |
| **OneAgent** | Edge capture + enrichment + local aggregation/export | Capture (0), contributes to labeling inputs, local metric/span emission |
| **Smartscape** | Live entity + relationship graph (vertical + horizontal) | Topology materialization (2); the index Davis expands |
| **Grail** | Unified storage + query (DQL) for traces, logs, metrics, events, entities | Indexing for retrieval (5); where evidence is queried/joined by entity + time |
| **Events** (platform event model) | Normalized “something changed” records from detectors | Eventization (4); the ignition Davis hears |
| **Davis** | Correlation, root-cause ranking, Problem packaging, impact | The thin RCA / decision layer on top |

#### Coherent web (block diagram)

```text
                         ┌──────────────────────────────────────┐
                         │           YOUR WORKLOADS             │
                         │   frontend → product → inventory     │
                         └──────────────────┬───────────────────┘
                                            │
                                            │ inject / observe
                                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              ONEAGENT (edge)                             │
│  Capture spans/paths · label candidate failures · process/host metrics   │
│  Enrich with container/process/service identity                          │
│                                                                          │
│  Style: continuous, local, mostly non-blocking export                    │
└───────────────┬───────────────────────────┬──────────────────────────────┘
                │                           │
                │ topology cues             │ telemetry streams
                │ + call edges              │ (spans, metrics, logs…)
                ▼                           ▼
┌──────────────────────────────┐   ┌───────────────────────────────────────┐
│         SMARTSCAPE           │   │              GRAIL                    │
│  Live property graph         │   │  Unified lake + DQL query plane       │
│                              │◄──┤  metrics · traces · logs · events     │
│  HOST / PG / container        │   │  entities (joined by entityId+time)   │
│  SERVICE call edges          │──►│                                       │
│                              │   │  Style: write-continuous, read-on-use │
│  Style: always updating      │   └──────────────────┬────────────────────┘
└───────────────┬──────────────┘                      │
                │                                     │
                │ neighborhood                        │ series / exemplars
                │                                     │
                ▼                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     DETECTORS / EVENT GENERATORS                         │
│  failure-rate · response-time · process restart · availability · …       │
│                                                                          │
│  Emit normalized Events (e.g. SERVICE_ERROR_RATE_INCREASED)              │
│  Style: async threshold/baseline evaluation over indexed series          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │ Events (+ change-points)
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              DAVIS                                       │
│  Merge by time + topology · score rootCauseRelevant · open Problem       │
│  Package evidence · estimate impact · drive UI Problem card              │
│                                                                          │
│  Style: correlator / ranker / packager — NOT the main data curator       │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
                            Problem card
                         (e.g. P-26076)
                    rootCause = inventory
```

#### Same story as a pipeline ↔ product map

```text
Capture            ──►  OneAgent
Labeling           ──►  OneAgent + failure rules (platform config)
Topology           ──►  Smartscape
Metricization      ──►  OneAgent rollups → Grail metrics
Eventization       ──►  Detectors → Events (often stored/queryable via Grail)
Indexing/Retrieval ──►  Grail (+ Smartscape as graph index)
RCA / Problem      ──►  Davis
```

#### Sync vs async (why it feels non-blocking)

```text
OneAgent ──async──► Grail / Smartscape updates     (continuous)
Detectors ─async──► Events                         (continuous)
Davis ────react──► Problem open/update             (event-driven)

Rare path: UI drill-down ──query──► Grail DQL      (on-demand exemplars)
```

There is little “synchronous blocking RCA request” in the critical path.  
The expensive coherence work is **already being maintained** by OneAgent + Smartscape + Grail + detectors. Davis rides that wave.

#### How this reframes Lean / Federated comparison

```text
┌─────────────────────────────────────────────────────────────┐
│ Dynatrace substrate (large)                                 │
│   OneAgent + Smartscape + Grail + Detectors/Events          │
└─────────────────────────────┬───────────────────────────────┘
                              │ curated entities, series, events
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Davis (small, visible)                                      │
│   correlate · rank · package Problem                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Lean / Federated RCA (comparable slice)                     │
│   usually assumes MELT (+ maybe topology) already available │
│   then correlates / ranks / explains                        │
└─────────────────────────────────────────────────────────────┘
```

Fair comparison questions become:

1. What substrate does Lean/Federated **assume** vs **build**?
2. Is topology first-class (Smartscape-like) or reconstructed per incident?
3. Are events pre-materialized, or does RCA scan raw metrics/logs at incident time?
4. Is retrieval entity-joined (Grail-like), or ad-hoc per tool?

---

## 4. Preprocessing Reference

Preprocessing is everything that happens **before** a Problem exists.

### Stage 0 — Capture / Instrumentation (edge)

**Subsystem:** OneAgent code modules  
(in this lab: Python + Flask/WSGI + requests/urllib3)

**Does:**
- Injects into the process (`liboneagentpython.so`, SubPath protocol)
- Intercepts inbound HTTP and outbound HTTP
- Emits spans/paths, resource attributes, and technology fingerprints

**Main outputs:**
- Span / PurePath nodes (timing, status, callee)
- Resource attributes such as:
  - `service.name`
  - container / process group / host identity
  - release tags (`DT_RELEASE_PRODUCT`, `DT_RELEASE_STAGE`)

**Main algorithms:**
- Binary / library hooking
- Framework sensors
- Trace-context propagation across hops
- Sampling and path-limit controls

---

### Stage 1 — Failure labeling (“what counts as a failed call?”)

**Subsystem:** Failure detection rulesets  
(`builtin:failure-detection-rulesets`)

In this environment the built-in default includes:
- HTTP status codes `500-599` count as failures
- Exceptions count as failures

**Does:**
- Converts raw HTTP status / exception into a boolean **failed call**
- This is preprocessing, not alerting

**Why it matters:**  
Later detectors and Davis do not start from raw “HTTP 500”. They start from already-labeled failed requests rolled into failure-rate series.

---

### Stage 2 — Topology materialization (Smartscape)

**Subsystem:** Entity / topology model

**Vertical links (containment):**

```text
HOST
  → PROCESS_GROUP
    → PROCESS_GROUP_INSTANCE
      → CONTAINER
        → SERVICE_INSTANCE
          → SERVICE
```

**Horizontal links (causality fabric):**

```text
frontend.calls → product
product.calls → inventory
```

**Main data structure:**
- Typed property graph: entities + relationship edges
- Stable IDs such as `SERVICE-…`, `PROCESS_GROUP_INSTANCE-…`

**Main algorithms:**
- Process group detection (executable, script, ports, `DT_CLUSTER_ID`, release metadata)
- Service detection from web entrypoints
- Call-edge extraction from distributed traces

This graph is the **index** later used to decide what neighborhood of data belongs to a problem.

---

### Stage 3 — Metricization / rollups

**Subsystem:** Metric pipeline

From labeled requests and process activity, Dynatrace builds entity-keyed time series such as:
- failure rate %
- request count / load
- response time percentiles
- process availability / restarts

**Main structures:**
- Time series conceptually keyed by `(entityId, metricKey, timeBucket) → value`
- Sliding windows / baselines for later change detection

**Main algorithms:**
- Fixed-interval aggregation (commonly 1-minute buckets)
- Baseline estimation (for auto mode)
- Before/after change-point comparison (for transactional evidence)

Observed example on inventory:

```text
failure rate before change ≈ 15.56%
failure rate after change  ≈ 100%
```

---

### Stage 4 — Eventization

**Subsystem:** Anomaly / lifecycle event generators

Examples observed or relevant here:
- `SERVICE_ERROR_RATE_INCREASED`
- `PROCESS_RESTART`

Important distinction:

```text
Event  ≠  Problem
Event  =  local detector output
Problem = correlated package of events + evidence
```

**Algorithms involved:**
- Threshold comparison (fixed) or baseline comparison (auto)
- Over-alerting protection (minimum RPM, minutes abnormal)
- Change-point style before/after comparison

---

### Stage 5 — Indexing for retrieval

Preprocessing’s real product is that everything is already joinable by **entity ID + time**.

| Conceptual store | Holds | Used later for |
|---|---|---|
| Topology graph | entities + edges | neighborhood expansion |
| Metrics store | entity-keyed time series | transactional evidence |
| Event store | anomaly / lifecycle events | triggers + evidence |
| Trace store | PurePaths / spans | service flow / exemplars |
| Log store | logs + enrichment IDs | optional corroboration |

Conceptual join key:

```text
(entityId, timeRange) → metrics | events | traces | logs
```

---

## 5. How RCA Learns There Is a Problem

Best mental model:

```text
Event generators ──► Davis problem correlator
                         │
                         ├─ merge by time + topology
                         ├─ score rootCauseRelevant
                         └─ open/update Problem (P-26076)
```

RCA does **not** primarily wait for an external ticket or pager alert.  
It consumes **internal Events** (and metric change-points) already produced inside Dynatrace.

For this lab fault, the ignition set was:

1. three nearby `SERVICE_ERROR_RATE_INCREASED` events
2. transactional failure-rate discontinuity on inventory
3. nearby `PROCESS_RESTART` on inventory process

---

### Does RCA “request MELT”?

More accurate model:

```text
Detectors already wrote Events + metric evidence.
Davis selects a subgraph and attaches precomputed evidence.
UI may lazily fetch exemplar traces/logs when you drill in.
```

| Channel | Role in P-26076 |
|---|---|
| **Events** | Direct triggers and packaged evidence |
| **Metrics** | Transactional before/after values |
| **Topology** | Merge neighborhood + root-cause ranking |
| **Traces** | Built the call graph earlier; exemplars for drill-down |
| **Logs** | Optional corroboration; not required for this problem |

So RCA does not usually start from raw MELT pull.  
It starts from **already entity-joined Events + Metrics + Topology**, then may fetch exemplar traces/logs for explanation.

---

### Information selection rule (practical)

Inferred operational pattern:

```text
1. Seed = triggering event entity(ies)
2. Expand neighborhood on Smartscape
   - callers / callees
   - process / container / host
3. Collect candidate evidence in a time halo
4. Score rootCauseRelevant
5. Package Problem:
   - affected / impacted entities
   - rootCauseEntity
   - evidence list
```

### Time windows (nested, not one window)

| Window | Role | Observed / typical |
|---|---|---|
| Metric evaluation window | detector (often ~5 min for fixed threshold) | opened the events |
| Change-point context | transactional before/after | ~15.56% → 100% |
| Correlation horizon | merge nearby events | same timestamp bucket for all 3 failure events |
| Evidence halo | include nearby restart/deploy | process restart a few minutes earlier |
| UI analysis range | what you inspect when opening the problem | problem start ± lookback |

RCA usually does not need you to pass a window. The triggering event timestamp anchors expansion.

### Format RCA consumes

Not raw MELT blobs first. Normalized evidence records roughly like:

```text
Evidence {
  evidenceType: EVENT | TRANSACTIONAL | ...
  eventType?: SERVICE_ERROR_RATE_INCREASED | PROCESS_RESTART | ...
  entity: { id, type, name }
  groupingEntity?: { id, type, name }
  startTime, endTime
  rootCauseRelevant: bool
  // transactional extras
  valueBeforeChangePoint?, valueAfterChangePoint?, unit?
}
```

Raw traces/logs remain in their stores and are fetched as exemplars when drilling into Service flow or logs.

---

## Practical Lab Controls

### Live fault flags

```bash
./scripts/fault.sh inventory fail true
./scripts/fault.sh inventory fail false
./scripts/fault.sh inventory latency 2
```

### Baseline traffic

```bash
while true; do curl -s http://localhost:18080 >/dev/null; sleep 0.2; done
```

### Verify local OneAgent/Python status

```bash
./scripts/verify_telemetry.sh
```

### Research log template

| Fault | First Signal | Problem Card | Root Cause | Service Flow | Trace | Logs | Metrics |
| ----- | ------------ | ------------ | ---------- | ------------ | ----- | ---- | ------- |
| inventory FAIL=true | SERVICE_ERROR_RATE_INCREASED on inventory | P-26076 | inventory | frontend→product→inventory | … | … | failure rate 15.6%→100% |

---

## Practical takeaway

Treat Dynatrace as a **black-box RCA engine** fed by a **pre-indexed telemetry fabric**.

For every controlled fault, record:

| Fault | First Signal | Problem Card | Root Cause | Service Flow | Trace | Logs | Metrics |
| ----- | ------------ | ------------ | ---------- | ------------ | ----- | ---- | ------- |

After enough controlled runs, the internal pipeline becomes visible through behavior: what appears first, what gets merged, what gets ranked as root cause, and which channels were necessary versus optional.

---

## 6. Preprocessing Internals (Detailed)

This section answers: what happens before a Problem exists, and how Davis later “knows” what to use.

### 6.1 End-to-end flow

```text
Capture → Label failures → Build topology → Roll up metrics
        → Emit Events → Index by (entityId, time)
                ↓
        Davis correlator
                ↓
     Problem (P-26076) = ranked package of evidence
```

### 6.2 Preprocessing stages, subsystems, algorithms, structures

#### Stage 0 — Capture

| | |
|---|---|
| **Subsystem** | OneAgent code modules (Python, Flask/WSGI, requests/urllib3) |
| **Does** | Hook process; intercept inbound/outbound HTTP; emit spans + resource attrs |
| **Structures** | Span/PurePath nodes; resource attribute maps |
| **Algorithms** | Library hooking; framework sensors; W3C/trace-context propagation; sampling / path limits |

Lab signal: SubPath resource attributes written for `service.name`, container, process group, host, release tags.

---

#### Stage 1 — Failure labeling

| | |
|---|---|
| **Subsystem** | Failure detection rulesets (`builtin:failure-detection-rulesets`) |
| **Does** | Maps status/exception → boolean **failed call** |
| **Structures** | Per-request failure flag |
| **Algorithms** | Rule match on status ranges (`500-599`) and exception classes |

This is preprocessing, not alerting. Later math is mostly:

```text
failure_rate = failure_count / request_count
```

---

#### Stage 2 — Topology materialization (Smartscape)

| | |
|---|---|
| **Subsystem** | Entity / topology model |
| **Structures** | Typed property graph: entities + edges + stable IDs |
| **Algorithms** | Process-group detection; service detection; call-edge extraction from traces |

Vertical (containment):

```text
HOST → PROCESS_GROUP → PROCESS_GROUP_INSTANCE → CONTAINER → SERVICE_INSTANCE → SERVICE
```

Horizontal (causality fabric):

```text
frontend.calls → product
product.calls → inventory
```

This graph is the **index** RCA later expands.

---

#### Stage 3 — Metricization

| | |
|---|---|
| **Subsystem** | Metric pipeline |
| **Structures** | Entity-keyed time series: `(entityId, metricKey, timeBucket) → value` |
| **Algorithms** | Bucket aggregation; baseline estimation; change-point before/after compare |

Observed on inventory:

```text
failure rate before ≈ 15.56%
failure rate after  ≈ 100%
```

---

#### Stage 4 — Eventization

| | |
|---|---|
| **Subsystem** | Detectors (service failure-rate, process restart, …) |
| **Structures** | Event records with entityId, type, time, thresholds, DQL exemplar |
| **Algorithms** | Threshold/baseline breach; over-alerting protection; change-point compare |

Observed event types:

```text
SERVICE_ERROR_RATE_INCREASED
PROCESS_RESTART
```

Remember:

```text
Event  ≠ Problem
Event  = local detector output
Problem = correlated package of events + evidence
```

---

#### Stage 5 — Indexing

| Store | Holds | Later used for |
|---|---|---|
| Topology graph | entities + edges | neighborhood expansion |
| Metrics store | time series | transactional evidence |
| Event store | anomaly/lifecycle events | triggers + evidence |
| Trace store | PurePaths/spans | service flow / exemplars |
| Log store | logs + entity enrichment | optional corroboration |

Join key:

```text
(entityId, timeRange) → metrics | events | traces | logs
```

---

## 7. How RCA Learns About a Problem and Selects MELT

### 7.1 How RCA “hears” that something is wrong

Best model:

```text
Detectors emit Events ──► Davis correlator
                              │
                              ├─ merge by time + topology
                              ├─ score rootCauseRelevant
                              └─ open/update Problem (P-26076)
```

RCA does **not** primarily wait for an external ticket.  
It consumes **internal Events** already produced by Dynatrace detectors.

For this lab fault, ignition was:

1. three nearby `SERVICE_ERROR_RATE_INCREASED` events  
2. transactional failure-rate discontinuity on inventory  
3. nearby `PROCESS_RESTART` on inventory process  

---

### 7.2 Does RCA “request MELT”?

More accurate:

```text
Detectors already wrote Events + metric evidence.
Davis selects a subgraph and attaches precomputed evidence.
UI may lazily fetch exemplar traces/logs when you drill in.
```

| Channel | Role in P-26076 |
|---|---|
| **Events** | Direct triggers + packaged evidence |
| **Metrics** | Transactional before/after values |
| **Topology** | Merge neighborhood + root-cause rank |
| **Traces** | Built call graph earlier; exemplars for drill-down |
| **Logs** | Optional; not required for this problem |

---

### 7.3 Information selection rule

Inferred operational pattern:

```text
1. Seed = triggering event entity(ies)
2. Expand neighborhood on Smartscape
   - callers / callees
   - process / container / host
3. Collect candidate evidence in a time halo
4. Score rootCauseRelevant
5. Package Problem:
   - affected / impacted entities
   - rootCauseEntity
   - evidence list
```

### 7.4 Time windows (nested)

| Window | Role | In P-26076 |
|---|---|---|
| Metric eval window | detector (often ~5 min fixed) | opened events |
| Change-point context | transactional before/after | ~15.56% → 100% |
| Correlation horizon | merge nearby events | same timestamp bucket for all 3 failure events |
| Evidence halo | include nearby restart/deploy | process restart a few minutes earlier |
| UI analysis range | what you inspect when opening the problem | problem start ± lookback |

RCA usually does not need you to pass a window. The triggering event timestamp anchors expansion.

### 7.5 Format RCA consumes

Normalized evidence records, not raw MELT blobs first:

```text
Evidence {
  evidenceType: EVENT | TRANSACTIONAL | ...
  eventType?: SERVICE_ERROR_RATE_INCREASED | PROCESS_RESTART | ...
  entity: { id, type, name }
  groupingEntity?: { id, type, name }
  startTime, endTime
  rootCauseRelevant: bool
  valueBeforeChangePoint?, valueAfterChangePoint?, unit?
}
```

Raw traces/logs remain in stores and are fetched as exemplars when drilling into Service flow or logs.

---

## Observed experiment: inventory FAIL=true

| Fault | First Signal | Problem Card | Root Cause | Service Flow | Metrics |
| ----- | ------------ | ------------ | ---------- | ------------ | ------- |
| inventory FAIL=true | SERVICE_ERROR_RATE_INCREASED on inventory | P-26076 | inventory | frontend→product→inventory | failure rate ~15.6%→100% |

---

## Code-level RCA enrichment (entity + exact fault)

### Real code defect (preferred demo)

Not a fault-flag raise. Inventory’s `WAREHOUSE_SKU_INDEX` is missing `MACBOOK-PRO-14`, so a normal dict lookup raises **`KeyError`** in `lookup_stock_in_warehouse` (`inventory/app.py`).

```bash
# already the live buggy build after compose rebuild — or:
./scripts/break_inventory_code.sh
# sustain load ~10–12 min, then watch Dynatrace Problems / traces / Exceptions

# heal (real fix + rebuild):
./scripts/heal_inventory_code.sh
```

**What to search:** `KeyError: 'MACBOOK-PRO-14'` · `lookup_stock_in_warehouse` · stack frame `app.py` line with `WAREHOUSE_SKU_INDEX[sku]`.

### Legacy flag-based simulation (optional)

`./scripts/fault.sh inventory fail true` previously staged a custom exception — use only if you need a reversible toggle without rebuild. Prefer the KeyError path above for honest code-level RCA.

**Token scopes (for full depth):**

| Path | Scopes |
| ---- | ------ |
| OTLP traces/metrics/logs | `openTelemetryTrace.ingest`, `metrics.ingest`, `logs.ingest` |
| Deploy/config events | `events.ingest` |
| OneAgent-only | Python injection enabled; OTLP 403 is OK if agent ships spans/logs |

If `events.ingest` is missing, run with `./scripts/run_code_level_rca.sh --no-deploy` (code exception still works).

### Run the enriched fault

```bash
./scripts/run_code_level_rca.sh              # deploy event + fail + ~12 min load
./scripts/run_code_level_rca.sh --no-deploy  # exception only
./scripts/run_code_level_rca.sh --minutes 10
```

Or step by step:

```bash
./scripts/ingest_change_event.sh deployment
sleep 45
./scripts/fault.sh inventory fail true
# sustain: while true; do ./scripts/load.sh 25; done
```

### Expected Problem story

1. **Where:** `rootCauseEntity ≈ inventory` (unchanged Localize/Package)
2. **What in code:** failing function `lookup_stock_in_warehouse` / `InventoryStockLookupError` / `WAREHOUSE_SKU_INDEX_CORRUPT`
3. **Why now (if deploy ingested):** related deployment event on inventory just before onset

Clear:

```bash
./scripts/fault.sh inventory fail false
```

---

## Practical takeaway

Treat Dynatrace as a **black-box RCA engine** fed by a **pre-indexed telemetry fabric**.

For every controlled fault, record:

| Fault | First Signal | Problem Card | Root Cause | Service Flow | Trace | Logs | Metrics |
| ----- | ------------ | ------------ | ---------- | ------------ | ----- | ---- | ------- |

After enough controlled runs, the internal pipeline becomes visible through behavior: what appears first, what gets merged, what gets ranked as root cause, and which channels were necessary versus optional.

