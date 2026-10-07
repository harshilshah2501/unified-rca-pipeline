# ObserveOps Use Cases — Initial List (v1)

Initial set, extensible later.

1. **Error rate increase on a service** — A service's error/failure rate (5xx, exceptions, failed requests) rises above its normal baseline. Seen across: Datadog, Dynatrace, Edge Delta.

2. **Response time / latency slowdown** — A service's response time (p95/p99 latency) degrades beyond its normal baseline. Seen across: Datadog, Dynatrace, Edge Delta.

3. **Resource contention (CPU / memory / disk)** — Host or process-level compute resources become saturated, degrading dependent workloads (includes noisy-neighbor patterns). Seen across: Datadog, Dynatrace, Edge Delta.

4. **Availability — service or host down** — A service, process, or host becomes unreachable or unresponsive, typically cascading to dependent callers. Seen across: Datadog, Dynatrace, Edge Delta.

5. **Monitoring / telemetry pipeline unavailable** — The observability pipeline stops receiving telemetry from an entity while the entity itself may still be running (an "are we blind?" signal, distinct from the entity actually being down). Seen across: Dynatrace, Edge Delta.

6. **Disk latency high on host** — Disk I/O latency on a host rises above its normal baseline, indicating a storage bottleneck. Seen across: Datadog, Dynatrace, Edge Delta.

7. **Disk storage / usage increase** — Disk space usage on a host climbs toward capacity exhaustion. Seen across: Datadog, Dynatrace, Edge Delta.

8. **Network traffic sent/received high on host** — Inbound or outbound network throughput on a host exceeds its normal baseline. Seen across: Datadog, Dynatrace, Edge Delta.
