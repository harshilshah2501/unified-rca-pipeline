# Federated pipeline

Panorama (detection) → Murphy (macro) → Nezha (micro) behind a coordination layer.

**Motadata note:** For ObserveOps UC-1..UC-5, **lean is primary** ([ADR-001](../docs/ADR-001-lean-primary-engine.md)). This tree is the federated PoC, bakeoff comparator, and optional microservice/code-path track.

| Path | Purpose |
|------|---------|
| [`poc/`](poc/) | Orchestrator, adapters, ingest, scenarios, Phase 0 harness |
| [`murphy/`](murphy/) | Murphy reference implementation |
| [`panorama/`](panorama/) | Panorama reference implementation |
| [`Nezha/`](Nezha/) | Nezha reference implementation |
| [`docs/`](docs/) | Architecture, capacity, requirements, algorithm dissections |
| [`deploy/`](deploy/) | systemd units for learning UI |
| [`scripts/`](scripts/) | Dissection PDF builder |
| [`index.html`](index.html) | Learning prototypes hub |
| [`run.py`](run.py) | CLI |
| [`tests/`](tests/) | Pipeline + ingest tests |

```bash
cd federated-pipeline
pip install -r requirements.txt -r murphy/requirements.txt
PYTHONPATH=..:. python run.py --scenario hipster --verbose
PYTHONPATH=..:. python run.py --scenario hipster --with-speed-tier
PYTHONPATH=..:. python -m pytest tests/ -v
```

Docs index: [docs/README.md](docs/README.md).
