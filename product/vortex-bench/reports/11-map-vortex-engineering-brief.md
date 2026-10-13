# Motadata map Vortex — engineering brief (cold readers)

**Audience:** engineers who did not sit through Design v3 chats and need a single shareable brief.  
**Date:** 2026-10-12 (updated pointers 2026-10-13)  
**Status:** Lab evidence through Design v3 Stage **4.2** (synthetic). Milestone A/B closed later — see **[Report 22](./22-program-one-stop.md)** for the current one-stop guide. **Not** a Motadata production architecture approval.  
**Owner path in repo:** `product/vortex-bench/`

If you need the **current** program close (Reports 01–21 + locked decisions), read **[Report 22](./22-program-one-stop.md)** instead. This page remains the Stage‑4.2-era brief. Deep dive: [Report 10](./10-design-v3-comprehensive.md). ADR after measurement: [Architecture Decision Record](./Map_Vortex_Graph_Architecture_Decision_Record.md).

---

## 1. Sixty-second takeaway

1. Motadata Scope does **not** open Vortex per neighbor hop. Product path is: load cold `.vortex` map parts → rebuild an in-memory **adjacency index** → walk that index.
2. On that path, **building the index dominates** decode and the first walk. Publishing edges in **clustered** order (source → edge type → target) and using a **sort-aware** builder remains the right packing default.
3. **Forward-only hash adjacency** rebuilds fastest but makes **reverse / blast-radius** queries slow (hundreds of milliseconds to seconds at multi-million edges).
4. If reverse walks matter, you need either **bidirectional hash (`hash_bi`)** or **packed forward+reverse arrays (CSR+CSC)**. Forward-only CSR is **not** enough.
5. In synthetic screens, `hash_bi` and CSR+CSC are similar on reverse latency; CSR+CSC usually keeps a **smaller retained index**; hash_bi usually **builds faster**.
6. Everything above is **synthetic**. Real Motadata estates, mutation rates, and SLOs are still required before locking GraphWriter.

---

## 2. Terms (defined once)

| Term | Meaning in this brief |
| ---- | --------------------- |
| **Vortex** | Columnar file format used for Motadata cold Dest parts. |
| **Cold → hot** | Decode Vortex map tables into process memory and build the walkable index. |
| **Spine load** | Decode only columns needed to rebuild walks (edge `source_id`, `target_id`, `edge_type`, and the matching node identity columns)—not every tag or evidence field. |
| **Clustered edges** | Edge rows written sorted by source, then edge type, then target (better rebuild locality). |
| **Natural edges** | Edge rows in generation order (control in labs; usually slower rebuild). |
| **Hash** | One forward map: source → list of `(target, edge_type)`. Reverse = scan everything. |
| **hash_bi** | Forward map **and** reverse map. |
| **CSR / CSC** | Packed adjacency arrays (forward / reverse). **CSR+CSC** means both directions packed. |
| **Hybrid** | CSR+CSC base plus a small mutable delta (inserts/deletes by occurrence count). |
| **Scope** | Motadata neighborhood walk over the **hot** index after rebuild (not per-hop Vortex I/O). |

Motadata **map schema columns stay locked**. This work changes packing and the hot index, not the logical tables.

---

## 3. What problem we are solving

Pillar B map already has a flat, locked schema (`map_nodes` / `map_edges`). The expensive product moment is **process start / failover / refresh**: load Dest Vortex parts and reconstruct adjacency so Scope can walk.

We are **not** redesigning nested map schemas. We are answering:

- Which **publish / load / build** choices make cold→hot fast enough?
- Which **hot index shapes** stay viable when queries include reverse walks?
- Where do layouts **cross over** under different graph shapes and query mixes?

---

## 4. What we measured (and what we did not)

### Measured (Design v3 Stages 0–4.2)

| Topic | Result location |
| ----- | --------------- |
| Clustered vs natural publish; naive vs sort-aware build | [Report 04](./04-design-v3-stage1-reproduce.md), [05](./05-design-v3-stage2-screen.md) |
| Fair compare of hash, hash_bi, CSR, CSR+CSC, hybrid (equal reverse mix) | [Report 07](./07-design-v3-stage3_5-fair.md) |
| Six synthetic graph families with structural validation | [Report 08](./08-design-v3-stage4_1-properties.md) |
| Same query traces replayed across layouts; workload profiles; ≤5M edges | [Report 09](./09-design-v3-stage4_2-screen.md) |
| End-to-end synthesis | [Report 10](./10-design-v3-comprehensive.md) |

Stage 4.2 coverage in plain words:

- **Full matrix** at 500k and 1M edges across six synthetic families and three experimental query mixes.
- **Thin 5M ladder** (uniform and hubby, balanced mix, five layouts) as a ceiling check—not a full 5M factorial.

Query mixes used in the lab (these are **scenarios**, not Motadata production estimates):

| Profile | Forward | Reverse | Dependency chain |
| ------- | ------: | ------: | ---------------: |
| Forward-dominant | 90% | 5% | 5% |
| Balanced | 45% | 45% | 10% |
| Reverse-heavy | 20% | 70% | 10% |

Seeds are chosen from out-degree percentiles among sources that have edges (`p10` / `p50` / `p90`). Reverse-heavy traces also include the highest-degree hub. The **same** trace file is replayed for every layout in a cell.

Coldness label: **`process_cold`** (fresh decode/build in-process). Operating-system page cache may still be warm. We did **not** measure drop-cache disk-cold or remote object-store cold.

### Not measured yet

- Real Motadata customer graphs or production query traces  
- Concurrent readers overlapping a rebuild  
- Mutation / lifecycle economics (Stage 4.2 ran hybrid with **zero churn**)  
- Disk-cold / remote-cold Dest paths  
- The proposed **segmented CSR+CSC** design in the Architecture Decision Record  

---

## 5. Engineering conclusions you can act on now

These are **lab-backed defaults for further Motadata GraphWriter design**, not a ship gate.

### 5.1 Publish and load (stable across Design v3)

| Choice | Guidance |
| ------ | -------- |
| Edge order at publish | Prefer **clustered** (`source_id` → `edge_type` → `target_id`). |
| Adjacency builder | Prefer **sort-aware** when edges are clustered. Do not claim sort-aware as a win on natural order. |
| Decode set for rebuild | Prefer **spine** columns for walk rebuild; defer tags / evidence until UI needs them. |
| Schema | **Do not** reopen map column redesign for layout performance. |

### 5.2 Hot index selection (mode-dependent)

| Product mode | Lab envelope |
| ------------ | ------------ |
| Rebuild / failover latency first; Scope mostly **forward** after the index exists | **Hash** (clustered + sort-aware) is the fastest rebuild baseline. |
| Reverse walks or blast-radius queries are **common** | Use **hash_bi** or **CSR+CSC**. Do **not** ship forward-only hash or CSR-only for that mode. |
| Retained index memory matters after build | Prefer **CSR+CSC** over hash_bi in the synthetic screen (often ~half the estimated retained bytes). |
| Need in-place mutation without full packed rebuild | **Hybrid** is a candidate only; Stage 4.2 did **not** prove mutation economics. |

### 5.3 Numbers engineers usually ask for (hubby, balanced, synthetic)

Illustrative medians from Stage 4.2 (not SLOs):

| Edges | Layout | Build (ms) | Reverse p95 (ms) | Est. retained index |
| ----: | ------ | ---------: | ---------------: | ------------------: |
| 500k | hash | ~142 | ~244 | ~62 MB |
| 500k | hash_bi | ~309 | ~0.04 | ~111 MB |
| 500k | CSR+CSC | ~450 | ~0.04 | ~48 MB |
| 1M | hash | ~407 | ~706 | ~127 MB |
| 1M | hash_bi | ~924 | ~0.06 | ~225 MB |
| 1M | CSR+CSC | ~1357 | ~0.06 | ~96 MB |
| 5M | hash | ~2909 | ~3961 | ~636 MB |
| 5M | hash_bi | ~6876 | ~0.05 | ~1.1 GB |
| 5M | CSR+CSC | ~10578 | ~0.03 | ~510 MB |

Reading guide: hash wins **time-to-index**; hash_bi and CSR+CSC win **reverse**; CSR+CSC wins **retained size** among the fast-reverse pair.

Full tables and other families: [Report 09](./09-design-v3-stage4_2-screen.md).

### 5.4 Correctness hygiene

Stage 4.2 screen cells reported walk checksum agreement versus forward hash with hybrid churn off. That checks **layout equivalence under the lab walk**, not full Motadata semantic completeness.

---

## 6. What leadership / ADR discussion proposed next (hypothesis only)

A separate Architecture Decision Record proposes moving toward:

- **Segmented** bidirectional adjacency (node-group chunks, not one monolithic CSR+CSC),  
- **Incremental copy-on-write** rebuild of affected groups,  
- **Atomic snapshot publish** so forward and reverse never disagree across groups,  
- Queries that **pin** one snapshot, with bounded reader lifetime before reclaim.

That proposal is a **design hypothesis**. It was **not** benchmarked in Stages 4.0–4.2. Conventional CSR+CSC numbers **do not transfer** automatically to a segmented implementation.

Open items in that ADR (correctly unresolved): visibility budget (seconds), durability/replay, partition thresholds, query timeout policy.

Read: [Architecture Decision Record (Markdown)](./Map_Vortex_Graph_Architecture_Decision_Record.md) · [Word copy](./Map_Vortex_Graph_Architecture_Decision_Record.docx).

---

## 7. What engineering should do next (decision-validation sprint)

Full program: [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md).  
Milestone A **FROZEN** ([Report 17](./17-milestone-a-close.md)): serve baseline **`csr_csc`**; recovery reference **`hash`**. Milestone B / Action 6 **CLOSED** ([Report 21](./21-action6-milestone-b-close.md)): segmented CSR+CSC retained as a **conditional** candidate for localized mutations only; conventional `csr_csc` remains the serve path. Per-segment journals stay a separate hypothesis.

### Do

1. **Freeze** primary candidates to `hash` · `hash_bi` · `csr_csc` — no new layout variants in the primary matrix.  
2. Get Motadata to fill (or formally waive) success criteria: query mix, latency SLO, recovery budget, memory ceiling, freshness.  
3. Strengthen correctness beyond walk checksums, then run Milestone A (final compare, real cold→hot, concurrency/memory).  
4. Treat **clustered publish + sort-aware + spine load** as the default cold packing path.  
5. Keep synthetic profiles labeled **experimental** unless an approved Motadata envelope replaces them.

### Do not

1. Do **not** declare a production winner from Stage 4.2 alone.  
2. Do **not** expand the architecture zoo before Milestone A closes.  
3. Do **not** treat hybrid Stage 4.2 numbers as mutation proof (churn was off).  
4. Do **not** treat the segmented ADR as “Design v3 chose segmented CSR+CSC universally” — Report 21 retains it only for localized mutations.  
5. Do **not** reopen map schema nesting to chase cold→hot performance.

---

## 8. Suggested reading order for cold engineers

| Order | Doc | Why |
| ----: | --- | --- |
| 1 | **This brief** | Shared picture and boundaries |
| 2 | [Report 10](./10-design-v3-comprehensive.md) | What changed from Report 02 and full analysis |
| 3 | [Report 07](./07-design-v3-stage3_5-fair.md) | Fair layout + hash_bi (fixes Stage 3 confound) |
| 4 | [Report 09](./09-design-v3-stage4_2-screen.md) | Workload screen and crossover list |
| 5 | [Architecture Decision Record](./Map_Vortex_Graph_Architecture_Decision_Record.md) | Next hypothesis to implement/bench |
| Optional | [Report 02](./02-map-load-adjacency.md) | Original cold→hot motivation |

Program contracts and exit gates: [`../design-v3/`](../design-v3/). Bench code and scripts: [`../map-vortex-bench/`](../map-vortex-bench/).

---

## 9. Bottom line for the engineering team

Motadata map performance work is about **cold→hot adjacency rebuild and the shape of the hot index**, not about redesigning locked Vortex map columns. Lab evidence through Milestone A supports **clustered publish**, **sort-aware build**, and a **mode-based** hot index: serve baseline **`csr_csc`**; recovery-speed reference **`hash`**. Milestone B measured segmented CSR+CSC under an approved synthetic mutation envelope: it is a **conditional** candidate for localized mutation publish windows, not a universal replacement, and not yet validated against measured Motadata churn.
