# Edge Delta Kubernetes install — local k3d while VMs wait

**Status (2026-08-17):** WSL k3d cluster `ed-lab` is up. Node Pipeline Helm-installed. Coordinator / Gateway **not** installed (2 CPU / ~2–3 Gi free — helm defaults would OOM). Admin Linux VMs still the production-quality path.

**Do not** reuse `AI-Connector-Telemetry-Pipeline` (GitHub IngestionPipeline) as the Helm API key.

## What is on this WSL box

| Piece | State |
|-------|--------|
| Cluster | `k3d cluster create ed-lab` (1 server, Traefik/metrics-server/servicelb off) |
| Node agent | `helm upgrade edgedelta edgedelta/edgedelta -i -n edgedelta` + [`helm-values-wsl.yaml`](./helm-values-wsl.yaml) |
| Workloads | `noisy-logger.yaml` (UC1) · `uc8-crash.yaml` (UC8) · `fake-ingest.yaml` (UC6 lite) |
| Gateway / Coordinator / Kafka / Postgres | **Skipped** on this host — UC4 traces and two-node UC8 wait on the VMs |

Pipeline ID comes from **AI Team → Connectors → Kubernetes** (creates an `Edge` pipeline tagged `kubernetes`). Pass it only via `--set secretApiKey.value=…` — do not commit it.

```bash
export ED_NODE_PIPELINE_ID='<pipeline-id>'
helm repo add edgedelta https://helm.edgedelta.com
helm repo update
helm upgrade edgedelta edgedelta/edgedelta -i \
  -n edgedelta --create-namespace \
  -f labs/edgedelta/helm-values-wsl.yaml \
  --set secretApiKey.value="$ED_NODE_PIPELINE_ID"

kubectl apply -f labs/edgedelta/noisy-logger.yaml
kubectl apply -f labs/edgedelta/uc8-crash.yaml
kubectl apply -f labs/edgedelta/fake-ingest.yaml
```

Confirm: `kubectl get pods -n edgedelta` is Running; agent logs show `Configuration loaded and running` and file-tailers under `/var/log/pods/ed_lab_*`. Then Logs explorer / MCP `get_log_search` should leave 0.

When the Linux VMs exist, install Coordinator + Gateway there and **do not** treat this k3d node as the two-node UC8 lab.

Sizes and use-case matrix: [`docs/EDGEDELTA_LAB_SETUP.md`](../../docs/EDGEDELTA_LAB_SETUP.md).
