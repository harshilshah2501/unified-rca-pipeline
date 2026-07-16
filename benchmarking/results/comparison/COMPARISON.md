# Federated vs Lean — Comparative Analysis

> **Canonical scoreboard** — regenerate with `python benchmarking/benchmark/compare.py --run-id bakeoff-phase-b-002` and `python benchmarking/dashboard/build_data.py`. Dashboard: [`benchmarking/dashboard/`](../dashboard/).

**Corpus:** `datasets/observeops` v1.1.0 (identical bundles for both engines; UC-1..UC-5 scored; UC-3b lean-only adversarial)
**Generated:** `2026-07-16T06:36:06.440601Z`
**Matched run id:** `bakeoff-phase-b-002`

## Verdict

**Overall better on this corpus: `lean`**

Both engines are 5/5 on root-CI accuracy and signatures; lean wins more per-UC tie-breaks on observation count (3 vs federated 1; ties=1).

## Scoreboard

| Metric | Federated | Lean |
|--------|-----------|------|
| Root-CI accuracy | **5/5** | **5/5** |
| Signature match | 5/5 | 5/5 |

## Four-axis scoreboard

| Axis | Federated | Lean |
|------|-----------|------|
| Accuracy | 5/5 root-CI; UC-5 infra FP 0 | 5/5 root-CI; UC-5 infra FP 0 |
| Reproducibility | 40.00% (5/5 reported) | 100.00% (5/5 reported) |
| Verifiability | main 5/5; fallback 0; evidence 5/5 | main 3/5; fallback 2; evidence 5/5 |
| Efficiency | avg observations 5.60; avg latency — | avg observations 5.00; best-first 2.40 vs naive BFS 2.80 (ratio 1.12); avg latency — |

Reproducibility inputs: federated `benchmarking/results/reproducibility_federated_full-repro.json`; lean `benchmarking/results/reproducibility_lean_full-repro.json`.
Main path means `fallback_fired: false`; CARE sets fallback and may promote to Tier 3 when `causal_verified`.
Lean efficiency ratio = naive_bfs_expansions / max(obs_to_convergence, 1).
Latency is shown only when a run's `run_meta.json` explicitly records a latency or hop-total field.

## Per use-case

| UC | Ground truth | Federated | Lean | Repro F/L | Verifiability F/L | Winner |
|----|--------------|-----------|------|-----------|---------------------|--------|
| UC-1 | `esxi-host-01` | `esxi-host-01` | `esxi-host-01` | 100.00%/100.00% | tier 1; main; evidence 6; sig Y / tier 3; CARE; causal Y; evidence 6; sig Y | **tie** |
| UC-2 | `switch-core-01:GigE0/2` | `switch-core-01:GigE0/2` | `switch-core-01:GigE0/2` | 0.00%/100.00% | tier 1; main; evidence 5; sig Y / tier 1; main; evidence 7; sig Y | **lean** |
| UC-3 | `datastore-01` | `datastore-01` | `datastore-01` | 0.00%/100.00% | tier 1; main; evidence 6; sig Y / tier 3; CARE; causal Y; evidence 6; sig Y | **federated** |
| UC-4 | `guest-os-vm-app-01` | `guest-os-vm-app-01` | `guest-os-vm-app-01` | 100.00%/100.00% | tier 1; main; evidence 4; sig Y / tier 1; main; evidence 6; sig Y | **lean** |
| UC-5 | `orders-api` | `orders-api` | `orders-api` | 0.00%/100.00% | tier 1; main; evidence 4; sig Y / tier 1; main; evidence 4; sig Y | **lean** |

## Efficiency and winner policy

Accuracy (root-CI match with UC-5 infrastructure false-positive guard), then fewer observations, then lower explicitly recorded latency; otherwise tie.

| UC | Fed observations | Lean observations | Lean best-first | Lean naive BFS | Ratio | Fed latency | Lean latency |
|----|------------------|-------------------|-----------------|----------------|-------|-------------|--------------|
| UC-1 | 6 | 6 | 3 | 3 | 1.00 | — | — |
| UC-2 | 6 | 5 | 4 | 5 | 1.25 | — | — |
| UC-3 | 5 | 6 | 3 | 4 | 1.33 | — | — |
| UC-4 | 6 | 4 | 1 | 1 | 1.00 | — | — |
| UC-5 | 5 | 4 | 1 | 1 | 1.00 | — | — |

## How to reproduce

```bash
RUN_ID=bakeoff-$(date -u +%Y%m%dT%H%M%SZ)
python3 benchmarking/benchmark/run_federated.py --all --run-id "$RUN_ID"
python3 benchmarking/benchmark/run_lean.py --all --run-id "$RUN_ID"
python3 benchmarking/benchmark/compare.py --run-id "$RUN_ID"
```

Contract: [COMPARISON_BENCHMARK.md](../../../datasets/observeops/COMPARISON_BENCHMARK.md)

Machine-readable: `comparison.json` alongside this file.
