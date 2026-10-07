# M.E.L.T.S. — what each signal is for

**Purpose:** One standalone teaching note: what Metrics, Events, Logs, Traces, and Spans each do in an RCA pipeline, how vendors use them, and a necessary → optional scale.  
**Audience:** Anyone who hears “we need MELTS” and needs a cold-reader answer without opening other hub pages.  
**Status:** Working teaching prior (aligned with ObserveOps modality thinking and common vendor practice). Not a Signed product ADR.  
**Date:** 2026-08-25  

**Not in this acronym:** topology / configuration-item map. That is a separate substrate (who is connected). It is often *more* necessary for Localize than traces are — but it is not a MELTS letter.

**Trace vs span (read once):** a **span** is one timed unit of work (one hop, one function, one remote call). A **trace** is the tree (or DAG) of spans that belong to one request or transaction. Vendors often say “traces” when they mean “span data you can query.” This note keeps both letters so the atom (span) is not confused with the whole journey (trace).

---

## 1) One-line objective each

| Letter | Name | Objective in one line |
|--------|------|------------------------|
| **M** | **Metrics** | Say *how bad / how often / how unusual* a named signal is on a configuration item over time (numbers you can threshold, baseline, and sketch). |
| **E** | **Events** | Say *that something discrete happened* at a time (change, deploy, trap, alert fire, state flip) — a fact with a timestamp, not a continuous series. |
| **L** | **Logs** | Say *what the software or device wrote in words* (error strings, stack traces, pool exhaustion, config dump) so Identify can name the *kind* of failure. |
| **T** | **Traces** | Say *which request journey* was slow or failed end-to-end (the full path story across services). |
| **S** | **Spans** | Say *which single hop or unit of work* on that journey burned time or returned the fault (the leaf bar on a flamegraph / PurePath). |

---

## 2) Why each matters (pipeline + vendors)

### Metrics (M)

| | |
|--|--|
| **In our pipeline** | Primary fuel for Detect (thresholds, seasonal baselines, sketches). E4 Stores keeps compact history; Localize uses “who is abnormal” on the map; Identify uses metric pointers as corroboration. Without metrics, Detect and “is this worse than usual?” mostly stop. |
| **At vendors** | Dynatrace Grail + Davis metric events; Datadog Metrics rail + Monitors/Watchdog; Edge Delta / agents scrape or roll up numeric series. Everyone treats metrics as the always-on health pulse. |
| **Failure mode if missing** | Blind or late Detect; no sketch baselines; Localize has little “who is hot” beyond binary alerts. |

### Events (E)

| | |
|--|--|
| **In our pipeline** | Discrete facts that join to a configuration item by identity and time: change/deploy markers, SNMP/traps, Detect fires (as *signals*, not topology vertices). Curate and Localize use them for onset ordering (“deploy then 5xx”). They are evidence/facts — not graph nodes. |
| **At vendors** | Overloaded word: Dynatrace “Event” ≈ Detect breach; change events in Grail; Datadog Events / deploy markers; traps and Kubernetes events in infra tools. Same job: *something happened at T*. |
| **Failure mode if missing** | Harder to order cause vs symptom; “what changed?” stays empty; some Detect classes never fire. |

### Logs (L)

| | |
|--|--|
| **In our pipeline** | Identify’s main language modality: error text, exception class, pool / heap messages, auth failures. Scope/Tailor pulls logs inside the time corridor when the incident class needs them. Thin evidence bundles when logs are absent for app-gray faults. |
| **At vendors** | Dynatrace Grail logs; Datadog Logs + Husky; Edge Delta pipelines reshape/forward logs. Operators pivot to logs after the map names a neighborhood. |
| **Failure mode if missing** | Localize may still point at a service; Identify often cannot name *what kind* of failure (class C–D style incidents). |

### Traces (T)

| | |
|--|--|
| **In our pipeline** | Request-path evidence for microservice estates: which dependency chain was in play. Feeds corroborating edges (`communicates_with` / `uses`) and path Identify. Sampling policy matters — missing coverage looks like “no path.” |
| **At vendors** | Dynatrace PurePath / distributed traces in Grail; Datadog APM; OpenTelemetry everywhere. Service maps are often *derived* from traces, not from CMDB. |
| **Failure mode if missing** | Path Identify collapses; dependency walks lean on declared/catalog edges or metrics only. |

### Spans (S)

| | |
|--|--|
| **In our pipeline** | The atomic evidence inside a trace: which hop timed out, which DB query, which handler threw. Flamegraph / PurePath leaf reading is span work. Stored and queried as span records; rolled up into a trace id. |
| **At vendors** | Same products as traces (APM). UI shows traces; storage and query are mostly span-level. |
| **Failure mode if missing** | You may know “checkout was slow” (metrics) but not *which call* on the path (span leaf). |

---

## 3) Chronology: absolute necessary → optional

This is a **build / coverage priority**, not “never collect the lower ones.” It answers: *if we can only afford to do well in stages, what comes first for useful Detect → Localize → Identify?*

```text
MORE NECESSARY ──────────────────────────────────────────────► MORE OPTIONAL
(for most RCA claims)                                    (path / deep Identify)

  Metrics  →  Events  →  Logs  →  Traces  →  Spans
     M           E         L         T         S
```

| Rank | Modality | Band | Why this place on the scale |
|------|----------|------|-----------------------------|
| **1** | **Metrics** | Absolute necessary (almost always) | Detect, baselines/sketches, “who is abnormal,” shared-upstream Localize on classic infra and many app symptoms. Vendors ship metrics first for a reason. |
| **2** | **Events** | Near-necessary (thin kit) | Onset, change correlation, Detect fires, traps. Cheap discrete facts that turn “metrics look bad” into “something happened then.” Without them, order and change context stay guesswork. |
| **3** | **Logs** | Necessary for trustworthy Identify on many app faults; optional for classic infra smoking guns | Class A–B Localize often works without rich logs; class C Identify usually does not. Next spend after metrics+events for app estates. |
| **4** | **Traces** | Optional until path/microservice Identify is a product claim | Required when the *journey* is the story (wrong hop, retry storm, dependency timeout on a specific edge). Costly; sampling and coverage become product decisions. |
| **5** | **Spans** | Optional atom of traces — last to demand full fidelity | You need span-level detail to name the leaf hop. Trace *ids* without useful spans are theater. Treat as the deepest, most expensive layer of the same path story as traces. |

**Planning priors (order-of-magnitude, not measured %):**

| Claim | Rough prior |
|-------|-------------|
| Useful Localize with metrics + topology (+ light events) | Large share of classic infra / clear smoking-gun cases |
| Logs materially required for Identify | Large share of app / dependency gray cases |
| Traces/spans required for path Identify | Smaller share overall; much higher in pure microservice estates |

**Honest degradation:** missing a modality should produce a **thin evidence bundle** with an explicit incompleteness flag — not a fake high-confidence leaf.

---

## 4) Quick compare (same incident, different jobs)

Example: checkout API returns 5xx after a deploy.

| Modality | What it contributes |
|----------|---------------------|
| **Metrics** | Error rate and latency up on `checkout-api`; maybe DB p95 also up. |
| **Events** | Deploy / change at T−12m on that service or its dependency. |
| **Logs** | `ConnectionPoolExhausted` or `KeyError` text that names the fault class. |
| **Traces** | This request’s journey touched inventory then DB. |
| **Spans** | The DB span (or inventory handler span) is where time or error actually sat. |

Metrics find the pain. Events place the change. Logs name the kind. Traces show the journey. Spans pin the hop.

---

## 5) What not to confuse

| Tempting mix-up | Clearer split |
|-----------------|---------------|
| Events = metrics | Metrics are continuous (or sampled) series; events are discrete “happened at T.” |
| Traces = logs | Logs are text the process emitted; traces/spans are structured timing of call structure. |
| Spans = a different product from traces | Spans are the rows; a trace is the grouped journey. |
| Alert = topology node | An alert/Detect fire is an event/signal *about* a configuration item — not a vertex on the estate map. |
| More MELTS = better RCA always | Unscoped lake dumps hurt. Bound by identity, time, hop budget, and incident class. |

---

## 6) One-minute summary

**Metrics** tell you something is wrong and how unusual it is. **Events** tell you what discrete thing happened when. **Logs** tell you what kind of failure the software admits. **Traces** tell you which request journey was involved. **Spans** tell you which hop on that journey is the leaf. Build coverage in that order for most estates; treat traces/spans as the path-Identify tax, not the day-one Detect tax. Topology (outside MELTS) remains the map you walk — without it, modalities hang in the air.
