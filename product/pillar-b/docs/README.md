# Pillar B docs — map and reading rules

**Canonical Vortex / map entry:** [`MAP_VORTEX_S3_POC_PRIMER.md`](./MAP_VORTEX_S3_POC_PRIMER.md).

One page should have **one job**. Do not fork contracts under this folder.

## Start here (required)

| If you want… | Open |
|--------------|------|
| Run the Python PoC | [`../README.md`](../README.md) |
| Team walkthrough | [`TEAM_WALKTHROUGH.md`](./TEAM_WALKTHROUGH.md) |
| Stream → graph timeline (PoC-aligned) | [pillar-b-stream-graph-demo.html](../../../docs/fabric/pillar-b-stream-graph-demo.html) |
| Code tour | [`Codebase-go-through.md`](./Codebase-go-through.md) |
| Build/maintain + walk eval | [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) |
| Vortex + S3 map PoC | [`MAP_VORTEX_S3_POC_PRIMER.md`](./MAP_VORTEX_S3_POC_PRIMER.md) |
| Rows → Arrow → Vortex (APIs) | [`MAP_ARROW_VORTEX_PIPELINE.md`](./MAP_ARROW_VORTEX_PIPELINE.md) |
| JSON → Arrow → Vortex → S3 (visual) | [map-arrow-vortex-pipeline.html](../../../docs/fabric/map-arrow-vortex-pipeline.html) |
| Framing hub | [Pillar B PoC hub](../../../docs/fabric/pillar-b-poc-hub.html) |

Suggested order: **package README → TEAM_WALKTHROUGH → stream demo → Codebase-go-through → MAP_P1 → `make test-all`**. Vortex work: **primer → Arrow/Vortex pipeline → lifecycle → write/read §6**.

## Optional

| Page | Why optional |
|------|----------------|
| [`MAP_P2_CASE_PATH.md`](./MAP_P2_CASE_PATH.md) · [`MAP_P3_DIAGNOSE_CLOSE.md`](./MAP_P3_DIAGNOSE_CLOSE.md) | Stub harnesses beyond map fabric |
| [`PILLAR_B_POC_CHAT_QNA.md`](./PILLAR_B_POC_CHAT_QNA.md) | Session Q&A log — not SoT |
| [`vortex_engineering_mystery_revised_v2.pdf`](./vortex_engineering_mystery_revised_v2.pdf) | Owner background notes |
| Call-graph PNG/SVG assets | Diagrams for hub |

## Elsewhere

| Path | Role |
|------|------|
| [`../poc/`](../poc/) | Code + sample estate |
| [`../../contracts/`](../../contracts/) | Wire + map SoT (start from primer for Vortex) |
| [`../map-vortex/`](../map-vortex/) | Rust Motadata columnar crate |
| [`../archived-docs/`](../archived-docs/) | Product HTML library — not wire SoT |
