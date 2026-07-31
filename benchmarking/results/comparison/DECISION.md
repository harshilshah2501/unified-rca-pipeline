# ObserveOps — Engine Evaluation Memo

**Date:** 2026-07-16  
**Corpus:** [`rca-use-cases-only.md`](../../../docs/rca-use-cases-only.md) → `datasets/observeops/`  
**Matched runs:** `bakeoff-phase-a-001`, `bakeoff-phase-b-001`, **`bakeoff-phase-b-002`** (corpus v1.1.0 — ADR-era decision evidence)  
**Current scoreboard:** [`COMPARISON.md`](./COMPARISON.md) (latest: **`adr001-rerun-20260723`**) · run index [`RUN_IDS.md`](./RUN_IDS.md)  
**ADR:** [`docs/ADR-001-lean-primary-engine.md`](../../../docs/ADR-001-lean-primary-engine.md)  
**Decision guide:** [`docs/README.md`](../../../docs/README.md#lean-vs-federated--design-choice--decision-guide)

## Recommendation (corpus-scoped; not finalized)

**On ObserveOps UC-1..UC-5, bakeoff evidence favors lean** for further classic-infra evaluation. Federated stays a valid comparator and optional hybrid candidate.

Both engines are **5/5** on root-CI and signature accuracy. Lean wins on the remaining axes that matter for this corpus:

| Axis | Federated | Lean | Edge |
|------|-----------|------|------|
| Accuracy | 5/5 | 5/5 | tie (measure vs a floor; not “must be 100% forever”) |
| Reproducibility (N=20) | **~40%** (UC-2/3/5 multi-hash) | **100%** | lean |
| Verifiability | Higher main-path %; fusion audit | Tier labels + CARE/causal log + SRE report | lean (audit narrative)* |
| Efficiency | Avg observations **5.60**; heavier stack | Avg **5.00**; best-first vs BFS metrics | lean |
| Causal Validity | Murphy partial (costly if global) | Recommended only on CARE→Tier 3 (UC-1/UC-3) | design choice — see docs |

\*On `bakeoff-phase-b-002`, federated scores **100% main-path** (no CARE fallback) vs lean **60%** (CARE on UC-1/UC-3). Lean still wins **Verifiability** for explicit tier/CARE/causal audit fields — not raw main-path % alone.

## Why not “federated only”

1. **Reproducibility** — Gibbs / synthetic store paths still produce multi-hash runs on some UCs.
2. **Cost / complexity** — Panorama + Murphy + Nezha + dual tiers for layers lean already resolves on a typed CI graph (**Roadblock 1b** + **Roadblock 5**).
3. **ObserveOps fit** — classic infra tickets prioritize bit-stable, auditable answers over fleet-wide structural causation.
4. **Fair scoring already exists** — **Roadblock 4** is handled by corpus convention (shared GT + matched bakeoff); Murphy CV does not improve top-1 accuracy on that contract.

Murphy’s causal-inference edge is real; it loses the ObserveOps cost–benefit when Reproducibility, Verifiability, Roadblock **4** (fair GT bakeoff already in place), and Roadblock **5** dominate. Details: [docs/README.md decision guide](../../../docs/README.md#lean-vs-federated--design-choice--decision-guide).

## Hybrid (optional, later)

| Workload | Engine |
|----------|--------|
| Classic infra (Network → Host → VM → OS → App) — **this corpus** | **Lean** |
| Microservice code-path / gray-failure / pair mining | Federated (Panorama + Nezha depth; Murphy as macro) |

## Checklist

| Phase | Status |
|-------|--------|
| A — Bakeoff close + primary evaluation engine (ADR-001) | **Done** |
| B — Lean PRD depth (tiers, CARE→causal, signatures, efficiency) | **Done** (`bakeoff-phase-b-002` canonical; `b-001` historical) |
| D — Package lean API/CLI/SRE report/systemd | **Done** (`lean_rca`, `lean-rca.service`) |
| C / E — Federated ingest & capacity | Deferred (microservice track) |
| B5 — Continuous causal memory | Optional later |

## Phase B tier snapshot (`bakeoff-phase-b-002`)

| UC | Tier | CARE | Causal verified | Best-first / naive BFS |
|----|------|------|-----------------|------------------------|
| UC-1 | 3 | yes | yes | 3 / 3 |
| UC-2 | 1 | no | — | 4 / 5 |
| UC-3 | 3 | yes | yes | 3 / 4 |
| UC-4 | 1 | no | — | 1 / 1 |
| UC-5 | 1 | no | — | 1 / 1 |
| UC-3b (lean only) | 3 | yes | yes | 3 / 4 — root stays datastore despite early switch |
