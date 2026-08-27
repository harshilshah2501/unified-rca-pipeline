# Edge Delta — supported scenarios (what they actually publish)

**Hub:** [`ed-ai-team-hub.html`](./ed-ai-team-hub.html) · **HTML:** [`ed-supported-scenarios.html`](./ed-supported-scenarios.html) · **Lab:** [`ed-lab-setup.html`](./ed-lab-setup.html)  
**Date:** 2026-08-14  
**Honesty:** Public framing (vendor docs) + Observed (UI) tenant + Observed (MCP) this session.

## Headline

Edge Delta does **not** publish a Davis-style Detect-class list (ERROR · SLOWDOWN · AVAILABILITY · …). There is no integer “N RCA scenarios.”

They publish **three catalogs that stack as jobs**. Do not add 43+8+10. Do **not** map them onto Node / Gateway / AI Team:

```text
  43 Packs shape the stream  →  8 monitor types notice  →  10 use cases investigate
  (hygiene in a pipeline)       (how an alert fires)         (who looks — this one IS the Team)
```

| | **43 Packs** | **8 monitor types** | **10 AI Team use cases** |
|--|--------------|---------------------|--------------------------|
| **Job** | How to parse / mask / route *this source* | *How* we decide something looks wrong | *Who* looks, with which connectors |
| **Lives** | Inside a pipeline — Node **or** Gateway | Pipeline Triggers (edge) **or** org Monitors (platform) | AI Team |
| **Alert?** | No | Yes, when configured | Uses alerts / webhooks as *input* |
| **Not** | The Node SKU | The Gateway SKU | Extra monitor types |

Hub one-story (catalogs → deploy → stages): [`ed-ai-team-hub.html`](./ed-ai-team-hub.html)#one-story. Stage table: §6 below.

---

## 1. Ten AI Team investigation scenarios (Public framing)

Each use case is an Input → Process → Output recipe: webhooks / user requests / monitor alerts in; pipelines + monitors + teammates + human approval in the middle; connector actions / recommendations / comms out.

| # | Use case | What it is for | Typical connectors |
|---|----------|----------------|--------------------|
| 1 | **Anomaly-triggered investigation** | Pattern-anomaly spike → OnCall delegates to SRE + Code Analyzer | Edge Delta MCP, GitHub, Pattern Anomaly Monitor |
| 2 | **Security-related degradation** | Perf/infra change that might be compromise — Security Engineer joins SRE | Edge Delta MCP, AWS, GitHub |
| 3 | **Cross-platform telemetry investigation** | Correlate Edge Delta with another lake (e.g. Elasticsearch MCP) | Edge Delta MCP, Elastic MCP |
| 4 | **Database performance investigation** | Frontend → backend → Postgres cascade (slow queries / pool) | Edge Delta MCP, GitHub, streaming sources |
| 5 | **CI/CD pipeline failure** | Code change vs flake vs environment | CircleCI, GitHub, Edge Delta MCP |
| 6 | **Ingest failure investigation** | Kafka / ingest API / storage cascade | Edge Delta MCP, GitHub, Pattern Anomaly Monitor |
| 7 | **PagerDuty incident response automation** | Webhook in; confidence-gated actions; human approval | PagerDuty, Edge Delta MCP, GitHub |
| 8 | **Kubernetes troubleshooting** | Pod logs, cluster events, HPA / scheduling | Edge Delta MCP, GitHub, Kubernetes source |
| 9 | **GitHub development workflow automation** | PR review, release readiness, Actions failures (`@edge-delta`) | GitHub, Edge Delta MCP |
| 10 | **Data locality for AI-driven investigations** | Why to route telemetry *through* Edge Delta so MCP is native | Edge Delta MCP, streaming, PagerDuty optional |

**This tenant (Observed UI + MCP):** GitHub + Edge Delta MCP + Edge Delta Documentation. **UC9** fully done (daily GitHub risk report). **UC8** completed — team recipe, no Issue card (OnCall thread; kubectl leaf). **UC4** partial (eBPF traces, no DB OnCall). **UC1 parked** (patterns; live Pattern Anomaly No Data; 18 Aug ingest 402; firehose scaled 0). **UC6** lite patterns (scaled 0). **UC10** MCP demo. **UC2/3/5/7** blocked on connectors. Issues **0**. Thread ≠ Issue. Hub: [`ed-ai-team-hub.html`](./ed-ai-team-hub.html) · Breakdown: [`edgedelta-subsystem-mechanisms.html`](./edgedelta-subsystem-mechanisms.html).

---

## 2. Eight monitor types (Detect mechanisms — not fault classes)

[Getting Started](https://docs.edgedelta.com/getting-started-ai-team/) says you can create **seven** types: Metric Threshold · Metric Change · Log Threshold · Pattern Anomaly · Composite · Synthetic · Event.

The [Monitors](https://docs.edgedelta.com/monitors/) section also documents **Metric Anomaly** (rolling baseline / σ band) as its own type, and that index omits Event.

**Union = 8 types.** Do not treat “seven” as a closed enum.

| Type | Job | Opens a Davis-like category? |
|------|-----|------------------------------|
| **Metric Threshold** | Fixed numeric threshold on a metric | No |
| **Metric Change** | Rate-of-change vs history | No |
| **Metric Anomaly** | Rolling mean ± Nσ | No |
| **Log Threshold** | Log volume / severity counts | No |
| **Pattern Anomaly** | Unusual log-pattern spike | No — not Watchdog, not Davis Event |
| **Event** (Observed UI: Event Threshold) | Event-source thresholds (e.g. GitHub) | No |
| **Composite** | Combine other monitor conditions | No |
| **Synthetic** | Periodic HTTP health check | No |

Two complementary Detect *locations* (not extra types): **Pipeline Triggers** (edge, one pipeline) ∥ **Monitors** (backend, cross-pipeline). [Pipeline Triggers](https://docs.edgedelta.com/pipeline-triggers/).

**Default monitors on a new org (Public framing):**

| Monitor | Type | Job |
|---------|------|-----|
| Default Service Anomaly | Pattern Anomaly | Pattern spike grouped by service |
| Default Pipeline Liveness | Metric Threshold | Agent heartbeat gone |

**This tenant Observed (UI):** 5 monitors — Event Threshold **3** (No Data) · Pattern Anomaly **1** (No Data) · Metric Threshold **1** (Pipeline Liveness **OK**). Alert **0**.

---

## 3. Forty-three Packs Library recipes (hygiene, not Detect)

[Packs overview](https://docs.edgedelta.com/packs/): “Showing **43** available packs.” A pack is a reusable pipeline segment. Two kinds: org-authored vs Edge Delta library (Knowledge tab).

| Kind | Count | Examples |
|------|------:|----------|
| **Source** | **36** | Nginx, Istio, AWS CloudTrail / VPC / Lambda / CloudWatch, Okta, Palo Alto, Windows Event, Syslog, MySQL Error / Slow Query, … |
| **Processing** | **3** | Dynamic Flow Control, Dynamic Sample Control, Large Message |
| **Destination** | **3** | Datadog K8s, New Relic Entities, Splunk Rosetta Stone |
| **Example** | **1** | Lookup Examples |
| **Total** | **43** | |

These are **shift-left** recipes (parse / mask / route for a source or dest). They are not ERROR/SLOWDOWN tabs.

**This tenant:** no Packs Observed in the UI. MCP listed one pipeline (below) with GitHub connector filters, not a library pack.

---

## 4. Five teammates (not scenarios)

Public framing + Observed UI cards: **OnCall AI** (orchestrator) · **SRE** · **Code Analyzer / Software Engineer** · **Security Engineer** · **Work Tracker**.

OnCall was not a card on this tenant; docs still name it as the router.

---

## 5. MCP this session (Observed)

Org `6da947fe-77af-421e-8a9c-dda8ead0b393`.

| Object | Result |
|--------|--------|
| Pipelines | **1:** `AI-Connector-Telemetry-Pipeline` (`dc098347-…`) · `fleet_type=IngestionPipeline` · `purpose=edgedelta-ai` · GitHub HTTP ingestion → `ed_ai_event_output` + Edge Delta dest |
| `event.type` facet | **0** values (empty event store) |
| Logs / traces / metrics explorers | Empty (UI snapshot) |

That hidden ingestion pipeline explains Pipeline Liveness **OK** without a Pipelines nav item: control-plane / AI-connector fleet, not application MELT.

---

## 6. E1–E11 on what you deploy (teaching map — Observed 17–18 Aug + Public framing)

You install **Node** (and optionally **Gateway**) in the cluster. After egress sits the **platform** (index + org monitors). The **AI Team sits on that platform**. Extra: **Coordinator** (mostly E5).

**Honesty:** this tenant ran **Node-only** on RTX `pro6000-server` plus Cloud ingest for UC9. No Gateway pipeline ID. IPO + UC matrix: [`edgedelta-subsystem-mechanisms.html`](./edgedelta-subsystem-mechanisms.html).

Legend: **P** primary · **A** assist · **R** read · **—** not this layer.

### Phase rollup

| Phase | Who owns the work | This tenant |
|-------|-------------------|-------------|
| **P1 Fabric (E1–E5)** | **Node ∥ Gateway**. Platform persists (E4). Team reads. | Node wrote patterns, BackOff events, eBPF traces. 402 can still stop E4 after local process. |
| **P2 Triage (E6–E8)** | **E6 three doors**; **E7–E8 Team** | Org Monitors only. UC8 ALERT. UC1 No Data. Issues 0 (E7 skipped). |
| **P3 Diagnose (E9–E11)** | **Standing AI Team**. Pipelines stay the evidence factory. | UC8 kubectl leaf. UC9 GitHub report. Threads yes, Issue cards no. |

```text
  Node (DaemonSet)  →  Gateway (Deployment)  →  Platform index + org Monitors  →  AI Team
       shape                  aggregate              store + notice                 investigate
```

### Stage distribution

| Stage | Node | Gateway | Platform (index / org monitors) | AI Team |
|-------|------|---------|---------------------------------|---------|
| **E1 Collect** | **P** node-local logs / metrics / events / eBPF | **P** OTLP / aggregation | **—** | **—** (GitHub cloud ingest is an exception) |
| **E2 Identity** | **P** OTel / OCSF + tags | **A** cluster enrich | **—** | **—** |
| **E3 Topology** | **P** eBPF service map | **A** service-level metrics, tail sampling | **—** | **R** |
| **E4 Stores** | **A** route out | **A** route out | **P** persist | **R** MCP |
| **E5 Maintain** | **A** heartbeat, Packs | **A** fleet health | Watch liveness | **R**. **Coordinator** owns control plane |
| **E6 Detect** | **P** edge door (Pipeline Triggers) | **P** cluster door | **P** org door (Monitors) | Consumes the alert; does **not** compute the threshold |
| **E7 Curate** | **—** | **—** | **—** | **P** Issue match |
| **E8 Scope** | **R** | **R** wider cluster | **—** | **P** working set |
| **E9 Localize** | **R** | **R** | **—** | **P** name the leaf |
| **E10 Identify** | **R** | **R** | **—** | **P** MCP corroboration |
| **E11 Package** | **—** | **—** | **—** | **P** Issue / Overview / approval |

**E6 is the only stage with three real doors.** That is why the 8 monitor types are not the Gateway catalog.

**P3 does not idle the pipelines.** Diagnose **reads** the estate Node/Gateway keep writing.

### Implication for use case 1 (anomaly-triggered investigation)

Need, in order: **Node** emitting the **same** negative templates into a lookback → **Pattern Anomaly** org monitor (E6) → **OnCall → SRE**. Packs optional. This tenant: patterns indexed (E4), live monitor **No Data**, then ingest **402** on 18 Aug. Firehose scaled to 0. Issues **0**.

---

## Do not equate

- 10 use cases ≠ 6 Davis categories ≠ 11 Datadog Host+APM pack templates
- 8 monitor types ≠ `event.category` ≠ the Gateway pipeline
- 43 packs ≠ Detect classes ≠ the Node pipeline
- Pattern Anomaly ≠ Watchdog story ≠ Davis Event
- Issue ≠ Problem ≠ Bits ≠ Incident
