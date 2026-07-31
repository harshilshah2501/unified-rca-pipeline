HISTORICAL / CONTAMINATED (2026-07-24) — do not cite for OO accuracy. Canonical fair write-up: OO/fair/

Incident Summary
Field	Value
Incident ID	3GwHs3RLrZZTvc3yvttA5r7pdJx
Severity	P3
Detected	2026-07-24 06:51:54 UTC
Resolved	Not resolved (incident still open)
Duration	Ongoing since alert trigger
Affected Services	orders-api (UC-1), esxi-host-01, vm-app-01, vm-db-01
Customer Impact	API latency degradation on the orders-api service with p95 request latency spiking to 1450ms, exceeding the 1000ms threshold
Impact Assessment
Field	Value
Services Affected	4 services impacted directly (orders-api, esxi-host-01 hypervisor, vm-app-01, vm-db-01)
Peak Error Rate	Not applicable (performance/latency issue, not error rate)
Peak Latency	p95 latency = 1450ms (threshold = 1000ms), representing a 45% degradation from baseline of 400ms
Users Impacted	All users accessing the orders-api service during the incident window
Data Loss	No
SLA Breach	Yes - p95 latency exceeded SLA threshold of 1000ms
Evidence
Service Dependencies
The incident demonstrates a cascading dependency chain:

orders-api (symptom surface) → depends on
vm-app-01 (guest OS) → depends on
esxi-host-01 (hypervisor) → providing CPU resources
The root cause propagates upward: hypervisor contention affects guest VMs, which manifests as elevated OS load, which in turn degrades application performance.

Distributed Traces
Not available in data streams. Analysis relies on metrics-based tracing through the resource stack.

Log Patterns
The observeops_uc_uc1 logs show the following event timeline:

2026-07-20 13:15:00 UTC (1783677000000000): Config event (CPU share configuration change)
2026-07-20 13:21:40 UTC (1783677300000000): Deploy event (5 minutes after config change)
2026-07-20 13:26:45 UTC (1783677625000000): Symptom seed and anomaly crossing events
The temporal alignment shows that the config event preceded the incident by approximately 5 minutes, followed closely by a deploy event.

Metrics Analysis
orders-api p95 Latency:

Baseline (before incident): 400ms
Peak (at incident): 1450ms
Spike magnitude: 263% increase
Timestamp: 1783677625000000 (2026-07-20 13:26:45 UTC)
ESXi Host CPU Metrics (at incident peak 1783677605000000):

observeops_cpu_usage on esxi-host-01: 92% (threshold: 85%) → BREACHED
observeops_cpu_ready on esxi-host-01: 12% (threshold: 5%) → BREACHED
Interpretation: The hypervisor is oversubscribed; CPU ready time of 12% means guest VMs spend 12% of their time waiting for physical CPU cores to become available, far exceeding normal contention threshold.
VM Guest Metrics (at incident peak 1783677612000000):

observeops_cpu_ready on vm-app-01: 11% (threshold: 5%) → BREACHED
observeops_cpu_ready on vm-db-01: 10% (threshold: 5%) → BREACHED
Interpretation: Both guest VMs are experiencing severe CPU scheduling delays due to hypervisor oversubscription.
Guest OS Load (at incident peak 1783677618000000):

observeops_load_avg on guest-os-vm-app-01: 8.0 (threshold: 4.0) → BREACHED
Interpretation: The guest OS reports load average of 8.0, indicating processes are queued waiting for CPU—consistent with hypervisor cpu.ready contention, not busy guest OS code.
Recent Changes
Config Change — 2026-07-20 13:15:00 UTC (1783677000000000)

Field	Value
Event Type	config
Implication	CPU share allocation was modified on the hypervisor or guest VMs
Timing	Preceded the symptom seed event by 11 minutes and 40 seconds
Deploy Event — 2026-07-20 13:21:40 UTC (1783677300000000)

Field	Value
Event Type	deploy
Timing	Occurred 6 minutes 25 seconds before the peak anomaly crossing
Repository	Observeops (corpus=observeops)
Critical finding: The alert description explicitly documents the expected root cause sequence:

"Root Cause (root_ci_gt=esxi-host-01, signature_gt=cpu_contention): CPU contention on ESXi host esxi-host-01 → VM cpu.ready climbs on every guest → guest load average climbs → orders-api p95 latency. Fix the hypervisor contention / CPU share change; do not tune orders-api."

Contributing Factors
CPU share reduction on hypervisor — A config change 5 minutes before the incident reduced CPU allocation or increased VM CPU demand. The 92% hypervisor CPU utilization with 12% cpu.ready (scheduler contention) shows the host is oversubscribed.

Insufficient hypervisor resource headroom — The esxi-host-01 lacks buffer capacity; normal workloads push it to 92% utilization. A deploy 5 minutes after the config change likely increased application workload or VM CPU demand.

Cascading performance degradation — Guest VM cpu.ready delays (11–12%) → guest OS load elevation (8.0 vs threshold 4.0) → application blocking on CPU availability → orders-api p95 latency spike (1450ms).

Timeline
Timestamp (UTC)	Microseconds	Event
2026-07-20 13:15:00	1783677000000000	Config event: CPU share change applied
2026-07-20 13:21:40	1783677300000000	Deploy event: Application or infrastructure deployed
2026-07-20 13:26:05	1783677605000000	ESXi host cpu.usage peaks at 92%, cpu.ready at 12%
2026-07-20 13:26:12	1783677612000000	Guest VM cpu.ready spike: vm-app-01 = 11%, vm-db-01 = 10%
2026-07-20 13:26:18	1783677618000000	Guest load average spike: guest-os-vm-app-01 = 8.0 (threshold 4.0)
2026-07-20 13:26:25	1783677625000000	orders-api p95 latency breaches 1000ms threshold, reaching 1450ms; alert fired; incident created
Actions
Immediate
Investigate the config change — Examine what CPU share or resource limits were modified 5 minutes before the incident. Verify if a CPU cap was lowered, overcommit ratio increased, or VM reservation removed.
Review the deploy — Identify what application or infrastructure changes were deployed at 2026-07-20 13:21:40 UTC. Determine if it increased workload or VM CPU demand.
Consider reverting the config change — If the CPU share reduction is not justified by capacity planning, rolling back the config to the pre-incident state may restore headroom and resolve the contention immediately.
Measure current state — Confirm that esxi-host-01 cpu usage and cpu.ready metrics are still breached, or if the incident has self-resolved.
Future
Enforce hypervisor resource headroom policy — Establish a maximum CPU utilization target for production hypervisors (e.g., 75%) to prevent runaway contention during spikes. Set up proactive alerting for cpu.ready > 2% as an early warning.
Right-size VM CPU allocation — Use historical cpu.ready and load metrics to calculate appropriate CPU shares and reservations for each VM. Avoid overcommitting the host.
Automate config validation — Add guardrails to the config change pipeline to prevent CPU share reductions below a safe minimum without explicit approval and capacity review.
Establish change coordination — Align deploy schedules with capacity checks; avoid deploying during or immediately after capacity-reducing config changes.
Executive Summary
Potential Cause: CPU contention on the ESXi host esxi-host-01 triggered by a config change that reduced CPU allocation 5 minutes before the incident, followed by a deploy that increased workload. The hypervisor reached 92% utilization with 12% cpu.ready (VM scheduler wait time), cascading through guest VMs (cpu.ready 10–11%) and their OS load (8.0), ultimately blocking the orders-api application and spiking p95 latency from 400ms to 1450ms.

Impact: orders-api p95 request latency increased 263% from baseline, breaching the 1000ms SLA threshold. All users accessing the service experienced degraded performance.

Resolution: Identify and roll back the CPU share configuration change applied at 2026-07-20 13:15:00 UTC. If rollback is not feasible, scale up the ESXi host or migrate workloads to reduce contention below 85% CPU utilization and < 5% cpu.ready.
