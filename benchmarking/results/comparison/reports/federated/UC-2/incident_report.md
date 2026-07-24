# Incident Analysis Report — `UC-2`

**Engine:** `federated` · **Schema:** `comprehensive_rca.v1` · **Completeness:** 15/15 (100.0%)

## RCA Summary

**Root cause:** `switch-core-01:GigE0/2` (`link_failure`)
Core switch link failure

**Causal path:** `switch-core-01:GigE0/2` → `esxi-host-01` → `vm-app-01` → `guest-os-vm-app-01` → `orders-api`

**Customer impact:** Symptom `tcp.timeouts` on `orders-api` (Core switch link failure)

**Amplifier:** classic-infra cascade (shared upstream fault → app symptom)

**False leads ruled out:** none identified

**Change evidence:** Network change window: uplink maintenance on switch-core-01 GigE0/2

## Incident Summary

| Field | Value |
|-------|-------|
| Root CI | `switch-core-01:GigE0/2` |
| Signature | `link_failure` |
| Matches pack GT | True |
| Severity | P2 |
| Detected | 2026-07-10T10:00:18Z |
| Dimension | ObserveOps classic-infra · `2_infra` / `network_fault` |
| Affected services | `orders-api` |
| Customer impact | Symptom `tcp.timeouts` on `orders-api` (Core switch link failure) |

## Impact Assessment

- **SLA breach:** True
- **Data loss:** False
- **Fail fraction:** ≈2.8% of checkouts in the affected dimension
- **Blast / services:** `esxi-host-01`, `vm-app-01`, `vm-db-01`, `orders-api`

## Service Dependencies

**Critical path:** `orders-api` → `guest-os-vm-app-01` → `vm-app-01` → `esxi-host-01` → `switch-core-01:GigE0/2`

Healthy siblings (pricing/inventory/token/fraud) are not on the failing payment path; errors escalate api-gateway ← checkout ← payment ← (DNS/RX/IRQ), with payment-provider as a decoy leaf.

## Distributed Traces

- Analyzed spans: 3
- Slow spans (>500ms): 3
- Span duration p50/max ms: 4366.7 / 5200.0

**Assessment:** App spans show connect/timeout failures consistent with an upstream network path break; treat app errors as blast-radius symptoms.

| Trace | Service | Span | Duration ms | CI / note |
|-------|---------|------|-------------|-----------|
| `uc2-t1…` | orders-api | POST /checkout | 5200.0 | orders-api |
| `uc2-t1…` | orders-api | tcp.connect | 4800.0 | network_path_failure |
| `uc2-t2…` | orders-api | GET /health | 3100.0 | orders-api |

## Log Patterns

- Network change window: uplink maintenance on switch-core-01 GigE0/2
- SNMP TRAP linkDown: ifDescr=GigE0/2 ifOperStatus=down
- ifOutDiscards rising on GigE0/2
- vmnic packet drops / link-down detected on esxi-host-01 uplink
- orders-api TCP timeouts / elevated error rate behind failed uplink

- `app.timeout` × 1
- `esx.net.drop` × 1
- `infra.change` × 1
- `snmp.ifOutDiscards` × 1
- `snmp.linkDown` × 1

## Metrics Analysis

- `switch-core-01:GigE0/2` `linkDown` = **1.0** (threshold 0.5) at 2026-07-10T10:00:00Z
- `switch-core-01:GigE0/2` `ifOutDiscards` = **450.0** (threshold 0.0) at 2026-07-10T10:00:05Z
- `esxi-host-01` `vmnic.dropped_packets` = **120.0** (threshold 0.0) at 2026-07-10T10:00:12Z
- `vm-app-01` `tcp.retransmits` = **85.0** (threshold 10.0) at 2026-07-10T10:00:12Z
- `orders-api` `tcp.timeouts` = **42.0** (threshold 5.0) at 2026-07-10T10:00:18Z

## Recent Changes

**Root-cause change:** 2026-07-10T09:58:00Z — Network change window: uplink maintenance on switch-core-01 GigE0/2
- 2026-07-10T09:58:00Z: Network change window: uplink maintenance on switch-core-01 GigE0/2

## Causal Chain

**Topology path:** switch-core-01:GigE0/2 → esxi-host-01 → vm-app-01 → guest-os-vm-app-01 → orders-api. Amplifier: high-cardinality request pattern.

**Narrative steps (evidence-backed):**

1. `infra.change` — Network change window: uplink maintenance on switch-core-01 GigE0/2 (event, 2026-07-10T09:58:00Z)
2. `snmp.linkDown` — SNMP TRAP linkDown: ifDescr=GigE0/2 ifOperStatus=down (event, 2026-07-10T10:00:00Z)
3. `snmp.ifOutDiscards` — ifOutDiscards rising on GigE0/2 (event, 2026-07-10T10:00:05Z)
4. `esx.net.drop` — vmnic packet drops / link-down detected on esxi-host-01 uplink (event, 2026-07-10T10:00:08Z)
5. `app.timeout` — orders-api TCP timeouts / elevated error rate behind failed uplink (event, 2026-07-10T10:00:12Z)
6. `anomaly_linkDown` — `switch-core-01:GigE0/2` linkDown=1.0 (anomaly, 2026-07-10T10:00:00Z)
7. `anomaly_ifOutDiscards` — `switch-core-01:GigE0/2` ifOutDiscards=450.0 (anomaly, 2026-07-10T10:00:05Z)
8. `anomaly_vmnic.dropped_packets` — `esxi-host-01` vmnic.dropped_packets=120.0 (anomaly, 2026-07-10T10:00:12Z)
9. `anomaly_tcp.retransmits` — `vm-app-01` tcp.retransmits=85.0 (anomaly, 2026-07-10T10:00:12Z)
10. `anomaly_tcp.timeouts` — `orders-api` tcp.timeouts=42.0 (anomaly, 2026-07-10T10:00:18Z)
11. `trace_symptom_spans` — 3 spans (p50≈4366.7ms) corroborate the cascade (trace)

## Contributing Factors

- **Primary:** Core switch link failure
- **Amplifier:** None
- **False leads:** 

## Timeline

- 2026-07-10T09:58:00Z · event — infra.change: Network change window: uplink maintenance on switch-core-01 GigE0/2
- 2026-07-10T10:00:00Z · event — snmp.linkDown: SNMP TRAP linkDown: ifDescr=GigE0/2 ifOperStatus=down
- 2026-07-10T10:00:00Z · anomaly — switch-core-01:GigE0/2 `linkDown`=1.0
- 2026-07-10T10:00:05Z · event — snmp.ifOutDiscards: ifOutDiscards rising on GigE0/2
- 2026-07-10T10:00:05Z · anomaly — switch-core-01:GigE0/2 `ifOutDiscards`=450.0
- 2026-07-10T10:00:08Z · event — esx.net.drop: vmnic packet drops / link-down detected on esxi-host-01 uplink
- 2026-07-10T10:00:12Z · event — app.timeout: orders-api TCP timeouts / elevated error rate behind failed uplink
- 2026-07-10T10:00:12Z · anomaly — esxi-host-01 `vmnic.dropped_packets`=120.0
- 2026-07-10T10:00:12Z · anomaly — vm-app-01 `tcp.retransmits`=85.0
- 2026-07-10T10:00:18Z · anomaly — orders-api `tcp.timeouts`=42.0
- 2026-07-10T10:00:18Z · symptom_seed — Symptom seed orders-api / tcp.timeouts

## Remediation

Restore the failed uplink/port first. App timeouts are effects of the network break; verify redundant paths and clear interface discards before restarting services.

_Source: `signature_template` (replace with LLM guidance when available)_

## Actions

### Immediate
- Restore or replace the failed switch uplink / port.
- Verify redundant NIC teaming and clear discards/errors.

### Future
- Alert on SNMP linkDown + rising discards; validate dual-homed uplinks in change windows.

## Executive Summary

**Potential cause:** Network change window: uplink maintenance on switch-core-01 GigE0/2

**Impact:** Symptom `tcp.timeouts` on `orders-api` (Core switch link failure)

**Resolution:** Restore or replace the failed switch uplink / port.; Verify redundant NIC teaming and clear discards/errors.

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
