# Report 01 — Sketch Vortex physical layout

- **Bench:** [`../sketch-vortex-bench/`](../sketch-vortex-bench/)
- **Room:** Motadata `history/` (Pillar A sketches)
- **Status:** Experiment results (not a Signed product freeze)
- **Primary result artifact:** `sketch-vortex-bench/out/run-100k-clustered/results.json`
- **Framing:** [`Vortex-unit-check.md`](../../../Vortex-unit-check.md) (zone ≈ prune, flat chunk ≈ decode, buffered run ≈ I/O)

---

## 1. Objective — why physical layout for sketches?

### Why we are talking about this

Pillar A’s product story for a sketch row is already clear: one window carries a **T‑Digest** (percentiles), **explicit buckets** (where mass sat), a **seasonal baseline** (was this abnormal?), and optional **exemplars** (which `trace_id` to open next). That is a good **logical** contract for humans and for Detect / investigate.

Vortex does not read “the sketch object.” It prunes **zones**, then **decodes flat column chunks**. If the physical file stores digest bytes and exemplar lists beside the fields Stage‑1 needs (`entity_id`, `anomaly`, `current_p95`, …), a naive or over-wide projection forces the engine to pay Stage‑3 cost while RCA is still only asking “which windows look bad?”

So this report is not about inventing a new Detect algorithm. It is about **whether the Motadata `history/` Vortex shape matches the staged RCA read path**.

### What we are trying to achieve

1. **Protect Stage‑1.** Locating anomalous sketch windows must stay cheap even at large row counts.
2. **Pay for evidence on demand.** Bucket arrays and exemplars should decode only after a candidate window is chosen.
3. **Separate logical nesting from physical columns.** Keep a nested sketch.v2 narrative if useful for docs/APIs, but choose a physical layout that Vortex can project narrowly.
4. **Give Retrieval / SketchWriter a freeze candidate** (for example hot spine + flat evidence columns) backed by numbers, not aesthetics.

### Success looks like

Stage‑1 queries that project only spine columns are several times faster than Stage‑1 `select *` over the same estate; Stage‑2/3 can still reach distribution and exemplars without redefining the logical evidence ladder.

---

## 2. Experiment question

For staged RCA reads over sketch.v2-shaped rows:

```text
Stage 1  locate anomalous windows (identity, anomaly, percentiles, baseline)
Stage 2  open distribution (T-Digest / bucket counts)
Stage 3  open exemplars (trace_id / span_id)
```

**what physical Vortex column shape minimizes Stage‑1 decode cost**, given Vortex’s default Struct → Zoned (8k rows) → Chunked (~2 MB uncompressed / column) → Buffered (~1 MB compressed) → Flat strategy?

---

## 3. Method

### 3.1 Synthetic workload

| Knob | Value (primary run) |
|------|---------------------|
| Rows | 100,000 |
| Entities | 256 |
| Metrics | 4 latency-like names |
| Anomaly rate | ~8% |
| T-Digest payload | 512 bytes / row |
| Bucket counts | 8 bins; bounds catalog id `7` |
| Exemplars | 0–4 per row when anomalous / sampled |
| Row sort | `clustered` = tenant → entity_id → metric_id → window_start |

### 3.2 Layouts under test

| Id | Physical shape | Stage‑1 projection discipline |
|----|----------------|-------------------------------|
| `A_nested` | Nested structs `tdigest`, `buckets`, `exemplars` | Spine fields only |
| `B_flat_wide` | Fully flat, includes repeated `bucket_bounds` | **Naive `*`** on Stage‑1 |
| `C_spine_nested_cold` | Flat spine + nested `cold_evidence` | Spine only until Stage‑2/3 |
| `D_spine_flat_evidence` | Flat spine + flat distribution/exemplar columns | Staged column lists |
| `E_split_tables` | `spine.vortex` + `distribution.vortex` + `exemplars.vortex` | Stage‑1 opens spine file only |

### 3.3 Queries

Q1–Q8 as listed in the bench README (Stage‑1: Q1,Q2,Q3,Q7,Q8; Stage‑2: Q4; Stage‑3: Q5,Q6).

### 3.4 Metrics

- Total Vortex bytes written
- Median decode_ms after 1 warmup + 3 timed repeats (`--release`)
- Rows decoded (full scan with column projection; filter applied post-decode for match counts)
- **Not yet:** zone filter pushdown, object-store bytes fetched, 1M-row scale

---

## 4. Results (100k clustered, `--release`)

### 4.1 File size

| Layout | Total bytes |
|--------|-------------|
| `A_nested` | 4.63 MB |
| `B_flat_wide` | 4.92 MB |
| `C_spine_nested_cold` | 3.95 MB |
| `D_spine_flat_evidence` | 3.95 MB |
| `E_split_tables` | 3.96 MB |

Repeating bounds on every row (`B`) costs space. Nesting vs flat evidence is similar when bounds live in a catalog id.

### 4.2 Stage‑1 decode_ms (Q1 / Q2 / Q7)

| Layout | Q1 | Q2 | Q7 |
|--------|----|----|-----|
| `A_nested` | 3.2 | 3.0 | 2.2 |
| `B_flat_wide` (`*`) | **20.8** | **21.0** | **32.6** |
| `C_spine_nested_cold` | 4.0 | 4.0 | 2.9 |
| `D_spine_flat_evidence` | 4.4 | 4.1 | 2.9 |
| `E_split_tables` | 3.8 | 4.6 | 2.1 |

### 4.3 Later stages (selected)

| Layout | Q4 buckets | Q5 exemplars | Q6 trace ids |
|--------|------------|--------------|--------------|
| `A_nested` | projects whole `buckets` / `exemplars` groups | same | same |
| `C_spine_nested_cold` | projects whole `cold_evidence` | same | same |
| `D_spine_flat_evidence` | only `bucket_*` columns | only exemplar columns | only trace/span lists |
| `E_split_tables` | opens distribution file (all dist rows today) | opens exemplars file (all rows today) | same |

Exact ms vary by run; the structural point is that **C/A pull nested bundles**, while **D projects narrowly**, and **E** avoids spine contamination but still lacks row-id selective cold fetch.

---

## 5. Interpretation

1. **The failure mode is Stage‑1 `select *`**, not “nesting exists.” `B` is ~5–10× slower on Stage‑1 because T‑Digest and exemplars enter the decode path before RCA has narrowed candidates.
2. When Stage‑1 projects only spine columns, **A / D / E land in the same band**. Vortex column pruning works.
3. **Progressive evidence favors flat cold columns (`D`)** over one nested `cold_evidence` blob (`C`): Stage‑2/3 should not pay for exemplars when only bucket counts are needed.
4. **File split (`E`)** is a useful Dest option for Stage‑1 isolation, but without row-selective reads it still materializes whole cold files at Stage‑2/3. Do not treat split files as a substitute for projection discipline.
5. **Logical sketch.v2 may stay nested for humans**; physical Vortex should expose a **hot spine + on-demand evidence columns**.

---

## 6. Recommendations (sketch / history)

| Decision | Recommendation |
|----------|----------------|
| Product logical contract | Keep nested sketch.v2 narrative (digest + buckets + baseline + optional exemplars) |
| Physical Vortex default candidate | **`D_spine_flat_evidence`** |
| Optional Dest split | Consider `E` after row-selective cold reads exist |
| Catalog | Store `bucket_schema_id`, not per-row `bounds[]` |
| Writer / reader rule | Stage‑1 Retrieval must never default to `select *` |
| Next measurements | Zone pushdown + `natural` vs `clustered` sort; 1M rows; S3 range-get bytes |

---

## 7. How to reproduce

```bash
cd pillar-ab-implementation/vortex-bench/sketch-vortex-bench
cargo run --release --bin sketch_vortex_bench -- \
  --rows 100000 --sort clustered --out out/run-100k-clustered \
  --warmup 1 --repeats 3
```
