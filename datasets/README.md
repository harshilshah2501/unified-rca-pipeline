# Datasets

**Evaluation corpus (ObserveOps bakeoff only):** UC-1..UC-5 as specified in
[`docs/rca-use-cases-only.md`](../docs/rca-use-cases-only.md) (also linked as [`use-cases.md`](use-cases.md)).

| Path | Contents |
|------|----------|
| [`observeops/`](observeops/) | UC-1..UC-5 frozen corpus (topology, anomalies, ground truth) — **canonical bakeoff** |
| [`ingest_samples/`](ingest_samples/) | Ingestion PoC streams: ObserveOps → `ingest.v1`, Motadata → `ingest.v1` (large Motadata dumps **local only**) |
| [`openobserve_incidents/`](openobserve_incidents/) | Separate real-incident corpus — **do not merge** with ObserveOps 5/5 |
| [`nezha/`](nezha/) | Symlinks to federated-pipeline Nezha telemetry (demo/reference only — **not** the bakeoff corpus) |
| [`use-cases.md`](use-cases.md) | Symlink → `../docs/rca-use-cases-only.md` |

```bash
# Regenerate ObserveOps bundles from the use-case spec
python3 datasets/observeops/build_corpus.py

# Validate
python3 benchmarking/benchmark/validate_corpus.py

# Ingest samples (normalized JSONL)
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke   # needs local jsonl_resolved/
```

Ingest contract: [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md). Workflow: [`docs/RCA_WORKFLOW_AND_NEXT.md`](../docs/RCA_WORKFLOW_AND_NEXT.md).
