# Simplified gist — Edge Delta on our 3-phase / 11-stage clock

**Purpose:** Read Edge Delta through **our** ObserveOps pipeline (P1 Fabric E1–E5 · P2 Triage E6–E8 · P3 Diagnose E9–E11). Not a second numbering system. Product names (Collect / Detect / Package) are **aliases** of these blocks.

**Honesty:** **Public framing** = vendor docs. **Observed** = this tenant (`gmailcom_d4486595`, RTX Node + UC9 Cloud ingest, 17–18 Aug 2026). D5 stays Review.

Hub IPO + reach matrix: [`edgedelta-subsystem-mechanisms.html`](./edgedelta-subsystem-mechanisms.html) · HLD: [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) · DT vs DD philosophy: [`DT_DD_COMPARATIVE_STUDY.md`](./DT_DD_COMPARATIVE_STUDY.md).

---

## Locus (the philosophy that stays)

Same destination: *what broke, where, with evidence.* Disagreement is **where the thinking happens**.

> **Centralize-then-analyze (Dynatrace / Datadog):** Collect at the edge (OneAgent / Agent + `ddtrace`) → ship the stream to HQ → bind, index, Detect, and Package **on the platform**. Dual-track vs three-rail is a later split *inside* this camp — they are not twins.
>
> **Shift processing left (Edge Delta):** Parse, enrich, mask, reduce, and Drain-cluster **at Node / Gateway before egress** → ship a smaller, already-shaped stream → persist on the Platform → run a **standing AI Team** that *consumes* a Detect door. “Left” does not mean “no platform.”

Dual-layer (Pipelines ∥ AI Team) ≠ Dual-track (Smartscape ∥ Grail) ≠ Three-rail (Metrics ∥ APM ∥ Logs).

Catalogs are **jobs**, not SKUs: **43 Packs** shape → **8 monitor types** notice → **10 use cases** investigate. Packs are not the Node. Monitor types are not the Gateway. The 10 use cases *are* the Team playbooks.

---

## P1 · Fabric (E1–E5)

Always-on write. Pipelines shape; Platform persists; Team only reads. Filling P1 is not finishing a use case.

### E1 Collect

Admit bytes. No RCA yet.

- **Dynatrace:** OneAgent / OTLP (auto-inject).
- **Datadog:** Agent + `ddtrace` + DogStatsD.
- **Edge Delta:** Node DaemonSet tails / eBPF, optional Gateway (OTLP / aggregate), or **Cloud ingest** (GitHub HTTP). Coordinator is control plane, not this path.
- **Observed:** RTX pipeline tag `kubernetes`. UC9 = hidden `AI-Connector-Telemetry-Pipeline`. noisy-logger / fake-ingest scaled to 0 on 18 Aug after **402**.

### E2 Identity (Normalize)

Stamp join keys. Not E10 Identify.

- **Dynatrace:** `entityId` on a Smartscape node.
- **Datadog:** Unified Service Tags (`service` / `env` / `version`).
- **Edge Delta:** OTel / OCSF + `k8s.*` / `service.name` / `ed.tag` / `ed.conf.id` at the agent. Not `entityId`, not Unified Service Tags.
- **Observed:** ed-lab payloads carried pod, namespace, `service.name` (`crash-loop`, `checkout-api-db`, `checkout-api`).

**Where “shift left” lives:** parse / enrich / mask / **Drain Log-to-Pattern** / optional log-to-metric run here (E1–E2), before TLS. Volume-reduction percentages are Public framing, not a number we measured on this tenant.

### E3 Topology

Make the call path walkable. Assist, not the localizer.

- **Dynatrace:** Smartscape — first-class typed graph.
- **Datadog:** Service Map — derived from APM after the fact.
- **Edge Delta:** eBPF Service Map at Node; Gateway assists OTLP. Not a Smartscape twin.
- **Observed:** `checkout-api-db` CLIENT → `checkout-db` (`edgedelta-eBPF`). No Gateway. No `rootCauseEntity` walk.

### E4 Stores

Persist durable evidence **after** egress. Local process ≠ index.

- **Dynatrace:** Grail (one multimodal lake + DQL).
- **Datadog:** Metrics timeseries ∥ Husky (traces + logs). Product rails stay separate. Husky ≠ Grail.
- **Edge Delta:** Platform index of *already-processed* rows. MCP exposes **five scopes**: `log` · `metric` · `trace` · `pattern` · `event`. Optional fan-out to 3rd-party dest (Public framing; not Observed here). Internal DB name unknown — do not call it Grail or Husky.
- **Observed:** Patterns loud (`New`, `past_count: 0`, cluster `anomaly: 0`). K8s `BackOff` events yes. `event.type:pattern_anomaly` = **0**. `get_log_search` 500. **402** on Free (17 Aug) and again on Pro (18 Aug).

**Do not collapse:** a Drain **pattern cluster** is not an anomaly **signal**. Anomaly signals are Events written when a Pattern Anomaly monitor’s spike-count vs lookback crosses threshold.

### E5 Maintain

Keep the fabric Detect-ready.

- **Dynatrace:** Grail lifecycle + Smartscape freshness (named readiness).
- **Datadog:** No single named Maintain across rails — retention per product.
- **Edge Delta:** Coordinator + optional Packs + **Default Pipeline Liveness** (Metric Threshold). Packs are hygiene snippets, not alerts.
- **Observed:** Coordinator Running. Liveness **OK**. No Packs applied. OK liveness is not an app fault class.

---

## P2 · Triage (E6–E8)

Notice, then lock a case. The Team **consumes** a door; it does **not** compute the threshold.

### E6 Detect

Emit fault signals.

- **Dynatrace:** Detectors → Event (`event.category`: ERROR / SLOWDOWN / …).
- **Datadog:** Door A Monitors ∥ Door B Watchdog (independent rails; no Davis taxonomy).
- **Edge Delta:** **Three doors** (where): Node Pipeline Trigger · Gateway Pipeline Trigger · org Monitor. **Eight types** (how): Metric Threshold / Change / Anomaly, Log Threshold, Pattern Anomaly, Event, Composite, Synthetic. Not ERROR/SLOWDOWN twins. Test Notification ≠ skyline ALERT.
- **Observed:** Org Monitors only (no Pipeline Triggers). **UC8** Pod Crash Event Threshold **ALERT**. **UC1** Default Service Anomaly **No Data** (empty lookback, then 402). Pipeline Liveness OK. Do not Test UC1/UC8 again.

### E7 Curate

Collapse to one seed / match an Issue. A channel **thread is a different object**.

- **Dynatrace:** Davis auto-merges nearby Events toward one Problem seed.
- **Datadog:** Thin auto-seed; operator or Bits often starts by hand.
- **Edge Delta:** Issue match (Public framing, black box). OnCall / workflow opens a **thread** first.
- **Observed:** Issues **0** on every run. UC8 `#alerts` and UC9 `#code-issues` were threads, not Issue cards.

### E8 Scope

Lock space ∩ time (working set).

- **Dynatrace:** Smartscape neighborhood + Grail time cut.
- **Datadog:** Operator / Bits scopes `env` / `service` / window.
- **Edge Delta:** Time window + tags **already on the alert** (`k8s.pod.name`, namespace, container, `service.name`). Not a graph neighborhood.
- **Observed:** UC8 payload already named `crash-loop` / `boom` / `ed-lab`. UC9 workflow scoped the GitHub repo, last 24h.

---

## P3 · Diagnose (E9–E11)

Name the leaf, corroborate, hand off. P3 only runs if something routed.

### E9 Localize

Name the leaf.

- **Dynatrace:** Smartscape walk → `rootCauseEntity` (may be null).
- **Datadog:** Flamegraph leaf, read by operator or Bits.
- **Edge Delta:** SRE (and specialists per recipe) query tagged evidence. Seed-at-the-leaf Detect (pod crash) does **not** need a topology walk. Not Davis, not Bits.
- **Observed:** UC8 kubectl: `inventory-api` refusing to start, missing `INVENTORY_DSN`. UC9 Software Engineer: zero PRs / CI risk, no action required.

### E10 Identify

Corroborate the leaf (Verify lives here through E11 — there is no E-Verify).

- **Dynatrace:** `rootCauseRelevant` ranking on Grail + Events.
- **Datadog:** Tag join across rails; Bits Hypothesis Tree optional.
- **Edge Delta:** **Edge Delta MCP** (and explorers) on the same five scopes. kubectl counts when SaaS log search 500s. **UC10 is this stage as the product** (locality), not a Detect door.
- **Observed:** MCP saw events, patterns, traces. Log search 500 — kubectl still counted. Empty index = empty MCP. AWS / Elastic / CircleCI / PagerDuty connectors absent (UC2/3/5/7 blocked).

### E11 Package

Operator verdict card.

- **Dynatrace:** **Problem** — default, always emitted.
- **Datadog:** **Bits** optional / **Incident** — often 0 on a real fault.
- **Edge Delta:** **Issue** + Overview health (open Issues: crit −25 / high −10 / med −4). Actions need human approval. Workflows may post to Slack without creating an Issue.
- **Observed:** Issues **0**. Health **100%**. UC8/UC9 Resolved threads. Thread ≠ Issue ≠ Problem ≠ Bits ≠ Incident.

---

## Comparison (locus only — not twins)

| Dimension | DT / DD (centralize-then-analyze) | Edge Delta (shift left, then a Team) |
| --- | --- | --- |
| **Where hygiene runs** | After ingest, on the platform | Node / Gateway **before egress**; Platform still indexes |
| **What ships** | Full (or lightly tagged) stream | Already-shaped stream + pattern metrics; raw fan-out optional (Public) |
| **Topology** | DT: Smartscape write. DD: APM-derived map | eBPF map at Node (Observed one edge). Assist, not `rootCauseEntity` |
| **Detect** | DT: `event.category`. DD: Monitors ∥ Watchdog | Eight types × three doors. This lab: org Monitors. Team does not score |
| **AI** | DT: Davis folded in (default Problem). DD: Watchdog + optional Bits | Standing **AI Team**. Starts when routed. Actions need approval |
| **Package** | DT: Problem. DD: Incident often 0 | Issue card. This tenant: Issues 0, threads yes |
| **Store** | Grail vs Metrics∥Husky — not twins | Five MCP scopes of processed telemetry. Not Grail, not Husky |

---

## Do not equate

- Issue ≠ Problem ≠ Bits investigation ≠ Incident
- Pattern cluster ≠ Pattern Anomaly event ≠ Watchdog story ≠ Davis Event
- Thread ≠ Issue · Test Notification ≠ skyline ALERT
- Dual-layer ≠ Dual-track ≠ Three-rail
- 43 Packs ≠ Node SKU · 8 monitor types ≠ Gateway · 10 use cases = Team jobs
- Drain at the agent ≠ Detect
- Pipeline Liveness OK ≠ application health
- MCP ≠ E11 (MCP is E10 / UC10)

**This tenant, one line:** P1 wrote (patterns, BackOff, eBPF traces). P2 fired once (UC8 completed — team recipe, no Issue card). P3 produced threads, not Issues. UC1 stopped at E6 No Data, then E4 402.
