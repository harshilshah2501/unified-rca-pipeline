# Pillar B docs — map and reading rules

One page should have **one job**. Contract / Q&A / product HTML are **not** copied into this folder — link the slice SoT or `references/` instead.

## Start here

| If you want… | Open |
|--------------|------|
| What this package is + how to run it | [`../README.md`](../README.md) |
| E1–E5 map eval (admit, gaps, Increment 1) | [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) |
| How the **code** is wired | [`Codebase-go-through.md`](./Codebase-go-through.md) |
| Who calls APIs / file roles / method glossary | [`Codebase-go-through.md` § Clarifications](./Codebase-go-through.md#clarifications) |
| Interactive layer navigator (Cursor canvas) | [`../reference/canvases/pillar-b-poc-navigator.canvas.tsx`](../reference/canvases/pillar-b-poc-navigator.canvas.tsx) |
| Case A/B expected vs actual | [`../poc/sample_estate/customer_checkout/SAMPLE_IO.md`](../poc/sample_estate/customer_checkout/SAMPLE_IO.md) |
| Hub visual (NOOP / WRITE / DROP) | [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter) |

Suggested order: **package README → MAP_P1_FABRIC_EVAL → Codebase-go-through → SAMPLE_IO → `make test-all`**.

---

## What belongs in `docs/` (this folder)

| Page | Purpose |
|------|---------|
| [`README.md`](./README.md) | This map |
| [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) | Increment 1 eval contract |
| [`Codebase-go-through.md`](./Codebase-go-through.md) | Code tour + runtime spine |
| `runtime-spine.png` / `.svg` | Spine diagram asset |

**Removed on purpose:** symlinks to `GRAPH_*`, `MAP_WRITE_READ_RECORD`, and the old GraphWriter HTML stub — use slice contracts and the hub URL above.

---

## Elsewhere in the package

| Path | Purpose | Required for PoC? |
|------|---------|-------------------|
| [`../poc/`](../poc/) | Code, sample estate, tests | **Yes** |
| [`../reference/canvases/`](../reference/canvases/) | Cursor canvases (navigator, GraphWriter I/O) | **No** — optional interactive index |
| [`../contracts/schemas/`](../contracts/schemas/) | Schema symlinks for validation | **Yes** (code path) |
| [`../../contracts/`](../../contracts/) | Slice SoT: map write/read, reject codes, GRAPH_QNA, samples | **Yes** (read/link; do not fork) |
| [`../references/`](../references/) | Motadata OneOps / Fusion product HTML + ED comparator notes | **No** — optional library; not wire SoT |

---

## Redundancy rules

- **Admit NOOP/WRITE/DROP** — package [`../README.md`](../README.md) + [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md). Elsewhere: one-line + link.
- **Estate bootstrap ≠ CaseSeed** — MAP_P1 terminology. Elsewhere: one sentence + link.
- **Runtime spine** — [`Codebase-go-through.md`](./Codebase-go-through.md) only.
- **Do not** re-mirror slice `contracts/*.md` under `pillar-b/contracts/` or symlink them under `docs/`.

---

## Slice contracts you’ll open often

| Doc | Why |
|-----|-----|
| [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md) | What lands under `map/` |
| [`../../contracts/IDENTIFIED_STREAM_REJECT.md`](../../contracts/IDENTIFIED_STREAM_REJECT.md) | DROP reason codes |
| [`../../contracts/GATE_B_DEST_PROFILE.md`](../../contracts/GATE_B_DEST_PROFILE.md) | Dest profile |
| [`../../contracts/GRAPH_QNA.md`](../../contracts/GRAPH_QNA.md) | Fabric Q&A |
| [`../../../docs/observeops/LLD-E3-Topology.md`](../../../docs/observeops/LLD-E3-Topology.md) | Topology LLD |
| [`../../../docs/observeops/LLD-E5-Maintain.md`](../../../docs/observeops/LLD-E5-Maintain.md) | Maintain Design stub |
