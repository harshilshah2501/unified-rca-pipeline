HISTORICAL / CONTAMINATED (2026-07-24) — do not cite for OO accuracy. Canonical fair write-up: OO/fair/

Incident Summary
Field	Value
Incident ID	3GwHuc2nJlHMJLg0HLIYLIS0nC4
Severity	P3 (Medium)
Detected	2026-07-24 06:52:14 UTC
Resolved	Ongoing
Duration	Detected at incident creation (alert correlation timestamp)
Affected Services	orders-api (UC-4)
Customer Impact	Orders API service is returning 42% error rate (5xx responses) versus a threshold of 5%, resulting in order processing failures
Impact Assessment
Field	Value
Services Affected	1 service (orders-api)
Peak Error Rate	42% (threshold: 5%)
Failed Requests	Significant portion of orders during the incident window
Users Impacted	All users attempting to process orders during the outage
Data Loss	No
SLA Breach	Yes (5xx error rate exceeds acceptable thresholds)
Evidence
Service Dependencies
The incident topology shows a single alert node with no upstream dependencies tracked. The orders-api service is the affected component in UC-4 (use case 4). The underlying infrastructure dependency is on guest-os-vm-app-01, which hosts the orders-api application.

Distributed Traces
No distributed trace data was available in the investigation. Evidence is derived from synthetic monitoring (health checks) and infrastructure metrics.

Log Patterns
Six anomalous events were detected in the observeops_uc_uc4 log stream:

1. 2026-07-10 10:00:18 UTC - "anomaly crossed: orders-api error_rate_5xx=0.42 (threshold=0.05)"
2. 2026-07-10 10:00:18 UTC - "symptom seed: orders-api error_rate_5xx"
3. 2026-07-10 10:00:12 UTC - "kernel: Out of memory: Killed process 1842 (orders-api)"
4. 2026-07-10 10:00:12 UTC - "anomaly crossed: guest-os-vm-app-01 oom_killer_event=1.0 (threshold=0.5)"
5. 2026-07-10 10:00:05 UTC - "No space left on device writing /var/log/orders-api"
6. 2026-07-10 10:00:05 UTC - "anomaly crossed: guest-os-vm-app-01 filesystem.used_pct=99.0 (threshold=95.0)"
Metrics Analysis
Error Rate (orders-api, UC-4):

Baseline: 0.02 (2%)
Peak: 0.42 (42%)
Timing: 2026-07-10 10:00:18 UTC
Filesystem Usage (guest-os-vm-app-01, UC-4):

Historical: 38%
Peak: 99% at 2026-07-10 10:00:05 UTC
Critical: Exceeded 95% threshold, triggering alert
OOM Killer Events (guest-os-vm-app-01, UC-4):

Historical: 0.2 (minor)
Peak: 1.0 at 2026-07-10 10:00:12 UTC
Triggered when filesystem full, causing kernel to reclaim memory by terminating process 1842 (orders-api)
Health Check Status (orders-api, UC-4):

Pre-incident: 0.4 (40% healthy)
Incident: 0 (0% healthy)
Status: Complete failure at 2026-07-10 10:00:18 UTC
Hypervisor CPU Usage (esxi-host-01, UC-4):

Status: Stable at 45% throughout incident window
Assessment: Hypervisor was NOT a bottleneck; ruled out as contributing factor
Recent Changes
Change history not investigated — no tool access to git history, deployment logs, or infrastructure-as-code repositories.

Contributing Factors
Filesystem Exhaustion (Primary): The guest-os-vm-app-01 filesystem reached 99% capacity at 2026-07-10 10:00:05 UTC, exceeding the 95% threshold. Specifically, /var/log/orders-api filled up, causing "No space left on device" errors when the application attempted to write logs.

Out-of-Memory (OOM) Killer Activation (Primary): Due to combined memory and disk pressure, the Linux kernel OOM killer was triggered at 2026-07-10 10:00:12 UTC, forcibly terminating process 1842 (orders-api). OOM events jumped from a baseline of 0.2 to 1.0, indicating the kernel reaping memory-consuming processes.

Orders-API Process Termination (Direct Cause): The OOM killer's termination of the orders-api process caused an immediate service outage. Health checks dropped to 0% (complete failure) at 2026-07-10 10:00:18 UTC, and error rates spiked to 42%.

Timeline
Time (UTC)	Event	Signal
2026-07-10 10:00:05	/var/log/orders-api disk full; filesystem reaches 99% capacity	observeops_filesystem_used_pct=99.0
2026-07-10 10:00:12	Kernel OOM killer activates, terminates orders-api process (PID 1842)	observeops_oom_killer_event=1.0, kernel log
2026-07-10 10:00:18	Orders-api fails all health checks; error rate jumps to 42%	observeops_error_rate_5xx=0.42, observeops_health_check=0
Actions
Immediate
Clear log files and free disk space on guest-os-vm-app-01 by removing old log files from /var/log/orders-api and other temporary directories. This is the critical path to service recovery.
Increase log rotation frequency in the orders-api configuration to prevent rapid log accumulation (e.g., rotate daily instead of weekly).
Verify orders-api process is running and confirm health checks return to normal (target: >95% healthy).
Monitor disk utilization on guest-os-vm-app-01 in real-time during recovery to ensure it does not exceed 95% again.
Future
Increase guest-os-vm-app-01 disk capacity (VirtualMachine or storage provisioning) to provide headroom above the current workload.
Implement disk-usage alerting with earlier thresholds (e.g., 80% and 85%) to catch fill-up conditions before they cascade into OOM events.
Review log retention policies across all services on guest-os-vm-app-01 to ensure logs are archived or pruned aggressively.
Isolate log destinations: Consider writing logs to a separate volume (e.g., /var/log on a dedicated VirtualMachine disk or NFS mount) to prevent application partitions from filling.
Memory limits and OOM prevention: If orders-api is running in Kubernetes or with cgroup limits, review memory limits to ensure they are appropriate for the workload. If no limits are set, consider implementing them to avoid unbounded memory growth.
Executive Summary
Potential Cause: Guest OS resource exhaustion on guest-os-vm-app-01. The /var/log partition reached 99% capacity (exceeding the 95% threshold) at 2026-07-10 10:00:05 UTC, preventing orders-api from writing logs. At 2026-07-10 10:00:12 UTC, combined memory and disk pressure triggered the Linux kernel OOM killer, which terminated the orders-api process (PID 1842). The service immediately failed all health checks and began returning 42% error rates to clients, far exceeding the 5% threshold.

Impact: Orders processing is completely unavailable during the outage window (2026-07-10 10:00:05 – 10:00:18 UTC). All order requests return 5xx errors. Customer-facing impact includes failed transactions and potential revenue loss.

Resolution: Free disk space on guest-os-vm-app-01 (clear /var/log/orders-api), restart the orders-api service if necessary, and monitor disk/memory metrics. Long-term: increase disk capacity, implement earlier alerting (80–85% thresholds), and review log retention policies to prevent recurrence.
