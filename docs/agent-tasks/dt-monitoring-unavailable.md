# Agent task · MONITORING_UNAVAILABLE (visibility dark)

**Status:** Observed — **P-260826**  
**Docs Timeline:** http://127.0.0.1:8765/dt-cat-monitoring-unavailable-lab.html  
**Hub:** http://127.0.0.1:8765/dt-davis-category-hub.html?cat=monitoring_unavailable  
**Lab root:** `dynatrace-rca-lab/`  
**Snapshot:** `docs/vendor-source/dynatrace/p260826-monitoring-unavailable-snapshot.json`

## Goal

Produce a Dynatrace Problem in the **MONITORING_UNAVAILABLE** (or equivalent agent/ingest-dark) category for the **inventory** service while the checkout HTTP path still works (process up, callers succeed). Then heal, snapshot evidence, and promote the Timeline page from agent-task → Observed (like ERROR / SLOWDOWN).

## Why this category (not ERROR / SLOWDOWN / AVAILABILITY)

| Category | Leaf shape |
|----------|------------|
| ERROR | App returns 5xx / error_rate↑ |
| SLOWDOWN | HTTP **200** but response_time↑ |
| **MONITORING_UNAVAILABLE** | Process **still serves** traffic; **telemetry / agent / ingest goes dark** |
| AVAILABILITY | Process / container **down** (connection refused) |

## Constraints

- Do **not** stop the inventory container (that is AVAILABILITY).
- Do **not** inject 5xx or the ledger-scan slowdown.
- Heal before finishing; leave the lab healthy.
- Prefer real Dynatrace evidence (Problems API) over fabricated Problem ids.
- Update `docs/dt-cat-monitoring-unavailable-lab.html` and `docs/dt-davis-categories.js` when Observed.

## Steps

1. Confirm lab healthy: `curl -s http://localhost:19080/` → product + inventory stock JSON.
2. Break visibility only: `./scripts/break_inventory_monitoring_dark.sh`  
   - Recreates inventory with OTLP/SDK disabled so Dynatrace stops receiving inventory spans/metrics while HTTP stays up.  
   - If host OneAgent is instrumenting the container, also note/disable deep monitoring for that process (document what you did).
3. Sustain checkout load 10–15 min: `./scripts/load.sh` in a loop (or `./scripts/run_monitoring_unavailable_rca.sh --minutes 15`).
4. Poll Dynatrace Problems/Events for monitoring-unavailable / agent dark on inventory (or HOST running inventory). Record Problem id, start time, evidence types, `rootCauseEntity`.
5. Heal: `./scripts/heal_inventory_monitoring_dark.sh` — confirm OTLP/telemetry resumes and `/inventory` still 200.
6. Write snapshot JSON under `docs/vendor-source/dynatrace/` and rewrite the Timeline page to Observed (mirror SLOWDOWN page structure).
7. Set category `status: "observed"` and `problem: "P-…"` in `docs/dt-davis-categories.js`.

## Success criteria

- [x] Inventory HTTP 200 throughout the fault window (callers may be fine).
- [x] Dynatrace shows monitoring / ingest gap (not primarily SERVICE_ERROR_RATE_INCREASED or SERVICE_SLOWDOWN) — **P-260826** `CUSTOM_ALERT` on inventory PG.
- [x] Problem id + UTC clocks documented on the Timeline page.
- [x] Lab healed; scripts idempotent.

## Observed notes (2026-08-07)

- Break: OTEL off + PG `MONITORING_OFF` (OneAgent Python inject cleared) + host `oneagent` stopped 06:31–06:43 UTC.
- Native severity `MONITORING_UNAVAILABLE` / `OSI_UNEXPECTEDLY_UNAVAILABLE` did **not** auto-open in-window (platform-wide vs graceful stop).
- Surfaced **P-260826** via `events.ingest` `CUSTOM_ALERT` on inventory `PROCESS_GROUP` at **06:42:35 UTC**.
- Healed ~06:43 UTC; reinject verified.

## Scripts

| Script | Role |
|--------|------|
| `scripts/break_inventory_monitoring_dark.sh` | Inject visibility dark |
| `scripts/heal_inventory_monitoring_dark.sh` | Restore telemetry |
| `scripts/run_monitoring_unavailable_rca.sh` | Break → load → optional heal |

## Teaching cross-links

- Breakdown `?cat=monitoring_unavailable` — Detect tip = agent/ingest  
- Dual-track — Grail gaps, map may go stale  
- Compare Observed: ERROR P-260817 · SLOWDOWN P-260820 · **MONITORING_UNAVAILABLE P-260826**
