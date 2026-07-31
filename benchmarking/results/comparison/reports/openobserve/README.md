# OpenObserve incident reports (fair Slice A)

Comprehensive `incident_report.json` / `.md` per UC, built from the
OpenObserve portal fair Analysis extracts — same folder shape as
[`../lean/`](../lean/) and [`../federated/`](../federated/).

**Generated:** 2026-07-28T10:32:11Z  
**UCs:** UC-1, UC-2, UC-3, UC-4, UC-5  
**Live fetch:** True  

Rebuild:

```bash
.venv/bin/python benchmarking/benchmark/build_oo_incident_reports.py
# optional refresh from portal:
OPENOBSERVE_USER=… OPENOBSERVE_PASSWORD=… \
  .venv/bin/python benchmarking/benchmark/build_oo_incident_reports.py --live-fetch
```

Canonical accuracy cite remains [`../OO/fair/`](../OO/fair/) +
[`../LEAN_FED_OO_COMPARISON.md`](../LEAN_FED_OO_COMPARISON.md).
