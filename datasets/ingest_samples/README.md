# Ingest samples

Normalized and source streams for the **ingestion PoC** (not the ObserveOps bakeoff scoreboard).

| Path | Role | In git? |
|------|------|---------|
| [`observeops-replay/`](observeops-replay/) | UC-1..5 → `ingest.v1` (from frozen ObserveOps bundles) | Yes (small) |
| [`motadata-ingest/`](motadata-ingest/) | Motadata → `ingest.v1` derived stream + `manifest.json` | README/manifest OK; `*.jsonl` gitignored when large |
| [`jsonl_resolved/`](jsonl_resolved/) | Motadata ClickHouse export (resolved names) | **Local only** — `*.jsonl` gitignored |
| `motadata-raw/` | Optional unresolved Motadata dumps | Gitignored if present |

**Do not push** Motadata bulk dumps (`span.jsonl` alone is multi-GB). Contract: [`docs/INGEST_DATA_FORMAT.md`](../../docs/INGEST_DATA_FORMAT.md).

```bash
# ObserveOps
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all

# Motadata smoke
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
```

Next: Vector F1 / Lean L0 on these streams — [`docs/RCA_WORKFLOW_AND_NEXT.md`](../../docs/RCA_WORKFLOW_AND_NEXT.md).
