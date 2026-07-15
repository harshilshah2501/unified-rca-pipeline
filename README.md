# Unified RCA

Root-cause analysis research workspace with two pipelines (federated + lean), shared datasets, and benchmarking.

## Layout

| Path | Purpose |
|------|---------|
| [`docs/`](docs/) | **Common PoC docs** — use-cases, roadmap, ADR, Lean PRD + Simple Guide, lean-vs-federated guide |
| [`rca-use-cases-only.md`](rca-use-cases-only.md) | Symlink → `docs/` (sole evaluation corpus spec) |
| [`ROADMAP.md`](ROADMAP.md) | Symlink → `docs/ROADMAP.md` |
| [`datasets/observeops/`](datasets/observeops/) | Frozen bundles derived from the use-case spec |
| [`federated-pipeline/`](federated-pipeline/) | Panorama → Murphy → Nezha + federated-specific docs (under evaluation) |
| [`lean-pipeline/`](lean-pipeline/) | Lean engine/API + docs (favored on classic-infra bakeoffs; not finalized) |
| [`benchmarking/`](benchmarking/) | Same-corpus bakeoff runners and results |
| [`benchmarking/dashboard/`](benchmarking/dashboard/) | **Comparative Web UI** — 4 axes, 5 roadblocks, UC + OpenObserve |
| [`repo_paths.py`](repo_paths.py) | Shared path constants + `sys.path` bootstrap |

## Quick start

```bash
# ObserveOps Lean RCA (evaluation packaging) — SRE report
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report

# HTTP API on :8780
./lean-pipeline/scripts/serve-rca.sh
# curl http://127.0.0.1:8780/v1/diagnose/UC-1

# Same-dataset bakeoff (ObserveOps UC-1..UC-5 only)
./benchmarking/benchmark/run_bakeoff.sh
```

See [`docs/POC_BRIEFING.md`](docs/POC_BRIEFING.md) for the full end-to-end PoC narrative (NotebookLM / slides), plus [`docs/README.md`](docs/README.md), [`docs/ADR-001-lean-primary-engine.md`](docs/ADR-001-lean-primary-engine.md), and [`benchmarking/README.md`](benchmarking/README.md).

## Learning UI (federated prototypes)

```bash
cd federated-pipeline && python3 -m http.server 8770
# → http://127.0.0.1:8770/
```
