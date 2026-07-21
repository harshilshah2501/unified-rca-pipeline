# Vector ingestion PoC skeleton

Design doc: [`../../docs/INGESTION_PIPELINE_VECTOR.md`](../../docs/INGESTION_PIPELINE_VECTOR.md)  
F1 smoke runner: [`../pipeline/f1_run.py`](../pipeline/f1_run.py)

## Layout

| Path | Purpose |
|------|---------|
| `vector.lean-only.toml` | Profile **L0** — Lean sinks only (sketch) |
| `vector.dual-sink.toml` | Profile **F1** — Lean + speed-tier (sketch) |
| `vector.f1-smoke.toml` | **N3** runnable F1: lean + structural + speed sinks |
| `samples/ingest.v1.example.jsonl` | Tiny example envelopes |
| `README.md` | This file |

## Run F1 smoke (recommended)

```bash
# Python fan-out + shared detect (no Docker required)
python3 ingestion-poc/pipeline/f1_run.py --suite UC-1

# Docker Vector sinks + same detect
python3 ingestion-poc/pipeline/f1_run.py --suite UC-1 --vector
```

Image default: `timberio/vector:0.41.1-alpine` (`VECTOR_IMAGE` to override).

## Manual Vector (compose)

```bash
docker compose -f ingestion-poc/compose/docker-compose.f1.yml run --rm vector-f1
# then: python3 ingestion-poc/detect/threshold_detect.py \
#   --ingest-jsonl datasets/ingest_samples/observeops-replay/UC-1/stream.jsonl \
#   --out-dir /tmp/detect
```

Post-Vector builders (N4–N5):

- `lean_bundle_writer` — lean feed → ObserveOps-shaped bundle  
- Federated structural writer — metric slice / Dragonfly stub  
- `topo_builder` — inventory → `topology.json` / structural store  

## Cost PoC note

Compare L0 vs F1 with **identical** replay volume; only sink fan-out changes. See cheatsheet §3 and design doc §6.
