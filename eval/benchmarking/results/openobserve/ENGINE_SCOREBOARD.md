# OpenObserve — Lean/Federated engine pack scoreboard

**Generated:** `2026-07-15T11:26:42.876768+00:00`  
**Corpus:** `/root/Harshil-PoCs/Unified-RCA/datasets/openobserve_incidents/v1/engine_packs`  
**Run filter:** `oo-bakeoff-v1`  
**Accuracy N:** 24 eligible · **Excluded:** 5  
**Best on Accuracy:** `tie`

## Pillars in scope

| Pillar | Status |
|--------|--------|
| **Accuracy** | scored (`root_ci` vs Option B `root_alert`) |
| **Verifiability** | proxies from verdict (tier / fallback / causal) |
| **Efficiency** | proxies from verdict (observations / walk ratio) |
| **Reproducibility** | N-run bit-identical `verdict.json` hashes |

Accuracy vs Option B. Verifiability/Efficiency from verdicts. Reproducibility = N-run bit-identical verdict hashes (when report present).

## Reproducibility (N-run hash stability)

Per pack: N runs, SHA-256(verdict.json); 100% iff all hashes identical.

| Engine | Overall | N | Packs scored |
|--------|---------|---|--------------|
| Lean | **100%** | 20 | 24 |
| Federated | **75%** | 20 | 24 |

## Accuracy (eligible only)

| Engine | Root-CI accuracy | Hits |
|--------|------------------|------|
| Lean | **62%** | 15/24 |
| Federated | **62%** | 15/24 |

## Verifiability proxies (eligible, present verdicts)

| Metric | Lean | Federated |
|--------|------|-----------|
| Fallback rate | 46% | 0% |
| Avg evidentiary tier | 1.71 | 1.00 |
| Causal verified rate | 25% | — |

## Efficiency proxies (eligible)

| Metric | Lean | Federated |
|--------|------|-----------|
| Avg observations | 2.17 | 5.00 |
| Avg obs_to_convergence | 0.79 | — |
| Avg efficiency_ratio | 0.79 | — |

## Per-incident (all packs)

| Title | GT root | Lean | Fed | L✓ | F✓ | Acc? |
|-------|---------|------|-----|----|----|------|
| starter_high_cpu | `starter_high_cpu` | `starter_high_cpu` | `starter_high_cpu` | Y | Y | no |
| starter_high_cpu | `starter_high_cpu` | `starter_high_cpu` | `starter_high_cpu` | Y | Y | no |
| starter_high_cpu | `starter_high_cpu` | `starter_high_cpu` | `starter_high_cpu` | Y | Y | no |
| database_down | `database_down` | `database_down` | `database_down` | Y | Y | Y |
| db_primary_down | `db_primary_down` | `db_primary_down` | `db_primary_down` | Y | Y | Y |
| db_primary_down | `db_primary_down` | `db_primary_down` | `db_primary_down` | Y | Y | Y |
| db_primary_down | `db_primary_down` | `db_primary_down` | `db_primary_down` | Y | Y | no |
| pg_ordersdb_outage | `pg_ordersdb_outage` | `pg_ordersdb_outage` | `pg_ordersdb_outage` | Y | Y | Y |
| pg_ordersdb_down | `pg_ordersdb_down` | `pg_ordersdb_down` | `pg_ordersdb_down` | Y | Y | Y |
| pg_ordersdb_outage3 | `pg_ordersdb_outage3` | `pg_ordersdb_outage3` | `pg_ordersdb_outage3` | Y | Y | Y |
| pg_svc_down | `pg_svc_down` | `pg_svc_down` | `pg_svc_down` | Y | Y | Y |
| pg_svc_down2 | `pg_svc_down2` | `pg_svc_down2` | `pg_svc_down2` | Y | Y | Y |
| pg_db_down_dim | `pg_db_down_dim` | `pg_db_down_dim` | `pg_db_down_dim` | Y | Y | Y |
| orders_service_surge on app-prod-01 | `orders_service_surge` | `orders_service_surge` | `orders_service_surge` | Y | Y | Y |
| pg_primary_down on pg-prod-01 | `pg_primary_down` | `pg_primary_down` | `pg_primary_down` | Y | Y | Y |
| net_link_saturation | `net_link_saturation` | `checkout_db_timeouts` | `net_link_saturation` | N | Y | Y |
| net_link_saturation | `net_link_saturation` | `checkout_db_timeouts` | `net_link_saturation` | N | Y | Y |
| ecom_checkout_slo_breach | `ecom_dns_aaaa_numa` | `ecom_checkout_slo_brea` | `ecom_checkout_slo_brea` | N | N | Y |
| ecom_checkout_slo_breach | `ecom_dns_aaaa_numa` | `ecom_checkout_slo_brea` | `ecom_checkout_slo_brea` | N | N | Y |
| ecom_checkout_slo_breach on checkout | `ecom_checkout_slo_breach` | `ecom_checkout_slo_brea` | `ecom_checkout_slo_brea` | Y | Y | no |
| ecom_payment_conn_exhaustion on paym | `ecom_payment_conn_exhaustion` | `ecom_payment_conn_exha` | `ecom_payment_conn_exha` | Y | Y | Y |
| ecom_dns_aaaa_numa on dns-resolver | `ecom_dns_aaaa_numa` | `ecom_dns_aaaa_numa` | `ecom_dns_aaaa_numa` | Y | Y | Y |
| ecom_checkout_slo_breach | `ecom_dns_aaaa_numa` | `ecom_checkout_slo_brea` | `ecom_checkout_slo_brea` | N | N | Y |
| sa_upload_slo | `sa_inode_high` | `sa_inode_high` | `sa_upload_slo` | Y | N | Y |
| sc_latency_slo | `redis-node-3` | `sc_db_cpu` | `sc_latency_slo` | N | N | Y |
| sd_notif_slo | `sd_tls_fail` | `sd_notif_slo` | `sd_notif_slo` | N | N | Y |
| cio_host_cpu_high | `cio_disk_io_stall` | `cio_disk_io_stall` | `cio_host_cpu_high` | Y | N | Y |
| pgw_checkout_tps_drop | `pgw_fw_443_denies` | `pgw_checkout_tps_drop` | `pgw_checkout_tps_drop` | N | N | Y |
| pgw_checkout_tps_drop | `pgw_fw_443_denies` | `pgw_checkout_tps_drop` | `pgw_checkout_tps_drop` | N | N | Y |

## How to reproduce

```bash
python3 benchmarking/benchmark/project_oo_engine_packs.py
.venv/bin/python benchmarking/benchmark/run_oo_engine_bakeoff.py
python3 benchmarking/benchmark/score_oo_engine_bakeoff.py
```

Peer track (no engine packs): `compare_openobserve.py` · Convention Accuracy (alert heuristics): `score_openobserve_gt.py`.

