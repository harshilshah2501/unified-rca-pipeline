# ObserveOps Corpus — Federated vs Lean Benchmark

Frozen input bundles for **UC-1..UC-5** from [docs/rca-use-cases-only.md](../../docs/rca-use-cases-only.md).

Classic infra typed CI graph (Network → ESXi → VM → OS → App + Datastore) — not a microservice deployment-identity call graph. See [docs/README.md](../../docs/README.md).

## 4-Step Workflow

| Step | Command / action | Output |
|------|------------------|--------|
| 1 Define corpus | `python3 datasets/observeops/build_corpus.py` | `UC-1/`..`UC-5/` bundles |
| 2 Test federated | `python3 benchmarking/benchmark/run_federated.py --all` | `benchmarking/results/federated/` |
| 3 Test lean | `python3 benchmarking/benchmark/run_lean.py --all` | `benchmarking/results/lean/` |
| 4 Compare | `python3 benchmarking/benchmark/compare.py` | `COMPARISON.md` |


## Bundle layout (per UC)

```
UC-N/
  topology.json
  metrics/*.json
  anomalies.json
  symptom_seed.json
  ground_truth.json
  injection_manifest.yaml
```

Both engines read **identical files**. No architecture-specific preprocessing that alters graph or timestamps.

## Regenerate corpus

```bash
cd /root/Harshil-PoCs/Unified-RCA
python3 datasets/observeops/build_corpus.py
```

## Agent continuation

See [benchmark/AGENTS.md](../../benchmarking/benchmark/AGENTS.md) and [benchmark/TASKS.md](../../benchmarking/benchmark/TASKS.md).
