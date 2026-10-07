# Agent task · Datadog MONITORING_UNAVAILABLE (semantic)

**Status:** agent_task → promote after Observed run  
**Hub:** http://127.0.0.1:8765/dd-detect-category-hub.html?cat=monitoring_unavailable  
**Timeline:** http://127.0.0.1:8765/dd-lab-timeline-monitoring-unavailable.html  
**Lab root:** `datadog-rca-lab/`

## Guardrails

1. Datadog has **no twin** Davis `MONITORING_UNAVAILABLE` enum — teach the gap honestly.
2. Fault via **Python** `SCENARIO_MODE="MONITORING_DARK"` (skip `patch_all` + DogStatsD no-op).
3. Do not stop the container (that is AVAILABILITY) or inject KeyError/slow.
4. Leave Dynatrace + existing DD ERROR/SLOWDOWN sections undisturbed; run sequentially after heal.

## Goal

Inventory HTTP stays 200 while inventory APM/metrics go quiet. Document empty/partial Detect if that is what Datadog shows.

## Steps

```bash
cd datadog-rca-lab
./scripts/run_monitoring_unavailable_rca.sh --minutes 10
```

## Success criteria

- [x] HTTP 200 throughout; checkout succeeds (`scenario=MONITORING_DARK`)
- [x] Detect honesty via MCP (inventory APM 0; logs still present; no twin category)
- [x] UTC + version recorded (`mu-20260813T071758Z` · APM `mu-20260813t071758z` · 07:19:46Z–07:29:46Z); lab healed

## Observed notes (2026-08-13 Write · 2026-08-14 MCP)

- Fault: `SCENARIO_MODE="MONITORING_DARK"` (skip `patch_all` + DogStatsD no-op).
- APM: FE/product ok (~6168); inventory **0** spans. Logs: inventory 1564 still wrote (partial dark).
- Snapshot: `docs/vendor-source/datadog/dd-mu-20260813-snapshot.json`
