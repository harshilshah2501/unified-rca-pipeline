# Design v3 — Motadata map Vortex experiment program (Stages 0–4.2)

Executable research program for **cold Vortex map parts → hot adjacency → Scope-like walks**.

This folder freezes P0 lab contracts before Stages 1–4. It is a companion to Report 02 and the guided analysis doc — **not** a product schema lock.

## Scope (this pass)

| In | Out |
| -- | --- |
| Stages 0–4.2 | Stages 4.3–6 (confirmation, concurrency, mutation economics, adoption) |
| Synthetic estates (six families) | Real Motadata dumps / production traces |
| Scales ≤5M edges (screening ladder) | 10M+ scale gate |
| p50 / p95 screening | Robust p99 confirmation (Stage 4.6) |

## Stage map

```text
0    P0 contracts (this folder)
1    Reproduce 2×2 (order × builder) + run manifests
2    Factor screen (hash layout only)
3    Deep hot layouts: hash vs CSR/CSC/hybrid
3.5  Fair compare: + hash_bi, equal reverse mix, per-class latency
4.0  Estate/workload contracts + generators + validators + query traces
4.1  Characterize graphs (properties)
4.2  Layout screen ≤5M → crossover candidates (not production lock)
```

Scripts live in [`../map-vortex-bench/scripts/`](../map-vortex-bench/scripts/). Reports 04–09 under [`../reports/`](../reports/).

**Share with engineering (cold readers):** [`../reports/11-map-vortex-engineering-brief.md`](../reports/11-map-vortex-engineering-brief.md).  
Deep synthesis: [`../reports/10-design-v3-comprehensive.md`](../reports/10-design-v3-comprehensive.md).

Stage 4 contracts: [`stage4/`](./stage4/).

## Artifacts

| File | Role |
| ---- | ---- |
| [`slo-worksheet.md`](./slo-worksheet.md) | Lab SLOs / readiness |
| [`trace-schema.json`](./trace-schema.json) | Per-query event schema |
| [`run-manifest.schema.json`](./run-manifest.schema.json) | Per-run manifest schema |
| [`run-manifest.example.json`](./run-manifest.example.json) | Example manifest |
| [`correctness-oracle.md`](./correctness-oracle.md) | Result equivalence rules |
| [`factor-registry.md`](./factor-registry.md) | Factor levels for Stages 1–3.5 |
| [`query-algorithms.md`](./query-algorithms.md) | Per-layout forward/reverse algorithms |
| [`gates.md`](./gates.md) | Exit criteria per stage |
| [`stage4/README.md`](./stage4/README.md) | Stage 4.0–4.2 philosophy + phase map |

## Evidence base

- [`../reports/02-map-load-adjacency.md`](../reports/02-map-load-adjacency.md)
- [`../contracts/MAP_HOT_COLD_LIFECYCLE.md`](../../contracts/MAP_HOT_COLD_LIFECYCLE.md) (via product/contracts)
- Guided analysis companion under `../reports/Map_Vortex_Guided_Analysis_Visual (1).docx`
