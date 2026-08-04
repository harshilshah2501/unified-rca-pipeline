# Comparable pipeline — Dynatrace vs Datadog

**Goal (shared):** From continuous telemetry on a service chain, surface *what broke*, *where*, and *what an operator should look at* — without re-collecting the estate from scratch on every alert.

### What we ran (and why it is “identical”)

We needed one fault both vendors could see, so differences would come from **pipeline behavior**, not from different apps or different bugs.

Both labs run the same three-service checkout chain: **frontend** calls **product**, which calls **inventory**. Traffic hits the edge checkout URL; when healthy, inventory returns stock and the request succeeds. For the fault we only break the **leaf** — inventory’s stock API starts returning **5xx** — then keep driving checkout traffic for many minutes so detectors and maps have time to react, then clear the fault and confirm recovery.

“Identical” means **same topology, same leaf-failure class, same sustain-then-clear shape**. It does **not** mean bit-identical HTTP codes: Dynatrace’s Flask path surfaced inventory **500** (and upstream 500s); Datadog’s path surfaced inventory **503** (and upstream 502s). Same causal story — inventory is sick, callers fail because of it — different status codes from each stack.

| Lab | Host URL | Capture | Env / stage tag |
|-----|----------|---------|-----------------|
| Dynatrace | `http://127.0.0.1:19080/` | OneAgent Python (+ OTLP) | `applicationEnvironment=rca-lab` |
| Datadog | `http://127.0.0.1:18080/api/checkout` | `ddtrace` → Agent `:8126` | `env:rca-lab` |

| | Dynatrace lab | Datadog lab |
|--|---------------|-------------|
| Inventory leaf | HTTP **500** | HTTP **503** |
| Upstream symptom | FE/product **500** | product/frontend **502** |
| Packaged RCA | **Problem P-26084**, `rootCauseEntity=inventory` | **No** Incident / Watchdog / alerted monitor |
| Detect *evidence* | Failure-rate Events + Problem | Strong APM: ~100% error, 1317× inventory 503 (~12 min / ~1297 checkouts) |

### How to read honesty labels

Claims in this doc are tagged so you can tell **what we saw** from **what we are inferring**:

| Label | Means | Use it when… |
|-------|--------|----------------|
| **Observed (lab)** | Seen in our controlled `dynatrace-rca-lab` / `datadog-rca-lab` runs (API, UI, or MCP against *this* traffic) | Default for stage outcomes, counts, Problem/Incident presence, span status codes |
| **Public framing** | How the vendor describes the product in docs/marketing — useful vocabulary, not a lab proof | Naming building blocks (Grail, Watchdog, Service Map) when we did not open the black box |
| **Inferred** | Reasonable model that fits observations + public framing, but is **not** an internal vendor spec | e.g. “Davis is a thin packager,” exact ranking math, how map and lake stay aligned |

Unless a sentence is marked otherwise, treat it as **Observed (lab)**. Where we generalize beyond this single cascade, we say so.

Labs: [`dynatrace-rca-lab`](../dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md) · [`datadog-rca-lab`](../datadog-rca-lab/DATADOG_RCA_REFERENCE.md)  
Browser: [`comparable-pipeline-dt-dd.html`](./comparable-pipeline-dt-dd.html) · [`:8765`](http://127.0.0.1:8765/comparable-pipeline-dt-dd.html) · [docs hub](http://127.0.0.1:8765/docs.html)

---

## 0. Philosophy — same destination, different path

Both platforms are trying to answer:

> *Something is wrong in checkout — what is the root, and what evidence proves it?*

They do **not** disagree on that destination. They disagree on **who does the last mile** and **what object you get**.

| | Dynatrace path | Datadog path |
|--|----------------|--------------|
| **Center of gravity** | Always-on **entity fabric** (map ∥ lake) + thin packager | Always-on **tagged multimodal evidence** (esp. APM) |
| **Join key** | Stable **`entityId`** | **`service` + `env` (+ host) tags** |
| **When fault happens** | Detectors → Events → **Davis** merges, walks map, ranks, **packages Problem** | Spans/metrics light up immediately; **operator** (or Bits AI) scopes traces/map |
| **Promise to the operator** | “Here is a **Problem** with **`rootCauseEntity`**” | “Here is the **full flamegraph + map** — go find the deepest error” |
| **Lab outcome** | Packaged RC = **inventory** | Evidence clear; **packaged RC absent** |

### Simplified illustration

```text
                    SAME DESTINATION
         “Name the root of the inventory 5xx cascade”
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
     DYNATRACE PATH                  DATADOG PATH
     ──────────────                  ─────────────
     Pre-join the world              Keep the evidence rich
     (entityId + Smartscape          (tags + APM/Metrics/Logs)
      ∥ Grail)                       map ≈ view on traces

     Detect → Event objects          Detect signal = spans / rates
     (case opens in platform)        (case often opens in UI)

     Davis thin diagnose             Operator / Bits diagnose
     → Problem card                  → optional Incident (lab: none)
       rootCauseEntity=inventory       deepest span = inventory
```

**One sentence:** Dynatrace **pre-computes a joinable world and packages a verdict**; Datadog **maximizes inspectable evidence and leaves packaging optional**.

---

## 1. Solidified pipeline (our three phases → product blocks)

We keep **our** stage names as a fair compare lens. Product names below are what each vendor actually runs.

### Phase 1 — Always-on fabric

| Our stage | Dynatrace (confirmed) | Datadog (confirmed) | Fit |
|-----------|----------------------|---------------------|-----|
| **Collect** | OneAgent / OTLP | Agent + ddtrace | Strong both |
| **Normalize** | Enrichment + failure labeling + entity prep | Unified Service Tags + span status/HTTP codes | Strong both (different ID model) |
| **Topology bind** | Smartscape + bind LUT → **`entityId`** | Catalog + APM Service Map / `peer.hostname` | Both reconstruct FE→PRD→INV; DT = typed entity graph, DD = tag/trace-derived |
| **Fan-out** | **Smartscape upserts ∥ Grail evidence** (not twin dumps; not Lean/Fed) | Write **Metrics ∥ APM ∥ Logs**; map mostly **derived from APM** | Same *idea* (continuous write); different *geometry* |
| **Maintain** | Grail lifecycle + Smartscape freshness | Retention / indexing / discovery | Strong both |

### Phase 2 — Case opens

| Our stage | Dynatrace (confirmed) | Datadog (confirmed) | Gaps |
|-----------|----------------------|---------------------|------|
| **Detect** | Failure-rate **Events** (e.g. inventory + upstream) | **APM error spans/rates** always visible; Monitors + Watchdog as **doors** | DD: auto High Error Rate often **OK** (`min(last_15m)`); Watchdog **0** on this fault |
| **Curate** | Davis merges nearby Events toward one Problem narrative | Monitor/story grouping; optional Incident seed | **DD gap:** no merge to one seed — FE/PRD/INV all `error` |
| **Tailor** | Smartscape neighborhood + Grail DQL time cut | Operator (or Bits) scopes services + time + related | **DD:** human-cut; not a first-class auto neighborhood expand |

### Phase 3 — Diagnose

| Our stage | Dynatrace (confirmed) | Datadog (confirmed) | Gaps |
|-----------|----------------------|---------------------|------|
| **Localize** | Smartscape walk from seed → candidate entities | Trace / Service Map; deepest error span | DD: **operator Localize**, not `rootCauseEntity` |
| **Identify** | Rank `rootCauseRelevant` evidence (inferred scoring) | Status codes, resources, related metrics/logs on the trace | Both correlational at packaging layer |
| **Verify / Package** | **Problem** card (`rootCauseEntity`, evidence, impact) | Insights / Bits AI / **Incidents** | **DD gap (lab):** Incidents **0**, no packaged RC |

---

## 2. Confirmed building blocks vs gaps (lab-hardened)

### Confirmed (both)

| Building block | Evidence |
|----------------|----------|
| Continuous collect on FE→PRD→INV | Both labs under load |
| Failure semantics on leaf + cascade | DT 5xx / DD 503→502 |
| Call path reconstruction | Smartscape edges · APM map + `peer.hostname` |
| Multimodal-ish evidence for operators | DT Grail pull · DD APM (+ metrics tags) |
| Clear **after** fault clear | Both return to healthy |

### Confirmed Dynatrace-only (this scenario)

| Building block | Evidence |
|----------------|----------|
| Entity-keyed map ∥ lake | Smartscape + Grail under shared `entityId` |
| Detector → **Event** objects | `SERVICE_ERROR_RATE_INCREASED` class |
| Packaged **Problem** with named RC | **P-26084**, `rootCauseEntity=inventory` |
| Upstream kept but **not** RC-relevant | FE/PRD Events marked not RC |

### Confirmed Datadog-only strength (this scenario)

| Building block | Evidence |
|----------------|----------|
| Immediate, dense APM Detect *signal* | ~100% Flask error; **1317** inventory `@http.status_code:503`; ~12 min / ~1297 checkouts |
| Operator-ready flamegraph | Deepest error = inventory `/api/stock` ([example trace](https://app.datadoghq.com/apm/trace/6a7196aa00000000b9a41769b31205b8)) |
| Service map for the chain | `frontend → product → inventory` |

### Gaps to address (product / compare / our design)

| Gap | Whose | Why it matters |
|-----|-------|----------------|
| **Packaged RCA object** | Datadog (lab) | No Incident / Watchdog story / alerted monitor naming inventory as root — operator must Localize |
| **Monitor windowing** | Datadog | `min(last_15m)` can stay OK through a full outage if healthy minutes remain in the window |
| **Watchdog on synthetic cascade** | Datadog | Second Detect door did not open for FE/PRD/INV here |
| **Map vs lake twin write** | Datadog vs DT vocabulary | Do not equate Service Map with Smartscape ∥ Grail |
| **Davis scoring internals** | Dynatrace | Exact rank math unpublished — treat Problem as thin packager on rich fabric (**Inferred**) |
| **Our product wedge** | Unified RCA | Decide: entity fabric + package (DT-like), evidence-first + optional package (DD-like), or hybrid with **explicit** Curate→Package |

```text
SOLIDIFIED COMPARE (lab)
────────────────────────
Fabric:     BOTH strong (different ID: entityId vs tags)
Detect:     BOTH have signal — DT as Events; DD as APM density
Curate:     DT yes (Davis merge) · DD thin/absent
Tailor:     DT auto neighborhood · DD operator scope
Diagnose:   DT packages RC · DD stops at inspectable evidence
```

---

## 3. One-page stage verdict (same scenario)

| Clock A / product stage | Dynatrace | Datadog |
|-------------------------|-----------|---------|
| **Collect** | OneAgent → tenant | ddtrace → Agent → HQ |
| **Normalize** | Failure labeling; `entityId` prep | Span `status:error` + HTTP tags |
| **Topology bind** | Smartscape FE→PRD→INV + host | APM map FE→PRD→INV |
| **Fan-out / store** | Smartscape ∥ Grail | Metrics ∥ APM ∥ Logs (tag join) |
| **Detect** | Events on inventory (+ FE/PRD) | Dense APM errors; monitor often OK; Watchdog 0 |
| **Curate / package** | **Problem P-26084** | **No Incident** |
| **Tailor / Localize** | **`rootCauseEntity=inventory`** | Operator: deepest **503** = inventory |

**Headline:** same fault → Dynatrace ships a **ranked Problem with named root**; Datadog ships **rich traces + map** and leaves packaging thinner.

---

## 4. Stage-by-stage evidence

### 4.1 Collect

```text
Workload: frontend → product → inventory
Fault:    inventory 5xx
```

| | Dynatrace | Datadog |
|--|-----------|---------|
| Edge | OneAgent (`PYTHON`) | `ddtrace` → Trace Agent `:8126` (`apm_non_local_traffic`) |
| Observed | Services on `HOST-2FAAA6F0DAF83B21` | Spans `env:rca-lab` on `DESKTOP-MBPAQK1` |
| Store write | Continuous to Grail + Smartscape cues | Continuous to APM (+ metrics tags) |

### 4.2 Normalize

| | Dynatrace | Datadog |
|--|-----------|---------|
| Leaf | Failed request → failure-rate series | `status:error`, `@http.status_code:503` |
| Upstream | Elevated failure rate (propagated) | `502` on product/frontend on same traces |
| Insight | Detectors score **per service**; Davis ranks later | **All three** error — no auto collapse |

### 4.3 Topology bind / map

```text
Dynatrace:  frontend --calls--> product --calls--> inventory   (+ runsOnHost)
Datadog:    frontend → product → inventory   (+ peer.hostname on client spans)
```

| | Dynatrace | Datadog |
|--|-----------|---------|
| Identity | Stable `entityId` | `service` + `env` tags |
| Graph role | First-class walk for Davis | APM-derived; trust flamegraph early (catalog can lag) |

### 4.4 Detect

| | Dynatrace | Datadog |
|--|-----------|---------|
| Mechanism | Failure-rate detector → **Events** | APM error density; query monitors; Watchdog |
| Lab | Events on inventory (RC) + FE/PRD | **1317**× inventory 503; ~100% Flask error on all three; auto monitor often **OK**; Watchdog **0** |

### 4.5 Curate → Package → Localize

**Dynatrace — Problem `P-26084`**

| Field | Value |
|-------|-------|
| **rootCauseEntity** | **inventory** (`SERVICE-E25379CAD5DC3234`) |
| Affected | frontend, product, inventory |
| Evidence | Inventory failure rate **RC**; FE/PRD Events **not RC** |
| UI | [Problem P-26084](https://jjd82607.live.dynatrace.com/#problems/problemdetails;pid=-4496328508171095417_1785822660000V2) |

**Datadog — packaging**

| Field | Value |
|-------|-------|
| Incident / Watchdog | **0** / **none** for this fault |
| Operator path | APM → deepest inventory 503 |
| Example | [trace `6a7196aa…`](https://app.datadoghq.com/apm/trace/6a7196aa00000000b9a41769b31205b8) · [traces explorer](https://app.datadoghq.com/apm/traces?query=env%3Arca-lab+service%3A%28frontend+OR+product+OR+inventory%29) |

---

## 5. Timing

| Milestone | Notes |
|-----------|-------|
| DT dual-lab window | Fault ~05:54 UTC → Problem with RC~06:04 (~10 min continuous 5xx) |
| DD sustained rerun | ~12 min fault, ~1297 checkouts; clear → 200 |
| DT Detect latency | Events→Problem slower than first DD spans |
| DD Detect *signal* | Traces within ~1 min; packaging doors stayed shut |

---

## 6. Reproduce

```bash
# Datadog :18080 · Dynatrace :19080
cd datadog-rca-lab && docker compose up -d
cd ../dynatrace-rca-lab && docker compose up -d

datadog-rca-lab/scripts/load.sh 20
dynatrace-rca-lab/scripts/load.sh 20

./datadog-rca-lab/scripts/fault.sh inventory fail   # or: echo true > faults/inventory.fail
./dynatrace-rca-lab/scripts/fault.sh inventory fail on
# sustain ≥10–15 min

./datadog-rca-lab/scripts/fault.sh inventory ok
./dynatrace-rca-lab/scripts/fault.sh inventory fail off
```

---

## 7. Design takeaways (for our Clock A/B)

1. **Same destination** — name the root of a cascade with evidence; **different path** — package-first entity fabric (DT) vs evidence-first tagged APM (DD).
2. **Fabric is not the wedge** — both Collect/Normalize/Map work; the wedge is **Curate → Package**.
3. **Do not equate** Problem ↔ Incident, Smartscape ↔ Service Map, Grail ↔ “Datadog lake.”
4. **Gaps to own in our design:** explicit Curate (storm → one seed), Tailor cut contract, and whether Package is mandatory or optional — lab shows optional packaging can leave a clear fault **unpackaged**.

---

## 8. Related

| Doc | Role |
|-----|------|
| [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) · [HTML](./dynatrace-production-pipeline.html) | DT unveil |
| [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) · [HTML](./datadog-production-pipeline.html) | DD unveil |
| [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) | DT mechanisms (Davis) |
| [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html) | DD mechanisms |
| [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md) | Earlier DD notes |
| [`index.html`](./index.html) · [`:8765/docs.html`](http://127.0.0.1:8765/docs.html) | Docs hub |
