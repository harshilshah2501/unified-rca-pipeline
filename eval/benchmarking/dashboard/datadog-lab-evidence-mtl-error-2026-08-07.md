# Datadog ERROR · Metrics ∥ Traces ∥ Logs evidence — 2026-08-07

Appendix for production-grade **error-rate increase** teaching across all three rails.
Companion: [`dd-error-mtl-dissection.html`](./dd-error-mtl-dissection.html) · Timeline [`dd-lab-timeline-error.html`](./dd-lab-timeline-error.html).

**Labels:** Observed (lab) + Observed (MCP). Tenant site: `datadoghq.com`. Host: `DESKTOP-MBPAQK1`.

---

## 1. Scenario

| Item | Value |
|------|-------|
| Topology | `frontend` → `product` → `inventory` (Flask + `ddtrace`) |
| Env | `env:rca-lab` · `version:1.0.0` |
| Inject | `./scripts/fault.sh inventory fail` |
| Leaf | inventory `GET /api/stock` → **503** · `error.type:InventoryFault` |
| Cascade | product/frontend checkout → **502** |
| Emit rails | APM spans · DogStatsD `rca.*` · JSON logs + Agent `rca_lab_logs.d` file tail |
| Window | ~2026-08-07T09:19–09:20Z UTC (plus prior load in last 30m) |

---

## 2. Metrics (Observed MCP)

Scalar queries ~`now-30m`, filters `env:rca-lab`:

| Series | Sum (as_count) |
|--------|----------------|
| `rca.inventory.stock.errors` | **80** |
| `rca.checkout.errors` | **80** |
| `trace.flask.request.errors` by `{service}` | frontend **34** · product **34** · inventory **34** |

Teaching: custom DogStatsD mirrors the business leaf (`stock.errors`); APM auto metrics feed Monitors door A.

---

## 3. Traces / APM (Observed MCP)

`aggregate_spans` · `env:rca-lab status:error` · ~30m:

| service | error span count |
|---------|------------------|
| frontend | **219** |
| product | **219** |
| inventory | **146** |

Leaf tags on inventory spans: `http.status_code:503`, `error.type:InventoryFault`, `fault.injected:true` (lab).

Explorer: `env:rca-lab service:inventory status:error`

---

## 4. Logs (Observed MCP)

Query: `env:rca-lab service:inventory @event:inventory.stock.error`

| Field | Observed |
|-------|----------|
| `status` | `error` |
| `@event` | `inventory.stock.error` |
| `@http_status` | `503` |
| `@error_type` | `InventoryFault` |
| `@sku` | `WIDGET-1` |
| Join | platform `trace_id` / `span_id` on the log event (log↔trace) |

Example message body (also carries optional host OneAgent `dt.*` noise in the string):  
`stock request failed — fault injected`

Logs explorer:  
https://app.datadoghq.com/logs?query=env%3Arca-lab+service%3Ainventory+%40event%3Ainventory.stock.error

Approx **80+** matching inventory ERROR lines in the capture window (MCP returned truncated batch; count ≥80).

---

## 5. Subsystem map (this run)

| Subsystem | Outcome |
|-----------|---------|
| Agent | Traces :8126 · DogStatsD :8125 · file logs via `rca_lab_logs.d` |
| Tagging | `service` / `env:rca-lab` / `version` on all rails |
| Metrics store | `rca.*` + `trace.flask.request.errors` present |
| APM store | Strong cascade error spans |
| Logs store | JSON indexed with `@event` / `@error_type` |
| Monitors | Auto Flask High Error Rate may stay OK under `min(last_15m)` |
| Watchdog / Incident | Not required for MTL leaf claim; often **0** on short labs |
| Operator leaf | Flamegraph deepest **503** + log `InventoryFault` + metric `rca.inventory.stock.errors` |

---

## 6. Correlate one request (operator recipe)

1. Metrics: spike on `rca.inventory.stock.errors` and APM error ratio for `service:inventory`.
2. Traces: open failing checkout → deepest span inventory **503**.
3. Logs: same `trace_id` → `@event:inventory.stock.error`.
4. Do **not** stop at frontend **502** — edge symptom on all three rails.

---

## 7. Reproduce

```bash
cd datadog-rca-lab
docker compose up -d --build
./scripts/run_error_rca.sh --minutes 12
# or: fault.sh inventory fail → load.sh → fault.sh inventory ok
tail -n 5 logs/inventory.log
```

UI: Metrics `rca.*` · APM `env:rca-lab status:error` · Logs `@event:inventory.stock.error`.

## Detect doors (hub alignment)

- **Door A:** Flask High Error Rate — thr `> 0.1`, `min(last_15m)` — often **OK** on short KeyError window.
- **Door B:** Watchdog `error_rate` stories → bridge Anomaly monitor **ALERT** (fresh `env:rca-lab-e2`).
- Primary Detect inputs = **Metrics/APM**; Logs corroborate via tag join. Detect ≠ Bits ≠ Incident.
- Shared IPO/Method: [`dd-detect-category-hub.html`](./dd-detect-category-hub.html) · Breakdown stage 06.

