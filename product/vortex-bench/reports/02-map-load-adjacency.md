# Report 02 — Map Vortex cold load and adjacency rebuild

- **Bench:** [`../map-vortex-bench/`](../map-vortex-bench/)
- **Room:** Motadata `map/` (Pillar B topology)
- **Status:** Experiment results (not a schema redesign — columns stay locked)
- **Primary artifacts:** natural vs clustered pairs at five edge counts under `map-vortex-bench/out/run-{100k,250k,500k,750k,1000k}-edges-{natural,clustered}/results.json`, plus rollup `map-vortex-bench/out/sort-scale-sweep-summary.json`
- **Contracts:** [`MAP_VORTEX_COLUMNAR_SCHEMA.md`](../../contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md) · [`MAP_HOT_COLD_LIFECYCLE.md`](../../contracts/MAP_HOT_COLD_LIFECYCLE.md) · [`MAP_SCOPE_WALK_POLICY.md`](../../contracts/MAP_SCOPE_WALK_POLICY.md)

---

## 1. Objective — why load and adjacency for map?

### Why we are talking about this

Pillar B’s Motadata map is already a **locked flat** two-table schema (`map_nodes`, `map_edges`): typed scalars, epoch-ms clocks, closed promoted tags — no nested JSON bag, no T‑Digest, no exemplars. Copying the sketch “nested vs flat vs split evidence” matrix onto map would optimize the wrong problem.

What map product actually does:

1. **`publish_map`** writes immutable cold `.vortex` parts (checkpoint).
2. On process start / failover, GraphWriter **loads those parts** and rebuilds an in-memory **adjacency index**.
3. **E8 Scope (Triage)** walks that hot index from a CaseSeed tip (hop budget, relation profile). It must **not** open S3/Vortex once per neighbor.

So the expensive Motadata path for graph is **cold → hot rebuild**, not “which nested layout looks clean.” This report measures that path.

### What we are trying to achieve

1. **Confirm the lifecycle rule with numbers.** After adjacency exists, a Scope-like BFS should be cheap relative to load/rebuild.
2. **Learn how to load for walks.** Prefer projecting the **spine** columns (defined in §2) instead of always materializing every tag and `evidence_event_id`.
3. **Improve publish packing.** See whether clustering edges by source/type/target shrinks cold parts (Dest cost) even when decode wins are modest.
4. **Avoid a false redesign.** Keep the locked schema; spend engineering on load projection, publish sort, and hot-index reuse.

### Success looks like

We can time the full path **cold start → first walk** as a pipeline of required steps —

```text
cold .vortex open
      → decode columns (Vortex → Arrow)
      → build adjacency index (hot)
      → first BFS / Scope-like walk
```

— and say **which step dominates the clock**, not which step is optional. All three matter for map; the bench only splits time so we know where to optimize (today: adjacency build ≫ decode ≫ BFS). We also show whether a spine-only load helps and whether publish-time edge clustering shrinks parts — without proposing new nested map tables.

---

## 2. Terms a cold reader needs

These words appear throughout the report. They are ordinary English labels for load choices — not Motadata product feature names.

### Spine

**Spine** means the **narrow set of columns you need for the first job** — here, rebuilding a walkable neighborhood — not every column that exists on the row.

On the Motadata map:

| Table | Spine columns (first lookup / walk rebuild) | Deferred until UI or filter needs them |
|-------|-----------------------------------------------|----------------------------------------|
| `map_nodes` | `entity_id`, `type` | `name`, promoted tags (`env`, `region`, `owner`, `namespace`), clocks (`last_seen`, `valid_from`, `valid_to`), `version` |
| `map_edges` | `source_id`, `target_id`, `edge_type` | `edge_id`, `valid_from`, `valid_to`, `evidence_event_id` |

Plain phrase: **spine = columns of the first lookup; everything else = load later if needed.**

That is the same idea as in the sketch bench (identity + cheap signals first; T‑Digest / exemplars later), but map rows are already thin — there is no fat digest blob. “Spine load” on map is still useful as **hygiene and a smaller decode set**, even when absolute millisecond wins are modest.

### Other terms used below

| Term | Meaning in this report |
|------|-------------------------|
| **Cold** | Immutable `.vortex` parts on Dest / disk from `publish_map`. Not used for per-neighbor Scope hops. |
| **Hot** | In-process node/edge Arrays plus an **adjacency index** built after load. Scope walks this. |
| **Adjacency (index)** | Map from each source configuration item to its outgoing neighbors `(target_id, edge_type)`. Built from the **edge spine** columns. |
| **Projection** | Asking Vortex to decode only named columns (not `select *` / all fields). |
| **BFS** | Breadth-first walk from a seed CI for a hop budget — stands in for E8 Scope’s neighborhood walk after the index exists. |
| **Clustered edge sort** | Writing edge rows ordered by `source_id` → `edge_type` → `target_id` so similar values sit together (better compression / prune locality). |

---

## 3. Experiment question

Interactive Scope walks run on **hot** adjacency after cold rebuild — not one Vortex open per neighbor hop. The map experiment therefore asks:

> For locked flat `map_nodes` / `map_edges`, how should we **load cold Vortex parts** and **rebuild adjacency** so restart / failover / analytics stay cheap?

Specifically:

1. Spine-only projection vs full-column materialize (see §2)
2. Edge sort (`natural` vs `clustered` by `source_id → edge_type → target_id`)
3. Along the **cold → first-walk** path, how much time is **decode**, how much is **adjacency build**, and how much is **BFS** — all required; we compare their share of the total

This is **not** a nested-vs-flat layout contest like the sketch report. Map has no T‑Digest or exemplar blobs; the schema stays the locked flat tables.

---

## 4. Method

### 4.1 Synthetic estate

Natural vs clustered is compared at **matched** estates. Seed is always `42`.

**Why `nodes = edges / 5` (average out-degree ≈ 5).** Larger runs should be bigger graphs with the **same density**, so a slowdown can be blamed on more rows—not on “each node suddenly has more neighbors.” The ratio is **average outgoing edges per node** (`edges ÷ nodes`), which is what the **out-adjacency** index cares about. Counting both ends of each directed edge, a typical node is incident to about **10** edge endpoints; this report treats “degree” as **out-degree** unless it says otherwise.

| Edges | Nodes | Mean out-degree | Out dirs (pair) |
| ----- | ----- | --------------- | --------------- |
| 100,000 | 20,000 | ~5 | `run-100k-edges-{natural,clustered}` |
| 250,000 | 50,000 | ~5 | `run-250k-edges-{natural,clustered}` |
| 500,000 | 100,000 | ~5 | `run-500k-edges-{natural,clustered}` |
| 750,000 | 150,000 | ~5 | `run-750k-edges-{natural,clustered}` |
| 1,000,000 | 200,000 | ~5 | `run-1000k-edges-{natural,clustered}` |

| Knob | Value |
| ---- | ----- |
| Node types | service, host, database, queue, runtime, middleware (cycled by a mix hash) |
| Edge types | all fifteen Motadata SCREAMING names (cycled by the same mix) |
| Endpoint sampling | For each edge, source and target are chosen **near-uniformly** over all nodes (`mix(seed, i) % nodes`, self-loops skipped and topped up). **No preferential attachment** — this estate does **not** invent a few hub CIs the way many real customer graphs do. Generator: [`map-vortex-bench/src/synth.rs`](../map-vortex-bench/src/synth.rs) `generate_estate`. |
| Columns | Locked Motadata flat schema (promoted tags + epoch-ms clocks) |
| Edge sort | **Natural** = generation order · **Clustered** = `source_id` → `edge_type` → `target_id` before write |

### 4.2 Load modes

Each mode is a different **projection** choice when opening the cold Vortex files. “Spine” here means the column sets defined in §2.

| Mode | What gets decoded | Plain intent |
|------|-------------------|--------------|
| `full` | All node columns + all edge columns | Naive restart: materialize everything |
| `spine` | Node spine (`entity_id`, `type`) + edge spine (`source_id`, `target_id`, `edge_type`) | Minimum needed to rebuild walks |
| `nodes_full_edges_spine` | All node columns + edge spine only | Keep node tags for UI; still defer edge audit fields |

### 4.3 Hot path after load

1. Build out-adjacency map from the **edge spine** columns (`source_id` → list of `(target_id, edge_type)`)
2. BFS from first generated node, hops = 2 (Scope-like microbench)

### 4.4 Metrics

Median of 3 timed repeats after 1 warmup (`--release`): node decode_ms, edge decode_ms, adjacency build_ms, bfs_ms, total, part bytes.

---

## 5. Results

All timings below are median of 3 timed repeats after 1 warmup (`--release`), load mode **`full`** unless noted. Percentages are **(natural − clustered) / natural** — positive means clustered is smaller or faster.

### 5.1 Natural vs clustered scale sweep (primary)

| Edges | nodes.vortex (same both sorts) | edges.vortex natural | edges.vortex clustered | Edge-part % smaller | Cold→walk natural | Cold→walk clustered | Cold→walk % faster |
| ----- | ------------------------------ | -------------------- | ---------------------- | ------------------- | ----------------- | ------------------- | ------------------ |
| 100k | 378 KB | 1.71 MB | **1.26 MB** | **26.6%** | 22.9 ms | **16.6 ms** | **27.7%** |
| 250k | 944 KB | 4.50 MB | **3.32 MB** | **26.1%** | 61.4 ms | **38.1 ms** | **37.9%** |
| 500k | 1.89 MB | 7.85 MB | **6.84 MB** | **12.9%** | 161.9 ms | **77.2 ms** | **52.3%** |
| 750k | 2.83 MB | 11.41 MB | **10.29 MB** | **9.9%** | 261.0 ms | **136.1 ms** | **47.9%** |
| 1000k | 3.77 MB | 16.55 MB | **14.05 MB** | **15.1%** | 383.4 ms | **175.3 ms** | **54.3%** |

Same sweep with **spine** load (narrower decode; same edge files):

| Edges | Cold→walk natural | Cold→walk clustered | Cold→walk % faster |
| ----- | ----------------- | ------------------- | ------------------ |
| 100k | 21.3 ms | **15.1 ms** | **28.8%** |
| 250k | 76.8 ms | **35.4 ms** | **53.9%** |
| 500k | 166.8 ms | **69.9 ms** | **58.1%** |
| 750k | 284.0 ms | **119.6 ms** | **57.9%** |
| 1000k | 423.7 ms | **162.6 ms** | **61.6%** |

### 5.2 Where the cold→walk win comes from (`full` load)

| Edges | Decode natural | Decode clustered | Adj build natural | Adj build clustered | Adj % faster |
| ----- | -------------- | ---------------- | ----------------- | ------------------- | ------------ |
| 100k | 6.0 ms | 4.6 ms | 16.9 ms | **11.9 ms** | **29%** |
| 250k | 9.9 ms | 10.5 ms | 51.4 ms | **27.6 ms** | **46%** |
| 500k | 17.8 ms | 16.8 ms | 144.1 ms | **60.4 ms** | **58%** |
| 750k | 25.7 ms | 25.7 ms | 235.3 ms | **110.4 ms** | **53%** |
| 1000k | 35.8 ms | 35.4 ms | 347.5 ms | **139.9 ms** | **60%** |

BFS stays under **0.1 ms** at every scale once the index exists.

### 5.3 Load-mode spot check (1000k edges, clustered)

| Load mode | decode (n+e) ms | adj ms | bfs ms | total ms |
| --------- | --------------- | ------ | ------ | -------- |
| `full` | 35.4 | 139.9 | 0.02 | **175.3** |
| `spine` | **26.4** | 136.2 | 0.10 | **162.6** |
| `nodes_full_edges_spine` | 30.2 | 134.4 | 0.11 | 164.7 |

Spine still wins a little on decode; adjacency build stays the dominant term.

---

## 6. Interpretation

1. **Compression gain is real but not a smooth climb with scale.** Edge-part shrink peaks near **26%** at 100k–250k, then sits around **10–15%** at 500k–1000k on this synthetic estate. Still worth clustering for Dest bytes; do not expect “bigger graph ⇒ bigger % compression forever.”
2. **Cold→walk % gain does grow with scale**, roughly **28% → ~50–55%** (`full`) and **29% → ~60%** (`spine`) from 100k to 1000k. The driver is **adjacency build**, not decode: clustered edges share consecutive `source_id` values, so building the out-neighbor map stays much cheaper as edge count rises.
3. **BFS after adjacency is negligible** (much less than 1 ms at every scale). Lifecycle rule holds: optimize load/rebuild and publish sort, not per-hop Vortex.
4. **Adjacency build dominates** cold→walk once the estate is large (~80–90% of total at 500k–1000k natural). Publish-time clustering is therefore a rebuild latency tool, not only a compression tool.
5. **Spine projection** remains correct hygiene; absolute decode wins stay modest because map columns are thin.
6. **Do not invent nested map layouts.** Keep locked flat tables; standardize clustered edge publish + spine load + hot-index reuse.

---

## 7. Recommendations (map)

| Decision                        | Recommendation                                                                                             |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Schema                          | Keep locked flat `map_nodes` / `map_edges`                                                                 |
| Cold load for walk rebuild      | Prefer **edge spine** projection (§2: `source_id`, `target_id`, `edge_type`); load node tags lazily if UI needs them |
| Publish sort                    | Cluster edges by `source_id`, `edge_type`, `target_id` (and consider node cluster by `type` / `entity_id`) |
| Hot path                        | Persist / reuse adjacency across `publish_map` generations when safe; walks must not re-open Vortex        |
| Analytics / filtered cold scans | Revisit zone prune with pushdown filters (`edge_type`, `env`, `last_seen`) — not covered in this run       |
| Bench vs product                | Teaching estates are too small to stress zones; keep 100k–1M edge labs in CI-ish benches                   |

---

## 8. How to reproduce

```bash
cd pillar-ab-implementation/vortex-bench/map-vortex-bench
# natural vs clustered at each scale (nodes = edges / 5)
for edges in 100000 250000 500000 750000 1000000; do
  nodes=$((edges / 5))
  case $edges in
    100000) label=100k ;; 250000) label=250k ;; 500000) label=500k ;;
    750000) label=750k ;; 1000000) label=1000k ;;
  esac
  for sort in natural clustered; do
    cargo run --release --bin map_vortex_bench -- \
      --nodes "$nodes" --edges "$edges" --edge-sort "$sort" \
      --out "out/run-${label}-edges-${sort}" --warmup 1 --repeats 3
  done
done
```
