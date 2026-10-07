# OO fair — UC-5 (orders-api resource exhaustion / anti-FP)

**Incident:** `3H540hUYTQLWbBGwKuuJ52GTz2W` · `orders_api_p95_latency_high_UC5`  
**Alert:** symptom-only · `observeops_request_p95_latency_ms` · `uc_id='UC-5'`  
**Shift:** yes  
**Pack GT:** `orders-api` / `app_resource_exhaustion`  
**Lean / Fed:** ✓ / ✓  
**OO ✓?** **Yes**

## Blind extract (Potential Cause)

Database connection pool saturation (100% active) + JVM heap pressure (~96%) → cascading resource exhaustion in **orders-api** → p95 ~1800ms and ~18% errors.

## Notes

- Root CI matches GT (`orders-api`).
- **Anti-FP pass:** did not blame healthy upstream infra.
- Only fair-run OO hit among UC-1..UC-5.

## Artifacts

- [`../_fair_extracts/UC-5_blind_extract.json`](../_fair_extracts/UC-5_blind_extract.json)
- [`../_fair_extracts/UC-5_fair_r4_analysis.md`](../_fair_extracts/UC-5_fair_r4_analysis.md)
