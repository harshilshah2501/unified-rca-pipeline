# Lab EPS — Vector + Dragonfly standing harness

**Target host:** `pro6000-server` (Tier B+, ≥16 cores / ≥64 GiB) for headline ≥50K EPS.  
**This WSL/laptop:** harness smoke + floor only — do **not** publish as capacity.

Design: [`../../docs/INGESTION_POC_PLAN.md`](../../docs/INGESTION_POC_PLAN.md) §4 · Capacity: [`../../federated-pipeline/docs/CAPACITY.md`](../../federated-pipeline/docs/CAPACITY.md)

## Quick start

```bash
# From repo root — starts Dragonfly (compose), runs phase0 + F1 fan-out + N4 read
python3 ingestion-poc/lab/run_lab_eps.py

# pro6000 recommended
DF_PROACTOR_THREADS=8 python3 ingestion-poc/lab/run_lab_eps.py --seconds 30 --workers 16
```

Artifacts: `benchmarking/capacity/lab/<run_id>/` + `benchmarking/capacity/lab/LATEST.md`

## Pieces

| Script | Role |
|--------|------|
| [`host_check.py`](host_check.py) | CPU/RAM/GPU → tier + recommended knobs |
| [`run_lab_eps.py`](run_lab_eps.py) | Orchestrator |
| [`run_cost_harness.py`](run_cost_harness.py) | **M2** L0 vs F1 cost report (+ optional Dragonfly soak / Vector) |
| [`vector_replay_eps.py`](vector_replay_eps.py) | F1 Python fan-out EPS (Vector-equivalent) |
| [`metric_slice_read.py`](metric_slice_read.py) | N4 `metric_slice` read + optional speed→Dragonfly load |
| [`../compose/docker-compose.lab.yml`](../compose/docker-compose.lab.yml) | Dragonfly (+ optional Vector profile) |

## Manual Dragonfly only

```bash
DF_PROACTOR_THREADS=8 DF_PORT=6380 \
  docker compose -f ingestion-poc/compose/docker-compose.lab.yml up -d dragonfly

cd federated-pipeline
PYTHONPATH=..:. python -m poc.benchmarks.phase0_dragonfly \
  --port 6380 --workers 16 --pipeline-size 128 --seconds 30 \
  --output ../benchmarking/capacity/lab/phase0_pro6000.json
```

After a **pro6000** run, paste the phase0 row into [`CAPACITY.md`](../../federated-pipeline/docs/CAPACITY.md) PoC table.

## Cost harness (L0 vs F1)

```bash
# Local smoke
python3 ingestion-poc/lab/run_cost_harness.py --events 100000

# pro6000 headline — Python + Vector + 120s Dragonfly soak
DF_PROACTOR_THREADS=8 python3 ingestion-poc/lab/run_cost_harness.py \
  --events 500000 --vector --seconds-soak 120
# → benchmarking/results/costing/<run_id>/cost_report.md
```
