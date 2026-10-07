# PoC explore & demo guide

**Audience:** you, stakeholders, or a colleague opening the repo cold  
**Goal:** walk the Unified RCA PoC without reading every design doc first  
**Canonical next actions:** [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3 (`LIVE` → `CHANGE`)  
**Full doc map:** [`NAVIGATION.md`](./NAVIGATION.md)  
**Code map:** [`CODE_GUIDE.md`](./CODE_GUIDE.md)

---

## 1. What this PoC proves (30-second pitch)

1. **Same frozen incidents, two engines** — Lean (primary on classic infra) vs Federated (comparator).
2. **Shared ingest fabric** — Motadata / ObserveOps → `ingest.v1` → **L0** (Lean-only writes) or **F1** (Lean **and** Federated writes) → shared threshold Detect → RCA packs.  
3. **Measured, not marketing** — UC bakeoff Lean/Fed 5/5 both (`adr001-rerun-20260723`); fair OO UC **1/5**; Motadata L1 7/7 both; pro6000 ~67K Dragonfly EPS; L0 vs F1 cost report.  
4. **Human GT stays authoritative** — dashboard Samples checklist; automation only scores against your labels.

**Demo surfaces:** `#incident` = stakeholder-friendly report (UC + Motadata L1). `#samples` = manual verify checklist. Workflow sim = algorithm narration only when asked.

OpenObserve **peer-29** % is **out of PoC console scope** (hidden in the UI). Fair ObserveOps UC OO compare (1/5) is documented under [`LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) — do not merge with peer %.

---

## 2. Start here — PoC console (best demo surface)

```bash
# From repo root (or use systemd: unified-rca-dashboard)
.venv/bin/python benchmarking/dashboard/server.py
# → http://127.0.0.1:8765/
```

| URL hash | Show this |
|----------|-----------|
| [`#guide`](http://127.0.0.1:8765/#guide) | Newcomer path + **interactive ingest / Lean·Federated pipeline** (click nodes, Play flow) |
| [`/rca-workflow-sim.html`](http://127.0.0.1:8765/rca-workflow-sim.html) | **Algorithm sim** — shared threshold Detect → Lean (best-first / CARE) vs Federated (Murphy / fusion) · [canvas](vscode://file/root/.cursor/projects/root-Harshil-PoCs-Unified-RCA/canvases/rca-workflow-sim.canvas.tsx) |
| [`#incident`](http://127.0.0.1:8765/#incident) | **Incident Analysis** — OO-style human report; ObserveOps UC + Motadata L1 (Lean / Fed / OO tabs) · [fields canvas](vscode://file/root/.cursor/projects/root-Harshil-PoCs-Unified-RCA/canvases/incident-report-fields.canvas.tsx) |
| [`#samples`](http://127.0.0.1:8765/#samples) | **Manual verify** — UC + Motadata cards (GT vs Lean vs Fed, fault buckets) |
| [`#conduct`](http://127.0.0.1:8765/#conduct) | Run Motadata broaden / UC bakeoff / lab EPS / Motadata L1 (live logs) |
| [`#overview`](http://127.0.0.1:8765/#overview) | Bakeoff + Motadata L1 + lab EPS KPIs |
| [`#uc`](http://127.0.0.1:8765/#uc) | UC-1..5 scoreboard table |
| [`#verdict`](http://127.0.0.1:8765/#verdict) | Lean-primary evaluation finding (ADR-001) |

**Demo script (15–20 min):**

1. **Guide** — Play flow (Both → then Lean-only). One sentence: shared Detect, then engine fork.  
2. **Incident Analysis** — UC-4 Lean, switch OO (miss); Motadata `motadata-apm-001` Lean (real export). Keep language human.  
3. **RCA workflow sim** — only if they ask *how* the engines differ.  
4. **Samples** — Pick `motadata-apm-001` (error rate). Walk the checklist aloud: seed → root → signature → evidence.  
5. **Overview / Verdict** — Lean wins repro/audit on UC; Motadata L1 is a tie on root+sig.

Rebuild Samples data after new packs:

```bash
.venv/bin/python benchmarking/benchmark/tag_corpus_fault_buckets.py
.venv/bin/python benchmarking/dashboard/build_data.py
sudo systemctl restart unified-rca-dashboard   # if using systemd
```

---

## 3. Reproduce bakeoffs (offline evidence)

### ObserveOps UC-1..UC-5

```bash
./benchmarking/benchmark/run_bakeoff.sh
# → benchmarking/results/comparison/COMPARISON.md
# Cite run: see benchmarking/results/comparison/RUN_IDS.md (adr001-rerun-20260723)
```

Single-pack Lean diagnose:

```bash
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report
```

### Motadata L1 (human GT → score)

```bash
# Rebuild packs (optional) then bakeoff
.venv/bin/python ingestion-poc/adapters/build_motadata_incident.py
.venv/bin/python benchmarking/benchmark/run_motadata_bakeoff.py
# → benchmarking/results/motadata/COMPARISON.md
```

**A1 reminder:** new Motadata incidents need **you** to write `ground_truth.json`, then manual verify on `#samples`. Do not auto-generate GT.

---

## 4. Ingest & capacity (lab story)

| Story | Command | Artifact |
|-------|---------|----------|
| Lab EPS (Dragonfly + F1 fan-out) | `python3 ingestion-poc/lab/run_lab_eps.py` | `benchmarking/capacity/lab/<run_id>/` |
| pro6000 headline | `DF_PROACTOR_THREADS=8 python3 ingestion-poc/lab/run_lab_eps.py --seconds 30 --workers 16` | ~67K EPS in [`CAPACITY.md`](../federated-pipeline/docs/CAPACITY.md) |
| L0 vs F1 cost | `python3 ingestion-poc/lab/run_cost_harness.py --events 500000 --vector --seconds-soak 120` | [`cost_report.md`](../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md) |
| Inventory topology | `python3 ingestion-poc/adapters/build_motadata_inventory_topology.py --refresh-incidents` | `motadata-ingest/topology.json` |

Conduct UI can SSH lab EPS to `pro6000-server` when configured.

---

## 5. How to explore the repo (map)

| Question | Go to |
|----------|--------|
| What next? | [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3 |
| Stakeholder narrative | [`POC_BRIEFING.md`](./POC_BRIEFING.md) |
| Fault types vs Datadog/Dynatrace | [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) · [`VENDOR_BENCHMARKS.md`](./VENDOR_BENCHMARKS.md) |
| Why Lean primary? | [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) |
| Ingest design | [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) · [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) |
| Fair Lean vs Fed | [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) |
| Step-2 white space (I2) | [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) |
| Everything else | [`NAVIGATION.md`](./NAVIGATION.md) |

**Code entrypoints:**

| Area | Path |
|------|------|
| Lean engine | `lean-pipeline/` · `python -m lean_rca` |
| Federated PoC | `federated-pipeline/poc/` |
| Motadata adapters | `ingestion-poc/adapters/` |
| Shared detect | `ingestion-poc/detect/` |
| F1 / Vector | `ingestion-poc/pipeline/f1_run.py` · `ingestion-poc/vector/` |
| Lab / cost | `ingestion-poc/lab/` |
| Bakeoff runners | `benchmarking/benchmark/` |
| Dashboard | `benchmarking/dashboard/` |

---

## 6. Manual verify checklist (every new Motadata GT)

1. Open `#samples` → filter Motadata / fault bucket.  
2. Confirm **GT** root + signature match your intent.  
3. Confirm **Lean** and **Fed** roots/sigs (PASS/FAIL chips).  
4. Mentally: symptom seed CI → localized root → signature name → skim evidence.  
5. Tag bucket: `tag_corpus_fault_buckets.py` → `build_data.py` → refresh UI.

---

## 7. What not to demo as “done”

| Topic | Status |
|-------|--------|
| Gray-failure / Panorama detect (D4) | No corpus yet |
| I2 execution-path diff in verdict | Stretch / gated |
| Live syslog/Prometheus collector (A2) | Next work |
| Real CI/CD change feed (A3) | Next work |
| OpenObserve accuracy % in console | Out of PoC scope |
| Samples confirm on `motadata-deps-001` (+ any new Motadata packs) | **Your** manual labeling on `#samples` |

---

## 8. One-page demo order (print this)

```
1. Console #guide       → Play flow (shared Detect, then engine fork)
2. Console #incident    → UC-4 Lean report; OO tab (miss); Motadata apm-001
3. Console #samples     → checklist on motadata-apm-001 (or UC-2)
4. COMPARISON.md        → UC 5/5 · Lean repro 100%
5. motadata COMPARISON  → L1 7/7 tie
6. cost_report / CAPACITY → ≥50K EPS gate met on pro6000
7. Close with next: `LIVE` smoke → `CHANGE` feed ([`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3)
```

*Guide updated 2026-07-28 (Incident Analysis UI · Motadata L1 in `#incident` · plain L0/F1 gloss). If status drifts, trust [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3 over older briefing slides.*
