# Edge Delta → Motadata mapping notes

**Audience:** Engineers comparing Edge Delta (vendor) to Motadata ObserveOps (E1–E11) and Pillar B topology language.  
**Status:** Research notes cleaned from chat-style dumps. Not a decision to replace the Motadata build path.  
**MD** means Motadata / ObserveOps design language.

| Artifact | Role |
|----------|------|
| This file | Readable markdown source of the notes |
| [`Mapping ED to MD.pdf`](../../Mapping%20ED%20to%20MD.pdf) | Original PDF dump |
| Hub diagrams | [`edgedelta-to-motadata-mapping.html`](../../../docs/vendors/edgedelta-to-motadata-mapping.html) → [`:8765/edgedelta-to-motadata-mapping.html`](http://127.0.0.1:8765/edgedelta-to-motadata-mapping.html) |
| ED L0 hub | [`ed-ai-team-hub.html`](http://127.0.0.1:8765/ed-ai-team-hub.html) |
| Pillar B GraphWriter | [`graphwriter-io-walkthrough.html`](http://127.0.0.1:8765/graphwriter-io-walkthrough.html) |

---

## Table of contents

1. [Two Edge Delta “graph” products](#1-two-edge-delta-graph-products)
2. [Dual-layer product model](#2-dual-layer-product-model)
3. [Actual pipeline flow (data plane)](#3-actual-pipeline-flow-data-plane)
4. [Terminology crosswalk](#4-terminology-crosswalk)
5. [Multi-source architecture (three enterprise sources)](#5-multi-source-architecture-three-enterprise-sources)
6. [Node · Coordinator · Gateway](#6-node--coordinator--gateway)
7. [Destination types](#7-destination-types)
8. [Events · signals · alerts](#8-events--signals--alerts)
9. [CQL (Common Query Language)](#9-cql-common-query-language)
10. [MCP plane vs Knowledge Graph](#10-mcp-plane-vs-knowledge-graph)
11. [MCP `*_graph` tools are time series](#11-mcp-_graph-tools-are-time-series)
12. [Knowledge Graph consumers and value](#12-knowledge-graph-consumers-and-value)
13. [Investigation / RCA information flow](#13-investigation--rca-information-flow)
14. [Ingest shape: metadata wrap, not full rewrite](#14-ingest-shape-metadata-wrap-not-full-rewrite)
15. [Backend storage vs Knowledge Graph entries](#15-backend-storage-vs-knowledge-graph-entries)
16. [ObserveOps E1–E11 coverage (rough)](#16-observeops-e1e11-coverage-rough)
17. [Appendix — deferred delivery options](#17-appendix--deferred-delivery-options)

---

## 1. Two Edge Delta “graph” products

Edge Delta offers **two** topology-related capabilities. Do not conflate them with Motadata Pillar B `map/`, or with MCP tools named `*_graph`.

### 1.1 Knowledge Graph (AI Team)

Automatic environment map that **AI teammates** use during investigations.

**Requirements**

- Event connectors (non-streaming, read-only tools), for example: GitHub, GitLab, Slack, PagerDuty, Jira, Confluence, Notion, AWS, Grafana, Argo CD, Harness
- Kubernetes Service Map connector (the only **streaming** connector that contributes to the Knowledge Graph)

**Behavior**

- Discovery starts automatically ~3 minutes after connecting a connector (near zero config)
- Re-reconciles about every 24 hours
- Entity types include services, repositories, teams, channels, incidents, documents, cloud resources, people, and more

**What teammates use it for**

- Trace dependencies
- Compute blast radius
- Assess service criticality
- Find entity relationships
- Search across discovered entities

**Human UI:** Topology View (AI Team → Knowledge) — 3D “city of districts” visualization.

### 1.2 Service Map (Platform)

Visualizes **Kubernetes service-to-service communication**.

**Requirements**

- Agent version 1.24.0 or higher
- Pipeline with Kubernetes Service Map source (formerly `k8s_traffic_input`) connected to an Edge Delta destination

**Provides**

- Service interconnection view
- Per-service metrics: requests/min, errors/min, p95 latency
- Color by error rate; link thickness by volume
- Integration with Traces Explorer and Logs

**Technical notes**

- Uses eBPF at the kernel
- Resource-intensive (CPU / memory)
- Metrics such as `k8s.traffic.communication.latency.p95` and `k8s.traffic.communication.count`
- Can be disabled via Helm: `tracerProps.enabled=false`

### 1.3 Side-by-side

| Feature | Knowledge Graph | Service Map |
|---------|-----------------|-------------|
| Purpose | AI teammate context for investigations | Service communication visualization |
| Scope | Multi-system (repos, teams, incidents, cloud, K8s services, …) | Kubernetes services only |
| Data source | Event connectors + K8s Service Map connector | eBPF network traffic |
| Configuration | Automatic from connectors | Specific pipeline nodes |
| Access | AI Team → Knowledge | Platform → Service Map |
| Motadata closest | Estate relationships for Localize (but **vendor-private**) | Live `communicates_with`-style links (partial) |

---

## 2. Dual-layer product model

```text
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Telemetry Pipelines         │    │  AI Team                     │
│  (data plane)                │    │  (investigation plane)       │
│                              │    │                              │
│  Sources → Processors →      │    │  Knowledge Graph (internal)  │
│  Destinations                │    │  + MCP tools (telemetry)     │
│  + Service Map (eBPF)        │    │  SRE / Security teammates    │
│                              │    │                              │
│  Motadata ≈ E1–E5-ish jobs   │    │  Motadata ≈ E6–E11-ish jobs  │
└──────────────────────────────┘    └──────────────────────────────┘
```

---

## 3. Actual pipeline flow (data plane)

Edge Delta’s native flow is **not** Motadata `ingest.v1` / TelemetryEnvelope.

```text
Sources  →  Processors  →  Destinations
 collect     transform      route / store / alert
```

### 3.1 Sources (Motadata ≈ E1 Collect)

Examples: file logs, Kubernetes pod logs / API events, OTLP (4317 gRPC / 4318 HTTP), syslog, HTTP POST, cloud streams (Kinesis, Pub/Sub, Kafka, Event Hub), security feeds.

**Wire formats:** JSON, OTLP Protobuf, plain text, CEF, LEEF, syslog — **not** `ingest.v1` JSONL.

**Data model (conceptual):** logs, metrics, traces, events as typed items with attributes / resource.

**Edge Delta does not have at source**

- TelemetryEnvelope abstraction
- Required `ci_id` / `ci_type` (no CMDB bind at ingest)
- Motadata `fact_kind` enum
- Reserved classes such as `change_event`, `cmdb_sync`, `ticket`
- Schema-version reject at ingestion (parsers / processors handle format)

### 3.2 Processors (Motadata ≈ E2 normalize, plus Detect prep)

Typical chain ideas: parse JSON, add field / enrich, mask PII, filter, extract metric, pattern recognition (e.g. Drain), route, OTTL transforms.

Still **no native CMDB graph write**. Optional **lookup processor** can stamp a `ci_id` from a table (declared mapping, not Motadata Identity).

### 3.3 Destinations

See [§7](#7-destination-types). Threshold nodes emit **signals** to trigger destinations.

**Processing engine** = agent runtime. **Processors** = tools inside that engine (multiprocessor nodes chain them).

---

## 4. Terminology crosswalk

| Motadata / ObserveOps | Edge Delta | Notes |
|-----------------------|------------|-------|
| E1 Collect | Source nodes | Per-pipeline sources, not one global stage object |
| `ingest.v1` / TelemetryEnvelope | OTLP / JSON / syslog / … items | No single Motadata envelope |
| `ci_id` / `ci_type` | Resource attributes (`service.name`, `k8s.pod.name`, …) | Semantic conventions; optional lookup |
| `fact_kind` | Item types: log · metric · trace · event · **signal** | Different enum; “signal” ≠ Motadata `fact_kind` |
| E2 Identity | Processors (enrich / OTTL / lookup) | No resolved / synthesized identity gate |
| E3 Topology / `map/` | Knowledge Graph + Service Map | Two products; KG not a public GraphWriter store |
| E4 Stores / sketches | ED Platform (e.g. ClickHouse) + archive destinations | Not `sketch.v1` / `map/` contracts |
| E5 Maintain | Platform ops / pipeline redeploy | Different validity model |
| E6 Detect | Monitors · Threshold nodes | Monitor events vs pipeline signals |
| E7–E11 Curate → Package | AI Team teammates + workflows | Agentic; not Motadata case-seed contracts |
| WorkingSet / retrieval | MCP search + `*_graph` charts + (internal) KG | External agents: MCP only |

Motadata terminology can look ITIL/CMDB-like (`CI`, change, ticket). Edge Delta is telemetry-pipeline + AI Team, **not** a CMDB product. Connectors (Jira, PagerDuty, ServiceNow) bring **events** for context, usually not as primary source telemetry.

---

## 5. Multi-source architecture (three enterprise sources)

**Objective:** Edge Delta as SRE companion for RCA across:

1. Completely cloud telemetry (AWS) — Cloud Pipeline (agentless)
2. OTEL-based apps — Gateway Pipeline (recommended)
3. On-premise workloads — Node Pipeline (agent-based)

```text
AWS Cloud  → Cloud Pipeline (Lambda / CloudWatch / …)
                    ↓
OTEL Apps  → Gateway Pipeline (OTLP)  →  Edge Delta Platform
                    ↑                         ↓
On-Prem    → Node Pipelines (+ Coordinator)  AI Team (RCA)
```

| Source | Pipeline type | Role |
|--------|---------------|------|
| AWS cloud | Cloud Pipeline (agentless) or Gateway in ECS/EC2 | Serverless / streaming; CloudWatch packs; optional central aggregation |
| OTEL | Gateway (OTLP 4317 / 4318) | Trace context, tail sampling, service-level aggregation |
| On-prem K8s / VMs | Node DaemonSet + Coordinator | Local collect; eBPF Service Map; file / host metrics |

**AI Team layer**

- **Edge Delta MCP connector** — teammates query processed telemetry (logs / metrics / traces / events)
- **Specialized teammates** — SRE, Security Engineer, …
- **Event connectors** — PagerDuty, Slack/Teams, Jira, GitHub, …

**RCA loop (product story):** anomaly / monitor → AI investigation (CQL + MCP tools) → human review in channels → approved actions.

**Correlation tags:** prefer shared OTEL resource attributes (`service.name`, `environment`, `region`, …), not a separate Motadata `ci_id` namespace unless you add a lookup.

---

## 6. Node · Coordinator · Gateway

| Layer | Role |
|-------|------|
| **Node agents** (DaemonSet) | Collect node-local data |
| **Coordinator** (same cluster) | Control plane only: heartbeats, control messages, live features, leader election — **does not process telemetry** |
| **Gateway** (same or other cluster) | Aggregate / process from many nodes or OTLP collectors; cross-source ops |
| **Edge Delta backend** | Platform store, monitors, AI Team |

Typical hierarchy: Node → Coordinator (control) → Gateway (optional aggregation) → backend.

---

## 7. Destination types

| Kind | Examples | Behavior |
|------|----------|----------|
| **Archive** | S3, GCS, Azure Blob | Buffer then flush; gzip/zstd/snappy; JSON/Parquet; default flush ~30 min / ~16 MB |
| **Streaming** | ED Platform, Splunk, Datadog, Elastic, Kafka, HTTP | Near real-time as processed |
| **Trigger** | Slack, Teams, PagerDuty, ServiceNow, webhooks | Receive **signals** from Threshold nodes (edge alerts) |

---

## 8. Events · signals · alerts

Three similar words; different meanings.

| Term | Type | Generated by | Notes |
|------|------|--------------|-------|
| **Event** | Data item (`_type: event`) | K8s API, Windows Event Log, external connectors; or **Monitor events** (derived) | Original **or** derived |
| **Signal** | Data item (`_type: signal`) | Threshold nodes in pipelines | Always derived at the edge → trigger destinations |
| **Alert** | State / concept | Monitor state (OK / Warning / Alert / No Data); general “notification” language | UI “Alerts” often means signals |

**Environment availability (summary)**

| Environment | Infra events | Monitor events | Connectors | Pipeline signals |
|-------------|--------------|----------------|------------|------------------|
| Kubernetes | Yes (K8s) | Yes | Yes | Yes |
| Windows | Yes (Event Log) | Yes | Yes | Yes |
| Linux / macOS (non-K8s) | No K8s/Windows-style OS event source | Yes | Yes | Yes |

Example signal shape (illustrative):

```json
{
  "_type": "signal",
  "signal": {
    "title": "Threshold triggered",
    "description": "error-logs-per-minute hit threshold",
    "signal_id": "111022",
    "name": "error-logs-per-minute",
    "value": 55,
    "threshold_condition": "value > 5"
  }
}
```

---

## 9. CQL (Common Query Language)

**CQL = Common Query Language** (not “Context” Query Language).

Used in Logs / Metrics / Trace explorers, Kubernetes events, monitor events, rehydrations — and by AI teammates via MCP search tools.

**Examples**

```text
error
service.name:payment-api AND severity_text:ERROR
k8s.namespace.name:production
@status_code > 399
"connection failed" -timeout
statusCode:"*04"
```

**CQL vs OTTL:** CQL searches in the UI / MCP. Pipeline **filter processors** use OTTL (convert search → processor via Edge Delta’s Log Search to Filter guidance).

---

## 10. MCP plane vs Knowledge Graph

**MCP is not the telemetry ingest/output path.**

```text
Data plane:   Sources → Pipelines → Platform → Destinations
AI plane:     AI agents ↔ MCP Server ↔ REST API ↔ platform data
Knowledge Graph: separate store · teammate-internal access · Topology View for humans
```

| Path | Endpoint / mechanism | Purpose |
|------|----------------------|---------|
| Ingest / egress | Pipelines; optional `in.edgedelta.com` HTTP | Telemetry in/out |
| Query / manage | MCP (`…/mcp`) and REST (`api.edgedelta.com`) | Search, pipeline mgmt, charts |
| Knowledge Graph | Internal teammate capability | Topology / ownership / blast radius |

**Why Edge Delta’s own teammates also use MCP:** one permission model, audit trail, connector set, and a clean boundary between data plane and AI plane. Teammates are first-class MCP clients from the platform’s point of view.

### Who can query what

| Data | Access | Available to |
|------|--------|--------------|
| Logs / metrics / traces | REST via MCP tools | All agents (internal + external) |
| Pipelines / dashboards | REST via MCP tools | Agents with permission |
| Time-series charts | `get_*_graph` MCP tools | All MCP clients |
| Knowledge Graph | Internal teammate capability | **Edge Delta teammates only** |
| Topology View | UI | Humans |

Compared with Datadog Service Catalog / Dynatrace Smartscape (API-accessible topology), Edge Delta’s Knowledge Graph is a **teammate-private context layer**. Motadata Pillar B `map/` is intentionally a **published** estate store — a different product choice.

---

## 11. MCP `*_graph` tools are time series

Tools such as `get_log_graph`, `get_metric_graph`, `get_trace_graph`, `get_pattern_graph` return **bucketed charts over time**. They are **not** the Knowledge Graph and not a graph database.

| MCP tool | Meaning of “graph” | Returns |
|----------|--------------------|---------|
| `get_log_graph` | Time series of log counts | Bucketed volumes |
| `get_metric_graph` | Time series of a named metric | Aggregated series |
| `get_trace_graph` | Time series from traces | Counts or latency percentiles |
| `get_pattern_graph` | Time series of log patterns | Pattern counts (+ volatility filters) |
| Knowledge Graph | Topology / relationships | **Not** exposed via MCP |

**Search vs chart tools:** search returns individual records (large); graph tools return compact buckets (good for spotting trends before drilling in).

---

## 12. Knowledge Graph consumers and value

| Consumer | Access | Use |
|----------|--------|-----|
| Edge Delta AI teammates | Internal | Investigation, impact analysis |
| Humans | Topology View (read-only) | Explore environment |
| External AI agents | None | Cannot query KG |
| REST / MCP | None for KG | No public graph API |

**Value of building it (product story):** ownership, dependency, criticality, blast radius, and change context that raw logs/metrics/traces do not contain — so ED teammates triage with more than telemetry alone.

**Trade-off:** strength if you are all-in on Edge Delta AI Team; limitation / lock-in if you need external agents with equivalent topology tools (Motadata’s published `map/` targets a different openness model).

**How teammates query KG:** documented as “query / use / cite Knowledge references,” but **no public MCP tool or REST endpoint**. Treat the mechanism as an undocumented internal platform capability (inferred).

---

## 13. Investigation / RCA information flow

```text
① Detect (monitor / signal / PagerDuty)
        ↓
② Localize via Knowledge Graph (internal) — entity, neighbors, blast radius, owners
        ↓
③ Corroborate via MCP — get_log_search, get_*_graph, traces, metrics
        ↓
④ Package — thread citations, recommendations, approved actions
```

**Motadata-shaped seed reasoning (conceptual mapping)**

| Seed idea | Likely ED behavior |
|-----------|--------------------|
| Suspect service | KG entity lookup |
| Neighborhood | Dependencies / dependents / blast radius |
| Time window | Anomaly window + recent change hints from connectors |
| Evidence | MCP telemetry tools |

External agents can do **③**; only ED teammates get **②** via the Knowledge Graph.

---

## 14. Ingest shape: metadata wrap, not full rewrite

Edge Delta typically does **not** rewrite the entire payload into a new schema. Pattern:

- Original content stays in **`body`** (largely unchanged)
- **Metadata envelope** is added: timestamp, severity, attributes, resource, optional trace/span ids

Illustrative log item:

```json
{
  "body": "<original log message unchanged>",
  "timestamp": "2024-01-15T10:30:00Z",
  "severity_text": "ERROR",
  "trace_id": "abc123...",
  "span_id": "xyz789...",
  "attributes": {
    "service.name": "payment-api",
    "environment": "production",
    "k8s.pod.name": "payment-api-7d9f8b-abc"
  },
  "resource": {
    "host.name": "node-1",
    "k8s.deployment.name": "payment-api",
    "container.id": "docker://abc123"
  }
}
```

Cost-sensitive insight: prefer **tagging / enveloping** over deep format conversion.

---

## 15. Backend storage vs Knowledge Graph entries

These are **different stores**.

### 15.1 Backend / platform telemetry (query with CQL + MCP)

Stores time-series telemetry (logs, metrics, traces, events). Conceptual log entry:

```json
{
  "id": "uuid-log-entry-123",
  "timestamp": "2024-01-15T10:30:00Z",
  "body": "Payment processing failed for order #12345",
  "severity_text": "ERROR",
  "attributes": {
    "service.name": "payment-api",
    "http.method": "POST",
    "error.code": "TIMEOUT"
  },
  "resource": {
    "k8s.deployment.name": "payment-api",
    "k8s.pod.name": "payment-api-7d9f8b-abc",
    "host.name": "node-1"
  },
  "trace_id": "abc123...",
  "span_id": "xyz789..."
}
```

### 15.2 Knowledge Graph (entity relationships — conceptual)

Stores entities and relationships (services, repos, teams, ownership, depends-on, …). Illustrative shape:

```json
{
  "nodes": [
    {
      "id": "service:payment-api",
      "type": "Service",
      "name": "payment-api",
      "criticality": 0.92,
      "source_connector": "kubernetes",
      "confidence": 0.98
    },
    {
      "id": "repo:payment-service-repo",
      "type": "Repository",
      "name": "payment-service",
      "source_connector": "github"
    },
    {
      "id": "team:platform",
      "type": "Team",
      "name": "Platform Team"
    }
  ],
  "relationships": [
    {
      "from": "service:payment-api",
      "to": "repo:payment-service-repo",
      "type": "DEPLOYED_FROM",
      "confidence": 1.0
    },
    {
      "from": "team:platform",
      "to": "service:payment-api",
      "type": "OWNS",
      "confidence": 0.95
    },
    {
      "from": "service:payment-api",
      "to": "service:order-api",
      "type": "DEPENDS_ON",
      "weight": 0.85
    }
  ]
}
```

| Aspect | Backend storage | Knowledge Graph |
|--------|-----------------|-----------------|
| Data type | Time-series telemetry | Entity / relationship graph |
| Query | CQL + MCP tools | Internal teammate capability only |
| Public API | REST / MCP | No dedicated public API (as of these notes) |

---

## 16. ObserveOps E1–E11 coverage (rough)

Use as a **research map**, not a migration scorecard. Motadata’s build path remains ObserveOps + Pillar A∥B.

| ObserveOps | Edge Delta locus | Fit | Watch-outs |
|------------|------------------|-----|------------|
| E1 Collect | Source nodes / pipeline types | Strong | Different wire formats |
| E2 Identity | Processors · lookup · OTTL | Partial | No Motadata identity statuses |
| E3 Topology | Knowledge Graph · Service Map | Partial | KG private; Service Map K8s-centric |
| E4 Stores | ED Platform · archive dests | Strong as vendor store | Not `sketch.v1` / `map/` contracts |
| E5 Maintain | Platform ops · redeploy | Partial | Different validity model |
| E6 Detect | Monitors · Threshold signals | Strong | Events vs signals naming |
| E7 Curate | Composite monitors / AI merge | Different | No Motadata case_seed contract |
| E8–E10 | AI teammates | Strong (agentic) | KG moat for localize |
| E11 Package | Threads · actions · ITSM connectors | Strong | Approval workflows differ |

---

## 17. Appendix — deferred delivery options

The original notes included conversational “pick option 1–6” trees (YAML templates, POC day plans, ADR drafts, TCO, risk registers). Those are **delivery choices**, not information-flow architecture. Keep them out of the main map unless a specific POC is kicked off.

If needed later: start from ED hub + this document’s architecture sections, then draft a Motadata-framed ADR (evaluate / hybrid / vendor lens) — not an automatic “replace E1–E11” decision.

---

## References (Edge Delta public docs themes)

Names as used in the notes (resolve on docs.edgedelta.com):

- Knowledge Graph · Service Map · Kubernetes Service Map Source · Connectors
- Edge Delta Architecture · Ingestion Pipelines · Processors · Pipeline Triggers
- Cloud / Gateway / Node / Coordinator pipelines · OTLP Connector
- Common Query Language (CQL) · MCP Server / Edge Delta MCP Connector
- AI Team Overview · Threshold Node · Monitors · Data Item Examples
