# Federated architecture requirement vs Dynatrace 5+3+3 pipeline — gap map

**Purpose:** Map Part 1 (Federated two-tier graph + Nezha / Murphy / Panorama RCA flow) onto the Dynatrace teaching pipeline we documented: **5 Always-on fabric + 3 Case opens + 3 Diagnose**. Call out **covered**, **partial**, and **missing** blocks with epistemic labels.

**Browser:** [`federated-vs-dt-pipeline-gaps.html`](./federated-vs-dt-pipeline-gaps.html) · [`:8765`](http://127.0.0.1:8765/federated-vs-dt-pipeline-gaps.html)

**Cursor canvas (IDE only):** `canvases/federated-vs-dt-pipeline-gaps.canvas.tsx` beside chat — not served by the PoC console.

**Related:** [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) · [`eleven-subsystem-mechanisms.html`](./eleven-subsystem-mechanisms.html) · [`federated-pipeline/docs/REQUIREMENTS.md`](../federated-pipeline/docs/REQUIREMENTS.md)

---

## 0. How to read this document

| Side | What it is |
|------|------------|
| **Federated requirement** | Target ObserveOps-style architecture (Dragonfly Event Graph + Vortex Knowledge Graph; Panorama → Murphy → Nezha) aimed at **1B EPS** and deep causal analysis |
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
| **Requirement** | Stated Federated target (not validated at 1B EPS in this PoC) |

**Nothing here is 100% Dynatrace-internal accuracy.** Federated rows are **requirement** claims; DT rows are **teaching + lab + public/inferred**.

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

Our lab is **discovery-first** (auto-create `SERVICE-INV` on first sighting). A CMDB-strict kit can instead **orphan** until an approved CI exists — opposite gate. Full write-up: [`DYNATRACE_PRODUCTION_PIPELINE.md`](./DYNATRACE_PRODUCTION_PIPELINE.md) §5.3.

On the Federated side, Discovery ≈ feeding the **Knowledge Graph** (Vortex CSR edges + entity identity). CMDB remains optional governance, not Vortex itself.

---

## 2. Federated Part 1 — required blocks

### 2.1 Tier 1 — Event Graph (Dragonfly) — “What” and “When”

| Requirement element | Tag |
|---------------------|-----|
| Ingest high-velocity traces/logs/metrics into **temporal execution graphs** per request | Requirement |
| **DragonflyDB** shared-nothing in-memory | Requirement |
| Time-bucketed ZSETs `tg:{tenant}:{trace_id}:{minute}` | Requirement |
| Sharded HSETs `pc:{phase}:{tenant}:{hash(pattern)%256}` (hot-key avoidance) | Requirement |
| **Nezha** Expected vs Actual scoring `Score = S_C / (S_C + S_P)` via **server-side Lua** | Requirement |

### 2.2 Tier 2 — Knowledge Graph (Vortex/Arrow + DashMap) — “Who” and “Why”

| Requirement element | Tag |
|---------------------|-----|
| Persistent semantic microservice topology | Requirement |
| **Vortex/Arrow CSR** for vectorized BFS / blast radius | Requirement |
| **DashMap** lock-free LSM property store (~100×/s updates) | Requirement |
| **Panorama** LOS + bounded look-back majority (gray failure) on DashMap | Requirement |
| **Murphy** counterfactual MRF + Gibbs sampling on Vortex CSR (cyclic deps) | Requirement |

### 2.3 End-to-end RCA flow (requirement)

```text
Ingest 1B EPS:  NATS → Rust → pattern hash → Dragonfly
Detect:         Panorama in-situ → DashMap LOS → gray-failure flags
Macro localize: anomaly → Murphy on Vortex CSR (Gibbs / counterfactual)
Micro localize: Rust → 256 Lua fans → Dragonfly Nezha scores → broken path
                e.g. Auth→DB_Query  ⇒  Auth→DB_Timeout
```

---

## 3. Crosswalk — Federated block → DT stage(s)

### 3.1 Architecture / stores

| Federated block | Nearest DT 5+3+3 | Gap | Notes |
|-----------------|------------------|-----|--------|
| Event Graph (Dragonfly) temporal execution graphs | **Grail** (evidence by `entityId`+time) + traces in lake | **Missing** as designed | Grail is a **multimodal lake**, not per-trace ZSET execution graphs or pattern-count shards. **Public framing / teaching.** |
| Knowledge Graph (Vortex CSR) | **Smartscape** (Topology + Maintain) | **Partial** | Both are “who is connected.” DT: discovery property graph (`calls`, `runsOn`). **No** CSR/Vortex, **no** Murphy Gibbs. **Public framing + teaching.** |
| DashMap LSM properties / LOS | Smartscape props + Grail series; no LOS | **Missing** | No Panorama Local Observation Store or bounded look-back majority in DT unveil. |
| NATS → Rust 1B EPS ingest | Collect (OneAgent/OTLP) | **Missing** (scale path) | Lab is tiny EPS; DT ingest is vendor-opaque. **Not** our NATS/Dragonfly pipeline. |
| Fan-out to Dragonfly shards | Fan-out Smartscape ∥ Grail | **Partial (name collision)** | DT Fan-out = **map∥lake facets**. Federated = **tiered sinks / Event Graph write path**. Do not equate. |

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
| 1 | **Collect** | Bring MELT in | **FR-1a** NATS ingest of traces/logs/metrics; prod vision 1B EPS | **Partial** job / **Missing** NATS·Rust·1B path (G4) |
| 2 | **Normalize** | Envelope + ids | **FR-1b** Rust → Nezha `Event`s; dual-stream split (speed vs structural) | **Partial** (envelope idea); Fed schema ≠ DT `failed_call` / `raw_ids` |
| 3 | **Topology bind** | CI graph + stamp `entityId` | **FR-1d** dependency edges → Murphy CSR; entity identity | **Partial** — Vortex CSR ≈ Smartscape *job*; **Discovery** ≈ edge/node upsert; **CMDB** optional (§1.1) |
| 4 | **Fan-out** | Map ∥ lake facets | Speed → **Dragonfly** (events) ∥ structural → **DashMap/Vortex** (topo + LOS + metrics) | **Partial / name collision** (G6) — same *split sinks* idea, different stores |
| 5 | **Maintain** | Keep map + lake fresh | Continuous DashMap LSM (~100×/s), CSR refresh, Dragonfly TTL windows | **Partial** freshness job; Fed retention model differs |
| **Phase 2 — Case opens** |||||
| 6 | **Detect** | Per-entity Events (≠ Problem) | **FR-2a** **Panorama** gray failure via LOS majority | **Partial / weak** — DT = threshold/baseline Events; Fed = Panorama (G3) |
| 7 | **Curate** | Storm → seed `(entity, t0)` | **FR-2b / FR-3a** orchestrator routes flag → Murphy symptom; arbitration | **Partial** — seed/case tip as *job*; no Davis Problem-merge product |
| 8 | **Tailor** | Space ∩ time working set | **FR-2d** narrow Murphy → service + window for Nezha | **Partial** — corridor/cut exists; Fed cut is algo-handoff, not DQL Tailor |
| **Phase 3 — Diagnose** |||||
| 9 | **Localize** | Where (entity) | **FR-2c** **Murphy** posterior on Vortex CSR (Gibbs / counterfactual) | **Missing** algo (G2); topology *use* only **Partial** |
| 10 | **Identify** | What / path | **FR-2e** **Nezha** `S_C/(S_C+S_P)` on Dragonfly patterns | **Missing** (G1) — DT lab stops at service `rootCauseEntity` |
| 11 | **Package** | Problem / verdict card | **FR-2f / FR-4b** fused verdict API | **Covered** as *job* (ship one answer); product semantics differ |

**Federated read order on this grid:** Collect→…→Maintain ≈ fabric for **FR-1**; Detect≈**Panorama**; Curate/Tailor≈**orchestrator hops**; Localize≈**Murphy**; Identify≈**Nezha**; Package≈**fused verdict**.

**CMDB / Discovery on this grid:** only stage **3** (and Maintain of that graph). Discovery builds/updates Knowledge Graph edges; CMDB is still optional governance, not Vortex itself.

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

**DT Observed:** Problem + `rootCauseEntity`.  
**Federated:** Micro path string as first-class Nezha output.  
**Block:** Evidence *packaging* exists; **path-pattern** evidence artifact does not.

---

## 5. What the DT pipeline *does* give you (so gaps aren’t overstated)

Useful **covered / strong partial** foundations for a Federated build:

1. **Clock A fabric vocabulary** — Collect → … → Maintain (joinable identity + time).  
2. **Map ∥ lake** — Smartscape-like “who” vs Grail-like “evidence” (even if not Dragonfly/Vortex).  
3. **Event ≠ Problem** — Detect storm before package (**Teaching**, matches lab).  
4. **Case scoping** — Curate seed + Tailor space/time (analogous *job* to “don’t scan whole lake”).  
5. **Comparable lab** — same FE→API→INV fault for DT vs DD honesty checks.

These are **necessary but not sufficient** for Part 1 Federated architecture.

---

## 6. Recommended build order (Federated), mapped to gaps

| Order | Build | Closes |
|------|--------|--------|
| 1 | Ingest path (NATS/Rust) + Dragonfly Event Graph schemas | G4, G1 (storage) |
| 2 | Knowledge Graph CSR + property LSM (Vortex/DashMap stand-ins OK) | G2 (store), G5 |
| 3 | Panorama LOS Detect | G3 |
| 4 | Murphy macro on KG | G2 (algo) |
| 5 | Nezha Lua micro on Event Graph | G1 (algo), G8 |
| 6 | Keep DT 5+3+3 as **vendor unveil / bakeoff lens**, not the Federated runtime | G6 clarity |

---

## 7. One-page verdict

```text
DT 5+3+3  =  how we *explain* Dynatrace-shaped RCA (lab-proven Problem packaging)
Federated =  how we *intend to build* extreme-EPS causal RCA (Dragonfly + Vortex + Panorama/Murphy/Nezha)

Overlap:  fabric jobs, map∥evidence idea, detect-then-localize-then-package intent
Gaps:     Event Graph, Nezha, Murphy, Panorama LOS, 1B EPS ingest, CSR/LSM stacks
```

**Do not** treat the DT teaching pipeline as implementation of Part 1. Use this gap map to see which Federated blocks are still **missing** after the unveil.
