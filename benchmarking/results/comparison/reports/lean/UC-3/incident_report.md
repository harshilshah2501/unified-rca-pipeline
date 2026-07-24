# Incident Analysis Report — `UC-3`

**Engine:** `lean` · **Schema:** `comprehensive_rca.v1` · **Completeness:** 15/15 (100.0%)

## RCA Summary

**Root cause:** `datastore-01` (`storage_contention`)
Datastore storage contention

**Causal path:** `datastore-01` → `vm-app-01` → `guest-os-vm-app-01` → `orders-api`

**Customer impact:** Symptom `request.p95_latency_ms` on `orders-api` (Datastore storage contention)

**Amplifier:** classic-infra cascade (shared upstream fault → app symptom)

**False leads ruled out:** none identified

**Change evidence:** Batch / fio workload started on vm-neighbor-01 (shared datastore-01)

## Incident Summary

| Field | Value |
|-------|-------|
| Root CI | `datastore-01` |
| Signature | `storage_contention` |
| Matches pack GT | True |
| Severity | P2 |
| Detected | 2026-07-10T10:00:25Z |
| Dimension | ObserveOps classic-infra · `2_infra` / `storage_noisy_neighbor` |
| Affected services | `orders-api` |
| Customer impact | Symptom `request.p95_latency_ms` on `orders-api` (Datastore storage contention) |

## Impact Assessment

- **SLA breach:** True
- **Data loss:** False
- **Fail fraction:** ≈2.8% of checkouts in the affected dimension
- **Blast / services:** `vm-db-01`, `guest-os-vm-db-01`, `orders-api`

## Service Dependencies

**Critical path:** `esxi-host-01` → `switch-core-01:GigE0/2`

Healthy siblings (pricing/inventory/token/fraud) are not on the failing payment path; errors escalate api-gateway ← checkout ← payment ← (DNS/RX/IRQ), with payment-provider as a decoy leaf.

## Distributed Traces

- Analyzed spans: 3
- Slow spans (>500ms): 3
- Span duration p50/max ms: 3866.7 / 4200.0

**Assessment:** Trace samples include infra/root-layer spans that corroborate the localized root CI; app spans show elevated latency as a downstream symptom.

| Trace | Service | Span | Duration ms | CI / note |
|-------|---------|------|-------------|-----------|
| `uc3-t1…` | orders-api | POST /orders | 4200.0 | orders-api |
| `uc3-t1…` | vm-db-01 | db.query | 3900.0 | vm-db-01 |
| `uc3-t1…` | datastore-01 | storage.io.wait | 3500.0 | root_evidence |

## Log Patterns

- Batch / fio workload started on vm-neighbor-01 (shared datastore-01)
- vm-db-01 virtualDisk.totalLatency elevated (victim VM)
- datastore-01 GAVG latency > 30ms (shared storage contention)
- vm-neighbor-01 heavy random I/O on datastore-01 (noisy neighbor)
- orders-api slow DB queries / timeouts (storage-backed)

- `app.db_slow` × 1
- `infra.change` × 1
- `storage.iops` × 1
- `storage.latency` × 1
- `vmware.disk.latency` × 1

## Metrics Analysis

- `datastore-01` `gavg_latency_ms` = **45.0** (threshold 30.0) at 2026-07-10T10:00:05Z
- `datastore-01` `davg_latency_ms` = **28.0** (threshold 20.0) at 2026-07-10T10:00:05Z
- `vm-neighbor-01` `virtualDisk.iops` = **12000.0** (threshold 5000.0) at 2026-07-10T10:00:05Z
- `vm-db-01` `virtualDisk.totalLatency_ms` = **38.0** (threshold 30.0) at 2026-07-10T10:00:12Z
- `guest-os-vm-db-01` `disk.iowait_pct` = **72.0** (threshold 50.0) at 2026-07-10T10:00:18Z
- `orders-api` `request.p95_latency_ms` = **2100.0** (threshold 1000.0) at 2026-07-10T10:00:25Z

## Recent Changes

**Root-cause change:** 2026-07-10T09:57:00Z — Batch / fio workload started on vm-neighbor-01 (shared datastore-01)
- 2026-07-10T09:57:00Z: Batch / fio workload started on vm-neighbor-01 (shared datastore-01)

## Causal Chain

**Topology path:** datastore-01 → vm-app-01 → guest-os-vm-app-01 → orders-api. Amplifier: high-cardinality request pattern.

**Narrative steps (evidence-backed):**

1. `infra.change` — Batch / fio workload started on vm-neighbor-01 (shared datastore-01) (event, 2026-07-10T09:57:00Z)
2. `storage.latency` — datastore-01 GAVG latency > 30ms (shared storage contention) (event, 2026-07-10T10:00:05Z)
3. `storage.iops` — vm-neighbor-01 heavy random I/O on datastore-01 (noisy neighbor) (event, 2026-07-10T10:00:08Z)
4. `vmware.disk.latency` — vm-db-01 virtualDisk.totalLatency elevated (victim VM) (event, 2026-07-10T10:00:12Z)
5. `app.db_slow` — orders-api slow DB queries / timeouts (storage-backed) (event, 2026-07-10T10:00:18Z)
6. `anomaly_gavg_latency_ms` — `datastore-01` gavg_latency_ms=45.0 (anomaly, 2026-07-10T10:00:05Z)
7. `anomaly_davg_latency_ms` — `datastore-01` davg_latency_ms=28.0 (anomaly, 2026-07-10T10:00:05Z)
8. `anomaly_virtualDisk.iops` — `vm-neighbor-01` virtualDisk.iops=12000.0 (anomaly, 2026-07-10T10:00:05Z)
9. `anomaly_virtualDisk.totalLatency_ms` — `vm-db-01` virtualDisk.totalLatency_ms=38.0 (anomaly, 2026-07-10T10:00:12Z)
10. `anomaly_disk.iowait_pct` — `guest-os-vm-db-01` disk.iowait_pct=72.0 (anomaly, 2026-07-10T10:00:18Z)
11. `trace_symptom_spans` — 3 spans (p50≈3866.7ms) corroborate the cascade (trace)

## Contributing Factors

- **Primary:** Datastore storage contention
- **Amplifier:** None
- **False leads:** 

## Timeline

- 2026-07-10T09:57:00Z · event — infra.change: Batch / fio workload started on vm-neighbor-01 (shared datastore-01)
- 2026-07-10T10:00:05Z · event — storage.latency: datastore-01 GAVG latency > 30ms (shared storage contention)
- 2026-07-10T10:00:05Z · anomaly — datastore-01 `gavg_latency_ms`=45.0
- 2026-07-10T10:00:05Z · anomaly — datastore-01 `davg_latency_ms`=28.0
- 2026-07-10T10:00:05Z · anomaly — vm-neighbor-01 `virtualDisk.iops`=12000.0
- 2026-07-10T10:00:08Z · event — storage.iops: vm-neighbor-01 heavy random I/O on datastore-01 (noisy neighbor)
- 2026-07-10T10:00:12Z · event — vmware.disk.latency: vm-db-01 virtualDisk.totalLatency elevated (victim VM)
- 2026-07-10T10:00:12Z · anomaly — vm-db-01 `virtualDisk.totalLatency_ms`=38.0
- 2026-07-10T10:00:18Z · event — app.db_slow: orders-api slow DB queries / timeouts (storage-backed)
- 2026-07-10T10:00:18Z · anomaly — guest-os-vm-db-01 `disk.iowait_pct`=72.0
- 2026-07-10T10:00:25Z · anomaly — orders-api `request.p95_latency_ms`=2100.0
- 2026-07-10T10:00:25Z · symptom_seed — Symptom seed orders-api / request.p95_latency_ms

## Remediation

Shared datastore latency plus a noisy-neighbor I/O source explains DB/app slowness. Move or throttle the neighbor; do not treat the DB as the primary root.

_Source: `signature_template` (replace with LLM guidance when available)_

## Actions

### Immediate
- Storage vMotion the noisy-neighbor VM or the victim DB VM off the hot datastore.
- Apply Storage I/O Control / IOPS limits on the noisy neighbor.

### Future
- Monitor datastore GAVG/DAVG with per-VM disk latency correlation.

## Executive Summary

**Potential cause:** Batch / fio workload started on vm-neighbor-01 (shared datastore-01)

**Impact:** Symptom `request.p95_latency_ms` on `orders-api` (Datastore storage contention)

**Resolution:** Storage vMotion the noisy-neighbor VM or the victim DB VM off the hot datastore.; Apply Storage I/O Control / IOPS limits on the noisy neighbor.

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
