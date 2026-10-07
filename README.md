# Unified RCA

Motadata ObserveOps research monorepo: **Pillar A/B** product slice, docs hub on `:8765`, and reference Lean/Federated bakeoff engines.

**Documentation door:** [`docs/observeops/observeops-pipeline-hld.html`](docs/observeops/observeops-pipeline-hld.html) (`:8765/observeops-pipeline-hld.html`)  
**Docs index (slim):** [`docs.html`](http://127.0.0.1:8765/docs.html) · audit [`docs/REPO_AUDIT.md`](docs/REPO_AUDIT.md) · portal [`docs/HUB_PORTAL_AUDIT.md`](docs/HUB_PORTAL_AUDIT.md)  
**Edit hygiene:** [`docs/REPO_HYGIENE.md`](docs/REPO_HYGIENE.md)  
**Pillar A+B:** [`product/`](product/README.md) (shim [`pillar-ab-implementation/`](pillar-ab-implementation/))

## Layout (zones + shims)

| Zone | Shim at root (still works) | Purpose |
|------|----------------------------|---------|
| [`knowledge/`](knowledge/) | `docs/` | **Docs hub source** — edit topic folders here |
| [`product/`](product/) | `pillar-ab-implementation/` | Motadata Pillar A/B — contracts SoT, packages, integration |
| [`eval/`](eval/) | `benchmarking/`, `datasets/` | Bakeoff runners, `:8765` dashboard, corpora |
| [`reference/`](reference/) | `lean-pipeline/`, `federated-pipeline/` | **Eval history only** — not Motadata product path |
| [`archive/`](archive/) | `_archive/` | Parked snapshots / agent-tasks / handoffs — not the live hub |
| [`labs/`](labs/) | — | Vendor fault labs |
| [`ingestion-poc/`](ingestion-poc/README.md) | — | ObserveOps `ingest.v1` bridge (not `writer_stream.v1` SoT) |
| [`KR Plan/`](KR%20Plan/) | — | Management PDFs / OKRs |
| [`scripts/`](scripts/) | — | `repo_inventory.py`, `check_doc_drift.sh` |

**Hub publish rule:** edit `knowledge/` (or shim `docs/`) and `product/` (or shim `pillar-ab-implementation/`) only. Never fork articles under `eval/benchmarking/dashboard/` or `archive/`.

**Local bulk (gitignored):** Motadata JSONL under `datasets/ingest_samples/`, Nezha trees under federated, Rust `product/pillar-b/map-vortex/target/` — inflate `du`, not clone size.

## Quick start

```bash
# PoC console + docs hub
./start-poc-dash.sh start
# → http://127.0.0.1:8765/docs.html  ·  Our HLD: /observeops-pipeline-hld.html

# Pillar B map unit tests
cd product/pillar-b/poc && make test-graph

# ObserveOps Lean RCA (reference track)
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report
```

See [`docs/NAVIGATION.md`](docs/NAVIGATION.md), [`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md), [`docs/reference/eval-reference.html`](docs/reference/eval-reference.html) (Lean/Fed).
