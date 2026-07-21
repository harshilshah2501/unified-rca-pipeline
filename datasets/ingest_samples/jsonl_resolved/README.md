# Motadata resolved JSONL (local only)

Large ClickHouse exports live here and are **gitignored** (GitHub 100MB limit; `span.jsonl` ~3.8GB). Keep on disk / pro6000 — **do not commit or push**.

| File | Role |
|------|------|
| `log.jsonl` | Logs |
| `metric_numeric.jsonl` | Numeric metrics |
| `metric_string.jsonl` | String metrics |
| `trace.jsonl` | Trace summaries |
| `span.jsonl` | Full spans |

**Converter (done):** [`ingestion-poc/adapters/motadata_to_ingest_v1.py`](../../../ingestion-poc/adapters/motadata_to_ingest_v1.py) reads this directory and emits `ingest.v1` under [`../motadata-ingest/`](../motadata-ingest/).

```bash
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
```

Optional alternate: unresolved dumps under `../motadata-raw/` (also gitignored). Prefer this `jsonl_resolved/` tree when attribute names are already expanded.
