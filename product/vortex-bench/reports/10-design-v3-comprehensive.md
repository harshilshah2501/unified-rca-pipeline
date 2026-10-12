# Report 10 — Design v3 comprehensive: what changed from Report 02, and what the staged results say

- **Audience:** teammates who may only remember Report 02 (map cold→hot) or the guided analysis companion, and need one place that explains Design v3 end-to-end.
- **Shareable eng brief (prefer for cold readers):** [Report 11](./11-map-vortex-engineering-brief.md)
- **Scope:** Motadata Pillar B **map** Vortex path only (not sketch layout Report 01).
- **Status:** Synthetic lab evidence through Stage **4.2**. This is **not** a Motadata production architecture lock.
- **Companion stage reports:** [04](./04-design-v3-stage1-reproduce.md) · [05](./05-design-v3-stage2-screen.md) · [06](./06-design-v3-stage3-layouts.md) · [07](./07-design-v3-stage3_5-fair.md) · [08](./08-design-v3-stage4_1-properties.md) · [09](./09-design-v3-stage4_2-screen.md)
- **Contracts / program:** [`../design-v3/`](../design-v3/) · Stage 4 families/workloads under [`../design-v3/stage4/`](../design-v3/stage4/)

---

## 1. Plain-language framing

Motadata map product does **not** open Vortex once per Scope hop. Cold `.vortex` parts are loaded, a **hot adjacency index** is rebuilt, and Scope walks that index. Report 02 established that **adjacency build dominates** decode and first BFS, and that **clustered edge publish** helps rebuild.

Design v3 did not restart that question. It asked: *under what experimental controls, layouts, and synthetic workloads does that picture hold or break — and where do layout crossovers appear?*

Throughout this document:

| Term | Meaning here |
| ---- | ------------ |
| **Cold→hot** | Decode Vortex map parts → build in-memory adjacency → first walk |
| **Hash** | Forward-only `HashMap` from source → typed neighbors; reverse = scan all out-lists |
| **hash_bi** | Forward + reverse HashMaps (bidirectional hash) |
| **CSR** | Packed forward compressed sparse row; reverse = scan all arcs |
| **CSR+CSC** (`csr_csc`) | Forward CSR plus reverse compressed sparse column |
| **Hybrid** | CSR+CSC base plus a mutable occurrence-count delta (inserts/deletes) |
| **Spine** | Decode only columns needed for walk rebuild (`source_id`, `target_id`, `edge_type`, …) |
| **Clustered vs natural** | Publish edge row order: sorted by source→type→target vs generation order |
| **Estate family** | Synthetic graph shape (uniform, hubby, power-law, hierarchical, community, layered) |
| **Workload profile** | Controlled mix of forward / reverse / dependency-chain queries (experimental scenario, not Motadata production mix) |

---

## 2. What “v2” was vs what Design v3 changed

In this program, **“v2”** means the **Report 02 / follow-up** era: useful map cold→hot measurements, but not yet a staged factor program with fair layout compare and workload-informed estates. Design v3 is the staged remediation and extension of that era.

### 2.1 What Report 02 already got right (kept in v3)

1. Map problem is **cold→hot rebuild**, not nested schema redesign.
2. **Adjacency build ≫ decode ≫ first BFS** on the measured path.
3. **Clustered publish** shrinks rebuild time vs natural order.
4. **Spine load** is the right default hygiene even when absolute decode wins are modest (map columns are already thin).
5. Schema stays locked; experiments change **physical packing and hot index**, not Motadata columns.

### 2.2 What Report 02 / early Stage 3 left open (why v3 exists)

| Gap in the v2-era evidence | How Design v3 addressed it |
| ------------------------- | -------------------------- |
| Confounded comparisons (e.g. natural+naive vs clustered+sort_aware treated as one “win”) | Stage 1 full **2×2** order × builder ([Report 04](./04-design-v3-stage1-reproduce.md)) |
| Factor importance not ranked under one protocol | Stage 2 screening + query JSONL ([Report 05](./05-design-v3-stage2-screen.md)) |
| Layout compare without `hash_bi`; CSR “win” partially from **unequal reverse** in the mix | Stage 3.5 fair reverse for every layout + per-class latency ([Report 07](./07-design-v3-stage3_5-fair.md)) |
| Aggregate query p95 used as if it were architecture evidence | Explicit warning; use **per-class** forward / reverse / dependency_chain |
| Only uniform + hubby synthetic shapes | Stage 4.0–4.1 six estate families with **property gates** ([Report 08](./08-design-v3-stage4_1-properties.md)) |
| No controlled query-mix regimes; traces not identical across layouts | Stage 4.2 three workload profiles + **identical trace replay** ([Report 09](./09-design-v3-stage4_2-screen.md)) |
| No steady-state index byte estimate vs peak RSS | Stage 4.2 reports both `peak_rss` and estimated retained index bytes |
| Hybrid delete semantics unclear | Documented as **occurrence-count** deletes, not `edge_id` wipe |

### 2.3 Method changes at a glance

```text
Report 02 era                          Design v3
─────────────────                      ─────────────────────────────
Ad-hoc scale sweeps                    Staged gates 0 → 4.2
Hash adjacency focus                   hash · hash_bi · csr · csr_csc · hybrid
Uniform (+ hubby follow-up)            Six property-validated families
Implicit / unequal query mixes         Equal reverse mix (3.5) then
                                       profiled traces (4.2)
Build + RSS emphasis                   + per-class latency + index bytes
“Looks good → recommend” risk          Explicit crossover candidates,
                                       not production lock
```

### 2.4 What Design v3 deliberately did **not** claim

- Motadata production topology or real customer query mix.
- Disk-cold / remote-cold (object-store) path — cells remain `process_cold`.
- Concurrency stress, mutation economics at product churn rates, or 10M+ edges.
- Stage 4.3–4.6 confirmation batches (p99 lock).
- A single winning hot layout for all product modes.

---

## 3. Stage-by-stage results (detailed)

### 3.1 Stage 1 — Order × builder is a real interaction ([Report 04](./04-design-v3-stage1-reproduce.md))

At 500k edges, mean out-degree 5, spine, N=20:

- **Clustered order** cuts build ~**35%** vs natural on both uniform and hubby (naive builder).
- **Sort-aware** helps on **clustered** (~6–8%); on **natural** it can be neutral or worse (uniform) because the builder assumes locality that is not there.
- Best lab cell: **clustered + sort-aware**.

**Carry-forward:** never market “sort-aware” without saying the publish order. Primary Design v3 path is clustered + sort-aware.

### 3.2 Stage 2 — What actually moves the needle ([Report 05](./05-design-v3-stage2-screen.md))

Ranked effects under hash layout:

1. **Edge order** — still largest (often ~40% build at 500k–1M).
2. **Builder × order** — positive on clustered only.
3. **Load mode** — decode share of cold→walk stays small; adjacency dominates.
4. **Shape × query tails** — reverse blast on forward-only hash is expensive (p95 hundreds of ms); degree-bin seeds matter.

**Carry-forward:** Stage 3 must compare layouts with reverse in the mix; Stage 4 must vary estate structure and query regime explicitly.

### 3.3 Stage 3 — Layout Pareto, then the confound ([Report 06](./06-design-v3-stage3-layouts.md))

Stage 3 showed:

- **Hash** wins **build** (often ~2–3× faster than CSR family).
- **CSR / CSR+CSC** collapse **aggregate** query p95 into sub-ms–low-ms territory.
- Hybrid tracks CSR+CSC with a mutation delta.

**Critical flaw (caught in review):** CSR cells did not always pay for reverse the same way hash did, and **`hash_bi` was missing**. Aggregate query p95 therefore overstated CSR’s “architecture win.”

Do **not** use Report 06 aggregate p95 alone for layout selection. Prefer Report 07 / 09 per-class numbers.

### 3.4 Stage 3.5 — Fair reverse fixes the story ([Report 07](./07-design-v3-stage3_5-fair.md))

With the **same** forward + dependency_chain + reverse mix on every layout (500k clustered excerpt):

| Shape | Layout | Build ms | Forward p95 ms | Reverse p95 ms |
| ----- | ------ | -------: | -------------: | -------------: |
| uniform | hash | **181** | 0.23 | **334** |
| uniform | hash_bi | 424 | 0.07 | **0.09** |
| uniform | csr | 370 | 0.14 | **55** |
| uniform | csr_csc | 479 | 0.05 | **0.06** |
| hubby | hash | **146** | 0.08 | **287** |
| hubby | hash_bi | 331 | 0.007 | **0.07** |
| hubby | csr_csc | 507 | 0.01 | **0.07** |

Interpretation that superseded Stage 3’s aggregate narrative:

1. **CSR alone is not a reverse solution** (tens of ms reverse p95 when forced to scan).
2. **`hash_bi` matches CSR+CSC reverse** at lower build than CSR+CSC in these cells.
3. **Forward-only Scope** can still prefer **hash** (fastest rebuild).
4. Hybrid remains a **mutation** candidate, not required for read-mostly publish cycles.

### 3.5 Stage 4.1 — Estates are characterized, not assumed ([Report 08](./08-design-v3-stage4_1-properties.md))

All six families passed property gates at 500k, 1M, and 5M (mean out-degree target 5). Headline structural fingerprints:

| Family | What it stresses | Example 1M signal |
| ------ | ---------------- | ----------------- |
| uniform | Flat degrees | top1% source edge share ~0.024 |
| hubby | Motadata-like hub skew | top1% share ~0.47; max out hundreds |
| power_law | Heavy-tailed sources | max out thousands; p99 ≫ mean |
| hierarchical | Layered PART_OF/RUNS_ON skeleton | few weak components |
| community | 32 communities, ~90% intra | dense local neighborhoods |
| layered | Infra→app directed deps | low reciprocity |

**Carry-forward:** Stage 4.2 timing is only meaningful after these gates. Generators are **modeling assumptions**, not Motadata customer graphs.

### 3.6 Stage 4.2 — Workload-informed layout screen ([Report 09](./09-design-v3-stage4_2-screen.md))

**Protocol**

- Identical JSONL query traces per `(family, scale, profile)` replayed on every layout.
- Profiles: forward-dominant 90/5/5 · balanced 45/45/10 · reverse-heavy 20/70/10 (experimental).
- Layouts: hash, hash_bi, csr, csr_csc, hybrid (hybrid **churn off** for this screen).
- Coverage: full factorial at **500k** and **1M**; thin **5M** ladder (`uniform`/`hubby` × balanced × five layouts). Remaining 5M cells skipped for wall-clock, not because of OOM.

**Hubby × balanced — scale ladder (build / reverse p95 / steady index bytes)**

| Scale | Layout | Build ms | Reverse p95 ms | Steady index B |
| ----: | ------ | -------: | -------------: | -------------: |
| 500k | hash | 142 | **244** | 62M |
| 500k | hash_bi | 309 | **0.038** | 111M |
| 500k | csr | 272 | 37 | 29M |
| 500k | csr_csc | 450 | **0.043** | **48M** |
| 500k | hybrid | 456 | 0.051 | 48M |
| 1M | hash | 407 | **706** | 127M |
| 1M | hash_bi | 924 | **0.057** | 225M |
| 1M | csr_csc | 1357 | **0.063** | **96M** |
| 5M | hash | 2909 | **3961** | 636M |
| 5M | hash_bi | 6876 | **0.051** | 1127M |
| 5M | csr_csc | 10578 | **0.030** | **510M** |

Reading that table in words:

- Forward-only **hash** stays the **fastest rebuild**, but reverse p95 grows into **seconds** by 5M under a balanced reverse share.
- **hash_bi** keeps reverse in the **sub-millisecond** class across 500k→5M, at roughly **2×** hash build and roughly **2×** CSR+CSC retained index bytes.
- **csr_csc** matches hash_bi reverse, usually with **~half the steady index** of hash_bi, but **slower build** (especially at 5M).
- **csr** without CSC is a middle trap: better reverse than hash, far worse than hash_bi/csr_csc, not a destination layout if reverse matters.

**Workload regime matters (same estate, different profile)**

On 500k hubby clustered:

| Profile | hash reverse p95 | hash_bi reverse p95 | csr_csc reverse p95 | Who “wins” if you only watch reverse |
| ------- | ---------------: | ------------------: | ------------------: | ------------------------------------ |
| forward_dominant | 233 ms | 0.13 ms | 0.06 ms | hash_bi ≈ csr_csc; hash rebuild still attractive if reverse share is tiny |
| balanced | 244 ms | 0.04 ms | 0.04 ms | bidirectional index required |
| reverse_heavy | 177 ms | 0.08 ms | 0.04 ms | csr_csc slightly tighter reverse; hash_bi still adequate |

Illustrative break-even sweeps in Report 09 (using class p50 as a stand-in for mean) show **hash** cheaper only while reverse share stays near zero; once reverse becomes material, **hash_bi** (or csr_csc) dominates the mixed cost. Those sweeps are labeled illustrative — not Motadata Qr estimates.

**Estate family sensitivity**

Across community / hierarchical / layered / power_law / uniform at 1M, automated crossover flags repeatedly show:

1. **`csr_csc` undercuts `hash_bi` on steady index** (~2× smaller retained estimate).
2. **`csr_csc` often slightly beats `hash_bi` on reverse p95** (same order of magnitude — both “fast reverse”).
3. On **forward_dominant**, **hash** still wins **build** with competitive forward tails — reinforcing Stage 3.5’s forward-only baseline.

Hubby and power_law do **not** invent a new ranking; they amplify reverse pain on forward-only hash (hub scans, heavy-tailed seeds).

**Natural-order control (500k)**

Natural publish remains slower to rebuild than clustered for the same layout family (consistent with Stages 1–2). It does not flip hash_bi vs csr_csc reverse competitiveness in the screened cells.

**Correctness**

Screened cells report `correctness_ok` against forward checksum vs hash (zero hybrid churn). That checks walk equivalence under the fair algorithms, not Motadata semantic completeness.

---

## 4. Synthesis — architectural envelope (still not a lock)

Think in **product modes**, not one global winner:

| If the product mode is… | Synthetic envelope says… | Why |
| ----------------------- | ------------------------ | --- |
| Restart/failover rebuild latency first; Scope mostly forward after index exists | Prefer **clustered + sort-aware + hash** | Fastest build; reverse unused or rare |
| Reverse / blast-radius walks are common | Need **hash_bi or CSR+CSC** — not forward-only hash, not CSR alone | Reverse p95 otherwise hundreds–thousands of ms at M-edge scale |
| Memory / retained index pressure dominates after build | Lean **CSR+CSC** over hash_bi | ~half steady index bytes in Stage 4.2 estimates |
| Mutating hot graph without full rebuild | **Hybrid** is a candidate | Tracks csr_csc query; Stage 4.2 did **not** measure churn economics |
| Unknown Motadata production mix | Do **not** lock | Need real estates + traces (deferred Stages 4.3+) |

### 4.1 Stable findings across v2 → v3

1. Clustered publish + sort-aware builder remain the cold packing defaults.
2. Adjacency rebuild dominates Vortex decode on this bench.
3. Forward walks are cheap once the index exists; reverse on forward-only hash is not.
4. Synthetic hub skew changes magnitudes more than rankings.

### 4.2 Findings that are new or corrected in v3

1. **hash_bi is the missing Stage 3 control** — equal reverse without packed CSC.
2. Stage 3 aggregate CSR “win” was partly a **measurement confound**.
3. Under identical traces, **csr_csc vs hash_bi** is primarily an **index-memory / build-time** trade, not a reverse-latency cliff.
4. Workload profile (forward vs reverse share) changes which end of that trade you care about.
5. Six estate families all validate; none overturned the layout envelope at ≤5M in this screen.

### 4.3 Explicit non-recommendation

Do **not** ship Motadata GraphWriter architecture from this report alone. Design v3 Stages 0–4.2 map the **performance envelope** on controlled synthetics. Production lock still needs real estates, concurrency, mutation economics, colder load labels, and confirmation sampling.

---

## 5. Artifact map (where to dig)

| Need | Open |
| ---- | ---- |
| Original map cold→hot narrative | [Report 02](./02-map-load-adjacency.md) |
| Sketch vs map Dest comparison | [Report 03](./03-comparative-analysis.md) |
| Order × builder factorial | [Report 04](./04-design-v3-stage1-reproduce.md) |
| Factor ranking + reverse pain on hash | [Report 05](./05-design-v3-stage2-screen.md) |
| Early layout Pareto (use with caution) | [Report 06](./06-design-v3-stage3-layouts.md) |
| Fair layout + hash_bi | [Report 07](./07-design-v3-stage3_5-fair.md) |
| Estate property tables | [Report 08](./08-design-v3-stage4_1-properties.md) |
| Workload screen + crossovers + Qr sweeps | [Report 09](./09-design-v3-stage4_2-screen.md) |
| Contracts / gates | [`../design-v3/gates.md`](../design-v3/gates.md) · [`../design-v3/stage4/`](../design-v3/stage4/) |
| Bench + scripts | [`../map-vortex-bench/`](../map-vortex-bench/) · `scripts/stage4_*.sh` |

Raw Stage 4.2 cells: `map-vortex-bench/out/design-v3/stage4/screen/`.

---

## 6. Deferred next work (named, not invented)

1. **Stage 4.3–4.6** — confirmation batches, p99, broader 5M/10M if memory allows.
2. **Real Motadata estates / traces** — replace synthetic profiles.
3. **Mutation / lifecycle economics** — hybrid under realistic churn (Stage 4.2 churn was off).
4. **Concurrency** — multi-reader / rebuild overlap.
5. **Disk-cold / remote-cold** — drop page cache / object-store path labels.
6. **Adaptive selector** — only after the above; not justified yet.

Related **architecture hypothesis** (not measured in Stages 4.0–4.2): segmented CSR+CSC with incremental copy-on-write publish — see [`Map_Vortex_Graph_Architecture_Decision_Record.md`](./Map_Vortex_Graph_Architecture_Decision_Record.md). That ADR must not be read as a Design v3 layout winner; it is the next candidate to benchmark on lifecycle metrics against the envelope above.

**Degree-bin convention used in Stage 4.2 traces:** out-degree percentiles among sources with at least one edge (`p10` / `p50` / `p90`); reverse-heavy profiles also include the max-degree hub.

---

## 7. One-paragraph bottom line

Report 02 correctly identified Motadata map’s cold→hot bottleneck and the value of clustered publish. Design v3 kept that core, then **unconfounded** builder×order, **fairly** compared hot layouts (adding `hash_bi` and per-class reverse), and **screened** six synthetic estates under three workload profiles with identical traces. The synthetic envelope is: **hash** for rebuild-first / forward-heavy modes; **hash_bi or CSR+CSC** when reverse matters; **CSR+CSC** preferred when retained index memory matters; **CSR alone** and **aggregate Stage 3 p95** are not architecture evidence. Nothing here is a Motadata production lock.
