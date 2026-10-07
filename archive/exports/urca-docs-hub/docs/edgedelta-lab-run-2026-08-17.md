# Edge Delta lab run — 2026-08-17

**Honesty:** Observed (UI + MCP + kubectl). Teaching analysis marked **Inferred**.  
**Org:** `gmailcom_d4486595` (`6da947fe-77af-421e-8a9c-dda8ead0b393`) · Pro after evening upgrade.  
**Do not flip HLD D5.** Issue ≠ Problem ≠ Bits ≠ Incident. No ERROR/SLOWDOWN twins.

Hub: [`ed-ai-team-hub.html`](./ed-ai-team-hub.html) · Timeline: [`ed-lab-timeline.html`](./ed-lab-timeline.html) · Portal: [`ed-portal-walkthrough.html`](./ed-portal-walkthrough.html) · Lab: [`ed-lab-setup.html`](./ed-lab-setup.html)  
WSL-only appendix: [`edgedelta-k3d-fabric-2026-08-17.md`](./edgedelta-k3d-fabric-2026-08-17.md) · UC9: [`edgedelta-uc9-github-2026-08-17.md`](./edgedelta-uc9-github-2026-08-17.md)

---

## What this day proved

Same E1→E11 order. **Locus** of P1 moved onto a Node DaemonSet. Detect signals appeared **without** Gateway, Coordinator, Packs, or an Issue.

| Layer | Job this day | Observed |
|-------|----------------|----------|
| **43 Packs** | Shape | None applied |
| **8 monitor types** | Notice | Pattern Anomaly still **0** events. K8s connector auto-monitors created; `event.domain:"Monitor Alerts"` empty. |
| **10 use cases** | Investigate | **9** (GitHub). **8** OnCall Investigating from Pod Crash Monitor (evening). **1 / 6** signals only. **4** eBPF traces + slow-query logs (no Gateway). **10** native MCP. |
| **Node** | Collect / tail | Yes — two clusters, one pipeline ID |
| **Gateway / Coordinator** | Aggregate / control plane | Coordinator installed. Gateway **not** (no Gateway pipeline ID in this AI-first nav). |
| **Platform + Team** | Index + investigate | Pro ingest OK on RTX. Issues still **0**. Thread ≠ Issue. |

---

## Sequence

### 1. UC9 (SaaS only) — morning

Daily GitHub Engineering Risk Report Resolved in `#code-issues` (391.1 K tokens). No cluster. Hidden `AI-Connector-Telemetry-Pipeline` (`IngestionPipeline`).

### 2. WSL k3d — midday — **ingest succeeded**

| | |
|--|--|
| Cluster | `k3d` `ed-lab` · node `k3d-ed-lab-server-0` |
| Connector | AI Team Kubernetes → Edge pipeline tag `kubernetes` (`5f43e54d-6afd-49c1-9209-6d92d8ce93ba`) |
| Agent | Helm Node DaemonSet, compactors/rollup **off** (2 CPU / ~3 Gi free) |
| Workloads | `noisy-logger` · `crash-loop` · `fake-ingest` · `inventory-ok` |

**MCP Observed (WSL node):**

| Signal | Query / object | Result |
|--------|----------------|--------|
| UC8 | `event.domain:"K8s"` `@event.reason:"BackOff"` | `crash-loop` / `ed-lab` / `k3d-ed-lab-server-0` |
| UC1 | negative patterns `k8s.namespace.name:"ed-lab"` | `checkout-api` `payment_auth failed` |
| UC6 | same | `ingest-api` `kafka produce timeout` / broker unreachable |
| Pattern Anomaly | `event.type:"pattern_anomaly"` | **0** |
| Log search API | `get_log_search` | **500** this session; patterns still proved the stream |
| Metrics | `ed.pipeline.node.read_bytes` by `host.name` | **only** `k3d-ed-lab-server-0` (~33 MB in a 30 min window) |

Agent later **uninstalled**; `ed-lab` namespace deleted so RTX would be the sole sender.

### 3. RTX host k3s — afternoon — **cluster up, SaaS refused**

Host `harshil@45.195.82.10` (`pro6000-server`): Ubuntu 24.04, 16 CPU, 125 Gi RAM. k3s `v1.36.3+k3s1`. Same Kubernetes pipeline ID. Same three workloads in `ed-lab`.

| Check | Observed |
|-------|----------|
| Node agent | Running; tailers on `ed-lab` pods; config loaded; outbound to `api.edgedelta.com` |
| CrashLoop | `crash-loop` CrashLoopBackOff on `pro6000-server` |
| MCP `k8s.node.name` | Still **only** `k3d-ed-lab-server-0` after RTX had been tailing |
| Agent log | `402 Payment Required` on `metric_upload_link`, `event_upload_link`, `s3_archive_upload_link`: *You are over your quota limit* |

Helm default also stood up **compactor + rollup**. Scaling those to 0 without disabling `rollUpProps` made the Node agent hammer `edgedelta-rollup-svc:9200` (connection refused). Cached-chart upgrade with [`labs/edgedelta/helm-values-wsl.yaml`](../labs/edgedelta/helm-values-wsl.yaml) left **Node-only**. Quota 402 remained.

### 4. Pro upgrade — evening — **RTX ingest OK**

Plan upgraded to Pro. Running agent still 402 until DaemonSet restart. After restart: `host.name: pro6000-server` in metrics + patterns. K8s BackOff + **K8s Pod Crash Monitor ALERT**. Coordinator Helm installed. Tracer/eBPF on. UC4 Postgres + nginx deployed (`labs/edgedelta/uc4-postgres.yaml`).

**Evening (later):** Node eBPF traces indexed (`ed.source.type: k8s_trace_input`, `otel.scope.name: edgedelta-eBPF`). MCP `service.name`: `checkout-db` / `checkout-api-db` (client spans to `net.peer.name: checkout-db`). Negative patterns still include `postgres slow query` / `pg_sleep`. Gateway still **not** installed — this tenant has no Pipelines nav (`/pipelines` redirects to AI Overview); MCP still only Edge `kubernetes` + GitHub IngestionPipeline.

**OnCall (16:52 IST):** Pod Crash monitor was already templated to `@ai-channel-alerts`. Suppression is on (first 5 then pause 3h — that is why live ALERTs did not start a thread). **Test Notifications** (Alert, group `BackOff` / `ed-lab` / `kubernetes`) created **two** Investigating threads titled `P3 K8s Pod CrashLoopBackOff Alert` in `#alerts` (source: K8s Pod Crash Monitor). Thread id `01M07Q8721EKGZR4ZPHFJDHV0D`. Issues still **0**. Also earlier: **Kubernetes Daily Health Report** Resolved at 14:16 IST (`#alerts`, workflow, ~1.19 M input tokens) — scheduled SRE report, not monitor-OnCall.

Pattern Anomaly events still **0**.

---

## Analysis (Inferred on Observed)

1. **Node-only is enough for UC1 log patterns and UC8 K8s events.** Gateway is a job (traces / OTLP / dedup), not a mandatory third SKU. Matches the vendor compose table.
2. **Detect can be loud while E11 stays quiet.** BackOff events + negative patterns ≠ Issue ≠ Pattern Anomaly monitor fire. The Team consumes a monitor/workflow; it does not invent an Issue from raw patterns alone on this tenant.
3. **E4 is after egress and can still fail.** Agent processed locally; SaaS returned 402 on upload links. Shift-left does not skip platform quota.
4. **One pipeline ID, two clusters** is a lab smell. WSL filled the index; RTX then hit quota. Do not run both senders on the Free plan.
5. **Credits vs ingest quota are different knobs.** Plan UI: AI **48/50** credits; 402 is upload/storage, not the GitHub token burn.
6. **UC4 traces can land from Node eBPF without Gateway.** Gateway remains the OTLP / network-ingest job, not the only trace path. Postgres + nginx workloads were already on RTX.

**D5 stays Review.** This run feeds the third AI geometry (standing Team, actions need approval) with a Node hygiene layer — it does not equate Issue with Problem or Bits.

---

## Still open

- Let **one** Pod Crash OnCall finish; the duplicate 16:52 thread was a second Test click — do not fire more Tests.
- Gateway Helm still needs a **separate** Gateway pipeline ID from classic Pipelines UI (this tenant hides that nav). OTLP from apps still not demonstrated; eBPF traces already exist.
- Pattern Anomaly events still **0** (monitor No Data).
- UC2 / UC3 / UC5 / UC7 wait on AWS / Elastic / CircleCI / PagerDuty connectors.
