# Unified RCA — Code guide (for newcomers)

**Audience:** engineers opening this repo for the first time  
**Goal:** know *where Motadata product code lives*, *what the evaluation bakeoff is*, and *which files to open next*  
**Not this doc:** product narrative → [`POC_BRIEFING.md`](./POC_BRIEFING.md) · full doc map → [`NAVIGATION.md`](./NAVIGATION.md) · click-through demo → [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) · edit hygiene → [`REPO_HYGIENE.md`](./REPO_HYGIENE.md)

---

## Cognitive path (code)

```
Folders = stages → One picture of data flow → Touch it (3 commands)
  → Area guides (Motadata A∥B · ingest · Lean · Federated · bakeoff · data)
  → Common tasks · env cheat sheet · pitfalls
```

| Stage | Question | Section |
|-------|----------|---------|
| **1. Map** | What are these folders *for*? | §1 |
| **2. Flow** | How does an event become a store row or a verdict? | §2 |
| **3. Touch** | Can I run something in 10 minutes? | §3 |
| **4. Areas** | Where do I dig for my task? | §4–§9 |
| **5. Tasks** | “I need to …” recipes | §10 |
| **6. Config** | Env vars / PYTHONPATH | §11 |
| **7. Pitfalls** | What trips everyone up? | §12 |

**One-line code contract (current Motadata stage):** shared `ingest.v1` after Identity → **Pillar A** (`history/` sketches) ∥ **Pillar B** (`map/` graph) under [`pillar-ab-implementation/`](../pillar-ab-implementation/README.md). **Lean** and **Federated** remain the ObserveOps UC **evaluation** bakeoff (ADR-001) — not the Motadata Pillar A∥B product tree.

Edit hygiene: [`REPO_HYGIENE.md`](./REPO_HYGIENE.md). Tier-1 reading door: [`observeops/OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md).

---

## 1) Folder map (remember this)

```
Unified-RCA/
├── repo_paths.py                 # shared path constants + sys.path helper
├── docs/                         # hub teaching (edit topic folders; flat names = :8765 symlinks)
├── pillar-ab-implementation/     # Motadata Pillar A∥B — contracts SoT + owner packages
├── ingestion-poc/                # normalize → ingest.v1 · shared Detect · Lean/Fed pack writers
├── labs/                         # vendor fault labs (Edge Delta / Datadog / Dynatrace)
├── datasets/                     # frozen corpora + ingest streams (data in, not logic)
├── lean-pipeline/                # evaluation engine — ObserveOps UC bakeoff (ADR-001)
├── federated-pipeline/           # evaluation comparator (Panorama → Murphy → Nezha)
├── benchmarking/                 # bakeoff runners, results, PoC console (:8765)
├── KR Plan/                      # management PDFs / OKR workbooks
└── _archive/                     # parked snapshots — not the live hub
```

### Motadata product surface (edit here day-to-day)

| Folder | Job in one sentence |
|--------|---------------------|
| [`pillar-ab-implementation/`](../pillar-ab-implementation/README.md) | Motadata **Pillar A** (sketches / `history/`) ∥ **Pillar B** (graph / `map/`) — contracts SoT, packages, optional read-join |
| [`ingestion-poc/`](../ingestion-poc/) | Shared front door: Motadata dumps / UC replay → `ingest.v1` + Detect seeds (+ Lean/Fed pack builders) |
| [`docs/`](./) | ObserveOps HLD / fabric visuals / Motadata teaching — **not** runtime |
| [`labs/`](../labs/) | Vendor fault labs that feed Motadata and unveil pages |

Canonical contracts live under `pillar-ab-implementation/contracts/` (JSON schemas, `GRAPH_QNA`, map write/read). Package `docs/` folders are **symlinks** into that tree — see [`REPO_HYGIENE.md`](./REPO_HYGIENE.md).

### Evaluation / host (not the Motadata Pillar tree)

| Folder | Job in one sentence |
|--------|---------------------|
| `lean-pipeline/` | Classic-infra RCA on typed CI graphs — **primary bakeoff** brain for UC-1..UC-5 |
| `federated-pipeline/` | Multi-algo comparator for the same UC incidents (large Nezha tree — not day-to-day Motadata edit) |
| `benchmarking/` | Score engines vs human GT; host the PoC console on `:8765` |
| `datasets/` | **What** we diagnose (ObserveOps UC packs, Motadata streams, OpenObserve peer) |

Design docs live under `docs/`. Runtime Motadata writers live under `pillar-ab-implementation/`. Runtime code does **not** belong under `docs/` or `benchmarking/dashboard/` (dashboard mounts hub via symlinks only).

---

## 2) One picture — two tracks

### Track A — Motadata fabric (current product slice)

```
Sources                 Front door              After Identity (E2)
─────────               ──────────              ───────────────────
Motadata dumps     ──►  ingest.v1 JSONL   ──►  fact_kind fan-out
ObserveOps replay  ──►  (ingestion-poc)        ├── metric_sample → Pillar A → history/ (sketch.v1)
Lab fixtures       ──►                         └── topo_update   → Pillar B → map/     (graph_*)
                                                          │
                                                          ▼
                                              dest profile (PoC: files.v1 under poc/out/)
                                                          │
                                                          ▼
                                              Detect onward reads map/ ∥ history/
                                              (docs: fabric + ObserveOps HLD)
```

Start: [`pillar-ab-implementation/README.md`](../pillar-ab-implementation/README.md) · post-E2 fixtures: [`E2_INPUT_FIXTURES.md`](../pillar-ab-implementation/E2_INPUT_FIXTURES.md) · I/O chain: [`OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md).

### Track B — ObserveOps UC bakeoff (evaluation history)

```
Frozen UC packs              Shared Detect                 Engines diverge
───────────────              ─────────────                 ───────────────
datasets/observeops/UC-* ──► (ingest PoC optional)   ├──► lean_rca diagnose
                             threshold seeds         └──► federated orchestrator
                                                              │
                                                              ▼
                                                 bakeoff → COMPARISON.md
                                                              ▼
                                                 dashboard (:8765)
```

**Important:** the UC **bakeoff** usually reads **frozen** `datasets/observeops/UC-*` packs directly. The ingest path (`f1_run` → builders) proves the *product-shaped* front door into Lean/Fed packs; Motadata Pillar A∥B writers consume **resolved** `ingest.v1` (lab fixtures or Motadata adapters) — they are not a rename of Lean.

Canonical product stages: **Ingest → Detect → Localize → Identify → Verify** — see [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md). Fabric stages **E1–E5** (Collect → … → Stores) sit under Detect’s always-on map/history — see [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md).

---

## 3) Touch it (10 minutes)

From repo root, with `.venv` already present:

```bash
# 1) Docs hub + PoC console
.venv/bin/python benchmarking/dashboard/server.py
# → http://127.0.0.1:8765/                 (#guide · #incident · #samples)
# → http://127.0.0.1:8765/observeops-pipeline-hld.html   (Our HLD door)

# 2) Motadata Pillar A∥B unit suites (current product code)
cd pillar-ab-implementation/pillar-a/poc && make install && make test-all
cd ../../pillar-b/poc && make install && make test-all

# 3) One Lean diagnose on a frozen UC pack (evaluation track)
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report
```

Optional bakeoff / ingest smokes:

```bash
./benchmarking/benchmark/run_bakeoff.sh
# → benchmarking/results/comparison/COMPARISON.md

PYTHONPATH=lean-pipeline:. .venv/bin/python ingestion-poc/builders/n45_chain.py
```

---

## 4) `pillar-ab-implementation/` — Motadata Pillar A∥B

**Role:** Motadata product slice after Identity — write **`history/`** (Pillar A sketches) and **`map/`** (Pillar B graph) from the same `ingest.v1` stream. This is **not** Lean or Federated.

| Path | What it does |
|------|----------------|
| `contracts/` | **Source of truth** — schemas, `GRAPH_QNA`, `MAP_WRITE_READ_RECORD`, Gate B dest profile |
| `contracts/schemas/` | `ingest_v1`, `sketch.v1`, graph node/edge / snapshot JSON schemas |
| `E2_INPUT_FIXTURES.md` | What writers consume after E2 (lab JSONL paths + `fact_kind`) |
| `pillar-a/poc/` | Sketch / percentile writer PoC (`history/` keys; `files.v1` dest) |
| `pillar-b/poc/` | Graph materializer PoC (`map/` keys; `topo_update` + seed topology) |
| `integration/` | Optional **read-join** harness after both unit suites are green (not an A∪B merge) |
| `scope/` | Motadata kickoff / merged implementation scope |
| `pillar-a/docs/`, `pillar-b/docs/` | **Symlinks** into contracts / fabric — do not replace with copies |

**First 5 files to read**

1. [`pillar-ab-implementation/README.md`](../pillar-ab-implementation/README.md)
2. [`E2_INPUT_FIXTURES.md`](../pillar-ab-implementation/E2_INPUT_FIXTURES.md)
3. [`contracts/MAP_WRITE_READ_RECORD.md`](../pillar-ab-implementation/contracts/MAP_WRITE_READ_RECORD.md)
4. [`contracts/GATE_B_DEST_PROFILE.md`](../pillar-ab-implementation/contracts/GATE_B_DEST_PROFILE.md)
5. [`docs/fabric/README.md`](./fabric/README.md) — ordered fabric visuals

**Run**

```bash
cd pillar-ab-implementation/pillar-a/poc && make install && make test-all
cd ../../pillar-b/poc && make install && make test-all
```

Sample estate (resolved `ingest.v1`): `pillar-a/poc/sample_estate/customer_checkout/`, `pillar-b/poc/sample_estate/customer_checkout/`, `integration/sample_estate/customer_checkout/`.

Former combined PoC lives under [`_archive/pillar-ab-combined-poc-2026-08/`](../_archive/pillar-ab-combined-poc-2026-08/) — do not expand.

---

## 5) `ingestion-poc/` — shared fabric

**Role:** everything *before* Motadata Pillar writers **and** before the two bakeoff engines diverge.

**Start here:** [`ingestion-poc/README.md`](../ingestion-poc/README.md) — layout, commands, and **local dump policy** (~4.3G Motadata `jsonl_resolved/` + ~2.8G Nezha `rca_data/` are gitignored; not required for UC replay or Pillar tests).

| Path | What it does |
|------|----------------|
| `replay/observeops_to_ingest_v1.py` | UC bundles → `ingest.v1` JSONL |
| `adapters/motadata_to_ingest_v1.py` | Motadata dumps → `ingest.v1` (**needs local dumps**) |
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

1. [`ingestion-poc/README.md`](../ingestion-poc/README.md)
2. [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) — the contract (`ingest.v1`)
3. `ingestion-poc/pipeline/f1_run.py`
4. `ingestion-poc/detect/threshold_detect.py`
5. [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) — design (why L0/F1)

Per-folder READMEs: `ingestion-poc/{adapters,detect,pipeline,builders,replay,vector,lab}/README.md`.

---

## 6) `lean-pipeline/` — evaluation engine (UC bakeoff)

**Role:** classic infrastructure RCA on typed CI graphs (network → host → VM → app). **Primary ObserveOps UC bakeoff brain** (ADR-001) — not Motadata Pillar A∥B.

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

## 7) `federated-pipeline/` — evaluation comparator

**Role:** same UC incidents, different localization/identify stack (bakeoff fairness). **Not** the Motadata Pillar A∥B product path and **not** the ObserveOps shipping diagnose API.

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

## 8) `benchmarking/` — score & show

**Role:** fair runners, scoreboards, PoC console. Hosts `:8765` by **symlinking** `docs/` and `pillar-ab-implementation/` — never fork articles under `dashboard/`.

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

## 9) `datasets/` — what engines and adapters read

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

## 10) Common tasks (“I need to…”)

| I need to… | Do this |
|------------|---------|
| **Orient Motadata Pillar A∥B** | [`pillar-ab-implementation/README.md`](../pillar-ab-implementation/README.md) → [`OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md) |
| **Run Pillar A / B unit suites** | `pillar-a/poc` or `pillar-b/poc` → `make install && make test-all` |
| **See post-E2 writer input** | [`E2_INPUT_FIXTURES.md`](../pillar-ab-implementation/E2_INPUT_FIXTURES.md) + `sample_estate/customer_checkout/` |
| **Change map/sketch contracts** | Edit **`pillar-ab-implementation/contracts/`** only ([`REPO_HYGIENE.md`](./REPO_HYGIENE.md)) |
| **Demo the PoC console** | `dashboard/server.py` → follow [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) |
| **Diagnose one UC (bakeoff)** | `python -m lean_rca diagnose UC-N --format report` |
| **Re-run official UC bakeoff** | `./benchmarking/benchmark/run_bakeoff.sh` |
| **Score Motadata L1 bakeoff** | `run_motadata_bakeoff.py` (packs from `build_motadata_incident.py`) — separate from Pillar A∥B writers |
| **Prove shared ingest → Lean** | `builders/n45_chain.py` |
| **Change Detect thresholds** | `ingestion-poc/detect/` (+ tests if present) |
| **Add a Lean rule / signature** | `lean-pipeline/core_engine/observeops/rules/` then re-diagnose |
| **Refresh Samples cards** | `tag_corpus_fault_buckets.py` → `dashboard/build_data.py` → restart dashboard |
| **Understand L0 vs F1 cost** | Read `results/costing/.../cost_report.md`; harness in `ingestion-poc/lab/` |
| **Find “what’s next” in product terms** | [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3 (`LIVE` / `CHANGE`) |

---

## 11) Config cheat sheet

| Knob | Meaning |
|------|---------|
| `PYTHONPATH=lean-pipeline:.` | Required for Lean / many bakeoff scripts |
| Which Python / venv | **Repo-root** `.venv` for hub, ingest PoC, bakeoff, dashboard (`benchmarking/dashboard/server.py`). **Package** `pillar-*/poc/.venv` only when developing or zipping that handoff package (`make install` there). Do not use `federated-pipeline/murphy/.venv` for Motadata work. |
| `repo_paths.py` | Canonical dirs: datasets, lean/federated, labs, **`PILLAR_AB`**, **`INGESTION_POC`**, **`DOCS`**, ingest samples — call `ensure_import_paths()` from shared tools |
| `OBSERVEOPS_CORPUS` | Override pack root (default `datasets/observeops`) |
| `POC_DASHBOARD_HOST` / `PORT` / `TOKEN` | Dashboard bind + optional token |
| Vector / lab | See `ingestion-poc/vector/*.toml`, `ingestion-poc/compose/*.yml`, `lab/README.md` |
| OpenObserve fetch | `OPENOBSERVE_URL`, `ORG`, `USER`, `PASSWORD` (peer track only) |

No root `.env` is required for the basic UC path. Motadata dumps must exist locally under `jsonl_resolved/` (gitignored) for Motadata **adapters**; Pillar A∥B **sample estate** under `pillar-*/poc/sample_estate/` do not need those dumps.

---

## 12) Pitfalls (read once)

1. **Motadata ≠ Lean/Federated** — Pillar A∥B writers under `pillar-ab-implementation/` are the Motadata product slice. Lean/Federated are the UC **evaluation** bakeoff. Do not treat `lean-pipeline/` as “where Motadata lives.”
2. **Two engines, one Detect (bakeoff)** — don’t compare Lean vs Federated if Detect seeds differ; parity is the point ([`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md)).
3. **Three scoreboards** — ObserveOps UC ≠ Motadata L1 ≠ OpenObserve. Never blend % headlines. Motadata L1 bakeoff packs ≠ Pillar A∥B `map/`/`history/` PoC output.
4. **Bakeoff vs live ingest vs Pillar writers** — UC bakeoff uses frozen packs; ingest PoC is a front door; Pillar A∥B consume resolved `ingest.v1`. Don’t assume every dashboard KPI came from Vector or from Vortex.
5. **PYTHONPATH** — `ModuleNotFoundError: lean_rca` / `core_engine` almost always means missing `PYTHONPATH=lean-pipeline:.`.
6. **Wrong venv** — Nested `.venv` trees (murphy, pillar pocs) are easy to activate by accident. Prefer repo-root `.venv` unless you are inside a package handoff.
7. **GT is sacred** — Samples checklist and Motadata `ground_truth.json` are human; don’t auto-generate “correct” roots for demos.
8. **Large dumps** — `jsonl_resolved/*.jsonl` and Nezha `rca_data/` are local/gitignored; missing Motadata dumps ≠ broken Lean UC path or broken Pillar unit fixtures. See [`ingestion-poc/README.md`](../ingestion-poc/README.md).
9. **Lean-primary is an evaluation finding** — ADR-001 on the ObserveOps UC corpus; not a Motadata product lock.
10. **Edit contracts in one place** — `pillar-ab-implementation/contracts/` is SoT. Do not fork copies under `pillar-*/contracts/` or under `_archive/exports/`.
11. **“Tier” means three things** — Prefer **hub Tier** / **evidentiary Tier** / **storage Tier** on first use ([`OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md), [`GLOSSARY.md`](./GLOSSARY.md)).

---

## Where to go deeper

| Topic | Doc |
|-------|-----|
| Doc reading order | [`NAVIGATION.md`](./NAVIGATION.md) |
| Hub Tier 1 + implementer I/O chain | [`observeops/OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md) |
| What to edit where | [`REPO_HYGIENE.md`](./REPO_HYGIENE.md) |
| Motadata Pillar A∥B code | [`pillar-ab-implementation/README.md`](../pillar-ab-implementation/README.md) |
| Demo script | [`POC_DEMO_GUIDE.md`](./POC_DEMO_GUIDE.md) |
| Workflow + open work | [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) |
| Ingest design | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) · [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) |
| Terms | [`GLOSSARY.md`](./GLOSSARY.md) |
| Lean study notes | [`./learning/Lean-decoded.md`](./learning/Lean-decoded.md) |
| Federated study notes | [`./learning/Federated-decoded.md`](./learning/Federated-decoded.md) |

*Last updated: 2026-09-04*
