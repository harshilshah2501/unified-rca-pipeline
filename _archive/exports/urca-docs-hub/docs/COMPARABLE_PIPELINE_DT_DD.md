# Comparable pipeline — DT vs DD vs ED

**Method (read this first):**

1. **Understand each vendor independently** — Dynatrace on Dynatrace terms ([DT hub](./dt-davis-category-hub.html) · [DT thesis](./DYNATRACE_PRODUCTION_PIPELINE.md)); Datadog on Datadog terms ([DD hub](./dd-detect-category-hub.html) · [DD thesis](./DATADOG_PRODUCTION_PIPELINE.md)); Edge Delta on Edge Delta terms ([ED hub](./ed-ai-team-hub.html) · [ED thesis](./EDGEDELTA_PRODUCTION_PIPELINE.md)).
2. **Then** use this page to **derive common patterns** — without forcing one vendor’s geometry onto another. Same-scenario lab tables (§3–§6) remain **DT vs DD**. Edge Delta enters **geometry / AI / E-block unfold** (§0), not those lab clocks.
3. **Our pipeline HLD** (building blocks we will build) — [OBSERVEOPS_PIPELINE_HLD.md](./OBSERVEOPS_PIPELINE_HLD.md) · [HTML](./observeops-pipeline-hld.html). Engineering blocks E1–E11; MTL/Bits = Interpret layer, not fabric.

**Goal (shared destination):** From continuous telemetry on a service chain, surface *what broke*, *where*, and *what an operator should look at* — without re-collecting the estate from scratch on every alert.

> **Special note — two philosophies, one destination**
>
> Both want the same answer: *what broke, where, with evidence.* They disagree on **where the thinking happens**.
>
> - **DT / DD — centralize-then-analyze:** ship the stream to HQ, then think there (map, lake, Detect, Package).
> - **ED — shift processing left:** think at the source (shape / reduce), then send less, cleaner data — then a standing Team.
>
> Dual-track vs three-rail is a later split *inside* the centralized camp. “Left” does not mean “no platform.”

### Geometry honesty (do not twin)

| | Dynatrace | Datadog | Edge Delta |
|--|-----------|---------|------------|
| **Teaching journey** | **Dual-track:** Smartscape ∥ Grail (two real write facets) | **Three-rail:** Metrics ∥ APM ∥ Logs (tag join) | **Dual-layer:** Telemetry Pipelines ∥ AI Team (hygiene, then a standing team) |
| **Topology** | Smartscape typed entity graph (`entityId`) | Service Map ≈ **APM-derived view** (not a peer write track) | eBPF Service Map at Node Pipeline (**Public framing**). This tenant: UI present, empty / error (**Observed UI**) |
| **Evidence store** | Grail (multimodal lake + DQL) | Product explorers stay separate; backend = classic **Metrics timeseries** ∥ **Husky** event store (traces + logs + …) — **not** three equal peer DBs and **not** Grail | Platform index of *already processed* telemetry; optional fan-out to 3rd-party lakes (**Public framing**). This tenant: Logs 0 · Traces 0 (**Observed UI**) |
| **Join key** | `entityId` | `service` + `env` (+ `host` / `version`) tags | OTel / OCSF + pipeline metadata tags (**Public framing**). Not Observed on this tenant |
| **AI geometry** | Causal AI folded into **Davis** (default Problem path) | Separable surfaces: **Watchdog** (ML Detect) + **Bits** (agentic packaging) — optional on dense MTL | Persistent **AI Team** (OnCall + specialists); Issues + Overview; human-in-the-loop for actions |
| **Processing locus** | **Centralize-then-analyze** — collect at the edge; bind / map / lake / detect **in platform** (**Observed lab**) | **Centralize-then-analyze** — collect tagged; rails write continuously **in platform** (**Observed lab**) | **Shift processing left** — parse / enrich / mask / pattern / route **before egress** (**Public framing**). This tenant: no named pipeline (**Observed UI**) |
| **Peer vs composition** | Full-stack observability peer | Full-stack observability peer | Peer *and* can sit **in front of** DT/DD as a destination (**Public framing**). This tenant: no Datadog/Splunk dest (**Observed UI**) |

There is **no Smartscape-like dual-track** on Datadog. There is **no Dual-track and no Three-rail twin** on Edge Delta. Dual-layer ≠ Dual-track. Comparing “Grail vs Husky vs ED Platform as twin lakes” is a category error.

### Processing locus (derived — not twins)

Plain language is in the **Special note** at the top of this page. Detail follows.

**Teaching names (ours):** Dynatrace and Datadog **centralize-then-analyze**. Edge Delta **shifts processing left**. Same destination; different *when* the estate is shaped.

- **Centralize-then-analyze** (DT, DD): the agent/tracer is collect (+ light tag). Topology, evidence store, Detect, and Package run on **platform-side** data. OneAgent and `ddtrace` are not dumb pipes — the *analyze* still happens after ingest.
- **Shift processing left** (ED): Telemetry Pipelines are the product lift — hygiene and reduction **at Node / Gateway before egress**, then a standing AI Team on that cleaned stream (**Public framing**). Overview / Issues still land centrally; the hygiene is left. That is why ED can sit **in front of** a DT/DD destination.

Same locus ≠ same geometry. Dual-track and three-rail both centralize; they are still not twins. Do not read “left” as “no platform.”

### Lab vintages (read before equating counts)

| Vintage | What | Use for |
|---------|------|---------|
| **Early same-scenario cascade** | DT **P-26084** (`rootCauseEntity=inventory`) · early DD inventory **503** / upstream **502** · dense APM, packaging doors quiet | Detailed §4 stage tables below |
| **Current DD ERROR primary** | `env:rca-lab-e3` · KeyError / HTTP **500** leaf · Door A Alert after sustain · APM Watchdog **0** · logs Watchdog stories **yes** · Bits investigation · Incident **0** | Building-block + AI/ML honesty; hubs / MTL / Bits tabs |
| **DT code-level follow-ons** | e.g. **P-260817** KeyError enrich · other Davis category timelines | Independent DT unveil — do not overwrite P-26084 clocks |
| **ED tenant snapshot (2026-08-14)** | Org `gmailcom_d4486595` Free · AI Team provisioned · Issues **0** · Logs/traces **0** · Pipeline Liveness **OK** | Geometry / AI / E-block unfold only — **not** a same-scenario lab |

Same causal story across vintages: inventory leaf sick → callers fail. Status codes and Detect surfaces can differ by stack and run.

### What we ran (and why it is “identical”)

We needed one fault both vendors could see, so differences would come from **pipeline behavior**, not from different apps or different bugs. Edge Delta is **not** in this lab — its column is geometry only (§0), from the 2026-08-14 tenant snapshot.

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
| **Observed (UI)** | Seen in a live vendor console that is **not** our same-scenario lab (Edge Delta org `gmailcom_d4486595`, 2026-08-14) | ED geometry claims: teammates, monitors, empty explorers, Issues 0 |
| **Public framing** | How the vendor describes the product in docs/marketing — useful vocabulary, not a lab proof | Naming building blocks (Grail, Watchdog, Service Map, ED Pipelines) when we did not open the black box |
| **Inferred** | Reasonable model that fits observations + public framing, but is **not** an internal vendor spec | e.g. “Davis is a thin packager,” exact ranking math, how map and lake stay aligned |

Unless a sentence is marked otherwise, treat DT/DD stage tables as **Observed (lab)**. Treat Edge Delta columns as **Observed (UI)** + **Public framing**. There is no `edgedelta-rca-lab`.

Labs: [`dynatrace-rca-lab`](../dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md) · [`datadog-rca-lab`](../datadog-rca-lab/DATADOG_RCA_REFERENCE.md)  
Browser: [`comparable-pipeline-dt-dd.html`](./comparable-pipeline-dt-dd.html) · [`:8765`](http://127.0.0.1:8765/comparable-pipeline-dt-dd.html) · [docs hub](http://127.0.0.1:8765/docs.html)

---

## 0. Philosophy — independent building blocks first

Three platforms are trying to answer:

> *Something is wrong in checkout — what is the root, and what evidence proves it?*

They do **not** disagree on that destination. They disagree on **building-block geometry**, **processing locus** (centralize-then-analyze vs shift processing left), and **who does the last mile**. Same-scenario lab clocks (§3–§6) remain **two vendors**. Geometry, AI placement, and E-block unfold in this section are **three**.

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

### 0.2b Edge Delta building blocks (native — Observed UI + Public framing)

Not lab-hardened. No `edgedelta-rca-lab`. Independent unveil: [ED hub](./ed-ai-team-hub.html) · [ED thesis](./EDGEDELTA_PRODUCTION_PIPELINE.md) · [tenant evidence 2026-08-14](./edgedelta-tenant-evidence-2026-08-14.md).

| Block | Role |
|-------|------|
| Telemetry Pipelines | Shape at the edge: admit / parse / enrich / mask / pattern / route. Node / Gateway / Cloud / Coordinator (**Public framing**). This tenant: no Pipelines nav; `/pipelines` redirected to AI Overview (**Observed UI**) |
| Platform index | Evidence of *already processed* telemetry; optional 3rd-party destination (**Public framing**). Logs **0** · traces **0** (**Observed UI**) |
| Service Map | eBPF at Node Pipeline (**Public framing**). UI present, empty / error (**Observed UI**) |
| Monitors | Event Threshold · Pattern Anomaly · Metric Threshold — not a Davis `event.category` enum (**Observed UI**: 5 monitors) |
| **AI Team** | Persistent OnCall + specialists (Security / Software / SRE / Work Tracker **Observed**). Human-in-the-loop for actions (**Public framing**) |
| **Issue ∥ Overview** | Recurring-problem package + health landing page. Issue ≠ Problem ≠ Bits ≠ Incident. **Observed:** Issues **0**, Overview 100% Healthy |

Teaching path: Thesis → **Dual-layer (Pipelines ∥ AI Team)** → tenant snapshot.

### 0.3 Common patterns (derived later — not forced twins)

| Pattern (ours) | Appears on Dynatrace as… | Appears on Datadog as… | Appears on Edge Delta as… |
|----------------|--------------------------|------------------------|---------------------------|
| Continuous edge collect | OneAgent | Agent + ddtrace | Node / Gateway / Cloud Pipelines (**Public framing**; none named **Observed UI**) |
| Identity on every record | `entityId` | tags (`service`/`env`/`host`/`version`) | OTel / OCSF + pipeline metadata (**Public framing**) |
| Call-path reconstruction | Smartscape edges | APM peers / Service Map | eBPF Service Map at Node (**Public framing**). Empty / error **Observed UI** |
| Always-on evidence | Grail | Metrics ∥ APM ∥ Logs (Husky behind traces+logs) | Platform index of processed telemetry; optional fan-out. Logs/traces **0 Observed UI** |
| Fault signal | Detectors → **Events** | Spans / rates + Door A Monitors ∥ Door B Watchdog | Pattern anomaly + Platform monitors (Event Threshold / Pattern Anomaly / Metric Threshold) |
| Named packaged root | **Problem** + `rootCauseEntity` (Davis default) | Flamegraph leaf always; **Bits** optional package; **Incident** often absent | **Issue** + Overview (**Public framing**). Issues **0 Observed UI** |
| AI / ML assist | Folded into Davis | Separable Watchdog + Bits surfaces | Persistent **AI Team** (OnCall + specialists); actions need approval |
| Where the heavy lift sits | Bind / map / lake **in platform** — **centralize-then-analyze** | Rails write continuously **in platform** — **centralize-then-analyze** | **Shift processing left** — shape at the edge before egress (**Public framing**) |

**One sentence:** Dynatrace and Datadog **centralize-then-analyze** (DT packages a verdict; DD leaves packaging optional); Edge Delta **shifts processing left**, then runs a standing AI Team whose landing page is Overview / Issues.

### 0.4 AI / ML comparison (derived — not twins)

**Honesty:** None of the three is “more AI/ML” as a blanket claim. They **place** AI differently. Datadog **exposes more separable AI product surfaces**; Dynatrace **runs AI as the packaging engine** (Davis) by default; Edge Delta **runs a persistent Team** whose packaging object is an Issue.

**Generation criteria:** neither DT nor DD is a clean Observability 2.0 or 3.0 match — score layers with must-pass checks (correlate ≠ 2.0; AI surfaces ≠ 3.0). Edge Delta is not scored on that page. See [`observability-generations-dt-dd.html`](./observability-generations-dt-dd.html).

| Layer | Dynatrace | Datadog | Edge Delta | Do not equate |
|-------|-----------|---------|------------|---------------|
| Anomaly / Detect AI | Detectors + auto baselining → **Events** | **Watchdog** unsupervised stories (+ anomaly monitors) | Pattern Anomaly monitor + Event / Metric Threshold (**Observed UI**) | Event ≠ Watchdog story ≠ Pattern Anomaly |
| Diagnose / package AI | **Davis** causal ranking → Problem + `rootCauseEntity` | **Bits** observe → hypothesize → validate (Hypothesis Tree); Incident separate | Persistent **AI Team** → **Issue** + Overview; actions need approval | Problem ≠ Bits ≠ Incident ≠ Issue |
| Topology role in AI | Smartscape walk is first-class input to Davis | Service Map assist; Bits / operator still rank on traces | eBPF Service Map at Node (**Public framing**); empty **Observed UI** | Smartscape ≠ Service Map ≠ ED Service Map |
| Default vs optional | AI package path is **default** | ML Detect door + agentic Bits are **optional surfaces** on dense MTL | Team is **standing** (default product surface); Issue may still be **0** | — |
| Honesty | Packaged RC **Observed (lab)** (e.g. **P-26084**) | e3 **Observed (lab):** Door A Alert after sustain; APM Watchdog **0**; logs Watchdog **yes**; Bits [`90a88d93…`](https://app.datadoghq.com/bits-ai/investigations/90a88d93-2570-40c6-9706-d186290ea2b6?v=tree); Incident **0** | **Observed (UI):** Team provisioned; Issues **0**; one GitHub workflow thread; no MELT | — |

Teaching one-liner: **Datadog shows more separate AI product surfaces; Dynatrace runs AI as the packaging engine; Edge Delta runs AI as a standing Team with human-in-the-loop actions.** Exact Davis / Watchdog / Bits / Issue-match internals remain unpublished (black-box) — no public top-1 bakeoff ([`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md)). HLD **D5** stays Review.

### 0.5 Detect signal categories — twin list? (Public framing + Observed packs)

**Question:** Are Datadog’s default monitors the same kind of thing as Dynatrace Davis **event categories**?

**Answer:** Same *layer* of the stack (Detect inputs) — **not** the same taxonomy. Dynatrace publishes one official **`event.category`** list (fault semantics + severity). Datadog has **no twin list**: it splits Door A (monitor types / packs) and Door B (Watchdog by product rail). Edge Delta also has **no twin list**: Observed types are Event Threshold · Pattern Anomaly · Metric Threshold — product-surface monitors, not ERROR / SLOWDOWN / AVAILABILITY. Do not invent a Davis category matrix for ED.

#### Dynatrace — official twin list (`event.category`)

Most → least severe ([Event categories](https://docs.dynatrace.com/docs/dynatrace-intelligence/root-cause-analysis/event-analysis-and-correlation/event-categories); semantic dictionary also lists `INFO`):

| Category | Meaning | Opens Problem? | Our lab hub |
|----------|---------|----------------|-------------|
| **MONITORING_UNAVAILABLE** | Widespread OneAgent / visibility dark | Yes | Observed P-260826 |
| **AVAILABILITY** | Host / process / service outage | Yes | Observed P-260831 · organic cascade P-260854 PERFORMANCE |
| **ERROR** | Error-rate / error incidents | Yes | Observed (KeyError) |
| **SLOWDOWN** | Performance / response-time degradation | Yes | Observed P-260820 |
| **RESOURCE_CONTENTION** | CPU / memory (and similar) saturation | Yes | Observed (negative Detect, 2026-08-12) |
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

| Fault semantics | Dynatrace category | Datadog (typical) | Edge Delta (this tenant) |
|-----------------|--------------------|-------------------|--------------------------|
| Failure / error rate | **ERROR** | APM High Error Rate pack · Watchdog APM error rate · log error anomalies | No ERROR twin. Pattern Anomaly exists as a type, not a fault class |
| Latency / slow | **SLOWDOWN** | APM latency monitor (often **custom**) · Watchdog APM latency | No SLOWDOWN twin |
| Hard down | **AVAILABILITY** | Process / service check / synthetics — **not** host CPU pack | No AVAILABILITY twin |
| CPU / mem saturation | **RESOURCE_CONTENTION** | Host monitor pack · Watchdog infra | No RESOURCE_CONTENTION twin |
| Agent / ingest dark | **MONITORING_UNAVAILABLE** | No single twin category | Default Pipeline Liveness (**Metric Threshold**, **OK Observed UI**) — control-plane heartbeat, not a Davis twin |
| Custom threshold | **CUSTOM_ALERT** | Any Metric / Log / … monitor you author | Event Threshold / Metric Threshold you author (GitHub Event Thresholds **No Data Observed**) |

**Our HLD implication:** E6 Detect should use **semantic Detect classes** (Dynatrace-like), implemented with threshold and/or anomaly doors (Datadog-like) — do not copy `monitor_pack` names, and do not copy ED monitor *types*, as the category system.

### 0.6 Edge Delta comparative unfold (geometry — not a third lab)

**Honesty:** this is **Observed (UI)** + **Public framing**, not **Observed (lab)**. Dual-layer ≠ Dual-track ≠ Three-rail. Processing locus: ED **shifts processing left**; DT/DD **centralize-then-analyze**. ED can be a **peer** *and* can sit **in front of** DT/DD as a destination (**Public framing**). This tenant fans out to GitHub + Edge Delta MCP + Edge Delta Documentation only — no Datadog/Splunk dest (**Observed UI**).

Same abstract I/O as Our HLD. Columns are native anchors, not twins.

| Block | Dynatrace | Datadog | Edge Delta |
|-------|-----------|---------|------------|
| **E1 Collect** | OneAgent / OTLP | Agent + ddtrace | Node / Gateway / Cloud Pipelines admit (**Public framing**). No pipeline options **Observed UI** |
| **E2 Identity** | `entityId` | Unified Service Tags | OTel / OCSF + pipeline metadata (**Public framing**) |
| **E3 Topology** | Smartscape typed write | APM-derived Service Map | eBPF Service Map at Node (**Public framing**). UI error **Observed UI** |
| **E4 Stores** | Grail | Metrics timeseries ∥ Husky | Platform index of processed telemetry; optional fan-out. Logs/traces **0 Observed UI** |
| **E5 Maintain** | OneAgent health / entity freshness | Agent / intake health | Coordinator, Packs, Pipeline Liveness **OK Observed UI** |
| **E6 Detect** | Detectors → Events (`event.category`) | Door A Monitors ∥ Door B Watchdog | Pattern anomaly + Platform monitors. No Davis twin list |
| **E7 Curate** | Davis merge into Problem | Operator / Bits / monitor grouping | Issue match (join or create). Issues **0 Observed UI** |
| **E8 Scope** | Problem entity set | Tag + time + related | Issue adds services/envs. Not Observed (no Issue) |
| **E9 Localize** | Davis + Smartscape walk | Flamegraph / related | SRE teammate investigation — not a Smartscape walk |
| **E10 Identify** | Grail DQL / code-level | MTL / Bits citations | Edge Delta MCP. Connected; no MELT **Observed UI** |
| **E11 Package** | Problem + `rootCauseEntity` (**default**) | Bits optional; Incident often **0** | Issue card + Overview. Issues **0 Observed UI** |

**Do not equate:** Problem ↔ Incident ↔ Issue; Davis ↔ Bits ↔ AI Team; Event ↔ Watchdog story ↔ Pattern Anomaly; Smartscape ↔ Service Map ↔ ED Service Map; Dual-track ↔ Three-rail ↔ Dual-layer.

### Simplified illustration

> **Browser:** the HTML page renders this as a three-column visual — open [`comparable-pipeline-dt-dd.html`](./comparable-pipeline-dt-dd.html)#simplified-illustration.

```text
                         SAME DESTINATION
        “Name the causal leaf — with evidence an operator can act on”
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        DYNATRACE             DATADOG              EDGE DELTA
        Dual-track            Three-rail           Dual-layer
        centralize-then-      centralize-then-     shift processing
          analyze               analyze              left
        Smartscape ∥ Grail    Metrics ∥ APM ∥ Logs Pipelines ∥ AI Team
        join = entityId       join = tags          join = OTel/OCSF (Public)
        map = typed write     map = APM-derived    map = eBPF at Node (Public)
        lake = Grail          backend = Metrics∥Husky  index of processed + optional fan-out

        Detect → Event        Door A ∥ Door B      Pattern Anomaly + Thresholds
        Davis → Problem       Flamegraph leaf      AI Team → Issue + Overview
          (default package)   Bits optional          Team standing; Issue may be 0
```

---

## 1. Pattern lens — `F → T → D` (after native reading)

Shared stage names are a **compare lens**, not either vendor’s product model. Read §0 first.

**Quick acronyms (5 + 3 + 3):**

| Acronym | Phase | Stages |
|---------|-------|--------|
| **F** | **Fabric** (always-on) | Collect → Normalize → Topology bind → Fan-out → Maintain |
| **T** | **Triage** (per incident) | Detect → Curate → Tailor |
| **D** | **Diagnose** (per case) | Localize → Identify → Package |

**Phase outputs (compare-lens contracts):**

| Phase | Output | Elements (abstract) | Fundamental question |
|-------|--------|---------------------|----------------------|
| **F · Fabric** | **Estate** | `join keys + topology + evidence stores + freshness baseline` | Is the world written and walkable before alert? |
| **T · Triage** | **Working set** | `seed + time + candidate CIs` | What space ∩ time are we diagnosing? |
| **D · Diagnose** | **Verdict card** | `leaf claim + corroboration + operator handoff` | What can on-call act on without re-diagnosing? |

Element lists are **as many parts as the job needs** — not forced to match stage count or align across phases. Vendor geometry lives inside the elements, not the phase name.

**Workflow (conceptual):** [`assets/fcd-focusing.svg`](./assets/fcd-focusing.svg) — *Estate → Seed → Leaf* · rendered on [`comparable-pipeline-dt-dd.html`](./comparable-pipeline-dt-dd.html)#fcd-overview

Stage-by-stage I/O tables below remain the precise reference; the diagram is the mental model.
### Volatility — high → low (F → T → D)

**Yes.** Volatility falls as you move right:

| Phase | Volatility | Why |
|-------|------------|-----|
| **F · Fabric** | **High** | Continuous high-rate writes (spans, metrics, logs, map upserts) |
| **T · Triage** | **Medium** | Episodic signals; storm then merge into a seed |
| **D · Diagnose** | **Low** | Locked working set — candidates + time corridor change slowly until close |

Do not confuse volatility with importance: **D** is where the leaf claim is made.

### F · Fabric — always-on (5)

Continuous path. Output of F is an **estate** — not an incident. Four abstract parts:

#### Estate elements

| Element | Meaning |
|---------|---------|
| **Join keys** | Shared identity + time axis on every record so modalities about the same workload can correlate. Without this → orphan telemetry. |
| **Topology** | Walkable structure: who connects to whom / runs where — neighbors and edges queryable before an alert. Map ≠ leaf. |
| **Evidence stores** | Durable persisted telemetry history (however many planes) addressable by join keys. Later stages **read** stores; they do not re-collect the company per alert. |
| **Freshness baseline** | Retention, indexes, discovery, deploy/version feed — estate trusted enough for Detect to run. Stale fabric → wrong baseline. |

**Acid test:** given a workload identity and a UTC window, can you pull multimodal history *and* walk neighbors without re-instrumenting? If yes, Fabric worked.

#### What “joinable, queryable” adds (teaching shorthand)

| Shorthand | Maps to |
|-----------|---------|
| **Joinable** | Join keys present and consistent |
| **Queryable** | Topology + evidence stores written |
| **Detect-ready** | Above + freshness baseline you can trust |

| Stage | Contribution to estate element |
|-------|-------------------------------|
| **Collect** | Raw intake — estate elements not built yet |
| **Normalize** | **Join keys** (+ failure cues) |
| **Topology bind** | **Topology** |
| **Fan-out** | **Evidence stores** (+ topology persistence where map is a write facet) |
| **Maintain** | **Freshness baseline** on join keys, topology, and stores |

| Stage | Common job | Input → Output | Dynatrace | Datadog |
|-------|------------|----------------|-----------|---------|
| **Collect** | Edge intake only — no RCA yet | **In:** host/app/log/stats signals → **Out:** near-raw payloads at Agent | OneAgent / OTLP → tenant | Agent + `ddtrace` + DogStatsD + log tails → HQ |
| **Normalize** *(Identity)* | Stamp join keys so modalities correlate | **In:** raw → **Out:** join-ready records (tags and/or entity id) + failure cues | Enrichment · failure label · entity prep → `entityId` | Unified Service Tags (`service`·`env`·`version`·host) · span status/HTTP |
| **Topology bind** | Make the call path walkable; Map ≠ leaf | **In:** discovery + peer/call cues → **Out:** neighbors + edges | Smartscape + Bind LUT → stamp `entityId` | Catalog + APM Service Map / `peer.hostname` (derived) |
| **Fan-out** | Persist continuous evidence plane(s) | **In:** join-ready records → **Out:** durable map facet ∥ evidence facet(s) | **Dual-track:** Smartscape ∥ Grail | **Three-rail:** Metrics ∥ APM ∥ Logs (Metrics store ∥ Husky); map mostly APM-derived |
| **Maintain** | Keep fabric Detect-ready (retention, index, discovery, deploy feed). Does not pick RC | **In:** written stores → **Out:** fresh indexes / warm catalog | Named stage: Grail lifecycle + Smartscape freshness | **No named Maintain** — continuous **03 Write** + product retention/indexing (remap) |

**F contract:** continuous joinable evidence + walkable neighbors. **Not common:** dual-track vs three-rail geometry; named Maintain on Datadog.

### T · Triage — per incident (3)

Something crossed a line. **Triage** is the one-word phase name (in sync with Fabric and Diagnose): sort what fired, merge to one seed, lock scope. Output of T is a **working set** — `seed + time + candidate CIs` — still not a verdict card. (Our HLD still labels this block E2 “Case opens”; Datadog product stage 06 is also named Triage — same spirit, wider phase here.)

#### Working set elements

| Element | Meaning |
|---------|---------|
| **Seed** | Primary tip from Curate: the entity/service (or symptom locus), incident start (`t0`), and Detect class — *where to start*, not the leaf. |
| **Time** | Locked UTC corridor (and often compare/baseline window) for everything downstream. |
| **Candidate CIs** | Configuration items / services / hosts in scope for Localize — the space half of space ∩ time. |

| Stage | Common job | Input → Output | Dynatrace | Datadog |
|-------|------------|----------------|-----------|---------|
| **Detect** | Emit fault *signals* for a Detect class. Write ≠ Detect. Signal ≠ leaf | **In:** fabric under join keys → **Out:** Events / alerts / stories | Detectors → **Event** objects | Door A **Monitors** ∥ Door B **Watchdog** (independent; can be empty while Write is loud) |
| **Curate** | Collapse related signals into **one case seed** | **In:** signal storm → **Out:** seed `(primary, t0, class)` | Davis merges nearby Events (strong) | Thin/absent auto-seed; FE/PRD/INV can all look hot; operator/Bits often seeds |
| **Tailor** *(Scope)* | Lock space ∩ time for diagnosis | **In:** seed → **Out:** working set = `seed + time + candidate CIs` | Smartscape neighborhood + Grail DQL cut | Operator/Bits scopes env/version/time + Related |

**T contract:** signals → (ideally) one seed → locked working set. Hardest gap: DD auto-Curate weak; empty Detect still allows Triage if an operator chooses a window (SLOWDOWN).

### D · Diagnose — per case (3)

Runs on Tailor’s working set. Lowest volatility — the cut is fixed. Output of D is a **verdict card** — `leaf claim + corroboration + operator handoff` — not raw explorer panes alone.

#### Verdict card elements

| Element | Meaning |
|---------|---------|
| **Leaf claim** | Named locus where work failed or burned time — by Detect-class rule. Answers *where* (deepest fault **or** longest self-time). |
| **Corroboration** | Multimodal evidence under the same join keys supporting the leaf — ranked, tagged, or narrated. Answers *why you believe it*. |
| **Operator handoff** | Shareable packaged artifact on-call can act on without re-running Localize/Identify. Vendor policy varies; element exists either way. |

**Acid test:** can on-call act from the handoff without re-diagnosing? Vendor skins (Problem, Bits, Incident, thin card) are implementations of **operator handoff**.

| Stage | Common job | Input → Output | Dynatrace | Datadog |
|-------|------------|----------------|-----------|---------|
| **Localize** | Name the **leaf** by Detect class (deepest error **or** longest self-time) | **In:** working set → **Out:** leaf claim | Smartscape walk; `rootCauseEntity` may be null | Flamegraph leaf (operator/Bits); no `rootCauseEntity` field |
| **Identify** | Corroborate leaf with multimodal evidence | **In:** leaf claim + scoped evidence → **Out:** corroboration | `rootCauseRelevant` ranking on Grail + Events | Tag join across rails; Bits Hypothesis Tree optional |
| **Package** *(Verify)* | Emit operator verdict (default or optional policy) | **In:** leaf + corroboration → **Out:** verdict card = `leaf claim + corroboration + operator handoff` | **Problem** — default handoff | **Bits** optional handoff · **Incident** often 0; thin handoff from leaf + MTL alone |

**D contract:** leaf rule by class → corroboration → **verdict card**. Policy fork: DT packages by default; DD often optional Package.

### Distilled I/O spine

Each row names **X** (input artifact) and **Y** (output artifact) abstractly — vendor mechanics sit inside the transform.

| Stage | X (input) | Y (output) |
|-------|-----------|------------|
| **F Collect** | **Edge bytes** — host/app/container/log/stats telemetry at the platform boundary, vendor-shaped | **Near-raw intake** — payloads accepted at edge; not join-ready |
| **F Normalize** | Near-raw intake | **Join-ready records** — stamped join keys (+ failure cues); builds estate **join keys** |
| **F Topology bind** | Join-ready records + discovery/peer cues | **Topology slice** — walkable neighbors + edges; builds estate **topology** |
| **F Fan-out** | Join-ready records (+ topology cues) | **Persisted planes** — durable evidence stores (+ map facet where written); builds estate **evidence stores** |
| **F Maintain** | Persisted planes (stores + topology) | **Detect-ready estate** — join keys + topology + evidence stores + freshness baseline |
| **T Detect** | Detect-ready estate | **Fault signals** — Detect-class signal objects (alert/Event/story); not leaf, not case |
| **T Curate** | Fault signals (storm in time/topo neighborhood) | **Seed** — primary tip: locus + `t0` + Detect class |
| **T Tailor** | Seed | **Working set** — `seed + time + candidate CIs` |
| **D Localize** | Working set | **Leaf claim** — named locus where work failed or burned time |
| **D Identify** | Leaf claim (+ estate evidence scoped to working set) | **Corroboration** — multimodal evidence bundle supporting the leaf |
| **D Package** | Leaf claim + corroboration | **Verdict card** — `leaf claim + corroboration + operator handoff` |

**Phase handoffs:** F → estate · T → working set · D → verdict card.

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

1. **Independent first** — finish DT, DD, and ED unveils on each vendor’s own terms; this page is for **derived** patterns, not a twining template. Same-scenario lab remains DT vs DD.
2. **Same destination** — name the root of a cascade with evidence; **three geometries** — DT dual-track (Smartscape ∥ Grail); DD three-rail (Metrics ∥ APM ∥ Logs) + Husky + APM-derived Service Map; ED dual-layer (Telemetry Pipelines ∥ AI Team). Dual-layer ≠ Dual-track.
3. **Processing locus** — DT and DD **centralize-then-analyze**; ED **shifts processing left**. Same locus ≠ same geometry. Composition follows: left-shifted hygiene can feed a centralized analyzer.
4. **Do not equate** Problem ↔ Incident ↔ Issue, Smartscape ↔ Service Map ↔ ED Service Map, Grail ↔ Husky ↔ ED Platform, Dual-track ↔ Three-rail ↔ Dual-layer, Davis ↔ Bits ↔ AI Team, Event ↔ Watchdog story ↔ Pattern Anomaly.
5. **Fabric is not the only wedge** — collect/map/evidence work on all three; a second wedge is **merge → package** (DT strong / default; DD thin unless Bits/Incident; ED Team is standing but Issue can still be **0** while stores are empty).
6. **AI geometry, not AI volume** — Datadog shows more **separable** AI surfaces (Watchdog + Bits); Dynatrace runs AI as the **Davis packaging engine**; Edge Delta runs AI as a **standing Team** with human-in-the-loop actions. None is “more AI” as a blanket claim (§0.4). HLD **D5** stays Review.
7. **Detect categories are not twin lists** — Dynatrace `event.category` (ERROR · SLOWDOWN · …) ≠ Datadog `monitor_pack` / Watchdog `apm|infrastructure|logs` ≠ ED Event Threshold / Pattern Anomaly / Metric Threshold. Observed Host+APM packs = **11 templates** on one screen, not a Davis taxonomy (§0.5).
8. **Composition vs peer** — DT and DD are full-stack peers. ED is a peer *and* can sit **in front of** them as a destination (**Public framing**). This tenant does not.
9. **Gaps to own in our design:** explicit Curate (storm → one seed), investigation cut contract, and whether Package is mandatory or optional — lab shows optional packaging can leave a clear fault **unpackaged**; ED snapshot shows a loud Detect/Team surface over empty E4 stores.

---

## 8. Related

| Doc | Role |
|-----|------|
| [`dt-davis-category-hub.html`](./dt-davis-category-hub.html) | DT hub (independent) |
| [`dd-detect-category-hub.html`](./dd-detect-category-hub.html) | DD hub (independent) |
| [`ed-ai-team-hub.html`](./ed-ai-team-hub.html) | ED hub (independent) |
| [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) · [HTML](./dynatrace-production-pipeline.html) | DT unveil |
| [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md) · [HTML](./datadog-production-pipeline.html) | DD unveil |
| [`EDGEDELTA_PRODUCTION_PIPELINE.md`](./EDGEDELTA_PRODUCTION_PIPELINE.md) · [HTML](./edgedelta-production-pipeline.html) | ED unveil |
| [`edgedelta-tenant-evidence-2026-08-14.md`](./edgedelta-tenant-evidence-2026-08-14.md) | ED Observed (UI) snapshot |
| [`dt-e2e-smartscape-grail.html`](./dt-e2e-smartscape-grail.html) | DT Dual-track Smartscape ∥ Grail |
| [`dd-e2e-metrics-traces-logs.html`](./dd-e2e-metrics-traces-logs.html) | DD Three-rail Metrics ∥ APM ∥ Logs |
| [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) | DT mechanisms (Davis) |
| [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html) | DD mechanisms |
| [`dd-bits-error-review.html`](./dd-bits-error-review.html) | DD Bits peer tab (Hypothesis Tree · 500 vs 502) |
| [`datadog-lab-evidence-mtl-error-2026-08-10.html`](./datadog-lab-evidence-mtl-error-2026-08-10.html) | DD e3 MTL appendix |
| [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md) | Earlier DD notes |
| [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) | No public top-1 AI bakeoff |
| [`index.html`](./index.html) · [`:8765/docs.html`](http://127.0.0.1:8765/docs.html) | Docs hub |
