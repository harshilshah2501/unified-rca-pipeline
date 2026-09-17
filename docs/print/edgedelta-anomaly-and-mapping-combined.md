---
title: "Edge Delta — Anomaly Detection & Motadata Mapping Notes"
subtitle: "Combined printable brief (A4)"
author: "Unified-RCA research notes"
date: "2026-09-15"
geometry:
  - a4paper
  - margin=14mm
fontsize: 10pt
mainfont: DejaVu Sans
monofont: DejaVu Sans Mono
colorlinks: true
linkcolor: "black"
urlcolor: "blue"
header-includes:
  - \usepackage{fancyhdr}
  - \usepackage{titlesec}
  - \titlespacing*{\section}{0pt}{0.8em}{0.4em}
  - \titlespacing*{\subsection}{0pt}{0.6em}{0.3em}
  - \titlespacing*{\subsubsection}{0pt}{0.5em}{0.25em}
  - \pagestyle{fancy}
  - \fancyhf{}
  - \fancyhead[L]{\footnotesize Edge Delta notes}
  - \fancyhead[R]{\footnotesize Unified-RCA}
  - \fancyfoot[C]{\thepage}
  - \renewcommand{\headrulewidth}{0.3pt}
  - \setlength{\parskip}{0.35em}
  - \setlength{\parindent}{0pt}
  - \renewcommand{\baselinestretch}{1.05}
---

\newpage

# Contents of this PDF

This printable brief combines two repository documents:

1. **Anomaly detection** — how Edge Delta baselines, monitors, and edge-versus-platform detection work (`docs/anomaly-detection.md`).
2. **Edge Delta concepts for Motadata / ObserveOps mapping** — multi-source architecture, telemetry model, MCP/CQL, and Knowledge Graph notes (`pillar-ab-implementation/pillar-b/references/ED-MD-New.md`).

Mermaid diagrams from the source markdown are rendered as text diagram blocks for reliable print.

\newpage



# Part I — Anomaly detection

## Edge Delta anomaly detection

How Edge Delta detects anomalies in logs and metrics, how baselines are computed, where work runs (agent versus platform), and why baselines are not pushed back to agents.

This page consolidates Edge Delta official-documentation concepts into a single reading path. For product reference pages, see [References](#references) at the end.

---

## Contents

1. [How anomaly detection works](#1-how-anomaly-detection-works)
2. [How baselines are computed](#2-how-baselines-are-computed)
3. [Metric Threshold versus Metric Anomaly monitors](#3-metric-threshold-versus-metric-anomaly-monitors)
4. [Where detection runs: edge versus platform](#4-where-detection-runs-edge-versus-platform)
5. [Is there a feedback loop to agents?](#5-is-there-a-feedback-loop-to-agents)
6. [Would pushing baselines to the edge be better?](#6-would-pushing-baselines-to-the-edge-be-better)
7. [References](#references)

---

## 1. How anomaly detection works

Edge Delta compares **current telemetry behaviour** against a **dynamically computed baseline**. For logs, the path is: cluster similar messages into patterns, score those patterns for spikes against history, then evaluate spike counts in a monitor.

### 1.1 Pattern detection (logs)

Edge Delta uses the **Drain** algorithm to cluster similar logs into patterns by replacing variable parts with wildcards.

**Raw logs:**

```text
User 12345 logged in from 192.168.1.1
User 67890 logged in from 10.0.0.5
User 99123 logged in from 172.16.0.3
```

**Become one pattern:**

```text
User * logged in from *
```

Each pattern is classified as **negative** (errors, failures) or **neutral**, based on keywords such as `error`, `failed`, and `panic` configured in Global Data Settings.

### 1.2 Anomaly scoring pipeline

The system evaluates patterns in three stages.

#### Stage 1 — Baseline establishment

- Collects pattern frequency and volume over a rolling window.
- Window size comes from the monitor **lookback period** (for example, last 7 days).
- Builds a statistical baseline of “normal” behaviour for each pattern.

#### Stage 2 — Spike detection

- Compares current pattern counts to the baseline.
- Flags when frequency **deviates significantly** from historical norms.
- Both **increases in existing negative patterns** and **new pattern appearances** count as spikes.

#### Stage 3 — Sensitivity filtering

| Sensitivity | Effect |
|-------------|--------|
| Lower | Smaller deviations count as spikes → more alerts |
| Higher | Only large deviations count → fewer alerts |

**Output:** pattern anomaly count (number of spikes detected).

### 1.3 Threshold evaluation

The **Pattern Anomaly Monitor** compares the spike count to configured thresholds:

- **Warning threshold** — early warning
- **Alert threshold** — critical alert

### 1.4 Example scenario

| Setting | Value |
|---------|--------|
| Baseline period | Last 7 days |
| Normal baseline | Pattern `Database connection timeout for host *` ≈ **5 times/hour** |
| Spread | About ±2 times/hour |
| Current window | Same pattern ≈ **25 times/hour** |

**Detection:**

- Deviation: 25 vs 5 → about a **400%** increase.
- If sensitivity treats ~3× deviations as spikes → **spike detected**.
- If spike count exceeds the alert threshold → **alert fires**.

### 1.5 Patterns UI signals

The Patterns tab shows behaviour over time, including:

- **Increasing** — volume rising
- **Decreasing** — volume falling
- **New** — first appearance
- **Disappeared** — no longer seen
- **Sentiment** — negative versus neutral

AI teammates can then investigate anomalies, correlate with other telemetry, and propose remediation.

---

## 2. How baselines are computed

### 2.1 Pattern anomalies

| Aspect | Behaviour |
|--------|-----------|
| Window | Rolling / sliding, sized by the monitor **lookback period** |
| Input | Historical pattern frequency (for example, 7 days of hourly counts) |
| Scope | Expected frequency range per pattern / source combination |
| Updates | Continuous as new data arrives |

### 2.2 Metric anomalies (statistical rolling baseline)

Typical configuration:

| Setting | Example |
|---------|---------|
| Historical window | 10 datapoints (default; range 5–100) |
| Rollup window | 1 minute |
| Alert threshold | 5 standard deviations |

**Computation:**

```text
baseline_mean      = average of last N evaluated datapoints
standard_deviation = computed from those N datapoints
alert_band_upper   = baseline_mean + (threshold × standard_deviation)
alert_band_lower   = baseline_mean - (threshold × standard_deviation)
```

**Numeric example**

Last 10 CPU measurements (millicores):

```text
[120, 115, 125, 118, 122, 119, 121, 123, 117, 120]
```

| Stat | Value |
|------|--------|
| Mean | 120 |
| Std Dev | ≈ 3.16 |
| Alert band (5σ) | **[104.2, 135.8]** |

If current CPU = **150** → above the upper band → **anomaly detected**.

### 2.3 Baseline characteristics

| Aspect | Behaviour |
|--------|-----------|
| Window type | Rolling / sliding — oldest point drops as a new one arrives |
| Adaptation | Continuously updates to recent behaviour |
| Warmup | No alerts until the window has enough data |
| Per-group | Separate baselines (for example, per service or host) |
| Metric-specific | Each pattern or metric keeps its own baseline |

---

## 3. Metric Threshold versus Metric Anomaly monitors

Edge Delta provides **two different metric monitor types**. They are not the same, and only one of them needs a historical window.

### 3.1 Metric Threshold Monitor (fixed user thresholds)

**Historical window: not needed.** You set fixed threshold values.

| Step | What happens |
|------|----------------|
| Configure | Static rule such as “alert if CPU > 80%” |
| Evaluate | Current value versus that fixed threshold |
| Trigger | When the value crosses above / below / equals the threshold |

**Example**

```text
Monitor:  CPU Utilization
Alert:    Above 80%
Warning:  Above 60%
```

If current CPU = **85%** → alert fires immediately. No baseline comparison.

### 3.2 Metric Anomaly Monitor (statistical baseline)

**Historical window: required.** Thresholds are dynamic bands from recent behaviour.

| Step | What happens |
|------|----------------|
| Configure | Rolling window of N datapoints (default 10) |
| Compute | Mean and standard deviation from that window |
| Threshold | Expressed as **standard deviations from the mean** (default 5σ) |
| Detect | Deviations from **learned normal**, not a fixed absolute |

**Example**

```text
Monitor:            CPU Utilization
Historical window:  10 datapoints
Alert threshold:    5 standard deviations

Last 10 readings:   [20%, 22%, 19%, 21%, 23%, 20%, 22%, 21%, 19%, 23%]
Mean:               21%
Std Dev:            ≈ 1.4%
Alert band:         21% ± (5 × 1.4%) ≈ [14%, 28%]
```

If current CPU = **85%** → far outside the band → alert.  
For a service that **normally** runs near 80%, **85%** might **not** alert, because it stays inside that service’s normal deviation.

### 3.3 When to use each

| Scenario | Prefer | Reason |
|----------|--------|--------|
| Known safe limits (disk at 90% is always bad) | Metric Threshold | Exact breaking point is known |
| Predictable ceilings (memory limits) | Metric Threshold | Fixed capacity |
| Natural variation (request rates) | Metric Anomaly | Adapts to traffic |
| Gradual drift (growing database size) | Metric Anomaly | Fixed thresholds need constant retuning |
| Compliance (“must stay below X”) | Metric Threshold | Regulatory limits are fixed |
| Unknown “normal” for new services | Metric Anomaly | Learns baseline automatically |

### 3.4 Side-by-side summary

| Aspect | Metric Threshold Monitor | Metric Anomaly Monitor |
|--------|--------------------------|------------------------|
| Threshold type | Fixed value you set | Dynamic statistical band |
| Historical window | Not needed | Required (5–100 datapoints) |
| Comparison | Current value vs static threshold | Current vs rolling baseline ± Nσ |
| Best for | Known limits, compliance | Variable patterns, drift |
| Setup | Set a number | Tune sensitivity / window |

**Bottom line:** you do **not** need a historical window for a Metric Threshold Monitor. The historical window applies to the **Metric Anomaly Monitor** only.

Choose **Threshold** when you know the danger zone. Choose **Anomaly** when the system should learn what is normal.

---

## 4. Where detection runs: edge versus platform

“Who detects the anomaly?” depends on which stage you mean. Edge Delta uses a **two-stage** design.

### 4.1 Edge (agents): pattern detection and clustering

Pattern clustering runs **on the agents** inside your pipelines.

| Responsibility | Detail |
|----------------|--------|
| Processor | Log to Pattern Metric (or related pattern processors) |
| Algorithm | Drain — clusters logs in near real time |
| Output | Pattern metrics, emitted periodically (default often every few minutes) |
| Also produced | Pattern samples; sentiment (negative vs neutral) |

**What is sent to the platform:** pattern metrics (for example, “pattern X appeared 150 times”), samples, and sentiment — **not** every raw log (raw logs go separately only if you route them).

Architecture docs describe processing inside agents as including metric extraction, anomaly-related processing, and pattern recognition in near real time. The **monitor-driven baseline comparison** for pattern anomalies still lands on the platform (next section).

### 4.2 Platform (backend): baseline, scoring, monitors

After pattern metrics arrive:

1. Agents send pattern metrics via the **Edge Delta destination**.
2. The platform stores those metrics.
3. The platform builds baselines from lookback history.
4. The platform compares current counts to the baseline and applies sensitivity.
5. Monitors evaluate anomaly counts against your thresholds and fire alerts.

Monitors evaluate **aggregated** data in the backend across pipelines.

### 4.3 Summary: who does what

| Task | Where | Who |
|------|-------|-----|
| Log clustering (Drain) | Edge | Agent processors |
| Pattern metric generation | Edge | Agent processors |
| Sentiment classification | Edge | Agent processors (global keywords) |
| Pattern metric emission | Edge → Platform | Agents → backend |
| Baseline computation | Platform | Backend |
| Spike / anomaly scoring | Platform | Backend |
| Sensitivity filtering | Platform | Backend |
| Monitor threshold evaluation | Platform | Monitors |
| Alert triggering | Platform | Monitors |

### 4.4 Two-stage architecture

```text
Stage 1 — Edge (agents)              Stage 2 — Platform (backend)
─────────────────────────            ────────────────────────────
Lightweight, distributed             Centralized, cross-pipeline
Reduce raw log volume sharply        Build baselines from history
Create structured pattern metrics    Detect anomalies across sources
Run on nodes / gateways / cloud      Correlate; alert; AI investigate
```

**Why this split**

| At the edge | On the platform |
|-------------|-----------------|
| Cut duplicate log volume and egress | Compare behaviour across all pipelines |
| Near real-time local structure | Cross-service anomalies |
| Lower bandwidth and storage cost | Weeks of history (not short agent memory) |
| | Trigger AI teammates to investigate |

### 4.5 End-to-end example

```text
1. App emits ~10,000 similar error logs
2. Agent clusters → pattern: "Database timeout for query *"     (edge)
3. Agent emits one metric, e.g. pattern count = 10000           (edge)
4. Platform stores the time series                               (platform)
5. Platform compares: normal ≈ 50/hour, current ≈ 10,000/hour   (platform)
6. Spike detected (~200× baseline)                               (platform)
7. Monitor threshold exceeded → alert                            (platform)
8. AI teammate can receive the alert and investigate             (platform)
```

**Data reduction:** many similar logs → one pattern metric.  
**Anomaly decision:** platform, with full historical context.

---

## 5. Is there a feedback loop to agents?

A common misconception is that the platform defines patterns and baselines, then pushes them to agents so agents flag anomalies locally. **That is not how Edge Delta works for modern pattern anomaly monitoring.**

### 5.1 What does *not* happen

```text
Platform computes baselines
  → Platform sends baselines to agents
  → Agents flag anomalies locally
  → Agents send only flagged data
```

Agents do **not** receive baseline data or anomaly scores from the platform for this path. Anomaly **scoring for Pattern Anomaly Monitors is centralized**.

### 5.2 What actually happens (one-way metrics, config pull)

```text
┌─────────────────────────────────────────┐
│  EDGE (Agent)                           │
│  1. Collect raw logs                    │
│  2. Cluster into patterns (Drain)       │
│  3. Generate pattern metrics            │
│  4. Send metrics to platform            │
│     (no monitor baseline compare here)  │
└──────────────────┬──────────────────────┘
                   │ pattern metrics UP
                   ▼
┌─────────────────────────────────────────┐
│  PLATFORM (Backend)                     │
│  5. Receive metrics from all agents     │
│  6. Store time series                   │
│  7. Compute baseline (lookback)         │
│  8. Compare current vs baseline         │
│  9. Sensitivity → anomaly counts        │
│ 10. Monitors → alerts                   │
└──────────────────┬──────────────────────┘
                   │ config DOWN (pull)
                   ▼
┌─────────────────────────────────────────┐
│  Platform → Agent (configuration only)  │
│  • Pipeline YAML                        │
│  • Processor definitions                │
│  • Global sentiment keywords            │
│  • Control signals (e.g. live capture)  │
│                                         │
│  NOT sent:                              │
│  • Pattern definitions from platform    │
│  • Baseline data                        │
│  • Anomaly scores / “anomalous” flags   │
└─────────────────────────────────────────┘
```

### 5.3 Worked example: database timeout pattern

**Hours 1–168 (first week)**

**Agent**

- Sees logs such as `DB timeout for query SELECT-1234`, `… UPDATE-5678`, `… INSERT-9012`.
- Clusters to pattern: `DB timeout for query *`.
- Emits metrics (for example every few minutes): count ≈ 5/hour, sentiment negative.
- Sends metrics to the platform. The agent does **not** know whether this is “normal.”

**Platform**

- Stores hourly counts (~5, ~4, ~6, …).
- Builds baseline (for example mean ≈ 5, stddev ≈ 1).
- Baseline stays **in the platform** — not written back to the agent.

**Hour 169 (breakage)**

**Agent**

- Sees ~500 timeout logs in an hour.
- Same pattern `DB timeout for query *`, count = 500.
- Still just emits the metric — **no local anomaly flag required**.

**Platform**

- Receives count = 500 vs baseline mean ≈ 5.
- Large deviation → spike under sensitivity rules.
- Monitor threshold exceeded → alert, for example:

```text
Pattern anomaly: 'DB timeout for query *'
Current: 500/hour | Baseline: ~5/hour | Deviation: large multiple of normal
```

### 5.4 What agents pull (configuration only)

| Agents receive | Agents do not receive |
|----------------|------------------------|
| Pipeline YAML (sources, processors, destinations) | Platform-computed pattern definitions |
| Processor settings (including pattern processor options) | Baseline statistics |
| Sentiment keywords from Global Data Settings | Anomaly scores |
| Control signals (live capture, leader election, and similar) | Monitor thresholds as local compare rules |
| | “This datapoint is anomalous” flags |

Architecture docs describe agents as initiating **outbound** connections and **polling** for pipeline configuration (pull-based control plane). The backend does not push anomaly intelligence into agents for this monitor path.

### 5.5 Division of responsibility

| Agents (lightweight, distributed) | Platform (centralized) |
|-----------------------------------|-------------------------|
| Data reduction (many logs → metrics) | Global view across pipelines |
| Pattern extraction | Long historical baselines |
| Fast local processing | Cross-pipeline correlation |
| | Persistence and monitor evaluation |

### 5.6 The only common “loop”: configuration

There **is** a loop for **configuration management**, not for anomaly baselines:

```text
Human updates pipeline in UI
  → Platform stores config
  → Agent polls and pulls new YAML
  → Agent applies processors
  → Agent sends pattern metrics upward again
```

### 5.7 Legacy note: `log_to_metric` local stats

A **legacy** `log_to_metric` processor can compute **local** anomaly-style stats (for example Z-score) from a short in-memory retention window on the agent, and emit those metrics upward. That is still **not** “platform pushes baseline to agent.” Modern pattern anomaly monitoring relies on **platform-side** baselines for fleet-wide accuracy.

---

## 6. Would pushing baselines to the edge be better?

### 6.1 Clarifying the proposal

A useful refinement of the idea is:

1. Platform **computes** the baseline (as today).
2. Platform **pushes** that baseline to agents (new).
3. Agents **compare** local pattern metrics to the pushed baseline (new).
4. Agents send **alerts (or only anomalous metrics)** when breached (new).

That is **not** documented as how Edge Delta works today. Today:

```text
Agents send pattern metrics
  → Backend compares to baseline
  → Backend evaluates monitors
  → Alert fires
```

Pattern metrics continue to flow to the backend even when nothing is anomalous, which supports the Patterns UI, history, and AI queries (for example via the Edge Delta MCP connector).

### 6.2 Why baselines stay central (current design)

| Reason | Explanation |
|--------|-------------|
| Fleet-wide view | Baseline needs history across agents in a pipeline; one agent only sees local traffic |
| Consistency | Per-agent baselines would diverge; central evaluation uses one shared baseline |
| Where heavy work already is | Agents already run Drain clustering and metric emission; σ-band compare is comparatively light and benefits from long history |

### 6.3 Early detection without edge baseline compare

Early detection still works because:

1. Clustering happens near real time at the edge.
2. Pattern metrics are sent promptly.
3. Pattern Anomaly Monitors evaluate continuously.
4. Alerts fire when spike thresholds are crossed.

Added latency from centralized compare is usually small relative to time-to-action.

### 6.4 Benefits and challenges of pushing baselines

**Potential benefits of the proposed model**

- Lower egress if agents stopped sending continuous pattern metrics.
- Less backend ingest for “normal” pattern traffic.
- Comparison without a network round-trip for the σ check itself.

**Challenges relative to current architecture**

| Challenge | Why it matters |
|-----------|----------------|
| Control plane is pull-based | Agents poll for config; true baseline push would need frequent poll or a push model |
| Monitor config lives in the UI | Sensitivity, thresholds, group-by, lookback would all need to ship to agents |
| Loss of visibility | Without continuous pattern metrics, Patterns UI, history, and AI exploration of non-alerting patterns suffer |
| Multi-monitor | Several monitors can evaluate the same metrics differently; agents would need all of that logic |

The current model favours **observability completeness** (compressed pattern metrics on the backend) over **egress minimization**. Pattern payloads are already templates plus counts, not every log line.

**Bottom line:** documentation describes **central** evaluation of pattern metrics against baselines. Pushing baselines to agents for local monitor evaluation would be an architectural change, not the documented product behaviour today.

---

## References

Official Edge Delta documentation (start here for authoritative detail):

| Topic | Documentation |
|-------|----------------|
| Architecture (edge processing, control plane, destinations) | [Edge Delta Architecture](https://docs.edgedelta.com/edge-delta-architecture/) |
| Anomaly detection overview | [Anomaly Detection](https://docs.edgedelta.com/anomaly-detection/) |
| Pattern Anomaly Monitor | [Pattern Anomaly Monitor](https://docs.edgedelta.com/pattern-anomaly-monitor/) |
| Metric Anomaly Monitor | [Metric Anomaly Monitor](https://docs.edgedelta.com/metric-anomaly-monitor/) |
| Metric Threshold Monitor | [Metric Threshold Monitor](https://docs.edgedelta.com/metric-threshold-monitor/) |
| Log to Pattern Metric processor | [Log to Pattern Metric Processor](https://docs.edgedelta.com/log-to-pattern-metric/) |
| Edge Delta destination (`ed_output`) | [Edge Delta Destination](https://docs.edgedelta.com/ed-output-node/) |
| Pipeline triggers / monitors evaluating backend data | Search “Pipeline Triggers” and “Monitors” on [docs.edgedelta.com](https://docs.edgedelta.com/) |

If a linked path 404s after a docs rename, search the same title on [docs.edgedelta.com](https://docs.edgedelta.com/).

\newpage

# Part II — Edge Delta ↔ Motadata mapping

## Edge Delta concepts for Motadata / ObserveOps mapping

**What this file is:** A restructured research note that maps **Edge Delta** platform concepts to the language used in Motadata / ObserveOps (**E1–E11** stages, configuration-item thinking, RCA seed preparation). Source material was a long Q&A / chat dump; the technical content is preserved here in a readable order.

**What this file is not:** A decision to replace the Motadata build path with Edge Delta. Treat it as a **comparator map**. Canonical Motadata / Pillar B contracts stay under [`../../contracts/`](../../contracts/).

**Companion materials:**

| File | Role |
|------|------|
| [`ED to MD Mapping.md`](./ED%20to%20MD%20Mapping.md) | Earlier formatted mapping notes |
| [`../Mapping-ED-to-MD-README.md`](../../Mapping-ED-to-MD-README.md) | Index of ED→MD materials |
| [`docs/anomaly-detection.md`](../../../docs/anomaly-detection.md) | Pattern / metric anomaly deep dive |

**Editorial notes (this rewrite):**

- No substantive technical section was deleted.
- Conversational “pick a deliverable / POC checklist” menus were moved to [Appendix A](#appendix-a--research-chat-planning-menus-preserved) (not deleted).
- The identical **MCP `get_*_graph` tools** explanation appeared twice in the source; it is kept **once** in [§E5](#e5-mcp-graph-tools--time-series-charts-not-topology).

---

## Reading path

```text
Orient (Part A)
  → Multi-source SRE architecture (Part B)
  → Pipeline internals (Part C)
  → Telemetry model: events / signals / alerts (Part D)
  → Query, MCP, APIs, correlation (Part E)
  → Knowledge Graph deep dive (Part F)
  → CMDB / Motadata mapping notes (Part G)
  → Appendix A (planning menus) · Appendix B (links)
```

| Part | Question it answers |
|------|---------------------|
| [A · Orient](#part-a--orient) | What are ED’s two “graphs”? How does E1–E11 language map? |
| [B · Multi-source SRE](#part-b--multi-source-sre-architecture) | AWS + OTEL + on-prem → which pipelines? How does RCA run? |
| [C · Pipeline internals](#part-c--pipeline-internals) | Sources, processors, destinations, engine vs processors |
| [D · Telemetry model](#part-d--telemetry-data-model) | What is stored? Events vs signals vs alerts? |
| [E · Query & MCP](#part-e--query-mcp-and-apis) | CQL, MCP vs ingest, REST, correlation tags |
| [F · Knowledge Graph](#part-f--knowledge-graph-deep-dive) | Who consumes it? How does localization work? |
| [G · CMDB notes](#part-g--cmdb--motadata-mapping-notes) | No native CI binding — what are the options? |

---

## Part A — Orient

### A1. Two topology / “graph” capabilities

Edge Delta offers **two different** topology-related capabilities. Do not conflate them.


```text
[diagram]
flowchart LR
  subgraph KG["Knowledge Graph — AI Team"]
    EC[Event connectors<br/>GitHub · PagerDuty · Jira · AWS · …]
    KSM[K8s Service Map connector<br/>streaming contributor]
    EC --> KGStore[(Entity + relationship store)]
    KSM --> KGStore
    KGStore --> AI[AI teammates<br/>blast radius · ownership]
    KGStore --> UI[Topology View UI<br/>AI Team → Knowledge]
  end

  subgraph SM["Service Map — Platform"]
    eBPF[eBPF traffic capture]
    Src[k8s traffic / Service Map source]
    EDDest[Edge Delta destination]
    eBPF --> Src --> EDDest --> Plat[Platform Service Map<br/>RPM · errors · p95]
  end
```


#### A1.1 Knowledge Graph (AI Team)

Automatic environment map that **AI teammates** use during investigations.

| Need | Detail |
|------|--------|
| Requirements | **Event connectors** (non-streaming, read-only tools): GitHub, GitLab, Slack, PagerDuty, Jira, Confluence, Notion, AWS, Grafana, Argo CD, Harness, … **plus** Kubernetes Service Map connector (the **only streaming connector** that contributes to the knowledge graph) |
| How it works | **Zero configuration** discovery starts ~3 minutes after connecting; **re-reconciles every 24 hours** |
| Entity types | Services, repositories, teams, channels, incidents, documents, cloud resources, people, … |
| Teammate uses | Trace dependencies · compute blast radius · assess criticality · find relationships · search entities |
| Human UI | Topology View (AI Team → Knowledge) — 3D “city of districts” |

#### A1.2 Service Map (Platform)

Visualizes **Kubernetes service-to-service communication**.

| Need | Detail |
|------|--------|
| Requirements | Agent **≥ 1.24.0**; pipeline with **Kubernetes Service Map source** (formerly `k8s_traffic_input`) linked to **Edge Delta destination** |
| Provides | Service interconnections; RPM; errors/min; P95 latency; error-rate coloring; link thickness; links to Traces Explorer / Logs |
| Technical | **eBPF** kernel capture; **resource-intensive**; metrics such as `k8s.traffic.communication.latency.p95`, `k8s.traffic.communication.count`; disable via Helm `tracerProps.enabled=false` |

#### A1.3 Side-by-side

| Feature | Knowledge Graph | Service Map |
|---------|-----------------|-------------|
| Purpose | AI teammate context for investigations | Service communication visualization |
| Scope | Multi-system (repos, teams, incidents, cloud, K8s services) | Kubernetes services only |
| Data source | Event connectors + K8s Service Map connector | eBPF network traffic |
| Configuration | Automatic from connectors | Specific pipeline nodes |
| Access | AI Team → Knowledge | Platform → Service Map |

**Docs:** Knowledge Graph · Service Map · Kubernetes Service Map Source · Connectors Overview (see [Appendix B](#appendix-b--documentation-references)).

---

### A2. Context lock for this research

Confirmed when this note was produced:

| Item | Status |
|------|--------|
| Internal pipeline stages **E1–E11** | In scope as Motadata / ObserveOps language |
| Internal design-doc terminology | In scope |
| Goal: understand Edge Delta architecture | Yes |
| Goal: map internal pipeline → Edge Delta | Yes |
| **CMDB correlation at ingest** | **Not required** for the mapping exercise |

---

### A3. Terminology mismatch: E1–E11 vs Edge Delta

Edge Delta’s real pipeline is **Sources → Processors → Destinations**, not an “E1 Collect / TelemetryEnvelope / ci_id” ingest contract.

| Your / Motadata term | Edge Delta equivalent | Notes |
|----------------------|----------------------|-------|
| E1 Collect (P1) | **Source nodes** | Configured per pipeline, not a single “E1” component |
| TelemetryEnvelope | No equivalent | OpenTelemetry-shaped data items (logs, metrics, traces) |
| ingest.v1 JSONL | No such format | OTLP, JSON, plain text, syslog, CEF, … |
| ci_id / ci_type | **Resource attributes** | OTEL semantic conventions (`service.name`, `k8s.pod.name`, …) |
| signal_class | No equivalent | Typed as log / metric / trace / event (and related) |
| CMDB / change / ticket at ingest | Not telemetry sources | Use **Connectors** (Jira, PagerDuty, …) for events |
| schema-version reject | Parser / processor errors | Format handled in processors, not a hard ingest schema gate |
| FR-K1 / AC | No ED equivalent | Internal requirement IDs |

**What the Motadata-style description often resembles:** ServiceNow Event Management / AIOps, Splunk ITSI, or a custom ITIL-centric pipeline — **not** Edge Delta’s native model.

```text
Edge Delta actual pipeline (corrected)

Sources  →  Processors  →  Destinations
  ↓            ↓              ↓
Collect      Transform      Route to:
telemetry    enrich         • Edge Delta Platform
(logs /      mask           • Third-party tools
 metrics /   filter         • Archives
 traces)     extract        • Alerts
```

---

### A4. Corrected collection → process → route flow

#### Phase 1 — Source collection (closest to “E1 Collect”)

**Component name in Edge Delta:** source nodes (not “E1 Collect”).

| Aspect | Detail |
|--------|--------|
| Purpose | Collect logs, metrics, traces, events from infrastructure |
| Trigger | Continuous streaming (not batch “ingestion”) |
| Inputs | File logs; Kubernetes API events / pod logs; OTLP 4317 gRPC / 4318 HTTP; syslog; HTTP POST; cloud streams (Kinesis, Pub/Sub, Kafka, Event Hub); security feeds (e.g. CrowdStrike FDR) |
| Wire formats | JSON, OTLP Protobuf, plain text, CEF, LEEF, syslog RFC — **not** ingest.v1 JSONL |
| Data shapes | Logs `{timestamp, body, attributes, resource, severity}` · Metrics `{name, value, timestamp, unit, kind, attributes}` · Traces `{trace_id, span_id, parent_span_id, attributes}` · Events `{event.type, event.domain, timestamp, attributes}` |

**Edge Delta does not have at source:** TelemetryEnvelope · ci_id/ci_type · signal_class enum · change_event/cmdb_sync/ticket reserved classes · schema-version validation at ingestion.

**Example — Kubernetes logs source**

```yaml
- type: kubernetes_logs   # illustrative; exact type names follow current ED docs
  include:
    - namespace: production
  exclude:
    - pod: "*-debug-*"
```

What happens:

1. Agent reads container / node logs.
2. Parses Kubernetes metadata (pod, namespace, container).
3. Adds **resource attributes** such as `k8s.pod.name`, `k8s.namespace.name`, `service.name`.
4. Emits an OpenTelemetry-shaped log record.

Still **no** ci_id, signal_class, TelemetryEnvelope, schema gate, or CMDB lookup at this stage.

#### Phase 2 — Processing (closest to “E2” enrichment)

Typical processor chain: Parse JSON → Add Field → Mask → Filter → Extract Metric → Pattern recognition (Drain) → Route.

Still **no native CMDB binding** — Edge Delta is not a CMDB system.

#### Phase 3 — Destination routing

Outputs may include: Edge Delta Platform · Splunk / Datadog / Elastic · SIEM · S3 / GCS archives · Slack / PagerDuty alerts. Encoding is destination-specific (HEC, OTLP, JSON, …).

---

## Part B — Multi-source SRE architecture

Enterprise starting point for this note:

1. **Completely cloud telemetry (AWS)** — Cloud Pipeline (agentless)  
2. **OTEL-based implementation** — Gateway Pipeline (recommended)  
3. **On-premise workloads** — Node Pipeline (agent-based)  

**End objective:** Edge Delta as **SRE companion for RCA**.

### B1. Architecture overview

Edge Delta combines **Telemetry Pipelines** (collect / process / route) with **AI Team** (investigation / RCA). Deploy **different pipeline types per source**; AI teammates query **all** indexed data for correlation.


```text
[diagram]
flowchart TB
  AWS[S1 AWS cloud telemetry]
  OTEL[S2 OTEL apps / collectors]
  ONP[S3 On-prem workloads]

  CLOUD[P-Cloud · Cloud Pipeline]
  GW[P-GW · Gateway Pipeline]
  NODE[P-Node · Node Pipeline]
  COORD[P-Coord · Coordinator<br/>control plane]

  BACK[(Edge Delta backend<br/>logs · metrics · traces · events · patterns)]
  MCP[Edge Delta MCP Connector]
  SRE[SRE + OnCall AI]

  AWS -->|serverless / streaming| CLOUD
  AWS -.->|optional EKS aggregation| GW
  OTEL -->|OTLP 4317/4318| GW
  ONP --> NODE
  ONP -.-> COORD
  NODE -.->|optional aggregation| GW
  NODE --> BACK
  CLOUD --> BACK
  GW --> BACK
  BACK --> MCP --> SRE
```


**Legend:** solid = primary path · dashed = optional.

### B2. Component selection by data source

#### B2.1 AWS cloud telemetry

**Pipeline:** Cloud Pipeline (agentless) **or** Gateway (agent-based on EKS).

**Cloud Pipeline — serverless / streaming**

- AWS Lambda via Lambda Extension / **Lambda Forwarder**
- CloudWatch Logs via subscription filters + Forwarder
- Apply **CloudWatch Pack** / **Lambda Pack** for parsing
- HTTP/HTTPS/GRPCS endpoints; pull sources (HTTP Pull, S3, …)
- Compute units scale with traffic (~12 MB/s per unit in docs)
- Data to Edge Delta backend for AI analysis

**Gateway — agents in AWS for aggregation**

- Centralized aggregation; OTLP, application logs, cross-source correlation / dedup
- Official docs: Gateway / Coordinator are **Kubernetes** deployments; use **Node** on ECS/EC2 hosts

#### B2.2 OTEL-based implementation

**Pipeline:** **Gateway Pipeline (recommended)** — not Cloud as the primary design.

| Step | Action |
|------|--------|
| 1 | Deploy Gateway as centralized OTLP receiver |
| 2 | Configure **OTLP Connector** for AI Team streaming access |
| 3 | Add **otlp_input** — port **4317** (gRPC) or **4318** (HTTP) |
| 4 | Point OTEL Collectors / SDKs at Gateway |
| 5 | Gateway enables full-trace **tail sampling** and service-level aggregation |

**Why Gateway:** Direct Collectors → Gateway avoids unnecessary Node hops and preserves complete-trace context.

*(Docs also describe Cloud Pipeline OTLP endpoints for agentless cases; keep Gateway as the recommended enterprise path for this architecture.)*

#### B2.3 On-premise workloads

**Pipeline:** Node Pipeline per cluster / host.

| Environment | Pipelines | Collects |
|-------------|-----------|----------|
| Kubernetes | Node (DaemonSet) + **Coordinator** | Container logs, host metrics, K8s events, eBPF traces, service maps |
| Linux / VM | Linux Node agent | File logs, system metrics; direct destinations or via Gateway |

### B3. RCA and investigation layer

| Component | Role |
|-----------|------|
| **Edge Delta MCP Connector** | Required for teammates to search logs / patterns / metrics / traces / events / pipelines |
| **SRE teammate** | Autonomous investigation across sources |
| **Security Engineer** | Threat / compliance workflows |
| **Event connectors** | PagerDuty / Slack / Jira / GitHub triggers and collaboration |

**Typical RCA workflow**

1. Pipelines / monitors detect pattern anomalies or threshold breaches.  
2. SRE teammate searches logs (CQL), patterns, metrics, traces; builds a cited timeline.  
3. Humans review in channels.  
4. Actions (tickets, playbooks, pipeline changes) with **explicit approval**.

**Important:** When saying “search across three sources,” the teammate searches **three telemetry signal types** (logs, metrics, traces) that may have been ingested from AWS / OTEL / on-prem pipelines — not three isolated backends.

### B4. Coordinator vs Gateway (hierarchy)

| Pipeline | Role |
|----------|------|
| **Node** (DaemonSet) | Collect node-local data |
| **Coordinator** (same cluster/namespace) | Control plane: heartbeats, live features, leader election — **does not process telemetry** |
| **Gateway** (same or other cluster) | Aggregate / dedup / tail-sample / OTLP ingress |
| **Backend** | Index, explore, AI, monitors |

Coordinator is especially important for live capture on larger clusters (docs: required for live tail on clusters with **more than 20 nodes**).

### B5. Key architecture benefits

- Unified data plane queryable through one MCP connector  
- Edge processing reduces volume before egress  
- OTEL apps need no re-instrumentation  
- Mask / filter / sample before AI sees data  

---

## Part C — Pipeline internals

### C1. Destination types

| Type | Meaning | Examples |
|------|---------|----------|
| **Archive** | Buffered long-term storage | S3, GCS, Azure Blob; flush interval / max byte limit; gzip/zstd/snappy; JSON/Parquet |
| **Streaming** | Continuous to observability / SIEM | Elasticsearch, Splunk, Datadog, Kafka, HTTP/TCP |
| **Trigger** | Notifications when threshold nodes fire | Slack, Teams, PagerDuty, ServiceNow, webhooks — **signals**, not full log streams |

### C2. Processing engine vs processors

| Term | Analogy |
|------|---------|
| **Processing engine** | Agent runtime that executes the pipeline |
| **Processors** | Individual transforms (parse, extract metric, filter, enrich, …) |

Processors chain inside multiprocessor / sequence nodes and run in order.

### C3. Integrate Node + Coordinator + Gateway

See Edge Delta docs: *Integrate Edge Delta's Node, Coordinator, and Gateway Pipelines*. Node agents can send **directly** to the Edge Delta destination (`ed_output`) **or** via Gateway when aggregation is required. `ed_output` is a **destination node**, not a Gateway.

---

## Part D — Telemetry data model

### D1. How many telemetry types are stored?

Documentation commonly treats **five** core types collected / stored:

| Type | Notes |
|------|--------|
| **Logs** (often grouped with events in usage) | Primary search surface |
| **Metrics** | Explorers + MCP metric tools |
| **Traces** | Timeline / graphs |
| **Patterns** | Derived from logs (Drain signatures: count, proportion, sentiment, delta) |
| **Service Map** | K8s traffic topology metrics (distinct telemetry) |

Kubernetes connector materials explicitly mention collecting logs, metrics, traces, service map, and events. “Security signals” appear as enriched / analyzed metadata rather than a separate storage class in Trust Center language.

### D2. Events are not all the same

| Kind | Original or derived? | Source |
|------|----------------------|--------|
| **Kubernetes events** | Original | K8s API (`item.type=event`) |
| **Windows events** | Original | Windows Event Log API |
| **Event connector payloads** | Original external | PagerDuty, GitHub, AWS EventBridge, Slack, … |
| **Monitor events** | Derived | Platform monitors on metrics/logs |

### D3. Two separate flows: connectors vs destinations


```text
[diagram]
flowchart LR
  EXT[External systems<br/>PagerDuty · GitHub · AWS]
  ED[Edge Delta AI Team]
  PIPE[Pipelines + monitors]
  DEST[Destinations<br/>webhook · Slack · PagerDuty]

  EXT -->|Event connectors RECEIVE| ED
  PIPE -->|Destinations SEND alerts| DEST
  DEST -.->|optional loop: incident back via connector| EXT
```


| Flow | Purpose | Example |
|------|---------|---------|
| External → Edge Delta (**Event Connector**) | Trigger AI investigation of **external** events | PagerDuty incident → AI Team investigates logs/metrics |
| Edge Delta → External (**Destination**) | Alert others about **Edge Delta** findings | CPU spike / pattern anomaly → create PagerDuty incident |

You can combine them: Edge Delta alerts PagerDuty → PagerDuty connector fires → AI Team investigates.

### D4. Signals vs events vs alerts

| Term | Type | Generated by | Where |
|------|------|--------------|-------|
| **Event** | Data item | K8s / Windows / connectors / monitors | Infra + backend |
| **Signal** | Data item | **Threshold nodes** in pipelines | Edge (in pipeline) |
| **Alert** | State / concept | Monitor state (`OK` / `Warning` / `Alert` / `No Data`) or general “notification” language | Backend / human language |

Example **signal** shape:

```json
{
  "_type": "signal",
  "signal": {
    "title": "Threshold -threshold-checker triggered",
    "description": "error-logs-per-minute hit threshold",
    "signal_id": "111022",
    "name": "error-logs-per-minute",
    "value": 55,
    "threshold_condition": "value > 5"
  }
}
```

In Global Data Settings, a label **“Alerts”** may describe agent-detected threshold signals sent to the backend — the underlying data item is still a **signal**. Docs sometimes use “alert” and “signal” loosely for notifications.

### D5. Events available outside Kubernetes

| Environment | Infra events | Monitor events | Event connectors | Pipeline signals |
|-------------|--------------|----------------|------------------|------------------|
| Kubernetes | K8s events | Yes | Yes | Yes |
| Windows | Windows events | Yes | Yes | Yes |
| Linux (non-K8s) | — | Yes | Yes | Yes |
| macOS | — | Yes | Yes | Yes |

### D6. What the Edge Delta backend stores (inventory)

| Category | Contents |
|----------|----------|
| **Processed telemetry** | Logs, metrics, traces, events / security-related signals after pipeline processing |
| **Derived analytics** | Log patterns · anomalies · monitor/threshold outcomes · extracted / rolled-up stats |
| **Configuration / ops** | Pipeline configs · processor rules · control signals · heartbeats / agent health |
| **AI Team data** | Threads · findings · token / performance metrics · ratings |
| **Audit** | Config change trails · auth / access events |

**Customer control:** Mask / filter / encrypt in pipelines before egress.  
**AI training:** Trust Center language — customer telemetry is **not** used to train models; used for tenant-isolated inference / analysis.

---

## Part E — Query, MCP, and APIs

### E1. CQL = Common Query Language

**CQL** is Edge Delta’s **Common Query Language** (not “Context Query Language”). Unified search across explorers (logs, metrics, traces, K8s / monitor events, rehydrations).

```text
error
host.name:webserver AND k8s.namespace.name:production
@region:"us-west-2" AND @status_code > 399
error AND database
level:(error OR warn)
"connection failed" -timeout
statusCode:"*04"
ed.tag:"*prod*"
```

**CQL vs OTTL:** CQL is for **search in the UI / MCP**. Pipeline **filter processors** use **OTTL** (OpenTelemetry Transformation Language); convert CQL → OTTL when promoting a search into a pipeline filter.

### E2. MCP is not the telemetry ingest/output path

```text
Data plane:   Sources → Pipelines → Platform → Destinations
AI plane:     AI agents / teammates ↔ MCP Server ↔ REST API ↔ Platform data
```

| Path | Role |
|------|------|
| Sources / pipelines / destinations / ingestion HTTP | **Ingest and egress** telemetry |
| MCP (`…/mcp`) | **Query and manage** for AI clients |
| REST API (`api.edgedelta.com`) | Scripts / automation |

MCP tools such as `get_log_graph` / `get_metric_graph` are **MCP tools** that call REST under the hood — not the ingest API.

### E3. Why Edge Delta’s own AI teammates also use MCP

Intentional design:

1. **Same permission model** (Allow / Ask Permission, RBAC, audit) for internal and external agents  
2. **Separation of concerns** — AI Team orchestration is a separate plane from the telemetry backend  
3. **Protocol standardization** — same connectors (AWS, GitHub, …) for custom and built-in teammates  
4. **Security / audit** — one authenticated pathway  

From the platform’s perspective, ED teammates are **first-class MCP clients** that happen to be built by Edge Delta.

### E4. REST API categories (high level)

Examples under `https://api.edgedelta.com`:

| Area | Examples |
|------|----------|
| AI / explore | pattern stats, log search, events search, dashboards, metrics graph |
| Pipeline management | create / add_source / deploy / history |
| Access & users | RBAC, groups, invites |
| Integrations | endpoints, testing |
| Lookup tables | upload / manage |
| Rehydrations | historical replay |
| Agent configs | legacy |

**Knowledge Graph:** documentation reviewed for this note showed **no dedicated public REST endpoint** and **no MCP tool** for graph traversal. Access is **internal to AI teammates** + Topology View UI. (See Part F.)

### E5. MCP “graph” tools — time series charts, not topology

`get_log_graph`, `get_metric_graph`, `get_trace_graph`, `get_pattern_graph` mean **charts over time**, **not** the Knowledge Graph / Neo4j-style graphs.

| Tool | Returns |
|------|---------|
| `get_log_graph` | Bucketed log counts over time |
| `get_metric_graph` | Aggregated metric series (exact metric name) |
| `get_trace_graph` | Span counts or latency percentiles |
| `get_pattern_graph` | Pattern counts with volatility filters (`all` / `new` / `existing` / `gone`) |

| Tool family | Returns | Size | Use |
|-------------|---------|------|-----|
| Search (`get_log_search`, …) | Individual records | Large | Drill into evidence |
| Graph (`get_*_graph`) | Time buckets | Compact | Spot trends first |

AI agents typically **graph first**, then **search** the interesting window — keeps context windows small.

### E6. Unified backend storage — not four siloed products

Edge Delta uses a **unified backend** with **type-specific query surfaces** (Log Search, Metrics Explorer, traces, events). Infrastructure mentions include ClickHouse, S3 (compressed raw logs per org), and related cloud services. Usage pricing language often applies the same credit-per-GB idea across logs/metrics/traces.

This differs from “Elasticsearch + Prometheus + Jaeger” as three separate products you operate.

### E7. Normalization and correlation (smart tagging, not full rewrite)

**At the pipeline:** standardize toward **OpenTelemetry** (and **OCSF** for security data).

**Lightweight wrapper (not expensive full rewrite):** the **original message stays in `body`**; metadata is **added**:

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

**Automatic / enrichable correlation fields** (Datadog “tags” analogue): `host.name`, `service.name`, `ed.source.*`, Kubernetes attributes, cloud region/provider, custom fields via Add Field / OTTL, plus `trace_id` / `span_id` for logs↔traces.

**Best practices for three ingest paths**

1. Same `service.name` everywhere (AWS / OTEL / on-prem).  
2. Consistent `environment` / `region` / optional `data_source` tag.  
3. Trace context in OTEL apps.  
4. Enrich **at the edge** before storage.


```text
[diagram]
flowchart TB
  S1[AWS Cloud Pipeline] --> N[Normalization + resource attributes]
  S2[OTEL → Gateway] --> N
  S3[On-prem Node] --> N
  N --> B[(Unified backend)]
  B --> MCP[MCP + CQL]
  MCP --> AI[SRE investigation]
```


---

## Part F — Knowledge Graph deep dive

### F1. Who consumes it?

| Consumer | Access | Use |
|----------|--------|-----|
| Edge Delta AI teammates | Built-in / internal | Investigation, impact, ownership |
| Humans | Topology View (read-only) | Explore environment |
| External AI agents | **None** via MCP/REST | — |
| Public REST / MCP tools | **None** documented | — |

**Value in investigations:** entity + neighbors · dependencies · blast radius · criticality · cross-entity search · “Knowledge references” citations in threads.

### F2. Compared with Datadog / Dynatrace

| Capability | Edge Delta | Datadog | Dynatrace |
|------------|------------|---------|-----------|
| Telemetry query engine | Backend + CQL | Husky | Grail |
| AI tool access | MCP tools | MCP / API | API |
| Topology / graph | Knowledge Graph (**internal**) | Service Catalog (API) | Smartscape (API) |
| Who queries topology? | ED teammates (+ UI) | API clients | API clients |

Husky/Grail ≈ **data lake / query engines**. ED Knowledge Graph ≈ **relationship / context layer on top of** telemetry — closer to a privileged AI context system than a public graph warehouse.

### F3. How teammates use the graph for localization (seed-like reasoning)

**Documented:** teammates query the graph during investigations and cite **Knowledge references**. Capabilities listed: find entity/neighbors, trace dependencies, blast radius, criticality, search.

**Not documented:** exact wire protocol (no MCP tool, no public REST). Likely **privileged internal API** and/or undocumented MCP **resources** (ED MCP already exposes some resources such as `services://list`, `facets://…`). Treat mechanism details as **inference until Edge Delta confirms**.

Illustrative localization flow (conceptual):

```text
1. Detect via telemetry MCP tools (logs/metrics/traces)
2. Resolve entity in Knowledge Graph (internal)
3. Neighborhood + blast radius + ownership + recent change context
4. Form investigation seed: suspect service · neighborhood · time window
5. Cite Knowledge references + telemetry evidence in the thread
```

**Implication for Motadata E7–E10 thinking:** graph-assisted **localize / seed** is a **native ED teammate advantage**, not something external MCP clients can fully copy today without building their own catalog.

### F4. Knowledge Graph entry vs backend telemetry entry

| Aspect | Backend storage | Knowledge Graph |
|--------|-----------------|-----------------|
| Data | Time-series telemetry | Entities + relationships |
| Updates | Continuous stream | Reconcile ~every 24h |
| Source | Streaming pipelines / connectors | Event connectors (+ Service Map as input for K8s) |
| Query | CQL via MCP | Internal teammate + Topology UI |
| Purpose | “Show errors for payment-api” | “What depends on payment-api?” |

**Conceptual KG entry** (illustrative):

```json
{
  "nodes": [
    {"id": "service:payment-api", "type": "Service", "criticality": 0.92},
    {"id": "repo:payment-service", "type": "Repository"},
    {"id": "team:platform", "type": "Team"}
  ],
  "relationships": [
    {"from": "service:payment-api", "to": "repo:payment-service", "type": "DEPLOYED_FROM"},
    {"from": "team:platform", "to": "service:payment-api", "type": "OWNS"},
    {"from": "service:payment-api", "to": "service:order-api", "type": "DEPENDS_ON"}
  ]
}
```

### F5. Why Service Map is stored telemetry but Knowledge Graph is not

| | Service Map | Knowledge Graph |
|--|-------------|-----------------|
| Nature | Continuous eBPF traffic telemetry + metrics | Discovery metadata / topology for AI |
| Pipeline | Flows through pipelines; usage/credits | Built from connector APIs; not a telemetry stream |
| Purpose | Who talks to whom **now** | Who owns what / depends on what / blast radius |
| Storage impact | Counts like other telemetry | Small vs continuous streams |

Service Map can be an **input** into Knowledge Graph for Kubernetes environments; they remain different products.

### F6. Combined RCA picture


```text
[diagram]
flowchart TB
  P[Three pipelines → backend]
  P --> TEL[(Telemetry store<br/>CQL + MCP)]
  CONN[Event connectors] --> KG[(Knowledge Graph)]
  SM[Service Map telemetry] -.-> KG
  TEL --> SRE[SRE teammate]
  KG --> SRE
  SRE --> OUT[Thread: Knowledge references + telemetry citations]
```


---

## Part G — CMDB / Motadata mapping notes

Edge Delta **does not** natively bind telemetry to CMDB configuration items at ingest.

| Approach | What it does |
|----------|----------------|
| **Knowledge Graph** | Closest operational topology for AI — not a CMDB replacement |
| **Lookup processor** | Manually map `service.name` → `ci_id` from a lookup table |
| **External CMDB connector** | Teammate queries ServiceNow (or similar) **during analysis**, not at ingest |

Illustrative lookup (conceptual YAML):

```yaml
- type: lookup_processor
  lookup_table: cmdb_mapping
  source_field: attributes["service.name"]
  target_field: attributes["ci_id"]
  lookup_key: service_name
  lookup_value: cmdb_ci_id
```

For Motadata Pillar B, durable CI–CI topology and blast-radius **computed** edges remain a **separate** product concern from Edge Delta’s Knowledge Graph (see pillar-b `references/` Fusion / OneOps HTMLs and `contracts/`).

---

## Appendix A — Research-chat planning menus (preserved)

These were conversational “what next?” menus in the source dump. Kept for continuity; they are **not** Motadata ADRs.

### A-1. Deliverable options discussed

1. **Configuration templates** — YAML for E1→sources, E2→processors, E6→monitors, E7–E11→workflows  
2. **Gap analysis document** — stage coverage table + mitigations  
3. *(Option 3 was not present in the source dump.)*  
4. **ADR** — e.g. “Replace internal E1–E11 with Edge Delta” draft  
5. **Cost / TCO spreadsheet**  
6. **Risk register** — migration, wrong RCA, vendor outage, …

Illustrative gap sketch from the chat (directional, not a Motadata lock):

| Stage | Edge Delta | Coverage sketch | Action sketch |
|-------|------------|-----------------|---------------|
| E1 Collect | Source nodes | High | Config |
| E2 Identity | Processors | Medium–high | Lookups |
| E3 Topology | Knowledge Graph | Medium–high | Connectors / MCP |
| E4 Stores | Backend (+ archives) | High | Deploy |
| E5 Maintain | Platform | Medium | Webhooks / ops |
| E6 Detect | Monitors | High | Migrate rules |
| E7 Curate | AI teammates | Different model | Rethink vs native AI |
| E8–E11 | AI teammates | High if trusting AI Team | Channels / approvals |

### A-2. Follow-on “next step” menu

A. Ready-to-deploy configs · B. Day-1 POC commands · C. E7 approach (Composite Monitors vs custom service) · D. Replay past incidents · E. Stakeholder presentation  

### A-3. POC environment checklist (fields to fill)

- Kubernetes distro / version / size / namespaces  
- Telemetry volume (logs / metrics / traces)  
- Data sources checklist (pod logs, events, OTLP, files, syslog, streams, …)  
- Top E6 detection rules  
- One real E7 correlation scenario (signals, merge logic, case_seed fields)  
- Integrations (GitHub, Slack, PagerDuty, Jira, AWS, …)

---

## Appendix B — Documentation references

Search these titles on [docs.edgedelta.com](https://docs.edgedelta.com/) if a path renames:

| Topic |
|-------|
| Edge Delta Architecture |
| Knowledge Graph |
| Service Map / Kubernetes Service Map Source |
| Connectors Overview / Event Connectors / OTLP Connector |
| Cloud Pipelines / Installation Overview / Ingestion Pipelines |
| Integrate Node, Coordinator, and Gateway Pipelines |
| Edge Delta Destination / Processors Overview / Pipeline Triggers / Threshold Node |
| Common Query Language (CQL) / Logs Explorer |
| Edge Delta MCP Connector / MCP Server Tools |
| Data Locality for AI-Driven Investigations |
| Specialized Teammates / AI Team Overview / Getting Started with AI Team |
| Anomaly Detection / Pattern Anomaly Monitor / Metric monitors |
| Pipeline Settings / Usage Report / Trust Center / API Reference |
| Add Field Processor / Strengthening Security and Compliance |
| Federation with Gateway Pipelines / AI Team Use Cases |

---

*End of restructured note. Source: research chat consolidated into Parts A–G + appendices.*
