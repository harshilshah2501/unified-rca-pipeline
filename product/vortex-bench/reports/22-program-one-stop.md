# Report 22 — Vortex bench program: one-stop guide for cold readers

**Audience:** anyone who did not sit through the Design v3 chats and needs one page that states what we decided, why, and where the detail lives.  
**Date:** 2026-10-13  
**Status:** Lab program through Report 21 is **closed** for the stated synthetic envelopes. This is **not** a Motadata-wide production architecture lock.  
**Owner path:** `product/vortex-bench/` (also linked from `docs/pillar-ab-implementation/vortex-bench/`).

If you read only one document from this folder, read **this**. Older Stage-4.2-only brief: [Report 11](./11-map-vortex-engineering-brief.md). Deep Stage 0–4.2 synthesis: [Report 10](./10-design-v3-comprehensive.md).

---

## 1. What this program was about (in plain words)

Motadata stores cold Dest data in **Vortex** files (a columnar on-disk format). Two Dest rooms use Vortex differently:

| Room | Product job | What the bench optimized |
| ---- | ----------- | ------------------------ |
| **Sketches** (`history/`, Pillar A) | Find anomalous windows, then open digests / buckets / exemplars | Keep Stage‑1 scans narrow so fat evidence columns are not decoded early |
| **Map** (`map/`, Pillar B) | Load topology once, then walk neighborhoods in Scope | Make **cold → hot adjacency rebuild** fast enough, and choose a walkable **hot index** that handles reverse (blast-radius) walks |

**Critical product fact for map:** Scope does **not** open Vortex on every neighbor hop. The path is:

```text
cold .vortex map parts  →  rebuild in-memory adjacency index  →  walk that index
```

Map **logical columns stay locked**. This program changes packing choices and the shape of the hot index — not the Motadata table schema.

---

## 2. Terms (defined once)

| Term | Meaning here |
| ---- | ------------ |
| **Cold → hot** | Decode Vortex map parts into process memory and build the walkable index. |
| **T_ready / T_cold-ready** | Time from start of load until the index can answer queries. |
| **T_mutation-visible** | Time from accepting a topology change until a **published** snapshot shows it. |
| **T_query** | Time for a Scope-like walk on a published (pinned) snapshot. |
| **Clustered edges** | Edge rows written sorted by source → edge type → target (faster rebuild). |
| **Hash** | Forward-only map: source → neighbors. Reverse walks scan everything (slow when reverse matters). |
| **hash_bi** | Forward map **and** reverse map. |
| **CSR+CSC (`csr_csc`)** | Packed forward arrays plus packed reverse arrays. Smaller retained index; slower rebuild than hash. |
| **Segmented CSR+CSC** | Same packed idea, but the graph is split into node groups so a mutation can rebuild only touched groups, then publish a new snapshot. |
| **Operating envelope** | Explicit synthetic workload we agreed to decide under (because real Motadata histograms were not available). |
| **Milestone A** | Pick the conventional serve / recovery baselines among `hash`, `hash_bi`, `csr_csc`. |
| **Milestone B** | Decide whether segmented CSR+CSC earns its complexity for mutations. |

---

## 3. Bottom line — what to do with the architecture

```text
Serve / concurrent Scope walks     →  conventional csr_csc   (FROZEN)
Fastest cold→ready reconstruction  →  hash                   (reference only)
Localized topology mutations       →  segmented csr_csc      (conditional candidate)
Large / all-segment-touch publishes→  conventional full rebuild
Per-segment edge journals          →  NOT adopted (separate idea, still open)
Vortex cold map columns            →  unchanged / locked
```

**In one sentence:** use packed forward+reverse arrays (`csr_csc`) for serving Scope; remember hash rebuilds faster after restart; use segmented rebuild only when mutations usually touch a small part of the estate.

This recommendation is **envelope-conditional**: it rests on approved synthetic graphs and query mixes, not measured Motadata production traffic.

---

## 4. Story arc (how the 21 reports fit together)

```text
Reports 01–03     Two Dest rooms, different jobs (sketches vs map)
Reports 04–09     Design v3 stages: controls, layouts, synthetic estates
Report 10–11      Synthesis + cold-reader brief (through Stage 4.2)
Reports 12–17     Milestone A: correctness → envelope → pick serve/recovery
Reports 18–21     Milestone B: mutation lifecycle → conditional segmented adopt
Report 22         This one-stop page
```

---

## 5. Report-by-report digest (what each proved)

### A. Opening pair — sketches vs map

| Report | Title | Derived conclusion in simple words |
| -----: | ----- | ---------------------------------- |
| **01** | Sketch physical layout | Sketch rows are **wide**. Stage‑1 RCA must project a **hot spine** and decode digests / exemplars only when a window is a real candidate. Physical layout matters for sketches. |
| **02** | Map load / adjacency | Map rows are already **flat**. The bottleneck is **building the hot index**, not nested schema. Clustered edge publish helps; spine load is good hygiene. |
| **03** | Comparative analysis | Same Vortex engine, **two playbooks**. Do **not** copy the sketch layout matrix onto map tables. |

### B. Design v3 stages — make the map evidence trustworthy

| Report | Title | Derived conclusion in simple words |
| -----: | ----- | ---------------------------------- |
| **04** | Stage 1 — order × builder 2×2 | Separates “clustered edges” from “sort-aware builder.” Both matter; do not confound them into one fake win. |
| **05** | Stage 2 — factor screen | Ranks which knobs move rebuild and query cost under one protocol. |
| **06** | Stage 3 — layout deep compare | First multi-layout screen (hash / CSR / CSR+CSC / hybrid). Useful but **not** yet a fair reverse compare. |
| **07** | Stage 3.5 — fair compare | Adds **hash_bi** and equal reverse work for every layout. Forward-only hash (and forward-only CSR) **fail** when reverse walks matter. |
| **08** | Stage 4.1 — estate properties | Six synthetic graph families with structural checks so later screens are not one accidental shape. |
| **09** | Stage 4.2 — layout screen ≤5M | Same query traces replayed across layouts. Shows **crossovers**: hash wins rebuild; CSR+CSC wins retained memory and reverse when that mix is needed. |
| **10** | Comprehensive synthesis | End-to-end Design v3 narrative for teammates who only remember Report 02. |
| **11** | Engineering brief (Stage 4.2 era) | Short shareable brief **before** Milestone A/B closed. Prefer **this Report 22** for current decisions. |

### C. Milestone A — conventional hot-index selection (Reports 12–17)

| Report | Title | Derived conclusion in simple words |
| -----: | ----- | ---------------------------------- |
| **12** | Correctness oracle | Independent typed-edge checks. Found and fixed a sort-aware natural-order bug that dropped edges. All three candidates then pass. |
| **13** | Operating envelope | Real Motadata mix unavailable → **waiver-approved** synthetic estate `motadata_like_hubby` and Scope mix ~70% forward / 20% reverse / 10% dependency (hops=2). Winners stay tied to this envelope. |
| **14** | Final three-layout compare | Under that envelope, **`csr_csc`** wins query latency and retained index size at 1M and 5M. **`hash`** rebuilds fastest but reverse latency is unacceptable for the mix. |
| **15** | Cold-to-hot recovery | **`hash`** is fastest to become query-ready after cold start. Serve winner ≠ recovery winner — both must be stated. Real Dest object-store remote-cold still unmeasured. |
| **16** | Concurrency + memory | Under many concurrent readers, **`csr_csc`** keeps (and widens) the lead. Forward-only **`hash` reverse collapses**. |
| **17** | Milestone A close | **FROZEN:** serve baseline = **`csr_csc`**; recovery-speed reference = **`hash`**. Do not reopen the three-layout pick without production evidence that contradicts the envelope. |

### D. Milestone B — mutation lifecycle (Reports 18–21)

| Report | Title | Derived conclusion in simple words |
| -----: | ----- | ---------------------------------- |
| **18** | Mutation locality ladder | Segmented rebuild helps when a batch touches **few** segments (~2× faster at 1M). When a batch touches **every** segment, segmented loses to a simple full rebuild. |
| **19** | Atomic publish + dual-hold memory | Readers see either the old complete snapshot or the new one (not a mix). Holding two generations costs ~1.7–1.8× memory during publish in the lab model. |
| **20** | Durability / replay | Injected crash points: incomplete snapshots are not committed; recovery matches expected generation; stale pending state is handled safely. **Lab durability model only** — not Motadata’s production commit protocol. |
| **21a** | 5M thin ladder | Localized win holds at 5M (~0.38–0.41× conventional). Medium all-touch batch ≈ tie / slight loss (~1.02×). |
| **21** | Milestone B close | **CLOSED (conditional):** keep segmented CSR+CSC for **localized** mutations; keep conventional `csr_csc` as serve path; do **not** adopt per-segment journals in this close. |

---

## 6. Decisions locked (and what they are not)

### Locked for the lab envelopes

| Decision | Locked meaning |
| -------- | -------------- |
| Clustered publish + sort-aware build | Default packing for map cold parts in this program |
| Serve baseline | Conventional **`csr_csc`** |
| Recovery reference | **`hash`** (speed after restart / failover in lab coldness tiers) |
| Segmented CSR+CSC | Worth complexity **only** when mutations are localized |
| Map schema | Unchanged |
| Sketch vs map playbooks | Stay separate |

### Explicitly not locked

- Motadata production traffic mix or real customer topology.
- True Dest S3 / object-store remote-cold numbers (`remote_proxy` was a local stand-in).
- Motadata production durability / commit protocol (Report 20 is a lab crash model).
- Universal “segmented always wins.”
- Per-segment edge journals (still a separate optimization idea).

---

## 7. How to choose in practice (routing guide)

Ask these questions in order:

1. **Are we serving Scope walks with meaningful reverse / blast-radius?**  
   → Prefer **`csr_csc`**. Do not ship forward-only **`hash`** as the serve index for that mix.

2. **Is the urgent constraint restart / failover time to first query?**  
   → **`hash`** is the fastest rebuild reference. Product may still choose `csr_csc` and accept slower ready time if reverse walks and memory matter more.

3. **Do topology updates usually touch a small region of the estate?**  
   → Segmented CSR+CSC is a **justified candidate** (lab: ~2–2.6× faster mutation visibility at 1M–5M for small batches).

4. **Do publishes routinely rewrite large fractions / every segment?**  
   → Prefer **conventional full rebuild**; segmented adds complexity without a win.

5. **Do we have measured Motadata mutation locality yet?**  
   → If no, treat segmented as **conditional**, not a Motadata-wide mandate.

---

## 8. Evidence map (where to click next)

| If you need… | Open |
| ------------ | ---- |
| Current architecture call | **This report** + [Report 17](./17-milestone-a-close.md) + [Report 21](./21-action6-milestone-b-close.md) |
| Sketch layout numbers | [Report 01](./01-sketch-physical-layout.md) |
| Why map ≠ sketch | [Report 03](./03-comparative-analysis.md) |
| Stage 0–4.2 deep dive | [Report 10](./10-design-v3-comprehensive.md) |
| Envelope we decided under | [Report 13](./13-action2-operating-envelope.md) · [`action2-synthetic-operating-envelope.md`](../design-v3/action2-synthetic-operating-envelope.md) |
| Query / index numbers | [Report 14](./14-action3-final-compare.md) |
| Recovery numbers | [Report 15](./15-action4-cold-recovery.md) |
| Concurrent readers | [Report 16](./16-action5-concurrency.md) |
| Mutation locality | [Report 18](./18-action6-mutation-lifecycle.md) · [Report 21a](./21-action6-5m-thin-ladder.md) |
| Publish atomicity / dual memory | [Report 19](./19-action6-atomic-publish.md) |
| Crash / replay lab model | [Report 20](./20-action6-durability-replay.md) |
| Mutation envelope waiver | [`action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md) |
| Segmented design hypothesis | [`Map_Vortex_Graph_Architecture_Decision_Record.md`](./Map_Vortex_Graph_Architecture_Decision_Record.md) |
| Program gates | [`../design-v3/gates.md`](../design-v3/gates.md) |

---

## 9. What would reopen these decisions

Only reopen if Motadata brings **measured** evidence that contradicts the envelopes, for example:

- Reverse share in Scope is near zero (would revive forward-only hash as a serve option).
- Recovery-time SLO is so tight that `csr_csc` T_ready is unacceptable even with a slower reverse path elsewhere.
- Production mutation batches routinely touch most of the estate (would drop segmented below “conditional candidate”).
- Production mutation batches are strongly localized and durability matches Motadata’s real commit protocol (would strengthen promoting segmented beyond lab-conditional).

Until then: **do not reopen Milestone A**, and **do not invent a new optimization hypothesis** before recording why Report 21’s conditional call is insufficient.

---

## 10. Full report index

| # | File |
| - | ---- |
| 01 | [`01-sketch-physical-layout.md`](./01-sketch-physical-layout.md) |
| 02 | [`02-map-load-adjacency.md`](./02-map-load-adjacency.md) |
| 03 | [`03-comparative-analysis.md`](./03-comparative-analysis.md) |
| 04 | [`04-design-v3-stage1-reproduce.md`](./04-design-v3-stage1-reproduce.md) |
| 05 | [`05-design-v3-stage2-screen.md`](./05-design-v3-stage2-screen.md) |
| 06 | [`06-design-v3-stage3-layouts.md`](./06-design-v3-stage3-layouts.md) |
| 07 | [`07-design-v3-stage3_5-fair.md`](./07-design-v3-stage3_5-fair.md) |
| 08 | [`08-design-v3-stage4_1-properties.md`](./08-design-v3-stage4_1-properties.md) |
| 09 | [`09-design-v3-stage4_2-screen.md`](./09-design-v3-stage4_2-screen.md) |
| 10 | [`10-design-v3-comprehensive.md`](./10-design-v3-comprehensive.md) |
| 11 | [`11-map-vortex-engineering-brief.md`](./11-map-vortex-engineering-brief.md) |
| 12 | [`12-action1-correctness-oracle.md`](./12-action1-correctness-oracle.md) |
| 13 | [`13-action2-operating-envelope.md`](./13-action2-operating-envelope.md) |
| 14 | [`14-action3-final-compare.md`](./14-action3-final-compare.md) |
| 15 | [`15-action4-cold-recovery.md`](./15-action4-cold-recovery.md) |
| 16 | [`16-action5-concurrency.md`](./16-action5-concurrency.md) |
| 17 | [`17-milestone-a-close.md`](./17-milestone-a-close.md) |
| 18 | [`18-action6-mutation-lifecycle.md`](./18-action6-mutation-lifecycle.md) |
| 19 | [`19-action6-atomic-publish.md`](./19-action6-atomic-publish.md) |
| 20 | [`20-action6-durability-replay.md`](./20-action6-durability-replay.md) |
| 21a | [`21-action6-5m-thin-ladder.md`](./21-action6-5m-thin-ladder.md) |
| 21 | [`21-action6-milestone-b-close.md`](./21-action6-milestone-b-close.md) |
| **22** | **This document** |
