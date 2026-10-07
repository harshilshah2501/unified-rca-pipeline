# Incident Analysis Report — `ecom-numa-001`

**Engine:** `lean` · **Schema:** `comprehensive_rca.v1` · **Completeness:** 13/13 (100.0%)

## Incident Summary

| Field | Value |
|-------|-------|
| Root CI | `np17-irq-affinity` |
| Signature | `cross_numa_irq_affinity` |
| Matches pack GT | True |
| Severity | P3 (Medium) |
| Detected | 2026-07-22T10:33:44Z |
| Dimension | Region-B · CARD · MOBILE · INR · cart_items>12 (payment-risk amplifier) |
| Customer impact | Checkout success ~96.901% (threshold 99.5) on seeded symptom `checkout-service` / `checkout_success_rate` |

## Impact Assessment

- **SLA breach:** True
- **Data loss:** False
- **Fail fraction:** ~2.8% of checkouts in the affected dimension
- **Blast / services:** `checkout-service`, `payment-service`, `payment-pod-118`, `payment-pod-124`, `payment-pod-131`, `payment-pod-144`

## Service Dependencies

**Critical path:** `checkout-service` → `payment-service` → `dns-aaaa-np17` → `nic-rx-queue-7` → `np17-irq-affinity`

Healthy siblings (pricing/inventory/token/fraud) are not on the failing payment path; impact concentrates on checkout→payment→(DNS/RX/IRQ) with payment-provider as a decoy leaf.

## Distributed Traces

- Analyzed spans: 840
- Slow payment-provider spans: 24
- Provider duration p50/max ms: 17000.0 / 17000.0
- Healthy sibling spans (<200ms): 252

**False-lead assessment:** Payment-provider CLIENT/SERVER spans show ~17s duration on affected traces, but sibling services remain fast and only NP-17 payment pods correlate — treat external provider as a false lead; latency is consistent with pre-provider DNS/connection stall (AAAA / pool).

| Trace | Span | Duration ms | DNS | Node pool |
|-------|------|-------------|-----|-----------|
| `56335ca16178…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `d7e58b1c0212…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `7543a28dd72c…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `b4b714950b42…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |
| `a0e00b32ea16…` | HTTP POST payments.provider.com | 17000 | AAAA | NP-17 |

## Log Patterns

- RX queue 7 processing latency high (2740ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- IRQ affinity set: RX-7 -> CPU48 (NUMA node 1); NIC queue memory on NUMA node 0
- RX queue 7 processing latency high (2769ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- RX queue 7 processing latency high (2666ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- RX queue 7 processing latency high (2727ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3159ms
- RX queue 7 processing latency high (2881ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)

- `deploy.app` × 1
- `dns.resolver` × 6
- `infra.automation` × 2
- `kernel.net` × 35

## Metrics Analysis

- `np17-irq-affinity` `irq_affinity_numa_mismatch` = **1.0** (threshold 0.0) at 2026-07-22T10:31:44Z
- `nic-rx-queue-7` `kernel_rx_queue_latency_ms` = **2936.6** (threshold 10.0) at 2026-07-22T10:31:44Z
- `dns-aaaa-np17` `dns_query_latency_p99_ms` = **3359.3** (threshold 50.0) at 2026-07-22T10:33:44Z
- `payment-service` `payment_connection_acquire_ms` = **4737.1** (threshold 100.0) at 2026-07-22T10:33:44Z
- `payment-provider` `payment_provider_latency_ms` = **17845.2** (threshold 200.0) at 2026-07-22T10:33:44Z — FALSE LEAD — only this app's NP-17 pods; provider is healthy for others
- `checkout-service` `checkout_latency_p99_ms` = **18779.8** (threshold 1000.0) at 2026-07-22T10:33:44Z
- `checkout-service` `checkout_success_rate` = **96.901** (threshold 99.5) at 2026-07-22T10:33:44Z

Raw export peaks/mins:
- `checkout_latency_p99_ms` → 18779.8
- `checkout_success_rate` → 96.901
- `dns_query_latency_p99_ms` → 3359.3
- `irq_affinity_numa_mismatch` → 1.0
- `kernel_rx_queue_latency_ms` → 2936.6
- `payment_connection_acquire_ms` → 4737.1

## Recent Changes

**Root-cause change:** 2026-07-22T10:31:44Z — Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- 2026-07-08T11:06:44Z: Deployed payment-risk feature: extra risk check for CARD+INR+cart_items>12 (adds device-intelligence + risk provider DNS lookups)
- 2026-07-22T10:31:44Z: Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- 2026-07-22T10:31:49Z: IRQ affinity set: RX-7 -> CPU48 (NUMA node 1); NIC queue memory on NUMA node 0

## Causal Chain

np17-irq-affinity → nic-rx-queue-7 → dns-aaaa-np17 → payment-service → checkout-service. Amplifier: CARD+INR+cart>12 payment-risk feature (extra AAAA DNS lookups)

## Contributing Factors

- **Primary:** NP-17 cross-NUMA IRQ affinity (node image 2026.06.18)
- **Amplifier:** CARD+INR+cart>12 payment-risk feature (extra AAAA DNS lookups)
- **False leads:** payment-provider, node_nic_mtu (NP-17 jumbo frames — in raw metrics, not pack anomalies)

## Timeline

- 2026-07-08T11:06:44Z · event — deploy.app: Deployed payment-risk feature: extra risk check for CARD+INR+cart_items>12 (adds device-intelligence + risk provider DNS
- 2026-07-22T10:31:44Z · event — kernel.net: RX queue 7 processing latency high (2740ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:31:44Z · event — infra.automation: Node pool NP-17 rolled to node image 2026.06.18 (IRQ balancing configuration applied)
- 2026-07-22T10:31:44Z · anomaly — np17-irq-affinity `irq_affinity_numa_mismatch`=1.0
- 2026-07-22T10:31:44Z · anomaly — nic-rx-queue-7 `kernel_rx_queue_latency_ms`=2936.6
- 2026-07-22T10:31:49Z · event — infra.automation: IRQ affinity set: RX-7 -> CPU48 (NUMA node 1); NIC queue memory on NUMA node 0
- 2026-07-22T10:32:44Z · event — kernel.net: RX queue 7 processing latency high (2769ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:33:44Z · event — kernel.net: RX queue 7 processing latency high (2666ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:33:44Z · anomaly — dns-aaaa-np17 `dns_query_latency_p99_ms`=3359.3
- 2026-07-22T10:33:44Z · anomaly — payment-service `payment_connection_acquire_ms`=4737.1
- 2026-07-22T10:33:44Z · anomaly — payment-provider `payment_provider_latency_ms`=17845.2
- 2026-07-22T10:33:44Z · anomaly — checkout-service `checkout_latency_p99_ms`=18779.8
- 2026-07-22T10:33:44Z · anomaly — checkout-service `checkout_success_rate`=96.901
- 2026-07-22T10:33:44Z · symptom_seed — Symptom seed checkout-service / checkout_success_rate
- 2026-07-22T10:34:44Z · event — kernel.net: RX queue 7 processing latency high (2727ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:35:20Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3159ms
- 2026-07-22T10:35:44Z · event — kernel.net: RX queue 7 processing latency high (2881ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:36:44Z · event — kernel.net: RX queue 7 processing latency high (2838ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:37:44Z · event — kernel.net: RX queue 7 processing latency high (2858ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:38:44Z · event — kernel.net: RX queue 7 processing latency high (2811ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:39:18Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3047ms
- 2026-07-22T10:39:44Z · event — kernel.net: RX queue 7 processing latency high (2799ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:40:44Z · event — kernel.net: RX queue 7 processing latency high (2700ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:41:44Z · event — kernel.net: RX queue 7 processing latency high (2684ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:42:44Z · event — kernel.net: RX queue 7 processing latency high (2621ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:43:44Z · event — kernel.net: RX queue 7 processing latency high (2780ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:44:44Z · event — kernel.net: RX queue 7 processing latency high (2808ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:45:35Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3108ms
- 2026-07-22T10:45:44Z · event — kernel.net: RX queue 7 processing latency high (2859ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:46:44Z · event — kernel.net: RX queue 7 processing latency high (2787ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:47:44Z · event — kernel.net: RX queue 7 processing latency high (2659ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:48:44Z · event — kernel.net: RX queue 7 processing latency high (2890ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:49:01Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3251ms
- 2026-07-22T10:49:44Z · event — kernel.net: RX queue 7 processing latency high (2797ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:50:44Z · event — kernel.net: RX queue 7 processing latency high (2648ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:51:44Z · event — kernel.net: RX queue 7 processing latency high (2639ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:52:44Z · event — kernel.net: RX queue 7 processing latency high (2871ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:53:44Z · event — kernel.net: RX queue 7 processing latency high (2700ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:54:44Z · event — kernel.net: RX queue 7 processing latency high (2758ms) cpu=48 numa=1 (queue memory numa=0 cross-NUMA)
- 2026-07-22T10:55:28Z · event — dns.resolver: DNS resolution exceeded expected latency hostname=payments.provider.com query=AAAA latency=3049ms

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

**Impact:** Checkout success ~96.901% (threshold 99.5) on seeded symptom `checkout-service` / `checkout_success_rate`

**Resolution:** Revert NP-17 node image 2026.06.18 → 2026.05.30 to restore IRQ affinity.; Confirm RX queue IRQs are pinned to CPUs on the same NUMA node as NIC queue memory.; Verify checkout p99 and RX-queue latency return to baseline after rollback.

## Completeness checklist

- [x] incident_summary
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
- [x] executive_summary
- [x] localization_root
