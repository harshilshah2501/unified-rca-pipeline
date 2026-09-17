# Nezha datasets

Large Online Boutique / TrainTicket telemetry lives under the Nezha reference tree
(`federated-pipeline/Nezha/`) and is gitignored (~**2.8G** under `rca_data/` alone). This folder exposes stable links:

| Link | Target |
|------|--------|
| `rca_data/` | `../../federated-pipeline/Nezha/rca_data/` |
| `construct_data/` | `../../federated-pipeline/Nezha/construct_data/` |

**Not Motadata.** These dumps are for the federated / Nezha comparator track only. They are unrelated to `datasets/ingest_samples/jsonl_resolved/` (Motadata lake) and are **not** required for Pillar A∥B or ObserveOps UC bakeoff.

**Note:** Bakeoff evaluation uses only the ObserveOps corpus from
[`rca-use-cases-only.md`](../../docs/rca-use-cases-only.md), not these Nezha datasets.

Dump policy overview: [`ingestion-poc/README.md`](../../ingestion-poc/README.md) § Local bulk dumps.

If links are missing, recreate:

```bash
ln -s ../../federated-pipeline/Nezha/rca_data datasets/nezha/rca_data
ln -s ../../federated-pipeline/Nezha/construct_data datasets/nezha/construct_data
```
