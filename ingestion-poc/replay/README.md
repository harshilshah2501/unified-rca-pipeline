# ObserveOps → ingest.v1 replay converter

```bash
# From repo root — convert UC-1..UC-5
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all

# Single UC
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --uc UC-1
```

**Output:** `datasets/ingest_samples/observeops-replay/UC-N/`

| File | Contents |
|------|----------|
| `stream.jsonl` | `ingest.v1` metric_sample (+ anomaly) + event lines |
| `topo_updates.jsonl` | Edge audit as `topo_update` |
| `topology.json` / `ground_truth.json` / … | Copied from corpus |
| `manifest.json` | Line counts + seed |

Format contract: [`docs/INGEST_DATA_FORMAT.md`](../../docs/INGEST_DATA_FORMAT.md)
