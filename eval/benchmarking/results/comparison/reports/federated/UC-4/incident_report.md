# Incident Analysis Report — `UC-4`

**Engine:** `federated` · **Schema:** `comprehensive_rca.v1` · **Completeness:** 15/15 (100.0%)

## RCA Summary

**Root cause:** `guest-os-vm-app-01` (`os_resource_exhaustion`)
Guest OS resource exhaustion

**Causal path:** `guest-os-vm-app-01` → `orders-api`

**Customer impact:** Symptom `error_rate_5xx` on `orders-api` (Guest OS resource exhaustion)

**Amplifier:** classic-infra cascade (shared upstream fault → app symptom)

**False leads ruled out:** none identified

**Change evidence:** Log retention / disk fill activity on guest-os-vm-app-01 filesystem

## Incident Summary

| Field | Value |
|-------|-------|
| Root CI | `guest-os-vm-app-01` |
| Signature | `os_resource_exhaustion` |
| Matches pack GT | True |
| Severity | P2 |
| Detected | 2026-07-10T10:00:18Z |
| Dimension | ObserveOps classic-infra · `2_infra` / `resource_contention` |
| Affected services | `orders-api` |
| Customer impact | Symptom `error_rate_5xx` on `orders-api` (Guest OS resource exhaustion) |

## Impact Assessment

- **SLA breach:** True
- **Data loss:** False
- **Fail fraction:** ≈2.8% of checkouts in the affected dimension
- **Blast / services:** `orders-api`

## Service Dependencies

**Critical path:** `vm-app-01` → `esxi-host-01` → `switch-core-01:GigE0/2`

Healthy siblings (pricing/inventory/token/fraud) are not on the failing payment path; errors escalate api-gateway ← checkout ← payment ← (DNS/RX/IRQ), with payment-provider as a decoy leaf.

## Distributed Traces

- Analyzed spans: 2
- Slow spans (>500ms): 0
- Span duration p50/max ms: 40.0 / 50.0

**Assessment:** Analyzed 2 spans; 0 exceed 500ms. Use span CI attributes with topology to separate symptom from root.

| Trace | Service | Span | Duration ms | CI / note |
|-------|---------|------|-------------|-----------|
| `uc4-t1…` | orders-api | POST /orders | 50.0 | orders-api |
| `uc4-t2…` | orders-api | GET /health | 30.0 | orders-api |

## Log Patterns

- Log retention / disk fill activity on guest-os-vm-app-01 filesystem
- No space left on device writing /var/log/orders-api
- kernel: Out of memory: Killed process 1842 (orders-api)
- orders-api service down after OOM / filesystem-full on guest OS

- `app.crash` × 1
- `infra.change` × 1
- `syslog.filesystem_full` × 1
- `syslog.oom_killer` × 1

## Metrics Analysis

- `guest-os-vm-app-01` `filesystem.used_pct` = **99.0** (threshold 95.0) at 2026-07-10T10:00:05Z
- `guest-os-vm-app-01` `oom_killer_event` = **1.0** (threshold 0.5) at 2026-07-10T10:00:12Z
- `orders-api` `error_rate_5xx` = **0.42** (threshold 0.05) at 2026-07-10T10:00:18Z
- `orders-api` `health_check` = **0.0** (threshold 1.0) at 2026-07-10T10:00:18Z

## Recent Changes

**Root-cause change:** 2026-07-10T09:56:00Z — Log retention / disk fill activity on guest-os-vm-app-01 filesystem
- 2026-07-10T09:56:00Z: Log retention / disk fill activity on guest-os-vm-app-01 filesystem

## Causal Chain

**Topology path:** guest-os-vm-app-01 → orders-api. Amplifier: high-cardinality request pattern.

**Narrative steps (evidence-backed):**

1. `infra.change` — Log retention / disk fill activity on guest-os-vm-app-01 filesystem (event, 2026-07-10T09:56:00Z)
2. `syslog.filesystem_full` — No space left on device writing /var/log/orders-api (event, 2026-07-10T10:00:05Z)
3. `syslog.oom_killer` — kernel: Out of memory: Killed process 1842 (orders-api) (event, 2026-07-10T10:00:12Z)
4. `app.crash` — orders-api service down after OOM / filesystem-full on guest OS (event, 2026-07-10T10:00:18Z)
5. `anomaly_filesystem.used_pct` — `guest-os-vm-app-01` filesystem.used_pct=99.0 (anomaly, 2026-07-10T10:00:05Z)
6. `anomaly_oom_killer_event` — `guest-os-vm-app-01` oom_killer_event=1.0 (anomaly, 2026-07-10T10:00:12Z)
7. `anomaly_error_rate_5xx` — `orders-api` error_rate_5xx=0.42 (anomaly, 2026-07-10T10:00:18Z)
8. `anomaly_health_check` — `orders-api` health_check=0.0 (anomaly, 2026-07-10T10:00:18Z)
9. `trace_symptom_spans` — 2 spans (p50≈40.0ms) corroborate the cascade (trace)

## Contributing Factors

- **Primary:** Guest OS resource exhaustion
- **Amplifier:** None
- **False leads:** 

## Timeline

- 2026-07-10T09:56:00Z · event — infra.change: Log retention / disk fill activity on guest-os-vm-app-01 filesystem
- 2026-07-10T10:00:05Z · event — syslog.filesystem_full: No space left on device writing /var/log/orders-api
- 2026-07-10T10:00:05Z · anomaly — guest-os-vm-app-01 `filesystem.used_pct`=99.0
- 2026-07-10T10:00:12Z · event — syslog.oom_killer: kernel: Out of memory: Killed process 1842 (orders-api)
- 2026-07-10T10:00:12Z · anomaly — guest-os-vm-app-01 `oom_killer_event`=1.0
- 2026-07-10T10:00:18Z · event — app.crash: orders-api service down after OOM / filesystem-full on guest OS
- 2026-07-10T10:00:18Z · anomaly — orders-api `error_rate_5xx`=0.42
- 2026-07-10T10:00:18Z · anomaly — orders-api `health_check`=0.0
- 2026-07-10T10:00:18Z · symptom_seed — Symptom seed orders-api / error_rate_5xx

## Remediation

Guest OS disk/memory exhaustion killed or blocked the app. Free filesystem space / address OOM, then restart the service. Infra below the OS should remain healthy.

_Source: `signature_template` (replace with LLM guidance when available)_

## Actions

### Immediate
- Free or extend filesystem space; restart the app after OOM/fs-full is cleared.
- Kill or limit runaway processes on the guest OS.

### Future
- Alert on guest fs>90% and OOM-killer events; disk quota / log rotation hygiene.

## Executive Summary

**Potential cause:** Log retention / disk fill activity on guest-os-vm-app-01 filesystem

**Impact:** Symptom `error_rate_5xx` on `orders-api` (Guest OS resource exhaustion)

**Resolution:** Free or extend filesystem space; restart the app after OOM/fs-full is cleared.; Kill or limit runaway processes on the guest OS.

## Completeness checklist

- [x] incident_summary
- [x] rca_summary
- [x] impact
- [x] service_dependencies
- [x] distributed_traces
- [x] log_patterns
- [x] metrics_analysis
- [x] recent_changes
- [x] causal_chain
- [x] contributing_factors
- [x] timeline
- [x] actions
- [x] remediation
- [x] executive_summary
- [x] localization_root
