# Incident Analysis Report — `ecom-numa-001`

**Engine:** `federated` · **Schema:** `comprehensive_rca.v1` · **Completeness:** 15/15 (100.0%)

**Source incident:** `3GAWT8nVjUE2rA95CZmtyiQcVri`

## RCA Summary

**Root cause:** `np17-irq-affinity` (`cross_numa_irq_affinity`)
NP-17 cross-NUMA IRQ affinity (node image 2026.06.18)

**Causal path:** `np17-irq-affinity` → `nic-rx-queue-7` → `dns-aaaa-np17` → `payment-service` → `checkout-service`

**Customer impact:** Checkout success ≈97.2% (threshold 99.5) on `checkout-service` / `checkout_success_rate`; ≈186/387 failed checkouts in the incident window (≈2.8% of the affected dimension)

**Amplifier:** CARD+INR+cart>12 payment-risk feature (extra AAAA DNS lookups)

**False leads ruled out:** `payment-provider`, `node_nic_mtu (NP-17 jumbo frames — in raw metrics, not pack anomalies)`

**Change evidence:** Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)

## Incident Summary

| Field | Value |
|-------|-------|
| Root CI | `np17-irq-affinity` |
| Signature | `cross_numa_irq_affinity` |
| Matches pack GT | True |
| Severity | P3 (Medium) |
| Detected | 2026-07-07T09:00:58Z |
| Dimension | Region-B · CARD · MOBILE · INR · cart_items>12 (payment-risk amplifier) |
| Affected services | `api-gateway`, `checkout-service`, `payment-service`, `dns-aaaa-np17` |
| Customer impact | Checkout success ≈97.2% (threshold 99.5) on `checkout-service` / `checkout_success_rate`; ≈186/387 failed checkouts in the incident window (≈2.8% of the affected dimension) |

## Impact Assessment

- **SLA breach:** True
- **Data loss:** False
- **Fail fraction:** ≈186 failed / 387 checkout transactions (≈2.8% of affected dimension)
- **Failed requests:** ≈186 / 387
- **Peak path error rate:** 48.06% on api-gateway → checkout-service
- **Checkout service error rate:** 17.6%
- **Payment service error rate:** 0.2% (blast-radius / escalation baseline)
- **Error escalation:** payment-service 0.2% → checkout-service 17.6% → api-gateway 48.06%
- **Blast / services:** `api-gateway`, `checkout-service`, `payment-service`, `payment-pod-118`, `payment-pod-124`, `payment-pod-131`, `payment-pod-144`

## Service Dependencies

**Critical path:** `api-gateway` → `checkout-service` → `payment-service` → `dns-aaaa-np17` → `nic-rx-queue-7` → `np17-irq-affinity`

Healthy siblings (pricing/inventory/token/fraud) are not on the failing payment path; errors escalate api-gateway ← checkout ← payment ← (DNS/RX/IRQ), with payment-provider as a decoy leaf.

## Distributed Traces

- Analyzed spans: 840
- Slow payment-provider spans: 24
- Provider duration p50/max ms: 17000.0 / 17000.0
- Healthy sibling spans (<200ms): 252

**False-lead assessment:** Payment-provider CLIENT/SERVER spans show ≈17s duration on affected traces, but sibling services remain fast and only NP-17 payment pods correlate — treat external provider as a false lead; latency is consistent with pre-provider DNS/connection stall (AAAA / pool).

| Trace | Span | Duration ms | DNS | Node pool |
|-------|------|-------------|-----|-----------|
| `56335ca16178…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `d7e58b1c0212…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `7543a28dd72c…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `b4b714950b42…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `a0e00b32ea16…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |

## Log Patterns

- Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- RX queue 7 processing latency high (2740ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3159ms
- Payment provider request timeout
- Connection acquisition took 4560ms
- Downstream payment call slow (14793ms) region=Region-B currency=INR cart_items=21
- Retry attempt 2/3
- Alert ecom_checkout_slo_breach fired: checkout success rate < 99.5

- `alert.fire` × 1
- `checkout.orchestrator` × 44
- `deploy.app` × 1
- `dns.resolver` × 6
- `http.connection` × 66
- `infra.automation` × 2
- `kernel.net` × 35
- `payment.client` × 66
- `payment.retry` × 66

## Metrics Analysis

- `np17-irq-affinity` `irq_affinity_numa_mismatch` = **1.0** (threshold 0.0) at 2026-07-07T08:25:48Z
- `nic-rx-queue-7` `kernel_rx_queue_latency_ms` = **2936.6** (threshold 10.0) at 2026-07-07T08:25:48Z
- `dns-aaaa-np17` `dns_query_latency_p99_ms` = **3359.3** (threshold 50.0) at 2026-07-07T08:27:48Z
- `payment-service` `payment_connection_acquire_ms` = **4737.1** (threshold 100.0) at 2026-07-07T08:27:48Z
- `payment-provider` `payment_provider_latency_ms` = **17845.2** (threshold 200.0) at 2026-07-07T08:27:48Z — FALSE LEAD — only this app's NP-17 pods; provider is healthy for others
- `checkout-service` `checkout_latency_p99_ms` = **18779.8** (threshold 1000.0) at 2026-07-07T08:27:48Z
- `checkout-service` `checkout_success_rate` = **97.2** (threshold 99.5) at 2026-07-07T08:27:48Z
- `api-gateway` `api_gateway_error_rate_pct` = **48.06** (threshold 20.0) at 2026-07-07T08:27:48Z — api-gateway → checkout path error escalation
- `checkout-service` `checkout_error_rate_pct` = **17.6** (threshold 5.0) at 2026-07-07T08:27:48Z — checkout-service error rate (blast / escalation mid-tier)

Raw export peaks/mins:
- `checkout_latency_p99_ms` → 18779.8
- `checkout_success_rate` → 97.009
- `dns_query_latency_p99_ms` → 3359.3
- `irq_affinity_numa_mismatch` → 1.0
- `kernel_rx_queue_latency_ms` → 2936.6
- `payment_connection_acquire_ms` → 4737.1
- `api_gateway_error_rate_pct` → 49.46
- `checkout_error_rate_pct` → 18.12
- `payment_service_error_rate_pct` → 0.3
- `checkout_requests_total` → 387
- `checkout_failures_total` → 186

## Recent Changes

**Root-cause change:** 2026-07-07T08:25:48Z — Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- 2026-06-23T09:00:48Z: Deployed payment-risk feature: extra risk check for CARD+INR+cart_items>12 (adds device-intelligence + risk provider DNS lookups)
- 2026-07-07T08:25:48Z: Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- 2026-07-07T08:25:53Z: IRQ affinity set: RX-7 -> CPU48 (NUMA node 1); NIC queue memory on NUMA node 0

## Causal Chain

**Topology path:** np17-irq-affinity → nic-rx-queue-7 → dns-aaaa-np17 → payment-service → checkout-service. Amplifier: CARD+INR+cart>12 payment-risk feature (extra AAAA DNS lookups)

**Narrative steps (evidence-backed):**

1. `node_image_irq_change` — Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied) (event, 2026-07-07T08:25:48Z)
2. `cross_numa_irq` — IRQ affinity mismatch on `np17-irq-affinity` value=1.0 (anomaly, 2026-07-07T08:25:48Z)
3. `rx_queue_stall` — RX-7 latency `kernel_rx_queue_latency_ms`=2936.6ms (anomaly, 2026-07-07T08:25:48Z)
4. `aaaa_dns_stall` — AAAA DNS p99 `dns_query_latency_p99_ms`=3359.3ms (anomaly, 2026-07-07T08:27:48Z)
5. `payment_pool_stall` — Payment acquire `payment_connection_acquire_ms`=4737.1ms (anomaly, 2026-07-07T08:27:48Z)
6. `provider_span_false_lead` — Payment-provider spans ≈17000.0ms ×24 — false lead (trace)
7. `checkout_gateway_symptom` — checkout success=97.2%; api-gateway error=48.06% (anomaly, 2026-07-07T08:27:48Z)
8. `amplifier` — CARD+INR+cart>12 payment-risk feature (extra AAAA DNS lookups) (ground_truth_amplifier)

## Contributing Factors

- **Primary:** NP-17 cross-NUMA IRQ affinity (node image 2026.06.18)
- **Amplifier:** CARD+INR+cart>12 payment-risk feature (extra AAAA DNS lookups)
- **False leads:** payment-provider, node_nic_mtu (NP-17 jumbo frames — in raw metrics, not pack anomalies)

## Timeline

- 2026-06-23T09:00:48Z · event — deploy.app: Deployed payment-risk feature: extra risk check for CARD+INR+cart_items>12 (adds device-intelligence + risk provider DNS
- 2026-07-07T08:25:48Z · event — kernel.net: RX queue 7 processing latency high (2740ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:25:48Z · event — infra.automation: Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- 2026-07-07T08:25:48Z · anomaly — np17-irq-affinity `irq_affinity_numa_mismatch`=1.0
- 2026-07-07T08:25:48Z · anomaly — nic-rx-queue-7 `kernel_rx_queue_latency_ms`=2936.6
- 2026-07-07T08:25:53Z · event — infra.automation: IRQ affinity set: RX-7 -> CPU48 (NUMA node 1); NIC queue memory on NUMA node 0
- 2026-07-07T08:26:48Z · event — kernel.net: RX queue 7 processing latency high (2769ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:27:48Z · event — payment.client: Payment provider request timeout
- 2026-07-07T08:27:48Z · event — checkout.orchestrator: Downstream payment call slow (14793ms) region=Region-B currency=INR cart_items=21
- 2026-07-07T08:27:48Z · event — kernel.net: RX queue 7 processing latency high (2666ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:27:48Z · anomaly — dns-aaaa-np17 `dns_query_latency_p99_ms`=3359.3
- 2026-07-07T08:27:48Z · anomaly — payment-service `payment_connection_acquire_ms`=4737.1
- 2026-07-07T08:27:48Z · anomaly — payment-provider `payment_provider_latency_ms`=17845.2
- 2026-07-07T08:27:48Z · anomaly — checkout-service `checkout_latency_p99_ms`=18779.8
- 2026-07-07T08:27:48Z · anomaly — checkout-service `checkout_success_rate`=97.2
- 2026-07-07T08:27:48Z · anomaly — api-gateway `api_gateway_error_rate_pct`=48.06
- 2026-07-07T08:27:48Z · anomaly — checkout-service `checkout_error_rate_pct`=17.6
- 2026-07-07T08:27:48Z · symptom_seed — Symptom seed checkout-service / checkout_success_rate
- 2026-07-07T08:27:52Z · event — http.connection: Connection acquisition took 4560ms
- 2026-07-07T08:28:18Z · event — payment.client: Payment provider request timeout
- 2026-07-07T08:28:22Z · event — http.connection: Connection acquisition took 4041ms
- 2026-07-07T08:28:33Z · event — checkout.orchestrator: Downstream payment call slow (16067ms) region=Region-B currency=INR cart_items=22
- 2026-07-07T08:28:48Z · event — kernel.net: RX queue 7 processing latency high (2727ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:28:48Z · event — payment.client: Payment provider request timeout
- 2026-07-07T08:28:52Z · event — http.connection: Connection acquisition took 4216ms
- 2026-07-07T08:29:18Z · event — checkout.orchestrator: Downstream payment call slow (11132ms) region=Region-B currency=INR cart_items=18
- 2026-07-07T08:29:24Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3159ms
- 2026-07-07T08:29:48Z · event — kernel.net: RX queue 7 processing latency high (2881ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:30:48Z · event — kernel.net: RX queue 7 processing latency high (2838ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:31:48Z · event — kernel.net: RX queue 7 processing latency high (2858ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:32:48Z · event — kernel.net: RX queue 7 processing latency high (2811ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-07T08:33:22Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3047ms
- 2026-07-07T08:39:39Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3108ms
- 2026-07-07T08:43:05Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3251ms
- 2026-07-07T09:00:58Z · alert — alert.fire: Alert ecom_checkout_slo_breach fired: checkout success rate < 99.5

## Remediation

Treat this as an infrastructure misconfiguration incident, not a payment-provider outage. Immediately roll NP-17 back from node image 2026.06.18 to 2026.05.30 so RX-7 IRQs pin to the same NUMA node as queue memory, then confirm kernel RX-queue latency, AAAA DNS p99, checkout p99, and checkout success rate return to baseline on the Region-B · CARD · MOBILE · INR · cart>12 slice. Do not restart payment pods as the primary fix — that only masks pool pressure. After mitigation, block cross-NUMA IRQ assignments in the node-image pipeline and stage future NP-17 rollouts on 1–2 nodes with RX/DNS watch windows before full pool promotion.

_Source: `signature_template` (replace with LLM guidance when available)_

## Actions

### Immediate
- Revert NP-17 node image 2026.06.18 → 2026.05.30 to restore IRQ affinity.
- Confirm RX queue IRQs are pinned to CPUs on the same NUMA node as NIC queue memory.
- Verify checkout p99 and RX-queue latency return to baseline after rollback.

### Future
- Add pre-deploy NUMA topology validation; fail builds that assign IRQ across NUMA.
- Stage node-image rollouts (1–2 nodes, watch RX/DNS latency 10+ min) before full pool.
- Alert on kernel cross-NUMA RX processing / irq_affinity_numa_mismatch.
- Harden payment-risk path: pool pre-warm + DNS timeout backoff with jitter.

## Executive Summary

**Potential cause:** Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)

**Impact:** Checkout success ≈97.2% (threshold 99.5) on `checkout-service` / `checkout_success_rate`; ≈186/387 failed checkouts in the incident window (≈2.8% of the affected dimension)

**Resolution:** Revert NP-17 node image 2026.06.18 → 2026.05.30 to restore IRQ affinity.; Confirm RX queue IRQs are pinned to CPUs on the same NUMA node as NIC queue memory.; Verify checkout p99 and RX-queue latency return to baseline after rollback.

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
