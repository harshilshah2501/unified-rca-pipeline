# Motadata resolved JSONL (local only)

Large ClickHouse exports live here and are **gitignored** (GitHub 100MB limit). Keep on disk — **do not commit or push**.

**Overview:** [`ingestion-poc/README.md`](../../../ingestion-poc/README.md) § Local bulk dumps.

## Typical sizes (this machine)

| File | Role | Approx size |
|------|------|-------------|
| `log.jsonl` | Logs | ~40M |
| `metric_numeric.jsonl` | Numeric metrics | ~300M |
| `metric_string.jsonl` | String metrics | ~0.5M |
| `trace.jsonl` | Trace summaries | ~120M |
| `span.jsonl` | Full spans | **~3.8G** |
| **Total** | | **~4.3G** |

Only `README.md` is tracked in git. `*.jsonl` matches `.gitignore`.

## Who needs this?

| Consumer | Needs dumps? |
|----------|----------------|
| `ingestion-poc/adapters/motadata_*.py` / `build_motadata_*.py` | **Yes** (defaults here) |
| ObserveOps UC replay (`observeops-replay/`) | No |
| Pillar A/B `poc/fixtures/lab_checkout/` | No |
| Lean UC bakeoff (`datasets/observeops/UC-*`) | No |
| Docs hub `:8765` | No |

Missing dumps: adapters exit with a message pointing at [`ingestion-poc/README.md`](../../../ingestion-poc/README.md) (helper: `ingestion-poc/adapters/local_dumps.py`).

## Convert

```bash
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
# → ../motadata-ingest/stream.jsonl (gitignored when large)
```

Optional alternate: unresolved dumps under `../motadata-raw/` (also gitignored). Prefer this `jsonl_resolved/` tree when attribute names are already expanded.
