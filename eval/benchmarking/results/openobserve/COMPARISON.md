> **Also see:** Option B convention Accuracy — [GT_SCOREBOARD.md](./GT_SCOREBOARD.md) · [GT_ANALYSIS.md](./GT_ANALYSIS.md) · Lean/Federated **engine pack** bakeoff — [ENGINE_SCOREBOARD.md](./ENGINE_SCOREBOARD.md)

# OpenObserve Incidents — Three-Way Peer Comparison

**Generated:** `2026-07-14T13:01:39.901099+00:00`  
**Corpus:** `/root/Harshil-PoCs/Unified-RCA/datasets/openobserve_incidents/v1` (29 incidents)  
**Mode:** peer comparison — **no accuracy / GT claim**  
**Methods:** Lean · Federated · OpenObserve (platform RCA)  
**Behavioral edge (Lean vs Federated only):** `lean`  
**Closest to OpenObserve layer (affinity, not correctness):** `both_equal`

## Framing

1. Each of the **29 incidents** is a use-case payload for comparative RCA.
2. **OpenObserve** is RCA method #3 (platform `suggested_root_cause`), not ground truth.
3. Lean / Federated here are **principle analyzers** on alert topology — not the UC typed-CI runners.
4. Metrics are **agreement and behavior only**. No method is declared correct.

## Peer scoreboard

### Pairwise layer agreement

| Pair | Agreement |
|------|-----------|
| Lean ↔ Federated | **100.0%** |
| Lean ↔ OpenObserve | **75.9%** |
| Federated ↔ OpenObserve | **75.9%** |
| **All three** | **75.9%** |

### Pairwise root-alert agreement

| Pair | Agreement |
|------|-----------|
| Lean ↔ Federated | 75.9% |
| Lean ↔ OpenObserve | 72.4% |
| Federated ↔ OpenObserve | 86.2% |

### Method behavior

| Metric | Lean | Federated | OpenObserve |
|--------|------|-----------|-------------|
| Reproducibility | **100%** | **100%** | **100%** |
| Multi-trigger: picks incident **title** alert | 36% | 100% | 64% |
| Incidents with platform narrative | — | — | 23/29 |
| Multi-trigger incidents | 11/29 | | |
| Incidents with topology edges | 3/29 | | |

Lower title-pick on multi-trigger cases = stronger decoy resistance (behavior, not accuracy).
OpenObserve’s structured root is usually title-shaped, so its title-pick rate is expected high.

## Where OpenObserve layers land (peer map)

Rows keyed by **OpenObserve layer** (method C’s map of the set). Lean/Fed columns = how often that method names the *same* layer — affinity, not hits-vs-GT.

| OO layer | N | Lean same | Federated same |
|----------|---|-----------|----------------|
| database | 10 | 9/10 | 9/10 |
| unknown | 6 | 4/6 | 4/6 |
| application | 5 | 1/5 | 1/5 |
| network | 2 | 2/2 | 2/2 |
| dns | 2 | 2/2 | 2/2 |
| firewall | 2 | 2/2 | 2/2 |
| filesystem | 1 | 1/1 | 1/1 |
| storage | 1 | 1/1 | 1/1 |

## Per-incident (three methods)

| Title | Lean | Fed | OpenObserve | L↔F | L↔O | F↔O | Triple |
|-------|------|-----|-------------|-----|-----|-----|--------|
| starter_high_cpu | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | Y | Y | Y | Y |
| starter_high_cpu | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | Y | Y | Y | Y |
| starter_high_cpu | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | Y | Y | Y | Y |
| database_down | `database`/`database_down` | `database`/`database_down` | `database`/`database_down` | Y | Y | Y | Y |
| db_primary_down | `database`/`db_primary_down` | `database`/`db_primary_down` | `database`/`db_primary_down` | Y | Y | Y | Y |
| db_primary_down | `database`/`db_primary_down` | `database`/`db_primary_down` | `database`/`db_primary_down` | Y | Y | Y | Y |
| db_primary_down | `database`/`db_primary_down` | `database`/`db_primary_down` | `unknown`/`db_primary_down` | Y | N | N | N |
| pg_ordersdb_outage | `database`/`pg_ordersdb_outage` | `database`/`pg_ordersdb_outage` | `database`/`pg_ordersdb_outage` | Y | Y | Y | Y |
| pg_ordersdb_down | `database`/`pg_ordersdb_down` | `database`/`pg_ordersdb_down` | `database`/`pg_ordersdb_down` | Y | Y | Y | Y |
| pg_ordersdb_outage3 | `database`/`pg_ordersdb_outage` | `database`/`pg_ordersdb_outage` | `database`/`pg_ordersdb_outage` | Y | Y | Y | Y |
| pg_svc_down | `database`/`pg_svc_down` | `database`/`pg_svc_down` | `database`/`pg_svc_down` | Y | Y | Y | Y |
| pg_svc_down2 | `database`/`pg_svc_down2` | `database`/`pg_svc_down2` | `database`/`pg_svc_down2` | Y | Y | Y | Y |
| pg_db_down_dim | `database`/`pg_db_down_dim` | `database`/`pg_db_down_dim` | `database`/`pg_db_down_dim` | Y | Y | Y | Y |
| orders_service_surge on app-prod-01 | `unknown`/`orders_service_sur` | `unknown`/`orders_service_sur` | `database`/`orders_service_sur` | Y | N | N | N |
| pg_primary_down on pg-prod-01 | `database`/`pg_primary_down` | `database`/`pg_primary_down` | `unknown`/`pg_primary_down` | Y | N | N | N |
| net_link_saturation | `network`/`net_link_saturatio` | `network`/`net_link_saturatio` | `network`/`checkout_db_timeou` | Y | Y | Y | Y |
| net_link_saturation | `network`/`net_link_saturatio` | `network`/`net_link_saturatio` | `network`/`net_link_saturatio` | Y | Y | Y | Y |
| ecom_checkout_slo_breach | `dns`/`ecom_dns_aaaa_numa` | `dns`/`ecom_checkout_slo_` | `dns`/`ecom_checkout_slo_` | Y | Y | Y | Y |
| ecom_checkout_slo_breach | `dns`/`ecom_dns_aaaa_numa` | `dns`/`ecom_checkout_slo_` | `application`/`ecom_checkout_slo_` | Y | N | N | N |
| ecom_checkout_slo_breach on checkout | `dns`/`ecom_checkout_slo_` | `dns`/`ecom_checkout_slo_` | `application`/`ecom_checkout_slo_` | Y | N | N | N |
| ecom_payment_conn_exhaustion on paym | `application`/`ecom_payment_conn_` | `application`/`ecom_payment_conn_` | `application`/`ecom_payment_conn_` | Y | Y | Y | Y |
| ecom_dns_aaaa_numa on dns-resolver | `dns`/`ecom_dns_aaaa_numa` | `dns`/`ecom_dns_aaaa_numa` | `dns`/`ecom_dns_aaaa_numa` | Y | Y | Y | Y |
| ecom_checkout_slo_breach | `dns`/`ecom_dns_aaaa_numa` | `dns`/`ecom_checkout_slo_` | `application`/`ecom_checkout_slo_` | Y | N | N | N |
| sa_upload_slo | `filesystem`/`sa_inode_high` | `filesystem`/`sa_upload_slo` | `filesystem`/`sa_upload_slo` | Y | Y | Y | Y |
| sc_latency_slo | `unknown`/`sc_latency_slo` | `unknown`/`sc_latency_slo` | `application`/`sc_latency_slo` | Y | N | N | N |
| sd_notif_slo | `unknown`/`sd_notif_slo` | `unknown`/`sd_notif_slo` | `unknown`/`sd_notif_slo` | Y | Y | Y | Y |
| cio_host_cpu_high | `storage`/`cio_disk_io_stall` | `storage`/`cio_host_cpu_high` | `storage`/`cio_host_load_avg_` | Y | Y | Y | Y |
| pgw_checkout_tps_drop | `firewall`/`pgw_fw_443_denies` | `firewall`/`pgw_checkout_tps_d` | `firewall`/`pgw_esxi_443_no_re` | Y | Y | Y | Y |
| pgw_checkout_tps_drop | `firewall`/`pgw_fw_443_denies` | `firewall`/`pgw_checkout_tps_d` | `firewall`/`pgw_esxi_443_no_re` | Y | Y | Y | Y |

## Cases worth discussing

- **db_primary_down** (`3GABGbdhy3…`): Lean+Fed agree (database), OpenObserve differs (unknown) — OO snippet: db_primary_down…
- **orders_service_surge on app-prod-01** (`3GAJqvDUEt…`): Lean+Fed agree (unknown), OpenObserve differs (database) — OO snippet: PostgreSQL database connection pool exhaustion on pg-prod-01 during load surges …
- **pg_primary_down on pg-prod-01** (`3GAJqzTd0V…`): Lean+Fed agree (database), OpenObserve differs (unknown) — OO snippet: **Investigation halted** — the backend service required for RCA analysis is not …
- **ecom_checkout_slo_breach** (`3GARI4Zcuh…`): Fed crowns title; Lean picks other alert; OpenObserve title-shaped; Lean prefers other alert — OO snippet: SEV1 - Checkout success rate dropped 99.97%->97.2% in region=Region-B, payment_m…
- **ecom_checkout_slo_breach** (`3GARrIHDnf…`): Lean+Fed agree (dns), OpenObserve differs (application); Fed crowns title; Lean picks other alert; OpenObserve title-shaped; Lean prefers other alert — OO snippet: DNS resolution of the payment-provider endpoint via AAAA (IPv6) queries to serve…
- **ecom_checkout_slo_breach on checkout-service** (`3GASgKbtYc…`): Lean+Fed agree (dns), OpenObserve differs (application) — OO snippet: Node pool NP-17 rollout to node image 2026.06.18 introduced an IRQ-affinity misc…
- **ecom_checkout_slo_breach** (`3GAWT8nVjU…`): Lean+Fed agree (dns), OpenObserve differs (application); Fed crowns title; Lean picks other alert; OpenObserve title-shaped; Lean prefers other alert — OO snippet: Node image 2026.06.18 deployed to node pool NP-17 in prod-use1/Region-B on 2026-…
- **sa_upload_slo** (`3GAYuTBAC1…`): Fed crowns title; Lean picks other alert; OpenObserve title-shaped; Lean prefers other alert — OO snippet: Inode exhaustion on the /var/tmp mount at node-euw1-a3, caused by the export-rep…
- **sc_latency_slo** (`3GAYvCuRe6…`): Lean+Fed agree (unknown), OpenObserve differs (application) — OO snippet: Redis-node-3 cache node failure caused cache hit ratio to collapse from 98% to 6…
- **cio_host_cpu_high** (`3GAjVpGX95…`): Fed crowns title; Lean picks other alert — OO snippet: RAID controller Battery-Backed Unit (BBU) failure on io-node-02 storage node, wh…
- **pgw_checkout_tps_drop** (`3GAmXmWYoB…`): Fed crowns title; Lean picks other alert — OO snippet: A misconfigured firewall ACL rule (ACL-OUT-DMZ-NEW) deployed by admin@corp at 10…
- **pgw_checkout_tps_drop** (`3GAnUjT7Pi…`): Fed crowns title; Lean picks other alert — OO snippet: A misconfigured firewall ACL (ACL-OUT-DMZ-NEW, deployed by admin@corp at 13:36:5…

## How to reproduce

```bash
python3 benchmarking/benchmark/compare_openobserve.py
python3 benchmarking/dashboard/build_data.py
```

## Relation to UC-1..UC-5

The 5 ObserveOps scenarios remain the **GT bakeoff** (root-CI accuracy).
These 29 are a **three-method peer** track on live OpenObserve incidents.
Do not merge into a single X/34 accuracy fraction.

