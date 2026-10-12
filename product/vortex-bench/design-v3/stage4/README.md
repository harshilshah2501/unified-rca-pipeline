# Stage 4 — Workload-Informed Synthetic Estate Validation (4.0–4.2)

**Philosophy:** Establish the architectural **performance envelope** across controlled, explicitly characterized synthetic workloads. This does **not** claim Motadata production workloads without real estates/traces.

## Scope this pass

| In | Out |
| -- | --- |
| Phases 4.0–4.2 | 4.3–4.6 (confirmation, concurrency, mutation economics) |
| ≤5M edges | 10M+ |
| Six estate families + three workload profiles | Production topology dumps |
| Screening report (crossover candidates) | Production architecture lock |

## Phase map

```text
4.0  Contracts + generators + property validators + query traces
4.1  Characterize graphs (properties only)
4.2  Layout screen → Report 09 crossover candidates
```

## Contracts

| Doc | Role |
| --- | ---- |
| [`estate-families.md`](./estate-families.md) | Six synthetic families |
| [`workload-profiles.md`](./workload-profiles.md) | Query mix profiles + trace replay |
| [`graph-properties.md`](./graph-properties.md) | Post-gen validation metrics |

Scripts: `map-vortex-bench/scripts/stage4_1_characterize.sh`, `stage4_2_screen.sh`.
Reports: [`../../reports/08-design-v3-stage4_1-properties.md`](../../reports/08-design-v3-stage4_1-properties.md), [`../../reports/09-design-v3-stage4_2-screen.md`](../../reports/09-design-v3-stage4_2-screen.md).
