# Vector ingestion PoC skeleton

Design doc: [`../../docs/INGESTION_PIPELINE_VECTOR.md`](../../docs/INGESTION_PIPELINE_VECTOR.md)

This folder is **config/docs only** for now — not a full running cost harness.

## Layout

| Path | Purpose |
|------|---------|
| `vector.lean-only.toml` | Profile **L0** — Lean sinks only |
| `vector.dual-sink.toml` | Profile **F1** — Lean + Federated speed-tier feed |
| `samples/ingest.v1.example.jsonl` | Example `ingest.v1` envelopes |
| `README.md` | This file |

## Prerequisites (when implementing D1)

```bash
# Install Vector: https://vector.dev/docs/setup/installation/
vector --version
```

## Intended run shape (future)

```bash
# Replay example events (Lean-only profile)
vector --config ingestion-poc/vector/vector.lean-only.toml

# Dual-sink profile (higher ingest cost path)
vector --config ingestion-poc/vector/vector.dual-sink.toml
```

Post-Vector builders (not included yet):

- `lean_bundle_writer` — JSONL / HTTP → ObserveOps-shaped bundle dir  
- `speed_tier_builder` — Redis/Kafka messages → `tg:` / `pc:` style keys  
- `topo_builder` — inventory export → `topology.json` / structural store  

## Cost PoC note

Compare L0 vs F1 with **identical** `samples/` replay volume; only sink fan-out changes. See cheatsheet §3 and design doc §6.
