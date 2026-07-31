# Push ObserveOps UC telemetry → OpenObserve

**Purpose:** Provision the same UC-1..UC-5 telemetry Lean/Federated used so OpenObserve can produce comparable gold OO incident reports.

**Credentials:** do **not** commit. Use env vars.

## Fair comparison (recommended)

Use the **exact** Lean shared-detect `parity_corpus` from run `adr001-rerun-20260723` — original timestamps, full 7-day metrics, no shift/truncation.

Requires `ZO_INGEST_ALLOWED_UPTO` large enough for pack dates (~Jul 3–10, 2026). This Motadata host is set to **365 days** (`8760` hours).

**Slice A (trustworthy Lean×Fed×OO):** add `--fair` so payloads omit `root_ci_gt` / `signature_gt` and use symptom scenario labels. Then use symptom-only alerts — see [`docs/SLICE_A_OO_UC_FAIRNESS.md`](../../docs/SLICE_A_OO_UC_FAIRNESS.md).

**Fair run result (2026-07-27):** OO root **1/5** vs Lean/Fed **5/5** — [`LEAN_FED_OO_COMPARISON.md`](../../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) · [`OO/fair/`](../../benchmarking/results/comparison/reports/OO/fair/). Portal Analysis needed `shift-to-now` (not absolute Jul-10 times).

```bash
export OPENOBSERVE_URL=http://172.16.14.77:5080
export OPENOBSERVE_ORG=default
export OPENOBSERVE_USER='admin@motadata.com'
export OPENOBSERVE_PASSWORD='…'

# Wipe earlier streams, push parity inputs WITHOUT GT coaching tags
.venv/bin/python ingestion-poc/adapters/push_observeops_uc_to_openobserve.py \
  --parity-run-id adr001-rerun-20260723 \
  --fair \
  --purge-stale \
  --out-summary benchmarking/results/comparison/oo_push_summary_fair.json
```

Without `--fair` (legacy / debug only — **not** for OO Localize claims):

```bash
.venv/bin/python ingestion-poc/adapters/push_observeops_uc_to_openobserve.py \
  --parity-run-id adr001-rerun-20260723 \
  --purge-stale
```

Summary: `benchmarking/results/comparison/oo_push_summary_fair.json` (fair) or `oo_push_summary.json`.

Zip of the same inputs: `benchmarking/results/comparison/observeops_UC1-UC5_lean_fed_parity_inputs.zip`.

### What parity mode pushes

| Signal | Source in parity_corpus | Notes |
|--------|-------------------------|--------|
| Metrics | `metrics/*.json` | Full series (~10.8k points) |
| Logs | events + crossed anomalies + seed (+ changes if present) | Lean had no `raw/logs`; these are the evidence Lean consumed |
| Spans | none in parity_corpus | Lean/Fed diagnosis did not use spans |

Tags (always): `uc_id`, `corpus=observeops`, `parity_input=true`.  
With `--fair`: `fair_push=true`, scenario = `UC-N symptom <seed_ci>/<signal>` — **no** `root_ci_gt` / `signature_gt`.  
Without `--fair`: also tags `root_ci_gt`, `signature_gt` (eval convenience only; contaminates OO if copied into alerts).

## After push (OO UI)

1. Streams → `observeops_uc_uc1` … `uc5` + `observeops_*` metrics.
2. Time range around **`2026-07-10T10:00:00Z`**. Filter `uc_id` / `parity_input=true`.
3. Run OO RCA per UC for gold reports.

## Workaround mode (only if ingest window is too small)

```bash
.venv/bin/python ingestion-poc/adapters/push_observeops_uc_to_openobserve.py --shift-to-now --retain-hours 4.5
```

Not valid for fair Lean/Fed comparison (absolute times differ; metrics truncated).
