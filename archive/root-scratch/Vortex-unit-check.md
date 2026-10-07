Yes. This is the right next problem. We have spent a lot of time defining the **logical RCA contract**; now we should deliberately design its **physical Vortex representation**.

And the table in your screenshot gives us the crucial distinction:

> **Zone optimizes elimination. Flat chunk/segment determines the actual decode cost. Buffered run optimizes physical I/O.**

So I would not start by asking, “What schema looks clean?” I would start with:

> **For each RCA query, what is the smallest set of bytes Vortex must fetch and decode to answer it?**

### Apply that to our `sketch.v2`

Our logical object currently looks roughly like:

```text
Sketch
├── tenant
├── entity_id
├── metric_id
├── window_start / window_end
├── season_key
├── sample_count
│
├── tdigest
│   ├── compression
│   ├── encoding
│   └── data
│
├── buckets
│   ├── schema_version
│   ├── bounds[]
│   └── counts[]
│
├── baseline
│   ├── expected_p50
│   ├── expected_p95
│   └── expected_p99
│
├── anomaly
│
└── exemplars[]
    ├── bucket_index
    ├── value
    ├── timestamp
    ├── trace_id
    ├── span_id
    └── selection_hint
```

That's a good **logical contract**.

But storing this literally as a deeply nested physical structure is probably not what we want.

Consider the first RCA query:

```sql
WHERE tenant = ?
  AND entity_id = 'checkout-api'
  AND window_start BETWEEN ...
  AND anomaly = true
```

At this stage RCA needs perhaps:

```text
entity_id
metric_id
window
anomaly
baseline
maybe p95/p99
```

It does **not** yet need:

```text
T-Digest bytes
bucket arrays
exemplar trace IDs
span IDs
selection hints
```

Only after narrowing down to:

```text
checkout-api
request.latency_ms
10:00–10:05
```

do we need the distribution evidence.

And only after identifying:

```text
(500,1000] looks suspicious
```

do we need an exemplar.

So our physical access pattern is naturally staged:

```text
STAGE 1
Locate suspicious sketches
        ↓
cheap columns

STAGE 2
Understand distribution
        ↓
T-Digest / buckets

STAGE 3
Find concrete evidence
        ↓
exemplars

STAGE 4
trace_id
        ↓
Trace Store
```

That immediately suggests an important Vortex design principle:

> **Don't make Stage 1 decode Stage 3 data.**

### I would investigate a “hot spine + cold evidence” physical layout

Conceptually:

```text
                    SKETCH ROW

        HOT / frequently queried spine
┌─────────────────────────────────────────┐
│ tenant                                  │
│ entity_id                               │
│ metric_id                               │
│ window_start                            │
│ window_end                              │
│ anomaly                                 │
│ sample_count                            │
│ current_p50                             │
│ current_p95                             │
│ current_p99                             │
│ expected_p50                            │
│ expected_p95                            │
│ expected_p99                            │
└─────────────────────────────────────────┘
                    │
             RCA narrows rows
                    ▼

       DISTRIBUTION EVIDENCE
┌─────────────────────────────────────────┐
│ tdigest_data                            │
│ bucket_schema_id                        │
│ bucket_counts[]                         │
└─────────────────────────────────────────┘
                    │
             suspicious tail
                    ▼

        CONCRETE EVIDENCE
┌─────────────────────────────────────────┐
│ exemplar_bucket_index[]                 │
│ exemplar_value[]                        │
│ exemplar_timestamp[]                    │
│ exemplar_trace_id[]                     │
│ exemplar_span_id[]                      │
│ exemplar_reason[]                       │
│ exemplar_confidence[]                   │
└─────────────────────────────────────────┘
```

Notice something else: I would seriously question whether `bounds[]` belongs in every sketch row.

If:

```text
bucket_schema_version = latency_v1
```

already deterministically means:

```text
[0,50,100,200,500,1000,2000]
```

then repeating those bounds for millions of rows is logically convenient but physically redundant.

We could instead have:

```text
bucket_schema_id = 7
```

with a catalog:

```text
7 → latency_v1
    [0,50,100,200,500,1000,2000]
```

Then each sketch only stores:

```text
bucket_schema_id
bucket_counts
```

That's exactly the kind of distinction we now need to explore:

```text
Logical schema
     ≠
Physical Vortex representation
```

### And the ~2 MB flat-chunk point changes how we should think

Suppose one physical column segment contains approximately 2 MB uncompressed.

The relevant question is no longer merely:

> “How many sketch rows fit in a Vortex file?”

Instead:

> “How many sketch rows fit inside one decodable segment **for each column**, and which columns are decoded together during our dominant RCA queries?”

For example, imagine 100,000 sketch rows.

A query might initially need only:

```text
entity_id
metric_id
window_start
anomaly
p95
expected_p95
```

If those columns prune well and decode cheaply, excellent.

But if `exemplars` is represented in a way that causes large nested structures or variable binary blobs to be fetched/decoded alongside that path, we have undermined Vortex's advantage.

### There are really three optimization layers

Your screenshot captures them nicely:

```text
                 QUERY
                   │
                   ▼
              ZONE PRUNING
       "Do I need these rows?"
                   │
              surviving zones
                   ▼
             FLAT CHUNKS
      "What must I actually decode?"
                   │
             required chunks
                   ▼
            BUFFERED RUNS
    "Which adjacent chunks should I
          fetch in one I/O?"
```

So our physical design has **three independent objectives**:

**1. Zone locality**

Rows likely to be queried together should be clustered so zone statistics become useful.

Potential ordering:

```text
tenant
 → entity_id
 → metric_id
 → window_start
```

But we shouldn't freeze that yet; it depends heavily on actual RCA predicates.

**2. Decode locality**

Frequently co-accessed fields should have compatible chunk boundaries and avoid dragging cold evidence into the decode path.

This is where:

```text
hot spine
distribution evidence
exemplar evidence
```

becomes interesting.

**3. I/O locality**

Columns commonly needed together should land in useful buffered runs so the storage layer can fetch them efficiently.

That is a different problem from logical nesting.

---

## I think we should design this experimentally

We already have something extremely useful for doing it: the NYC taxi Parquet dataset available in this project.

Instead of arguing theoretically about the best Vortex layout, I'd suggest we construct a **synthetic RCA sketch workload** resembling our real schema:

```text
1M+ sketch rows

tenant
entity_id
metric_id
window
anomaly
RED dimension
percentiles
baseline
tdigest blob
bucket counts
0..8 exemplars
trace/span IDs
selection hints
```

Then test competing physical layouts:

```text
A. Natural nested sketch.v2
B. Fully flattened
C. Hot spine + nested cold evidence
D. Hot spine + flattened exemplar columns
E. Split logical evidence tables
```

against actual RCA queries such as:

```text
Q1 Find anomalous metrics for entity/time
Q2 RED Duration drill-down
Q3 Read p95/p99 + baseline
Q4 Open bucket distribution
Q5 Retrieve exemplar for suspicious bucket
Q6 Read trace_id/span_id
Q7 Scan anomalies across many entities
Q8 Historical baseline comparison
```

Then measure:

```text
bytes fetched
      ↓
zones eliminated
      ↓
flat chunks touched
      ↓
bytes decoded
      ↓
decode time
      ↓
query latency
```

That will tell us something much more valuable than “nested versus flat”:

> **the optimal physical schema for our actual RCA access pattern.**

And I suspect we'll discover that the best representation is neither fully nested nor blindly flattened, but a **hot, narrow RCA index/spine with progressively colder distribution and execution-evidence columns**.

That would also fit beautifully with the architecture we've already developed:

```text
Graph
  ↓
RED/KPI
  ↓
HOT SPINE                  ← very cheap
  ↓
Distribution Sketch        ← decode on demand
  ↓
Exemplar                   ← decode later
  ↓
Trace Store                ← separate substrate
  ↓
Raw Evidence               ← expensive last resort
```

This is where our Vortex learning and RCA design finally intersect.

---

## Experiment harness (landed)

Program home: [`pillar-ab-implementation/vortex-bench/`](pillar-ab-implementation/vortex-bench/)

| Bench | Path | Report |
|-------|------|--------|
| Sketch layouts A–E × Q1–Q8 | [`vortex-bench/sketch-vortex-bench/`](pillar-ab-implementation/vortex-bench/sketch-vortex-bench/) | [`reports/01-sketch-physical-layout.md`](pillar-ab-implementation/vortex-bench/reports/01-sketch-physical-layout.md) |
| Map load + adjacency | [`vortex-bench/map-vortex-bench/`](pillar-ab-implementation/vortex-bench/map-vortex-bench/) | [`reports/02-map-load-adjacency.md`](pillar-ab-implementation/vortex-bench/reports/02-map-load-adjacency.md) |
| Comparative analysis | — | [`reports/03-comparative-analysis.md`](pillar-ab-implementation/vortex-bench/reports/03-comparative-analysis.md) |

The sketch harness builds synthetic sketch.v2-shaped rows and writes five physical layouts, then times **column-projected** Vortex decode for Q1–Q8.

| Layout id | What it is |
|-----------|------------|
| `A_nested` | Nested `tdigest` / `buckets` / `exemplars` structs |
| `B_flat_wide` | Flat wide table; Stage‑1 deliberately projects `*` |
| `C_spine_nested_cold` | Flat spine + nested `cold_evidence` |
| `D_spine_flat_evidence` | Flat spine + flat distribution/exemplar columns; staged projections |
| `E_split_tables` | Separate spine / distribution / exemplars files |

```bash
cd pillar-ab-implementation/vortex-bench/sketch-vortex-bench
cargo run --release --bin sketch_vortex_bench -- \
  --rows 100000 --sort clustered --out out/run-100k-clustered
# scale: --rows 1000000 --out out/run-1m-clustered

cd ../map-vortex-bench
cargo run --release --bin map_vortex_bench -- \
  --nodes 20000 --edges 100000 --edge-sort clustered \
  --out out/run-100k-edges-clustered
```

### First 100k clustered sketch result (`--release`, median of 3 after 1 warmup)

Stage‑1 decode_ms (Q1 / Q2 / Q7) — lower is better. Full JSON: `vortex-bench/sketch-vortex-bench/out/run-100k-clustered/results.json`.

| Layout | Total bytes | Q1 | Q2 | Q7 |
|--------|-------------|----|----|----|
| `A_nested` | 4.6 MB | 3.2 | 3.0 | 2.2 |
| `B_flat_wide` (`*` on Stage‑1) | 4.9 MB | **20.8** | **21.0** | **32.6** |
| `C_spine_nested_cold` | 4.0 MB | 4.0 | 4.0 | 2.9 |
| `D_spine_flat_evidence` | 4.0 MB | 4.4 | 4.1 | 2.9 |
| `E_split_tables` | 4.0 MB | 3.8 | 4.6 | 2.1 |

**Early read:**

1. Naive wide Stage‑1 (`B` + `*`) is ~5–10× slower — it forces decode of T‑Digest + exemplar columns before RCA has narrowed rows.
2. **`A` / `D` / `E`** are in the same Stage‑1 band when projections stay on spine fields (column pruning works).
3. **`E_split_tables`** is close on Stage‑1 (opens only `spine.vortex`) but Stage‑3 still opens the whole exemplars file today (no row-id prune yet) — file split alone is not enough without selective row fetch.
4. **`C`** pays on Stage‑2/3 when projecting `cold_evidence` (whole nested bundle). Prefer flat evidence columns (`D`) for progressive decode.
5. Nesting (`A`) is fine for spine-only stages; treat nested groups as “decode the whole child,” not field-granular cold access.

**Not yet measured:** Vortex zone filter pushdown (`entity_id` / `anomaly` / window) under `natural` vs `clustered` sort; bytes-fetched from object storage (this run is local buffer open + decode time); 1M-row scale.

**Working conclusion (provisional):** keep the logical sketch.v2 contract nested for humans; physically prefer **flat hot spine + flat on-demand evidence columns** (`D`), with optional Dest split (`E`) only after row-selective cold reads exist. Do not default Stage‑1 to `select *`.

### Map bench (summary)

At 500k edges, cold→walk total is dominated by **adjacency build** (~80 ms), not BFS (≪1 ms). Spine projection trims decode modestly; clustering edges at publish shrinks edge parts (~26% at 100k). Keep the locked flat map schema — see Report 02 and the comparative analysis (Report 03).
