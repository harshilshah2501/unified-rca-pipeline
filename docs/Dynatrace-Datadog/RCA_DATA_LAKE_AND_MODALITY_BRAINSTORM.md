# Brainstorm — RCA data problem, competitors & lake lifecycle

**Status:** brainstorm / working hypotheses (not a measured industry survey)  
**Date:** 2026-07-29 (abstract problem framing · competitors · lake lifecycle)  
**Context:** Frame the RCA data problem in the abstract first; PoC corpora and vendor bakeoffs are out of scope here.  
**Related (deeper / PoC later):** [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) · [`RCA_Vendor_Comparison_NOTES.md`](./RCA_Vendor_Comparison_NOTES.md) · PDF [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf)

**Honesty label:** competitor mechanics below are from **public product framing + our vendor notes** (self-reported where noted). Percentile bands are **planning priors**, not a published survey.

---

## 0. Document map

| Section | Question |
|---------|----------|
| **§1** | What is the problem? |
| **§2** | What are the pain points? |
| **§3** | How do competitors tackle it? (Datadog, Dynatrace, + BigPanda sketch) |
| **§4** | What does each data type answer? |
| **§5** | Survey-style priors: % scenarios × modality mix |
| **§6** | Detect vs seed vs gray-failure Detect |
| **§7** | Lake lifecycle (+ ingest order, topo granularity, industry names) |
| **§8** | Open questions · takeaway |

---

## 1. What is the problem? (define it)

### 1.1 One-sentence problem

**Given noisy, high-volume, multi-modal telemetry and a shifting estate, automatically (or assistively) answer: what is wrong, where is the fault, and—when justified—why, with an evidence trail an SRE can trust.**

### 1.2 Decompose into jobs (our workflow)

```
Ingest → Detect → Localize → Identify → Verify
```

| Job | Plain question | Failure mode if skipped |
|-----|----------------|-------------------------|
| **Ingest** | Can we join signals by identity + time? | Orphan metrics/logs; no walk |
| **Detect** | Is something wrong *now*, and where does pain show? | No case start / wrong seed |
| **Localize** | Which CI / service is the fault region? | Blame the loud symptom app |
| **Identify** | What *kind* of failure (and optionally which path)? | “Host X bad” with no actionable class |
| **Verify** | How strongly may we claim cause? | Marketing “causal” without evidence depth |

Market shorthand ([`two-step-rca-white-space.md`](./two-step-rca-white-space.md)):

- **Step 1 “where”** ≈ Detect → Localize (vendors automate this well).  
- **Step 2 “what happened there”** ≈ Identify (+ Verify); deep path-diff automation still thin.

### 1.3 The data sub-problem (why a “lake” is not enough)

Raw production data is:

- **Huge** (metrics × hosts × minutes; log lines; sampled spans),  
- **Heterogeneous** (infra vs app vs change),  
- **Non-stationary** (deploys change topology),  
- **Identity-unstable** (pods churn; monitors rename).

So the real systems problem is not “store everything.” It is:

> **Create an entity-keyed, time-aligned store; then, per incident, tailor a small AI-ready working set (seed + neighborhood + corridor) that Localize/Identify can reason over.**

That is what Datadog/Dynatrace-class products optimize for operationally—and what any serious RCA stack must approximate: a normalized stream plus an incident-scoped working set.

---

## 2. Pain points (systematic)

Group pains by layer. These are why naive “dump lake → LLM” fails and why vendors invest in agents, graphs, and scoping.

### 2.1 Volume & cost

| Pain | Symptom | Consequence |
|------|---------|-------------|
| Cardinality explosion | High-cardinality metrics/logs | Hot store cost; query timeouts |
| Trace flood | Full request capture | Must sample; miss rare failures |
| Alert storms | Many alerts, one fault | Human overload; bad seeds |

### 2.2 Join & identity

| Pain | Symptom | Consequence |
|------|---------|-------------|
| No stable CI | Host vs pod vs service mismatch | Cannot hang logs on topology |
| Stale topology | Deploy changed deps | Walk to wrong upstream |
| Clock skew | Modalities disagree on “onset” | False Δt ordering |

### 2.3 Detect quality

| Pain | Symptom | Consequence |
|------|---------|-------------|
| Missing Detect | No alert / weak threshold | RCA never starts |
| Wrong seed | Alert on symptom only, treated as root | Localize never asked to walk |
| Contaminated alerts | Ground truth / root text in alert body | Inflated accuracy; engines “cheat” |
| Gray failure | Soft unhealthiness without hard threshold | Threshold Detect blind |

### 2.4 Reasoning quality

| Pain | Symptom | Consequence |
|------|---------|-------------|
| Symptom bias | Loud app blamed | Miss shared infra root |
| Correlation ≠ cause | Ranked list of “related” | Weak Verify / overclaim causal |
| Modality gaps | No logs/traces when Identify needs them | Stop at Localize or guess |
| Step-2 automation gap | Deep traces exist but no fused path-diff verdict | Human digs manually |

### 2.5 Organizational / product

| Pain | Symptom | Consequence |
|------|---------|-------------|
| Tool sprawl | Metrics in A, logs in B, traces in C | Slow multimodal RCA |
| No GT / feedback | Cannot score engines | Cannot improve lake or Detect |
| Dual-engine cost | Store everything for every approach | Need cheap vs rich fan-out profiles |

---

## 3. How competitors tackle it

**Three philosophies** (from our vendor survey): Dynatrace ≈ deterministic topology walk; Datadog ≈ statistical / learned correlation; BigPanda ≈ alert+change correlation. Soft wording: [`RCA_Vendor_Comparison_NOTES.md`](./RCA_Vendor_Comparison_NOTES.md).

### 3.1 Shared competitor pattern (all serious players)

Regardless of brand, production RCA stacks converge on:

1. **Agents + continuous discovery** → entity universe  
2. **Detect / Watchdog / Davis events** → incident seed  
3. **Entity / service / Smartscape-style graph** → where to relate signals  
4. **Incident-scoped pull** of metrics/logs/traces near seed (not full lake)  
5. **Rank or pick a culprit** → UI + optional AI narrative  
6. **Human Step-2** for deep method/path “why” (often)

They do **not** feed the entire retention window into one model per ticket.

### 3.2 Dynatrace (Davis) — topology-first, causal claim

| Dimension | Approach (public framing) |
|-----------|---------------------------|
| **Problem focus** | Continuously known dependency world; diagnose on the map |
| **Graph** | **Smartscape / topology** — processes, services, hosts, calls (CI relationship graph, live) |
| **Detect** | Davis events / anomaly detection on monitored entities |
| **Localize** | Deterministic / rule-assisted walk and causation engine over topology + signals |
| **Identify / Verify** | Product claims **causal** reasoning (separate from generative “advice”) — **self-reported**; hard to independently scoreboard |
| **Lake tactic** | OneAgent-style capture + entity model; Davis consumes curated entity context |
| **Pain mitigated** | Stale-map and symptom bias (if topology fresh); “random correlation soup” |
| **Pain remaining** | Gray cases + Step-2 path-diff fusion; causal claim hard to independently verify; cost of full-stack agents |

**Design takeaway:** topology-first Localize + disciplined Verify language is the Dynatrace-shaped bet; treat their broad “causal” marketing as philosophy until independently scored.

### 3.3 Datadog — observability platform + statistical / Watchdog localization

| Dimension | Approach (public framing) |
|-----------|---------------------------|
| **Problem focus** | Unified metrics/logs/traces; find what **deviated from normal** |
| **Graph** | **Service map / APM entities** + infra hosts; relationships from instrumentation |
| **Detect** | Monitors + **Watchdog**-style anomaly / outlier detection |
| **Localize** | Statistical correlation / change-point style “likely culprit” among related entities |
| **Identify** | Pivot to related logs, traces, profiles, error tracking; Bits AI / narratives assist humans |
| **Lake tactic** | Tag-heavy entity model; sampling; index/retention tiers; query across modalities by tag/entity |
| **Pain mitigated** | Tool sprawl (one pane); volume via sampling/indexing; symptom vs related infra via correlation |
| **Pain remaining** | Correlation ≠ cause; depends on instrumentation coverage; Step-2 still largely operator + UI |

**Design takeaway:** strong on **platform lake + Detect** and correlational “what moved together”; Localize is less “typed CI walk” branded than Dynatrace.

### 3.4 BigPanda (sketch) — alert/event correlation

| Dimension | Approach |
|-----------|----------|
| **Graph** | More **alert / change event graph** than deep APM topology |
| **Tactic** | Deduplicate storms; correlate alerts + changes → probable culprit |
| **Pain mitigated** | Alert fatigue, cross-tool noise |
| **Gap vs multimodal north star** | Weaker path-level Identify unless enriched with deep APM + change elsewhere |

### 3.5 Competitor comparison matrix (brainstorm)

| Capability | Dynatrace | Datadog | Abstract design target |
|------------|-----------|---------|------------------------|
| Entity / topology graph | **Smartscape (core)** | Service map / tags (**core**) | Typed CI / service graph |
| Detect → seed | Davis events | Monitors + Watchdog | Explicit Detect → symptom seed |
| Localize style | Topology + causal engine claim | Statistical / related entities | Topology walk and/or statistical rank (comparable Detect) |
| Logs in RCA | Yes, entity-joined | Yes, first-class | Required for class C–D Identify |
| Traces/spans | Deep APM | Deep APM | Required for class D path Identify |
| Lake scoping | Incident / entity context | Query + Watchdog context | Tailor: seed + neighborhood + time corridor |
| Step-2 path-diff fused in verdict | Not verified as fused auto | Not verified | White-space / stretch ([`two-step-rca-white-space.md`](./two-step-rca-white-space.md)) |
| Independent accuracy scoreboard | Self-reported | Self-reported | Measure on held-out incidents with human GT |

### 3.6 Insights for lake / RCA design

1. **Graph choice:** primary store is a **CI / service relationship graph**, not a vague “knowledge graph” marketing term; hang metrics/logs/spans on entities.  
2. **Tailor like vendors:** Detect seed → expand neighborhood → pull corridor — Dynatrace and Datadog both do this under different branding.  
3. **Do not copy causal marketing:** copy **evidence discipline** (tiered confidence / Verify depth).  
4. **Compete where they stop:** multimodal **Identify / report quality** + optional **automated path Identify**; don’t only re-race Step-1 Localize.  
5. **Cost fan-out:** cheap vs rich retention profiles mirror vendor reality—full dual-engine retention is expensive.

---

## 4. Questions each data type answers (recalibrated)

| Data type | Primary question(s) | Notes |
|-----------|---------------------|--------|
| **Alerts / Detect** | *That* something is wrong — start the case | Absolute intake for automated RCA |
| **Topology / CI graph** | *Where* things connect — where to walk | Structure; not request-path “where” |
| **Metrics** | *What* is unhealthy + *when* it started (onset / magnitude) | Classic Localize workhorse |
| **Logs / events** | *What happened* (errors, deploys, SNMP, kernel) — sometimes a line of *why* | Often required for Identify |
| **Traces** | End-to-end request story | Path-level Identify |
| **Spans** | One hop inside a trace | Same family as traces (building blocks) |

**Corrected shorthand:**

- Topology → **where** (structure / walk)  
- Metrics → **what + when** (symptoms & onsets)  
- Logs → **what happened** (+ often why)  
- Traces/spans → **where-on-the-path + when** (request timing)  
- **Root-cause “why”** → Localize + Identify + Verify using several modalities together  

**Yes:** some production class-A incidents Localize **without rich logs**.  
**Also yes:** many class C–D incidents need logs (and D needs traces) for trustworthy Identify.

---

## 5. Survey-style prior: % of production scenarios by data mix

### 5.1 Axes

“Reliably RCA’able” here ≈ useful **Step-1 Localize** with high confidence; Identify depth called out separately.

### 5.2 Hypothesis bands (planning priors)

| Scenario class (examples) | Share of infra/app incidents* | Reliably Localize with… | Logs? | Traces/spans? |
|---------------------------|-------------------------------|-------------------------|-------|----------------|
| **A. Classic infra smoking gun** — link down, host CPU/storage saturation, clear shared-upstream | ~25–35% | Alerts + metrics + topology (+ light events/traps) | Often **not required** for Localize | Usually not |
| **B. Metrics-led with thin events** — multi-signal onset, need topology walk + Δt | ~20–25% | Alerts + metrics + topology + sparse events | **Recommended** | Optional |
| **C. App / dependency gray** — 5xx, latency, pool exhaustion, “slow somewhere” | ~25–35% | Above + **logs** (and change) | **Necessary** for Identify; help Localize | **Recommended** |
| **D. Path / microservice** — wrong hop, timeout on dependency call, cross-layer infra↔app | ~10–20% | Multimodal corridor: metrics + logs + traces/spans + change | Necessary | **Necessary** for path Identify |
| **E. Outside organic RCA** — pure security, capacity planning, human process | ~5–10% | Often not “RCA engine” territory | — | — |

\*Share of *actionable production incidents an observability RCA product is asked to touch*.

**Roll-up:**

| Claim | Prior |
|-------|--------|
| Localize possible **without rich logs** (A–B) | ~**45–55%** |
| Logs **materially required** (C–D Identify) | ~**40–50%** |
| Traces/spans **required** (D) | ~**10–20%** (higher in pure microservice estates) |
| Alerts + topology + metrics as **minimum Detect→Localize kit** | ~**80%+** |

### 5.3 How to validate priors (later)

Sample 50–100 production incidents; tag fault class, modalities available vs decisive, metrics+topo-only Localize Y/N, logs/traces needed Y/N. Replace §5.2 with measured %.

---

## 6. Detect vs symptom seed (and gray-failure Detect)

**Detect** = something is wrong (thresholds / SLOs → anomalies).  
**Symptom seed** = start Localize here (CI + signal + time) — usually not the root.  
**Shared Detect** (when comparing engines) = one Detect path so Localize comparisons stay fair.

**Gray-failure Detect** (soft unhealthiness without hard thresholds) is a separate Detect upgrade path—not required to define the abstract RCA jobs.

Production bar: **stream → Detect → seed → Localize**, not only pre-baked seeds.

---

## 7. Data lake lifecycle — create → maintain → curate → tailor → churn

Aligned with how Datadog/Dynatrace operationally avoid “whole lake → RCA.”

### 7.0 Two clocks (do not confuse)

| Clock | Stages | What it is |
|-------|--------|------------|
| **A. Ingest / lake ops** | Collect · Normalize · Topology · Fan-out · Maintain · Curate · Tailor · Churn | How telemetry becomes joinable and incident-scoped |
| **B. RCA case** | Detect → Localize → Identify → Verify | How one incident is reasoned once a seed exists |

**Ingest is not RCA.** Collect/Normalize/Topology/Fan-out prepare the estate; Detect starts a case; Localize/Identify/Verify are the diagnosis jobs.

Industry names for clock A (old, well-known problems under new branding):

| Our word | Classical / industry name |
|----------|---------------------------|
| Collect + Normalize | **Observability / telemetry pipeline** (OTel collectors, Vector, Fluent Bit) — same family as **ETL/ELT** |
| Topology + CI bind | **Discovery + CMDB / service inventory** + **entity / identity resolution** |
| Maintain (retention, sampling, freshness) | **Data lifecycle management** (hot/warm/cold; cardinality control) |
| Curate (quality, GT, storm control) | **Data quality / data curation** (+ ITSM **event correlation** for storms) |
| Tailor (seed → neighborhood → corridor) | **Context assembly / incident scoping** — vendors: “related entities,” Smartscape slice, investigation workspace; ML analogue: **feature / working-set construction** |
| Whole loop | Often marketed as **observability data platform** or **AIOps data prep**; the hard bit is still **joinable entities + scoped context**, not “bigger lake” |

So yes: managing/curating/tailoring this data is an **old** problem (CMDB + event mgmt in ITIL; ETL + DQ in data platforms; now reframed for AIOps). What is newer is multimodal volume + automated Localize on top of it.

### 7.1 Create (ingest) — order & parallelism

**Collect → Normalize → Topology → Fan-out is not “first collect metrics, then invent topology.”**  
It is a **dependency order of contracts**, with **parallel pipelines** in practice:

```
                    ┌── Collect (continuous streams) ──► Normalize (entity envelope) ──┐
                    │                                                                  ├──► Fan-out (cheap / rich sinks)
 Topology discovery ──► CI graph ──► identity bind ────────────────────────────────────┘
```

| Step | Order role | Parallel? |
|------|------------|-----------|
| **Collect** | First: raw telemetry arrives (agents, APIs, traps, OTel) | Yes — many sources at once |
| **Normalize** | Second *for each event*: map to join keys (`ci_id`, `signal`, `ts`, value…) | Yes — per stream |
| **Topology** | **Sibling**, not “after all metrics.” Needs discovery/CMDB; **must exist** so Normalize can bind identity and so Localize can walk | Continuous refresh; snapshot CI graph |
| **Fan-out** | After normalize (+ topo available for bind): write cheap vs rich sinks **without** forking Detect | Profile choice, not a time-ordered “collect phase” |

**Bar:** joinable by **stable identity + time**. Without topo + bind, Collect/Normalize produce orphans.

#### Topology: of what, at what granularity?

Topology is the **typed CI / dependency graph** Localize walks — not a request trace, not a full CMDB dump of every attribute.

| Layer (typical) | Node examples | Edge examples | Used when |
|-----------------|---------------|---------------|-----------|
| **L1 Application / service** | Service, API, queue consumer | `calls`, `publishes_to` | Microservice / app path Localize |
| **L2 Runtime / workload** | Pod, process, JVM, container | `runs_on`, `contains` | Deploy churn, noisy neighbor |
| **L3 Compute host** | VM, bare metal, node | `hosted_on` | Classic host/CPU faults |
| **L4 Shared infra** | Datastore, switch/port, LB, NUMA node | `uses_datastore`, `uplink` | Storage/network/shared-upstream roots |

**Granularity rule of thumb:**

- **Coarse enough** that Detect seeds and human tickets name the same IDs (service/host, not every ephemeral pod if pods churn).  
- **Fine enough** that the true fault CI is a node (e.g. `datastore-01`, not only `datacenter`).  
- **Edges typed** for walk direction (upstream shared infra vs downstream symptom).  
- **Refresh** on discovery/deploy — stale edges = wrong Localize.

Concrete artifact shapes (normalized envelopes, topology snapshots) are implementation detail—out of scope for this abstract framing.

### 7.1b Create checklist

| Step | Output | Notes |
|------|--------|--------|
| Collect | Metrics, logs, spans/traces, events/changes, alerts | Prefer unified agents / OTel |
| Normalize | Entity-keyed envelope | CI id, signal, time, value, threshold |
| Topology sibling | Typed CI / service graph | Discovery / CMDB / service map beside the telemetry pipeline |
| Fan-out | Cheap vs rich sinks | Cost control without forking Detect |

### 7.2 Maintain

| Concern | Practice |
|---------|----------|
| Identity | Workload/service/host keys over raw pod churn when relevant |
| Topology freshness | Refresh on deploy/discovery |
| Retention tiers | Hot incident / warm / cold |
| Sampling | Traces + logs: keep decisive coverage under cost |
| Clock sync | Shared time base across modalities |

### 7.3 Curate

| Concern | Practice |
|---------|----------|
| Storm control | Many alerts → one seed |
| Human GT | Labeled incident kits; never auto-invent GT |
| Quality flags | Missing topo/traces/logs called out in reports |
| No coaching | GT out of alert text |
| Gold set | Held-out multimodal incidents for Identify / report quality |

### 7.4 Tailor (AI-ready working set)

```
Alert / Detect
  → symptom seed (CI, signal, t0)
  → expand topology neighborhood (k-hop / critical path)
  → pull metrics + logs + spans in [t0 − pre, t0 + post]
  → pack / working set → Localize → Identify → Verify
```

| Knob | Production prior | Working-set analogue |
|------|------------------|---------------------|
| Time corridor | Minutes–hours around onset | Incident window (not “search last N days”) |
| Space corridor | Seed + up/downstream + shared infra | Topology neighborhood slice |
| Modality mix | A: metrics+topo; D: +logs+spans+change | Class A–D from §5 |
| Format | Entity envelopes + edges | Normalized stream + incident kit |

| Store | Role |
|-------|------|
| **CI / service relationship graph** | Localize walk (primary) — Dynatrace Smartscape / Datadog service map analogue |
| Metrics / events / logs / spans | Signals on entities |
| “Knowledge graph” | Marketing umbrella for the above |
| Event / alert graph | BigPanda-style; secondary for topology-first Localize |

### 7.5 Churn

Topology rebuild · detector retune · GT refresh · re-run gold after engine changes · cheap/rich cost rebalance.

**Accuracy loop:** tailored working set → engines → score vs GT/gold → gaps feed curation.

---

## 8. Open questions · takeaway

### Open questions

1. Measured % of production incidents in classes A–D?  
2. Default corridor: ±15 min vs ±2 h vs change-aware?  
3. When is “no logs” an acceptable product claim?  
4. Min trace sampling for class-D Identify under cost caps?  
5. Where to deliberately **not** copy Dynatrace causal marketing vs Datadog Watchdog branding?

### Takeaway

1. **Problem** = joinable multi-modal estate + Detect seed + scoped reasoning — not “bigger lake.”  
2. **Pains** = volume, identity, stale topo, bad seeds, symptom bias, modality gaps, Step-2 automation hole.  
3. **Dynatrace** = topology-first + causal claim; **Datadog** = platform lake + statistical/Watchdog Localize + multimodal pivot — both **scope before reason**.  
4. **Design bet** = explicit Detect, typed topology Localize, honest Verify tiers, multimodal Identify where class C–D demand it, white space on fused path Identify.  
5. §5 percentiles stay **priors** until ticket-sampled.

---

*Brainstorm only — do not cite competitor accuracy or §5 bands externally without measurement / primary sources.*
