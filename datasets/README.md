# Datasets

**Evaluation corpus (only):** ObserveOps UC-1..UC-5 as specified in
[`docs/rca-use-cases-only.md`](../docs/rca-use-cases-only.md) (also linked as [`use-cases.md`](use-cases.md)).

| Path | Contents |
|------|----------|
| [`observeops/`](observeops/) | UC-1..UC-5 frozen corpus (topology, anomalies, ground truth) |
| [`nezha/`](nezha/) | Symlinks to federated-pipeline Nezha telemetry (demo/reference only — **not** the bakeoff corpus) |
| [`use-cases.md`](use-cases.md) | Symlink → `../docs/rca-use-cases-only.md` |

```bash
# Regenerate ObserveOps bundles from the use-case spec
python3 datasets/observeops/build_corpus.py

# Validate
python3 benchmarking/benchmark/validate_corpus.py
```
