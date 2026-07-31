# Unified RCA

Root-cause analysis research workspace with two pipelines (federated + lean), shared datasets, and benchmarking.

**Documentation:** **[`docs/NAVIGATION.md`](docs/NAVIGATION.md)** — doc reading path.  
**Code (newcomers):** **[`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md)** — folders, data→verdict flow, what to run.

## Layout

| Path | Purpose |
|------|---------|
| [`docs/`](docs/) | **Common PoC docs** — use-cases, roadmap, ADR, **[NAVIGATION](docs/NAVIGATION.md)**, ingestion design, Lean PRD + Simple Guide |
| [`ingestion-poc/`](ingestion-poc/) | Vector skeleton, shared detect, ObserveOps replay, Motadata → `ingest.v1` adapter |
| [`rca-use-cases-only.md`](rca-use-cases-only.md) | Symlink → `docs/` (sole evaluation corpus spec) |
| [`ROADMAP.md`](ROADMAP.md) | Symlink → `docs/ROADMAP.md` |
| [`datasets/observeops/`](datasets/observeops/) | Frozen bundles derived from the use-case spec (bakeoff) |
| [`datasets/ingest_samples/`](datasets/ingest_samples/) | Normalized `ingest.v1` streams (UC replay + Motadata; large dumps local) |
| [`federated-pipeline/`](federated-pipeline/) | Panorama → Murphy → Nezha + federated-specific docs (under evaluation) |
| [`lean-pipeline/`](lean-pipeline/) | Lean engine/API + docs (primary evaluation engine on ObserveOps bakeoffs; ADR-001; not finalized) |
| [`benchmarking/`](benchmarking/) | Same-corpus bakeoff runners and results |
| [`benchmarking/dashboard/`](benchmarking/dashboard/) | **PoC console** — Guide, Samples (manual verify), Conduct, UC bakeoff UI (OO peer hidden) |
| [`repo_paths.py`](repo_paths.py) | Shared path constants + `sys.path` bootstrap |

## Quick start

```bash
# PoC console (best explore / demo surface)
.venv/bin/python benchmarking/dashboard/server.py
# → http://127.0.0.1:8765/  (#guide · #samples · #conduct)
# Full walkthrough: docs/POC_DEMO_GUIDE.md

# ObserveOps Lean RCA — SRE report
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report

# HTTP API on :8780
./lean-pipeline/scripts/serve-rca.sh
# curl http://127.0.0.1:8780/v1/diagnose/UC-1

# Same-dataset bakeoff (ObserveOps UC-1..UC-5 only)
./benchmarking/benchmark/run_bakeoff.sh
```

See [`docs/NAVIGATION.md`](docs/NAVIGATION.md) for the full doc map. Short path: [`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md) (code), [`docs/POC_DEMO_GUIDE.md`](docs/POC_DEMO_GUIDE.md) (explore/demo), [`docs/POC_BRIEFING.md`](docs/POC_BRIEFING.md) (narrative), [`docs/RCA_WORKFLOW_AND_NEXT.md`](docs/RCA_WORKFLOW_AND_NEXT.md) (current next actions), [`docs/learning/RCA-learning-cheatsheet.md`](docs/learning/RCA-learning-cheatsheet.md) (study + cost PoC plan), [`docs/ADR-001-lean-primary-engine.md`](docs/ADR-001-lean-primary-engine.md), [`benchmarking/README.md`](benchmarking/README.md).

## Learning UI (federated prototypes)

```bash
cd federated-pipeline && python3 -m http.server 8770
# → http://127.0.0.1:8770/
```
