# Ingest samples

Normalized and source streams for the **ingestion PoC** (not the ObserveOps bakeoff scoreboard).

**Front door + dump policy:** [`ingestion-poc/README.md`](../../ingestion-poc/README.md).

| Path | Role | In git? | Typical size |
|------|------|---------|--------------|
| [`observeops-replay/`](observeops-replay/) | UC-1..5 → `ingest.v1` (from frozen ObserveOps bundles) | Yes (small) | MB |
| [`motadata-ingest/`](motadata-ingest/) | Motadata → `ingest.v1` derived stream + `manifest.json` + incidents | README/manifest/incidents OK; `*.jsonl` gitignored when large | varies |
| [`jsonl_resolved/`](jsonl_resolved/) | Motadata ClickHouse export (resolved names) | **Local only** — `*.jsonl` gitignored | **~4.3G** |
| `motadata-raw/` | Optional unresolved Motadata dumps | Gitignored if present | large |

**Do not push** Motadata bulk dumps (`span.jsonl` alone is multi-GB). Contract: [`docs/INGEST_DATA_FORMAT.md`](../../docs/INGEST_DATA_FORMAT.md).

```bash
# ObserveOps (no Motadata dumps)
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all

# Motadata smoke (requires jsonl_resolved/*.jsonl locally)
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
```

Next: Vector F1 / Lean L0 on these streams — [`docs/RCA_WORKFLOW_AND_NEXT.md`](../../docs/RCA_WORKFLOW_AND_NEXT.md).
