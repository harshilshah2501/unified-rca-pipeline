# ObserveOps replay samples (`ingest.v1`)

Generated from `datasets/observeops/UC-1..UC-5` by:

```bash
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all
```

| UC | `stream.jsonl` lines | metric_sample | anomaly | event | GT root |
|----|---------------------:|--------------:|--------:|------:|---------|
| UC-1 | 2028 | 2022 | 6 | 0 | `esxi-host-01` |
| UC-2 | 1692 | 1685 | 5 | 2 | `switch-core-01:GigE0/2` |
| UC-3 | 2028 | 2022 | 6 | 0 | `datastore-01` |
| UC-4 | 2027 | 2022 | 3 | 2 | `guest-os-vm-app-01` |
| UC-5 | 3037 | 3033 | 4 | 0 | `orders-api` |

Each `UC-N/` also has: `topology.json`, `ground_truth.json`, `symptom_seed.json`, `anomalies.json`, `topo_updates.jsonl`, `manifest.json`.

Contract: [`docs/INGEST_DATA_FORMAT.md`](../../../docs/INGEST_DATA_FORMAT.md)
