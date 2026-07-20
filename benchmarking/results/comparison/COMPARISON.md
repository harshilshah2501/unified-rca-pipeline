# Federated vs Lean — Comparative Analysis

**Corpus:** `datasets/observeops` (identical bundles for both engines)
**Generated:** `2026-07-20T06:58:01.891134Z`
**Matched run id:** `bakeoff-parity-001`

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
| Efficiency | avg observations 5.40; avg RCA 4128.07 ms; avg detect 1.22 ms; avg system 4129.29 ms | avg observations 4.80; best-first 2.40 vs naive BFS 2.80 (ratio 1.12); avg RCA 0.80 ms; avg detect 1.03 ms; avg system 1.83 ms |

Reproducibility inputs: federated `benchmarking/results/reproducibility_federated_full-repro.json`; lean `benchmarking/results/reproducibility_lean_full-repro.json`.
Main path means `fallback_fired: false`; CARE sets fallback and may promote to Tier 3 when `causal_verified`.
Lean efficiency ratio = naive_bfs_expansions / max(obs_to_convergence, 1).
Parity profile: shared threshold detect (`detect_latency_ms`) + RCA (`latency_ms`); `system_latency_ms` = detect + RCA. See `docs/PIPELINE_PARITY.md`.

## Per use-case

| UC | Ground truth | Federated | Lean | Repro F/L | Verifiability F/L | Winner |
|----|--------------|-----------|------|-----------|---------------------|--------|
| UC-1 | `esxi-host-01` | `esxi-host-01` | `esxi-host-01` | 100.00%/100.00% | tier 1; main; evidence 6; sig Y / tier 3; CARE; causal Y; evidence 6; sig Y | **lean** |
| UC-2 | `switch-core-01:GigE0/2` | `switch-core-01:GigE0/2` | `switch-core-01:GigE0/2` | 0.00%/100.00% | tier 2; CARE; evidence 5; sig Y / tier 1; main; evidence 7; sig Y | **lean** |
| UC-3 | `datastore-01` | `datastore-01` | `datastore-01` | 0.00%/100.00% | tier 1; main; evidence 6; sig Y / tier 3; CARE; causal Y; evidence 6; sig Y | **federated** |
| UC-4 | `guest-os-vm-app-01` | `guest-os-vm-app-01` | `guest-os-vm-app-01` | 100.00%/100.00% | tier 1; main; evidence 3; sig Y / tier 1; main; evidence 5; sig Y | **lean** |
| UC-5 | `orders-api` | `orders-api` | `orders-api` | 0.00%/100.00% | tier 1; main; evidence 4; sig Y / tier 1; main; evidence 4; sig Y | **lean** |

## Efficiency and winner policy

Accuracy (root-CI match with UC-5 infrastructure false-positive guard), then fewer observations, then lower explicitly recorded latency; otherwise tie.

| UC | Fed observations | Lean observations | Lean best-first | Lean naive BFS | Ratio | Fed latency | Lean latency |
|----|------------------|-------------------|-----------------|----------------|-------|-------------|--------------|
| UC-1 | 6 | 6 | 3 | 3 | 1.00 | 9999.71 ms | 3.03 ms |
| UC-2 | 5 | 5 | 4 | 5 | 1.25 | 2837.41 ms | 0.25 ms |
| UC-3 | 5 | 6 | 3 | 4 | 1.33 | 6719.93 ms | 0.28 ms |
| UC-4 | 6 | 3 | 1 | 1 | 1.00 | 1079.39 ms | 0.24 ms |
| UC-5 | 5 | 4 | 1 | 1 | 1.00 | 3.91 ms | 0.21 ms |

## Parity timings (shared detect + RCA)

| UC | Detect | Fed RCA | Lean RCA | Fed system | Lean system | Hop-1 component |
|----|--------|---------|----------|------------|-------------|-----------------|
| UC-1 | 1.51 ms | 9999.71 ms | 3.03 ms | 10001.21 ms | 4.15 ms | `shared_threshold` |
| UC-2 | 0.70 ms | 2837.41 ms | 0.25 ms | 2838.10 ms | 1.01 ms | `shared_threshold` |
| UC-3 | 1.24 ms | 6719.93 ms | 0.28 ms | 6721.16 ms | 1.07 ms | `shared_threshold` |
| UC-4 | 1.03 ms | 1079.39 ms | 0.24 ms | 1080.41 ms | 1.44 ms | `shared_threshold` |
| UC-5 | 1.63 ms | 3.91 ms | 0.21 ms | 5.53 ms | 1.48 ms | `shared_threshold` |

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
