# Incident Analysis Report — OpenObserve · `UC-3`

**Engine:** openobserve (fair Slice A portal Analysis)  
**Portal incident:** `3H541z1bJNXfExUagp4l5AyAdGg`  
**Pack GT:** `datastore-01` / `storage_contention`  
**OO match to pack GT:** No  
**OO claimed root:** unidentified shared downstream bottleneck (UC-1/3/5 co-spike)  
**Generated:** 2026-07-28T10:32:11Z  

## Executive Summary (from portal)

**Potential Cause:** P95 latency for orders-api (UC-3) surged from 400 ms to 2100 ms at 2026-07-27 09:23:51 UTC, with simultaneous spikes in UC-1 and UC-5, indicating a shared downstream bottleneck. The specific bottleneck cannot be identified without access to database latency metrics, cache health, error rates, distributed traces, or change history.

**Impact:** Customers querying the orders API during 09:23:51–09:26:24 UTC experienced elevated latency (2.1–4.2x normal), breaching the 1000 ms SLA threshold for UC-3.

**Resolution:** Immediate investigation should focus on verifying the spike has resolved, checking for recent deployments/config changes, and querying database/cache health. Long-term resolution requires enabling distributed tracing, centralizing logs, and implementing composite alerting to correlate latency with errors and resource metrics.

---

## Portal Analysis (verbatim fair extract)

# Incident Analysis Report

## Incident Summary
- **Incident ID**: 3H541z1bJNXfExUagp4l5AyAdGg
- **Severity**: P3 (Medium)
- **Detected**: 2026-07-27 09:26:24 UTC
- **Resolved**: Ongoing
- **Duration**: First alert at 09:23:51 UTC, last alert at 09:23:51 UTC
- **Affected Services**: orders-api
- **Customer Impact**: Elevated API response latency on UC-3 (orders-api use case), breaching SLA threshold

## Impact Assessment

- **Services Affected**: 1 (orders-api)
- **Peak P95 Latency**: 2100 ms (threshold: 1000 ms)
- **Latency Increase**: 5.25x baseline (from ~400 ms to 2100 ms)
- **Use Cases Impacted**: UC-3 (orders-api), UC-5, UC-1
- **Users Impacted**: Unknown (dependent on traffic during incident window)
- **Data Loss**: No
- **SLA Breach**: Yes (threshold breach 2026-07-27 09:23:51 UTC)

## Evidence

### Service Dependencies
Service topology returned no nodes or edges, indicating either:
- Trace data collection not yet available for service graph construction
- Service instrumentation not configured
- Traces stream not populated during incident window

The alert metadata references only "orders-api" with no upstream/downstream dependencies documented in the system.

### Distributed Traces
No trace data available in the traces stream for the time window 2026-07-27 08:56:24 UTC to 2026-07-27 09:26:24 UTC. Trace instrumentation may not be enabled for orders-api or the traces stream may not contain data from this service.

### Log Patterns
Log searches across api_gateway_logs and app_logs streams returned zero hits during the incident window. These streams contain stale data:
- api_gateway_logs: last data point 2026-07-14 01:04:50 UTC (13+ days old)
- app_logs: last data point 2026-07-14 00:58:21 UTC (13+ days old)

No contemporary log data available to correlate with latency spike.

### Metrics Analysis

**P95 Latency Timeline (observeops_request_p95_latency_ms stream):**

| Timestamp UTC | UC-3 P95 (ms) | UC-1 P95 (ms) | UC-5 P95 (ms) | Status |
|---|---|---|---|---|
| 2026-07-27 09:16:46 | 400 | 400 | 400 | Baseline |
| 2026-07-27 09:20:06 | 400 | 400 | 400 | Baseline |
| 2026-07-27 09:23:51 | **2100** | 1450 | 1800 | **SPIKE** |

**Key Observations:**
- Latency remained stable at ~400 ms baseline across all use cases until 09:23:51 UTC
- At 09:23:51 UTC, a sharp latency spike occurred:
  - UC-3: 400 → 2100 ms (+425%)
  - UC-1: 400 → 1450 ms (+262.5%)
  - UC-5: 400 → 1800 ms (+350%)
- All three use cases affected simultaneously, suggesting common downstream dependency
- No error rate or throughput metrics available to correlate
- No CPU/memory/disk metrics available from Prometheus

### Recent Changes
**Change history not investigated** — no tools available to query deploy audit logs, Git commit history, configuration change history, or Helm/Terraform modifications. The incident timestamp of 09:23:51 UTC aligns with a potential deployment or configuration change, but without access to change history, this remains speculative.

### Contributing Factors
1. **Simultaneous latency spike across all use cases** — Suggests a common bottleneck in shared infrastructure (database, cache, load balancer, or backing service dependency) rather than orders-api application logic alone
2. **Sustained elevated latency** — Latency remained elevated (2100 ms for UC-3) at the time of alert generation, indicating the condition was not transient
3. **Lack of correlated signals** — No error logs, no error-rate spike, no trace data, no resource-exhaustion metrics available to isolate the failure point
4. **Data collection gaps** — Missing trace instrumentation, stale log streams, and absence of resource metrics limit RCA depth

## Timeline

- **2026-07-27 09:16:46 UTC** - Baseline latency: 400 ms across UC-1, UC-3, UC-5
- **2026-07-27 09:20:06 UTC** - Baseline latency maintained: 400 ms across all use cases
- **2026-07-27 09:23:51 UTC** - **Latency spike detected**: UC-3 P95 jumps to 2100 ms; UC-1 to 1450 ms; UC-5 to 1800 ms
- **2026-07-27 09:26:24 UTC** - **Alert fires**: `orders_api_p95_latency_high_UC3` (alert threshold: value > 1000 ms)

## Actions

### Immediate
1. **Verify current latency state** — Re-run P95 latency query for UC-3 post-09:26:24 UTC to determine if spike has resolved or persists
2. **Check orders-api deployment status** — Confirm no recent deployments/rollovers occurred between 09:15-09:25 UTC
3. **Query database/cache health** — Since all use cases spiked simultaneously, check database query latency, connection pool saturation, and cache hit rates
4. **Inspect load balancer/reverse proxy logs** — Check for request queuing, connection drops, or upstream timeouts
5. **Enable trace instrumentation** — Populate traces stream with orders-api transaction data to identify which downstream service(s) injected latency

### Future
1. **Establish baseline SLOs per use case** — Current 1000 ms threshold may not align with customer expectations; validate with SLA definition
2. **Implement composite alerting** — Create alerts that correlate latency spike with error rate and resource utilization (CPU, memory, disk I/O) to reduce alert volume and improve signal-to-noise ratio
3. **Enable comprehensive logging** — Modernize and centralize logs from orders-api, database, and cache layers; retire stale log streams
4. **Instrument distributed traces** — Ensure all services in the orders path (API gateway → orders-api → database/cache → payment/shipping services) emit spans for end-to-end latency breakdown
5. **Implement change detection** — Correlate incident timestamps with Git commits, deploy records, and infrastructure changes to accelerate RCA

## Executive Summary

**Potential Cause**: P95 latency for orders-api (UC-3) surged from 400 ms to 2100 ms at 2026-07-27 09:23:51 UTC, with simultaneous spikes in UC-1 and UC-5, indicating a shared downstream bottleneck. The specific bottleneck cannot be identified without access to database latency metrics, cache health, error rates, distributed traces, or change history. The spike aligns with a potential deployment or configuration change, but this cannot be confirmed without change-history tooling.

**Impact**: Customers querying the orders API during 09:23:51–09:26:24 UTC experienced elevated latency (2.1–4.2x normal), breaching the 1000 ms SLA threshold for UC-3.

**Resolution**: Immediate investigation should focus on verifying the spike has resolved, checking for recent deployments/config changes, and querying database/cache health. Long-term resolution requires enabling distributed tracing, centralizing logs, and implementing composite alerting to correlate latency with errors and resource metrics.
