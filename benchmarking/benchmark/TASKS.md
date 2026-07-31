# ObserveOps Benchmark — Task Status

**Corpus version:** 1.1.0 (`datasets/observeops/` — manifest.yaml + 7-day time-series; UC-3b + events.json)  
**Last updated:** 2026-07-16 (ObserveOps critical path A→B→D complete; primary evaluation engine per ADR-001)  
**Canonical roadmap:** [`docs/ROADMAP.md`](../../docs/ROADMAP.md) · decision: [`docs/ADR-001-lean-primary-engine.md`](../../docs/ADR-001-lean-primary-engine.md)

## Latest bakeoffs

| Run | Result |
|-----|--------|
| `bakeoff-phase-a-001` | Both 5/5; primary evaluation engine called (ADR-001) |
| `bakeoff-phase-b-002` | Corpus v1.1.0; both 5/5; lean Tier 3 on UC-1/UC-3; four-axis + efficiency; **ADR-era decision snapshot** |
| **`adr001-rerun-20260723`** | Parity shared-detect; both 5/5; **current scoreboard cite** ([`COMPARISON.md`](../results/comparison/COMPARISON.md), [`RUN_IDS.md`](../results/comparison/RUN_IDS.md)) |
| `bakeoff-phase-b-001` | Historical; superseded by b-002 for ADR-era headline numbers |

Reports: [`../results/comparison/COMPARISON.md`](../results/comparison/COMPARISON.md), [`../results/comparison/DECISION.md`](../results/comparison/DECISION.md)

## Step 1 — Corpus

| Task | Status | Artifact |
|------|--------|----------|
| UC bundles | **done** | `datasets/observeops/UC-*/` |
| Topology / anomalies / GT / metrics schemas | **done** | `datasets/observeops/schema/` |
| Typed topology schema (lean) | **done** | `lean-pipeline/core_engine/schema/observeops_topology.json` |
| manifest.yaml + topology hash | **done** | `datasets/observeops/manifest.yaml` |
| 7-day metric time-series | **done** | `datasets/observeops/build_corpus.py` |
| Schema validation | **done** | `benchmarking/benchmark/validate_corpus.py` |

## Step 2 — Federated RCA

| Task | Status | Artifact |
|------|--------|----------|
| Corpus adapter | **done** | `benchmark/adapters/observeops_federated.py` |
| Hop logs per run | **done** | `results/federated/UC-N/run-*/hop_logs.json` |
| Murphy causal rules on topology | **done** | SimulatedMetricStore + layer propagation |
| Fusion path (no lean-heuristic fallback) | **done** | Murphy posteriors; UC-2/3 may use `earliest_onset_upstream` override |
| Reproducibility N=20 | **done** | `results/reproducibility_federated_full-repro.json` (~40% overall) |

## Step 3 — Lean RCA

| Task | Status | Artifact |
|------|--------|----------|
| ObserveOps rules | **done** | `lean-pipeline/core_engine/observeops/rules/` |
| Lean core (BFS, info-gain, CARE, causal) | **done** | `lean-pipeline/core_engine/lean/` |
| Engine + SRE report fields | **done** | `engine.py` + `lean_rca` (`causal_chain`, `blast_radius`, `remediation`) |
| Signature inference (no GT leak) | **done** | `lean/signature.py` |
| Unit tests UC-1..UC-5 | **done** | `lean-pipeline/core_engine/tests/` (36 passed) |
| Reproducibility N=20 | **done** | `results/reproducibility_lean_full-repro.json` (100%) |

## Step 4 — Comparison

| Task | Status | Artifact |
|------|--------|----------|
| Compare + four-axis + efficiency | **done** | `benchmark/compare.py` → `results/comparison/` |
| ObserveOps engine decision | **done** | Primary evaluation engine (ADR-001); not a finalized product commitment |

## Optional / deferred

- Federated Phase C ingest & Phase E capacity — only if microservice track prioritized  
- Lean B5 continuous causal memory  

## Agent continuation

See [AGENTS.md](AGENTS.md). Prefer `./benchmarking/benchmark/run_bakeoff.sh` for a matched rerun.
