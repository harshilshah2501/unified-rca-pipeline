# ObserveOps — Engine Evaluation Memo

**Date:** 2026-07-13  
**Corpus:** [`rca-use-cases-only.md`](../../../docs/rca-use-cases-only.md) → `datasets/observeops/`  
**Matched runs:** `bakeoff-phase-a-001`, `bakeoff-phase-b-001`, **`bakeoff-phase-b-002`** (corpus v1.1.0 — events + shared-upstream-under-ambiguity)  
**Report:** [`COMPARISON.md`](./COMPARISON.md) (latest: `bakeoff-phase-b-002`)  
**ADR:** [`docs/ADR-001-lean-primary-engine.md`](../../../docs/ADR-001-lean-primary-engine.md)  
**Decision guide:** [`docs/README.md`](../../../docs/README.md#lean-vs-federated--design-choice--decision-guide)

## Recommendation (corpus-scoped; not finalized)

**On ObserveOps UC-1..UC-5, bakeoff evidence favors lean** for further classic-infra evaluation. Federated stays a valid comparator and optional hybrid candidate.

Both engines are **5/5** on root-CI and signature accuracy. Lean wins on the remaining axes that matter for this corpus:

| Axis | Federated | Lean | Edge |
|------|-----------|------|------|
| Accuracy | 5/5 | 5/5 | tie (measure vs a floor; not “must be 100% forever”) |
| Reproducibility (N=20) | **~40%** (UC-2/3/5 multi-hash) | **100%** | lean |
| Verifiability | Fusion path + logged overrides | Tier labels + CARE/causal log + SRE report | lean |
| Efficiency | Higher avg observations; heavier stack | Fewer observations; best-first vs BFS metrics | lean |
| Causal Validity | Murphy partial (costly if global) | Recommended only on CARE→Tier 3 (UC-1/UC-3) | design choice — see docs |

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
| A — Bakeoff close + lean primary | **Done** |
| B — Lean PRD depth (tiers, CARE→causal, signatures, efficiency) | **Done** (`bakeoff-phase-b-001`) |
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
