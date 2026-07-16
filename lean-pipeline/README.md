# Lean pipeline

**Primary ObserveOps evaluation engine** ([ADR-001](../docs/ADR-001-lean-primary-engine.md); not a finalized product commitment): BFS + temporal ordering + information-gain search, with CARE fallback and scoped ObserveOps rules (§2.9).

| Path | Purpose |
|------|---------|
| [`core_engine/`](core_engine/) | Lean core + ObserveOps engine |
| [`lean_rca/`](lean_rca/) | ObserveOps CLI + HTTP API + SRE report enrichment |
| [`deploy/`](deploy/) | systemd unit for the RCA API (`:8780`) |
| [`docs/`](docs/) | Architecture, limitations/future work, historical notes · federated twin: [`../federated-pipeline/docs/`](../federated-pipeline/docs/) |

```bash
# From repo root
PYTHONPATH=lean-pipeline:. python -m pytest lean-pipeline/core_engine/tests/observeops/ -v
PYTHONPATH=lean-pipeline:. python benchmarking/benchmark/run_lean.py --all
```

## ObserveOps Lean RCA API

The public package is `lean_rca`. It resolves the bundled ObserveOps corpus
from `repo_paths.OBSERVEOPS_CORPUS`, or from `OBSERVEOPS_CORPUS` when set.

```bash
# From repo root
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca serve --host 127.0.0.1 --port 8780
```

The stdlib WSGI server exposes `GET /health`, `GET /v1/diagnose/UC-1`, and
`POST /v1/diagnose` with `{"uc_id":"UC-1"}`. Production-style unit:

```bash
./lean-pipeline/scripts/serve-rca.sh
# or: see lean-pipeline/deploy/README.md for systemd install
```

PRD / Simple Guide (shared, MD canonical): [../docs/Lean_RCA_PRD.md](../docs/Lean_RCA_PRD.md) · [PDF](../docs/Lean_RCA_PRD.pdf) · [../docs/Lean_RCA_Simple_Guide.md](../docs/Lean_RCA_Simple_Guide.md) · [PDF](../docs/Lean_RCA_Simple_Guide.pdf)

Lean architecture & limits: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/LIMITATIONS_AND_FUTURE.md](docs/LIMITATIONS_AND_FUTURE.md) · [docs/README.md](docs/README.md)
