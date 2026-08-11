# Datadog production pipeline — native map & evidence

**Audience:** engineers who need Datadog’s always-on fabric clear **on Datadog’s own terms** before comparing any other vendor.  
**Status:** teaching / design reference — public product framing + **live MCP tenant evidence** + local Agent observation.  
**Date:** 2026-08-03 · lab update 2026-08-04  

**Honesty labels**

| Label | Meaning |
|-------|---------|
| **Observed (MCP)** | Seen via Datadog MCP against org Self / `datadoghq.com` — see evidence appendices |
| **Observed (agent)** | Seen on local Datadog Agent install (WSL host `DESKTOP-MBPAQK1`) |
| **Observed (lab)** | Controlled `datadog-rca-lab` run (FE→product→inventory fault) |
| **Public framing** | Datadog product docs / marketing-shaped architecture |
| **Inferred** | Reasonable model; not a Datadog-internal spec |
| **Teaching** | Pedagogical example — **not** yet observed |

**Browser:** [`datadog-production-pipeline.html`](./datadog-production-pipeline.html) · [`:8765`](http://127.0.0.1:8765/datadog-production-pipeline.html)  
**Mechanisms:** [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html)  
**Evidence:** [`datadog-tenant-evidence-2026-08-03.md`](./datadog-tenant-evidence-2026-08-03.md) · [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md)  
**Lab:** [`../datadog-rca-lab/DATADOG_RCA_REFERENCE.md`](../datadog-rca-lab/DATADOG_RCA_REFERENCE.md)  
**Separate unveil (not a twin):** [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md)  
**Same-scenario lab compare:** [`COMPARABLE_PIPELINE_DT_DD.md`](./COMPARABLE_PIPELINE_DT_DD.md)  
**Out of scope here:** Lean vs Federated, L0/F1, CARE / Murphy / Nezha, head-to-head bakeoff.

---

## 0. Method · stage IPO · Doors vs stores (hub shared)

**Method:** Finish independent Datadog end-to-end dissection for **ERROR-rate** and **SLOWDOWN** first (**Detect → leaf → packaging limits**). Dynatrace ↔ Datadog building-block parallels come only after both categories have that insight — not mid-pipeline.

Lean Breakdown stages are **01–08** (no Maintain stage — continuous write is **03**).

| Method phrase | Breakdown stages |
|---------------|------------------|
| Write (continuous) | **03** M ∥ APM ∥ Logs (not Detect) |
| Detect | **05** Monitors · Watchdog (Door A ∥ Door B) |
| leaf | **07** Flamegraph leaf · tag join |
| packaging limits | **08** Bits Investigation ∥ Incident (often absent) |

**Doors vs product rails:** Stage **03** writes Metrics ∥ APM ∥ Logs continuously (backend: Metrics timeseries ∥ Husky events for traces/logs). Stage **05** Detect does **not** equally consume all three rails:

| Door | Primary Detect input | Lab ERROR note (e3 · 2026-08-10) | Lab SLOWDOWN note (e3 · 2026-08-11) |
|------|----------------------|----------------------------------|-------------------------------------|
| **A · Monitors** | Metric / APM **query + threshold** | Error-rate `310925690` → **Alert** after sustain | Same error Door **OK** (HTTP 200); **no** latency/p95 Door scoped → no Alert |
| **B · Watchdog APM** | APM anomaly **stories** → events → bridge `310485027` | **0** APM stories · bridge **OK** | **0** APM stories |
| **B · Watchdog Logs** | `logs_pattern_anomaly` under `env:rca-lab-e3` | **Present** (~07:51Z+) | Not the Detect tip (ok logs) |
| Logs (MTL) | Corroboration at **tag join** (stage **07**) | Equal evidence, not fused Detect | `inventory.stock.ok` corroborates success path |

∥ = parallel, not merged. Same fault can light different Detect surfaces with different verdicts. **SLOWDOWN Observed:** Write can be loud while Detect stays empty — operator Localize (Timeline §2). **Bits** = optional Bits AI Investigation (separate click). Detect ALERT ≠ Bits ≠ Incident.

**Hub tabs:** Thesis / Breakdown / Three-rail / Timeline (+ Interpret: MTL · Bits) share one spine via `?cat=`. Full **8-stage** IPO table: Breakdown + Hub (`#urca-dd-pipeline-guide`).

Live HTML injects the same guide from [`dd-detect-categories.js`](./dd-detect-categories.js) (`URCA_DD_CATS.pipeline`).


## 1. What this tenant actually has

**Observed (MCP)** on 2026-08-03 — thin but real:

| Area | Snapshot |
|------|----------|
| Hosts | **1** — `DESKTOP-MBPAQK1`, Agent **7.81.3**, `env:dev` |
| Metrics | Live host series (e.g. mem usable ~45%, load.norm.1 ~0.27, cpu.user ~5%) |
| APM | ~900 spans / 6h — mostly auto `service:node` (Cursor / shell / outbound HTTP to MCP peers) |
| Logs | ~100k+ lines / 6h — `rsyslogd`, `oneagentloganalytics`, … |
| Service catalog | Process / peer names (`node`, `bash`, `rsyslogd`, `peer.hostname:…`, `oneagent*`) — **not** a microservices lab |
| Service map edges | `node` → `peer.hostname:api2.cursor.sh`, `mcp.datadoghq.com`, `docs.mcp.cloudflare.com` |
| Monitors | Default **query** host monitors (OK) + **Watchdog** `event-v2` monitor (**Alert**) + auto APM error-rate monitor |
| Watchdog | Stories on `service:node` / resource `/bin/bash` (`story_type:error_rate`) |
| Incidents | **0** packaged incidents |

**Implication (2026-08-03):** Host + monitors + Watchdog were the only Observed Detect paths.  
**Update (2026-08-04):** `datadog-rca-lab` adds **Observed (lab)** FE→product→inventory APM traces + auto Flask error-rate monitor — see §7 and [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md).

**Update (2026-08-07):** same ERROR scenario with **production-grade Metrics ∥ Traces ∥ Logs** — DogStatsD `rca.*`, JSON logs + Agent file tail, APM error tags. Teaching: [`dd-error-mtl-dissection.html`](./dd-error-mtl-dissection.html) · evidence [`datadog-lab-evidence-mtl-error-2026-08-07.md`](./datadog-lab-evidence-mtl-error-2026-08-07.md).

**Update (2026-08-10):** primary teaching run **`env:rca-lab-e3`** · `version:keyerror-20260810T072333Z` · code-level KeyError (no `fault.injected`). MCP: Metrics≈2403 · spans KeyError≈2427 · logs≈2486 · Door A **Alert** · Door B APM **0** · logs Watchdog **yes** · Incident **0**. Evidence: [`datadog-lab-evidence-mtl-error-2026-08-10.md`](./datadog-lab-evidence-mtl-error-2026-08-10.md).

---

## 2. Mental model (Datadog-native)

Datadog is best understood as:

```text
Datadog Agent
   └─► tagged intake ──┬─► Metrics
                       ├─► APM (traces / resources / inferred service map)
                       └─► Logs
                              │
                              ▼
              Monitors (metric / log / APM query)
           +  Watchdog (anomaly stories → events → optional event monitors)
                              │
                              ▼
         Operator / Insights / Bits AI  (related + scoped query — correlational)
```

| Path | Meaning |
|------|---------|
| Agent → **Metrics / APM / Logs** | Continuous productized intake, joined primarily by **tags** (`service`, `env`, `host`, …) |
| **Monitors** | Explicit thresholds / forecasts / APM queries → alert states |
| **Watchdog** | Statistical anomaly **stories** (often without a hand-written threshold) → events; may drive an `event-v2` monitor |
| Insights / Bits AI / Incidents | Assist correlational packaging — **not** observed as a rich Incident card in this tenant |

It is **not**:

```text
Alert fires → RCA wakes → pulls raw MELT from scratch for the whole estate
```

And it is **not** Dynatrace’s shape:

```text
OneAgent ─┬─► Smartscape (typed map write path)
          └─► Grail (single multimodal lake + DQL)
```

### Myths to drop

1. **“Platform lake = Grail.”** Datadog ships **separate product explorers** for Metrics, APM, and Logs. Backend: Metrics timeseries ∥ Husky events (traces+logs) — still not one Grail lake. Join = tags.
2. **“Service Map is written in parallel like Smartscape.”** In practice the map / dependency list is largely **APM-derived** from call peers (**Observed (MCP)** for `node` → peer hostnames).
3. **“Detect = only monitors.”** **Watchdog** is a second Detect door (**Observed (MCP)**).
4. **“Alert = Incident.”** Monitors and Watchdog stories can fire with **zero** Incidents packaged (**Observed (MCP)**).

---

## 3. Building blocks (Datadog products)

Each block as **Input → Process → Output**. Use Datadog product names throughout.

### 3.1 Datadog Agent (edge collect)

| Role | Content |
|------|---------|
| **Input** | Host OS / processes / containers; optional APM libraries; log files / journal |
| **Process** | Collect system metrics; dogstatsd; optional APM / log forward; attach tags; export |
| **Output** | Streams into Metrics / APM / Logs intake |

**Observed (agent):** Agent v7 on WSL; hostname must be set explicitly or Agent exits; successful intake to `app.datadoghq.com`.  
**Observed (MCP):** Host appears with Agent `7.81.3`, `env:dev`.

### 3.2 Unified Service Tags / enrichment (Tagging)

In Datadog, **Tagging** is how identity is attached: every metric, span, and log gets the same keys so Metrics, APM, and Logs can be joined later.

| Tag | Role |
|-----|------|
| `service` | Which app / component |
| `env` | Which environment |
| `version` | Deploy version |
| `host` | Where it ran (often from the Agent) |

Plus Agent / container auto-tags and APM cues on spans (`status`, HTTP code, `peer.hostname`, …).

| Role | Content |
|------|---------|
| **Input** | Raw points / spans / logs |
| **Process** | Stamp the keys above |
| **Output** | Tag-joinable envelopes — still not an Incident |

#### Where tags come from

1. **App / tracer** — `DD_SERVICE`, `DD_ENV`, `DD_VERSION` (lab sets these per container in `datadog-rca-lab/docker-compose.yml`).
2. **Agent** — host tags, Docker/K8s auto-tags, `datadog.yaml` / `DD_TAGS`.
3. **APM enrichment** — peers and status on spans as traces are processed.

**Lab (Observed):** `env:rca-lab` + `service:frontend|product|inventory` + `version:1.0.0`. That is why Monitors and pivots scope with `env:rca-lab,service:inventory`.

#### Why it matters

Datadog’s **product rails** (Metrics ∥ APM ∥ Logs) stay separate explorers. The join key is **tags**. Backend is **not** three equal peer databases: classic **Metrics timeseries** vs **Husky** event store (logs + traces + other Event Platform products). See §3.3.

- Consistent tags → Related / monitors / flamegraph pivots work.
- Mistagged / unbound → orphan series, weak Related, noisy monitors.

Do **not** conflate two artifacts:

```
Telemetry stream  ──►  Tagging                         (identity on each record)  ← this stage
APM discovery     ──►  Service Map / dependencies      (edges)
```

Tags do not invent the Service Map; spans do. See also §8.

**Observed (MCP):** Spans carry `service:node`, `env:dev`, `host:DESKTOP-MBPAQK1`, `svc.auto:node`.

### 3.3 Metrics / APM / Logs (product rails · backend honesty)

| Product rail | Holds (operator) | Backend (official eng) | Observed here |
|--------------|------------------|------------------------|---------------|
| **Metrics** | Timeseries by tags | **Classic Metrics timeseries store** — pre-aggregated `<timeseries_id, timestamp, float64>`; bounded tag cardinality. *Not* Husky. | Host system metrics + lab `rca.*` / `trace.*.errors` |
| **APM / Traces** | Spans, resources, flamegraph | **Husky / Event Platform** — spans as events (with logs, NPM, RUM, …) | Lab KeyError spans; host auto `node` spans |
| **Logs** | Indexed log lines | **Husky / Event Platform** — high-cardinality events | Lab JSON + host syslog |

**Write = continuous. Query = on-demand** per product explorer. There is no Dynatrace-style single DQL lake name.

Cite: [Introducing Husky](https://www.datadoghq.com/blog/engineering/introducing-husky/) · [Husky query architecture](https://www.datadoghq.com/blog/engineering/husky-query-architecture/) (“logs, traces, network data, and more”).

**Lab nuance:** APM can also emit Metrics series (e.g. `trace.flask.request.errors`) while spans land as Husky events — dual emission, still tag-joined.

### 3.4 Service Catalog + Service Map / dependencies

| Role | Content |
|------|---------|
| **Input** | APM peers, process discovery, optional catalog YAML |
| **Process** | Upsert service names; materialize **calls / peer** edges from traces |
| **Output** | Catalog entries + dependency list for a service |

**Observed (MCP):** Catalog is discovery-heavy; `node` dependencies are **peer hostnames**, not typed microservice edges.  
**Does not:** store full metric history (that’s Metrics).

### 3.5 Monitors (explicit Detect)

| Role | Content |
|------|---------|
| **Input** | Metric / log / APM queries + thresholds / forecasts |
| **Process** | Async evaluation → OK / Warn / Alert / No Data |
| **Output** | Monitor status + notifications |

**Observed (MCP):** Host query monitors (mem, CPU, load, disk, network) all **OK** at snapshot; auto APM `web.request` error-rate monitor **OK**.

### 3.6 Watchdog (anomaly Detect)

| Role | Content |
|------|---------|
| **Input** | Platform series (APM / infra / logs categories) |
| **Process** | Statistical anomaly → **Watchdog story** → events (`source:watchdog`) |
| **Output** | Stories + events; optional bridge monitor on those events |

**Observed (MCP):**

- Story: error rate increased on resource `/bin/bash` in `service:node` (`story_type:error_rate`, `story_category:apm`)
- Bridge monitor: `events("source:watchdog (story_category:apm)")… > 0` → status **Alert**

**Alert ≠ Incident.** Stories can exist with no Incident object.

### 3.7 Insights / Bits AI / Incidents (package — thin)

| Role | Content |
|------|---------|
| **Input** | Alerts / stories; related services; scoped Metrics/APM/Logs |
| **Process** | **Correlational** relatedness / ranking; UI pivots (**Inferred** scoring) |
| **Output** | Insight assists / optional Incident card |

**Observed (MCP):** **0** Incidents. Treat packaging as **Public framing / Inferred** until a richer estate produces one.

### 3.8 Compact product chain

```text
Workloads
  → Datadog Agent
  → Tagging
  → Metrics ∥ APM ∥ Logs
       ├─► Service Catalog / Map (mostly from APM)
       ├─► Monitors → alert states
       └─► Watchdog → stories / events → (optional) event monitors
            → Operator pivots / Insights / Bits AI → (optional) Incident
```

---

## 4. Stores — what gets updated when

| Store | Holds | Touched at |
|-------|-------|------------|
| Agent (edge) | Collectors, buffers, export | Continuous collect |
| Metrics | Tag-keyed series | Continuous write; explorer = read |
| APM | Spans / resources / peers | Continuous write; trace search = read |
| Logs | Indexed lines | Continuous write; log search = read |
| Service Catalog / Map | Names + APM-derived edges | Discovery / trace materialization |
| Monitors | Alert state machines | Detect evaluation |
| Watchdog | Stories + events | Anomaly Detect |
| Incidents | Packaged operator cards | Optional; **absent** in this tenant snapshot |

---

## 5. Optional dual-vendor appendix (skip for Datadog-only reading)

This section exists only for later head-to-head compares. **Do not use it as Datadog’s product model.** Datadog teaching in this hub uses Agent, Tagging, Service Map, Metrics/APM/Logs, Monitors, Watchdog, Related, flamegraph, Insights/Incident.

| If you later map concepts | Datadog product reality |
|---------------------------|-------------------------|
| Edge collect | Datadog Agent |
| Identity bind | Unified Service Tags |
| Topology view | Service Catalog + APM-derived Service Map |
| Telemetry stores | Product rails Metrics ∥ APM ∥ Logs; backend Metrics timeseries ∥ Husky events |
| Alerting | Monitors **and** Watchdog |
| Investigation | Related + time/tag scope + flamegraph |
| Packaging | Insights / Bits AI / Incident (often thin here) |

Primary Datadog unveil stays on Datadog terms. Separate Dynatrace unveil: [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md). Optional same-scenario compare: [`COMPARABLE_PIPELINE_DT_DD.md`](./COMPARABLE_PIPELINE_DT_DD.md).

---

## 6. Observed walkthrough — this tenant

**Labels:** Observed (agent) + Observed (MCP). No Teaching fiction.

### 6.1 Setup

1. Agent installed on WSL; `hostname: DESKTOP-MBPAQK1` set so Agent can start (**Observed (agent)**).
2. Agent exports with `env:dev`.
3. Support-default monitors + Watchdog bridge appear after onboarding (**Observed (MCP)**).

### 6.2 Continuous fabric

```text
Agent on DESKTOP-MBPAQK1
  → Metrics: system.mem.pct_usable, system.load.norm.1, system.cpu.user, …
  → APM: service:node spans (shell, HTTP to MCP peers)
  → Logs: rsyslogd / other shippers on same host
  → Catalog: node, bash, peer.hostname:…, …
  → Map: node → peer.hostname:api2.cursor.sh | mcp.datadoghq.com | docs.mcp.cloudflare.com
```

### 6.3 Detect — two doors

**Door A — Monitors (query):** host CPU/mem/load/disk/network thresholds evaluate **OK** (usable mem ~45% ≫ 10% alert floor).

**Door B — Watchdog:** anomaly story on `service:node` resource `/bin/bash` (`error_rate`) writes `source:watchdog` events; bridge monitor rolls up by `story_key` → **Alert**.

### 6.4 What an operator does next (observed limits)

| Step | Available here? |
|------|-----------------|
| Open Watchdog story UI (`/watchdog/story/…`) | Yes (event links) |
| Pivot Metrics for `host:DESKTOP-MBPAQK1` | Yes |
| Pivot APM for `service:node` | Yes (auto spans) |
| Pivot Logs for host | Yes |
| Open a packaged **Incident** | **No** — count 0 |

**End fact:** Detect and multimodal evidence exist; **packaged RCA Incident does not** in this snapshot. That is an accurate Datadog-tenant observation, not a failure of the Agent.

---

## 7. Observed (lab) walkthrough — FE → product → inventory

**Labels:** Observed (lab) + Observed (MCP). Primary: [`datadog-lab-evidence-mtl-error-2026-08-10.md`](./datadog-lab-evidence-mtl-error-2026-08-10.md) · Timeline: [`dd-lab-timeline-error.html`](./dd-lab-timeline-error.html).

```text
curl :18080/api/checkout
        │
        ▼
   frontend ──ddtrace──► Agent :8126 ──► Datadog APM (env:rca-lab-e3)
        │                 DogStatsD :8125 ──► Metrics (rca.*)
        │                 file logs ──► Logs (rca_lab_logs.d)
        ▼
    product
        │
        ▼
  inventory  ← fault: HTTP 500 KeyError on /api/stock
```

### 7.1 What fired in the pipeline

| Stage | What we saw (e3 · 2026-08-10 MCP) |
|-------|-----------------------------------|
| **Agent** | Containers → host Trace Agent; DogStatsD `:8125`; log tail `rca_lab_logs.d` |
| **Tagging** | `service` + `env:rca-lab-e3` + `version:keyerror-20260810T072333Z` + container tags; same join keys on Metrics ∥ Logs |
| **Metrics ∥ Traces ∥ Logs** | `rca.inventory.stock.errors`≈**2403** · APM KeyError/500≈**2427** · Upstream*/502≈**2421** · Logs stock.error≈**2486** |
| **Service Map** | Trace peers `product` / `inventory`; FE→product→inventory |
| **Monitors · Watchdog** | Door A Flask `310925690` → **Alert** after sustain · Door B APM bridge `310485027` **OK** (0 APM stories) · logs_pattern_anomaly **present** · Incident **0** |
| **Flamegraph / Related** | Deepest `500`/`KeyError` on inventory (sample `6a79840f…`); confirm with log + `rca.inventory.stock.errors`; upstream `502` are symptoms |

### 7.2 Pipeline insight (Datadog-native)

1. **Errors fan out on the trace** — inventory 500 KeyError + product/frontend 502 all `status:error`. The operator (or Bits AI) correlates on the flamegraph; there is no auto `rootCauseEntity` field in this path.
2. **All three rails agree on the leaf** when the lab emits Metrics + Traces + Logs — use tag join (`env`/`service`/`trace_id`), not a second fabric.
3. **Service Map is laggy relative to traces** — trust the flamegraph/`peer.hostname` first for a fresh lab.
4. **Detect surfaces diverge** — Door A can Alert after sustain while APM Watchdog stays quiet and logs Watchdog stories fire; Detect ≠ Bits ≠ Incident.
5. **Join key is tags** — evidence lives in Metrics ∥ APM ∥ Logs scoped by `service` / `env:rca-lab-e3` / `version`.

---

## 8. Identity & bind (why tags matter)

Tagging here means **tags join** across Metrics ∥ APM ∥ Logs. Full model: **§3.2**.

| Later stage | Needs | If unbound / mistagged |
|-------------|-------|------------------------|
| Metrics / Logs / APM write | consistent `service` / `host` / `env` | Orphan series, weak Related |
| Service Map edges | peer services from traces | Floating peers / inferred hostnames |
| Monitors / Watchdog | tag scope on queries / stories | Wrong entity or noisy story |
| Related / flamegraph | related + scoped pull | Cannot name culprit honestly |

Two artifacts (do not conflate):

```text
APM discovery     ──►  Service Map / dependencies   (edges)
Telemetry stream  ──►  Tagging                      (identity on each record)
```

Unresolved `service:inv-svc-v2`: first-seen auto service, weak Related, or remapping (**Public framing**).

**Lab reminder:** compose sets `DD_SERVICE` / `DD_ENV=rca-lab` / `DD_VERSION=1.0.0` on FE, product, and inventory — the same keys you filter on in Monitors and pivots.

---

## 9. Known unknowns

| Topic | Status |
|-------|--------|
| Exact Watchdog / Bits AI scoring internals | Not published; black-box |
| When Insights auto-opens an Incident | Environment-dependent; **not observed** here |
| Retention / sampling SKUs | Not specified in this repo |
| Automated Step-2 path-diff fused into Incident | **Not verified** — [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) |
| Public top-1 RCA accuracy scoreboard | Self-reported / absent — [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) |

---

## 10. Related reading

| Doc | Use |
|-----|-----|
| [`dd-detect-category-hub.html`](./dd-detect-category-hub.html) | Detect category hub (ERROR · SLOWDOWN) |
| [`dd-e2e-metrics-traces-logs.html`](./dd-e2e-metrics-traces-logs.html) | Three-rail journey (animated write path; Metrics timeseries ∥ Husky events) |
| [`dd-error-mtl-dissection.html`](./dd-error-mtl-dissection.html) | ERROR · MTL deep (error-rate increase) |
| [`dd-lab-timeline-error.html`](./dd-lab-timeline-error.html) | ERROR Observed Timeline |
| [`dd-lab-timeline-slowdown.html`](./dd-lab-timeline-slowdown.html) | SLOWDOWN Observed Timeline |
| [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html) | Animated Datadog product mechanisms |
| [`datadog-tenant-evidence-2026-08-03.md`](./datadog-tenant-evidence-2026-08-03.md) | MCP snapshot citations (host / Watchdog baseline) |
| [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md) | FE→inventory lab run + trace IDs |
| [`datadog-lab-evidence-mtl-error-2026-08-07.md`](./datadog-lab-evidence-mtl-error-2026-08-07.md) | ERROR Metrics∥Traces∥Logs Observed numbers |
| [`../datadog-rca-lab/DATADOG_RCA_REFERENCE.md`](../datadog-rca-lab/DATADOG_RCA_REFERENCE.md) | Lab topology + fault scripts |
| [`COMPARABLE_PIPELINE_DT_DD.md`](./COMPARABLE_PIPELINE_DT_DD.md) | After independent unveils — derived patterns |
| [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) | Separate Dynatrace unveil |
| [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) | Fault buckets vs vendors |

---

## 11. Takeaway

1. Describe Datadog **as Datadog**: Agent → Tagging → Metrics/APM/Logs → Monitors **and** Watchdog → Related / flamegraph → optional Insights/Incident.
2. Service Map is largely **APM-derived**; product rails are separate explorers joined by **tags**; backend is Metrics timeseries ∥ Husky events (not three equal peer DBs).
3. Host snapshot proved **fabric + Watchdog**; the lab proved **microservice APM + auto error-rate monitors** and (2026-08-07) **full MTL leaf agreement** — still **not** a packaged Incident RCA card in this tenant.
4. Keep Datadog scenarios independent. Dual-vendor compares are a separate doc after each unveil stands alone.
