# Federated architecture requirement vs Dynatrace 5+3+3 pipeline — gap map

**Purpose:** Map Motadata’s **proposed Federated architecture** (two-tier Event Graph + Knowledge Graph; Panorama → Murphy → Nezha; 1B EPS) onto the Dynatrace teaching pipeline: **5 Always-on fabric + 3 Case opens + 3 Diagnose**. Compare **functional objectives** (can Motadata achieve the job?), not Dynatrace product clones (Smartscape/Grail). Call out covered / partial / missing with epistemic labels. Motadata’s **multi-telemetry FR/AC** is the broad acceptance bar (§8). **Vector** is the Collect/Normalize **pipeline**, not a lake (§1.3).

**Browser:** [`federated-vs-dt-pipeline-gaps.html`](./federated-vs-dt-pipeline-gaps.html) · [`:8765`](http://127.0.0.1:8765/federated-vs-dt-pipeline-gaps.html)

**Related:** [`DYNATRACE_PRODUCTION_PIPELINE.md`](../DYNATRACE_PRODUCTION_PIPELINE.md) · [`eleven-subsystem-mechanisms.html`](../eleven-subsystem-mechanisms.html) · [`federated-pipeline/docs/REQUIREMENTS.md`](../federated-pipeline/docs/REQUIREMENTS.md) · [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](../multi-telemetry-rca-functional-and-acceptance-criteria.md) · [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) · [`RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md`](./RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md) §6

---

## 0. How to read this document

| Side | What it is |
|------|------------|
| **Federated requirement / Motadata architecture** | Proposed Motadata design: Dragonfly Event Graph + Vortex Knowledge Graph; Panorama → Murphy → Nezha; aimed at **1B EPS** and deep causal analysis (§2) |
| **Motadata multi-telemetry FR/AC** | Broad **functional & acceptance** criteria only — normalized Signal → CI → one incident (§8). Does **not** specify Dragonfly/Vortex/algos |
| **DT 5+3+3 pipeline** | **Teaching unveil** of Dynatrace-shaped Clock A/B using our lab (`frontend → product → inventory`) — not a claim we reimplemented Dynatrace |

| Gap class | Meaning |
|-----------|---------|
| **Covered** | Same *job* exists in DT teaching pipeline (possibly different tech/name) |
| **Partial** | Analogous store or stage exists, but **algorithm / data model / scale contract** differs |
| **Missing** | Required Federated block has **no** counterpart in the DT 5+3+3 teaching map |

| Epistemic tag | Reliability |
|---------------|-------------|
| **Observed (lab)** | Seen in our DT/DD labs |
| **Public framing** | Matches vendor public architecture language |
| **Inferred** | Fits lab + public story; internals unpublished |
| **Teaching** | Demo vocabulary / simplified model |
| **Requirement / Motadata architecture** | Stated Federated design target (not validated at 1B EPS in this PoC) |

**Nothing here is 100% Dynatrace-internal accuracy.** Federated / Motadata-architecture rows are **proposed design** claims; Motadata FR/AC rows are **acceptance** claims; DT rows are **teaching + lab + public/inferred**.

**Motadata docs are complementary, not contradictory:**

| Motadata doc | Answers |
|--------------|---------|
| Multi-telemetry FR/AC | *What* must the product accept? (signals → one incident + evidence + blast radius) |
| Federated two-tier graph + RCA flow (§2) | *How* is deep causal RCA at extreme EPS proposed to be built? (Dragonfly / Vortex / Panorama–Murphy–Nezha) |

The FR/AC does **not** deeply specify CMDB vs Discovery policy, dual-graph stores, or algo depth — that lives in the architecture. Gaps G1–G4 are **architecture vs DT unveil**, not “Motadata AC fails Federated.”

---

## 1. Stage cheatsheet — DT 5+3+3

```text
Phase 1 · Always-on fabric (5)
  Collect → Normalize → Topology bind → Fan-out → Maintain

Phase 2 · Case opens (3)
  Detect → Curate → Tailor

Phase 3 · Davis diagnose (3)
  Localize → Identify → Package
```

| # | Stage | Teaching output |
|---|--------|-----------------|
| 1 | Collect | Vendor-shaped streams (OneAgent / OTLP) |
| 2 | Normalize | Envelope: `failed_call`, `raw_ids`, … |
| 3 | Topology | Smartscape graph + bind LUT → `entityId` |
| 4 | Fan-out | Smartscape upserts ∥ Grail evidence (**not** Lean/Fed L0/F1) |
| 5 | Maintain | Keep map fresh + lake retained |
| 6 | Detect | Per-entity **Events** (Event ≠ Problem) |
| 7 | Curate | Storm → one **seed** `(entityId, t0)` |
| 8 | Tailor | Space ∩ time **working set** |
| 9 | Localize | Smartscape walk (inferred) |
| 10 | Identify | Scoped Grail pull + rank (inferred) |
| 11 | Package | Problem card (`rootCauseEntity`, …) |

### 1.1 Discovery vs CMDB (Topology bind context)

**CMDB is not the production observability CI graph** in this teaching pipeline.

| Term | What it is here | Role |
|------|-----------------|------|
| **Smartscape / CI graph** | Live entity + relationship graph (`calls`, `runsOn`, …) used for walk/bind | **The** map Davis/Tailor read |
| **Discovery** | Observability discovery: OneAgent/OTLP sees processes, hosts, ports, call peers → upsert nodes/edges (+ LUT) | How the CI graph is **built/refreshed** |
| **CMDB** | Separate system of record (ServiceNow-style inventory) | Optional enrich/merge/tag — **not** required for Smartscape to exist |

Our lab is **discovery-first** (auto-create `SERVICE-INV` on first sighting). A CMDB-strict kit can instead **orphan** until an approved CI exists — opposite gate. Full write-up: [`DYNATRACE_PRODUCTION_PIPELINE.md`](../DYNATRACE_PRODUCTION_PIPELINE.md) §5.3.

On the Federated side, Discovery ≈ feeding the **Knowledge Graph** (Vortex CSR edges + entity identity). CMDB remains optional governance, not Vortex itself.

### 1.2 Functional objectives — Motadata achievability (not DT product clones)

**Smartscape** and **Grail** are Dynatrace product names. Motadata is **not** shipping those products. When we compare pipelines, we only ask: *can Motadata achieve the same job?* — not *do we have a 100% match?*

In plain language, Dynatrace’s unveil needs **two kinds of memory** plus a **pipe that fills them**:

| Everyday job (objective) | What it means for operators | DT teaching name | Motadata way to achieve it |
|--------------------------|-----------------------------|------------------|----------------------------|
| **Who is connected?** | Walk hosts/services/edges; compute blast radius | Smartscape | **Knowledge Graph** (Vortex CSR + DashMap properties) |
| **What happened, when?** | Keep high-volume evidence so Diagnose can prove the story | Grail | **Event Graph** (Dragonfly temporal graphs + pattern counts) + structural metrics/LOS on DashMap |
| **Same id on map and evidence** | One CI means the same thing everywhere | Shared `entityId` | Shared CI / entity identity across KG ↔ Event Graph / Signals (FR-B) |
| **Get data in cleanly** | Collect → normalize → stamp CI → write both stores | Collect → Normalize → Topology → Fan-out | **Vector-class pipeline** → bus → Rust → dual sinks (§1.3, §2.4) |
| **Something is wrong** | Raise signals without yet naming the Problem | Detect Events | Panorama (+ AC anomaly/storm seeds) |
| **One answer** | Single incident: root cause + evidence + impact | Problem / Package | Fused verdict / Motadata incident (FR-I) |

**Achievability rule of thumb**

- If Motadata has a **walkable topology** and a **high-velocity evidence plane** joined by **CI identity**, the Smartscape/Grail *objectives* are achievable under Motadata names.
- If Motadata only has correlation rules and no dual stores, AC scenarios may still pass for simple faults — deep gray-failure / path Identify / 1B EPS will not.
- **No claim of twin query models.** Motadata does not need DQL-over-Grail; it needs *enough evidence, scoped in time and neighborhood, to explain the root cause*.

### 1.3 Vector in Collect — simple explanation

**Vector is not a third lake.** In our vocabulary ([`RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md`](./RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md) §6):

| Name | Kind of thing | One-line role |
|------|---------------|---------------|
| **Smartscape** (DT) / **Knowledge Graph** (Motadata) | Map | Who depends on whom |
| **Grail** (DT) / **Event Graph** (Motadata) | Evidence store(s) | What happened, when |
| **Vector** (us / industry) | **Ingest pipeline** | Collect → transform/normalize → **route** into the map and evidence sinks |

Think of Vector (or OTel Collector / Fluent Bit — same *class*) as the **plumbing**, not the filing cabinet:

```text
Agents / collectors / traps / flow exporters
        │
        ▼
  Vector-class pipeline     ← Collect + Normalize (+ help Topology bind keys)
   • accept vendor-shaped bytes
   • build joinable Signal / envelope (type, time, ci keys, severity, …)
   • route copies to the right sinks
        │
        ├──────────────────────────────┐
        ▼                              ▼
  Event Graph (Dragonfly)      Knowledge Graph (Vortex + DashMap)
  "what / when"                "who / why" (+ LOS / metrics)
```

**Why §2’s short ingest line looked incomplete**

The Motadata architecture brief often writes:

`NATS → Rust → Dragonfly`

That describes the **hot path into the Event Graph**. It **skips naming** the front door:

1. **Collectors** (already assumed by Motadata FR/AC — out of FR scope as “existing”).
2. **Vector-class Collect/Normalize** — turn raw telemetry into Motadata Signals / Nezha events with CI keys.
3. **Bus** (NATS) — move normalized traffic at scale.
4. **Rust** — pattern hash, dual-stream split, write Dragonfly **and** structural sinks.
5. **Topology upserts** into Vortex/DashMap (Fan-out’s “map” half).

So Vector was **missing from the Motadata Collect write-up**, not missing as a *job*. The job is still Collect → Normalize → Fan-out; Vector (or equivalent) is the intended **how** for Motadata fabric stages 1–2–4. Design detail: [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md).

**Fan-out in Motadata words (avoid DT confusion)**

| Teaching word | Motadata meaning |
|---------------|------------------|
| DT Fan-out | Same stream → Smartscape *and* Grail (different facets) |
| Motadata Fan-out | Same normalized stream → Event Graph *and* Knowledge Graph / LOS / metrics |
| Not | “Fan-out” = Nezha’s 256 Lua calls (that is Diagnose compute, stage 10) |

---

## 2. Motadata proposed architecture — Federated Part 1

Canonical Motadata design (supplementary to the multi-telemetry FR/AC — not a replacement for it). Same content as PoC [`REQUIREMENTS.md`](../federated-pipeline/docs/REQUIREMENTS.md) / Part 1 brief.

### 2.1 Tier 1 — Event Graph (Dragonfly) — “What” and “When”

| Design element | Tag |
|----------------|-----|
| Ingest high-velocity traces/logs/metrics into **temporal execution graphs** per request | Motadata architecture |
| **DragonflyDB** shared-nothing in-memory | Motadata architecture |
| Time-bucketed ZSETs `tg:{tenant}:{trace_id}:{minute}` | Motadata architecture |
| Sharded HSETs `pc:{phase}:{tenant}:{hash(pattern)%256}` (hot-key avoidance) | Motadata architecture |
| **Nezha** Expected vs Actual scoring `Score = S_C / (S_C + S_P)` via **server-side Lua** | Motadata architecture |

### 2.2 Tier 2 — Knowledge Graph (Vortex/Arrow + DashMap) — “Who” and “Why”

| Design element | Tag |
|----------------|-----|
| Persistent semantic microservice topology | Motadata architecture |
| **Vortex/Arrow CSR** for vectorized BFS / blast radius | Motadata architecture |
| **DashMap** lock-free LSM property store (~100×/s updates) | Motadata architecture |
| **Panorama** LOS + bounded look-back majority (gray failure) on DashMap | Motadata architecture |
| **Murphy** counterfactual MRF + Gibbs sampling on Vortex CSR (cyclic deps) | Motadata architecture |

### 2.3 End-to-end RCA flow (Motadata architecture)

```text
Ingestion (1B EPS):  collectors → Vector-class pipeline → NATS → Rust
                     → pattern hash → Dragonfly  ∥  Vortex/DashMap (topo + LOS + metrics)
Detection:           Panorama in-situ → DashMap LOS → gray-failure flags
Macro localization:  anomaly → Murphy on Vortex CSR (Gibbs / counterfactual)
Micro localization:  Rust → 256 Lua fans → Dragonfly Nezha scores → broken path
                     e.g. Auth→DB_Query  ⇒  Auth→DB_Timeout
Package:             fused verdict / Motadata incident (root CI + evidence + blast radius)
```

### 2.4 Collect path spelled out (Vector → dual sinks)

| Step | Motadata piece | DT 5+3+3 job | Notes |
|------|----------------|--------------|-------|
| 0 | Existing collectors (metric/log/flow/trap/trace/event) | Collect (sources) | FR/AC assumes collectors already exist |
| 1 | **Vector-class** sources + transforms | Collect + Normalize | Build unified Signal / envelope; preserve native keys (FR-A) |
| 2 | Entity resolution / bind keys | Topology bind (LUT half) | Stamp `ci_ref` / entity id (FR-B); Discovery/CMDB policy per §1.1 |
| 3 | NATS (or equivalent bus) | — (transport) | Scale handoff into compute |
| 4 | Rust normalizer / dual-stream writer | Fan-out | Speed → Dragonfly; structural → DashMap + Vortex edges (FR-1) |
| 5 | Continuous upserts + TTLs | Maintain | Keep KG fresh; Event Graph windows hot |

**Doc hygiene:** always show steps 1–2 when quoting Motadata ingest. Jumping straight to “NATS → Rust → Dragonfly” understates Collect/Normalize and the Knowledge Graph write path.

---

## 3. Crosswalk — Federated block → DT stage(s)

### 3.1 Architecture / stores

| Federated block | Nearest DT 5+3+3 | Gap | Notes |
|-----------------|------------------|-----|--------|
| Event Graph (Dragonfly) temporal execution graphs | **Grail** (evidence by `entityId`+time) + traces in lake | **Missing** as designed | Grail is a **multimodal lake**, not per-trace ZSET execution graphs or pattern-count shards. **Public framing / teaching.** |
| Knowledge Graph (Vortex CSR) | **Smartscape** (Topology + Maintain) | **Partial** | Both are “who is connected.” DT: discovery property graph (`calls`, `runsOn`). **No** CSR/Vortex, **no** Murphy Gibbs. **Public framing + teaching.** |
| DashMap LSM properties / LOS | Smartscape props + Grail series; no LOS | **Missing** | No Panorama Local Observation Store or bounded look-back majority in DT unveil. |
| NATS → Rust 1B EPS ingest | Collect (OneAgent/OTLP) | **Missing** (scale path) | Lab is tiny EPS; DT ingest is vendor-opaque. Motadata front door should include **Vector-class** Collect (§1.3) before NATS. |
| Fan-out to Dragonfly shards | Fan-out Smartscape ∥ Grail | **Partial (name collision)** | DT Fan-out = **map∥lake facets**. Motadata = **Event Graph ∥ Knowledge Graph**. Do not equate to Nezha’s 256 Lua fans. |
| **Vector-class pipeline** | Collect → Normalize → Fan-out | **Partial / under-named in §2 brief** | Job exists in Clock A teaching + [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md); Motadata Part 1 brief often omitted it (G9). |

### 3.2 Algorithms → diagnose stages

| Federated algorithm | Nearest DT stage | Gap | Notes |
|---------------------|------------------|-----|--------|
| **Panorama** Detect (gray failure / LOS) | **Detect** | **Partial / weak** | DT Detect = threshold/baseline **Events** on Grail series (**Observed** inventory error-rate Events in lab). **Not** Panorama majority look-back. |
| **Murphy** Macro localization | **Localize** (+ Curate seed) | **Missing** algo | DT Localize = Smartscape neighborhood walk (**Inferred**). **No** counterfactual MRF / Gibbs. |
| **Nezha** Micro localization (path pattern score) | **Identify** | **Missing** algo | DT Identify = scoped Grail pull + rank (**Inferred**). Lab Outcome = service-level `rootCauseEntity=inventory` (**Observed**), **not** Auth→DB_Timeout path rewrite via Lua/ZSET. |
| Expected vs Actual `S_C/(S_C+S_P)` on Dragonfly | — | **Missing** | No Nezha scoring layer in DT teaching pipeline. |
| 256-way Lua fan-out | — | **Missing** | No Dragonfly compute-offload story in DT unveil. |

### 3.3 RCA flow steps → 5+3+3

| Federated flow step | DT stages | Gap |
|---------------------|-----------|-----|
| Ingestion → Dragonfly | Collect → Normalize → Topology → Fan-out → Maintain | **Partial** ingest/normalize/bind; **Missing** Event Graph |
| Panorama detection | Detect | **Partial** (Events exist; Panorama algo missing) |
| Murphy macro localize | Curate seed tip + Localize | **Partial** topology use; **Missing** Murphy |
| Nezha micro localize | Identify | **Missing** Nezha |
| (operator package) | Package | **Covered** as *job* (Problem card) — different product semantics (**Observed** P-26084) |

```text
Federated:  Ingest → Panorama → Murphy → Nezha
DT teach:   Fabric(5) → Detect → Curate → Tailor → Localize → Identify → Package
```

Shared *intent*: continuous fabric, then detect, then localize root with evidence.  
Divergent *machinery*: two-tier Dragonfly/Vortex + named algos vs Smartscape∥Grail + Davis thin package.

### 3.4 All 11 DT stages → Federated requirements (detail)

FR ids from [`federated-pipeline/docs/REQUIREMENTS.md`](../federated-pipeline/docs/REQUIREMENTS.md). Fit uses the same Covered / Partial / Missing classes as §0.

| # | DT stage (teaching) | Job | Federated requirement (nearest) | Fit |
|---|---------------------|-----|----------------------------------|-----|
| **Phase 1 — Always-on fabric** |||||
| 1 | **Collect** | Bring MELT / multi-telem in | **Vector-class** sources + **FR-1a** NATS; prod vision 1B EPS | **Partial** — job clear; Vector under-named in short §2 brief (G9); 1B path Missing (G4) |
| 2 | **Normalize** | Envelope + ids | Vector transforms + **FR-1b** Rust → Nezha `Event`s / Motadata Signals | **Partial** — same objective; schemas differ |
| 3 | **Topology bind** | CI graph + stamp `entityId` | **FR-1d** dependency edges → Murphy CSR; entity identity | **Partial** — Vortex CSR ≈ Smartscape *objective*; **Discovery** ≈ edge/node upsert; **CMDB** optional (§1.1) |
| 4 | **Fan-out** | Map ∥ evidence facets | Vector/Rust dual-write → **Dragonfly** ∥ **DashMap/Vortex** | **Partial / name collision** (G6) — objective yes; stores ≠ Smartscape∥Grail |
| 5 | **Maintain** | Keep map + lake fresh | Continuous DashMap LSM (~100×/s), CSR refresh, Dragonfly TTL windows | **Partial** freshness job; Fed retention model differs |
| **Phase 2 — Case opens** |||||
| 6 | **Detect** | Per-entity Events (≠ Problem) | **FR-2a** **Panorama** gray failure via LOS majority | **Partial / weak** — DT = threshold/baseline Events; Fed = Panorama (G3) |
| 7 | **Curate** | Storm → seed `(entity, t0)` | **FR-2b / FR-3a** orchestrator routes flag → Murphy symptom; arbitration | **Partial** — seed/case tip as *job*; no Davis Problem-merge product |
| 8 | **Tailor** | Space ∩ time working set | **FR-2d** narrow Murphy → service + window for Nezha | **Partial** — corridor/cut exists; Fed cut is algo-handoff, not DQL Tailor |
| **Phase 3 — Diagnose** |||||
| 9 | **Localize** | Where (entity) | **FR-2c** **Murphy** posterior on Vortex CSR (Gibbs / counterfactual) | **Missing** algo (G2); topology *use* only **Partial** |
| 10 | **Identify** | What / path | **FR-2e** **Nezha** `S_C/(S_C+S_P)` on Dragonfly patterns | **Missing** (G1) — DT lab stops at service `rootCauseEntity` |
| 11 | **Package** | Problem / verdict card | **FR-2f / FR-4b** fused verdict API | **Covered** as *job* (ship one answer); product semantics differ |

**Federated read order on this grid:** Collect→Normalize (**Vector-class**) → Topology → Fan-out → Maintain ≈ fabric for **FR-1**; Detect≈**Panorama**; Curate/Tailor≈**orchestrator hops**; Localize≈**Murphy**; Identify≈**Nezha**; Package≈**fused verdict**.

**CMDB / Discovery on this grid:** only stage **3** (and Maintain of that graph). Discovery builds/updates Knowledge Graph edges; CMDB is still optional governance, not Vortex itself.

**Smartscape / Grail on this grid:** teaching labels only. Motadata achieves their *objectives* via Knowledge Graph + Event Graph (§1.2) — not by cloning those products.

---

## 4. Gap register (actionable)

### G1 — No Event Graph / Nezha compute plane — **Missing** · Priority P0 for Federated build

**Requirement:** Dragonfly ZSET/HSET + Lua Nezha scoring; micro path localization.  
**DT today:** Grail evidence + inferred Identify; lab stops at **service** root.  
**Block:** Cannot claim Nezha-equivalent “broken execution path” from DT unveil alone.

### G2 — No Vortex CSR + Murphy — **Missing** · P0

**Requirement:** Counterfactual MRF / Gibbs on cyclic infra graph.  
**DT today:** Smartscape walk (**Inferred** Localize).  
**Block:** Macro localization algorithm and cyclic counterfactuals unspecified in DT teaching.

### G3 — No Panorama LOS / gray-failure Detect — **Missing** · P1

**Requirement:** In-situ LOS + bounded look-back majority.  
**DT today:** Detector Events on series (**Observed** for hard 5xx cascade).  
**Block:** Gray-failure Detect path not represented; DT lab fault is **hard** failure-rate, not Panorama gray.

### G4 — 1B EPS / NATS / Rust ingest — **Missing** · P0 (platform)

**Requirement:** Shared-nothing ingest to Dragonfly at extreme EPS.  
**DT today:** OneAgent/OTLP Collect (**Public framing**); lab EPS negligible.  
**Block:** Scale and transport architecture not in DT 5+3+3 docs.

### G5 — Dual-graph identity model — **Partial** · P1

**Requirement:** Event Graph (execution) ∥ Knowledge Graph (semantic).  
**DT today:** Grail ∥ Smartscape under shared **`entityId`** (**Teaching / Public framing**).  
**Block:** Alignment story exists at *identity* level; **missing** execution-pattern graph distinct from entity topology.

### G6 — Fan-out semantics collision — **Teaching hazard** · P2

**DT Fan-out** ≠ Federated L0/F1 or Dragonfly shard fan-out.  
Docs already warn; keep gap visible so builders don’t wire the wrong “Fan-out.”

### G7 — Curate / Tailor vs Federated case cut — **Partial** · P2

**DT:** Event storm → seed → space/time working set (**Teaching / Inferred**).  
**Federated:** Often “shared Detect then Lean vs Fed”; Panorama/Murphy/Nezha sequencing differs.  
**Block:** Case-open *jobs* map loosely; **no** Lean/Fed fork on DT mechanisms page (by design).

### G8 — Package / Problem vs Nezha path evidence — **Partial** · P1

**Requirement:** Micro path string as first-class Nezha output.  
**DT Observed:** Problem + `rootCauseEntity`.  
**Block:** Evidence *packaging* exists; **path-pattern** evidence artifact does not.

### G9 — Vector-class Collect under-named in Motadata §2 brief — **Partial** · P1 (docs / fabric)

**Objective:** Collect → Normalize → route into dual sinks (Clock A stages 1–2–4).  
**Motadata §2 short form:** Often starts at `NATS → Rust → Dragonfly` — Event Graph hot path only.  
**Already designed elsewhere:** [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md); LIVE Vector configs in ingest PoC.  
**Block (clarity, not invention):** Teams may think Motadata has “no Collect stage” or confuse Vector with a lake. **Fix:** always document Vector-class (or equivalent) in front of NATS (§1.3, §2.4).

---

## 5. What the DT pipeline *does* give you (so gaps aren’t overstated)

Useful **covered / strong partial** foundations for a Motadata Federated build:

1. **Clock A fabric vocabulary** — Collect → … → Maintain (joinable identity + time).  
2. **Map ∥ evidence objectives** — “who” vs “what/when” (Motadata: Knowledge Graph ∥ Event Graph; DT names: Smartscape ∥ Grail — **objectives only**, §1.2).  
3. **Event ≠ Problem** — Detect storm before package (**Teaching**, matches lab).  
4. **Case scoping** — Curate seed + Tailor space/time (analogous *job* to “don’t scan whole lake”).  
5. **Comparable lab** — same FE→API→INV fault for DT vs DD honesty checks.  
6. **Vector-class ingest design** — shared Collect/Normalize/route fabric already sketched for Motadata ([`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md)); wire it explicitly into §2 (G9).

These are **necessary but not sufficient** for Motadata Federated Part 1 (still need Panorama / Murphy / Nezha / 1B path).

---

## 6. Recommended build order (Federated), mapped to gaps

| Order | Build | Closes |
|------|--------|--------|
| 0 | Document + wire **Vector-class** Collect/Normalize into Motadata fabric (before/alongside NATS) | G9 |
| 1 | Ingest path (NATS/Rust) + Dragonfly Event Graph schemas | G4, G1 (storage) |
| 2 | Knowledge Graph CSR + property LSM (Vortex/DashMap stand-ins OK) | G2 (store), G5 |
| 3 | Panorama LOS Detect | G3 |
| 4 | Murphy macro on KG | G2 (algo) |
| 5 | Nezha Lua micro on Event Graph | G1 (algo), G8 |
| 6 | Keep DT 5+3+3 as **vendor unveil / bakeoff lens**, not the Motadata runtime | G6 clarity |

---

## 7. One-page verdict

```text
DT 5+3+3              =  how we *explain* Dynatrace-shaped RCA (lab-proven Problem packaging)
Motadata architecture =  how Motadata *proposes to build* extreme-EPS causal RCA (§2)
Motadata FR/AC        =  broad *acceptance* bar (engine-agnostic product outcomes)

Objectives (not clones):
  "who" map     → Knowledge Graph     (DT teaching label: Smartscape)
  "what/when"   → Event Graph (+ LOS) (DT teaching label: Grail)
  Collect pipe  → Vector-class        (NOT a lake; fills both sinks)

Overlap:  fabric jobs, map∥evidence idea, detect-then-localize-then-package intent
Gaps:     Event Graph, Nezha, Murphy, Panorama LOS, 1B EPS ingest, CSR/LSM stacks,
          Vector under-named in short Motadata ingest line (G9)
          (architecture ↔ DT unveil — not FR/AC vs architecture)
```

**Do not** treat the DT teaching pipeline as implementation of Motadata §2. Use this gap map to see which Federated blocks are still **missing** after the unveil. Treat Motadata FR/AC + §2 as **supplementary layers** of one Motadata story. Ask *objective achievability*, not *Smartscape/Grail product parity*.

---

## 8. Motadata multi-telemetry FR/AC — supplementary acceptance bar

**Source:** [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](../multi-telemetry-rca-functional-and-acceptance-criteria.md) (draft 2026-07-31).

Both Motadata artifacts below are **supplementary**, not opposing:

| Motadata artifact | Layer | Answers |
|-------------------|-------|---------|
| **Multi-telemetry FR/AC** | Acceptance | Broad *what*: normalize every telemetry class → bind CI → correlate → one root cause + evidence + blast radius + incident |
| **Federated graph + RCA flow (§2)** | Proposed architecture / design | Detailed *how*: Dragonfly Event Graph ∥ Vortex KG; Panorama → Murphy → Nezha; 1B EPS ingest |

The FR/AC does **not** go deep on CMDB vs Discovery policy, dual-graph stores, Fan-out semantics, or Panorama/Murphy/Nezha. Those live in §2. Do **not** read “FR-E uses topology + signatures” as Motadata rejecting Federated algos — the AC stays engine-agnostic so product QA can pass without locking the implementation.

This gap map’s **Missing** rows (G1–G4) compare **§2 architecture ↔ DT 5+3+3 teaching**. Passing Motadata FR/AC validates product behavior; shipping §2 closes the Federated design gaps vs DT unveil.

### 8.1 FR/AC jobs ↔ DT 5+3+3 / §2 architecture

| Motadata FR | DT 5+3+3 / §2 nearest | How to read |
|-------------|----------------------|-------------|
| **FR-A** Signal ingest + normalize | Collect → Normalize; §2 ingest path | AC *what*; §2 NATS→Rust→Dragonfly is *how* at scale |
| **FR-B** Entity resolution | Topology bind LUT | AC requires `ci_ref`; §2 / DT use shared entity identity on KG / Smartscape |
| **FR-C** Shared topology + time | Topology + Maintain; Tailor | AC needs a shared graph + timeline. **FR-C1** names “Discovery/CMDB” as Motadata module shorthand — it does **not** decide discovery-first vs CMDB-gate (that policy is §1.1 / product design, not contradicted by AC) |
| **FR-D** Corr + suppress | Detect → Curate (+ Tailor) | AC *job*; §2 Detect is Panorama, case cut is orchestrator hops |
| **FR-E** Root-cause CI | Localize (+ Identify) | AC *outcome* (top-1 CI accuracy). §2 *engines* = Murphy macro + Nezha micro — not specified in FR text |
| **FR-F / G** Evidence + blast radius | Identify evidence + Package; Vortex BFS | AC *artifact*; §2 CSR traversal is one design for blast radius |
| **FR-H** Anomaly / storm seed | Detect + Curate storm | AC allows baseline/anomaly seeds; §2 adds Panorama gray-failure LOS (stronger than AC minimum) |
| **FR-I** One incident | Package | Shared *job* |
| **FR-J** ServiceOps / notify | — | Motadata product surface (outside DT teach / §2 core) |
| **FR-K / L / M** NFRs, RBAC, explain | §2 1B EPS + Package explain | AC = platform peak + explainability; §2 = extreme-EPS design target |

Scenarios **S1–S6** remain the right **acceptance** stories (one fault → one incident, multi-type evidence, no false infra blame). §2 is how Motadata proposes to win hard cases (gray failure, cyclic deps, path-level Identify) beyond the AC minimum.

### 8.2 What the FR/AC deliberately leaves open (filled by §2)

| Topic | FR/AC stance | §2 Motadata architecture |
|-------|--------------|--------------------------|
| Topology source of truth | Mentions Discovery/CMDB module; assumes usable topology | Knowledge Graph (Vortex) + DashMap; Discovery/CMDB policy orthogonal (§1.1) |
| Detect depth | Anomaly/pattern signals + storms (FR-H) | **Panorama** LOS + bounded look-back majority |
| Macro localize | Topo + severity + signature rules (outcome-level) | **Murphy** counterfactual MRF / Gibbs on CSR |
| Micro / path Identify | Not required for AC pass | **Nezha** on Dragonfly Lua / pattern scores |
| Store model | Unified Signal + shared topology (logical) | Dual tier: Event Graph ∥ Knowledge Graph |
| Scale | Sustain “platform peak” (FR-K) | **1B EPS** NATS → Rust → Dragonfly |

### 8.3 Practical reading

- **FR/AC** = Motadata **acceptance criteria** (broad, engine-agnostic).
- **§2** = Motadata **proposed architecture** (Federated Part 1) — closes G1–G4 relative to DT unveil when built; include **Vector-class Collect** explicitly (G9).
- **§1.2** = ask *objective achievability* (who-map / what-when evidence / one incident) — **not** Smartscape/Grail product parity.
- **This doc** = map §2 onto DT 5+3+3 and show which teaching stages are only *job*-aligned.
- Treat Motadata AC + Motadata architecture as **one product story, two layers** — supplementary, not contradictory.