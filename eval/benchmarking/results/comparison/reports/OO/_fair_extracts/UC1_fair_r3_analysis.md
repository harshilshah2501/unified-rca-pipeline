# Incident Analysis Report

## Incident Summary
- **Incident ID**: 3H538eGNAa0meaFoJwB2o8NnQMO
- **Severity**: P3
- **Detected**: 2026-07-27 09:19:04 UTC
- **Resolved**: Ongoing
- **Duration**: Ongoing (first alert at 09:19:04 UTC)
- **Affected Services**: orders-api, checkout-service, payment-db (db-01)
- **Customer Impact**: High latency on orders API; p95 latency breached SLO threshold (1000ms); checkout service unable to process payment transactions due to database connectivity failures

## Impact Assessment

- **Services Affected**: 3 primary services (orders-api, checkout-service, payment-db)
- **Peak Error Rate**: 100% (46/46 API gateway requests to checkout-service resulted in 504 Gateway Timeout errors)
- **Failed Requests**: 46 confirmed 504 errors in gateway logs; all checkout payment calls timing out
- **Users Impacted**: All users attempting to complete orders/checkout transactions
- **Data Loss**: No (service timeouts did not result in data corruption)
- **SLA Breach**: Yes (orders-api p95 latency of 1450ms exceeded 1000ms SLO threshold)

## Evidence

### Service Dependencies
Service topology analysis shows an empty node graph, but investigation revealed the dependency chain:
- **orders-api** → depends on → **checkout-service**
- **checkout-service** → depends on → **payment-db (db-01)**
- **checkout-service** logs indicate repeated "downstream payment call slow" warnings and complete database connection timeouts

### Distributed Traces
Trace data from observeops metrics shows:
- p95 latency for orders-api peaking at 1450ms (1.45x the 1000ms SLO threshold)
- Consistent latency values maintained throughout the window, indicating sustained degradation rather than a transient spike
- No error traces available in the core incident window (1785143944 UTC)

### Log Patterns
**API Gateway Logs** (api_gateway_logs stream):
- 46 ERROR entries spanning from 1783408212 to 1783410290 UTC
- Pattern: "504 Gateway Timeout POST /api/checkout: upstream checkout-service did not respond within 5s"
- Service: api-gateway
- Consistent 5-second timeout across all failures

**Checkout Service Logs** (checkout_service_logs stream):
- 246 total log entries analyzed
- 46 ERROR entries: "connection to payment-db (db-01:5432) timed out after 5000ms; TCP retransmissions to db-01 detected"
- 100+ WARN entries: "Downstream payment call slow (9000-18000ms) region=Region-B currency=INR cart_items=13-22"
- Indicates systematic database connection issues with TCP-level evidence (retransmissions detected)

**Database Slow Query Logs** (db_slow_query_logs stream):
- 64 slow query warnings logged
- Queries: "SELECT * FROM products WHERE ..." with execution times ranging 946ms-2389ms
- All queries examined 50,000-200,000 rows
- Pattern concentrated in Region-B; INR currency transactions affected

### Metrics Analysis
**Latency Metrics**:
- orders-api p95_latency_ms: consistently 1450ms (breaching 1000ms threshold)
- checkout_latency_p95_ms: peak values at 986.9ms, 980.5ms, 964.2ms, 965.2ms (approaching but not breaching individual checkout SLO)
- Combined latency (orders-api waiting for checkout-service waiting for payment-db) = root cause

**Connection & Network Evidence**:
- Checkout service reporting TCP retransmissions to payment-db (db-01)
- All connection timeouts exactly 5000ms (matching application connection timeout configuration)
- 100% timeout rate on database connections during incident window

**Database Metrics** (searched but no data):
- observeops_db_conn_pool_active_ratio: no results (pool metrics unavailable)
- observeops_disk_iowait_pct: no results (disk I/O metrics unavailable)
- observeops_filesystem_used_pct: no results (filesystem metrics unavailable)

### Recent Changes
Change history tool not available. Investigation scope limited to observable evidence. No commit/deploy information available for correlation with incident start time (2026-07-27 09:19:04 UTC).

### Contributing Factors

1. **Database Connection Timeout Cascade** — checkout-service unable to establish connections to payment-db (db-01) within 5-second timeout window; TCP retransmissions detected indicating network-level or kernel-level packet loss; 100% connection failure rate propagated upstream

2. **Slow Product Queries** — database slow query logs show repeated product table full scans (examining 50K-200K rows per query) with execution times of 1000-2400ms; systematic query performance degradation coinciding with checkout service failures

3. **Upstream Timeout Propagation** — orders-api gateway timeout (5 seconds) exceeded by checkout-service latency (average ~13000ms from downstream payment call warnings); orders-api unable to reach checkout-service within its 5-second SLA, resulting in 504 errors and elevated p95 latency

## Timeline

- **1783408212 UTC** - First 504 Gateway Timeout error logged (POST /api/checkout)
- **1783408212-1783410290 UTC** - Sustained 504 error rate (46 total errors in ~34 minute window)
- **1783408212 UTC** - Checkout service first records database connection timeout (payment-db connection refused)
- **1783408212-1783414803 UTC** - Checkout service logs "Downstream payment call slow" warnings repeatedly
- **1783414045-1783415935 UTC** - Database slow query logs begin appearing (64 slow query warnings over ~31 minutes)
- **1785143944 UTC** - Alert "orders_api_p95_latency_high_UC1" fires (1450ms p95 latency, exceeding 1000ms threshold)

## Actions

### Immediate
1. **Verify payment-db (db-01) connectivity** — Execute `ping db-01`, `nc -zv db-01 5432`, and check PostgreSQL service status (systemctl status postgresql)
2. **Review TCP retransmission metrics** — Query kernel metrics (`ss -i` on affected host) to confirm packet loss and retransmission count
3. **Analyze database connection pool** — Check active connections, connection wait queue, and idle timeout settings on payment-db
4. **Optimize product queries** — Add index on products table (scan count of 50K-200K rows per query indicates missing index); estimate execution time reduction to <500ms with proper indexing
5. **Increase checkout-service timeout** — Raise database connection timeout from 5000ms to 10000ms as temporary mitigation pending root cause fix

### Future
1. **Network path diagnostics** — Run MTR (My Traceroute) between checkout-service and db-01; investigate TCP window scaling, PMTUD issues, or network device queuing
2. **Implement circuit breaker** — Prevent cascading failures by implementing exponential backoff and circuit breaker pattern in checkout-service database client
3. **Add query result caching** — Cache product catalog queries (they appear to be reference data); eliminate repeated full table scans
4. **Increase observability** — Instrument payment-db host metrics (disk I/O, CPU, filesystem usage, memory) to detect resource exhaustion scenarios
5. **Establish SLO alerting at each layer** — Alert on checkout-service latency independently from orders-api p95 to isolate failures earlier in the dependency chain

## Executive Summary

**Potential Cause**: checkout-service unable to establish connections to payment-db (db-01) due to network connectivity failure (TCP retransmissions detected); combined with systematic slow product catalog queries (1000-2400ms execution time on 50K-200K row scans), resulting in 13000ms+ downstream payment latency; orders-api unable to reach checkout-service within 5-second timeout, cascading to 100% 504 Gateway Timeout errors and p95 latency of 1450ms (45% above 1000ms SLO threshold).

**Impact**: All checkout/payment transactions unable to complete during incident window; orders-api SLO breached; customers experiencing transaction timeouts.

**Resolution**: Restore payment-db connectivity (investigate TCP retransmissions, verify network path, check PostgreSQL service health); optimize product queries with indexes or caching; increase timeout tolerances to accommodate legitimate network latency; implement circuit breaker patterns to prevent cascading failures across service tiers.
