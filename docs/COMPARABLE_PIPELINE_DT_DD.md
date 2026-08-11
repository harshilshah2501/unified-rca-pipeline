# Comparable pipeline — Dynatrace vs Datadog

**Method (read this first):**

1. **Understand each vendor independently** — Dynatrace on Dynatrace terms ([DT hub](./dt-davis-category-hub.html) · [DT thesis](./DYNATRACE_PRODUCTION_PIPELINE.md)); Datadog on Datadog terms ([DD hub](./dd-detect-category-hub.html) · [DD thesis](./DATADOG_PRODUCTION_PIPELINE.md)).
2. **Then** use this page to line up a same-scenario lab and **derive common patterns** — without forcing one vendor’s geometry onto the other.
3. **Our pipeline HLD** (building blocks we will build) — [OBSERVEOPS_PIPELINE_HLD.md](./OBSERVEOPS_PIPELINE_HLD.md) · [HTML](./observeops-pipeline-hld.html). Engineering blocks E1–E11; MTL/Bits = Interpret layer, not fabric.

**Goal (shared destination):** From continuous telemetry on a service chain, surface *what broke*, *where*, and *what an operator should look at* — without re-collecting the estate from scratch on every alert.

### Geometry honesty (do not twin)

| | Dynatrace | Datadog |
|--|-----------|---------|
| **Teaching journey** | **Dual-track:** Smartscape ∥ Grail (two real write facets) | **Three-rail:** Metrics ∥ APM ∥ Logs (tag join) |
| **Topology** | Smartscape typed entity graph (`entityId`) | Service Map ≈ **APM-derived view** (not a peer write track) |
| **Evidence store** | Grail (multimodal lake + DQL) | Product explorers stay separate; backend = classic **Metrics timeseries** ∥ **Husky** event store (traces + logs + …) — **not** three equal peer DBs and **not** Grail |
| **Join key** | `entityId` | `service` + `env` (+ `host` / `version`) tags |
| **AI geometry** | Causal AI folded into **Davis** (default Problem path) | Separable surfaces: **Watchdog** (ML Detect) + **Bits** (agentic packaging) — optional on dense MTL |

There is **no Smartscape-like dual-track** on Datadog. Comparing “dual-track vs dual-track” or “Grail vs Husky as twin lakes” is a category error.

### Lab vintages (read before equating counts)

| Vintage | What | Use for |
|---------|------|---------|
| **Early same-scenario cascade** | DT **P-26084** (`rootCauseEntity=inventory`) · early DD inventory **503** / upstream **502** · dense APM, packaging doors quiet | Detailed §4 stage tables below |
| **Current DD ERROR primary** | `env:rca-lab-e3` · KeyError / HTTP **500** leaf · Door A Alert after sustain · APM Watchdog **0** · logs Watchdog stories **yes** · Bits investigation · Incident **0** | Building-block + AI/ML honesty; hubs / MTL / Bits tabs |
| **DT code-level follow-ons** | e.g. **P-260817** KeyError enrich · other Davis category timelines | Independent DT unveil — do not overwrite P-26084 clocks |

Same causal story across vintages: inventory leaf sick → callers fail. Status codes and Detect surfaces can differ by stack and run.

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

## 0. Philosophy — independent building blocks first

Both platforms are trying to answer:

> *Something is wrong in checkout — what is the root, and what evidence proves it?*

They do **not** disagree on that destination. They disagree on **building-block geometry** and **who does the last mile**.

### 0.1 Dynatrace building blocks (native)

| Block | Role (lab-hardened) |
|-------|---------------------|
| OneAgent / OTLP | Edge collect |
| Smartscape | Typed topology write / walk (`entityId`) |
| Grail | Multimodal evidence lake + DQL |
| Detectors → Events | Fault signal objects (baselines / thresholds on entity series) |
| **Davis** | Merge / rank / **Problem** package — causal AI layer (`rootCauseEntity` when ranked) |

Teaching path: Thesis → Breakdown → **Dual-track (Smartscape ∥ Grail)** → Timeline.

### 0.2 Datadog building blocks (native)

| Block | Role (lab-hardened) |
|-------|---------------------|
| Agent + ddtrace | Edge collect |
| Unified Service Tags | Identity join across products |
| Metrics ∥ APM ∥ Logs | Three **product** rails (three-rail); backend Metrics timeseries ∥ Husky events (traces+logs) |
| Service Map | APM-derived dependency view (not a dual-track write) |
| **Monitors ∥ Watchdog** | Door A (query) ∥ Door B (ML anomaly stories) — parallel Detect, not merged |
| Related / flamegraph | Operator leaf on dense MTL |
| **Bits ∥ Incident** | Packaging peer tab (Hypothesis Tree) ∥ optional Incident declare |

Teaching path: Thesis → Breakdown → **Three-rail (Metrics ∥ APM ∥ Logs)** → Timeline → MTL workbook → **Bits**.

### 0.3 Common patterns (derived later — not forced twins)

| Pattern (ours) | Appears on Dynatrace as… | Appears on Datadog as… |
|----------------|--------------------------|------------------------|
| Continuous edge collect | OneAgent | Agent + ddtrace |
| Identity on every record | `entityId` | tags (`service`/`env`/`host`/`version`) |
| Call-path reconstruction | Smartscape edges | APM peers / Service Map |
| Always-on evidence | Grail | Metrics ∥ APM ∥ Logs (Husky behind traces+logs) |
| Fault signal | Detectors → **Events** | Spans / rates + Door A Monitors ∥ Door B Watchdog |
| Named packaged root | **Problem** + `rootCauseEntity` (Davis default) | Flamegraph leaf always; **Bits** optional package; **Incident** often absent |
| AI / ML assist | Folded into Davis | Separable Watchdog + Bits surfaces |

**One sentence:** Dynatrace **pre-computes a joinable world and packages a verdict**; Datadog **maximizes inspectable evidence and leaves AI packaging optional**.

### 0.4 AI / ML comparison (derived — not twins)

**Honesty:** Datadog is **not** “more AI/ML” overall. Both are AI-heavy. Datadog **exposes more separable AI product surfaces**; Dynatrace **runs AI as the packaging engine** (Davis) by default.

**Generation criteria:** neither vendor is a clean Observability 2.0 or 3.0 match — score layers with must-pass checks (correlate ≠ 2.0; AI surfaces ≠ 3.0). See [`observability-generations-dt-dd.html`](./observability-generations-dt-dd.html).

| Layer | Dynatrace | Datadog | Do not equate |
|-------|-----------|---------|---------------|
| Anomaly / Detect AI | Detectors + auto baselining → **Events** | **Watchdog** unsupervised stories (+ anomaly monitors) | Event ≠ Watchdog story |
| Diagnose / package AI | **Davis** causal ranking → Problem + `rootCauseEntity` | **Bits** observe → hypothesize → validate (Hypothesis Tree); Incident separate | Problem ≠ Bits ≠ Incident |
| Topology role in AI | Smartscape walk is first-class input to Davis | Service Map assist; Bits / operator still rank on traces | Smartscape ≠ Service Map |
| Default vs optional | AI package path is **default** | ML Detect door + agentic Bits are **optional surfaces** on dense MTL | — |
| Lab honesty | Packaged RC Observed (e.g. **P-26084**) | e3: Door A Alert after sustain; APM Watchdog **0**; logs Watchdog **yes**; Bits [`90a88d93…`](https://app.datadoghq.com/bits-ai/investigations/90a88d93-2570-40c6-9706-d186290ea2b6?v=tree); Incident **0** | — |

Teaching one-liner: **Datadog shows more separate AI product surfaces; Dynatrace runs AI as the packaging engine.** Exact Davis / Watchdog / Bits scoring internals remain unpublished (black-box) — no public top-1 bakeoff ([`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md)).

### 0.5 Detect signal categories — twin list? (Public framing + Observed packs)

**Question:** Are Datadog’s default monitors the same kind of thing as Dynatrace Davis **event categories**?

**Answer:** Same *layer* of the stack (Detect inputs) — **not** the same taxonomy. Dynatrace publishes one official **`event.category`** list (fault semantics + severity). Datadog has **no twin list**: it splits Door A (monitor types / packs) and Door B (Watchdog by product rail).

#### Dynatrace — official twin list (`event.category`)

Most → least severe ([Event categories](https://docs.dynatrace.com/docs/dynatrace-intelligence/root-cause-analysis/event-analysis-and-correlation/event-categories); semantic dictionary also lists `INFO`):

| Category | Meaning | Opens Problem? | Our lab hub |
|----------|---------|----------------|-------------|
| **MONITORING_UNAVAILABLE** | Widespread OneAgent / visibility dark | Yes | Observed P-260826 |
| **AVAILABILITY** | Host / process / service outage | Yes | Observed P-260831 |
| **ERROR** | Error-rate / error incidents | Yes | Observed (KeyError) |
| **SLOWDOWN** | Performance / response-time degradation | Yes | Observed P-260820 |
| **RESOURCE_CONTENTION** | CPU / memory (and similar) saturation | Yes | Agent task |
| **CUSTOM_ALERT** | User-defined metric thresholds | Yes (merge often restricted) | — |
| **INFO / Warning** | Deploy / config / early warnings | Typically **no** | — |

Under each category sit many `event.type` values (e.g. `SERVICE_ERROR_RATE_INCREASED`, `SERVICE_SLOWDOWN`). **Category = significance class; type = concrete detector.**

#### Datadog — no twin list (what that means)

Datadog does **not** stamp every alert with one of ERROR · SLOWDOWN · AVAILABILITY · …. Instead:

| Surface | How signals are grouped | Not a Davis twin because… |
|---------|-------------------------|---------------------------|
| **Door A · Monitors** | By **monitor type** (Metric, APM, Logs, Anomaly, Process, Synthetics, …) and **`monitor_pack:`** tags | Pack = “default templates for a product surface,” not fault semantics |
| **Door B · Watchdog** | Facet **Alert Category** = `apm` · `infrastructure` · `logs` | Product-rail anomaly feed; APM watches error rate · latency · hits |

Same *ideas* (errors, latency, CPU) exist on Datadog; they are just **not filed in one twin category enum**.

#### Observed tenant: Host + APM recommended packs (11 templates)

**Public framing:** `monitor_pack` marks Datadog **recommended / out-of-the-box** monitors (multi-alert with `{{host.name}}` / `{{service.name}}`).

**Observed (this tenant UI):** Host pack **7** + APM pack **4** = **11** templates on that screen — **not** a global “Datadog defines exactly 11 monitors” rule. Other integrations can add more packs.

| Pack | Tag | Templates (Observed) |
|------|-----|----------------------|
| **Host** (7) | `monitor_pack:host` · `integration:host` | CPU high · Disk latency · Disk usage · Memory low · Network RX high · Network TX high · System load high |
| **APM** (4) | `monitor_pack:apm` | Watchdog Anomaly bridge · High Error Rate `fastapi.request` · **`flask.request`** · `web.request` |

Lab ERROR Door A (`310925690` family) sits in the **Flask High Error Rate** APM-pack line. **SLOWDOWN** has **no** twin in this 11 — latency Door A is often absent until you add a duration/p95 monitor. Host-pack CPU OK during KeyError is **negative** infra evidence, not the ERROR leaf.

#### Crosswalk (semantics → where it lives)

| Fault semantics | Dynatrace category | Datadog (typical) |
|-----------------|--------------------|-------------------|
| Failure / error rate | **ERROR** | APM High Error Rate pack · Watchdog APM error rate · log error anomalies |
| Latency / slow | **SLOWDOWN** | APM latency monitor (often **custom**) · Watchdog APM latency |
| Hard down | **AVAILABILITY** | Process / service check / synthetics — **not** host CPU pack |
| CPU / mem saturation | **RESOURCE_CONTENTION** | Host monitor pack · Watchdog infra |
| Agent / ingest dark | **MONITORING_UNAVAILABLE** | No single twin category |
| Custom threshold | **CUSTOM_ALERT** | Any Metric / Log / … monitor you author |

**Our HLD implication:** E6 Detect should use **semantic Detect classes** (Dynatrace-like), implemented with threshold and/or anomaly doors (Datadog-like) — do not copy `monitor_pack` names as the category system.

### Simplified illustration

> **Browser:** the HTML page renders this as a two-column visual — open [`comparable-pipeline-dt-dd.html`](./comparable-pipeline-dt-dd.html)#simplified-illustration.

```text
                    SAME DESTINATION
   “Name the causal leaf on the shared FE → product → inventory workload”
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
     DYNATRACE (native)              DATADOG (native)
     ──────────────────              ────────────────
     Dual-track fabric               Three-rail stores
     Smartscape ∥ Grail              Metrics ∥ APM ∥ Logs
     join = entityId                 join = tags
     map = typed write path          map = APM-derived view
     lake = Grail                    backend = Metrics store ∥ Husky

     Detect → Event objects          Door A Monitors ∥ Door B Watchdog
     Davis (causal AI) → Problem     Signal = spans / rates / logs
       rootCauseEntity (may be null) Flamegraph leaf by Detect class
                                     Bits (optional) · Incident often 0
```

---

## 1. Optional pattern lens (Clock A — after native reading)

We keep **our** stage names as a **later** compare lens only — not as either vendor’s product model. Read §0 first.

### Phase 1 — Always-on fabric

| Our stage | Dynatrace (confirmed) | Datadog (confirmed) | Fit |
|-----------|----------------------|---------------------|-----|
| **Collect** | OneAgent / OTLP | Agent + ddtrace | Strong both |
| **Normalize** | Enrichment + failure labeling + entity prep | Unified Service Tags + span status/HTTP codes | Strong both (different ID model) |
| **Topology bind** | Smartscape + bind LUT → **`entityId`** | Catalog + APM Service Map / `peer.hostname` | Both reconstruct FE→PRD→INV; DT = typed entity graph, DD = tag/trace-derived |
| **Fan-out** | **Smartscape upserts ∥ Grail evidence** (dual-track) | Write **Metrics ∥ APM ∥ Logs** (three-rail); backend Metrics store ∥ Husky; map mostly **derived from APM** | Continuous write both; **different geometry** — do not call DD dual-track |
| **Maintain** | Grail lifecycle + Smartscape freshness (**named DT fabric stage**) | **No named Maintain stage** — continuous **03 Write** + retention/indexing/discovery in product stores | DT yes · DD remap (do not call DD “Maintain”) |

### Phase 2 — Case opens

| Our stage | Dynatrace (confirmed) | Datadog (confirmed) | Gaps |
|-----------|----------------------|---------------------|------|
| **Detect** | Failure-rate **Events** (e.g. inventory + upstream) | **APM error spans/rates** always visible; Door A **Monitors** ∥ Door B **Watchdog** | Early cascade: auto High Error Rate often **OK** (`min(last_15m)`); Watchdog quiet. **e3:** Door A Alert after sustain; APM Watchdog **0**; logs Watchdog stories **yes** |
| **Curate** | Davis merges nearby Events toward one Problem narrative | Monitor/story grouping; optional Incident seed; Bits scopes later | **DD gap:** no auto merge to one seed — FE/PRD/INV all `error` |
| **Tailor** | Smartscape neighborhood + Grail DQL time cut | Operator (or **Bits**) scopes services + time + Related | **DD:** human / Bits cut; not a first-class auto neighborhood expand |

### Phase 3 — Diagnose

| Our stage | Dynatrace (confirmed) | Datadog (confirmed) | Gaps |
|-----------|----------------------|---------------------|------|
| **Localize** | Smartscape walk from seed → candidate entities | Trace / Service Map; deepest error span | DD: **operator (or Bits) on flamegraph**, not `rootCauseEntity` |
| **Identify** | Rank `rootCauseRelevant` evidence (inferred scoring) | Status codes, resources, related metrics/logs on the trace; Bits Hypothesis Tree | Both correlational at packaging layer; DT packages by default |
| **Verify / Package** | **Problem** card (`rootCauseEntity`, evidence, impact) — Davis AI default | **Bits** peer tab ∥ **Incidents** | **DD:** Incident often **0**; Bits optional (e3: [`90a88d93…`](https://app.datadoghq.com/bits-ai/investigations/90a88d93-2570-40c6-9706-d186290ea2b6?v=tree)); leaf claim still valid from MTL alone |

---

## 2. Confirmed building blocks vs gaps (lab-hardened)

### Confirmed (both)

| Building block | Evidence |
|----------------|----------|
| Continuous collect on FE→PRD→INV | Both labs under load |
| Failure semantics on leaf + cascade | DT 5xx / early DD 503→502 / e3 DD 500→502 |
| Call path reconstruction | Smartscape edges · APM map + `peer.hostname` |
| Multimodal-ish evidence for operators | DT Grail pull · DD APM + Metrics + Logs (tag join) |
| Clear **after** fault clear | Both return to healthy |
| AI surfaces exist | Davis packaging · Watchdog / Bits (different geometry — see §0.4) |

### Confirmed Dynatrace-only (this scenario)

| Building block | Evidence |
|----------------|----------|
| Entity-keyed map ∥ lake | Smartscape + Grail under shared `entityId` |
| Detector → **Event** objects | `SERVICE_ERROR_RATE_INCREASED` class |
| Packaged **Problem** with named RC | **P-26084**, `rootCauseEntity=inventory` |
| Upstream kept but **not** RC-relevant | FE/PRD Events marked not RC |

**Follow-on (2026-08-06, code-level enrich):** **P-260817** — same leaf pattern with real `KeyError` in inventory; API event timeline + teaching notes in [`dt-lab-timeline-code-level.html`](./dt-lab-timeline-code-level.html) (`rootCauseEntity=null` this pull).

### Confirmed Datadog-only strength (this scenario)

| Building block | Evidence |
|----------------|----------|
| Immediate, dense APM Detect *signal* | Early cascade: ~100% Flask error; **1317** inventory `@http.status_code:503`. **e3:** KeyError/500 ≈2427 · Upstream*/502 ≈2421 · `rca.inventory.stock.errors` ≈2403 |
| Operator-ready flamegraph | Deepest error = inventory `/api/stock` (e3 sample [`6a79840f…`](https://app.datadoghq.com/apm/trace/6a79840f000000005f3c58a8cfc1f888); early [`6a7196aa…`](https://app.datadoghq.com/apm/trace/6a7196aa00000000b9a41769b31205b8)) |
| Service map for the chain | `frontend → product → inventory` |
| Separable AI surfaces | Door B Watchdog (logs stories on e3) + **Bits** peer tab ([`dd-bits-error-review.html`](./dd-bits-error-review.html) · investigation `90a88d93…`) |

### Gaps to address (product / compare / our design)

| Gap | Whose | Why it matters |
|-----|-------|----------------|
| **Default packaged RCA object** | Datadog (lab) | Incident often **0**; Bits is optional peer packaging — operator / Bits must still name the leaf (unlike Davis Problem default) |
| **Monitor windowing** | Datadog | `min(last_15m)` can stay OK through a short outage; sustain (~15m near-100% errors) can flip Door A to **Alert** (e3 Observed) |
| **Watchdog APM vs logs** | Datadog | APM Watchdog bridge can stay quiet while **logs** Watchdog stories fire — doors are not fused |
| **Map vs lake twin write** | Vocabulary trap | Datadog has **three-rail** stores + APM-derived Service Map + Husky behind traces/logs — **not** Smartscape ∥ Grail dual-track |
| **“DD is more AI” myth** | Vocabulary trap | More **separable** AI surfaces ≠ more AI overall; Davis **is** the AI packaging engine (§0.4) |
| **Detect category twin list** | Vocabulary trap | DT `event.category` ≠ DD `monitor_pack` / Watchdog rails; Observed Host+APM = **11 templates**, not Davis taxonomy (§0.5) |
| **Davis / Bits / Watchdog scoring internals** | Both | Exact rank math unpublished — treat as black-box (**Inferred** / Public framing) |
| **Our product wedge** | Unified RCA | Decide after independent unveils: entity fabric + package (DT-like), evidence-first + optional package (DD-like), or hybrid with **explicit** Curate→Package |

```text
SOLIDIFIED COMPARE (lab)
────────────────────────
Geometry:   DT dual-track (Smartscape∥Grail) · DD three-rail (M∥T∥L) + Husky + derived map
Fabric:     BOTH strong (different ID: entityId vs tags)
Detect:     BOTH have signal — DT as Events; DD as APM density + Door A∥B
AI:         DT Davis default package · DD Watchdog ML door + Bits optional agent
Curate:     DT yes (Davis merge) · DD thin/absent as auto seed
Investigate: DT auto neighborhood · DD Related + flamegraph (+ Bits)
Diagnose:   DT packages RC · DD leaf from MTL; Bits/Incident optional
```

---

## 3. One-page stage verdict (same scenario)

| Pattern lens / product | Dynatrace | Datadog |
|------------------------|-----------|---------|
| **Collect** | OneAgent → tenant | ddtrace → Agent → HQ |
| **Identity** | `entityId` prep | Unified Service Tags + HTTP/status |
| **Topology** | Smartscape FE→PRD→INV + host | APM Service Map FE→PRD→INV (derived) |
| **Stores** | Smartscape ∥ Grail (**dual-track**) | Metrics ∥ APM ∥ Logs (**three-rail**); backend Metrics ∥ Husky |
| **Detect** | Events on inventory (+ FE/PRD) | Dense APM errors; Door A∥B (e3: Door A Alert after sustain; APM Watchdog 0; logs Watchdog yes) |
| **AI / package** | **Davis → Problem P-26084** | Flamegraph leaf; **Bits** optional ([`90a88d93…`](https://app.datadoghq.com/bits-ai/investigations/90a88d93-2570-40c6-9706-d186290ea2b6?v=tree)); Incident often **0** |
| **Leaf claim** | **`rootCauseEntity=inventory`** | Operator / Bits: deepest **5xx** = inventory (early 503 · e3 KeyError/500) |

**Headline:** same fault → Dynatrace ships a **ranked Problem with named root (Davis default)**; Datadog ships **rich MTL + separable AI surfaces** and leaves packaging (Bits / Incident) optional.

---

## 4. Stage-by-stage evidence

> **Vintage:** tables in this section are the **early same-scenario cascade** (DD inventory **503**, packaging doors quiet) unless noted. For current DD ERROR Detect/Bits honesty see lab vintages above and [`dd-detect-category-hub.html`](./dd-detect-category-hub.html).

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
| Incident / Watchdog | Early cascade: Incident **0** / Watchdog quiet. **e3:** APM Watchdog **0**, logs Watchdog **yes**, Door A Alert after sustain |
| Operator path | APM → deepest inventory 5xx; optional **Bits** peer tab |
| Example (early) | [trace `6a7196aa…`](https://app.datadoghq.com/apm/trace/6a7196aa00000000b9a41769b31205b8) |
| Example (e3 Bits) | [`dd-bits-error-review.html`](./dd-bits-error-review.html) · [investigation `90a88d93…`](https://app.datadoghq.com/bits-ai/investigations/90a88d93-2570-40c6-9706-d186290ea2b6?v=tree) |

---

## 5. Timing

| Milestone | Notes |
|-----------|-------|
| DT dual-lab window | Fault ~**05:54 UTC** → Problem with RC ~**06:04 UTC** (~10 min continuous 5xx) |
| DD sustained rerun | ~12 min fault, ~1297 checkouts; clear → 200 |
| DT Detect latency | Events→Problem slower than first DD spans |
| DD Detect *signal* | Traces within ~1 min; packaging doors stayed shut |

**Teaching alignment:** Dynatrace mechanisms / Maintain / Curate / Tailor clocks for **ERROR** teaching use this **same UTC window** (not fictional `07:xx`, not IST). Mid-window sample times are illustrative inside `[05:54, 06:04]`; anchors **05:54** and **06:04** are **Observed**. For **SLOWDOWN**, use **P-260820** clocks (Events ≈15:05 → Problem ≈15:10) — do not reuse this ERROR window. See [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html)`?cat=` · [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md).

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

## 7. Design takeaways

1. **Independent first** — finish DT and DD unveils on each vendor’s own terms; this page is for **derived** patterns, not a twining template.
2. **Same destination** — name the root of a cascade with evidence; **different geometry** — DT dual-track (Smartscape ∥ Grail) vs DD three-rail (Metrics ∥ APM ∥ Logs) + Husky + APM-derived Service Map.
3. **Do not equate** Problem ↔ Incident, Smartscape ↔ Service Map, Grail ↔ Husky / “Datadog lake,” Dual-track ↔ Three-rail, Davis ↔ Bits, Event ↔ Watchdog story.
4. **Fabric is not the wedge** — both collect/map/evidence work; the wedge is **merge → package** (DT strong / default; DD thin unless Bits/Incident).
5. **AI geometry, not AI volume** — Datadog shows more **separable** AI surfaces (Watchdog + Bits); Dynatrace runs AI as the **Davis packaging engine**. Neither is “more AI” as a blanket claim (§0.4).
6. **Detect categories are not twin lists** — Dynatrace `event.category` (ERROR · SLOWDOWN · …) ≠ Datadog `monitor_pack` / Watchdog `apm|infrastructure|logs`. Observed Host+APM packs = **11 templates** on one screen, not a Davis taxonomy (§0.5).
7. **Gaps to own in our design:** explicit Curate (storm → one seed), investigation cut contract, and whether Package is mandatory or optional — lab shows optional packaging can leave a clear fault **unpackaged**.

---

## 8. Related

| Doc | Role |
|-----|------|
| [`dt-davis-category-hub.html`](./dt-davis-category-hub.html) | DT hub (independent) |
| [`dd-detect-category-hub.html`](./dd-detect-category-hub.html) | DD hub (independent) |
| [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) · [HTML](./dynatrace-production-pipeline.html) | DT unveil |
| [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) · [HTML](./datadog-production-pipeline.html) | DD unveil |
| [`dt-e2e-smartscape-grail.html`](./dt-e2e-smartscape-grail.html) | DT Dual-track Smartscape ∥ Grail |
| [`dd-e2e-metrics-traces-logs.html`](./dd-e2e-metrics-traces-logs.html) | DD Three-rail Metrics ∥ APM ∥ Logs |
| [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) | DT mechanisms (Davis) |
| [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html) | DD mechanisms |
| [`dd-bits-error-review.html`](./dd-bits-error-review.html) | DD Bits peer tab (Hypothesis Tree · 500 vs 502) |
| [`datadog-lab-evidence-mtl-error-2026-08-10.html`](./datadog-lab-evidence-mtl-error-2026-08-10.html) | DD e3 MTL appendix |
| [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md) | Earlier DD notes |
| [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) | No public top-1 AI bakeoff |
| [`index.html`](./index.html) · [`:8765/docs.html`](http://127.0.0.1:8765/docs.html) | Docs hub |
