# Agent task · Datadog AVAILABILITY (semantic)

**Status:** agent_task → promote after Observed run  
**Hub:** http://127.0.0.1:8765/dd-detect-category-hub.html?cat=availability  
**Timeline:** http://127.0.0.1:8765/dd-lab-timeline-availability.html  
**Lab root:** `datadog-rca-lab/`

## Guardrails

1. Do **not** require a Datadog “AVAILABILITY” category stamp.
2. Fault via **Python** `SCENARIO_MODE="AVAILABILITY_DOWN"` (process exit) — not docker-stop-as-primary teaching story.
3. Leave Dynatrace + DD ERROR/SLOWDOWN docs untouched.
4. Run only on a healed baseline; sequential, not parallel with other cats.

## Goal

Inventory process exits ~2s after boot; callers fail. Document native Detect surfaces (process/container check, caller APM) without renaming them to Davis categories.

## Steps

```bash
cd datadog-rca-lab
./scripts/run_availability_rca.sh --minutes 10
```

## Success criteria

- [x] Inventory down during window; checkout fails (HTTP 502)
- [x] UTC + version recorded (`avail-20260813T070424Z` · APM `avail-20260813t070424z` · 07:05:45Z–07:17:04Z)
- [x] Detect honesty via MCP (caller APM + DIE; no Davis AVAILABILITY stamp)
- [x] Healed to HEALTHY

## Observed notes (2026-08-13 Write · 2026-08-14 MCP)

- Fault: `SCENARIO_MODE="AVAILABILITY_DOWN"` → `os._exit(1)` ~2s after boot.
- APM: FE/product error (~243); inventory 0 spans; sample `UpstreamProductError` → 502.
- Infra: inventory DIE ~07:05:35Z. Flask Alert not locked for this short window.
- Snapshot: `docs/vendor-source/datadog/dd-avail-20260813-snapshot.json`
