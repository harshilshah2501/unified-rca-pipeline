# Unified RCA

Root-cause analysis research workspace with two pipelines (federated + lean), shared datasets, Motadata Pillar A/B implementation, and a docs hub on `:8765`.

**Documentation:** **[`docs/NAVIGATION.md`](docs/NAVIGATION.md)** — doc reading path.  
**Edit hygiene:** **[`docs/REPO_HYGIENE.md`](docs/REPO_HYGIENE.md)** — canonical paths (avoid brief/Q&A drift).  
**Code (newcomers):** **[`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md)** — folders, data→verdict flow, what to run.  
**Pillar A+B work:** **[`pillar-ab-implementation/`](pillar-ab-implementation/README.md)** — contracts, owner packages, integration.

## Layout

| Path | Purpose |
|------|---------|
| [`docs/`](docs/) | **Docs hub source** — HTML/MD/CSS/JS. Edit here (or under `pillar-ab-implementation/`). |
| [`pillar-ab-implementation/`](pillar-ab-implementation/) | Motadata Pillar A+B — `contracts/` SoT, `pillar-a/` / `pillar-b/` packages, `integration/` |
| [`KR Plan/`](KR%20Plan/) | Management PDFs and OKR workbooks (canonical binaries) |
| [`labs/`](labs/) | Vendor fault labs: EdgeDelta, Datadog, Dynatrace |
| [`ingestion-poc/`](ingestion-poc/README.md) | Vector skeleton, shared detect, ObserveOps replay, Motadata → `ingest.v1` adapter (**local dumps:** see README) |
| [`lean-pipeline/`](lean-pipeline/) | Lean engine/API (evaluation track; ADR-001) |
| [`federated-pipeline/`](federated-pipeline/) | Panorama → Murphy → Nezha + federated-specific docs (**large** Nezha tree — not day-to-day Motadata edit) |
| [`benchmarking/`](benchmarking/) | Same-corpus bakeoff runners and results |
| [`benchmarking/dashboard/`](benchmarking/dashboard/) | **PoC console + docs host** (`:8765`) — mounts `docs/` and `pillar-ab-implementation/` via symlinks |
| [`datasets/`](datasets/) | ObserveOps frozen bundles + `ingest_samples` (**large** local dumps) |
| [`_archive/`](_archive/) | Parked snapshots / ad-hoc / notes — **not** the live hub |
| [`repo_paths.py`](repo_paths.py) | Shared path constants + `sys.path` bootstrap |
| [`rca-use-cases-only.md`](rca-use-cases-only.md) · [`ROADMAP.md`](ROADMAP.md) · [`NAVIGATION.md`](NAVIGATION.md) | Convenience symlinks → `docs/` |

**Hub publish rule:** edit `docs/` or `pillar-ab-implementation/` only. Never fork content under `benchmarking/dashboard/` or `_archive/`. Owner-package `docs/` are **symlinks** to hub/contracts — see [`docs/REPO_HYGIENE.md`](docs/REPO_HYGIENE.md).

## Quick start

```bash
# PoC console + docs hub
.venv/bin/python benchmarking/dashboard/server.py
# → http://127.0.0.1:8765/  (#guide · #samples · #conduct)
# Docs index: http://127.0.0.1:8765/docs.html
# Full walkthrough: docs/POC_DEMO_GUIDE.md

# ObserveOps Lean RCA — SRE report
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report

# HTTP API on :8780
./lean-pipeline/scripts/serve-rca.sh
# curl http://127.0.0.1:8780/v1/diagnose/UC-1

# Same-dataset bakeoff (ObserveOps UC-1..UC-5 only)
./benchmarking/benchmark/run_bakeoff.sh
```

See [`docs/NAVIGATION.md`](docs/NAVIGATION.md) for the full doc map. Short path: [`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md) (code), [`docs/POC_DEMO_GUIDE.md`](docs/POC_DEMO_GUIDE.md) (explore/demo), [`docs/POC_BRIEFING.md`](docs/POC_BRIEFING.md) (narrative), [`docs/RCA_WORKFLOW_AND_NEXT.md`](docs/RCA_WORKFLOW_AND_NEXT.md) (current next actions), [`pillar-ab-implementation/README.md`](pillar-ab-implementation/README.md) (A/B implementation), [`docs/ADR-001-lean-primary-engine.md`](docs/ADR-001-lean-primary-engine.md), [`benchmarking/README.md`](benchmarking/README.md).

## Learning UI (federated prototypes)

```bash
cd federated-pipeline && python3 -m http.server 8770
# → http://127.0.0.1:8770/
```
