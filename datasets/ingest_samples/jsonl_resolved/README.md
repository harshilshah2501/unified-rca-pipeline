# Motadata resolved JSONL (local only)

Large ClickHouse exports live here and are **gitignored** (GitHub 100MB limit; `span.jsonl` ~3.8GB).

Expected files (keep on disk / pro6000, do not commit):

| File | Role |
|------|------|
| `log.jsonl` | Logs |
| `metric_numeric.jsonl` | Numeric metrics |
| `metric_string.jsonl` | String metrics |
| `trace.jsonl` | Traces |
| `span.jsonl` | Spans |

Adapter work should read from this path (or `motadata-raw/`) and emit `ingest.v1` under a smaller derived suite.
