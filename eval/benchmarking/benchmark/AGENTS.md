# ObserveOps Benchmark — Agent Continuation Guide

Orchestrates the **4-step federated vs lean comparison** on Corpus B (`datasets/observeops/`).

**ObserveOps status (2026-07-13):** Critical path complete — lean is primary ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)). Use this guide to **rerun** bakeoffs or extend optional work (Phase C/E, B5), not to rediscover the engine choice.

## Current pipeline

```
Step 1  datasets/observeops/                         DONE
Step 2  benchmarking/benchmark/run_federated.py   →  results/federated/
Step 3  benchmarking/benchmark/run_lean.py        →  results/lean/
Step 4  benchmarking/benchmark/compare.py         →  results/comparison/
```

## Full-fledged checklist

See [FULLFLEDGED.md](FULLFLEDGED.md) (all ObserveOps items checked) and [TASKS.md](TASKS.md).

## For agents resuming

1. Read [TASKS.md](TASKS.md) and [`docs/ROADMAP.md`](../../docs/ROADMAP.md)
2. Create venv if missing:
   `python3 -m venv .venv && .venv/bin/pip install -r federated-pipeline/requirements.txt -r federated-pipeline/murphy/requirements.txt`
3. Validate: `python3 benchmarking/benchmark/validate_corpus.py`
4. Matched bakeoff: `./benchmarking/benchmark/run_bakeoff.sh`
5. Never change corpus files between Step 2 and Step 3 for the same `run_id`
6. Product RCA API (lean): `PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report`

## Step 2 — Federated

- Engine: [federated-pipeline/poc/orchestrator.py](../../federated-pipeline/poc/orchestrator.py)
- Adapter: [adapters/observeops_federated.py](adapters/observeops_federated.py)

```bash
python3 benchmarking/benchmark/run_federated.py --all --run-id my-run
```

## Step 3 — Lean

- Engine: [lean-pipeline/core_engine/observeops/](../../lean-pipeline/core_engine/observeops/)
- API: [lean-pipeline/lean_rca/](../../lean-pipeline/lean_rca/)

```bash
python3 benchmarking/benchmark/run_lean.py --all --run-id my-run
```

## Step 4 — Compare

```bash
python3 benchmarking/benchmark/compare.py --run-id my-run
```

Writes `benchmarking/results/comparison/COMPARISON.md` using
[COMPARISON_BENCHMARK.md](../../datasets/observeops/COMPARISON_BENCHMARK.md).
