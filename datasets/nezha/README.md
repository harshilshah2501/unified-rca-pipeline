# Nezha datasets

Large Online Boutique / TrainTicket telemetry lives under the Nezha reference tree
(`federated-pipeline/Nezha/`) and is gitignored. This folder exposes stable links:

| Link | Target |
|------|--------|
| `rca_data/` | `../../federated-pipeline/Nezha/rca_data/` |
| `construct_data/` | `../../federated-pipeline/Nezha/construct_data/` |

**Note:** Bakeoff evaluation uses only the ObserveOps corpus from
[`rca-use-cases-only.md`](../../docs/rca-use-cases-only.md), not these Nezha datasets.

If links are missing, recreate:

```bash
ln -s ../../federated-pipeline/Nezha/rca_data datasets/nezha/rca_data
ln -s ../../federated-pipeline/Nezha/construct_data datasets/nezha/construct_data
```
