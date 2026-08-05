# Multi-Telemetry RCA — Functional & Acceptance Criteria (Motadata ObserveOps)

|            |                                                                                                                             |
| ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| Product    | Motadata ObserveOps (unified observability / AIOps)                                                                         |
| Capability | Root-Cause Analysis correlating **metrics, logs, flows, SNMP traps, traces, and events** into one root cause + blast-radius |
| Module(s)  | Alert Policy & Event Correlation · AIOps · Discovery/Topology (CMDB) · Collectors · (feeds ServiceOps incident)             |
| Date       | 2026-07-31 · **Status:** Draft functional spec                                                                              |

> Extends the topology-based RCA design in `../rca-poc-observeops/`. There the signals were infra KPIs; here RCA ingests **every telemetry class** and produces one root cause with cross-telemetry evidence.

---

## 1. Scope

**Telemetry classes in scope (signals):** 

metric (KPI threshold/anomaly), 

log (pattern/error/spike), 

flow (NetFlow/sFlow/IPFIX traffic anomaly + flow-security detection), 

trap (SNMP trap/inform), 

trace (APM span error/latency), 

event (generic/synthetic/RUM error). "etc." = the model is signal-type-extensible.

**Core idea:** every telemetry type is reduced to a **normalized Signal** bound to a **CI** on a shared **topology** and a common **timeline**. 

RCA then correlates signals across type + time + topology to name **one root-cause CI + root-cause signal(s)**, with **evidence drawn from multiple telemetry types**, and computes **blast radius**. It suppresses symptom signals so the operator sees one incident, not fifty alarms across five tools.

**In scope:** ingestion/normalization, entity resolution, multi-signal correlation, root-cause determination, blast-radius, evidence, incident synthesis, noise reduction, tuning, non-functional (scale/latency/accuracy).
**Out of scope (this doc):** remediation execution, per-telemetry collection mechanics (assumed existing), UI pixel design.

---

## 2. Key concepts

- **Signal** — a normalized observation from any telemetry class: `{signal_id, type, ci_ref, start_ts, end_ts, severity, state, attributes{}, source}`.
- **Entity resolution** — mapping a raw telemetry record to exactly one CI.
- **Correlation window** — the time window within which related signals are grouped.
- **Root-cause CI / root-cause signal** — the CI (and its originating signal) determined to be the cause.
- **Evidence** — the set of contributing signals (across telemetry types) supporting the root cause.
- **Blast radius** — downstream CIs/services impacted, with the signals evidencing impact.
- **Incident** — the single correlated output: root cause + evidence + blast radius + timeline.

---

## 3. Unified Signal model (normalization target)

All collectors emit into one schema so RCA is telemetry-agnostic:

| Field               | Meaning                    | Example per type                                                            |
| ------------------- | -------------------------- | --------------------------------------------------------------------------- |
| `type`              | telemetry class            | metric / log / flow / trap / trace / event                                  |
| `ci_ref`            | resolved CI                | device, interface, host, service, app, container                            |
| `start_ts`/`end_ts` | signal time span           | anomaly window / trap time / span time                                      |
| `severity`          | normalized severity        | Info/Warning/Critical                                                       |
| `state`             | active/cleared             | for de-dup and recovery                                                     |
| `signature`         | normalized signal identity | metric+condition / log pattern id / trap OID / span error / flow anomaly id |
| `attributes`        | type-specific payload      | value+threshold / log msg / 5-tuple / varbinds / trace_id+span / etc.       |

---

## 4. Functional requirements & acceptance criteria

### FR-A — Multi-telemetry signal ingestion & normalization

- **FR-A1** Ingest signals from all in-scope telemetry classes (metric, log, flow, trap, trace, event) into the unified Signal model.
  *AC:* A representative signal of each of the 6 types is ingested and observable as a normalized Signal with `type`, `ci_ref`, timestamps, severity, and signature populated, within one processing interval of arrival.
- **FR-A2** Normalize severity and state consistently across telemetry types (active vs cleared/recovery).
  *AC:* A metric breach and its later clear, a trap and its clearing trap, and a log error burst that stops all produce a Signal that transitions active→cleared; RCA treats all three consistently.
- **FR-A3** Preserve native correlation keys per type (trace_id/span_id, flow 5-tuple, trap OID+varbinds, log fields, metric+instance) in `attributes`.
  *AC:* For each type, the native keys are retrievable from the stored Signal and usable in correlation (verified per type).

### FR-B — Entity resolution (bind every signal to a CI)

- **FR-B1** Resolve each signal to exactly one CI using type-appropriate keys: metric→monitored CI; log→host/service/app; flow→endpoint IPs→device/interface/service; trap→source device/interface (ifIndex); trace→service/instance CI; event→referenced CI.
  *AC:* Given signals whose source maps to a known CI, ≥95% resolve to the correct CI on a labeled test set; unresolved signals land in an "unattributed" queue, never silently dropped.
- **FR-B2** Resolve flow endpoints and trace services to the same CIs used by metrics/traps (shared identity), so a device seen via SNMP and via flow is one CI.
  *AC:* A flow to/from a device IP and an SNMP trap from that device resolve to the **same** CI id (verified).
- **FR-B3** Handle interface/instance-level attribution (an interface, a disk, a container, a service instance), not just device-level.
  *AC:* An `ifIndex`-specific trap and an interface-specific flow anomaly both resolve to the same interface CI, distinct from the parent device CI.

### FR-C — Common topology & time alignment

- **FR-C1** All signals bind to the shared Discovery/CMDB topology graph used by RCA.
  *AC:* Every resolved signal's CI exists in the topology and its upstream/downstream relationships are queryable during correlation.
- **FR-C2** Align timestamps across sources to a common timeline; tolerate source clock skew within a configurable bound.
  *AC:* Signals from sources with ≤ configured skew still fall in the same correlation window; a skew report is available; NTP-unsynced sources are flagged.

### FR-D — Multi-signal correlation engine

- **FR-D1 Temporal correlation** — group signals occurring within the correlation window.
  *AC:* Signals on related CIs within window W are grouped into one incident candidate; signals outside W are not.
- **FR-D2 Topological correlation** — group signals on topologically related CIs (upstream/downstream/peer) even across telemetry types.
  *AC:* A trap on a switch, a metric anomaly on a host behind it, and a trace error on an app on that host are grouped into one candidate because the CIs are on one dependency path.
- **FR-D3 Cross-telemetry correlation** — signals of *different* types on the same/related CIs correlate into one incident (not separate per-tool incidents).
  *AC:* A metric + a log + a flow + a trap + a trace signal describing one underlying fault produce **one** incident, not five.
- **FR-D4 De-duplication & symptom suppression** — repeated/equivalent signals dedupe; downstream symptom signals are marked effects and suppressed under the root cause.
  *AC:* In a fault affecting N CIs, the operator sees 1 incident; the suppressed symptom count is reported and the raw signals remain inspectable.
- **FR-D5 Configurable correlation policy** — window size, topology depth, and per-type weights are configurable.
  *AC:* Changing window/topology-depth/weights changes grouping on a fixed replay in the documented direction.

### FR-E — Root-cause determination

- **FR-E1** Determine a single **root-cause CI** (and its originating signal) by combining topology (deepest common upstream cause), signal severity, and signature rules across telemetry.
  *AC:* For each seeded fault in the test suite, the top-ranked root-cause CI equals the injected fault CI in ≥ target% of cases.
- **FR-E2** Produce a **confidence score** and a ranked list of probable causes when ambiguous.
  *AC:* Every incident carries a confidence value; when two causes are plausible, both are listed ranked, with the reason each is/ isn't preferred.
- **FR-E3** Correctly localize when the cause is genuinely single-telemetry (e.g., an app-only fault with healthy infra) — do **not** false-blame another layer/telemetry.
  *AC:* A fault with a real cause visible only in traces, and healthy metric/flow/trap/log upstream, is attributed to the app CI; infra is not named as root cause.
- **FR-E4** Cross-telemetry causal reasoning — a lower-layer signal (trap/metric/flow) is preferred as cause over a higher-layer symptom (trace/log) when topology supports it.
  *AC:* Given an uplink `linkDown` trap + flow drop + app trace errors, the root cause is the link/interface CI, and the trace errors are evidence/blast-radius, not the cause.

### FR-F — Evidence chain (multi-telemetry)

- **FR-F1** Each incident includes an evidence set citing the contributing signals **grouped by telemetry type**, with the causal chain.
  *AC:* Opening an incident shows the root-cause signal plus supporting signals labeled by type (metric/log/flow/trap/trace), and a human can reconstruct "what happened" without opening five tools.
- **FR-F2** Evidence shows the ordered timeline of signals across types.
  *AC:* The incident timeline renders signals from all contributing types in time order with their CIs.

### FR-G — Blast radius / impact

- **FR-G1** Compute downstream impacted CIs/services and cite which telemetry evidences each impact.
  *AC:* For a link/host failure, the impacted CIs list matches the actually-affected set (≥90% on the test suite), and each impacted CI references the signal(s) evidencing its impact.
- **FR-G2** Map impact to business/application services.
  *AC:* An incident lists the affected business services derived from the CI→service topology.

### FR-H — Anomaly/pattern detection feeding RCA (AIOps)

- **FR-H1** Consume anomaly/pattern signals per telemetry type: metric baselines, log pattern/spike detection, flow traffic anomaly, trace latency/error-rate anomaly, trap storms.
  *AC:* An anomaly of each supported type (not just static thresholds) can seed/contribute to an incident and appears as a Signal.
- **FR-H2** Trap/alert storm detection — collapse a flood of like signals into one storm signal feeding RCA.
  *AC:* A burst of N similar traps within a short window is represented as one storm signal with count, not N incidents.

### FR-I — Incident synthesis & output

- **FR-I1** Emit **one incident** per correlated root cause into Alert Policy & Event Correlation, carrying root cause, confidence, evidence, blast radius, timeline, and recommended remediation (where a signature provides one).
  *AC:* The correlated result is a single incident record with all listed fields populated and consistent with the underlying signals.
- **FR-I2** Recovery handling — when root-cause and symptom signals clear, the incident auto-resolves/closes with a recovery timeline.
  *AC:* Clearing the seeded fault transitions the incident to resolved within the configured window; the recovery is timestamped.

### FR-J — Integration & actions

- **FR-J1** Feed the incident to ServiceOps (incident creation with CI mapping) and Notifications.
  *AC:* A qualifying incident creates a ServiceOps incident linked to the root-cause CI, and fires the configured notification channel.

### FR-K — Non-functional: scale, latency, accuracy *(see also §6)*

- **FR-K1** Sustain the platform's peak combined signal rate across all telemetry types without dropping correlation.
  *AC:* At target peak signal rate over a soak test, no correlation-affecting signal loss; queue drains.
- **FR-K2** Time-to-RCA within a bounded latency after the contributing signals arrive.
  *AC:* p95 time from last contributing signal to emitted incident ≤ (correlation window + target seconds).

### FR-L — RBAC, multi-tenancy, retention, audit

- **FR-L1** Incidents, signals, and correlation config are tenant-scoped and RBAC-governed.
  *AC:* A tenant sees only its incidents/signals; a viewer role cannot edit correlation policy.
- **FR-L2** Retention of incidents/evidence independent of raw-telemetry retention; all config changes audited.
  *AC:* Incidents remain queryable after raw signals age out; correlation-policy edits appear in the audit log with actor/time.

### FR-M — Explainability

- **FR-M1** For any incident, expose *why* this root cause was chosen (which topology path, which signals, which rule, what confidence).
  *AC:* An incident's "why" view lists the deciding factors; two engineers reviewing it reach the same understanding without source access.

---

## 5. Cross-telemetry acceptance scenarios (worked, QA-ready)

Each scenario is an end-to-end acceptance test: inject the fault, assert one incident with the right root cause + evidence + blast radius.

| #   | Injected fault                                    | Signals that fire (by type)                                                                                                       | Expected root cause                              | Evidence must cite                   | Blast radius                     |
| --- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------ | -------------------------------- |
| S1  | Switch uplink down                                | **trap** linkDown; **flow** traffic drop on uplink; **metric** interface down; **trace** app errors; **log** connection timeouts  | the **interface/link CI**                        | ≥3 telemetry types incl. the trap    | all hosts/apps behind the uplink |
| S2  | ESXi host CPU contention                          | **metric** CPU-ready high (host+VMs); **trace** latency up; **log** app slow-query warnings                                       | the **ESXi host CI**                             | metric (ready%) + trace              | VMs/apps on the host             |
| S3  | App DB connection-pool exhaustion (infra healthy) | **trace** span errors; **log** pool-exhausted errors; metrics/flow/trap **healthy**                                               | the **app CI** (localize; no infra blame)        | trace + log; note "upstream healthy" | the service + its consumers only |
| S4  | Storage/datastore latency (noisy neighbor)        | **metric** datastore latency; **trace** DB slow; **log** iowait; **flow** normal                                                  | the **datastore CI**                             | metric (GAVG) + trace                | VMs on the datastore             |
| S5  | DDoS on a service                                 | **flow** volumetric anomaly / security detection; **metric** bandwidth spike; **trap** device high-CPU; **trace** latency/timeout | the **flow-security detection / target edge CI** | flow + metric + trace                | the targeted service             |
| S6  | Trap storm from a flapping device                 | **trap** flood; **metric** availability flaps                                                                                     | one **storm** incident on the device CI          | trap storm (count)                   | device + dependents              |

*For each: assert exactly ONE incident, correct root-cause CI, evidence spanning the listed telemetry types, blast radius matching the affected set, and symptom-signal suppression count > 0 where applicable.*

---

## 6. Non-functional acceptance criteria (targets to tune)

| Metric                                                          | Acceptance target                     |
| --------------------------------------------------------------- | ------------------------------------- |
| Root-cause accuracy (top-1 = injected CI) across scenario suite | ≥ 90%                                 |
| No-false-blame localization (S3-type)                           | must pass (pass/fail)                 |
| Cross-telemetry grouping (one fault → one incident)             | ≥ 95% of scenarios                    |
| Blast-radius completeness                                       | ≥ 90% of actually-impacted CIs        |
| Alert-noise reduction (signals → incidents)                     | ≥ 70% fewer actionable items          |
| Time-to-RCA (p95)                                               | ≤ correlation window + target seconds |
| Sustained combined signal ingest with correlation on            | ≥ platform peak (validate)            |
| Entity-resolution accuracy                                      | ≥ 95% of resolvable signals           |

---

## 7. Assumptions, dependencies & open questions

**Assumptions:** collectors already produce the raw telemetry; Discovery/CMDB provides a reasonably complete topology (RCA quality ∝ topology completeness — gate on it); clocks are NTP-synced within the skew bound.
**Dependencies:** unified Signal ingestion, shared entity/topology model, AIOps anomaly primitives, Alert Policy & Event Correlation as the incident surface.
**Open questions (decide before build):**

1. **Correlation window default** per telemetry mix (traces are sub-second; traps/metrics are seconds-minutes) — one adaptive window or per-type windows?
2. **Weighting** of telemetry types in root-cause scoring (does a trap outrank a metric anomaly?) — configurable defaults needed.
3. **Confidence threshold** for auto-creating a ServiceOps incident vs holding for review.
4. **Trace sampling** — how partial trace sampling affects trace-derived evidence/accuracy.
5. **Unattributed signals** — handling policy for signals that don't resolve to a CI (queue, best-effort, drop-with-log).
6. **Storm thresholds** per telemetry type.

---

*Companion: `../rca-poc-observeops/` (topology-based RCA algorithm + blended engine this extends), `../serviceops-asset-cmdb-endpoint-unification/` (the CI/entity model signals resolve to).*

**Role of this doc:** Motadata **functional & acceptance criteria** only (broad, engine-agnostic). It does **not** specify CMDB-vs-Discovery gate policy, dual-graph stores, Panorama/Murphy/Nezha depth, or the Vector-class Collect pipeline.

**Supplementary Motadata architecture** (Federated two-tier graph + RCA flow + Vector Collect) and DT objective mapping: [`FEDERATED_VS_DT_PIPELINE_GAPS.md`](./FEDERATED_VS_DT_PIPELINE_GAPS.md) §1.2–§1.3 · §2 · §8 · hosted [`:8765`](http://127.0.0.1:8765/federated-vs-dt-pipeline-gaps.html#functional-objectives-motadata-achievability-not-dt-product-clones). AC + architecture are **one product story, two layers** — not contradictions.
