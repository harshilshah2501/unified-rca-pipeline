# Incident Analysis Report — OpenObserve · `UC-5`

**Engine:** openobserve (fair Slice A portal Analysis)  
**Portal incident:** `3H540hUYTQLWbBGwKuuJ52GTz2W`  
**Pack GT:** `orders-api` / `app_resource_exhaustion`  
**OO match to pack GT:** Yes  
**OO claimed root:** orders-api (DB connection pool saturation + JVM heap pressure)  
**Generated:** 2026-07-28T10:32:11Z  

## Executive Summary (from portal)

**Potential Cause:** Database connection pool saturation (100% active ratio) combined with JVM heap memory pressure (96% utilization) caused cascading resource exhaustion in orders-api. The saturated connection pool created request queueing, directly resulting in the observed p95 latency increase to 1800ms and 18% error rate.

**Impact:** All orders-api requests during UC-5 scenario experienced significant latency (1800ms vs 1000ms threshold) and an 18% failure rate, breaking SLA commitments.

**Resolution:** Immediate investigation into connection pool configuration and database health required; short-term fix is service restart to flush the pool and memory state. Long-term remediation includes pool sizing analysis, memory optimization, and earlier detection through 70-80% utilization alerts.

---

## Portal Analysis (verbatim fair extract)

# Incident Analysis Report

## Incident Summary
- **Incident ID**: 3H540hUYTQLWbBGwKuuJ52GTz2W
- **Severity**: P3 (Medium)
- **Detected**: 2026-07-27 09:26:14 UTC
- **Resolved**: Ongoing
- **Duration**: ~2 minutes (continuing)
- **Affected Services**: orders-api
- **Customer Impact**: Request latency increased to 1800ms (80% above threshold), 18% error rate in 5xx responses

## Impact Assessment

- **Services Affected**: 1 (orders-api)
- **Peak Error Rate**: 18% (5xx errors, threshold 5%)
- **Failed Requests**: 18% of requests during the incident window
- **Users Impacted**: All users accessing orders functionality in UC-5 slice
- **Data Loss**: No
- **SLA Breach**: Yes (p95 latency breach at 1800ms vs 1000ms threshold)

## Evidence

### Service Dependencies
Limited topological data available. orders-api identified as the primary affected component. No upstream/downstream service correlation data retrieved from topology service.

### Distributed Traces
No trace data available in the default or ecom_traces streams for orders-api during the incident window. Trace correlation not possible.

### Log Patterns
Observeops monitoring revealed cascading resource and performance anomalies:

**Anomalies Detected (in chronological order):**
1. JVM heap memory pressure: 96% utilization (threshold: 90%)
2. Database connection pool saturation: 100% active ratio (threshold: 95%)
3. Request latency degradation: p95 latency jumped to 1800ms (threshold: 1000ms)
4. Error rate spike: 18% 5xx error rate (threshold: 5%)

**Key Error Message:**
- "symptom seed: orders-api request.p95_latency_ms" — indicates symptom detection at the application layer

### Metrics Analysis
From observeops_uc_uc5 logs during UC-5 scenario execution:

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| jvm.heap.used_pct | 96% | 90% | BREACHED |
| db.conn_pool.active_ratio | 1.0 (100%) | 0.95 (95%) | BREACHED |
| request.p95_latency_ms | 1800ms | 1000ms | BREACHED |
| error_rate_5xx | 18% | 5% | BREACHED |

The sequence indicates resource exhaustion cascading to application impact: JVM memory and database connection pool saturation preceded the latency spike by 7 seconds.

### Recent Changes
Change history not investigated — no tool access to deployment or configuration change auditing systems. Alert configuration indicates this is UC-5 (Slice A fair) monitoring scenario with fair_push enabled.

### Contributing Factors
1. **Database connection pool exhaustion** — active ratio reached 100%, suggesting all available connections were in use and the pool could not service new requests. This is the immediate bottleneck for the latency increase.
2. **JVM heap memory pressure** — 96% utilization indicates the application was under memory stress, potentially causing GC pressure or memory allocation delays that compound connection wait times.
3. **Request queue buildup** — with the connection pool saturated, incoming requests must wait in queue, directly explaining the 1800ms p95 latency (80% increase from the 1000ms threshold).

## Timeline

- **09:23:44 UTC** — JVM heap memory reaches 96% utilization (anomaly crossed; threshold 90%)
- **09:23:44 UTC** — Database connection pool reaches 100% active ratio (anomaly crossed; threshold 95%)
- **09:23:51 UTC** — Request p95 latency spikes to 1800ms (anomaly crossed; threshold 1000ms)
- **09:23:51 UTC** — Error rate jumps to 18% 5xx responses (anomaly crossed; threshold 5%)
- **09:23:51 UTC** — Symptom seed triggered for orders-api request.p95_latency_ms
- **09:26:14 UTC** — Incident created and correlated alert fired

## Actions

### Immediate
- **Identify the root cause of connection pool exhaustion** — Check database connection configuration (pool size, max wait time) and current active connection count to confirm saturation.
- **Monitor memory pressure** — Check if GC pauses are contributing to latency. Review heap dump or GC logs to identify if there is a memory leak or excessive object allocation.
- **Check database health** — Verify database server is responsive and not experiencing lock contention, slow queries, or resource exhaustion.
- **Implement connection pool recovery** — Consider graceful draining and restart of the orders-api service to reset the connection pool and memory state.

### Future
- **Increase connection pool size** — If the current pool is undersized for peak load in UC-5 scenario, increase the pool max size to handle burst traffic.
- **Implement circuit breaker** — Add circuit breaker pattern to fail fast and reduce queue buildup when the connection pool approaches saturation.
- **JVM memory tuning** — Review heap size allocation and GC tuning parameters. If heap is consistently near 90%+, increase max heap size or optimize memory consumption.
- **Add connection pool monitoring alerts** — Create proactive alerts for connection pool utilization at 70% and 80% thresholds to catch saturation earlier.
- **Database query optimization** — Analyze slow queries to reduce connection hold time, allowing the pool to service more requests concurrently.

## Executive Summary

**Potential Cause**: Database connection pool saturation (100% active ratio) combined with JVM heap memory pressure (96% utilization) caused cascading resource exhaustion in orders-api. The saturated connection pool created request queueing, directly resulting in the observed p95 latency increase to 1800ms and 18% error rate.

**Impact**: All orders-api requests during UC-5 scenario experienced significant latency (1800ms vs 1000ms threshold) and an 18% failure rate, breaking SLA commitments.

**Resolution**: Immediate investigation into connection pool configuration and database health required; short-term fix is service restart to flush the pool and memory state. Long-term remediation includes pool sizing analysis, memory optimization, and earlier detection through 70-80% utilization alerts.
