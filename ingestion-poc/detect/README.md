# Shared detection (fair pipeline front door)

**Role:** Profile A threshold detect for Lean **and** Federated. Not Panorama.

```bash
# From repo root
python3 ingestion-poc/detect/threshold_detect.py \
  --uc-dir datasets/observeops/UC-1 \
  --out-dir /tmp/uc1-detect
```

Contract: [`docs/PIPELINE_PARITY.md`](../../docs/PIPELINE_PARITY.md)

Bakeoff runners call `detect_uc()` before RCA and record `detect_latency_ms` in `run_meta.json`.
