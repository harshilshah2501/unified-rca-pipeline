# Edge Delta tenant evidence — 2026-08-14

**Org:** `gmailcom_d4486595` (`6da947fe-77af-421e-8a9c-dda8ead0b393`)  
**User:** Harshil Shah (`harshilshah25@gmail.com`) — Account Owner  
**App:** [https://app.edgedelta.com/ai/overview](https://app.edgedelta.com/ai/overview)  
**Method:** Observed (UI) after interactive login in Cursor browser. No Edge Delta MCP/API pull this session.  
**Plan:** Free · ends 2026-08-28 (13 days left) · 1 user · credits **13 / 50** (AI Token 13 · Storage 0 · Sandbox 0 · Cloud Compute 0)

This appendix grounds **Observed (UI)** claims in [`EDGEDELTA_PRODUCTION_PIPELINE.md`](./EDGEDELTA_PRODUCTION_PIPELINE.md). It is a snapshot of a **brand-new org** (user created 2026-08-14 14:41 IST), not a product specification and not a same-scenario RCA lab.

Screenshots: [`vendor-source/edgedelta/`](../vendor-source/edgedelta/)

---

## Honesty

| Label | Meaning |
|-------|---------|
| **Observed (UI)** | Seen in this tenant on 2026-08-14 |
| **Public framing** | Edge Delta docs / marketing — not proven here |
| **Inferred** | Fits observations + docs; not an Edge Delta-internal spec |

Empty explorers are **Observed**, not a product gap. This org has not deployed a telemetry pipeline that writes logs/traces into the Platform.

---

## 1. Primary nav (Observed UI)

Landing page after login is **AI Team → Overview**. Primary sidebar:

| Section | Items |
|---------|--------|
| AI | AI Team (current) · Guardrails |
| MONITOR | Monitors · Events |
| EXPLORE | Dashboards · Logs · Metrics · Traces · Service Map |
| SETTINGS | Admin |

**No Pipelines item** in this tenant’s primary nav. `https://app.edgedelta.com/pipelines` redirected to `/ai/overview`. Pipeline-related settings live at Admin → Global Data Settings (`/pipeline/settings`).

---

## 2. AI Overview (Observed UI)

URL: `/ai/overview` · screenshot `ed-ai-overview-2026-08-14.png`

| Panel | Value |
|-------|--------|
| Health score | **100% · Healthy** |
| Last 7 days | New **0** · Re-Opened **0** · Resolved **0** · MTTR **—** |
| Incident timeline | Solid green buckets Aug 8 → Today |
| Active Issues | **0** · “All clear! No active issues” |
| Suggested START prompts | Template copy (checkout latency / auth token / CDN) — **not** tenant incidents |
| Live Ops | “No agent activity yet” |

**Recent threads (1):**

| Thread | Human actions | Status | Channel | Time | Source |
|--------|---------------|--------|---------|------|--------|
| Daily GitHub Activity and Risk Report | No action required | Resolved | `#code-issues` | 3:00 PM | Workflow |

No Issue cards existed to open. Packaging surface this session = Overview + one Workflow thread, not an Issue.

---

## 3. Teammates (Observed UI)

URL: `/ai/teammates` · screenshot `ed-teammates-2026-08-14.png`

Four specialized teammates, all Account Owner. Performance: “No score yet / No response data” on every card.

| # | Role | Model | Last active (UI) | Visible connectors / channels (screenshot) |
|---|------|-------|------------------|--------------------------------------------|
| 01 | Security Engineer | Opus 4.8 | ~26m | GitHub · `#alerts` · `#security-issues` |
| 02 | Software Engineer | GPT-5.6 Sol | ~6m | GitHub · `#code-issues` · `#alerts` |
| 03 | SRE | Opus 5 | ~26m | (card below fold; role copy Observed) |
| 04 | Work Tracker | Opus 4.8 | ~26m | UI listed Connectors/Channels as None in a11y tree |

SRE role copy (Observed): “Detects symptoms, builds timelines, summarizes impact, correlates metrics/logs, proposes mitigations, pages on-call, and drafts postmortems.”

**OnCall AI** is **Public framing** (docs: orchestrator). It did **not** appear as a Teammates card in this snapshot.

---

## 4. Connectors (Observed UI)

URL: `/ai/connectors` · screenshot `ed-connectors-2026-08-14.png`

| Connector | Status |
|-----------|--------|
| GitHub | Connected |
| Edge Delta MCP | Connected |
| Edge Delta Documentation | Connected |

No Datadog, Splunk, PagerDuty, or other streaming/event destinations Observed. Fan-out-to-Datadog remains **Public framing**, not Observed on this tenant.

---

## 5. Monitors (Observed UI)

URL: `/monitors/list` · screenshot `ed-monitors-2026-08-14.png`

Five monitors. Filter rollup: Status No Data **4** · OK **1** · Alert **0** · Warn **0**. Types: Event Threshold **3** · Pattern Anomaly **1** · Metric Threshold **1**. Creators: Edge Delta **3** · `harshilshah25@gmail.com` **2**.

| Priority | Status | Name | Type |
|----------|--------|------|------|
| High | No Data | GitHub CI Failure Monitor | Event Threshold |
| Medium | No Data | GitHub PR Review Monitor | Event Threshold |
| Medium | No Data | GitHub Push Event Monitor | Event Threshold |
| High | **OK** | Default Pipeline Liveness Monitor | Metric Threshold (`count:heartbeat`) |
| High | No Data | Default Service Anomaly Monitor | Pattern Anomaly |

**Reading:** GitHub event monitors exist but have no matching event volume in-window. Pattern Anomaly has no log patterns to score. Pipeline liveness **OK** is the only green Detect door — a heartbeat, not an application fault class.

---

## 6. Workflows (Observed UI)

URL: `/ai/workflows` · screenshot `ed-workflows-2026-08-14.png`

Four Edge Delta–authored workflows. Compare-window stats all showed **0.0%** (empty run counters in the 7d-vs-prior widget). The Overview thread still proves at least the GitHub daily report fired once today.

| Workflow | Steps (UI) | Shape |
|----------|------------|--------|
| Daily Report - github | 4 | Start → Action (channel message) → Task → Action (email) |
| Default Service Anomaly Workflow | 3 | Start → Teammate (SRE) → Action (email) |
| Default Workflow - Company Page Daily Summary | 4 | Start → Teammate (SRE) → If/Else Healthy → Action (email) |
| Default Pipeline Liveness Workflow | 3 | Start → Teammate (SRE) → Action (email) |

---

## 7. Explorers — empty fabric (Observed UI)

| Surface | URL | Result |
|---------|-----|--------|
| Logs Search | `/logs/search` | **0 results** · Base → Pipeline **No options found** |
| Metrics Explorer | `/metrics/explorer` | Default query `sum:ed.pipeline.node.read_bytes{*}.rollup(60)` · empty series · Pipeline **No options found** |
| Traces | `/traces` | **No traces found** · Pipeline **No options found** |
| Service Map | `/service-map` | “There was an error processing the request” · Pipeline **No options found** |

Screenshots: `ed-logs-2026-08-14.png` · `ed-metrics-2026-08-14.png` · `ed-service-map-2026-08-14.png`

**Reading:** Logs / Metrics / Traces / Service Map exist as product rails, but this tenant has **no named pipeline** feeding them. Do not treat empty Service Map as “ED has no topology product.”

---

## 8. Admin / ingestion prefs (Observed UI)

- Global Data Settings (`/pipeline/settings`): Agent Self Logs, Alerts, Log Archiving, Log Patterns, Log Pattern Samples, Alert Contextual Logs, Events, Agent Health Data, Agent Heartbeats, Metrics, Traces — all **Enabled**. No configuration variables.
- Usage Report (`/admin/usage`): token charts **No data available / 0 TOKENS** for Aug 8–14. Plan page still showed **13 AI credits** consumed — credit counter ≠ empty usage charts. Record both; do not reconcile internally.

---

## 9. What this snapshot can and cannot support

**Can support**

- AI Overview as the operator landing page (health score, Issues list, threads, live feed).
- Specialized teammates + connectors + monitors + workflows as the AI Team layer.
- Detect doors present: Event Threshold · Pattern Anomaly · Metric Threshold (liveness).
- Issue count = 0 is a valid Observed packaging outcome (like DD Incident **0**).

**Cannot support (yet)**

- Same-scenario FE→product→inventory lab.
- Pattern-anomaly Detect on application logs.
- eBPF Service Map as a walkable graph.
- Fan-out to Datadog / Splunk.
- Issue lifecycle (match / occurrence count / action approval columns) — no Issue existed to open.

---

## MCP follow-up (same day, after Docker MCP install)

**Observed (MCP)** against org `6da947fe-77af-421e-8a9c-dda8ead0b393`:

| Object | Result |
|--------|--------|
| Pipelines | **1:** `AI-Connector-Telemetry-Pipeline` (`dc098347-4420-41b8-ad1b-95678d8ad6ba`) · `IngestionPipeline` · `purpose=edgedelta-ai` · GitHub HTTP ingest → `ed_ai_event_output` |
| `event.type` | **0** values |

Catalogs (Public framing, not this tenant’s installed set): see [`EDGEDELTA_SUPPORTED_SCENARIOS.md`](./EDGEDELTA_SUPPORTED_SCENARIOS.md).
