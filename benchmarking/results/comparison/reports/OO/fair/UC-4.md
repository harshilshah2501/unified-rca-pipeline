# OO fair — UC-4 (guest OS resource exhaustion)

**Incident:** `3H543H5FOsjMsNlfp197LYU8FqJ` · `orders_api_5xx_error_rate_high_UC4`  
**Alert:** symptom-only · `observeops_error_rate_5xx` · `uc_id='UC-4'`  
**Shift:** yes  
**Pack GT:** `guest-os-vm-app-01` / `os_resource_exhaustion`  
**Lean / Fed:** ✓ / ✓  
**OO ✓?** **No**

## Blind extract (Potential Cause)

Sudden elevation of orders-api error rate 2%→42%; coinciding with possible deploy/config/infra or upstream failure; traces/logs not captured — **precise failure point unknown**.

## Notes

- `observeops_uc_uc4` log stream was stuck “being deleted” during push; metrics alert still fired.
- Did not name guest OS / OOM / filesystem exhaustion.

## Artifacts

- [`../_fair_extracts/UC-4_blind_extract.json`](../_fair_extracts/UC-4_blind_extract.json)
- [`../_fair_extracts/UC-4_fair_r4_analysis.md`](../_fair_extracts/UC-4_fair_r4_analysis.md)
