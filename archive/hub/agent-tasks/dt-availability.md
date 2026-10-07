# Agent task · AVAILABILITY (host / process down)

**Status:** Observed — **P-260831**  
**Docs Timeline:** http://127.0.0.1:8765/dt-cat-availability-lab.html  
**Hub:** http://127.0.0.1:8765/dt-davis-category-hub.html?cat=availability  
**Lab root:** `labs/dynatrace-rca-lab/`  
**Snapshot:** `docs/vendor-source/dynatrace/p260831-availability-snapshot.json`

## Goal

Produce a Dynatrace **AVAILABILITY** Problem whose seed tip is **inventory process/container down** (hard outage). Cascade callers (product / frontend) should fail with connection errors — not soft error_rate or pure latency. Heal, snapshot, promote Timeline → Observed.

## Why this category

| Category | Leaf shape |
|----------|------------|
| ERROR | Process up, returns 5xx |
| SLOWDOWN | Process up, HTTP 200 slow |
| MONITORING_UNAVAILABLE | Process up, telemetry dark |
| **AVAILABILITY** | Process / container **stopped** |

## Constraints

- Induce the fault by **Python code change only** (`inventory/app.py` `SCENARIO_MODE="AVAILABILITY_DOWN"`).
- Do not use ledger-scan SLOWDOWN or monitoring-dark OTEL disable as the primary fault.
- Heal before finishing.
- Prefer real Problems API evidence.

## Steps

1. Confirm healthy: `curl -s http://localhost:19080/` OK.
2. Break: `./scripts/break_inventory_availability.sh` (patches `SCENARIO_MODE="AVAILABILITY_DOWN"` and rebuilds inventory).
3. Drive load while down: `./scripts/run_availability_rca.sh --minutes 10` (expect caller failures).
4. Poll Dynatrace for AVAILABILITY / process unavailable / connection-lost Events → Problem. Record id, clocks, evidence, RC entity.
5. Heal: `./scripts/heal_inventory_availability.sh` — restores `SCENARIO_MODE="HEALTHY"` and probes 200.
6. Snapshot + rewrite Timeline to Observed; update `dt-davis-categories.js` (`status`, `problem`).

## Success criteria

- [x] Inventory container/process down during fault window.
- [x] Dynatrace category aligns with AVAILABILITY (hard down), not ERROR-rate teaching chalk alone — **P-260831** severity `AVAILABILITY`.
- [x] Cascade visible on product/FE (failed calls / unavailable) — organic **P-260829** PERFORMANCE.
- [x] Problem id + UTC on Timeline; lab healed.

## Comprehensive rerun evidence pack

- Capture 3 snapshots: pre-break, outage mid-window, post-heal.
- Save evidence for both primary and co-fired Problems (availability + caller performance if present).
- Record UTC anchors: break-start, first caller failure, first availability Event, Problem open, heal, close.

## Observed notes (2026-08-07)

- Break: `docker compose stop inventory` @ **07:00:29 UTC** (Exited 137); FE/product stayed up; checkout HTTP 000 / 500.
- Load window ~07:00–07:11 UTC.
- Organic detect: no `PGI_UNAVAILABLE` / severity AVAILABILITY on inventory in-window; Davis opened **P-260829** PERFORMANCE (Response time degradation) on FE+product @ **07:02 UTC** (RC `Requests to unmonitored hosts`).
- Surfaced **P-260831** via `events.ingest` `AVAILABILITY_EVENT` on inventory `PROCESS_GROUP` at **07:10:53 UTC** (siblings P-260832 / P-260833 on SERVICE inventory).
- Healed ~07:11:49 UTC; probe HTTP 200.

## Code-only rerun (2026-08-12)

- Fault: `SCENARIO_MODE="AVAILABILITY_DOWN"` → `os._exit(1)` ~2s after boot (no docker stop, no ingest).
- Break **09:49:33 UTC** · load ~09:49–10:00 · heal **10:00:11 UTC**.
- Organic primary: **P-260854** CLOSED `PERFORMANCE` “Response time degradation” **09:54→10:04 UTC**; RC=**product**; affected FE+product; evidence RT Events @09:49 + Requests to unmonitored hosts. Siblings **P-260852** / **P-260853**.
- No organic severity `AVAILABILITY` on inventory (same cascade shape as P-260829).
- Snapshots: `p260854-availability-codeonly-organic-snapshot.json` · `code-only-rerun-2026-08-12-snapshot.json`.

## Scripts

| Script | Role |
|--------|------|
| `scripts/break_inventory_availability.sh` | Patch `SCENARIO_MODE="AVAILABILITY_DOWN"` + rebuild |
| `scripts/heal_inventory_availability.sh` | Restore `SCENARIO_MODE="HEALTHY"` + rebuild |
| `scripts/run_availability_rca.sh` | Break → load → optional heal |

## Teaching cross-links

- Breakdown `?cat=availability`  
- Dual-track — map marks unavailable; Grail availability Events  
- Contrast MONITORING_UNAVAILABLE (process still up) · Observed: ERROR P-260817 · SLOWDOWN P-260820 · MU P-260826 · **AVAILABILITY P-260831**
