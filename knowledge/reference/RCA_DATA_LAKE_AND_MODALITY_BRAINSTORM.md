# RCA data plane — team reference (problem, clocks, modalities, competitors)

**Audience:** engineers and PMs who need a shared vocabulary for ingest + RCA design (no prior PoC context required).  
**Status:** working hypotheses / design reference — **not** a measured industry survey or accuracy claim.  
**Date:** 2026-07-31 (team reference: Clock A/B · classes A–E · Grail/Smartscape/Vector · Fed tiers)  
**Honesty label:** competitor mechanics from **public product framing + our vendor notes** (self-reported where noted). Percentile bands are **planning priors**, not published measurements.

**Also available as:**

**Browser HTML:** [`rca-data-lake-brainstorm.html`](./rca-data-lake-brainstorm.html) · PoC console [http://127.0.0.1:8765/rca-data-lake-brainstorm.html](http://127.0.0.1:8765/rca-data-lake-brainstorm.html)  
**Clock A/B stage cards:** [`clock-ab-stage-reference.html`](./clock-ab-stage-reference.html)

**Related (deeper):** [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) · [`RCA_Vendor_Comparison_NOTES.md`](./RCA_Vendor_Comparison_NOTES.md) · [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) · [`federated-pipeline/docs/STORAGE_TIERS.md`](../../federated-pipeline/docs/STORAGE_TIERS.md) · [`federated-pipeline/docs/ARCHITECTURE.md`](../../federated-pipeline/docs/ARCHITECTURE.md) · [`labs/dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md`](../../labs/dynatrace-rca-lab/DYNATRACE_RCA_REFERENCE.md) · PDF [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf)

---

## How to read this document

1. Start with **§G Glossary** if terms like Clock A, class C–D, or CI are unfamiliar.  
2. **§1** defines the problem; **§2** lists constraints we design against (once).  
3. **§3** is **Clock A vs Clock B** — the most important structural idea. **§3.2b** = step I/O; **§3.6** = Federated tiers.  
4. **§4–§5** are how vendors and we cope; **§6** is Grail / Smartscape / Vector.  
5. **§7** defines **scenario classes A–E** (this is what “class C–D” means).  
6. Later sections deepen modalities, Detect/seed, and lake lifecycle.

---

## 0. Document map

| Section | Contents |
|---------|----------|
| **§G** | Glossary (Clock A/B, class A–E, CI, seed, Tailor, …) |
| **§1** | Problem definition + RCA jobs |
| **§2** | Production constraints |
| **§3** | **Clock A/B** · §3.2b step I/O · **§3.6 Federated tiers** |
| **§4** | How competitors cope |
| **§5** | How we solve it |
| **§6** | Grail · Smartscape · Vector |
| **§7** | **Scenario classes A–E** (modality priors) |
| **§8** | What each data type answers |
| **§9** | Detect vs symptom seed |
| **§10** | Lake lifecycle (create → … → churn) |
| **§11** | Open questions · takeaway |

---

## G. Glossary (read this first)

Terms used throughout. Bold = used constantly.

### G.1 Two clocks (structural)

| Term | Meaning |
|------|---------|
| **Clock A** | The **continuous platform / ingest / lake** timeline: collect telemetry, normalize it, keep topology fresh, store/retain, and — when an incident starts — **tailor** a small working set. Runs all the time, whether or not anyone is debugging. |
| **Clock B** | The **per-incident diagnosis** timeline: after Tailor, **Localize → Identify → Verify** for that case. Starts and ends with an incident. |
| Why “clock”? | Metaphor only: two different cadences. Do **not** mix “we need a better lake” (Clock A) with “our Localize missed the root” (Clock B) in the same discussion without saying which clock you mean. |

**One-line:** Clock A prepares joinable data; Clock B reasons about one fault.

```
Clock A (always on)          Clock B (per incident)
─────────────────────        ────────────────────────
Collect / Normalize          Localize
Topology / Fan-out / Maintain Identify
Detect → Curate → seed       Verify
Tailor ────────────────────►
```

### G.2 RCA jobs (Clock B)

| Term | Meaning |
|------|---------|
| **Ingest** | Make signals joinable by **identity + time** (usually Clock A; listed first in the end-to-end chain). |
| **Detect** | Decide that something is wrong *now*, and where pain shows. Emits anomalies / alerts. |
| **Symptom seed** | The (CI, signal, time) where Localize **starts**. Usually a **symptom**, not the root cause. |
| **Localize** | Find which **CI / service** is the fault *region* (Step 1 “where”). |
| **Identify** | Name the **kind** of failure (signature / fault class), and optionally the **execution path** (Step 2). |
| **Verify** | How strongly we may claim cause (evidence depth / confidence tiers — not marketing “causal”). |
| **Step 1** | Market shorthand ≈ Detect → Localize (“where”). Vendors automate this relatively well. |
| **Step 2** | Market shorthand ≈ Identify (+ Verify) (“what happened there”). Deep path-diff automation is still thin industry-wide. See [`two-step-rca-white-space.md`](./two-step-rca-white-space.md). |

### G.3 Entities, topology, scoping

| Term | Meaning |
|------|---------|
| **CI** | Configuration Item — a typed node we reason about (service, VM, datastore, switch port, …). |
| **Topology / CI graph** | Typed nodes + edges Localize walks (calls, hosted_on, uses_datastore, …). Not a request trace. |
| **Neighborhood / k-hop** | CIs within *k* graph edges of the seed (and often shared-upstream infra). |
| **Time corridor** | Window around onset, e.g. *[t0 − pre, t0 + post]* — not “search last 7 days of the lake.” |
| **Tailor** | Clock A step that builds the **incident working set**: seed + neighborhood + corridor + modalities. |
| **Working set / incident kit** | The small pack Localize/Identify actually see. |
| **Fan-out** | Write cheap vs rich sinks from the same normalized stream (cost control; same Detect). |

### G.4 Scenario classes A–E (modality mix)

These are **planning buckets** for “what data do we need?” — **not** product SKUs and **not** ObserveOps UC numbers.

| Class | Short name | Typical story | Logs? | Traces? |
|-------|------------|---------------|-------|---------|
| **A** | Classic infra smoking gun | Host CPU, link down, datastore saturation — clear shared-upstream | Often **not** needed for Localize | Usually not |
| **B** | Metrics-led, thin events | Multi-signal onset; need topology walk + timing | Recommended | Optional |
| **C** | App / dependency gray | 5xx, latency, pool exhaustion — “slow somewhere” | **Necessary** for Identify | Recommended |
| **D** | Path / microservice | Wrong hop, dependency timeout, cross-layer path | Necessary | **Necessary** for path Identify |
| **E** | Outside organic RCA | Pure security, capacity planning, process | Often not RCA-engine territory | — |

**“Class C–D”** in this doc = incidents that usually need **logs** (and for D, **traces/spans**) for trustworthy Identify — not metrics+topology alone.

Full detail: **§7**.

### G.5 Vendor / platform terms

| Term | Meaning |
|------|---------|
| **OneAgent** | Dynatrace edge agent (capture + enrichment). |
| **Smartscape** | Dynatrace **live topology graph** (entities + relationships). Fed by discovery/OneAgent — **not** by DQL against Grail. |
| **Grail** | Dynatrace **unified lake + DQL query** for metrics/logs/traces/events by entity + time. |
| **Davis** | Dynatrace thin RCA / Problem layer on top of Smartscape + Grail + detectors. |
| **Watchdog** | Datadog-style anomaly / outlier detection used as Detect signal. |
| **Vector** | Our (and industry) **telemetry pipeline**: collect → transform → route (OTel/Fluent Bit family). **Not** a lake. |
| **DQL** | Dynatrace Query Language — how consumers **read** Grail. |

### G.6 Other

| Term | Meaning |
|------|---------|
| **GT** | Ground truth — human-labeled root / fault for scoring. Must **not** leak into alert text (“coaching”). |
| **Gray-failure Detect** | Soft unhealthiness without hard thresholds; optional Detect upgrade. |
| **Modality** | A data type: metrics, logs, traces/spans, events/changes, alerts, topology. |
| **Tier 1 / Event Graph** | Federated **speed tier** (Dragonfly): high-velocity traces/metrics/patterns — “what/when.” See §3.6. |
| **Tier 2 / Knowledge Graph** | Federated **structural tier** (Vortex/DashMap design): persistent topology + properties/LOS — “who/why.” See §3.6. |
| **Panorama / Murphy / Nezha** | Federated hops ≈ Detect (gray) / Localize (macro) / Identify (path). See §3.6. |

---

## 1. What is the problem?

### 1.1 One-sentence problem

**Given noisy, high-volume, multi-modal telemetry and a shifting estate, automatically (or assistively) answer: what is wrong, where is the fault, and—when justified—why, with an evidence trail an SRE can trust.**

### 1.2 End-to-end jobs

```
Ingest → Detect → Localize → Identify → Verify
```

| Job | Plain question | Failure mode if skipped | Typical clock |
|-----|----------------|-------------------------|---------------|
| **Ingest** | Can we join signals by identity + time? | Orphan metrics/logs; no walk | Mostly **A** |
| **Detect** | Is something wrong *now*, and where does pain show? | No case start / wrong seed | **A** (opens case; Curate → seed) |
| **Localize** | Which CI / service is the fault region? | Blame the loud symptom app | **B** |
| **Identify** | What *kind* of failure (and optionally which path)? | “Host X bad” with no actionable class | **B** |
| **Verify** | How strongly may we claim cause? | Marketing “causal” without evidence depth | **B** |

Market shorthand:

- **Step 1 “where”** ≈ Detect → Localize.  
- **Step 2 “what happened there”** ≈ Identify (+ Verify).

### 1.3 Why a “bigger lake” alone is not the solution

Raw production data is:

- **Huge** — metrics × hosts × minutes; log lines; sampled spans  
- **Heterogeneous** — infra vs app vs change events  
- **Non-stationary** — deploys change topology  
- **Identity-unstable** — pods churn; monitors rename  

So the systems problem is not “store everything.” It is:

> **Create an entity-keyed, time-aligned store; then, per incident, tailor a small working set (seed + neighborhood + corridor) that Localize/Identify can reason over.**

Datadog/Dynatrace-class products optimize for that operationally. Any serious RCA stack needs: **normalized streams + scoped working sets**, not full-retention diagnosis.

---

## 2. Constraints (design against these once)

These are **hard facts of production telemetry**, not a product pitch. Later sections assume them.

| Constraint | Plain meaning | What design must do |
|------------|---------------|---------------------|
| Volume / cardinality | Too many series, log lines, spans to keep or scan raw | Sample, tier retention, cheap vs rich fan-out |
| Identity + fresh topology | Hosts/pods/services rename and redeploy | Stable CI ids + an up-to-date dependency graph |
| Detect / seed quality | RCA starts from “something is wrong *here*” | Reliable Detect → symptom seed |
| Symptom bias / correlation≠cause | Loud apps look guilty; “moved together” ≠ root | Topology-aware Localize + honest Verify depth |
| Modality gaps + Step-2 hole | Some faults need logs/traces; deep path “why” is thin | Pull the right modalities for the **class**; don’t overclaim path Identify |

**How to read §3 onward:** answers to *how systems cope with this table* — not another pain catalog.

---

## 3. Clock A and Clock B (thorough)

This section is the shared mental model for the team.

### 3.1 Definitions

| | **Clock A — Ingest / lake ops** | **Clock B — RCA case** |
|--|--------------------------------|------------------------|
| **Question** | Is our estate joinable and incident-ready? | For *this* incident, where is the fault and what kind is it? |
| **Cadence** | Continuous (seconds–minutes forever) | Sparse (when Detect fires) |
| **Stages** | Collect · Normalize · Topology · Fan-out · Maintain · **Detect** · **Curate** · **Tailor** · Churn | **Localize** → **Identify** → **Verify** |
| **Primary outputs** | Normalized envelopes, CI graph, sinks, incident kits | Root CI, signature, evidence, confidence language |
| **Failure looks like** | Orphans, stale topo, cost blow-ups, un-scoped dumps | Wrong root, symptom bias, overclaiming “causal” |
| **Who “owns” it in Dynatrace-shaped stacks** | OneAgent, Smartscape, Grail, retention/sampling | Detectors + Davis (thin) |
| **Who “owns” it in our design** | Vector-class pipeline + topo sibling + sinks/builders | Shared Detect + Localize/Identify engines + Verify tiers |

**Ingest is not RCA.** Collecting and storing well does not localize a fault. Localizing well does not invent missing topology.

### 3.2 How the clocks connect

```
CLOCK A (continuous)
  Collect → Normalize → Topology bind → Fan-out → Maintain
                              │
                              │  Detect watches streams / stores
                              ▼
                         raw alerts (often a storm)
                              │
                              │  Curate (storm → one honest seed)
                              ▼
                         symptom seed (CI, signal, t0)
                              │
                              │  Tailor (still Clock A ops, triggered by case)
                              ▼
              working set = neighborhood + time corridor + modalities
                              │
                              ▼
CLOCK B (this incident)
              Localize → Identify → Verify → (human / ticket)
```

**Tailor** is the bridge: still “data ops,” but **incident-triggered**. Without Tailor, Clock B either sees nothing useful or sees the whole lake (and fails §2 volume).

### 3.2b Clock A step-by-step — input → process → output

Read this as a **pipeline of contracts**. Some stages run **in parallel** (topology beside collect); case sequencing is **Detect → Curate → Tailor**; Tailor is **case-triggered Clock A**.

```
Continuous (always on):
  Collect → Normalize ─┬─► Fan-out → Maintain  (stores stay healthy)
                       │
 Topology discovery ───┘   (CI graph + bind LUT; sibling path)

Case handoff (Clock A):
  Detect → raw alerts
  Curate → one honest symptom seed (CI, signal, t0)
  Tailor(seed) → incident working set → Clock B
```

#### 1. Collect

| | |
|--|--|
| **Input** | Raw telemetry from the estate: Prometheus scrapes, syslog, traps, OTel spans/logs, agent metrics, change/deploy feeds, vendor APIs, replay files |
| **Process** | Agents / collectors / Vector **sources** pull or receive bytes; optional light filter (drop noise, TLS terminate). **No** RCA yet |
| **Output** | Raw (or lightly framed) events on a bus / file / Vector internal stream — still vendor-shaped, often **without** stable `ci_id` |

#### 2. Normalize

| | |
|--|--|
| **Input** | Collect output (raw / semi-raw events) |
| **Process** | Map each event into a **joinable envelope** (our `ingest.v1`-class contract): stable fields such as `ts` (UTC), `ci_id` (or a key that *will* bind), `signal`, `value`, optional threshold / severity / modality tags. Drop or quarantine malformed rows |
| **Output** | Normalized stream — same *meaning* across sources so later stages can join by **identity + time** |

Without Normalize, Fan-out and Detect see incompatible schemas; Localize cannot hang metrics/logs on one CI.

#### 3. Topology bind (CI graph + identity)

**Yes — this is the relationship / dependency graph** Localize will walk (and that Tailor will slice). It is **not** a request trace.

| Piece | What it is |
|-------|------------|
| **CI (node)** | Typed entity: service, pod, VM, host, datastore, switch port, … |
| **Edge** | Typed relationship: `calls`, `hosted_on`, `runs_on`, `uses_datastore`, `uplink`, … |
| **Bind LUT** | Map messy labels (IP, hostname, K8s name) → stable `ci_id` used in Normalize |

| | |
|--|--|
| **Input** | Discovery / CMDB / service-map crawler cues (and optionally call-edge hints from APM); parallel to Collect, not “after all metrics arrive” |
| **Process** | Build/refresh the **typed CI graph**; publish bind table so Normalize can resolve `ci_id`; mark edges with direction useful for upstream/downstream walks |
| **Output** | Snapshot graph (`topology.json` / `A-TOPO` / Smartscape analogue) + bind LUT consumed by Normalize and later Tailor/Localize |

**Granularity reminder:** coarse enough for stable ticket IDs; fine enough that the true fault CI is a **node**; refresh on deploy/discovery.

#### 4. Fan-out — what it means

**Fan-out = write the *same* normalized stream to one or more sinks/profiles without forking Detect.**

It is **not** “split the RCA algorithm.” It is **cost / consumer routing**:

| Profile (example) | What gets written | Why |
|-------------------|-------------------|-----|
| **Cheap (L0)** | Lean-oriented incident bundles / metric slices needed for classic Localize | Lower store + query cost |
| **Rich (F1)** | + structural / speed-tier feeds (Fed Dragonfly `tg:`/`pc:`, KG slice, richer modalities) | Enable Murphy/Nezha / class C–D depth when paid for |

| | |
|--|--|
| **Input** | Normalized envelopes (+ topology available for bind) |
| **Process** | Vector (or Python stand-in) **routes** events to configured sinks — file, Dragonfly, structural store, Lean bundle writer. Same Detect watches the shared logical stream |
| **Output** | Populated stores / bundles ready for Maintain and Detect; **one** Detect path remains shared for fair engine compare |

#### 5. Maintain — how it works

**Maintain = keep the estate usable over time** (lifecycle), continuous.

| Concern | What happens |
|---------|----------------|
| **Identity** | Prefer service/host keys over ephemeral pod names when pods churn |
| **Topology freshness** | Rebuild/patch graph on discovery/deploy; stale edges → wrong walks |
| **Retention tiers** | Hot (recent incident windows) / warm / cold; drop or downsample what Tailor will never need |
| **Sampling** | Traces/logs: keep decisive coverage under cost caps |
| **Clock sync** | Shared time base so “onset” across modalities is comparable |

| | |
|--|--|
| **Input** | Fan-out sinks + live topology updates |
| **Process** | TTL, compaction, resample, re-index, re-crawl; ops policies — mostly automated |
| **Output** | Healthy hot/warm stores + fresh graph that Detect/Tailor can query |

#### 6. Detect (watches streams/stores) — opens the case

Detect sits on the **boundary**: feeds on Clock A data; **opens the case** (raw alerts still need Curate).

| | |
|--|--|
| **Input** | Normalized metrics/events (and optionally LOS / baselines) from Maintain’d stores or live streams |
| **Process** | Thresholds / SLOs / Watchdog-class / (optional) Panorama gray-failure: mark “crossed” anomalies; emit **raw alerts** (often several per real incident) |
| **Output** | Raw alert storm — usually **not** yet one honest seed |

```
alert examples (one incident):  orders-api latency · orders-api errors · db pool depth …
```

#### 7. Curate — storm → one honest seed

**Curate = quality and labeling discipline** (not the same as Maintain). On the live path it sits **on Detect’s raw output**.

| Concern | What happens |
|---------|----------------|
| **Storm control** | Many alerts → one logical case / one primary seed |
| **Human GT** | Labeled kits for scoring; never auto-invent GT |
| **Quality flags** | Mark missing topo / traces / logs so reports stay honest |
| **No coaching** | Keep root/GT text **out** of alert bodies |
| **Gold set** | Held-out multimodal incidents for Identify / report quality |

| | |
|--|--|
| **Input** | Detect’s raw alerts + historical incidents + human labels |
| **Process** | Dedup/correlate storms; attach quality metadata; GT workflow |
| **Output** | **One honest symptom seed** `(ci_id, signal, t0)` + scorable packs / explicit gaps |

```
seed example:  orders-api , request.p95_latency_ms , 2026-07-28T07:19:30Z
```

#### 8. Tailor — cut the incident working set

**Tailor is case-triggered Clock A.** Input is the **seed** plus the maintained lake/graph; output is everything Clock B is allowed to see.

| Knob | Meaning | Typical process |
|------|---------|-----------------|
| **Neighborhood / k-hop** | CIs within *k* edges of the seed (and often **shared-upstream** infra: host, datastore, uplink) | Graph walk/BFS on topology from `seed.ci_id`; include typed up/downstream |
| **Time corridor** | Window around onset: `[t0 − pre, t0 + post]` | Query stores only in that window — **not** “last 7 days of the lake” |
| **Modality mix** | Which data types to pull (class A–D) | A–B: metrics (+ thin events); C: +logs/change; D: +traces/spans |
| **Working set / kit** | Seed + neighborhood + corridor + modalities | Pack files / query results / F1 slices handed to engines |

| | |
|--|--|
| **Input** | Symptom seed + CI graph + Maintain’d stores (+ Curate flags) |
| **Process** | Expand k-hop neighborhood → pull modalities in time corridor → assemble pack; drop entities/times outside the cut |
| **Output** | **Incident working set** → **Clock B** (Localize → Identify → Verify) |

```
Incident working set =
    seed
  + neighborhood (k-hop / shared-upstream slice of CI graph)
  + time corridor [t0 − pre, t0 + post]
  + modalities (metrics, and logs/traces/change as class requires)
```

**Your guess is right:** neighborhood + time corridor + modality pull **are** the Tailor cut; that cut **is** the input to Clock B.

#### Compact I/O chain

| Step | In | Out |
|------|----|-----|
| Collect | Raw sources | Raw streams |
| Normalize | Raw streams | Entity envelopes (`ci_id`, signal, `ts`, …) |
| Topology bind | Discovery | CI **relationship/dependency graph** + bind LUT |
| Fan-out | Envelopes | Cheap and/or rich **sinks** (same Detect) |
| Maintain | Sinks + graph | Fresh, retained, sampled stores |
| Detect | Streams/stores | Raw alert storm |
| Curate | Raw alerts + humans | **One honest seed**, quality flags, GT |
| Tailor | Seed + graph + stores | **Working set** → Clock B |

### 3.3 What belongs on which clock (examples)


| Discussion | Clock | Example |
|------------|-------|---------|
| “Vector remaps Prometheus → entity envelope” | **A** | Collect + Normalize |
| “topology.json missing datastore edge” | **A** | Topology |
| “L0 vs F1 sinks cost too much” | **A** | Fan-out / Maintain |
| “threshold Detect never fired” | **A** (opens the case) | Detect |
| “storm never became one seed” | **A** | Curate |
| “engine blamed checkout-api; root was datastore” | **B** | Localize |
| “we need stack traces for pool exhaustion” | **B** + class **C** | Identify modalities |
| “UI said ‘root cause proven’ on weak evidence” | **B** | Verify |

### 3.4 Industry names for Clock A stages

| Our word | Classical / industry name |
|----------|---------------------------|
| Collect + Normalize | Observability / telemetry pipeline (OTel, Vector, Fluent Bit) — ETL/ELT family |
| Topology + CI bind | Discovery + CMDB / service inventory + **entity / identity resolution** |
| Maintain | Data lifecycle (hot/warm/cold, cardinality, sampling) |
| Curate | Data quality (+ ITSM event correlation for alert storms) |
| Tailor | **Context assembly / incident scoping** (vendor: related entities, Smartscape slice) |
| Whole loop | Often marketed as “observability data platform” or “AIOps data prep” |

These are **old** problems (ITIL CMDB + events; ETL + DQ), reframed for multimodal AIOps. What is newer is volume + automated Localize on top.

### 3.5 Common confusion to avoid

| Confusion | Correction |
|-----------|------------|
| “Clock A vs Clock B are two products” | No — two **timelines / job families** in one system |
| “Grail is Clock B” | No — Grail is Clock A **store**; Davis is mostly Clock B |
| “Vector is our Grail” | No — Vector is Clock A **pipeline**; sinks/kits are a partial store |
| “Class C–D is a Clock” | No — class is an **incident modality bucket**; both clocks still apply |
| “Clock A = Event Graph, Clock B = Knowledge Graph” | No — **orthogonal axes**. Both tiers are written on A and read on B. See **§3.6**. |

### 3.6 Clocks vs Federated two-tier design

People often map Clock A/B onto Federated’s two graph tiers. The intuition is useful; the **1:1 equation is wrong**.

#### Plain reading (team shareable)

**Tier 1 / Tier 2** ≈ **where data lives** (Federated storage split: Event Graph vs Knowledge Graph), and therefore **which hop reads which store**. Storage-first axis.

**Clock A / Clock B** ≈ **workflow / job cadence**, not another storage layer:

- **Clock A** — continuous platform work + case bridge: collect → normalize → topo → fan-out → maintain → **Detect → Curate → Tailor**  
- **Clock B** — per-incident RCA algorithms: **Localize → Identify → Verify** 

Together, A then B (with **Tailor** as the bridge) is the end-to-end story. The clocks **use** the tiers; they aren’t the same kind of split.

```
Tier axis  →  Dragonfly (T1)  |  Vortex/DashMap (T2)     [storage / data plane]
Clock axis →  A: write/maintain both continuously
              B: Panorama/Murphy read T2; Nezha reads T1
```

**Bottom line:** tiers = data-plane layout; clocks = when work runs and which RCA/preprocess jobs run on that data. **Orthogonal, intersecting.**

#### Visual: orthogonality + relationship

Think of a **plane**, not a line. Horizontal = **where** (tiers). Vertical = **when / which job** (clocks). Each cell is a real write or read.

```
                        TIER AXIS (where data lives)
                        ─────────────────────────────────────────────►
                        Tier 1 Event Graph              Tier 2 Knowledge Graph
                        Dragonfly  tg: / pc:            Vortex CSR + DashMap LOS
                        “what / when” (paths)           “who / why” (topology)
                   ┌────────────────────────────┬────────────────────────────┐
     C             │                            │                            │
     L   Clock A   │  WRITE high-EPS            │  WRITE / UPDATE            │
     O   continuous│  traces → tg: timelines    │  CI edges → CSR            │
     C   platform  │  patterns → pc: counts     │  properties / LOS → DashMap│
     K             │                            │                            │
                   ├────────────────────────────┼────────────────────────────┤
     A             │                            │                            │
     X   Clock B   │  READ  Nezha               │  READ  Panorama (Detect)   │
     I   per       │  (path Identify /          │  READ  Murphy (Localize)   │
     S   incident  │   micro-localize)          │                            │
                   │                            │                            │
                   └────────────────────────────┴────────────────────────────┘
     │
     ▼  when / which job
```

**How to read it**

| Look at… | Means… |
|----------|--------|
| A **column** | One store; used on *both* clocks |
| A **row** | One job cadence; may touch *both* stores |
| A **cell** | Concrete operation (write or read) |
| The **whole grid** | Why “Clock A = Tier 1” is wrong — A fills *both* columns; B reads *both* (different hops) |

**Relationship (arrows), not identity:**

```
                    ┌──────────── Clock A (continuous) ────────────┐
                    │                                              │
   sources ──► normalize ──┬──► Tier 1 writes (tg:/pc:)            │
                           └──► Tier 2 writes (CSR / LOS)          │
                    │                                              │
                    │         Detect → seed                        │
                    │              │                               │
                    │         Tailor (scope working set)           │
                    └──────────────┼───────────────────────────────┘
                                   ▼
                    ┌──────────── Clock B (this incident) ─────────┐
                    │  Panorama/Murphy ◄── Tier 2                  │
                    │  Nezha           ◄── Tier 1                  │
                    │  fuse / Verify                               │
                    └──────────────────────────────────────────────┘
```

**Lean on the same clocks (no Fed dual tier):** Clock A still exists (kits + `topology.json`); Clock B is the typed CI walk — one “structural” column, no Event Graph column required for classic UC Localize.

**Docs:** [`federated-pipeline/docs/STORAGE_TIERS.md`](../../federated-pipeline/docs/STORAGE_TIERS.md) · [`ARCHITECTURE.md`](../../federated-pipeline/docs/ARCHITECTURE.md).  
**Honesty:** Vortex/DashMap/NATS-Rust at 1B EPS is **design vision**; PoC today uses in-memory structural + optional Dragonfly/Redis speed tier.

#### Two axes (do not collapse)

| Axis | What it partitions | Question |
|------|--------------------|----------|
| **Clock A vs Clock B** | **When / which job** | Continuous platform ops vs per-incident diagnosis |
| **Tier 1 vs Tier 2** | **Where data lives + which algo reads it** | Speed/event graph vs structural/knowledge graph |

- **Clocks** apply to **any** RCA stack (Lean packs + `topology.json` included).  
- **Two tiers** are the **Federated** scale design so high-EPS path data and deep topology reasoning don’t share one bottle.

#### What the Federated tiers are

| | **Tier 1 — Event Graph (speed)** | **Tier 2 — Knowledge Graph (structural)** |
|--|----------------------------------|-------------------------------------------|
| **Nickname** | “What” and “When” | “Who” and “Why” (topology / semantics) |
| **Role** | High-velocity traces, logs, metrics; temporal / per-request pattern material | Persistent microservice (and infra) topology; blast-radius traversals; heavy property updates |
| **Storage (design)** | DragonflyDB — time-bucketed ZSETs `tg:…`, sharded pattern HSETs `pc:…`, server-side Lua | Vortex/Arrow CSR (vectorized BFS) + DashMap LSM (lock-free properties / LOS) |
| **Primary Clock B consumers** | **Nezha** — expected vs actual path/pattern score | **Panorama** (LOS / gray Detect) · **Murphy** (MRF / Gibbs Localize) |

#### Intersection matrix (the useful picture)

```
                 Tier 1 Event Graph              Tier 2 Knowledge Graph
                 (Dragonfly — what/when)         (Vortex/DashMap — who/why)
                 ──────────────────────          ─────────────────────────
Clock A          Ingest traces/metrics           Update CSR topology,
(continuous)     into tg:/pc: keys               DashMap properties / LOS

Clock B          Nezha micro-localize            Panorama Detect (LOS)
(per incident)   (path / Identify)               Murphy macro-Localize
```

| Federated piece | Closer to… | Why |
|-----------------|------------|-----|
| Ingest → Dragonfly (`tg:` / `pc:`) | **Clock A → Tier 1** | Continuous high-EPS write path |
| Topology / property updates → CSR + DashMap | **Clock A → Tier 2** | Continuous Smartscape-like structural maintain |
| **Panorama** (bounded look-back on LOS) | **Clock B · Detect** (Fed-native; often gray-failure) | Case ignition from structural LOS |
| **Murphy** (CSR + Gibbs) | **Clock B · Localize** (macro “where”) | Walk Tier 2 graph |
| **Nezha** (Lua on Dragonfly) | **Clock B · Identify** (micro path) | Read Tier 1 patterns **after** Localize scopes the candidate |
| Fuse / evidence packaging | **Clock B · Verify** (in spirit) | Confidence / packaging of the hops |

**Tailor** (Clock A bridge) still applies: do not run Murphy/Nezha over the whole fleet forever — seed + neighborhood + corridor, then Clock B hops.

#### End-to-end flow in both languages

```
Clock A / Tier writes:
  Ingest (high EPS) ──► Dragonfly (Tier 1)
  Topology + LOS updates ──► Vortex/DashMap (Tier 2)

Clock B / hops:
  Panorama (Tier 2)  → Detect / gray seed          ≈ Detect
  Murphy (Tier 2)    → macro root service          ≈ Localize
  Nezha (Tier 1)     → broken execution path       ≈ Identify (path)
  fuse + evidence    →                             ≈ Verify (in spirit)
```

#### What *not* to equate

| Tempting 1:1 | Why it’s wrong |
|--------------|----------------|
| Clock A = Event Graph | Event Graph is also **Nezha on Clock B** |
| Clock B = Knowledge Graph | Knowledge Graph is also **maintained on Clock A**; Panorama/Murphy only *use* it on B |
| Tier 1 = “preprocess,” Tier 2 = “RCA” | Both tiers are **written on A** and **read on B** |
| Two clocks = only a Federated idea | Clocks are universal; two tiers are Federated’s scale split |
| Fair Lean vs Fed bakeoff “uses Panorama Detect” | Fair compare uses **shared threshold Detect**; Panorama is the Fed-native gray-failure path (see [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md)) |

#### Lean vs Federated on the same clocks

| | Lean | Federated |
|--|------|-----------|
| Clock A store shape | Incident kits / bundles + `topology.json` (often L0-cheap) | Dual sink: speed (Dragonfly) + structural (KG/LOS) — F1 when enabled |
| Clock B Localize | Typed CI best-first / CARE / signatures | Murphy on structural graph |
| Clock B path Identify | Limited / stretch | Nezha on Event Graph (class D strength) |
| Clock B Detect | Shared threshold (fair) or alerts | Shared threshold (fair) **or** Panorama LOS |

**One-line for the team:** Clock A/B = *jobs and timing*; Federated Tier 1/2 = *which store each hop needs so high EPS and deep causal analysis don’t share one bottle*.

---

## 4. How competitors cope with the same problem

**Meaning of “cope”:** how Dynatrace, Datadog, and BigPanda-class products handle §2 via ingest, Detect, scoping, and Localize. Soft wording: [`RCA_Vendor_Comparison_NOTES.md`](./RCA_Vendor_Comparison_NOTES.md).

**Three Localize philosophies:**

| Vendor shape | Localize idea |
|--------------|---------------|
| Dynatrace | Walk a live topology (Smartscape) with causal *claim* |
| Datadog | Statistical / correlational “likely culprit” among related entities |
| BigPanda | Correlate alerts + changes (event-centric) |

### 4.1 Shared operating loop (maps to §2)

| Step | What happens | Why (§2) |
|------|----------------|----------|
| **1. Capture + discover** | Agents emit telemetry; discovery keeps entities alive | Volume + identity |
| **2. Detect → seed** | Thresholds / Watchdog / Davis events mark wrong on a CI at *t0* | Detect/seed quality |
| **3. Hold relationship graph** | Smartscape / service map / CI edges | Topology for walk |
| **4. Scope the evidence** | Pull modalities near seed only | Volume — not whole retention per ticket |
| **5. Rank / pick culprit** | Engine + UI propose root / shortlist | Symptom bias |
| **6. Human deep-dive (often)** | Operator opens logs/traces for path “why” | Modality + Step-2 hole |

**Point:** **Detect → scope → reason on a small working set** — not replaying weeks of telemetry into diagnosis each time.

### 4.2 Dynatrace — topology-first + platform substrate

| Piece | Role | Clock |
|-------|------|-------|
| **OneAgent** | Edge capture / enrichment | A |
| **Smartscape** | Live CI / relationship graph | A (topology) |
| **Grail** | Unified multimodal store + DQL | A (store/query) |
| **Detectors / Events** | Detect → seed material | A→B handoff |
| **Davis** | Thin Localize / Problem packaging | B |

**Design takeaway:** topology-first Localize + evidence discipline; treat broad “causal” marketing as philosophy until independently scored.

### 4.3 Datadog — platform lake + statistical Localize

Unified metrics/logs/traces; service map / tags; monitors + Watchdog; correlational ranking; pivot to related logs/traces for Identify. Strong on **platform lake + Detect**; Localize less “typed CI walk” than Dynatrace.

### 4.4 BigPanda (sketch)

Alert/change event graph; storm dedup → probable culprit. Weaker multimodal path Identify unless enriched elsewhere.

### 4.5 Comparison matrix

| Capability | Dynatrace | Datadog | Abstract design target |
|------------|-----------|---------|------------------------|
| Entity / topology graph | Smartscape (core) | Service map / tags (core) | Typed CI / service graph |
| Detect → seed | Davis events | Monitors + Watchdog | Explicit Detect → symptom seed |
| Localize style | Topology + causal claim | Statistical / related entities | Topology walk and/or statistical rank |
| Lake / retrieval | **Grail** (DQL, entity+time) | Indexed platform + query | Entity-keyed store + scoped pull |
| Ingest pipeline | OneAgent → platform | Agents / OTel → platform | Collect → normalize → fan-out (Vector-class) |
| Step-2 path-diff fused | Not verified as fused auto | Not verified | White-space / stretch |
| Accuracy scoreboard | Self-reported | Self-reported | Held-out incidents + human GT |

### 4.6 Design insights

1. Primary graph = **CI / service relationships**; hang modalities on entities.  
2. **Tailor like vendors:** seed → neighborhood → corridor.  
3. Copy **evidence discipline**, not causal marketing.  
4. Compete where they stop: multimodal Identify + optional automated path Identify.  
5. Cheap vs rich retention is normal — full dual-engine lake is expensive.

---

## 5. How we solve it (vendor-aligned preprocess → RCA bet)

**Premise:** Collect → Normalize → Topology sibling → Fan-out → Detect → scoped Tailor is **near-accurate and in-line** with Dynatrace/Datadog. Differentiation is **not** a new ingest religion. It is **what we do after the working set exists**, plus honest cost and Verify.

### 5.1 Solved on Clock A (match vendors)

| Problem slice | Our approach |
|---------------|--------------|
| Orphan signals | Entity-keyed normalize + CI bind |
| Dual-engine cost | Cheap vs rich fan-out (**same** Detect) |
| Whole-lake → diagnosis | Tailor: seed + neighborhood + time corridor → incident kit |
| Stale map | Topology sibling refreshed on discovery/deploy |
| Fair engine compare | Shared Detect → seed, then diverge on Localize |

### 5.2 Product bet on Clock B

| Job | How we solve it | Deliberate difference vs vendors |
|-----|-----------------|----------------------------------|
| **Detect** | Threshold / alert front door; optional gray-failure later | Explicit, measurable detect cost; not buried inside Localize |
| **Localize** | Typed CI walk (topology-first primary on classic infra); optional correlational comparator | Comparable Detect; bakeoff on Localize quality, not Detect luck |
| **Identify** | Signatures / fault class; multimodal corridor for **class C–D** | Compete on report quality and optional path-level Identify |
| **Verify** | Tiered evidence depth — claim only what the tier supports | Do **not** copy broad “causal” marketing |

### 5.3 White space (where vendors still stop)

| Gap | Our move |
|-----|----------|
| Step-2 fused path Identify | Scoped path-diff **after** Localize only ([`two-step-rca-white-space.md`](./two-step-rca-white-space.md)) |
| Contaminated Detect / coaching | GT out of alert text; score held-out human labels |
| Overclaiming cause | Verify tiers gate language in UI and bakeoffs |

### 5.4 Deliberately not solved by copying Grail

- Full Dynatrace-scale lake + DQL is **not** the differentiator.  
- Vector + sinks + builders + incident kits suffice to prove Localize/Identify **if** Tailor scopes correctly.  
- Grow store only when **class C–D** Identify or live Detect demos demand it.

### 5.5 Solution sequence (abstract roadmap)

| # | Focus | Detail |
|---|--------|--------|
| 1 | Solid Clock A | Normalize + topo + fan-out + Detect→seed |
| 2 | Strong Step-1 Localize | Topology walk on scoped kits (**class A–B** first) |
| 3 | Honest Verify + GT | Tiered language; scored labels |
| 4 | Multimodal Identify | Corridor for **class C–D** / report quality |
| 5 | Optional path Identify | White space — scoped, cost-gated |
| 6 | Optional richer store / gray Detect | Only with cost gates |

---

## 6. Grail · Smartscape · Vector

Three different things. Mixing them causes wrong architecture debates.

### 6.1 Grail vs Smartscape (Dynatrace)

| | **Smartscape** | **Grail** |
|--|----------------|-----------|
| **What** | Live **entity + relationship graph** | Unified **data lake + DQL** |
| **Stores** | Nodes + edges (runs-on, calls, …) | Metrics, logs, traces, events over time |
| **Answers** | How are things connected *right now*? | What did this entity look like in *[t0, t1]*? |
| **Fed by** | OneAgent topology cues / discovery | OneAgent telemetry streams |
| **Our analogue** | `topology.json` / CI graph | Entity-keyed store / evidence sinks |

**Myth to drop:** Smartscape does **not** stay fresh by querying Grail with DQL.

**Write path (parallel):**

```
OneAgent ─┬─► Smartscape   (map)
          └─► Grail        (evidence)
```

**Read path (Davis / UI):** Detect on entity → expand neighborhood on **Smartscape** → pull series from **Grail** for those `entityId`s + time → rank / Problem.

They stay aligned because of a **shared entity model**, not because the map rebuilds itself from the lake. DQL is how consumers **read** Grail.

### 6.2 Grail vs Vector (us vs Dynatrace lake)

| | **Grail** | **Vector** |
|--|-----------|------------|
| **What** | Multimodal **storage + query** | **Collect → normalize → fan-out** pipeline |
| **Industry family** | Observability lake / lakehouse | OTel collector / Fluent Bit / ETL |
| **Clock A slot** | Maintain + retrieval | Collect + Normalize + Fan-out |
| **Topology?** | No — Smartscape | No — sibling discovery → CI graph |
| **RCA?** | No — Davis consumes it | Detect after/with; Localize out of scope |

```
Dynatrace:  OneAgent ─┬─► Smartscape ─┐
                      └─► Grail ──────┼─► Detect/Events ─► Davis
Ours:       Sources ──► Vector (+ topo sibling) ─► Detect/seed ─► engines
                         └── sinks/builders ≈ partial lake (not DQL parity)
```

**Implication:** matching Vector to vendors means matching **ingest discipline**, not rebuilding Grail.

---

## 7. Scenario classes A–E (what “class C–D” means)

### 7.1 Purpose of the taxonomy

When someone says “we need logs for class C–D,” they mean:

> This incident type usually **cannot** finish trustworthy **Identify** (and sometimes Localize) on alerts + metrics + topology alone — it needs richer modalities.

Classes are **planning priors** for data requirements and product claims. They are **not**:

- ObserveOps UC-1..5 IDs  
- Severity levels (P1/P2)  
- Vendor feature names  

“Reliably RCA’able” below ≈ useful **Step-1 Localize** with high confidence; Identify called out separately.

### 7.2 Class definitions (detailed)

#### Class A — Classic infra smoking gun (~25–35% prior)

| | |
|--|--|
| **Examples** | Link down / high errors on uplink; host CPU + ready time contention; datastore latency with clear shared victims |
| **Localize with** | Alerts + metrics + topology (+ light traps/events) |
| **Logs** | Often **not required** for Localize |
| **Traces** | Usually not |
| **Why it works** | Fault CI is on the infra graph; onset and shared-upstream pattern are enough |
| **Product claim** | Safe to say “metrics + topology Localize” for much of this class |

#### Class B — Metrics-led, thin events (~20–25% prior)

| | |
|--|--|
| **Examples** | Multi-VM / multi-service metric crossings; need Δt ordering on the walk; sparse SNMP/change hints |
| **Localize with** | Alerts + metrics + topology + sparse events |
| **Logs** | Recommended (confirm / disambiguate) |
| **Traces** | Optional |
| **Why** | Still mostly metric+topo, but ambiguity rises without light events |

#### Class C — App / dependency gray (~25–35% prior)  ← part of “C–D”

| | |
|--|--|
| **Examples** | 5xx bursts; latency without hard infra smoking gun; connection pool / heap exhaustion; “slow dependency” with thin infra anomalies |
| **Localize with** | Above + **logs** (+ change) help; may still point at an app CI |
| **Logs** | **Necessary for Identify** (error strings, pool exhaustion, deploy markers) |
| **Traces** | Recommended |
| **Why** | Metrics show *pain*; logs often show *what kind* of failure |
| **Product claim** | Do **not** promise full Identify on metrics-only for this class |

#### Class D — Path / microservice (~10–20% prior)  ← part of “C–D”

| | |
|--|--|
| **Examples** | Wrong hop / retry storm; dependency timeout on a specific call edge; cross-layer path (app ↔ infra) where the *path* is the story |
| **Localize with** | Multimodal corridor: metrics + logs + **traces/spans** + change |
| **Logs** | Necessary |
| **Traces/spans** | **Necessary for path Identify** |
| **Why** | “Where on the request path” is a trace/span question |
| **Product claim** | Path Identify requires span coverage; sampling policy matters |

#### Class E — Outside organic RCA (~5–10% prior)

| | |
|--|--|
| **Examples** | Pure security incident response; long-range capacity planning; human process failures |
| **Note** | May use observability data, but often not the RCA engine’s job |

### 7.3 Roll-up priors (planning only)

| Claim | Prior |
|-------|--------|
| Localize possible **without rich logs** (A–B) | ~**45–55%** |
| Logs **materially required** (C–D Identify) | ~**40–50%** |
| Traces/spans **required** (D) | ~**10–20%** (higher in pure microservice estates) |
| Alerts + topology + metrics as **minimum Detect→Localize kit** | ~**80%+** |

**Validate later:** sample 50–100 production incidents; tag class + modalities decisive; replace bands with measured %.

### 7.4 How to use classes in design discussions

| If someone says… | Interpret as… |
|------------------|---------------|
| “Ship A–B first” | Prove topology Localize on classic infra with metrics+topo kits |
| “Class C–D gap” | Missing logs/traces (or Identify depth) for app/path incidents |
| “North star is D” | Multimodal path-quality reports, not only Step-1 Localize bakeoffs |
| “E is out of scope” | Don’t force the RCA engine to own security/capacity/process |

---

## 8. Questions each data type answers

| Data type | Primary question(s) | Notes |
|-----------|---------------------|--------|
| **Alerts / Detect** | *That* something is wrong — start the case | Absolute intake for automated RCA |
| **Topology / CI graph** | *Where* things connect — where to walk | Structure; not request-path “where” |
| **Metrics** | *What* is unhealthy + *when* it started | Classic Localize workhorse (A–B) |
| **Logs / events** | *What happened* — sometimes a line of *why* | Often required for Identify (C–D) |
| **Traces / spans** | Path *where + when* (request timing) | Path-level Identify (D) |

**Root-cause “why”** = Localize + Identify + Verify across modalities together — no single modality owns “why.”

---

## 9. Detect vs symptom seed

| Term | Definition |
|------|------------|
| **Detect** | Something is wrong → anomalies (thresholds / SLOs / Watchdog-class). |
| **Symptom seed** | Start Localize at (CI, signal, time). **Usually not the root.** |
| **Shared Detect** | When comparing engines: **one** Detect path so Localize comparisons stay fair. |
| **Gray-failure Detect** | Soft unhealthiness without hard thresholds — optional upgrade; not required to define the jobs. |

**Production bar:** stream → Detect → seed → Localize — not only pre-baked seeds in packs.

**Anti-pattern:** treating the seed CI as the root without a topology walk (symptom bias).

---

## 10. Lake lifecycle — create → maintain → curate → tailor → churn

Aligned with how vendors avoid “whole lake → RCA.” This is **Clock A**, with Tailor handing off to **Clock B**.

### 10.1 Create — order & parallelism

Collect → Normalize → Topology → Fan-out is a **contract dependency**, not “finish all metrics, then invent topology.”

```
                    ┌── Collect ──► Normalize (entity envelope) ──┐
                    │                                             ├──► Fan-out (cheap / rich)
 Topology discovery ──► CI graph ──► identity bind ───────────────┘
```

| Step | Order role | Parallel? |
|------|------------|-----------|
| **Collect** | Raw telemetry arrives | Yes — many sources |
| **Normalize** | Map each event to join keys (`ci_id`, signal, `ts`, …) | Yes — per stream |
| **Topology** | Sibling path; **must exist** for bind + Localize walk | Continuous refresh |
| **Fan-out** | Cheap vs rich sinks without forking Detect | Profile choice |

**Bar:** joinable by **stable identity + time**.

#### Topology granularity

Typed CI graph Localize walks (not a full CMDB dump, not a trace):

| Layer | Node examples | Edge examples | Used when |
|-------|---------------|---------------|-----------|
| L1 Application / service | Service, API, consumer | `calls`, `publishes_to` | Microservice / app path |
| L2 Runtime / workload | Pod, process, JVM | `runs_on`, `contains` | Deploy churn, noisy neighbor |
| L3 Compute host | VM, node, bare metal | `hosted_on` | Classic host/CPU |
| L4 Shared infra | Datastore, port, LB, NUMA | `uses_datastore`, `uplink` | Shared-upstream roots |

**Rules:** coarse enough for stable ticket IDs; fine enough that the fault CI is a node; edges typed; refresh on deploy.

### 10.2 Maintain · Curate · Tailor · Churn

| Phase | Practice |
|-------|----------|
| **Maintain** | Stable identity keys; topo freshness; hot/warm/cold; sampling; clock sync |
| **Curate** | Storm → one seed; human GT; quality flags; no coaching in alerts; gold set |
| **Tailor** | Seed → k-hop neighborhood → time corridor → working set → **Clock B** |
| **Churn** | Rebuild topo · retune detectors · refresh GT · rebalance cheap/rich |

| Tailor knob | Production prior | Working-set analogue |
|-------------|------------------|----------------------|
| Time corridor | Minutes–hours around onset | Incident window (not “last N days”) |
| Space corridor | Seed + up/downstream + shared infra | Topology neighborhood slice |
| Modality mix | A: metrics+topo; D: +logs+spans+change | Classes from **§7** |
| Format | Entity envelopes + edges | Normalized stream + incident kit |

| Store | Role |
|-------|------|
| CI / service relationship graph | Localize walk (primary) |
| Metrics / events / logs / spans | Signals on entities |
| “Knowledge graph” | Marketing umbrella — prefer precise terms |
| Event / alert graph | BigPanda-style; secondary for topology-first Localize |

**Accuracy loop:** tailored set → engines → score vs GT → gaps feed curation.

---

## 11. Open questions · takeaway

### Open questions

1. Measured % of production incidents in classes A–E?  
2. Default corridor: ±15 min vs ±2 h vs change-aware?  
3. When is “no logs” an acceptable product claim (which classes)?  
4. Min trace sampling for class-D Identify under cost caps?  
5. How far to grow store toward Grail-like retrieval vs stay kit-centric?  
6. Where to deliberately **not** copy Dynatrace causal vs Datadog Watchdog branding?

### Takeaway (for the team)

1. **Problem** = joinable estate + Detect seed + scoped reasoning — not “bigger lake.”  
2. **Clock A** = continuous ingest/lake/topo/tailor; **Clock B** = per-incident Detect→Localize→Identify→Verify. Don’t conflate them.  
3. **Federated Tier 1/2** (Event Graph / Knowledge Graph) is a **storage + hop** split orthogonal to clocks — both tiers write on A and read on B (§3.6).  
4. **Class A–E** = modality / difficulty buckets. **Class C–D** = usually need logs (and D needs traces) for Identify.  
5. **Grail ≠ Smartscape ≠ Vector** — evidence lake vs topology map vs ingest pipeline; Davis joins map+lake via `entityId`.  
6. **Vendors** = Detect → scope → reason on a small working set.  
7. **Our bet** = match preprocess; win on Localize discipline, Verify honesty, multimodal Identify, optional scoped path Identify — not on rebuilding Grail.  
8. §7 percentiles stay **priors** until ticket-sampled — do not cite externally as facts.

---

*Design reference / brainstorm — do not cite competitor accuracy or §7 bands externally without measurement / primary sources.*
