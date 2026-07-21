# Post-F1 builders (N4 / N5)

| Script | Role |
|--------|------|
| [`federated_store_writer.py`](federated_store_writer.py) | **N4** — `structural/stream.jsonl` → metric slice + topology edges + Dragonfly key stub |
| [`lean_bundle_writer.py`](lean_bundle_writer.py) | **N5** — F1 detect artifacts → Lean UC bundle |
| [`n45_chain.py`](n45_chain.py) | F1 → N4 → N5 → `lean_rca diagnose` (UC suites) |

```bash
# Full chain (UC-1 exit criteria)
python3 ingestion-poc/builders/n45_chain.py --suite UC-1

# Pieces
python3 ingestion-poc/pipeline/f1_run.py --suite UC-1
python3 ingestion-poc/builders/federated_store_writer.py --f1-dir ingestion-poc/out/f1-smoke/UC-1
python3 ingestion-poc/builders/lean_bundle_writer.py --f1-dir ingestion-poc/out/f1-smoke/UC-1 --diagnose
```

Diagnose uses ingested corpus:

```bash
OBSERVEOPS_CORPUS=ingestion-poc/out/lean-bundles \
  PYTHONPATH=lean-pipeline:. python3 -m lean_rca diagnose UC-1 --format report
```
