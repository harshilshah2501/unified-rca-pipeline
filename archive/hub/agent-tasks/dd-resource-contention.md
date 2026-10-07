# Agent task · Datadog RESOURCE_CONTENTION (semantic)

**Status:** agent_task → promote after Observed run  
**Hub:** http://127.0.0.1:8765/dd-detect-category-hub.html?cat=resource_contention  
**Timeline:** http://127.0.0.1:8765/dd-lab-timeline-resource-contention.html  
**Lab root:** `labs/datadog-rca-lab/`

## Guardrails

1. Do **not** force Datadog to behave like Dynatrace Davis `RESOURCE_CONTENTION`.
2. Fault via **Python code** (`RESOURCE_BURN` markers) only — not env-only simulation.
3. Leave Dynatrace lab/docs and DD ERROR/SLOWDOWN teaching pages untouched.
4. Run **after** a healthy baseline; do not overlap with other scenario windows.

## Goal

Induce background CPU burn on inventory while `/api/stock` stays fast HTTP 200. Document what Datadog **actually** showed (Host pack / Watchdog infra / empty Detect).

## Steps

```bash
cd labs/datadog-rca-lab
./scripts/run_resource_contention_rca.sh --minutes 10
```

## Success criteria

- [x] Burn active; stock/checkout stay fast 200
- [x] UTC window + `DD_VERSION` recorded (`rc-20260813T065225Z` · APM `rc-20260813t065225z` · 06:53:04Z–07:03:05Z)
- [x] Detect honesty via MCP (Host pack load Alert; no Davis stamp)
- [x] Lab healed to baseline

## Observed notes (2026-08-13 Write · 2026-08-14 MCP)

- Fault: Python `RESOURCE_BURN` thread only.
- Door A: monitor `310484611` System load high — Triggered 06:56:31Z · Recovered 07:07:31Z.
- APM all ok / Flask `310925690` OK; Watchdog stories not claimed (toolset absent).
- Snapshot: `docs/vendor-source/datadog/dd-rc-20260813-snapshot.json`
