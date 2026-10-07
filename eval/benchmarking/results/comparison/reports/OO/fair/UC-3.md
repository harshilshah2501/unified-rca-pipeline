# OO fair — UC-3 (datastore storage contention)

**Incident:** `3H541z1bJNXfExUagp4l5AyAdGg` · `orders_api_p95_latency_high_UC3`  
**Alert:** symptom-only · `observeops_request_p95_latency_ms` · `uc_id='UC-3'`  
**Shift:** yes  
**Pack GT:** `datastore-01` / `storage_contention`  
**Lean / Fed:** ✓ / ✓  
**OO ✓?** **No**

## Blind extract (Potential Cause)

P95 for orders-api (UC-3) surged 400→2100 ms with simultaneous spikes in UC-1 and UC-5 → shared downstream bottleneck; **specific bottleneck not identified** (no DB/cache/traces/change history).

## Notes

- Symptom magnitude observed; datastore / storage contention not named.

## Artifacts

- [`../_fair_extracts/UC-3_blind_extract.json`](../_fair_extracts/UC-3_blind_extract.json)
- [`../_fair_extracts/UC-3_fair_r4_analysis.md`](../_fair_extracts/UC-3_fair_r4_analysis.md)
