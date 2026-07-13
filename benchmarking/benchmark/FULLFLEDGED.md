# Full-Fledged Steps 1–3 RCA — Requirements

**Status:** **Complete** for Motadata ObserveOps (Corpus B). Historical checklist kept for audit; live status is in [TASKS.md](TASKS.md) and [`docs/ROADMAP.md`](../../docs/ROADMAP.md).

## Current vs target

| Step | Target | Status |
|------|--------|--------|
| **1 Corpus** | JSON schemas, `manifest.yaml`, 7-day metrics, topology hash | **Done** — `datasets/observeops/` |
| **2 Federated** | Panorama→Murphy→Nezha on typed graph; hop logs; N=20 repro | **Done** — fusion path; no lean-heuristic fallback |
| **3 Lean** | Best-first + info-gain + temporal; CARE; Tier 3 scoped causal; signatures; tests | **Done** — UC-1/UC-3 Tier 3; `lean_rca` packaged |

## Step 1 exit criteria

- [x] `datasets/observeops/manifest.yaml` with corpus version + topology hash
- [x] JSON schemas: topology, anomalies, ground_truth, symptom_seed, metrics
- [x] `validate_corpus.py` validates all schemas
- [x] `metrics/` contain 7-day time-series (30min interval)
- [x] `build_corpus.py` regenerates deterministically

## Step 2 exit criteria

- [x] `observeops_federated.py` maps bundle → Murphy store with causal propagation rules
- [x] Pipeline runs Panorama→Murphy→Nezha; writes `hop_logs.json` per run
- [x] `root_ci` from fusion path (logged overrides when needed)
- [x] `run_reproducibility.py --engine federated --n 20`
- [x] `murphy_posterior` / fallback reason in run_meta

## Step 3 exit criteria

- [x] `lean-pipeline/core_engine/lean/` — invocation graph, best-first, info-gain, temporal, CARE, causal
- [x] `lean-pipeline/core_engine/schema/observeops_topology.json`
- [x] `observeops/engine.py` uses lean core (no GT signature leak)
- [x] Signature inferred from decisive signals / hardened matchers
- [x] `evidentiary_tier` 1/2/3; `fallback_fired` when CARE runs; Tier 3 when causal verifies
- [x] Tests UC-1..UC-5 (+ signature + API tests)
- [x] `run_reproducibility.py --engine lean --n 20`

## Shared

- [x] Same corpus version for both engines
- [x] `compare.py` with reproducibility + four-axis (+ lean efficiency) columns
- [x] Do not modify ground truth between paired runs
