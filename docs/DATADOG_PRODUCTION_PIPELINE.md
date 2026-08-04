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

1. **“Platform lake = Grail.”** Datadog ships **separate** Metrics, APM, and Logs products. “Lake” here is our shorthand for those indexes sharing tags — **Public framing / Inferred**.
2. **“Service Map is written in parallel like Smartscape.”** In practice the map / dependency list is largely **APM-derived** from call peers (**Observed (MCP)** for `node` → peer hostnames).
3. **“Detect = only monitors.”** **Watchdog** is a second Detect door (**Observed (MCP)**).
4. **“Alert = Incident.”** Monitors and Watchdog stories can fire with **zero** Incidents packaged (**Observed (MCP)**).

---

## 3. Building blocks (Datadog products)

Each block as **Input → Process → Output**. Prefer product names over Clock A until §5.

### 3.1 Datadog Agent (edge collect)

| Role | Content |
|------|---------|
| **Input** | Host OS / processes / containers; optional APM libraries; log files / journal |
| **Process** | Collect system metrics; dogstatsd; optional APM / log forward; attach tags; export |
| **Output** | Streams into Metrics / APM / Logs intake |

**Observed (agent):** Agent v7 on WSL; hostname must be set explicitly or Agent exits; successful intake to `app.datadoghq.com`.  
**Observed (MCP):** Host appears with Agent `7.81.3`, `env:dev`.

### 3.2 Unified Service Tags / enrichment

| Role | Content |
|------|---------|
| **Input** | Raw points / spans / logs |
| **Process** | Stamp `service`, `env`, `version`, `host` (and peers); failure / status cues on spans |
| **Output** | Tag-joinable envelopes — still not an Incident |

**Observed (MCP):** Spans carry `service:node`, `env:dev`, `host:DESKTOP-MBPAQK1`, `svc.auto:node`.

### 3.3 Metrics / APM / Logs (three stores)

| Store | Holds | Observed here |
|-------|-------|---------------|
| **Metrics** | Timeseries by tags | Host system metrics live |
| **APM** | Spans, resources, service entry points | Auto `node` spans + peer HTTP |
| **Logs** | Indexed log lines by tags | Host syslog + other shippers |

**Write = continuous. Query = on-demand.** There is no single DQL lake name in this product framing.

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

## 5. Clock A translation (optional lens — imperfect fit)

We keep **our** Clock A vocabulary as a **translation layer** for later compares — not as Datadog’s native architecture.

| Clock A stage | Closest Datadog reality | Fit notes |
|---------------|-------------------------|-----------|
| **Collect** | Datadog Agent | Strong |
| **Normalize** | Unified Service Tags / enrichment | Strong (tag-centric, not `entityId`-centric) |
| **Topology bind** | Catalog + APM dependencies + tag resolution | Weaker / different — map is **derived**, not Smartscape-class typed CI |
| **Fan-out** | Write into Metrics + APM + Logs | **Not** “map ∥ lake twin”; map is mostly a view on APM |
| **Maintain** | Retention / indexing / discovery freshness | Strong as product ops |
| **Detect** | Monitors **and** Watchdog | Two doors |
| **Curate** | Grouping / primary symptom selection | Partial / UI-heavy; **Inferred** |
| **Tailor** | Related + time-scoped query | Public framing; correlational |
| **Package** | Insights / Bits AI / Incident | Thin; not observed as Incident here |

**Do not** force Datadog into “Smartscape ∥ Grail → Davis.” That is Dynatrace’s story ([`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md)).

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

**Labels:** Observed (lab) + Observed (MCP). Same topology as `dynatrace-rca-lab`. Detail: [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md).

```text
curl :18080/api/checkout
        │
        ▼
   frontend ──ddtrace──► Agent :8126 ──► Datadog APM (env:rca-lab)
        │
        ▼
    product
        │
        ▼
  inventory  ← fault: HTTP 503 on /api/stock
```

### 7.1 What fired in the pipeline

| Stage | What we saw |
|-------|-------------|
| **Collect** | Containers → host Trace Agent (`apm_non_local_traffic`) → `trace.agent.datadoghq.com` |
| **Normalize / tags** | `service` + `env:rca-lab` + `version:1.0.0` + container tags; HTTP status on spans |
| **Map (APM-derived)** | Trace shows `peer.hostname:product` / `peer.hostname:inventory` client edges. Catalog dependency API empty at T+~2m — map lag vs flamegraph |
| **Detect** | Auto monitor `[operation:flask.request] High Error Rate…` **created** when Flask traffic appeared (`min(last_15m)` error ratio `> 0.1`). **Watchdog:** no new `source:watchdog` events in the short window |
| **Operator Tailor** | Open error trace → deepest `503` on inventory; upstream `502` on product/frontend are symptoms |

### 7.2 Pipeline insight (vs Dynatrace mental model)

1. **Errors fan out on the trace** — inventory 503 + product/frontend 502 all `status:error`. Datadog does not collapse to one `rootCauseEntity` here; the operator (or Bits AI) correlates.
2. **Service Map is laggy relative to traces** — trust the flamegraph/`peer.hostname` first for a fresh lab.
3. **Detect default for this fault is APM monitor auto-gen**, not Watchdog story — Watchdog remains a second door that may not open on a short synthetic spike.
4. **No Smartscape∥Grail** — evidence lives in APM (and optionally Metrics/Logs); join key is **tags**, not a single multimodal lake query.

---

## 8. Identity & bind (why tags matter)

Normalize / bind here means **tags join**, not Dynatrace `entityId` stamping.

| Later stage | Needs | If unbound / mistagged |
|-------------|-------|------------------------|
| Metrics / Logs / APM write | consistent `service` / `host` / `env` | Orphan series, weak Related |
| Service Map edges | peer services from traces | Floating peers / inferred hostnames |
| Monitors / Watchdog | tag scope on queries / stories | Wrong entity or noisy story |
| Operator Tailor | related + scoped pull | Cannot name culprit honestly |

Two artifacts (do not conflate):

```text
APM discovery     ──►  Service Map / dependencies   (edges)
Telemetry stream  ──►  Tag resolution               (identity on each record)
```

Unresolved `service:inv-svc-v2`: first-seen auto service, weak Related, or remapping (**Public framing**).

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
| [`datadog-tenant-evidence-2026-08-03.md`](./datadog-tenant-evidence-2026-08-03.md) | MCP snapshot citations (host / Watchdog baseline) |
| [`datadog-lab-evidence-2026-08-04.md`](./datadog-lab-evidence-2026-08-04.md) | FE→inventory lab run + trace IDs |
| [`../datadog-rca-lab/DATADOG_RCA_REFERENCE.md`](../datadog-rca-lab/DATADOG_RCA_REFERENCE.md) | Lab topology + fault scripts |
| [`datadog-subsystem-mechanisms.html`](./datadog-subsystem-mechanisms.html) | Animated Datadog product mechanisms |
| [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) | Separate Dynatrace unveil (topology-first) |
| [`RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md`](./RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md) §4.3 · §4.5 | Short Datadog vs Dynatrace matrix (planning) |
| [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) | Fault buckets vs vendors |

---

## 11. Takeaway

1. Describe Datadog **as Datadog**: Agent → tagged Metrics/APM/Logs → Monitors **and** Watchdog → correlational operator assist.
2. **Do not** clone Smartscape∥Grail; Service Map is largely **APM-derived**; stores are **product-split**.
3. Host snapshot proved **fabric + Watchdog Detect**; the lab proved **microservice APM + auto error-rate Detect** — still **not** a packaged Incident RCA card.
4. Clock A is a **translation lens** with imperfect fits — use it after the native model, not before.
5. Head-to-head comparison waits until both vendor unveils stand alone on their own evidence.
