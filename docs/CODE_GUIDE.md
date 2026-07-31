# Unified RCA — Code guide (for newcomers)

**Audience:** engineers opening this repo for the first time  
**Goal:** know *where code lives*, *what runs what*, and *which 5 files to open next*  
**Not this doc:** product narrative → [`POC_BRIEFING.md`](./POC_BRIEFING.md) · full doc map → [`NAVIGATION.md`](./NAVIGATION.md) · click-through demo → [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md)

---

## Cognitive path (code)

```
Folders = stages → One picture of data flow → Touch it (3 commands)
  → Area guides (ingest · Lean · Federated · bakeoff · data)
  → Common tasks · env cheat sheet · pitfalls
```

| Stage | Question | Section |
|-------|----------|---------|
| **1. Map** | What are these folders *for*? | §1 |
| **2. Flow** | How does an event become a verdict? | §2 |
| **3. Touch** | Can I run something in 10 minutes? | §3 |
| **4. Areas** | Where do I dig for my task? | §4–§8 |
| **5. Tasks** | “I need to …” recipes | §9 |
| **6. Config** | Env vars / PYTHONPATH | §10 |
| **7. Pitfalls** | What trips everyone up? | §11 |

**One-line code contract:** shared ingest + shared Detect; then **Lean** or **Federated** localize/identify; bakeoff scores vs **human** ground truth; dashboard shows it.

---

## 1) Folder map (remember this)

```
Unified-RCA/
├── repo_paths.py           # shared path constants + sys.path helper
├── docs/                   # design & PoC docs (not runtime)
├── datasets/               # frozen corpora + ingest streams (data in, not logic)
├── ingestion-poc/          # normalize → detect → write packs (shared fabric)
├── lean-pipeline/          # primary RCA engine (CLI + HTTP)
├── federated-pipeline/     # comparator stack (Panorama → Murphy → Nezha)
└── benchmarking/           # runners, results, PoC console (:8765)
```

| Folder | Job in one sentence |
|--------|---------------------|
| `datasets/` | **What** we diagnose (UC bundles, Motadata streams, OO incidents) |
| `ingestion-poc/` | Turn telemetry into `ingest.v1` + seeds + Lean/Fed packs |
| `lean-pipeline/` | Classic-infra RCA: walk topology → signature → report |
| `federated-pipeline/` | Multi-algo orchestration for the same incidents (comparator) |
| `benchmarking/` | Score engines vs GT; drive the PoC console |

Design docs live under `docs/`. Runtime code does **not** belong there.

---

## 2) One picture — data → verdict

```
Sources                    Normalize                 Shared fabric
─────────                  ─────────                 ─────────────
ObserveOps UC bundles  ──► ingest.v1 JSONL  ──►  detect (thresholds)
Motadata dumps         ──► (replay/adapters)     ├──► Lean bundle writer
OpenObserve (peer)     ──►                       └──► Federated store writer
                                                        │
                              ┌─────────────────────────┴─────────────────────────┐
                              ▼                                                   ▼
                         lean_rca diagnose                              federated orchestrator
                         (Localize → Identify → Verify)                 (Panorama → Murphy → Nezha)
                              │                                                   │
                              └──────────────────┬────────────────────────────────┘
                                                 ▼
                                    benchmarking runners → COMPARISON.md
                                                 ▼
                                    dashboard (:8765)  Guide · Samples · Conduct
```

**Important:** the ObserveOps **bakeoff** usually reads **frozen** `datasets/observeops/UC-*` packs directly. The ingest path (`f1_run` → builders) proves the *product-shaped* front door; both should agree on roots when wired through `n45_chain.py`.

Canonical stages: **Ingest → Detect → Localize → Identify → Verify** — see [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md).

---

## 3) Touch it (10 minutes)

From repo root, with `.venv` already present:

```bash
# 1) PoC console — best overview of what the code produces
.venv/bin/python benchmarking/dashboard/server.py
# → http://127.0.0.1:8765/   (#guide · #incident · #samples · #verdict)

# 2) One Lean diagnose (frozen UC pack)
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report

# 3) Full UC bakeoff (Lean + Federated → scoreboard)
./benchmarking/benchmark/run_bakeoff.sh
# → benchmarking/results/comparison/COMPARISON.md
```

Optional ingest smoke (shared fabric → packs → Lean root check):

```bash
PYTHONPATH=lean-pipeline:. .venv/bin/python ingestion-poc/builders/n45_chain.py
```

---

## 4) `ingestion-poc/` — shared fabric

**Role:** everything *before* the two RCA engines diverge.

| Path | What it does |
|------|----------------|
| `replay/observeops_to_ingest_v1.py` | UC bundles → `ingest.v1` JSONL |
| `adapters/motadata_to_ingest_v1.py` | Motadata dumps → `ingest.v1` |
| `adapters/build_motadata_incident.py` | Motadata → Lean/Fed-style incident packs + GT stamp |
| `detect/threshold_detect.py` | Shared Detect → `A-ANOM` / `A-SEED` |
| `detect/change_near_onset.py` | Optional change-near-onset context (D2) |
| `pipeline/f1_run.py` | F1 smoke: stream → sinks + detect |
| `builders/lean_bundle_writer.py` | N5 — Lean-ready bundle |
| `builders/federated_store_writer.py` | N4 — Federated stores / stubs |
| `builders/n45_chain.py` | End-to-end: F1 → N4/N5 → `lean_rca diagnose` |
| `vector/*.toml` | Vector skeletons (L0 lean-only / F1 dual-sink) |
| `lab/run_lab_eps.py` · `lab/run_cost_harness.py` | EPS / L0 vs F1 cost lab |

**First 5 files to read**

1. [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) — the contract (`ingest.v1`)
2. `ingestion-poc/pipeline/f1_run.py`
3. `ingestion-poc/detect/threshold_detect.py`
4. `ingestion-poc/builders/n45_chain.py`
5. [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) — design (why L0/F1)

Per-folder READMEs: `ingestion-poc/{adapters,detect,pipeline,builders,replay,vector,lab}/README.md`.

---

## 5) `lean-pipeline/` — primary engine

**Role:** classic infrastructure RCA on typed CI graphs (network → host → VM → app).

| Path | What it does |
|------|----------------|
| `lean_rca/__main__.py` | CLI: `diagnose` · `serve` |
| `lean_rca/http.py` | HTTP API (`/v1/diagnose/...`) |
| `lean_rca/report.py` | Human SRE report formatter |
| `core_engine/observeops/engine.py` | ObserveOps diagnose entry |
| `core_engine/observeops/ingest/bundle.py` | Load UC / Motadata-style packs |
| `core_engine/observeops/rules/` | Domain rules / signatures |
| `core_engine/lean/search.py` | Best-first / info-gain walk |
| `core_engine/lean/{temporal,signature,care,causal}.py` | Tiered evidence path |
| `scripts/serve-rca.sh` | Serve on `:8780` |
| `deploy/` | systemd packaging |

**First 5 files to read**

1. `lean-pipeline/README.md`
2. `lean-pipeline/lean_rca/__main__.py`
3. `lean-pipeline/core_engine/observeops/engine.py`
4. `lean-pipeline/core_engine/lean/search.py`
5. `lean-pipeline/docs/ARCHITECTURE.md`

**Run**

```bash
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-2 --format report
./lean-pipeline/scripts/serve-rca.sh   # → :8780
```

Corpus override: `OBSERVEOPS_CORPUS=/path/to/packs`.

---

## 6) `federated-pipeline/` — comparator

**Role:** same incidents, different localization/identify stack (for bakeoff fairness, not the default product path).

| Path | What it does |
|------|----------------|
| `run.py` | Demo CLI (`--scenario crawler\|hipster\|ingest`) |
| `poc/orchestrator.py` | Hop orchestration + fusion |
| `poc/adapters/` | Panorama / Murphy / Nezha adapters |
| `poc/stores/` | Speed vs structural store abstractions |
| `murphy/` · `panorama/` · `Nezha/` | Upstream algorithm trees |
| `index.html` | Learning UI (static) |

**First 5 files to read**

1. `federated-pipeline/README.md`
2. `federated-pipeline/run.py`
3. `federated-pipeline/poc/orchestrator.py`
4. `federated-pipeline/docs/ORCHESTRATOR.md`
5. `federated-pipeline/docs/ARCHITECTURE.md`

**Run**

```bash
cd federated-pipeline && python3 -m http.server 8770   # learning UI
# Bakeoff path is via benchmarking/benchmark/run_federated.py (not this UI)
```

---

## 7) `benchmarking/` — score & show

**Role:** fair runners, scoreboards, PoC console.

| Path | What it does |
|------|----------------|
| `benchmark/run_bakeoff.sh` | One-shot ObserveOps UC Lean + Fed compare |
| `benchmark/run_lean.py` | Lean over UC packs → `results/lean/` |
| `benchmark/run_federated.py` | Federated over same packs → `results/federated/` |
| `benchmark/compare.py` | Scoreboard → `results/comparison/COMPARISON.md` |
| `benchmark/run_motadata_bakeoff.py` | Motadata L1 scoreboard |
| `benchmark/fault_taxonomy.py` | Fault bucket tags for Samples |
| `benchmark/tag_corpus_fault_buckets.py` | Stamp packs with taxonomy |
| `dashboard/server.py` | PoC console `:8765` |
| `dashboard/build_data.py` | Rebuild `data.js` from results + packs |
| `dashboard/index.html` | Guide / Samples / Conduct UI |
| `results/` | Artifacts (cite `RUN_IDS.md` for official runs) |

**First 5 files to read**

1. `benchmarking/README.md`
2. `benchmarking/benchmark/run_bakeoff.sh`
3. `benchmarking/benchmark/run_lean.py`
4. `benchmarking/benchmark/compare.py`
5. `benchmarking/dashboard/server.py`

**Cite:** ObserveOps accuracy → `adr001-rerun-20260723` in [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md). Never merge with OpenObserve peer %.

---

## 8) `datasets/` — what engines read

| Path | Contents |
|------|----------|
| `observeops/UC-*` | Frozen bakeoff packs (`topology`, metrics, logs, `ground_truth.json`, …) |
| `observeops/build_corpus.py` | Rebuild packs from the UC spec |
| `ingest_samples/observeops-replay/` | UC → `ingest.v1` streams |
| `ingest_samples/motadata-ingest/` | Motadata → `ingest.v1` (derived) |
| `ingest_samples/jsonl_resolved/` | Large Motadata dumps (**local / gitignored**) |
| `openobserve_incidents/` | Peer corpus — **separate** scoreboard |

**First 5 files to read**

1. `datasets/README.md`
2. [`rca-use-cases-only.md`](./rca-use-cases-only.md) — eval spec
3. `datasets/observeops/README.md`
4. `datasets/observeops/build_corpus.py`
5. `datasets/ingest_samples/README.md`

**GT rule:** ground truth is **human-authored**. Automation scores against it; it must not invent Motadata GT (see A1 in [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md)).

---

## 9) Common tasks (“I need to…”)

| I need to… | Do this |
|------------|---------|
| **Demo the PoC** | `dashboard/server.py` → follow [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) |
| **Diagnose one UC** | `python -m lean_rca diagnose UC-N --format report` |
| **Re-run official UC bakeoff** | `./benchmarking/benchmark/run_bakeoff.sh` |
| **Score Motadata L1** | `run_motadata_bakeoff.py` (packs from `build_motadata_incident.py`) |
| **Prove shared ingest → Lean** | `builders/n45_chain.py` |
| **Change Detect thresholds** | `ingestion-poc/detect/` (+ tests if present) |
| **Add a Lean rule / signature** | `lean-pipeline/core_engine/observeops/rules/` then re-diagnose |
| **Refresh Samples cards** | `tag_corpus_fault_buckets.py` → `dashboard/build_data.py` → restart dashboard |
| **Understand L0 vs F1 cost** | Read `results/costing/.../cost_report.md`; harness in `ingestion-poc/lab/` |
| **Find “what’s next” in product terms** | [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3 (`LIVE` / `CHANGE`) |

---

## 10) Config cheat sheet

| Knob | Meaning |
|------|---------|
| `PYTHONPATH=lean-pipeline:.` | Almost always required for Lean / many scripts |
| `repo_paths.py` | Canonical dirs; call `ensure_import_paths()` from tools that need it |
| `OBSERVEOPS_CORPUS` | Override pack root (default `datasets/observeops`) |
| `POC_DASHBOARD_HOST` / `PORT` / `TOKEN` | Dashboard bind + optional token |
| Vector / lab | See `ingestion-poc/vector/*.toml`, `ingestion-poc/compose/*.yml`, `lab/README.md` |
| OpenObserve fetch | `OPENOBSERVE_URL`, `ORG`, `USER`, `PASSWORD` (peer track only) |

No root `.env` is required for the basic UC path. Motadata dumps must exist locally under `jsonl_resolved/` (gitignored).

---

## 11) Pitfalls (read once)

1. **Two engines, one Detect** — don’t compare Lean vs Federated if Detect seeds differ; parity is the point ([`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md)).
2. **Three scoreboards** — ObserveOps UC ≠ Motadata L1 ≠ OpenObserve. Never blend % headlines.
3. **Bakeoff vs live ingest** — UC bakeoff uses frozen packs; ingest PoC is a parallel front door. Wire them with builders / `n45_chain`, don’t assume every dashboard KPI came from Vector.
4. **PYTHONPATH** — `ModuleNotFoundError: lean_rca` / `core_engine` almost always means missing `PYTHONPATH=lean-pipeline:.`.
5. **GT is sacred** — Samples checklist and Motadata `ground_truth.json` are human; don’t auto-generate “correct” roots for demos.
6. **Large dumps** — `jsonl_resolved/*.jsonl` and costing `work/` trees are local/gitignored; missing Motadata data ≠ broken Lean UC path.
7. **Lean-primary is an evaluation finding** — ADR-001 on this corpus; not a hard product lock forever.

---

## Where to go deeper

| Topic | Doc |
|-------|-----|
| Doc reading order | [`NAVIGATION.md`](./NAVIGATION.md) |
| Demo script | [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) |
| Workflow + open work | [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) |
| Ingest design | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) |
| Terms | [`GLOSSARY.md`](./GLOSSARY.md) |
| Lean study notes | [`./learning/Lean-decoded.md`](./learning/Lean-decoded.md) |
| Federated study notes | [`./learning/Federated-decoded.md`](./learning/Federated-decoded.md) |

*Last updated: 2026-07-22*
