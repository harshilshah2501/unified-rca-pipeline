# Federated vs Lean — Comparative Analysis

**Corpus:** `datasets/observeops` (identical bundles for both engines)
**Generated:** `2026-07-28T07:19:56.919146Z`
**Matched run id:** `bakeoff-20260728T071930Z`

## Verdict

**Overall better on this corpus: `lean`**

Both engines are 5/5 on root-CI accuracy and signatures; lean wins more per-UC tie-breaks on observation count (4 vs federated 1; ties=0).

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
| Verifiability | main 4/5; fallback 1; evidence 5/5 | main 3/5; fallback 2; evidence 5/5 |
| Efficiency | avg observations 5.40; avg RCA 4108.38 ms; avg detect 1.18 ms; avg system 4109.56 ms | avg observations 4.80; best-first 2.40 vs naive BFS 2.80 (ratio 1.12); avg RCA 1.05 ms; avg detect 1.65 ms; avg system 2.70 ms |

Reproducibility inputs: federated `benchmarking/results/reproducibility_federated_full-repro.json`; lean `benchmarking/results/reproducibility_lean_full-repro.json`.
Main path means `fallback_fired: false`; CARE sets fallback and may promote to Tier 3 when `causal_verified`.
Lean efficiency ratio = naive_bfs_expansions / max(obs_to_convergence, 1).
Parity profile: shared threshold detect (`detect_latency_ms` / `C_detect_ms`) + RCA (`latency_ms`); `system_latency_ms` = detect + RCA. See `docs/PIPELINE_PARITY.md`.

## Per use-case

| UC | Ground truth | Federated | Lean | Repro F/L | Verifiability F/L | Winner |
|----|--------------|-----------|------|-----------|---------------------|--------|
| UC-1 | `esxi-host-01` | `esxi-host-01` | `esxi-host-01` | 100.00%/100.00% | tier 1; main; evidence 6; sig Y / tier 3; CARE; causal Y; evidence 12; sig Y | **lean** |
| UC-2 | `switch-core-01:GigE0/2` | `switch-core-01:GigE0/2` | `switch-core-01:GigE0/2` | 0.00%/100.00% | tier 2; CARE; evidence 5; sig Y / tier 1; main; evidence 10; sig Y | **lean** |
| UC-3 | `datastore-01` | `datastore-01` | `datastore-01` | 0.00%/100.00% | tier 1; main; evidence 6; sig Y / tier 3; CARE; causal Y; evidence 11; sig Y | **federated** |
| UC-4 | `guest-os-vm-app-01` | `guest-os-vm-app-01` | `guest-os-vm-app-01` | 100.00%/100.00% | tier 1; main; evidence 3; sig Y / tier 1; main; evidence 7; sig Y | **lean** |
| UC-5 | `orders-api` | `orders-api` | `orders-api` | 0.00%/100.00% | tier 1; main; evidence 4; sig Y / tier 1; main; evidence 8; sig Y | **lean** |

## Efficiency and winner policy

Accuracy (root-CI match with UC-5 infrastructure false-positive guard), then fewer observations, then lower explicitly recorded latency; otherwise tie.

| UC | Fed observations | Lean observations | Lean best-first | Lean naive BFS | Ratio | Fed latency | Lean latency |
|----|------------------|-------------------|-----------------|----------------|-------|-------------|--------------|
| UC-1 | 6 | 6 | 3 | 3 | 1.00 | 9756.58 ms | 3.74 ms |
| UC-2 | 5 | 5 | 4 | 5 | 1.25 | 3229.13 ms | 0.44 ms |
| UC-3 | 5 | 6 | 3 | 4 | 1.33 | 6656.68 ms | 0.43 ms |
| UC-4 | 6 | 3 | 1 | 1 | 1.00 | 896.54 ms | 0.29 ms |
| UC-5 | 5 | 4 | 1 | 1 | 1.00 | 2.96 ms | 0.35 ms |

## Parity timings (shared detect + RCA)

| UC | C_detect | Fed RCA | Lean RCA | Fed system | Lean system | Hop-1 component |
|----|----------|---------|----------|------------|-------------|-----------------|
| UC-1 | 1.60 ms | 9756.58 ms | 3.74 ms | 9758.18 ms | 5.27 ms | `shared_threshold` |
| UC-2 | 0.83 ms | 3229.13 ms | 0.44 ms | 3229.96 ms | 2.07 ms | `shared_threshold` |
| UC-3 | 1.08 ms | 6656.68 ms | 0.43 ms | 6657.76 ms | 2.22 ms | `shared_threshold` |
| UC-4 | 1.10 ms | 896.54 ms | 0.29 ms | 897.64 ms | 1.61 ms | `shared_threshold` |
| UC-5 | 1.31 ms | 2.96 ms | 0.35 ms | 4.26 ms | 2.31 ms | `shared_threshold` |

## Detect classes + change near onset (D1/D2/D3)

| UC | by_anomaly_class | change_near_onset | changes in window |
|----|------------------|-------------------|-------------------|
| UC-1 | performance=1, resource=5 | Y | 2 |
| UC-2 | network=3, threshold=2 | N | 0 |
| UC-3 | performance=4, resource=2 | N | 0 |
| UC-4 | error_rate=1, resource=2 | N | 0 |
| UC-5 | error_rate=1, performance=1, resource=1, threshold=1 | N | 0 |

Class totals (Lean axis): `error_rate=2, network=3, performance=6, resource=10, threshold=3`; change_near_onset UCs: 1.

## How to reproduce

```bash
RUN_ID=bakeoff-$(date -u +%Y%m%dT%H%M%SZ)
# Prefer repo .venv (numpy + PyYAML). Shared threshold detect is on by default.
.venv/bin/python benchmarking/benchmark/run_lean.py --all --run-id "$RUN_ID"
.venv/bin/python benchmarking/benchmark/run_federated.py --all --run-id "$RUN_ID"
.venv/bin/python benchmarking/benchmark/compare.py --run-id "$RUN_ID"
```

Parity contract: [PIPELINE_PARITY.md](../../../docs/PIPELINE_PARITY.md)
Bakeoff metric contract: [COMPARISON_BENCHMARK.md](../../../datasets/observeops/COMPARISON_BENCHMARK.md)

Machine-readable: `comparison.json` alongside this file.
