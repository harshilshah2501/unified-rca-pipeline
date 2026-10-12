# Motadata map Vortex — engineering brief (cold readers)

**Audience:** engineers who did not sit through Design v3 chats and need a single shareable brief.  
**Date:** 2026-10-12  
**Status:** Lab evidence through Design v3 Stage **4.2** (synthetic). **Not** a Motadata production architecture approval.  
**Owner path in repo:** `product/vortex-bench/`

If you read only one page of map Vortex work, read **this**. Deep dive: [Report 10](./10-design-v3-comprehensive.md). Next architecture hypothesis (unmeasured): [Architecture Decision Record](./Map_Vortex_Graph_Architecture_Decision_Record.md).

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

## 7. What engineering should do / not do this week

### Do

1. Treat **clustered publish + sort-aware + spine load** as the default cold packing path in design docs and prototypes.  
2. When designing Scope features, state whether the path is **forward-only** or **needs reverse**—that choice drives hot index shape more than micro-tuning Vortex nesting.  
3. Use Reports **07 / 09 / 10** when someone quotes old Stage 3 “CSR wins on query p95” aggregate numbers—those aggregates were **confounded**; fair reverse is in Report 07.  
4. If prototyping mutation, measure **mutation-to-visibility**, rebuild cost, peak RSS with two snapshots live, and recovery—not insert microseconds alone.  
5. Keep synthetic profiles labeled as **experimental**, never as Motadata production mix.

### Do not

1. Do **not** announce a production GraphWriter architecture lock from this brief.  
2. Do **not** treat hybrid’s Stage 4.2 numbers as proof of mutation superiority (churn was off).  
3. Do **not** treat the segmented ADR as “Design v3 chose segmented CSR+CSC.” Design v3 chose an **evidence boundary**; the ADR proposes the **next candidate to test**.  
4. Do **not** reopen map schema nesting to chase cold→hot performance.

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

Motadata map performance work is about **cold→hot adjacency rebuild and the shape of the hot index**, not about redesigning locked Vortex map columns. Lab evidence through Stage 4.2 supports **clustered publish**, **sort-aware build**, and a **mode-based** hot index choice: **hash** when rebuild and forward walks dominate; **hash_bi or CSR+CSC** when reverse matters; **CSR+CSC** when retained memory matters. A **segmented, snapshot-published** index is a plausible next architecture for mutation and consistency, but it remains **unproven** until measured against these baselines on lifecycle metrics and real Motadata traces.
