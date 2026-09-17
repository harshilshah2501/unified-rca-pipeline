# Datadog tenant + lab evidence — 2026-08-04

Appendix for [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md).  
**Labels:** Observed (agent) + Observed (MCP) + **Observed (lab)** from `datadog-rca-lab`.

---

## 1. Lab run (Dynatrace-parity scenario)

| Item | Value |
|------|-------|
| Topology | `frontend` → `product` → `inventory` (Flask + `ddtrace`) |
| Env tag | `env:rca-lab` |
| Host | `DESKTOP-MBPAQK1` (Agent 7.81.3 → `trace.agent.datadoghq.com`) |
| Fault | `./scripts/fault.sh inventory fail` → inventory `GET /api/stock` **503** |
| Symptom | checkout returns **502**; product sees `inventory_status:503` |
| Window | ~2026-08-04T05:35–05:36Z UTC |

Healthy then fault load: 25×200 then 50×502 on `http://127.0.0.1:18080/api/checkout`.

---

## 2. APM aggregates (`env:rca-lab`, last ~30m)

| service | status | span count |
|---------|--------|------------|
| frontend | ok | 190 |
| product | ok | 190 |
| inventory | ok | 175 |
| frontend | error | 102 |
| product | error | 102 |
| inventory | error | 51 |

Traces explorer (errors):  
https://app.datadoghq.com/apm/traces?query=env%3Arca-lab+service%3Ainventory+status%3Aerror

---

## 3. Distributed trace (example)

**Trace ID:** `6a717a3e00000000a9fa020928a93f8c`  
**UI:** https://app.datadoghq.com/apm/trace/6a717a3e00000000a9fa020928a93f8c

Call chain (service entry / client peers):

```text
frontend  GET /api/checkout          → http.status_code 502  (error)
  └─ requests → product              → 502  (peer.hostname:product)
       product GET /api/product      → 502  (error)
         └─ requests → inventory     → 503  (peer.hostname:inventory)
              inventory GET /api/stock → 503  (error)
```

**Insight:** Same failure propagates as **503 at leaf, 502 upstream** — Datadog marks multiple services `status:error` on one trace. Localize by reading the **deepest** error / peer edge, not the entry span alone. Service Map catalog API had not yet returned edges at T+~2m; edges are **visible on the trace** via `peer.hostname`.

---

## 4. Detect surfaces during the run

| Surface | Observation |
|---------|-------------|
| Auto APM monitor | `[operation:flask.request] High Error Rate on {{service.name}}` **created** 2026-08-04T05:36:11Z (Datadog Support auto-gen) — query uses `trace.flask.request.errors/hits` by `{env,service}`, threshold `> 0.1` over `min(last_15m)`. Status still **OK** at T+minutes (needs sustained 15m window). |
| Watchdog events | `source:watchdog` search in same hour: **0** new stories for lab services |
| Incidents | Not checked as packaged; prior tenant baseline was 0 |

**Insight:** Detect door for this fault is primarily **APM error-rate monitors** (auto-created once Flask traffic appears), not immediate Watchdog. Watchdog may lag or never fire on a short synthetic spike.

---

## 5. Agent path (local)

```text
ddtrace (containers) → host Agent APM 0.0.0.0:8126 (apm_non_local_traffic)
  → Writer → https://trace.agent.datadoghq.com
```

`datadog-agent status` showed Python 3.12 / ddtrace 2.21.3 TCP intake for `service:frontend|product|inventory,env:rca-lab` at 100% priority sampling.

---

## 6. Reproduce

```bash
cd labs/datadog-rca-lab
docker compose up -d --build
./scripts/load.sh 20
./scripts/fault.sh inventory fail
./scripts/load.sh 40
# UI: APM → env:rca-lab → services frontend|product|inventory
./scripts/fault.sh inventory ok
```

Lab guide: [`../labs/datadog-rca-lab/DATADOG_RCA_REFERENCE.md`](../../labs/datadog-rca-lab/DATADOG_RCA_REFERENCE.md)
