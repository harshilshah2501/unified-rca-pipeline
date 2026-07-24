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

**Three-way (Lean × Federated × OO):** [`LEAN_FED_OO_COMPARISON.md`](./LEAN_FED_OO_COMPARISON.md) — includes OO alert/past-incident caveats.

| UC | Lean | Federated | OpenObserve |
|----|------|-----------|-------------|
| UC-1 | [lean/UC-1](./lean/UC-1/incident_report.md) | [federated/UC-1](./federated/UC-1/incident_report.md) | [OO/uc1…](./OO/uc1_esxi_cpu_contention) |
| UC-2 | [lean/UC-2](./lean/UC-2/incident_report.md) | [federated/UC-2](./federated/UC-2/incident_report.md) | [OO/uc2…](./OO/uc2_core_switch_link_failure) |
| UC-3 | [lean/UC-3](./lean/UC-3/incident_report.md) | [federated/UC-3](./federated/UC-3/incident_report.md) | [OO/uc3…](./OO/uc3_datastore_storage_contention) |
| UC-4 | [lean/UC-4](./lean/UC-4/incident_report.md) | [federated/UC-4](./federated/UC-4/incident_report.md) | [OO/uc4…](./OO/uc4_guest_os_resource_exhaustion) |
| UC-5 | [lean/UC-5](./lean/UC-5/incident_report.md) | [federated/UC-5](./federated/UC-5/incident_report.md) | [OO/uc5…](./OO/uc5_orders_api_resource_exhaustion) |

```bash
.venv/bin/python ingestion-poc/adapters/synthesize_observeops_uc_multimodal.py
.venv/bin/python benchmarking/benchmark/comprehensive_rca_report.py \
  --pack datasets/observeops/UC-1 \
  --raw datasets/observeops/UC-1/raw \
  --verdict benchmarking/results/lean/UC-1/run-adr001-rerun-20260723/verdict.json \
  --out-dir benchmarking/results/comparison/reports/lean/UC-1
```
