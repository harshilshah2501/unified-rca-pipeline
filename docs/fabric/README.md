# Fabric teaching (E1–E5 / Pillar A∥B stores)

Motadata always-on fabric visuals and deep dives for Pillar A (sketches) and Pillar B (graph).

**Hub entry:** [`../observeops/observeops-pipeline-hld.html#fabric`](../observeops/observeops-pipeline-hld.html#fabric) (Our HLD → Fabric & data contracts)  
**Archive index:** [`../observeops/hld-archive.html#fabric`](../observeops/hld-archive.html#fabric)  
**Q&A:** [`../GRAPH_QNA.md`](../GRAPH_QNA.md) (symlink to pillar-ab contracts)

Compatibility symlinks at `docs/<filename>` keep `:8765` URLs working.

## Visuals (read in this order for cold start)

| Order | Visual | Topic |
|-------|--------|--------|
| 0 | [`edge-platform-detect-simulation.html`](./edge-platform-detect-simulation.html) | **Looping film** — Edge devices · Node · optional Collector · SaaS; two ingest doors; Detect Signal. Notes: [`SIMULATION_THREAD.md`](./SIMULATION_THREAD.md) |
| 1 | [`data-shape-journey.html`](./data-shape-journey.html) | **E1–E11 data evolution** — Edge devices vs Platform; names, forms, structure |
| 2 | [`e1-e5-pipeline-architecture.html`](./e1-e5-pipeline-architecture.html) | E2 fan-out → `map/` ∥ `history/`; Edge · Gateway · Platform |
| 2b | [`inventory-catalog-on-the-map.html`](./inventory-catalog-on-the-map.html) | **Inventory vs catalog** → `graph_edge.v1`; LUT vs `map/`; G10–G11 teaching |
| 2c | [`graphwriter-io-walkthrough.html`](./graphwriter-io-walkthrough.html) | **GraphWriter I/O** — partners, admit, seed→flush · Site tab · [`:8765`](http://127.0.0.1:8765/graphwriter-io-walkthrough.html) |
| 3 | [`map-history-storage-blocks.html`](./map-history-storage-blocks.html) | Rooms, R/W, no sync; join at WorkingSet |
| 4 | [`map-history-storage-animation.html`](./map-history-storage-animation.html) | Animated write → rooms → read-join |
| 5 | [`vortex-s3-interaction.html`](./vortex-s3-interaction.html) | Rooms vs temperature (Vortex + S3) |
| 5b | [`storage-formats-vortex-parquet-lance.html`](./storage-formats-vortex-parquet-lance.html) | **Vortex vs Parquet vs Lance** — animated learning |
| 6 | [`sketch-exemplars-visual.html`](./sketch-exemplars-visual.html) | **RED + exemplars** — OTel vs ObserveOps; optional exemplars on sketch rows |

## Markdown deep dives

| Doc | Topic |
|-----|--------|
| [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](./PILLAR_A_PERCENTILES_DEEP_DIVE.md) | Inputs → `sketch.v1` / S3 / Vortex |
| [`red-metrics-and-exemplars.md`](./red-metrics-and-exemplars.md) | Redirect → [`sketch-exemplars-visual.html`](./sketch-exemplars-visual.html) §RED |
| [`end-to-end-algorithm-walkthrough.md`](./end-to-end-algorithm-walkthrough.md) | Admit → window → Detect door C |
| [`Sketches_Merging_RawData_QnA.pdf`](./Sketches_Merging_RawData_QnA.pdf) | Owner exercise — answers in GRAPH_QNA G33–G37 |
