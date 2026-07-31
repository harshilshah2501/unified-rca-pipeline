# OO fair — UC-1 (ESXi CPU contention)

**Incident:** `3H538eGNAa0meaFoJwB2o8NnQMO` · `orders_api_p95_latency_high_UC1`  
**Alert:** symptom-only · `observeops_request_p95_latency_ms` · `uc_id='UC-1'`  
**Shift:** yes (`--fair --shift-to-now`)  
**Pack GT:** `esxi-host-01` / `cpu_contention`  
**Lean / Fed:** ✓ / ✓ (`adr001-rerun-20260723`)  
**OO ✓?** **No**

## Blind extract (Potential Cause)

payment-db (db-01) / checkout-service network connectivity (TCP retransmissions) + slow product catalog queries; orders-api 504 cascade; p95 1450ms.

## Notes

- Did cite observeops p95=1450.
- Did **not** cite `esxi-host-01` / `cpu_ready` / CPU contention.
- Narrative bled from unrelated org streams (`api_gateway_logs`, `checkout_service_logs`, `db_slow_query_logs`).

## Artifacts

- [`../_fair_extracts/UC1_blind_extract.json`](../_fair_extracts/UC1_blind_extract.json)
- [`../_fair_extracts/UC1_fair_r3_analysis.md`](../_fair_extracts/UC1_fair_r3_analysis.md)
