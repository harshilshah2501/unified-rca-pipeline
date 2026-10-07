# Datadog ERROR lab evidence — KeyError · `env:rca-lab-e3` · 2026-08-10

**Honesty:** Observed (MCP) + Observed (lab) · site `app.datadoghq.com` · host `DESKTOP-MBPAQK1`  
**Filter:** `env:rca-lab-e3` · `version:keyerror-20260810T072333Z`  
**Retired teaching filters:** `env:rca-lab`, `env:rca-lab-e2`

## Defect

| Item | Value |
|------|--------|
| File | `labs/datadog-rca-lab/inventory/app.py` |
| Change | `"WIDGET-1"` commented out of `WAREHOUSE_SKU_INDEX` |
| Mechanism | `lookup_stock_in_warehouse("WIDGET-1")` → **KeyError** |
| Scripts | `break_inventory_code.sh` / `heal_inventory_code.sh` |
| Telemetry hygiene | No `fault.injected` span tags; no `"fault"` log fields |

## Lab clocks (UTC)

| Window | Kind | Notes |
|--------|------|-------|
| **Before 07:24:50Z** | **Baseline** | Healthy checkouts — live baseline + warm discovery |
| **07:24:50Z – 07:31:13Z** | **Fault W1** | Break #1 → heal · *not* baseline |
| **~07:31Z – 07:45:54Z** | Healthy again | Post-heal |
| **07:45:54Z – ~07:56:42Z** | **Fault W2** | Heavy re-break · Door A Alert after sustain |

| Event | Time |
|-------|------|
| Break #1 | 2026-08-10T07:24:50Z |
| Break #1 up | 2026-08-10T07:25:10Z |
| Heal #1 | 2026-08-10T07:31:13Z |
| Re-break (heavy) | 2026-08-10T07:45:54Z |
| Heavy load end | 2026-08-10T07:56:42Z |
| Post-load drip | continued (catalog still broken for Live UI) |

IST ≈ UTC+5:30 (e.g. re-break **13:15** IST).

## Where telemetry writes (backend)

| Product rail | Sink |
|--------------|------|
| Metrics | Classic **timeseries store** |
| APM / Traces | **Husky** / Event Platform |
| Logs | **Husky** / Event Platform |

## Fault-time infra (MCP span tags, reload window)

| Tag | Value |
|-----|--------|
| `container_name` | `dd-inventory` |
| `container_id` (reload) | `3f0f94af1ade8d7b2c50e56b23af7c12480a781368e8c127c08de1f6e8069da3` |
| `docker_image` / `image_name` | `datadog-rca-lab-inventory` |
| `image_id` | `sha256:ef224e9d27e1e73d88297da3056364770f1ca357b4b7f0d3f47e1d7bf7bd7a77` |
| First-break container (local meta) | `165bbcad2f1d90e6e4e5c7fc9b11e3e1d61f9e94778eea80693bba281b735751` |

Note: host also carries `env:dev` Agent default alongside app `env:rca-lab-e3`.

## APM — typed error spans (MCP `aggregate_spans`, from 07:24Z → query time)

| service | @error.type | @http.status_code | count |
|---------|-------------|-------------------|------:|
| inventory | KeyError | 500 | **2427** |
| product | UpstreamInventoryError | 502 | **2421** |
| frontend | UpstreamProductError | 502 | **2421** |

Sample leaf message: `KeyError: 'WIDGET-1' — SKU missing from WAREHOUSE_SKU_INDEX`.

## Metrics (MCP `get_datadog_metric` scalar, `env:rca-lab-e3`)

| Metric | Group | sum (as_count) |
|--------|-------|----------------:|
| `trace.flask.request.errors` | service:inventory | **2403** |
| `trace.flask.request.errors` | service:product | **2397** |
| `trace.flask.request.errors` | service:frontend | **2397** |
| `rca.inventory.stock.errors` | (env) | **2403** |

## Logs (MCP `analyze_datadog_logs`, `env:rca-lab-e3 status:error`)

| service | @event | @error_type | n |
|---------|--------|-------------|--:|
| inventory | inventory.stock.error | KeyError | **2486** |
| product | product.upstream.error | UpstreamInventoryError | **2481** |
| frontend | checkout.upstream.error | UpstreamProductError | **2480** |

Explorer: `env:rca-lab-e3 @event:inventory.stock.error`

## Sample distributed trace (MCP)

| Field | Value |
|-------|--------|
| trace_id | `6a79840f000000005f3c58a8cfc1f888` |
| Time | ~2026-08-10T07:55:59Z |
| Chain | frontend `GET /api/checkout` **502** → product `GET /api/product` → inventory `GET /api/stock` **500** |
| UI | https://app.datadoghq.com/apm/trace/6a79840f000000005f3c58a8cfc1f888 |

## Detect doors (MCP)

| Door | Monitor / surface | ID / key | Observed |
|------|-------------------|----------|----------|
| **A · Monitors** | `[operation:flask.request] High Error Rate` | `310925690` | Query `min(last_15m): errors/hits > 0.1` · status **Alert** after sustained reload (short first window alone often stayed OK) |
| **B · Watchdog APM** | Bridge `events(source:watchdog story_category:apm)` | `310485027` | Status **OK** · **0** `story_category:apm` events for lab services in window |
| **B · Watchdog Logs** | `story_type:logs_pattern_anomaly` | inventory `f5ebc59d-88e6-55eb-a625-31bd6bd0b23f` · product `43e60457-…` · frontend `05f69bc6-…` | **Present** under `env:rca-lab-e3` from ~07:51Z (title: “New error logs were detected”) |
| **Incident** | — | — | **0** matching Incidents |

Teaching: Door A can ALERT on long enough ERROR windows; Door B **logs** stories ≠ Door B **APM** bridge. Detect ≠ Bits ≠ Incident.

## Bits

Open from Watchdog log story or APM inventory · expect KeyError / HTTP 500 · infra version/container · **no** `fault.injected`. Peer tab: [`dd-bits-error-review.html`](./dd-bits-error-review.html).

## Meta file

`docs/vendor-source/datadog/fresh-error-run-20260810T072450Z.meta`
