# Edge Delta local k3d fabric — 2026-08-17

**Honesty:** Observed (MCP + kubectl) on WSL. Degraded lab: **Node only**, no Gateway/Coordinator. Not the two-VM production picture.  
**Org:** `gmailcom_d4486595`  
**Cluster:** `k3d` cluster `ed-lab` (1 node: `k3d-ed-lab-server-0`)  
**Pipeline:** Edge fleet tagged `kubernetes` (AI Team Kubernetes connector). Helm in namespace `edgedelta`.  
**Do not flip HLD D5.**

---

## What we installed

| Layer | This host |
|-------|-----------|
| Node Pipeline | DaemonSet Running (`edgedelta-wf5gq`). Tailers on `ed-lab` pods. Compactor/rollup/aggregator/eBPF **off** (RAM). |
| Gateway / Coordinator | **Not installed** |
| Workloads (`ed-lab`) | `noisy-logger` (UC1) · `crash-loop` CrashLoopBackOff (UC8) · `fake-ingest` (UC6 lite) · `inventory-ok` |
| AI Team | Kubernetes connector **Connected**. Auto-monitors named in the connector UI (Pod Crash / Startup / Placement / Node Health). |

Host: 2 CPU / 7.8 Gi, ~2.3 Gi available after k3d + agent. Helm chart defaults (2 CPU / 2 Gi **per extra agent**) would not fit.

---

## Use cases (this pass)

| UC | Execute? | Observed |
|----|----------|----------|
| **8** Kubernetes troubleshooting | **Yes — events** | `event.domain:"K8s"` `@event.reason:"BackOff"` on `crash-loop` / `ed-lab`. Body: back-off restarting container `boom`. |
| **1** Anomaly-triggered | **Partial** | Negative **log patterns** for `checkout-api` `payment_auth failed`. `event.type:"pattern_anomaly"` still **0** (monitor needs a baseline; do not wait for ERROR/SLOWDOWN twins). |
| **6** Ingest failure | **Lite** | Patterns: `ingest-api` `kafka produce timeout` / `broker unreachable`. No Kafka. |
| **4** Database performance | **Skipped** | Needs Gateway + OTLP + nginx/Postgres. Does not fit this WSL node. |
| **10** Data locality | **Write-up** | Native MCP already queries **K8s events + patterns** on this org. Log *search* API returned 500 this session; patterns still prove the stream is in ED, not a foreign lake. |
| **9** GitHub | Unchanged | Still the daily report; not this cluster. |

**AI credits:** Free plan **48 / 50** used (2026-08-17 Plan page). Did **not** start an OnCall investigation this pass.

---

## Next (when VMs exist)

Install Coordinator + Gateway on RTX when quota allows. Recreate two-node UC8 there if needed. Add nginx/Postgres for UC4. Combined run: [`edgedelta-lab-run-2026-08-17.md`](./edgedelta-lab-run-2026-08-17.md).
