# ADR-001 ObserveOps UC reports (rerun + multimodal)

**Run id:** `adr001-rerun-20260723`  
**Corpus:** `datasets/observeops` UC-1..UC-5  
**Scoreboard:** [`../COMPARISON.md`](../COMPARISON.md)

Comprehensive `incident_report.md` / `.json` per engine × UC (**15/15** with synthesized events/logs/spans).

Multimodal evidence is GT-aligned synthetic add-on:
- `datasets/observeops/UC-N/events.json`
- `datasets/observeops/UC-N/raw/{logs,spans,manifest}.json`
- Generator: `ingestion-poc/adapters/synthesize_observeops_uc_multimodal.py`

Does **not** change `ground_truth.json` / topology / anomalies.

**Three-way (Lean × Federated × OO):** [`LEAN_FED_OO_COMPARISON.md`](./LEAN_FED_OO_COMPARISON.md)  

**Fair OO (2026-07-27):** root **1/5** (UC-5 only) · Lean/Fed **5/5** — canonical write-ups [`OO/fair/`](./OO/fair/). Contaminated 2026-07-24 OO files under [`OO/_historical_contaminated/`](./OO/_historical_contaminated/) only.

| UC | Lean | Federated | OpenObserve (fair) |
|----|------|-----------|---------------------|
| UC | Lean | Federated | OpenObserve (fair portal report) |
|----|------|-----------|----------------------------------|
| UC-1 | [lean/UC-1](./lean/UC-1/incident_report.md) | [federated/UC-1](./federated/UC-1/incident_report.md) | [openobserve/UC-1](./openobserve/UC-1/incident_report.md) · [OO/fair/UC-1](./OO/fair/UC-1.md) ✗ |
| UC-2 | [lean/UC-2](./lean/UC-2/incident_report.md) | [federated/UC-2](./federated/UC-2/incident_report.md) | [openobserve/UC-2](./openobserve/UC-2/incident_report.md) · [OO/fair/UC-2](./OO/fair/UC-2.md) ✗ |
| UC-3 | [lean/UC-3](./lean/UC-3/incident_report.md) | [federated/UC-3](./federated/UC-3/incident_report.md) | [openobserve/UC-3](./openobserve/UC-3/incident_report.md) · [OO/fair/UC-3](./OO/fair/UC-3.md) ✗ |
| UC-4 | [lean/UC-4](./lean/UC-4/incident_report.md) | [federated/UC-4](./federated/UC-4/incident_report.md) | [openobserve/UC-4](./openobserve/UC-4/incident_report.md) · [OO/fair/UC-4](./OO/fair/UC-4.md) ✗ |
| UC-5 | [lean/UC-5](./lean/UC-5/incident_report.md) | [federated/UC-5](./federated/UC-5/incident_report.md) | [openobserve/UC-5](./openobserve/UC-5/incident_report.md) · [OO/fair/UC-5](./OO/fair/UC-5.md) ✓ |

Rebuild OO reports from fair portal extracts:

```bash
.venv/bin/python benchmarking/benchmark/build_oo_incident_reports.py
# optional live refresh (needs OPENOBSERVE_USER / PASSWORD):
.venv/bin/python benchmarking/benchmark/build_oo_incident_reports.py --live-fetch
```


```bash
.venv/bin/python ingestion-poc/adapters/synthesize_observeops_uc_multimodal.py
.venv/bin/python benchmarking/benchmark/comprehensive_rca_report.py \
  --pack datasets/observeops/UC-1 \
  --raw datasets/observeops/UC-1/raw \
  --verdict benchmarking/results/lean/UC-1/run-adr001-rerun-20260723/verdict.json \
  --out-dir benchmarking/results/comparison/reports/lean/UC-1
```
