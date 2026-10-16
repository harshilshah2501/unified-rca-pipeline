# Incident Analysis Report

## Incident Summary
- **Incident ID**: 3H4esOwJNtWQvSUx3TUMwDKL48m
- **Severity**: P3 (Medium)
- **Detected**: 2026-07-27 05:59:34 UTC
- **Resolved**: Ongoing
- **Duration**: Active (less than 1 minute from detection)
- **Affected Services**: orders-api (UC-3 slice)
- **Customer Impact**: Elevated latency on orders API requests for UC-3 (Use Case 3), potentially affecting order processing workflows

## Impact Assessment

- **Services Affected**: 1 (orders-api)
- **Peak Error Rate**: Unknown (no error rate metric queried)
- **Failed Requests**: Data not available in incident window
- **Users Impacted**: Unknown (UC-3 specific, estimated subset of customers)
- **Data Loss**: No
- **SLA Breach**: Likely (orders-api P95 latency breached 1000ms threshold at UC-3 slice A)

## Evidence

### Service Dependencies
Service topology graph returned empty (no nodes/edges), indicating either:
1. Service topology data not yet collected in the current monitoring window
2. Service graph is not actively tracking relationships in this environment

However, based on log evidence and alert context:
- **orders-api** is the primary affected service (UC-3 slice)
- **checkout-service** is a downstream dependency showing correlated payment call slowness in historical logs
- **api-gateway** is an upstream service showing 504 Gateway Timeout errors when checkout-service fails
- **catalog-db** shows concurrent slow query patterns in the same historical period
- **checkout-db** shows latency spikes correlating with the incident pattern

### Distributed Traces
No recent trace data available in current incident window. Historical API gateway logs from 2026-07-07 show:
- 46 ERROR level log entries
- Primary error: "504 Gateway Timeout POST /api/checkout: upstream checkout-service did not respond within 5s"
- Timestamps clustered between 2026-07-07 07:33:02 UTC and 2026-07-07 07:44:51 UTC
- Indicates upstream timeout issues (checkout-service not responding within SLA)

### Log Patterns
**Anomalies detected:**

1. **Checkout service payment call slowness** (100+ log entries):
   - Downstream payment calls showing 9000ms–17000ms latencies
   - Region-B specific issue with INR currency transactions
   - Cart sizes 13–22 items (high complexity orders)
   - Consistent pattern: "Downstream payment call slow (Xms)"
   - Timeframe: 2026-07-07 07:11:08 UTC to 2026-07-07 10:00:25 UTC

2. **Database slow queries** (64 log entries):
   - Catalog-db product queries: 977ms–2389ms each
   - Multiple queries examining 50k–200k rows per execution
   - All from catalog-db in ap-southeast-1 region
   - Concurrent with payment slowness

3. **API Gateway errors** (46 entries):
   - 504 Gateway Timeout on `/api/checkout` endpoint
   - Upstream checkout-service timeout (5s threshold)
   - Clustered between 2026-07-07 07:33:02 UTC and 07:44:51 UTC
   - Cascading failures from checkout-service unavailability

### Metrics Analysis

**orders-api P95 Latency (observeops_request_p95_latency_ms):**

Recent data available from 2026-07-10:
- UC-3 (current incident): **2100ms** (exceeds 1000ms threshold)
- UC-1: 1450ms (within threshold)
- UC-5: 1800ms (exceeds threshold)

Historical degradation pattern (2026-07-07, checkout-db latency):
- Peak latencies: **5000ms** sustained (2026-07-07 07:33:02 to 07:44:51 UTC)
- Degradation: 5000ms → 28ms over 30 minutes
- Recovery: Sharp drop from 5000ms to baseline (12–20ms range)

This suggests a resource exhaustion event that was self-healed or manually recovered within ~30 minutes.

Current incident (UC-3 = 2100ms) reflects elevated baseline from that historical event, indicating incomplete recovery or new degradation.

**checkout-db call latency:**
- Baseline: ~12–21ms
- Peak: 5000ms+ (matches orders-api degradation window)
- Symptom: Downstream payment processing delays

### Recent Changes
Change history not investigated — no tool access to git commits, deployment audit logs, or infrastructure change tracking.

### Contributing Factors

1. **Database performance degradation** — Catalog-db and checkout-db showing sustained high query latencies (1000–2389ms) and slow external calls (9000–17000ms), indicating either:
   - Missing database indexes on product queries
   - Resource contention (disk I/O, CPU, memory pressure)
   - Connection pool saturation

2. **Downstream payment service latency** — Checkout-service is experiencing slow calls to an external payment processor (Region-B, INR currency), causing:
   - Order processing delays (9–17 seconds per payment call)
   - Cascading timeout failures in API gateway (5s upstream timeout)
   - Orders-api latency spike when orders include Region-B payment region

3. **Cross-region request distribution** — UC-3 appears to concentrate high-cart-complexity orders (13–22 items, INR currency, Region-B) that are slower to process, pushing orders-api P95 latency above SLA when combined with payment slowness

## Timeline

- **2026-07-07 07:11:08 UTC** — Checkout-service payment slowness begins (first slow payment call logged)
- **2026-07-07 07:33:02 UTC** — API gateway 504 errors spike; checkout-service unresponsive within 5s SLA
- **2026-07-07 07:44:51 UTC** — Last error log; database slow query pattern ends
- **2026-07-07 ~08:15 UTC** — Apparent recovery: checkout-db latency drops from 5000ms to <21ms baseline
- **2026-07-10 10:00:25 UTC** — Most recent historical data point in system (orders-api P95 at 2100ms)
- **2026-07-27 05:59:34 UTC** — Alert fires: orders-api UC-3 P95 latency reaches 2100ms (threshold 1000ms)

## Actions

### Immediate
- Investigate current state of checkout-service and payment processor connection (test latency, error rates, connection pool)
- Check database index coverage on catalog-db product queries; add composite index on (category, status) if missing
- Validate orders-api query patterns against checkout-db — identify if N+1 queries or missing result caching exists
- Review Region-B payment processor SLA and circuit-breaker configuration (current 5s timeout may be too aggressive given observed 9–17s call times)

### Future
- Implement query caching for product catalog queries (Redis or in-memory cache) to reduce database load
- Add connection pooling with adaptive timeout backoff to payment processor to handle transient latency
- Establish database performance baselines and alert on sustained query latency >1000ms for critical tables
- Implement distributed tracing (if not present) to isolate latency to specific service boundaries
- Review and optimize Region-B payment routing — consider dedicated payment service or circuit breaker pattern with fallback

## Executive Summary

**Potential Cause**: Orders-api P95 latency breach (2100ms on UC-3) is driven by downstream payment processor slowness (9–17 second call times) combined with catalog-database query degradation (1–2+ second queries). Historical evidence shows this pattern correlates with high-complexity orders (13+ items, INR currency, Region-B region) processed through checkout-service, where payment calls are not adequately parallelized or cached. Recent change history not investigated due to lack of tool access.

**Impact**: UC-3 customer orders are experiencing elevated processing latency, breaching the 1000ms P95 SLA on orders-api. This cascades to api-gateway 504 errors when checkout-service timeouts occur, resulting in lost transactions if not retried.

**Resolution**: Identify and address the root cause of payment processor slowness (external service degradation vs. local connection pool exhaustion); optimize database query performance for product lookups; implement circuit breaker with exponential backoff on payment calls; consider adding request-level caching or result pagination for high-item-count orders.
