# Ingestion pipeline runners

| Script | Role |
|--------|------|
| [`f1_run.py`](f1_run.py) | **N3** F1 smoke: `ingest.v1` → lean + structural + speed sinks + shared detect |

**One shared fabric for Lean + Federated** — Python fan-out (default) and `--vector` are two implementations of the **same** sink contract; N4/N5 are post-sink builders. See [`docs/INGESTION_PIPELINE_VECTOR.md`](../../docs/INGESTION_PIPELINE_VECTOR.md) §5.4.

```bash
# UC-1 (Python fan-out + detect) — default WSL smoke
python3 ingestion-poc/pipeline/f1_run.py --suite UC-1

# Optional: Docker Vector for sinks (same layout)
python3 ingestion-poc/pipeline/f1_run.py --suite UC-1 --vector

# D2 change-near-onset annotation
python3 ingestion-poc/pipeline/f1_run.py --suite UC-1 \
  --changes ingestion-poc/detect/samples/changes_uc1_near.jsonl

# Full chain → Lean diagnose
python3 ingestion-poc/builders/n45_chain.py --suite UC-1
```

Lab: smokes on **WSL**; **pro6000** for EPS / standing Vector+Dragonfly later.

Outputs under `ingestion-poc/out/f1-smoke/<suite>/` (gitignored).
