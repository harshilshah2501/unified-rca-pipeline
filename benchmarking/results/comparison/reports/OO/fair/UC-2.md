# OO fair — UC-2 (core switch link failure)

**Incident:** `3H5422DwKJLI1NtoagESqnaoZ3v` · `orders_api_tcp_timeouts_high_UC2`  
**Alert:** symptom-only · `observeops_tcp_timeouts` · `uc_id='UC-2'`  
**Shift:** yes  
**Pack GT:** `switch-core-01:GigE0/2` / `link_failure`  
**Lean / Fed:** ✓ / ✓  
**OO ✓?** **No**

## Blind extract (Potential Cause)

OpenObserve API service unavailable at time of analysis — root cause unknown; no RCA produced.

## Notes

- Platform failure, not a wrong infra guess.
- Counts as miss for fair Localize accuracy.

## Artifacts

- [`../_fair_extracts/UC-2_blind_extract.json`](../_fair_extracts/UC-2_blind_extract.json)
- [`../_fair_extracts/UC-2_fair_r4_analysis.md`](../_fair_extracts/UC-2_fair_r4_analysis.md)
