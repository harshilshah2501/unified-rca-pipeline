# Incident Analysis Report — `UC-1`

**Engine:** `federated` · **Schema:** `comprehensive_rca.v1` · **Completeness:** 15/15 (100.0%)

## RCA Summary

**Root cause:** `esxi-host-01` (`cpu_contention`)
CPU contention on ESXi host

**Causal path:** `esxi-host-01` → `vm-app-01` → `guest-os-vm-app-01` → `orders-api`

**Customer impact:** Symptom `request.p95_latency_ms` on `orders-api` (CPU contention on ESXi host)

**Amplifier:** classic-infra cascade (shared upstream fault → app symptom)

**False leads ruled out:** none identified

**Change evidence:** DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01

## Incident Summary

| Field | Value |
|-------|-------|
| Root CI | `esxi-host-01` |
| Signature | `cpu_contention` |
| Matches pack GT | True |
| Severity | P2 |
| Detected | 2026-07-10T10:00:25Z |
| Dimension | ObserveOps classic-infra · `2_infra` / `resource_contention` |
| Affected services | `orders-api` |
| Customer impact | Symptom `request.p95_latency_ms` on `orders-api` (CPU contention on ESXi host) |

## Impact Assessment

- **SLA breach:** True
- **Data loss:** False
- **Fail fraction:** ≈2.8% of checkouts in the affected dimension
- **Blast / services:** `vm-app-01`, `vm-db-01`, `guest-os-vm-app-01`, `orders-api`

## Service Dependencies

**Critical path:** `esxi-host-01` → `switch-core-01:GigE0/2`

Healthy siblings (pricing/inventory/token/fraud) are not on the failing payment path; errors escalate api-gateway ← checkout ← payment ← (DNS/RX/IRQ), with payment-provider as a decoy leaf.

## Distributed Traces

- Analyzed spans: 4
- Slow spans (>500ms): 4
- Span duration p50/max ms: 1100.0 / 1480.0

**Assessment:** Trace samples include infra/root-layer spans that corroborate the localized root CI; app spans show elevated latency as a downstream symptom.

| Trace | Service | Span | Duration ms | CI / note |
|-------|---------|------|-------------|-----------|
| `uc1-t1…` | orders-api | POST /orders | 1480.0 | orders-api |
| `uc1-t2…` | orders-api | GET /orders/{id} | 1320.0 | orders-api |
| `uc1-t1…` | guest-os-vm-app-01 | os.sched.wait | 900.0 | guest-os-vm-app-01 |
| `uc1-t1…` | esxi-host-01 | hypervisor.cpu.ready | 700.0 | root_evidence |

## Log Patterns

- DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01
- ESXi cpu.ready elevated on esxi-host-01 (12% > 5% threshold)
- ESXi cpu.usage 92% sustained on esxi-host-01
- VM cpu.ready 11% on vm-app-01 (host scheduler starvation)
- load average 8.0 on guest-os-vm-app-01 (run-queue backlog)
- orders-api p95 latency 1450ms (SLO threshold 1000ms)

- `app.latency` × 1
- `esx.cpu.ready` × 1
- `esx.cpu.usage` × 1
- `infra.change` × 1
- `syslog.loadavg` × 1
- `vmware.cpu.ready` × 1

## Metrics Analysis

- `esxi-host-01` `cpu.usage` = **92.0** (threshold 85.0) at 2026-07-10T10:00:05Z
- `esxi-host-01` `cpu.ready` = **12.0** (threshold 5.0) at 2026-07-10T10:00:05Z
- `vm-app-01` `cpu.ready` = **11.0** (threshold 5.0) at 2026-07-10T10:00:12Z
- `vm-db-01` `cpu.ready` = **10.0** (threshold 5.0) at 2026-07-10T10:00:12Z
- `guest-os-vm-app-01` `load.avg` = **8.0** (threshold 4.0) at 2026-07-10T10:00:18Z
- `orders-api` `request.p95_latency_ms` = **1450.0** (threshold 1000.0) at 2026-07-10T10:00:25Z

## Recent Changes

**Root-cause change:** 2026-07-10T09:55:00Z — DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01
- 2026-07-10T09:55:00Z: DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01
- 2026-07-10T09:50:00Z: CPU share change near onset

## Causal Chain

**Topology path:** esxi-host-01 → vm-app-01 → guest-os-vm-app-01 → orders-api. Amplifier: high-cardinality request pattern.

**Narrative steps (evidence-backed):**

1. `infra.change` — DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01 (event, 2026-07-10T09:55:00Z)
2. `esx.cpu.ready` — ESXi cpu.ready elevated on esxi-host-01 (12% > 5% threshold) (event, 2026-07-10T10:00:05Z)
3. `esx.cpu.usage` — ESXi cpu.usage 92% sustained on esxi-host-01 (event, 2026-07-10T10:00:05Z)
4. `vmware.cpu.ready` — VM cpu.ready 11% on vm-app-01 (host scheduler starvation) (event, 2026-07-10T10:00:12Z)
5. `syslog.loadavg` — load average 8.0 on guest-os-vm-app-01 (run-queue backlog) (event, 2026-07-10T10:00:18Z)
6. `app.latency` — orders-api p95 latency 1450ms (SLO threshold 1000ms) (event, 2026-07-10T10:00:25Z)
7. `anomaly_cpu.usage` — `esxi-host-01` cpu.usage=92.0 (anomaly, 2026-07-10T10:00:05Z)
8. `anomaly_cpu.ready` — `esxi-host-01` cpu.ready=12.0 (anomaly, 2026-07-10T10:00:05Z)
9. `anomaly_cpu.ready` — `vm-app-01` cpu.ready=11.0 (anomaly, 2026-07-10T10:00:12Z)
10. `anomaly_cpu.ready` — `vm-db-01` cpu.ready=10.0 (anomaly, 2026-07-10T10:00:12Z)
11. `trace_symptom_spans` — 4 spans (p50≈1100.0ms) corroborate the cascade (trace)

## Contributing Factors

- **Primary:** CPU contention on ESXi host
- **Amplifier:** None
- **False leads:** 

## Timeline

- 2026-07-10T09:55:00Z · event — infra.change: DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01
- 2026-07-10T10:00:05Z · event — esx.cpu.ready: ESXi cpu.ready elevated on esxi-host-01 (12% > 5% threshold)
- 2026-07-10T10:00:05Z · event — esx.cpu.usage: ESXi cpu.usage 92% sustained on esxi-host-01
- 2026-07-10T10:00:05Z · anomaly — esxi-host-01 `cpu.usage`=92.0
- 2026-07-10T10:00:05Z · anomaly — esxi-host-01 `cpu.ready`=12.0
- 2026-07-10T10:00:12Z · event — vmware.cpu.ready: VM cpu.ready 11% on vm-app-01 (host scheduler starvation)
- 2026-07-10T10:00:12Z · anomaly — vm-app-01 `cpu.ready`=11.0
- 2026-07-10T10:00:12Z · anomaly — vm-db-01 `cpu.ready`=10.0
- 2026-07-10T10:00:18Z · event — syslog.loadavg: load average 8.0 on guest-os-vm-app-01 (run-queue backlog)
- 2026-07-10T10:00:18Z · anomaly — guest-os-vm-app-01 `load.avg`=8.0
- 2026-07-10T10:00:25Z · event — app.latency: orders-api p95 latency 1450ms (SLO threshold 1000ms)
- 2026-07-10T10:00:25Z · anomaly — orders-api `request.p95_latency_ms`=1450.0
- 2026-07-10T10:00:25Z · symptom_seed — Symptom seed orders-api / request.p95_latency_ms

## Remediation

Host CPU Ready / usage shows the hypervisor is oversubscribed. Rebalance VMs, reduce vCPU overcommit, then confirm app p95 recovers — do not scale the app alone.

_Source: `signature_template` (replace with LLM guidance when available)_

## Actions

### Immediate
- Rebalance or vMotion overloaded VMs off the contended ESXi host.
- Identify runaway / over-provisioned vCPU consumers; reduce host overcommit.

### Future
- Tune DRS / right-size vCPU reservations; alert on host cpu.ready across ≥2 VMs.

## Executive Summary

**Potential cause:** DRS / capacity change: additional vCPU-heavy VMs scheduled onto esxi-host-01

**Impact:** Symptom `request.p95_latency_ms` on `orders-api` (CPU contention on ESXi host)

**Resolution:** Rebalance or vMotion overloaded VMs off the contended ESXi host.; Identify runaway / over-provisioned vCPU consumers; reduce host overcommit.

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
