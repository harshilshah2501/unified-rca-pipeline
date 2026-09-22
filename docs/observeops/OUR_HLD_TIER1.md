# Our HLD — Tier 1 reading list (locked)

**Status:** Locked for hub navigation refactor (2026-09-02).  
**Purpose:** Name the **only** pages that belong above the fold on [Our HLD](./observeops-pipeline-hld.html). Everything else is Tier 2 (depth) or Tier 3 (reference / history) until explicitly promoted.

**Door:** [`observeops-pipeline-hld.html`](./observeops-pipeline-hld.html) (`http://127.0.0.1:8765/observeops-pipeline-hld.html`) — frame and links; **not** a substitute for reading Tier 1 content.

---

## Naming hygiene (avoid letter clutter)

This repo already has too many **letter codes**. Prefer plain words in hub navigation.

| Keep (Motadata / product) | Prefer saying | Avoid as hub labels |
|---------------------------|---------------|---------------------|
| **Pillar A** / **Pillar B** / **Pillar C** | sketches · knowledge graph · optional agent | Renaming pillars |
| **Hub Tier 1 / 2 / 3** | must-read · depth · archive | Extra “Band A / Band B” codes |
| Detect **entry on Node / Gateway / platform** | say the locus | Overloading hub talks with “Door A/B/C” (those names stay in Detect/shift-left docs only) |
| Datadog **Monitors / Watchdog** | product names | Importing Datadog “Door A/B” into Motadata hub copy |

**Do not invent** new Path/Band/Door letter codes for reading lists. If two audiences need different pages, title the sections **Everyone** and **Implementers**.

---

## What Tier 1 means

**Disambiguation — “Tier” is overloaded in this repo.** On this page and on Our HLD hub tags, **hub Tier** means reading depth for Motadata / ObserveOps docs (Tier 1 = must-read, Tier 2 = depth, Tier 3 = archive/history). It is **not**:

- **Lean evidentiary Tier** 1/2/3 (verdict depth on the UC bakeoff — see [`GLOSSARY.md`](../reference/GLOSSARY.md))
- **Federated storage Tier** 1/2 (Dragonfly vs structural store — see [`STORAGE_TIERS.md`](../../federated-pipeline/docs/STORAGE_TIERS.md))
- Vortex / S3 **temperature** (hot vs cold encoding of the same rooms)

When you write a new page, say **hub Tier**, **evidentiary Tier**, or **storage Tier** on first use if more than one could apply.

| Hub Tier | Job | Reader question |
|----------|-----|-----------------|
| **Tier 1** | Orient + lock | “What is ObserveOps, what is frozen, and where do I start?” |
| **Tier 2** | Depth | “How does this slice work in detail?” → [HLD archive](./hld-archive.html), fabric visuals, LLDs, contract brief |
| **Tier 3** | Reference / history | “How did we compare vendors or run bakeoffs?” → vendor hubs, Lean/Federated, [`NAVIGATION.md`](../NAVIGATION.md) §4–§8 |

**Inclusion rule:** A page is Tier 1 only if a cold reader **must** see it before any other Our HLD article. If two pages answer the same question, **one** stays Tier 1.

**Exclusion rule:** Teaching annexes, evaluation scoreboards, leadership study packs, and duplicate indexes are **never** Tier 1 — even when linked from the hub today.

---

## Tier 1 catalog (six pages + Tier 2 I/O chain)

### Everyone (five pages)

Read in this order on first visit.

| # | Page | Path | One-line job |
|---|------|------|--------------|
| **0** | **Unified pipeline workflow** | [`motadata-unified-pipeline-workflow.html`](../motadata-unified-pipeline-workflow.html) | GIF-style end-to-end: estate map vs diagnose procedure · guidance bias · E1–E11 · checkout walk. |
| **1** | **Fusion** | [`observeops-fusion-guide.html`](./observeops-fusion-guide.html) | Click a Detect class; walk E1–E11 with step inputs and outputs. |
| **2** | **Pipeline HLD** | [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) | Canonical written spec — stage purpose, contracts, signed ADRs, NFR targets. |
| **3** | **Data shape journey** | [`../fabric/data-shape-journey.html`](../fabric/data-shape-journey.html) | How object names and JSON forms evolve Edge → Platform → case objects (E1–E11). |
| **4** | **GRAPH_QNA** | [`../GRAPH_QNA.md`](../GRAPH_QNA.md) | Locked fabric rules — fan-out, `map/` vs `history/`, rooms ≠ temperature, sketch vs graph. FAQ with TOC. |
| **5** | **Glossary** | [`urca-glossary.html`](./urca-glossary.html) | Disambiguate Normalize vs Identify, Detect classes, tier vocabulary — before reading deeper docs. |

**Done with Everyone when:** you can explain the one pipeline (E1–E11), the two parallel writers after Identity (`map/` ∥ `history/`), and where locked rules live (GRAPH_QNA).

### Implementers (one entry page)

Add when wiring **Pillar A** (sketches) or **Pillar B** (knowledge graph) — not required for product or leadership orientation.

| # | Page | Path | One-line job |
|---|------|------|--------------|
| **6** | **Pillar A + B slice** | [`../../pillar-ab-implementation/README.md`](../../pillar-ab-implementation/README.md) | Code layout, contracts SoT, what each pillar owns, how to run unit tests. For a Pillar B demo, continue to [`TEAM_WALKTHROUGH.md`](../../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md). |

**Done with Implementers when:** you know which package to open, where JSON schemas live under `pillar-ab-implementation/contracts/`, and (for Pillar B demos) you have opened the team walkthrough.

### Tier 2 — Implementer I/O contracts (not Tier 1)

These are **implementation-specific wire records** — normative for builders, not for cold product orientation. Read them in pipeline order when connecting ingest → writers → dest files.

```text
E1 Collect envelope          E2 Identity overlay           Pillar writers              Dest rooms
        │                            │                          │                         │
        ▼                            ▼                          ▼                         ▼
 INGEST_DATA_FORMAT.md    E2_INPUT_FIXTURES.md          (pillar code)          MAP_WRITE_READ_RECORD.md
 (upstream + delivery)     (post-E2 lab input)                                    (Pillar B map/ output)
        │                            │                          │
        └──────── same ingest.v1 ────┴── metric_sample / topo_update ──►  history/ sketch.v1
                                                                          (see Pillar A deep dive)
```

| Order | Page | Canonical path | Stage | One-line job |
|-------|------|----------------|-------|--------------|
| **I/O-1** | **Ingest data format** | [`../INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md) | E1 (+ §2.2 E2 overlay) | `ingest.v1` envelope, `fact_kind` enum, corpus folder layout, identity overlay spec. For **data owners and converter authors** — wider than the lab fixtures. |
| **I/O-2** | **Post-E2 ingest fixtures** | [`../../pillar-ab-implementation/E2_INPUT_FIXTURES.md`](../../pillar-ab-implementation/E2_INPUT_FIXTURES.md) | After E2 (lab stub) | **What Pillar A and B actually read today** — resolved-only JSONL paths, `metric_sample` vs `topo_update`. Subset of I/O-1 focused on pillar PoC tapes. |
| **I/O-3** | **Map write/read record** | [`../../pillar-ab-implementation/contracts/MAP_WRITE_READ_RECORD.md`](../../pillar-ab-implementation/contracts/MAP_WRITE_READ_RECORD.md) | E3 output (`map/`) | Pillar B **output** keys — `graph_snapshot.json`, `nodes.jsonl`, `edges.jsonl`, logical keys, `files.v1` PoC profile. Hub mirror: [`docs/MAP_WRITE_READ_RECORD.md`](../MAP_WRITE_READ_RECORD.md) when present. |
| **I/O-4** | **Pillar A deep dive** (history output) | [`../fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) | E4 output (`history/`) | Pillar A **output** — `sketch.v1` row shape, windows, Vortex/S3 temperature. Pair with I/O-3 for both rooms. |

**Pillar B PoC demo pack (after I/O-2):** [`pillar-b-poc-hub.html`](../fabric/pillar-b-poc-hub.html) → [`TEAM_WALKTHROUGH.md`](../../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md) → [`MAP_P1_FABRIC_EVAL.md`](../../pillar-ab-implementation/pillar-b/docs/MAP_P1_FABRIC_EVAL.md) → [`Codebase-go-through.md`](../../pillar-ab-implementation/pillar-b/docs/Codebase-go-through.md). Hub: [`observeops-pipeline-hld.html#pillar-b-poc`](./observeops-pipeline-hld.html#pillar-b-poc).

**Why these are Tier 2, not Tier 1:** Tier 1 answers “what is ObserveOps?” These answer “what bytes on the wire for **this** PoC slice?” A product reviewer stops after the **Everyone** pages; an engineer reads I/O-1 → I/O-2 before code, then I/O-3 or I/O-4 when validating flush output.

**Overlap to avoid confusion:**

| Question | Read this | Not this |
|----------|-----------|----------|
| Full E1 field list + corpus delivery options | **INGEST_DATA_FORMAT** | E2 fixtures alone |
| Lab JSONL paths for `make flush` / unit tests | **E2_INPUT_FIXTURES** | INGEST_DATA_FORMAT §3 delivery (broader) |
| What GraphWriter writes to `map/` | **MAP_WRITE_READ_RECORD** | GRAPH_QNA (rules, not file keys) |
| Why `map/` ≠ `history/` | **GRAPH_QNA** (Tier 1 #4) | MAP_WRITE_READ_RECORD alone |

---

## Role shortcuts (max six links each)

### Product / architecture reviewer

1. Fusion → 2. Pipeline HLD → 3. Data shape journey → 4. GRAPH_QNA → 5. Glossary  

Skip the implementer entry (#6) unless reviewing Pillar A/B delivery.

### Pillar A or B engineer

**Tier 1:** Data shape journey → GRAPH_QNA → Pillar A + B slice

**Tier 2 I/O chain (in order):** Ingest data format → Post-E2 fixtures → run pillar code → Map write/read (B) or Pillar A deep dive (A output)

**Pillar B team demo (after I/O-2):** [`pillar-b-poc-hub.html`](../fabric/pillar-b-poc-hub.html) → [`TEAM_WALKTHROUGH.md`](../../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md) → [`MAP_P1_FABRIC_EVAL.md`](../../pillar-ab-implementation/pillar-b/docs/MAP_P1_FABRIC_EVAL.md) → `cd pillar-b/poc && make test-all`. Hub: [`#pillar-b-poc`](./observeops-pipeline-hld.html#pillar-b-poc).

Optional: Pipeline HLD E3/E4 sections · Fusion sanity check  

Other Tier 2: contract brief, exemplars visual, inventory/catalog visual, LLD-E1/E2

### Leadership / Motadata alignment (no code)

1. Fusion → 2. Pipeline HLD (§ purpose + ADRs) → 3. Data shape journey ( skim ) → 4. Glossary  

Tier 2 only if needed: [`motadata-3pillars-implementation-scope.html`](../motadata-3pillars-implementation-scope.html). Tier 3 for study Q&A and PDF job-map depth.

---

## Explicitly not Tier 1

These stay valuable but move **below the fold** or to Tier 2/3 indexes.

| Page / area | Tier | Why not Tier 1 | Go here instead when… |
|-------------|------|----------------|-------------------------|
| [`observeops-pipeline-hld.html`](./observeops-pipeline-hld.html) long body (E1–E11 accordions, ADR tables) | — | Duplicates Pipeline HLD MD; makes the door too long | Read **Pipeline HLD** MD |
| [`hld-archive.html`](./hld-archive.html) | 2 | Secondary index — search, not start | You know the topic name |
| Fabric card grid duplicates (second RED card, duplicate launchpad) | 2 | Same destination as Tier 1 #3–#4 or archive | Tier 1 or archive filter |
| [`motadata-3pillars-architecture.html`](../motadata/motadata-3pillars-architecture.html) | 2–3 | Leadership teaching depth | PDF / pillar alignment review |
| [`motadata-3pillars-study-qna.html`](../motadata/motadata-3pillars-study-qna.html) | 3 | Study + conflict register | Resolving PDF vs pipeline wording |
| [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) | 2 | Map **chapter** of the spec, not a second HLD | E3 topology / provenance depth |
| [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) | 2 | Sit-down lock list — longer than GRAPH_QNA | Signing CI catalog / fifteen edges |
| [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md) | 2 · **I/O-1** | E1 envelope + corpus delivery — upstream of pillars | Converters / data owners (see [Implementer I/O](#tier-2--implementer-io-contracts-not-tier-1)) |
| [`E2_INPUT_FIXTURES.md`](../../pillar-ab-implementation/E2_INPUT_FIXTURES.md) | 2 · **I/O-2** | Lab post-E2 JSONL — pillar writer input | `make flush`, unit tests |
| [`MAP_WRITE_READ_RECORD.md`](../../pillar-ab-implementation/contracts/MAP_WRITE_READ_RECORD.md) | 2 · **I/O-3** | Pillar B `map/` output keys | Validating graph snapshot publish |
| [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) | 2 · **I/O-4** | Pillar A `history/` sketch output | Validating sketch flush |
| LLD-E1 … LLD-E5 | 2 | Block implementation detail | Building a specific E-stage (E5 = Design stub) |
| Vendor DT / DD / ED hubs | 3 | Independent production references | Vendor compare, not ObserveOps lock |
| Lean / Federated / bakeoff docs | 3 | Evaluation history | ADR-001 era scoreboards |
| [`NAVIGATION.md`](../NAVIGATION.md) full index | — (maintainer) | Maintainer map, not cold start | Finding any file in repo |

---

## How Tier 1 maps to the old “five paths”

The hub’s five paths collapse into Tier 1 + Tier 2:

| Old path | Tier 1 | Tier 2 (first stop after Tier 1) |
|----------|--------|----------------------------------|
| **1 · Try** | Fusion (#1) | — |
| **2 · Spec** | Pipeline HLD (#2) | Hub spec excerpt → prefer MD |
| **3 · Fabric** | Data shape journey (#3) + GRAPH_QNA (#4) | [`fabric/README.md`](../fabric/README.md) ordered visuals |
| **4 · Build** | Pillar slice (#6) | I/O-1 … I/O-4, implementation scope HTML, shift-left, LLDs |
| **5 · Archive** | — (not Tier 1) | [`hld-archive.html`](./hld-archive.html) |

---

## Hub refactor checklist

- [x] Above the fold: Everyone (five links) + Implementers entry (#6) + I/O chain
- [x] Remove duplicate launchpad cards that repeat paths 1–5
- [x] Remove duplicate fabric cards (single exemplars/RED entry)
- [x] Spec detail note → prefer Pipeline HLD MD (long accordion retained below fold)
- [x] Tag archive rows: Tier 1 / Tier 2 / Tier 2 · I/O / Tier 3 + `#implementer-io` section
- [x] Point [`NAVIGATION.md`](../NAVIGATION.md) §1 at this file for cold start
- [x] Drop “Band A / Band B” labels — use Everyone / Implementers only

---

## Related

- Fabric visual order (Tier 2): [`../fabric/README.md`](../fabric/README.md)  
- Maintainer full index: [`../NAVIGATION.md`](../NAVIGATION.md)  
- Repo hygiene: [`../REPO_HYGIENE.md`](../REPO_HYGIENE.md)
