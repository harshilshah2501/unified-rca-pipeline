# Motadata → ingest.v1 adapter

Converts local Motadata dumps in `datasets/ingest_samples/jsonl_resolved/` (gitignored large files) into `ingest.v1` JSONL.

```bash
# Smoke (default limits — recommended first)
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke

# Larger but not full spans
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py \
  --limit-logs 10000 --limit-metrics 20000 --limit-traces 5000 --limit-spans 50000

# Full corpus (multi-GB output — local only, do not commit)
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --full --out-name stream.full.jsonl
```

**Output:** `datasets/ingest_samples/motadata-ingest/stream.jsonl` + `manifest.json`

| Source file | → signal_class | ci_id |
|-------------|----------------|-------|
| `log.jsonl` | `event` | hostname or `event_source` |
| `metric_numeric.jsonl` | `metric_sample` (one per field) | `monitor-{id}` |
| `metric_string.jsonl` | `event` | `monitor-{id}` |
| `trace.jsonl` | `trace_span` (summary) | service name |
| `span.jsonl` | `trace_span` | service name |

Contract: [`docs/INGEST_DATA_FORMAT.md`](../../docs/INGEST_DATA_FORMAT.md)
