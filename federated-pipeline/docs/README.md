# Federated pipeline — specific documentation

Federated-only architecture and algorithm docs. Shared PoC materials (use-cases, roadmap, Lean PRD/Simple Guide, ADR, lean-vs-federated decision guide) live in [`../../docs/`](../../docs/README.md).

**Motadata note:** For ObserveOps UC-1..UC-5, **lean is the primary engine** ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)). This tree remains the federated PoC + optional microservice/code-path track.

## Documents

| Document | Purpose |
|----------|---------|
| [REQUIREMENTS.md](./REQUIREMENTS.md) | Federated PoC scope, goals, success criteria, implementation status |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Storage tiers, algorithms, write/query paths |
| [ORCHESTRATOR.md](./ORCHESTRATOR.md) | Coordination layer — triggers, hop contracts, fusion |
| [ARCHITECTURE_RATIONALE.md](./ARCHITECTURE_RATIONALE.md) | Novelty claim, paper gaps, design decisions |
| [CAPACITY.md](./CAPACITY.md) | PoC sizing vs. 1B EPS production vision |

## Related learning dissections

| Pipeline step | Algorithm | Dissection |
|---------------|-----------|------------|
| Step 1 — Symptom detection | Panorama | [Panorama_dissection.md](./dissections/Panorama_dissection.md) |
| Step 2 — Macro localization | Murphy | [Murphy_dissection.md](./dissections/Murphy_dissection.md) |
| Step 3 — Micro localization | Nezha | [Nezha-dissection.md](./dissections/Nezha-dissection.md) |

## Terminology

Two independent naming schemes — do not conflate them:

| Scheme | Labels | Answers the question |
|--------|--------|----------------------|
| **Pipeline steps** | Step 1 → 2 → 3 (Panorama → Murphy → Nezha) | What runs, in what order, during an incident |
| **Storage tiers** | Speed tier / Structural tier | Where data lives and how fast it moves |

The **orchestrator** sits above both: it routes triggers, translates schemas, and fuses outputs. It is not a storage tier.

## Quick start

```bash
cd federated-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Murphy Figure 1 crawler (simulated Panorama flag + real Murphy + Nezha scorer)
PYTHONPATH=..:. python run.py --scenario crawler --verbose

# Online Boutique: real Panorama majority + real Murphy + Nezha patterns
PYTHONPATH=..:. python run.py --scenario hipster --verbose

# Dual-stream ingest into Redis speed tier + in-memory structural store
PYTHONPATH=..:. python run.py --scenario ingest

# Hipster RCA with Nezha scored from Redis pc: keys
PYTHONPATH=..:. python run.py --scenario hipster --with-speed-tier --verbose

# Phase 0 capacity probe (Redis/Dragonfly on :6379 or :6380)
  --output ../benchmarking/capacity/phase0_latest.json

# Dragonfly (example — 2 threads on this host)
# docker run -d --name poc-dragonfly --network host \
#   docker.dragonflydb.io/dragonflydb/dragonfly:v1.25.1 \
#   --proactor_threads=2 --port=6380

# Tests
PYTHONPATH=..:. python -m pytest tests/ -v
```

Expected hipster output: fused `RCAVerdict` with `root_cause_entity: checkoutservice`.

## Code layout

```
federated-pipeline/
├── run.py                  # CLI entry point
├── poc/
│   ├── types.py            # Hop payload types (ORCHESTRATOR.md schemas)
│   ├── orchestrator.py     # UnifiedRCAOrchestrator — 6-hop pipeline
│   ├── adapters/
│   │   ├── panorama.py           # DetectionFlag adapter
│   │   ├── panorama_majority.py  # InferView / InferPano (Go port)
│   │   ├── murphy.py             # Murphy.diagnose() adapter
│   │   ├── nezha.py              # Pattern scoring + dataset path
│   │   └── nezha_speed.py        # Nezha from Redis pc: counts
│   ├── stores/
│   │   ├── speed.py              # Dragonfly/Redis tg:/pc: writer
│   │   └── structural.py         # In-memory LOS + metrics + edges
│   ├── ingest.py                 # Dual-stream write-path normalizer
│   ├── scenarios/
│   │   ├── crawler.py
│   │   └── hipster.py
│   └── benchmarks/
│       └── phase0_dragonfly.py
└── tests/
    └── test_pipeline.py
```
