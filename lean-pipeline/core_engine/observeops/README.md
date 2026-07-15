# Lean ObserveOps RCA Engine

Best-first upstream walk over the invocation graph with info-gain scoring,
temporal onset ranking, conditional CARE (Tier 2), and scoped causal verification (Tier 3).

## Layout

| Path | Role |
|------|------|
| `engine.py` | Orchestrates ingest, lean core search, CARE/causal tiers, rules, signature |
| `signals.yaml` | CI-type → signal → rule bindings (decisive signals per UC) |
| `registry.py` | Loads and caches `signals.yaml` for rules and decisive signals |
| `ingest/bundle.py` | Frozen corpus bundle → typed graph |
| `rules/shared_upstream.py` | UC-1 / UC-3 shared-host or datastore convergence |
| `rules/datastore_contributor.py` | UC-3 noisy-neighbor contributor |
| `rules/upstream_healthy.py` | UC-5 anti-false-positive gate |
| `../lean/` | Invocation graph, search, info-gain, temporal, CARE, causal, signature |

## Diagnosis flow

1. **Invocation graph** — `InvocationGraph.from_topology(bundle["topology"])`
2. **Best-first walk** — upstream from `symptom_seed.ci` with `score_candidate` (info-gain)
3. **Δt gate** — if onset ambiguity → **CARE** (Tier 2); prefer **shared_upstream** when it matches (keeps UC-3b off the early switch)
4. **Scoped causal check** — only when CARE path is active; topology + onset → Tier 3 if verified
5. **Else Tier 1** — `shared_upstream` / earliest onset / best-first without CARE
6. **Upstream healthy gate** — UC-5: no crossed infra → keep root at `orders-*`
7. **Signature** — `infer_signature(crossed)` (no ground-truth leak)
8. **Events** — `events.json` merged into evidence (UC-2/UC-4/UC-3b nonempty)
9. **Efficiency** — `obs_to_convergence` vs `naive_bfs_expansions`

## Evidentiary tiers

| Tier | Meaning |
|------|---------|
| 1 | Main path (temporal / shared_upstream / clear winner) |
| 2 | CARE fired; not yet causally verified |
| 3 | CARE fired **and** scoped causal check passed |

## Run API / report

```bash
# from repo root
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report
```

## Run benchmark

```bash
# from repo root
.venv/bin/python benchmarking/benchmark/run_lean.py --all --run-id full-001
```

## Tests

```bash
PYTHONPATH=lean-pipeline:. .venv/bin/python -m pytest lean-pipeline/core_engine/tests/ -v
```

## Dependency

`registry.py` requires PyYAML (`pip install pyyaml`).

Shared ObserveOps docs: [`../../../docs/README.md`](../../../docs/README.md).