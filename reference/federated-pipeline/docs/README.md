# Federated pipeline — documentation

Federated-only architecture and algorithm docs. Shared ObserveOps materials (use-cases, roadmap, ADR, lean-vs-federated guide) live in [`../../docs/`](../../docs/README.md).

**ObserveOps status:** For ObserveOps UC-1..UC-5, **lean is the primary evaluation engine** per [ADR-001](../../docs/ADR-001-lean-primary-engine.md) (**not a finalized product commitment**). This tree is the federated PoC, bakeoff comparator, and optional microservice / code-path track.

## Start here (aligned with lean-pipeline docs)

| Document | Purpose |
|----------|---------|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | **Architecture, components, and workflows** (demos + ObserveOps bakeoff) |
| [`FEDERATED_PIPELINE_VISUAL_GUIDE.md`](./FEDERATED_PIPELINE_VISUAL_GUIDE.md) | **Sub-step guide for visual simulation (UC-1)** — Panorama → Murphy → Nezha → resolve |
| [`LIMITATIONS_AND_FUTURE.md`](./LIMITATIONS_AND_FUTURE.md) | **Limitations, when to choose federated, Phase C/E deferrals** |
| [`STORAGE_TIERS.md`](./STORAGE_TIERS.md) | Speed vs structural tier design vision |
| [`ORCHESTRATOR.md`](./ORCHESTRATOR.md) | Hop contracts, fusion, open decisions |
| [`REQUIREMENTS.md`](./REQUIREMENTS.md) | Federated PoC goals and implementation status |
| [`ARCHITECTURE_RATIONALE.md`](./ARCHITECTURE_RATIONALE.md) | Novelty claim / paper gaps |
| [`CAPACITY.md`](./CAPACITY.md) | PoC EPS measurements + 1B vision |

Lean primary twin: [`../../lean-pipeline/docs/ARCHITECTURE.md`](../../lean-pipeline/docs/ARCHITECTURE.md).

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
PYTHONPATH=..:. python -m poc.benchmarks.phase0_dragonfly \
  --port 6380 --workers 4 --pipeline-size 128 --seconds 20 \
  --output ../benchmarking/capacity/phase0_latest.json

# ObserveOps bakeoff (from repo root)
# ./benchmarking/benchmark/run_bakeoff.sh

# Tests
PYTHONPATH=..:. python -m pytest tests/ -v
```

Expected hipster output: fused `RCAVerdict` with `root_cause_entity: checkoutservice`.

Learning UI (not RCA API): `cd federated-pipeline && python3 -m http.server 8770`.

## Code layout

```
federated-pipeline/
├── run.py                  # Demo CLI
├── poc/
│   ├── types.py            # Hop payload types
│   ├── orchestrator.py     # UnifiedRCAOrchestrator — 6-hop pipeline
│   ├── adapters/           # Panorama / Murphy / Nezha adapters
│   ├── stores/             # Redis speed + in-memory structural
│   ├── ingest.py           # Dual-stream write-path normalizer (PoC)
│   ├── scenarios/          # crawler, hipster
│   └── benchmarks/         # phase0_dragonfly
├── murphy/ panorama/ Nezha/  # Reference implementations + learning UIs
├── docs/                   # This documentation set
├── deploy/systemd/         # Learning prototype :8770
└── tests/
```

ObserveOps bakeoff adapter (outside this tree):  
`benchmarking/benchmark/adapters/observeops_federated.py`.
