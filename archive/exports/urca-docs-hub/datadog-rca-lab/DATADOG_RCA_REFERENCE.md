# Datadog RCA Lab — Reference Guide

Same three-service topology as `dynatrace-rca-lab`, instrumented with **ddtrace** → host **Datadog Agent** (`:8126`) so you can compare APM / Service Map / monitors with Dynatrace Smartscape / Grail / Davis.

**Docs hub:** [Detect categories](http://127.0.0.1:8765/dd-detect-category-hub.html) · [ERROR Timeline](http://127.0.0.1:8765/dd-lab-timeline-error.html) · [ERROR · MTL deep](http://127.0.0.1:8765/dd-error-mtl-dissection.html?cat=error) · [SLOWDOWN Timeline](http://127.0.0.1:8765/dd-lab-timeline-slowdown.html)

---

## 1. Purpose

Generate controlled telemetry for Datadog’s detection and RCA surfaces (not an app demo).

For each injected fault, record:

| Fault | First Signal | Monitor / Watchdog | Root Cause hint | Service Map | Trace | Logs | Metrics |
| ----- | ------------ | ------------------ | --------------- | ----------- | ----- | ---- | ------- |

---

## 2. Lab Topology

```text
            curl :18080
              │
              ▼
      frontend:8080  ──ddtrace──► Agent :8126 ──► Datadog HQ
              │                    DogStatsD :8125
              │                    file logs → rca_lab_logs.d
              ▼
       product:8081
              │
              ▼
     inventory:8082
```

Prerequisites: Datadog Agent running on the host (`systemctl status datadog-agent`), APM enabled, preferably `apm_non_local_traffic: true` so Docker can reach `:8126`. DogStatsD UDP `:8125` for custom `rca.*` metrics. Log tail config: `/etc/datadog-agent/conf.d/rca_lab_logs.d/conf.yaml` → `logs/{frontend,product,inventory}.log`.

Caller timeouts are **40s** so code-level SLOWDOWN (~9s) is not truncated.

---

## 3. ERROR vs SLOWDOWN injection

| | ERROR | SLOWDOWN |
|--|-------|----------|
| Mechanism | `./scripts/break_inventory_code.sh` — drop `WIDGET-1` from `WAREHOUSE_SKU_INDEX` → **KeyError** | `./scripts/break_inventory_slow_code.sh` (ledger scan) |
| HTTP | inventory **500**; checkout **502** | inventory **200** ~9–22s; checkout **200** slow |
| MTL emit | APM error spans (`error.type:KeyError`) + DogStatsD `rca.*.errors` + JSON `@event:inventory.stock.error` | APM high `@duration` · ok logs (`inventory.stock.ok`) |
| Not used | `fault.sh … fail` (legacy flag; teaching prefers real KeyError) | `faults/*.latency` sleep (teaching rejects sleep) |
| Runner | `./scripts/run_error_rca.sh` | `./scripts/run_slowdown_rca.sh` |
| Heal | `./scripts/heal_inventory_code.sh` | `./scripts/heal_inventory_slow_code.sh` |
| Detect tip | Door A Flask Alert after sustain · APM KeyError · logs Watchdog (e3) | **05 empty** (error Door A OK · latency Door A absent · Watchdog 0) · leaf via operator APM / longest self-time |
| Packaged RC | Often none (Incident 0; Bits optional) | Often none (Watchdog 0 · Incident 0) |
| Teaching page | [MTL dissection](http://127.0.0.1:8765/dd-error-mtl-dissection.html?cat=error) · [Bits](http://127.0.0.1:8765/dd-bits-error-review.html) | [SLOWDOWN timeline](http://127.0.0.1:8765/dd-lab-timeline-slowdown.html) · Observed e3 2026-08-11 |

---

## 4. ERROR · Metrics ∥ Traces ∥ Logs (production-grade)

Under code-level KeyError, each checkout should light **all three rails** under `env:rca-lab-e3`:

| Rail | What to look for |
|------|------------------|
| **Metrics** | `sum:rca.inventory.stock.errors{env:rca-lab-e3}.as_count()` · `rca.checkout.errors` · `trace.flask.request.errors` by `{service}` |
| **Traces** | `env:rca-lab-e3 status:error` — leaf inventory `500` / `KeyError`; callers `502` |
| **Logs** | `env:rca-lab-e3 @event:inventory.stock.error` — `@error_type:KeyError` · join via `trace_id` |

Observed capture (**primary**, 2026-08-10 MCP): [`docs/datadog-lab-evidence-mtl-error-2026-08-10.md`](../docs/datadog-lab-evidence-mtl-error-2026-08-10.md)
(`rca.*`≈2403 · KeyError spans≈2427 · stock.error logs≈2486 · Door A Alert · Door B APM 0 · logs Watchdog yes).

Leaf claim = deepest inventory **KeyError / 500** + matching log + `rca.inventory.stock.errors` — **not** frontend 502 alone.

### Detect / Incidents (portal)

- **Telemetry RCA does not require an Incident.** APM + Logs + Metrics are enough for leaf claim.
- **Auto monitor** `[operation:flask.request] High Error Rate` (`310925690`) uses `min(last_15m)` — short windows often OK; sustained e3 load → **Alert**.
- **Door B APM bridge** (`310485027`) stayed **OK** on e3 (0 `story_category:apm`); Watchdog **logs** pattern anomalies did fire under `env:rca-lab-e3`.
- **Incidents** are optional packaging — declare manually, or skip and investigate in explorers / Bits.

---

## 5. SLOWDOWN · Metrics ∥ Traces ∥ Logs (Observed e3)

Under code-level ledger scan, each checkout lights **duration** on all three services while staying HTTP **200**:

| Rail | What to look for |
|------|------------------|
| **Metrics** | `p95:trace.flask.request{env:rca-lab-e3,service:inventory,version:slowdown-20260811t045553z}` — baseline ~5&nbsp;ms → fault ~9–22&nbsp;s |
| **Traces** | `env:rca-lab-e3 version:slowdown-20260811t045553z @duration:>5s` — leaf `inventory.stock` / `GET /api/stock` · `status:ok` · HTTP 200 |
| **Logs** | `env:rca-lab-e3 service:inventory` — `@event:inventory.stock.ok` · `http_status:200` · **0** KeyError |

Observed capture (**primary**, 2026-08-11 MCP): [`docs/vendor-source/datadog/slowdown-2026-08-11.json`](../docs/vendor-source/datadog/slowdown-2026-08-11.json)
(inventory stock p50≈10.9&nbsp;s · p95≈17.6&nbsp;s · 295 spans &gt;5&nbsp;s · error spans 0 · Door A error-rate OK · Watchdog APM 0 · Incident 0).

Leaf claim = **longest** inventory span (CPU ledger scan) — **not** `status:error` / HTTP 5xx.

### Detect / Incidents (portal)

- Error-rate Door A (`310925690`) stays **OK** — SLOWDOWN needs a **latency** Door A (p95/duration), which this lab did not scope.
- Watchdog Door B: **0** anomaly stories (deployment version story only).
- Incidents: **0**.

**Teaching insight (Write ≠ Detect ≠ Localize):** Stage **03 Write** had loud latency telemetry (p95 ~9–22s, hundreds of ok spans &gt;5s). Stage **05 Detect** stayed quiet — Datadog did not foghorn this run. The leaf was found because the lab **opened APM** for the known fault window and read the longest self-time span — operator **07 Localize**, not a Door. Slow explorer charts ≠ Detected incident. Full write-up: [Timeline §2](http://127.0.0.1:8765/dd-lab-timeline-slowdown.html?cat=slowdown#insight).

---

## 6. Quick start

```bash
cd datadog-rca-lab
docker compose up -d --build

# ERROR (full MTL)
./scripts/run_error_rca.sh --minutes 12
tail -n 5 logs/inventory.log   # JSON ERROR + dd.trace_id

# SLOWDOWN (code-level)
./scripts/run_slowdown_rca.sh --minutes 12
```

Host URLs: `http://127.0.0.1:18080/api/checkout`, `:18081`, `:18082`.

In Datadog UI (env `rca-lab`): **APM → Services** (`frontend`, `product`, `inventory`), **Service Map**, **Traces** / **Logs** / **Metrics** filtered by `env:rca-lab-e3`.

---

## 7. What to compare vs Dynatrace

| Concern | Dynatrace (lab) | Datadog (this lab) |
| ------- | --------------- | ------------------ |
| Collect | OneAgent | Agent + ddtrace → Trace Agent |
| Topology | Smartscape | Service Map / USM / inferred services |
| Telemetry store | Grail | Metrics / Traces / Logs backends |
| Detect | Davis Problems | Monitors + Watchdog |
| Localize | Problem evidence / entities | Flamegraph leaf + tag join across M∥T∥L |
| Package | Problem + rootCauseEntity (varies) | Often no Incident; operator MTL leaf |

For dual-vendor patterns after independent unveils: [`COMPARABLE_PIPELINE_DT_DD.md`](../docs/COMPARABLE_PIPELINE_DT_DD.md).


## Bits AI review

Step-by-step: [`docs/dd-bits-error-review.html`](../docs/dd-bits-error-review.html) · filter `env:rca-lab-e3` only (retire `rca-lab` / `rca-lab-e2` for teaching).
