# Incident Analysis Report — `UC-5`

**Engine:** `federated` · **Schema:** `comprehensive_rca.v1` · **Completeness:** 15/15 (100.0%)

## RCA Summary

**Root cause:** `orders-api` (`app_resource_exhaustion`)
Orders-api resource exhaustion

**Causal path:** `orders-api`

**Customer impact:** Symptom `request.p95_latency_ms` on `orders-api` (Orders-api resource exhaustion)

**Amplifier:** classic-infra cascade (shared upstream fault → app symptom)

**False leads ruled out:** none identified

**Change evidence:** App deploy / pool-size config change on orders-api (infra below unchanged)

## Incident Summary

| Field | Value |
|-------|-------|
| Root CI | `orders-api` |
| Signature | `app_resource_exhaustion` |
| Matches pack GT | True |
| Severity | P2 |
| Detected | 2026-07-10T10:00:12Z |
| Dimension | ObserveOps classic-infra · `3_application` / `dependency_downstream` |
| Affected services | `orders-api` |
| Customer impact | Symptom `request.p95_latency_ms` on `orders-api` (Orders-api resource exhaustion) |

## Impact Assessment

- **SLA breach:** True
- **Data loss:** False
- **Fail fraction:** ≈2.8% of checkouts in the affected dimension
- **Blast / services:** `orders-api`

## Service Dependencies

**Critical path:** `vm-db-01` → `esxi-host-01` → `switch-core-01:GigE0/2`

Healthy siblings (pricing/inventory/token/fraud) are not on the failing payment path; errors escalate api-gateway ← checkout ← payment ← (DNS/RX/IRQ), with payment-provider as a decoy leaf.

## Distributed Traces

- Analyzed spans: 3
- Slow spans (>500ms): 3
- Span duration p50/max ms: 2466.7 / 2800.0

**Assessment:** Slow spans are confined to the application service with pool/queue waits — consistent with app-tier exhaustion and healthy upstream infra.

| Trace | Service | Span | Duration ms | CI / note |
|-------|---------|------|-------------|-----------|
| `uc5-t1…` | orders-api | POST /orders | 2800.0 | app_pool_exhaustion |
| `uc5-t1…` | orders-api | internal.worker | 2500.0 | orders-api |
| `uc5-t2…` | orders-api | GET /orders | 2100.0 | orders-api |

## Log Patterns

- App deploy / pool-size config change on orders-api (infra below unchanged)
- orders-api thread pool exhausted (app-tier fault; infra healthy)
- JVM heap pressure / GC thrash on orders-api
- orders-api error rate elevated — root is application resource exhaustion

- `app.error_rate` × 1
- `app.heap` × 1
- `app.thread_pool` × 1
- `config.change` × 1

## Metrics Analysis

- `orders-api` `jvm.heap.used_pct` = **96.0** (threshold 90.0) at 2026-07-10T10:00:05Z
- `orders-api` `db.conn_pool.active_ratio` = **1.0** (threshold 0.95) at 2026-07-10T10:00:05Z
- `orders-api` `request.p95_latency_ms` = **1800.0** (threshold 1000.0) at 2026-07-10T10:00:12Z
- `orders-api` `error_rate_5xx` = **0.18** (threshold 0.05) at 2026-07-10T10:00:12Z

## Recent Changes

**Root-cause change:** 2026-07-10T09:59:00Z — App deploy / pool-size config change on orders-api (infra below unchanged)
- 2026-07-10T09:59:00Z: App deploy / pool-size config change on orders-api (infra below unchanged)

## Causal Chain

**Topology path:** orders-api. Amplifier: high-cardinality request pattern.

**Narrative steps (evidence-backed):**

1. `config.change` — App deploy / pool-size config change on orders-api (infra below unchanged) (event, 2026-07-10T09:59:00Z)
2. `app.thread_pool` — orders-api thread pool exhausted (app-tier fault; infra healthy) (event, 2026-07-10T10:00:05Z)
3. `app.heap` — JVM heap pressure / GC thrash on orders-api (event, 2026-07-10T10:00:08Z)
4. `app.error_rate` — orders-api error rate elevated — root is application resource exhaustion (event, 2026-07-10T10:00:12Z)
5. `anomaly_jvm.heap.used_pct` — `orders-api` jvm.heap.used_pct=96.0 (anomaly, 2026-07-10T10:00:05Z)
6. `anomaly_db.conn_pool.active_ratio` — `orders-api` db.conn_pool.active_ratio=1.0 (anomaly, 2026-07-10T10:00:05Z)
7. `anomaly_request.p95_latency_ms` — `orders-api` request.p95_latency_ms=1800.0 (anomaly, 2026-07-10T10:00:12Z)
8. `anomaly_error_rate_5xx` — `orders-api` error_rate_5xx=0.18 (anomaly, 2026-07-10T10:00:12Z)
9. `trace_symptom_spans` — 3 spans (p50≈2466.7ms) corroborate the cascade (trace)

## Contributing Factors

- **Primary:** Orders-api resource exhaustion
- **Amplifier:** None
- **False leads:** 

## Timeline

- 2026-07-10T09:59:00Z · event — config.change: App deploy / pool-size config change on orders-api (infra below unchanged)
- 2026-07-10T10:00:05Z · event — app.thread_pool: orders-api thread pool exhausted (app-tier fault; infra healthy)
- 2026-07-10T10:00:05Z · anomaly — orders-api `jvm.heap.used_pct`=96.0
- 2026-07-10T10:00:05Z · anomaly — orders-api `db.conn_pool.active_ratio`=1.0
- 2026-07-10T10:00:08Z · event — app.heap: JVM heap pressure / GC thrash on orders-api
- 2026-07-10T10:00:12Z · event — app.error_rate: orders-api error rate elevated — root is application resource exhaustion
- 2026-07-10T10:00:12Z · anomaly — orders-api `request.p95_latency_ms`=1800.0
- 2026-07-10T10:00:12Z · anomaly — orders-api `error_rate_5xx`=0.18
- 2026-07-10T10:00:12Z · symptom_seed — Symptom seed orders-api / request.p95_latency_ms

## Remediation

Application pool/heap exhaustion with healthy upstream infra. Fix app capacity (threads, heap, connections); avoid blaming host/network/storage.

_Source: `signature_template` (replace with LLM guidance when available)_

## Actions

### Immediate
- Scale or restart the app tier; raise thread/heap/connection pool limits carefully.
- Confirm upstream infra remains healthy (do not restart hosts).

### Future
- Capacity alerts on pool saturation / GC pressure; load-test pool sizing.

## Executive Summary

**Potential cause:** App deploy / pool-size config change on orders-api (infra below unchanged)

**Impact:** Symptom `request.p95_latency_ms` on `orders-api` (Orders-api resource exhaustion)

**Resolution:** Scale or restart the app tier; raise thread/heap/connection pool limits carefully.; Confirm upstream infra remains healthy (do not restart hosts).

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
