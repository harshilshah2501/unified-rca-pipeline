# Benchmarking — same-dataset bakeoff

**What this folder is for:** run **both** pipelines on the **same** ObserveOps corpus
([`docs/rca-use-cases-only.md`](../docs/rca-use-cases-only.md) → `datasets/observeops/`), keep per-engine run artifacts, then produce a **comparative analysis**.

**Motadata outcome:** lean is the primary engine ([ADR-001](../docs/ADR-001-lean-primary-engine.md), [DECISION.md](results/comparison/DECISION.md)). Federated remains for bakeoff comparison and optional microservice work.

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
| [`capacity/`](capacity/) | Infra EPS probes (Dragonfly/Redis) — separate from UC bakeoff |

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
| Verifiability | Evidence trail / tier / CARE·causal notes |
| Efficiency | Observations; lean best-first vs naive BFS when present |
| Per-UC / overall winner | Accuracy first, then fewer observations, then explicit latency |

Latest report: [`results/comparison/COMPARISON.md`](results/comparison/COMPARISON.md)

Contract: [`datasets/observeops/COMPARISON_BENCHMARK.md`](../datasets/observeops/COMPARISON_BENCHMARK.md)

## Capacity (separate)

Infra throughput is **not** part of the UC bakeoff:

```bash
PYTHONPATH=federated-pipeline:. python -m poc.benchmarks.phase0_dragonfly \
  --port 6380 --workers 4 --pipeline-size 128 --seconds 20 \
  --output benchmarking/capacity/phase0_latest.json
```
