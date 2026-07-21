# Shared detection (fair pipeline front door)

**Role:** Profile A threshold detect for Lean **and** Federated. Not Panorama.

| Module | Role |
|--------|------|
| [`threshold_detect.py`](threshold_detect.py) | Shared crossings + **D3** `anomaly_class` |
| [`change_near_onset.py`](change_near_onset.py) | **D2** change feed → `change_context.json` |

```bash
# ObserveOps metrics/ directory
python3 ingestion-poc/detect/threshold_detect.py \
  --uc-dir datasets/observeops/UC-1 \
  --out-dir /tmp/uc1-detect

# ingest.v1 + D2 change feed
python3 ingestion-poc/detect/threshold_detect.py \
  --ingest-jsonl datasets/ingest_samples/observeops-replay/UC-1/stream.jsonl \
  --changes ingestion-poc/detect/samples/changes_uc1_near.jsonl \
  --out-dir /tmp/uc1-detect-change

# F1 (sinks + detect); optional --changes
python3 ingestion-poc/pipeline/f1_run.py --suite UC-1 \
  --changes ingestion-poc/detect/samples/changes_uc1_near.jsonl
```

**D3 classes:** `error_rate` | `performance` | `resource` | `network` | `threshold`  
**D2 samples:** [`samples/changes_uc1_far.jsonl`](samples/changes_uc1_far.jsonl) (outside window) · [`samples/changes_uc1_near.jsonl`](samples/changes_uc1_near.jsonl) (inside 30m)

Contract: [`docs/PIPELINE_PARITY.md`](../../docs/PIPELINE_PARITY.md) · buckets: [`docs/FAULT_BUCKET_COVERAGE.md`](../../docs/FAULT_BUCKET_COVERAGE.md)
