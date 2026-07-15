# OpenObserve Option B — Convention GT Scoreboard

**Generated:** `2026-07-15T07:39:57.261864+00:00`  
**Corpus:** `/root/Harshil-PoCs/Unified-RCA/datasets/openobserve_incidents/v1`  
**Mode:** score Lean · Federated · OpenObserve vs **convention baseline**  
**Accuracy N:** 10 confident labels · **Excluded:** 2 ambiguous  
**Labeling:** `solo_dual_pass` (solo dual-pass — not independent human A/B)  
**Best on this baseline:** `lean`  
**Ranking (layer → root):** lean > federated > openobserve

## What we measured

For each eligible incident we treat the adjudicated `root_layer` + `root_alert` as the **scoring baseline** (Murphy language: close to *operator-decided ground truth* / *true root cause entity* for Top-1 — **not** objective physics truth).

| Hit type | Rule |
|----------|------|
| Layer | method layer == baseline `root_layer` |
| Root alert | method root equals / contains baseline `root_alert` |
| Both | layer and root hit |

### Caveats (read before over-claiming)

1. Solo dual-pass labels — stronger if re-done with two independent humans.
2. Lean / Federated here are **principle analyzers**, not full UC typed-CI engines.
3. OpenObserve is method #3 (platform narrative), scored like the others.
4. One baseline root is a CI id (`redis-node-3`) with no matching alert name — root-alert hits are hard for all methods there; layer still scorable.

## Scoreboard (eligible only)

| Metric | Lean | Federated | OpenObserve |
|--------|------|-----------|-------------|
| **Layer accuracy** | **80%** (8/10) | **80%** (8/10) | **80%** (8/10) |
| **Root-alert accuracy** | **90%** (9/10) | **40%** (4/10) | **30%** (3/10) |
| Layer **and** root | 80% | 30% | 20% |

### Split: multi-trigger vs single-trigger (eligible)

Multi n=7 · Single n=3

| Slice | Lean layer | Fed layer | OO layer | Lean root | Fed root | OO root |
|-------|------------|-----------|----------|-----------|----------|---------|
| Multi-trigger | 86% | 86% | 86% | 86% | 14% | 0% |
| Single-trigger | 67% | 67% | 67% | — | — | — |

### Title-pick on eligible multi-trigger (behavior)

Lower usually better when the incident title is a decoy symptom.

| Lean | Federated | OpenObserve |
|------|-----------|-------------|
| 29% | 100% | 57% |

## Per-incident results (all 12)

| Title | GT layer / alert | Lean | Fed | OO | L✓ | F✓ | O✓ | Acc? |
|-------|------------------|------|-----|----|----|----|----|------|
| starter_high_cpu | `compute` / `starter_high_cpu` | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | `unknown`/`starter_high_cpu` | N/Y | N/Y | N/Y | no |
| database_down | `database` / `database_down` | `database`/`database_down` | `database`/`database_down` | `database`/`database_down` | Y/Y | Y/Y | Y/Y | Y |
| db_primary_down | `database` / `db_primary_down` | `database`/`db_primary_down` | `database`/`db_primary_down` | `unknown`/`db_primary_down` | Y/Y | Y/Y | N/Y | no |
| orders_service_surge on app-prod-0 | `application` / `orders_service_surge` | `unknown`/`orders_service_s` | `unknown`/`orders_service_s` | `database`/`orders_service_s` | N/Y | N/Y | N/Y | Y |
| net_link_saturation | `network` / `net_link_saturation` | `network`/`net_link_saturat` | `network`/`net_link_saturat` | `network`/`checkout_db_time` | Y/Y | Y/Y | Y/N | Y |
| ecom_checkout_slo_breach | `dns` / `ecom_dns_aaaa_numa` | `dns`/`ecom_dns_aaaa_nu` | `dns`/`ecom_checkout_sl` | `dns`/`ecom_checkout_sl` | Y/Y | Y/N | Y/N | Y |
| ecom_checkout_slo_breach | `dns` / `ecom_dns_aaaa_numa` | `dns`/`ecom_dns_aaaa_nu` | `dns`/`ecom_checkout_sl` | `application`/`ecom_checkout_sl` | Y/Y | Y/N | N/N | Y |
| ecom_dns_aaaa_numa on dns-resolver | `dns` / `ecom_dns_aaaa_numa` | `dns`/`ecom_dns_aaaa_nu` | `dns`/`ecom_dns_aaaa_nu` | `dns`/`ecom_dns_aaaa_nu` | Y/Y | Y/Y | Y/Y | Y |
| sa_upload_slo | `filesystem` / `sa_inode_high` | `filesystem`/`sa_inode_high` | `filesystem`/`sa_upload_slo` | `filesystem`/`sa_upload_slo` | Y/Y | Y/N | Y/N | Y |
| sc_latency_slo | `application` / `redis-node-3` | `unknown`/`sc_latency_slo` | `unknown`/`sc_latency_slo` | `application`/`sc_latency_slo` | N/N | N/N | Y/N | Y |
| cio_host_cpu_high | `storage` / `cio_disk_io_stall` | `storage`/`cio_disk_io_stal` | `storage`/`cio_host_cpu_hig` | `storage`/`cio_host_load_av` | Y/Y | Y/N | Y/N | Y |
| pgw_checkout_tps_drop | `firewall` / `pgw_fw_443_denies` | `firewall`/`pgw_fw_443_denie` | `firewall`/`pgw_checkout_tps` | `firewall`/`pgw_esxi_443_no_` | Y/Y | Y/N | Y/N | Y |

## Cases that teach something

- **orders_service_surge on app-prod-01** (`single_app_surge_vs_db_layer`): lean layer miss (unknown≠application); federated layer miss (unknown≠application); openobserve layer miss (database≠application)
- **net_link_saturation** (`multi_network_topo`): openobserve layer ok but wrong root (`checkout_db_timeouts`≠`net_link_saturation`)
- **ecom_checkout_slo_breach** (`decoy_multi_slo_title_dns_topo`): federated layer ok but wrong root (`ecom_checkout_slo_breach`≠`ecom_dns_aaaa_numa`); openobserve layer ok but wrong root (`ecom_checkout_slo_breach`≠`ecom_dns_aaaa_numa`); Fed crowns title; Lean does not
- **ecom_checkout_slo_breach** (`decoy_multi_lean_fed_disagree_oo`): federated layer ok but wrong root (`ecom_checkout_slo_breach`≠`ecom_dns_aaaa_numa`); openobserve layer miss (application≠dns); Fed crowns title; Lean does not
- **sa_upload_slo** (`decoy_multi_slo_filesystem`): federated layer ok but wrong root (`sa_upload_slo`≠`sa_inode_high`); openobserve layer ok but wrong root (`sa_upload_slo`≠`sa_inode_high`); Fed crowns title; Lean does not
- **sc_latency_slo** (`multi_app_slo_lean_fed_disagree_oo`): lean layer miss (unknown≠application); federated layer miss (unknown≠application); openobserve layer ok but wrong root (`sc_latency_slo`≠`redis-node-3`)
- **cio_host_cpu_high** (`decoy_multi_cpu_title_storage`): federated layer ok but wrong root (`cio_host_cpu_high`≠`cio_disk_io_stall`); openobserve layer ok but wrong root (`cio_host_load_avg_high`≠`cio_disk_io_stall`); Fed crowns title; Lean does not
- **pgw_checkout_tps_drop** (`multi_firewall_topo`): federated layer ok but wrong root (`pgw_checkout_tps_drop`≠`pgw_fw_443_denies`); openobserve layer ok but wrong root (`pgw_esxi_443_no_return`≠`pgw_fw_443_denies`); Fed crowns title; Lean does not

### Excluded from accuracy

- **starter_high_cpu** (`3G8HsK79Ff…`, ambiguous): Single stub alert (mock CPU>80); no co-firing signals, topology, or narrative. Convention root = title alert only — too thin for accuracy scoring.
- **db_primary_down** (`3GABGbdhy3…`, ambiguous): Incident has empty triggers, empty alerts list, and no platform narrative — only title db_primary_down. Title-only convention; exclude from accuracy.

## By stratum (eligible layer / root hits)

| Stratum | n | Lean L/R | Fed L/R | OO L/R |
|---------|---|----------|---------|--------|
| decoy_multi_cpu_title_storage | 1 | 1/1 | 1/0 | 1/0 |
| decoy_multi_lean_fed_disagree_oo | 1 | 1/1 | 1/0 | 0/0 |
| decoy_multi_slo_filesystem | 1 | 1/1 | 1/0 | 1/0 |
| decoy_multi_slo_title_dns_topo | 1 | 1/1 | 1/0 | 1/0 |
| multi_app_slo_lean_fed_disagree_oo | 1 | 0/0 | 0/0 | 1/0 |
| multi_firewall_topo | 1 | 1/1 | 1/0 | 1/0 |
| multi_network_topo | 1 | 1/1 | 1/1 | 1/0 |
| single_app_surge_vs_db_layer | 1 | 0/1 | 0/1 | 0/1 |
| single_database_with_narrative | 1 | 1/1 | 1/1 | 1/1 |
| single_dns | 1 | 1/1 | 1/1 | 1/1 |

## Deep insights & conclusion

Full narrative: [`GT_ANALYSIS.md`](./GT_ANALYSIS.md)

## How to reproduce

```bash
python3 benchmarking/benchmark/score_openobserve_gt.py
```

Related: peer-only (no GT) → `compare_openobserve.py` · UC GT bakeoff → `results/comparison/`.

