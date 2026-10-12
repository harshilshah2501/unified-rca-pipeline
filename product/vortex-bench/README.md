# Vortex bench program (Motadata map + sketches)

Physical experiments for how ObserveOps should store Motadata cold data in **Vortex** files.

This folder is the experiment home. It is **not** a product schema lock.

## Program objective

We already locked **logical** Motadata contracts (flat map columns; sketch evidence ladder with digest, buckets, baseline, optional exemplars). These benches ask a different question: **how should those rows sit inside Vortex files** so product reads stay cheap under Vortex’s zone / chunk / buffered-run layout.

| Room | Why this experiment | What we are trying to achieve |
|------|---------------------|-------------------------------|
| **`history/` sketches** | Sketch rows are **wide** (T‑Digest bytes, bucket arrays, exemplars). RCA reads them in **stages** (locate → distribution → exemplar). A neat nested logical schema can still force Stage‑1 to decode Stage‑3 bytes. | Choose a **physical column shape + projection discipline** so Detect/investigate can scan cheap spine columns first, and only decode fat evidence when a window is a real candidate. |
| **`map/` topology** | Map rows are already **flat and thin**. Interactive Scope does **not** open Vortex per neighbor; it walks a **hot adjacency index** rebuilt from cold parts. The bottleneck is restart/failover/load, not layout beauty contests. | Measure **cold load → adjacency rebuild → first walk**, and learn whether spine projection and publish-time edge clustering make that path fast enough—without redesigning the locked schema. |

Shared achievement bar: **one Vortex Dest temperature, two playbooks** — project only what the current stage needs; cluster rows for prune; never put Vortex on the interactive inner hop.

| Bench | Room | Experiment question |
|-------|------|---------------------|
| [`sketch-vortex-bench/`](./sketch-vortex-bench/) | `history/` | How should sketch.v2-shaped rows be laid out so Stage‑1 RCA does not decode T‑Digest / exemplars early? |
| [`map-vortex-bench/`](./map-vortex-bench/) | `map/` | How expensive is cold load → hot adjacency rebuild under spine vs full projection and edge clustering? |
| [`design-v3/`](./design-v3/) | `map/` | Design v3 Stages 0–4.2: contracts, 2×2, factor screen, layouts, workload-informed synthetic estates |

## Reports

| Doc | Content |
|-----|---------|
| [`reports/01-sketch-physical-layout.md`](./reports/01-sketch-physical-layout.md) | Detailed sketch layout results (A–E × Q1–Q8) |
| [`reports/02-map-load-adjacency.md`](./reports/02-map-load-adjacency.md) | Detailed map load / adjacency / BFS results |
| [`reports/03-comparative-analysis.md`](./reports/03-comparative-analysis.md) | Side-by-side conclusions for Motadata Dest |
| [`reports/04-design-v3-stage1-reproduce.md`](./reports/04-design-v3-stage1-reproduce.md) | Design v3 Stage 1 — order × builder 2×2 |
| [`reports/05-design-v3-stage2-screen.md`](./reports/05-design-v3-stage2-screen.md) | Design v3 Stage 2 — factor screening |
| [`reports/06-design-v3-stage3-layouts.md`](./reports/06-design-v3-stage3-layouts.md) | Design v3 Stage 3 — hash / CSR / CSC / hybrid |
| [`reports/07-design-v3-stage3_5-fair.md`](./reports/07-design-v3-stage3_5-fair.md) | Design v3 Stage 3.5 — fair compare + hash_bi + per-class latency |
| [`reports/08-design-v3-stage4_1-properties.md`](./reports/08-design-v3-stage4_1-properties.md) | Design v3 Stage 4.1 — six estate family property reports |
| [`reports/09-design-v3-stage4_2-screen.md`](./reports/09-design-v3-stage4_2-screen.md) | Design v3 Stage 4.2 — layout screen ≤5M + crossover candidates |
| [`reports/10-design-v3-comprehensive.md`](./reports/10-design-v3-comprehensive.md) | Design v3 comprehensive — v2→v3 changes + full results analysis |
| [`reports/11-map-vortex-engineering-brief.md`](./reports/11-map-vortex-engineering-brief.md) | **Share with eng (cold readers)** — final brief, decisions, do/don’t |
| [`reports/Map_Vortex_Graph_Architecture_Decision_Record.md`](./reports/Map_Vortex_Graph_Architecture_Decision_Record.md) | ADR hypothesis (segmented CSR+CSC) — not a Stage 4.2 lock |

Companion design notes:

- Repo root [`Vortex-unit-check.md`](../../Vortex-unit-check.md) — zone / chunk / buffered-run framing + sketch experiment origin
- [`contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md`](../contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md) — locked map columns
- [`contracts/MAP_HOT_COLD_LIFECYCLE.md`](../contracts/MAP_HOT_COLD_LIFECYCLE.md) — walks on hot, Vortex on cold load
- [`contracts/OpenTelemetry_Exemplars_RCA_Design_Guide_v4.md`](../contracts/OpenTelemetry_Exemplars_RCA_Design_Guide_v4.md) — sketch evidence ladder

## Quick run

```bash
# Sketch physical layouts (100k rows)
cd sketch-vortex-bench
cargo run --release --bin sketch_vortex_bench -- \
  --rows 100000 --sort clustered --out out/run-100k-clustered

# Map cold load + adjacency (100k edges)
cd ../map-vortex-bench
cargo run --release --bin map_vortex_bench -- \
  --nodes 20000 --edges 100000 --edge-sort clustered \
  --out out/run-100k-edges-clustered
```

## One-line program conclusion

**Sketches need a hot spine and progressive cold columns; map needs a fast cold→hot rebuild and already-flat walk spines — do not copy the sketch layout matrix onto `map_nodes` / `map_edges`.**
