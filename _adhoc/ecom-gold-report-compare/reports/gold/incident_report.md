# Incident Analysis Report — `ecom-numa-001` (Gold)

**Engine:** `gold` · **Source:** OpenObserve write-up · **Incident:** `3GAWT8nVjUE2rA95CZmtyiQcVri`

> Acceptance-story reference for Lean/Federated `comprehensive_rca.v1` reports.
> Body below is the original OO `suggested_root_cause` (unchanged substance).

---

## RCA Summary

**Root cause:** NP-17 cross-NUMA IRQ affinity (node image `2026.06.18`)

**Causal path:** node-image / IRQ affinity change → RX-7 cross-NUMA stall → AAAA DNS latency → payment pool / acquire stall → payment-provider span (≈17s, **false lead**) → checkout SLO → api-gateway error escalation

**Customer impact:** Checkout success dropped 99.97% → 97.2% for Region-B · CARD · MOBILE (≈2.8% of checkouts); ≈186 failed / 387 checkout transactions in the incident window

**Amplifier:** CARD + INR + cart_items > 12 payment-risk feature (extra AAAA DNS lookups)

**False leads ruled out:** external payment-provider (healthy for other apps); NP-17 jumbo-frame / MTU decoys

**Change evidence:** Node pool NP-17 rolled to node image `2026.06.18` (IRQ affinity RX-7 → CPU48 / NUMA1 while queue memory on NUMA0)

---

## Incident Summary
- **Incident ID**: 3GAWT8nVjUE2rA95CZmtyiQcVri
- **Severity**: P3 (Medium)
- **Detected**: 2026-07-07 09:00:58 UTC
- **Resolved**: Ongoing
- **Duration**: Approximately 35 minutes (from 08:25 to 09:00)
- **Affected Services**: checkout-service, payment-service, api-gateway
- **Customer Impact**: Checkout success rate dropped from 99.97% to 97.2% for mobile CARD payments in Region-B with INR currency and cart items >= 12 (≈2.8% of checkout transactions failed)

## Impact Assessment

- **Services Affected**: 3 services (checkout-service, payment-service, api-gateway) + 1 external dependency (payment-provider)
- **Peak Error Rate**: 48.06% on api-gateway → checkout-service path
- **Failed Requests**: ≈186 failed requests out of 387 checkout transactions during the incident window
- **Users Impacted**: Estimated ≈2.8% of checkout transactions affected (specific dimension: mobile + CARD payments + INR + cart size >= 12 items)
- **Data Loss**: No (SLO breach only)
- **SLA Breach**: Yes (Checkout success rate SLO of 99.5% breached at 97.2%)

## Evidence

### Service Dependencies

The service topology reveals a critical path:
- **api-gateway** → **checkout-service** → **payment-service** → **payment-provider** (external)
- The error rate escalation flows upward: payment-service (0% errors) → checkout-service (17.6% errors) → api-gateway (48% errors)
- **Root dependency**: payment-service calls payment-provider with p99 latency of ≈17 seconds (vs normal 60ms), causing connection pool exhaustion on checkout-service
- Upstream services (orders-service, pricing-service, inventory-service) show 0% errors, confirming isolated impact to payment path

### Distributed Traces

Payment-service to payment-provider span shows consistent 17-second durations across all affected traces:
- 30 analyzed traces all show 17,000ms duration for payment-provider HTTP POST calls
- This 17-second latency is not a payment-provider slowdown (other applications calling the same provider report normal latencies)
- Latency injection point: occurs before the payment-provider span, indicating DNS resolution or connection acquisition delays

### Log Patterns

**Kernel network logs** reveal systematic cross-NUMA latency on node pool NP-17:
- 30 consecutive WARN entries (from 2026-07-07 08:13:48 UTC onward) show RX queue 7 processing latency consistently ≈2.6–2.9 seconds
- Every log entry includes the diagnostic: `"cpu=48 numa=1 (queue memory numa=0 cross-NUMA)"`
- This indicates IRQ (Interrupt Request) pinned to CPU 48 on NUMA node 1, while NIC queue memory resides on NUMA node 0
- Cross-NUMA memory access causes memory controller contention and pipeline stalls

**Infrastructure change logs** document the root cause event:
- **2026-07-07 08:25:48 UTC**: Node pool NP-17 rolled to node image 2026.06.18 with message "IRQ balancing configuration applied"
- **2026-07-07 08:25:53 UTC**: IRQ affinity configuration logged as WARNING: `"IRQ affinity set: RX-7 -> CPU48 (NUMA node 1); NIC queue memory on NUMA node 0"`
- This timing aligns precisely with the incident onset (35 minutes before alert at 09:00:58)

### Metrics Analysis

**Checkout latency correlation**:
- Checkout p99 latency for affected dimension (Region-B, INR, cart>=12 items): sustained 15.7–18.8 seconds
- This directly matches the payment-provider call duration observed in traces (17 seconds)
- Latency remained elevated throughout the ≈35-minute incident window

**DNS query latency on NP-17**:
- AAAA (IPv6) queries: p99 latency ≈2.8–3.3 seconds (baseline unknown, but anomalously high for DNS)
- A-records and cluster DNS show normal latency (not affected by RX queue issue)
- Only IPv6 AAAA queries affected because the payment-risk feature for CARD+INR+cart>12 dimension issues 6–12 IPv6 DNS lookups per request

**Payment connection acquisition latency**:
- Connection acquisition times on NP-17: 3.0–4.7 seconds (baseline expected <50ms)
- Pool exhaustion inferred from sustained high latencies (connection queue backlog)

**Kernel RX queue latency**:
- RX-7 queue latency: 2.5–2.9 seconds consistently
- Spike recorded at exact infrastructure change time (2026-07-07 08:25:48 UTC) with sharp transition to elevated baseline
- One anomalous reading at 2026-07-07 08:25:12 UTC showing 0.12ms (before the change), confirming normal state prior to rollout

**Success rate drop alignment**:
- Checkout success rate dropped from 99.97% (normal baseline) to 97.2–97.4% (during incident)
- The timing shows success rate already degraded at the earliest metric timestamp (2026-07-07 08:06:48 UTC = 1783410808000000), ≈19 minutes after the node image rollout

### Recent Changes

**Infrastructure Change Event (Root Cause)**:
- **Timestamp**: 2026-07-07 08:25:48 UTC (1783412748000000 microseconds)
- **Change Type**: node_image_rollout
- **Node Pool**: NP-17
- **New Image**: 2026.06.18
- **Previous Image**: 2026.05.30
- **Region**: Region-B
- **Cluster**: prod-use1
- **Configuration Applied**: IRQ balancing configuration
- **Specific Configuration Error**: IRQ affinity set with RX-7 → CPU48 (NUMA node 1), but NIC queue memory allocated on NUMA node 0
- **Impact**: Cross-NUMA memory access penalty causes ≈2.8 second additional latency per NIC queue process cycle

**Causal Chain Confirmed**:
1. Node image 2026.06.18 deployed to NP-17 with bad IRQ affinity config
2. RX-7 IRQ pinned to CPU48 (NUMA1), queue memory on NUMA0 → cross-NUMA latency ≈2.8s
3. Cross-NUMA latency → slow IPv6 DNS (AAAA queries) ≈3.2s p99 on NP-17
4. Slow DNS → payment-connection acquisition stalled ≈4.3s + pool exhaustion on 4 pods
5. Payment service calls payment-provider with retries and queuing delays → 17s latency
6. Checkout service experiences tail latency and timeouts → SLO breach (97.2% success rate)
7. Dimension amplification: CARD+INR+cart>12 payment-risk feature triggers 6–12 DNS lookups per request, only this subset affected

### Contributing Factors

1. **Primary cause**: Node image 2026.06.18 IRQ affinity misconfiguration pinning RX-7 interrupt to cross-NUMA CPU core, causing 2.8s per-cycle network processing delays
2. **Amplification vector**: Payment-risk feature for CARD+INR+cart>12 dimension triggers multiple IPv6 DNS lookups (6–12 per request), making only this dimension susceptible
3. **Lack of pre-rollout testing**: The IRQ affinity configuration change was not validated against NUMA topology before deployment
4. **Missing canary/gradual rollout**: Node pool was fully rolled to the broken image without staged validation

## Timeline

- **2026-07-07 08:25:48 UTC** - Node pool NP-17 rolled to image 2026.06.18 with IRQ balancing configuration
- **2026-07-07 08:25:53 UTC** - IRQ affinity misconfiguration logged: RX-7 → CPU48 (NUMA1) with queue memory on NUMA0
- **2026-07-07 08:26:48 UTC** - Kernel logs begin showing elevated RX queue latency (≈2.6–2.9s on RX-7)
- **2026-07-07 08:06:48 UTC (earliest metric)** - Checkout success rate already degraded to 97.2% (billing timestamps reflect time-shifted ingestion)
- **2026-07-07 09:00:58 UTC** - Alert "ecom_checkout_slo_breach" fires, detecting success rate < 99.5%
- **Status**: Ongoing (no remediation recorded)

## Actions

### Immediate
- **Revert node image 2026.06.18 on NP-17** to previous version 2026.05.30 to restore normal IRQ affinity configuration
- **Verify IRQ affinity configuration** in deployment artifacts; specifically confirm RX queue interrupts are pinned to CPUs on the same NUMA node as their allocated memory
- **Verify kernel checkout latency** returns to baseline (<1s p99) after rollback

### Future
- **Implement pre-deployment NUMA topology validation** in the infrastructure automation pipeline; cross-NUMA IRQ affinity assignments must be flagged as errors
- **Add staged rollout process** for node image updates: begin with 1–2 nodes in a node pool, monitor RX/TX queue latencies and network performance metrics for 10+ minutes before proceeding to full pool rollout
- **Create monitoring rule** for cross-NUMA network processing: alert if kernel logs show `irq_affinity` changes assigning interrupts to a different NUMA node than the NIC queue memory
- **Improve payment-risk feature resilience** by adding connection pool pre-warming and implementing exponential backoff with jitter for DNS timeouts to prevent cascading failures

## Executive Summary

**Potential Cause**: Node image 2026.06.18 deployed to node pool NP-17 in prod-use1/Region-B on 2026-07-07 08:25:48 UTC with an IRQ affinity misconfiguration that pinned the RX-7 network interrupt to CPU48 (NUMA node 1) while NIC queue memory resides on NUMA node 0, causing ≈2.8-second cross-NUMA memory access latencies. This network processing delay cascaded through DNS resolution (≈3.2s AAAA query latency on affected nodes) → payment service connection acquisition stalls (≈4.3s) → payment provider call retries and timeout delays (≈17s) → checkout service SLO breach (success rate dropped from 99.97% to 97.2%). Impact was isolated to mobile CARD payments in INR currency with cart size ≥ 12 items due to a 6–12× IPv6 DNS lookup amplification factor in the payment-risk feature for that dimension.

**Impact**: Checkout SLO breach affecting ≈2.8% of transactions in the mobile CARD + INR + cart≥12 dimension (Region-B, prod-use1 cluster). 186 failed checkouts out of 387 during the 35-minute incident window.

**Resolution**: Rollback node image 2026.06.18 on NP-17 to version 2026.05.30 and validate IRQ affinity configuration before any re-deployment. Implement pre-deployment NUMA topology validation and staged rollout procedures to prevent future misconfiguration.
