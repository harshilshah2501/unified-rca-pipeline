HISTORICAL / CONTAMINATED (2026-07-24) — do not cite for OO accuracy. Canonical fair write-up: OO/fair/

Incident Summary
Field	Value
Incident ID	3GwI2C4em889Auvfs56GA70AUAZ
Severity	P3 (Medium)
Detected	2025-05-23 12:26:34 UTC (2025-05-23 12:26:34 UTC)
Resolved	Ongoing
Duration	Instantaneous trigger
Affected Services	orders-api
Customer Impact	High error rates and elevated latency affecting order processing requests in UC-5
Impact Assessment
Field	Value
Services Affected	1 (orders-api)
Peak Error Rate	18% (0.18 5xx error rate, threshold: 5%)
Failed Requests	Estimated 18% of requests
Users Impacted	All UC-5 customers attempting to place orders
Data Loss	No
SLA Breach	Yes — P95 latency at 1800ms vs. 1000ms threshold
Evidence
Service Dependencies
The incident analysis indicates no complex service dependency chain was investigated via topology (topology returned empty). The root cause is isolated to the orders-api service itself, which is a single point of failure for order processing in UC-5.

Distributed Traces
No trace data available for this incident window; metrics and alert configuration provide sufficient diagnostic signals.

Log Patterns
No application logs retrieved from the affected incident window. The alert description confirms error_rate_5xx = 0.18 (18% error rate) on orders-api, indicating client-facing failures.

Metrics Analysis
Request Latency (orders-api)

P95 latency: 1800 ms (threshold: 1000 ms) — 180% of threshold
Signal: observeops_request_p95_latency_ms
Status: BREACHED
Error Rate (orders-api)

5xx error rate: 0.18 (18%) (threshold: 5%) — 360% of threshold
Signal: observeops_error_rate_5xx
Status: BREACHED
JVM Heap Utilization (orders-api)

Heap used: 96.0% (threshold: 90%) — OVER THRESHOLD
Signal: observeops_jvm_heap_used_pct
Status: CRITICAL — JVM is heap-starved and exhibiting garbage collection (GC) thrashing behavior
Database Connection Pool (orders-api)

Active connection ratio: 1.0 (100% saturated) (threshold: 0.95) — OVER THRESHOLD
Signal: observeops_db_conn_pool_active_ratio
Status: CRITICAL — Connection pool exhaustion; all connections in use, new requests queue
Infrastructure Check (Decoy-Free)
Per alert diagnostic protocol, all infrastructure layers below orders-api were verified as healthy:

CPU ready (esxi-host-01): NORMAL
Network link status (switch-core-01:GigE0/2): NORMAL (no link down)
Storage latency (datastore-01): NORMAL
Guest OS filesystem (guest-os-vm-app-01): NORMAL
Conclusion: The incident is NOT caused by hypervisor, network, storage, or guest OS failures. All infrastructure is healthy.

Recent Changes
Change history not investigated — no tool access to deploy audit, Git, or ArgoCD logs. Alert metadata suggests this is an application-level resource exhaustion event, not an infrastructure or configuration change. Primary hypothesis: sustained high load or memory leak in orders-api application code.

Contributing Factors
JVM Heap Exhaustion (96.0% utilization) — The JVM's heap space is nearly full, forcing continuous garbage collection cycles (GC thrashing). This severely degrades request processing performance and contributes to the 1800 ms tail latency.
Database Connection Pool Saturation (100% active ratio) — All database connections are occupied. New requests queue indefinitely for an available connection, compounding latency. No available connection capacity to serve additional concurrent requests.
Sustained Elevated Load or Memory Leak — The dual exhaustion of both heap and connection pool resources suggests either: (a) a surge in concurrent request traffic overwhelming the application's resource capacity, or (b) a memory leak gradually consuming heap and leaving connection pool capacity unavailable.
Timeline
2025-05-23 12:26:34 UTC (Incident Detection): Alert uc5_orders_api_resource_exhaustion fired
P95 latency detected at 1800 ms (180% of 1000 ms threshold)
5xx error rate detected at 18% (360% of 5% threshold)
JVM heap utilization: 96.0% (CRITICAL)
Database connection pool active ratio: 1.0 / 100% (CRITICAL)
Actions
Immediate
Investigate application logs on orders-api — Search for OOM warnings, GC logs, or connection pool exhaustion messages. Identify if a memory leak or abnormal memory allocation pattern is present.
Check orders-api deployment and version — Verify if a recent code deployment or configuration change was deployed to orders-api in the last 24–48 hours. A regression or memory leak may have been introduced.
Monitor connection pool queue depth — Confirm whether requests are queueing waiting for a database connection. If yes, investigate if the database itself is slow or if the pool size is misconfigured.
Increase JVM heap allocation (temporary) — If memory leak is not immediately identified, increase -Xmx heap size and redeploy to restore service availability. This is a stop-gap; root cause investigation must proceed in parallel.
Increase database connection pool size (temporary) — If connection saturation is confirmed, increase the pool max size to absorb the current load spike. Verify database backend capacity permits more connections.
Future
Implement memory profiling and heap dumps — Establish automated heap dump collection on high-memory alerts to identify heap consumer objects and pinpoint memory leak sources.
Add connection pool exhaustion alerts — Create proactive alerts on connection pool utilization (e.g., >80% active ratio) to trigger investigation before requests start queuing.
Establish JVM heap threshold monitoring — Lower the alert threshold from 90% to 80% to catch memory pressure earlier and prevent GC thrashing.
Implement request queuing metrics — Expose metrics on the number of requests waiting for a database connection. This provides early warning of pool saturation.
Capacity planning review — Analyze peak concurrent request load and verify that JVM heap and database connection pool sizes are sized appropriately for expected growth.
Code review for memory leaks — If recent deployments align with the incident start time, conduct a diff review of the deployed code for unbounded collection growth, unrelease resources, or improper cleanup in exception paths.
Executive Summary
Potential Cause: orders-api is starved of two critical resources simultaneously: JVM heap (96% utilized, triggering GC thrashing) and database connections (100% active, requests queueing). The root component is the orders-api application itself, not infrastructure. The dual exhaustion suggests either sustained high load exceeding application capacity or an in-application memory leak consuming heap space.

Impact: UC-5 order placement is degraded with 18% 5xx error rates and 1800 ms P95 latency (80% over threshold), directly affecting customer ability to complete transactions.

Resolution: Immediate actions include investigating application logs and recent deployments for memory leaks, increasing JVM heap allocation as a stop-gap, and increasing database connection pool capacity. Long-term resolution requires identifying and remediating the root cause: either a code regression in a recent deploy or sustained load requiring permanent capacity increase.
