# Benchmarking — same-dataset bakeoff

**What this folder is for:** run **both** pipelines on the **same** ObserveOps corpus
([`docs/rca-use-cases-only.md`](../docs/rca-use-cases-only.md) → `datasets/observeops/`), keep per-engine run artifacts, then produce a **comparative analysis**.

**Canonical scoreboard:** [`results/comparison/COMPARISON.md`](results/comparison/COMPARISON.md) · run IDs: [`results/comparison/RUN_IDS.md`](results/comparison/RUN_IDS.md)

**OpenObserve incidents (29) — same engines, different corpus:**

| Surface | What | Report |
|---------|------|--------|
| Peer (no GT) | Lean · Federated · OpenObserve agreement | [`results/openobserve/COMPARISON.md`](results/openobserve/COMPARISON.md) |
| Option B convention Accuracy | Alert-heuristic Lean/Fed/OO vs labels (n=29 · 24 scored) | [`GT_SCOREBOARD.md`](results/openobserve/GT_SCOREBOARD.md) |
| **Engine pack bakeoff** | Real Lean/Federated on projected packs; Accuracy + Verif/Eff proxies | [`ENGINE_SCOREBOARD.md`](results/openobserve/ENGINE_SCOREBOARD.md) |

Labels: [`../datasets/openobserve_incidents/v1/ground_truth/`](../datasets/openobserve_incidents/v1/ground_truth/). Packs: [`../datasets/openobserve_incidents/v1/engine_packs/`](../datasets/openobserve_incidents/v1/engine_packs/). Dashboard: [`dashboard/`](dashboard/). Do **not** fold OO + UC into one accuracy fraction.

Nezha Online Boutique / TrainTicket data under `datasets/nezha/` is reference-only and is **not** part of this bakeoff.

```
datasets/observeops/UC-1..UC-5     ← shared frozen dataset
        │
        ├─► federated-pipeline  →  results/federated/UC-*/run-<id>/
        │
        └─► lean-pipeline       →  results/lean/UC-*/run-<id>/
                                          │
                                          ▼
                               results/comparison/COMPARISON.md
                               results/comparison/comparison.json
```

## Layout

| Path | Purpose |
|------|---------|
| [`benchmark/`](benchmark/) | Runners: validate, federated, lean, compare |
| [`results/federated/`](results/federated/) | Individual federated verdicts per UC/run |
| [`results/lean/`](results/lean/) | Individual lean verdicts per UC/run |
| [`results/comparison/`](results/comparison/) | Side-by-side analysis + winner |
| [`capacity/`](capacity/) | Infra EPS probes (Dragonfly/Redis) — see [`../ingestion-poc/lab/`](../ingestion-poc/lab/) + `capacity/lab/` |
| [`dashboard/`](dashboard/) | **Comparative Web UI** (4 axes · 5 roadblocks · UC · OpenObserve) |

## One-command bakeoff

From repo root (matched `run_id` for both engines):

```bash
./benchmarking/benchmark/run_bakeoff.sh
# or: RUN_ID=my-bakeoff-001 ./benchmarking/benchmark/run_bakeoff.sh
```

## Step by step

```bash
# 0. Shared dataset must validate
python3 benchmarking/benchmark/validate_corpus.py

# 1. Federated alone
python3 benchmarking/benchmark/run_federated.py --all --run-id bakeoff-001

# 2. Lean alone (same corpus, same run id)
python3 benchmarking/benchmark/run_lean.py --all --run-id bakeoff-001

# 3. Comparative analysis (prefer --run-id so both sides match)
python3 benchmarking/benchmark/compare.py --run-id bakeoff-001
```

## What “better” means here

Scored identically for both engines against `datasets/observeops/*/ground_truth.json`. Prefer matched `--run-id` runs. Four-axis details: [COMPARISON_BENCHMARK.md](../datasets/observeops/COMPARISON_BENCHMARK.md) and [docs/README.md](../docs/README.md).

| Metric | Meaning |
|--------|---------|
| Root-CI accuracy | `verdict.root_ci == ground_truth.root_ci` (KPI with a floor — not “always 100% forever”) |
| Signature match | Fault signature matches GT |
| UC-5 false infra blame | Automatic fail if app fault blamed on infra |
| Reproducibility | N-run harness % (lean Mandatory bit-stable) |
| Verifiability | Evidence trail / tier / CARE·causal notes (see [GLOSSARY](../docs/GLOSSARY.md): lean may score lower **main-path %** when CARE fires but still wins audit narrative) |
| Efficiency | Observations; lean best-first vs naive BFS when present |
| Per-UC / overall winner | Accuracy first, then fewer observations, then explicit latency |

Latest report: [`results/comparison/COMPARISON.md`](results/comparison/COMPARISON.md)

Contract: [`datasets/observeops/COMPARISON_BENCHMARK.md`](../datasets/observeops/COMPARISON_BENCHMARK.md)

## OpenObserve engine packs (Lean / Federated)

```bash
# Project incidents → ObserveOps-shaped packs
python3 benchmarking/benchmark/project_oo_engine_packs.py

# Single bakeoff (uses .venv for Federated/numpy)
.venv/bin/python benchmarking/benchmark/run_oo_engine_bakeoff.py --run-id oo-bakeoff-v1

# Or drive engines directly
.venv/bin/python benchmarking/benchmark/run_lean.py \
  --corpus datasets/openobserve_incidents/v1/engine_packs --all --run-id oo-bakeoff-v1
.venv/bin/python benchmarking/benchmark/run_federated.py \
  --corpus datasets/openobserve_incidents/v1/engine_packs --all --run-id oo-bakeoff-v1

# Score Accuracy vs Option B + Verifiability/Efficiency proxies
python3 benchmarking/benchmark/score_oo_engine_bakeoff.py --run-id oo-bakeoff-v1
```

Reproducibility (N-run bit-identical `verdict.json` hashes):

```bash
# ObserveOps UC-1..UC-5 (legacy)
.venv/bin/python benchmarking/benchmark/run_reproducibility.py --engine lean --n 20 --prefix full-repro

# OO engine packs (Option B eligible)
.venv/bin/python benchmarking/benchmark/run_reproducibility.py \
  --engine lean --n 20 --prefix oo-repro-v1 \
  --corpus datasets/openobserve_incidents/v1/engine_packs --eligible-only
.venv/bin/python benchmarking/benchmark/run_reproducibility.py \
  --engine federated --n 20 --prefix oo-repro-v1 \
  --corpus datasets/openobserve_incidents/v1/engine_packs --eligible-only
python3 benchmarking/benchmark/score_oo_engine_bakeoff.py --run-id oo-bakeoff-v1
```

## Capacity (separate)

Infra throughput is **not** part of the UC bakeoff:

```bash
PYTHONPATH=federated-pipeline:. python -m poc.benchmarks.phase0_dragonfly \
  --port 6380 --workers 4 --pipeline-size 128 --seconds 20 \
  --output benchmarking/capacity/phase0_latest.json
```
