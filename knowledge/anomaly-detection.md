# Edge Delta anomaly detection

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
