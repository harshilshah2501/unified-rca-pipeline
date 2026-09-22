# Pillar B docs — map and reading rules

One page should have **one job**. Contract / Q&A / product HTML are **not** copied into this folder — link the slice SoT or `references/` instead.

## Start here

| If you want… | Open |
|--------------|------|
| What this package is + how to run it | [`../README.md`](../README.md) |
| **Team demo / one-stop walkthrough** | [`TEAM_WALKTHROUGH.md`](./TEAM_WALKTHROUGH.md) |
| **Two use cases (build/maintain vs walk)** + layer navigator | [Pillar B PoC Navigator canvas](../reference/canvases/pillar-b-poc-navigator.canvas.tsx) |
| Build/maintain + walk eval | [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) |
| Stub harnesses (optional): CaseSeed…VerdictCard | [`MAP_P2_CASE_PATH.md`](./MAP_P2_CASE_PATH.md) · [`MAP_P3_DIAGNOSE_CLOSE.md`](./MAP_P3_DIAGNOSE_CLOSE.md) |
| How the **code** is wired | [`Codebase-go-through.md`](./Codebase-go-through.md) |
| Who calls APIs / file roles / method glossary | [`Codebase-go-through.md` § Clarifications](./Codebase-go-through.md#clarifications) |
| Case A/B expected vs actual | [`../poc/sample_estate/customer_checkout/SAMPLE_IO.md`](../poc/sample_estate/customer_checkout/SAMPLE_IO.md) |
| Hub visual (NOOP / WRITE / DROP) | [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter) |

Suggested order: **package README → TEAM_WALKTHROUGH → Pillar B PoC Navigator canvas → MAP_P1 → Codebase-go-through → SAMPLE_IO → `make test-all`**.

---

## What belongs in `docs/` (this folder)

| Page | Purpose |
|------|---------|
| [`README.md`](./README.md) | This map |
| [`TEAM_WALKTHROUGH.md`](./TEAM_WALKTHROUGH.md) | One-stop team demo: signal_class, admit, I/O, run |
| [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md) | Core eval: build/maintain + walk |
| [`MAP_P2_CASE_PATH.md`](./MAP_P2_CASE_PATH.md) | Optional stub harness (CaseSeed…LeafClaim) |
| [`MAP_P3_DIAGNOSE_CLOSE.md`](./MAP_P3_DIAGNOSE_CLOSE.md) | Optional stub harness (EvidenceBundle…VerdictCard) |
| [`Codebase-go-through.md`](./Codebase-go-through.md) | Code tour + runtime spine |
| `runtime-spine.png` / `.svg` | Spine diagram asset |
| `pillar-b-callgraph.png` / `.svg` / `.dot` | Use case 1: build+maintain call graph |
| `pillar-b-walk-callgraph.png` / `.svg` / `.dot` | Use case 2: walk-through call graph |
| `pillar-b-callgraph-auto.png` | Optional auto `code2flow` dump (write path; noisier) |

**Framing (two use cases + stubs)** lives in the [Pillar B PoC Navigator canvas](../reference/canvases/pillar-b-poc-navigator.canvas.tsx), not a separate markdown page.

**Removed on purpose:** symlinks to `GRAPH_*`, `MAP_WRITE_READ_RECORD`, and the old GraphWriter HTML stub — use slice contracts and the hub URL above.

---

## Elsewhere in the package

| Path | Purpose | Required for PoC? |
|------|---------|-------------------|
| [`../poc/`](../poc/) | Code, sample estate, tests | **Yes** |
| [`../reference/canvases/`](../reference/canvases/) | Cursor canvases — navigator is the two-use-case framing home | **Yes** for framing; optional for layer drill |
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
