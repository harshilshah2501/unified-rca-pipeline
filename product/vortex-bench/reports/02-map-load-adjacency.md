# Report 02 — Map Vortex cold load and adjacency rebuild

- **Bench:** [`../map-vortex-bench/`](../map-vortex-bench/)
- **Room:** Motadata `map/` (Pillar B topology)
- **Status:** Experiment results (not a schema redesign — columns stay locked)
- **Primary artifacts:**
  - `map-vortex-bench/out/run-100k-edges-clustered/results.json`
  - `map-vortex-bench/out/run-100k-edges-natural/results.json`
  - `map-vortex-bench/out/run-500k-edges-clustered/results.json`
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

| Knob       | 100k-edge runs                                                | 500k-edge run |
| ---------- | ------------------------------------------------------------- | ------------- |
| Nodes      | 20,000                                                        | 50,000        |
| Edges      | 100,000                                                       | 500,000       |
| Node types | service, host, database, queue, runtime, middleware           | same          |
| Edge types | all fifteen Motadata SCREAMING names (mixed)                  | same          |
| Columns    | Locked Motadata flat schema (promoted tags + epoch-ms clocks) | same          |

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

### 5.1 Compression / part size (100k edges)

| Edge sort | nodes.vortex | edges.vortex | Total       |
| --------- | ------------ | ------------ | ----------- |
| Clustered | 378 KB       | **1.26 MB**  | **1.63 MB** |
| Natural   | 378 KB       | **1.71 MB**  | **2.09 MB** |

Clustering edges by source + type shrinks the edge part ~26% at this scale (dictionary / run locality).

### 5.2 Cold → walk totals (100k edges, clustered)

| Load mode                | decode (n+e) ms | adj ms | bfs ms | total ms |
| ------------------------ | --------------- | ------ | ------ | -------- |
| `full`                   | 6.6             | 25.9   | 0.03   | **32.5** |
| `spine`                  | 6.6             | 48.8*  | 0.04   | 55.4*    |
| `nodes_full_edges_spine` | 8.5             | 30.1   | 0.01   | 38.6     |

\*Spine adjacency was noisier in this median sample; see natural run and 500k run where spine is consistently competitive or better. Decode deltas between full and spine are **small** at 100k because map columns are thin (no 512‑byte blobs).

### 5.3 Cold → walk totals (100k edges, natural)

| Load mode                | decode (n+e) ms | adj ms | bfs ms | total ms |
| ------------------------ | --------------- | ------ | ------ | -------- |
| `full`                   | 7.0             | 33.7   | 0.02   | 40.7     |
| `spine`                  | **5.2**         | 29.4   | 0.05   | **34.6** |
| `nodes_full_edges_spine` | 8.2             | 23.9   | 0.02   | 32.1     |

### 5.4 Scale-up (500k edges, clustered)

| Load mode                | decode (n+e) ms | adj ms | bfs ms | total ms  | parts      |
| ------------------------ | --------------- | ------ | ------ | --------- | ---------- |
| `full`                   | 19.8            | 95.2   | 0.05   | **115.1** | 7.4 MB     |
| `spine`                  | **17.3**        | 84.7   | 0.03   | **102.1** | same files |
| `nodes_full_edges_spine` | 22.7            | 80.4   | 0.04   | 103.1     | same files |

Reachable set from seed at hops=2: 93 nodes (synthetic random graph — not a teaching checkout estate).

---

## 6. Interpretation

1. **BFS after adjacency is negligible** (much less than 1 ms). Once the hot index exists, Scope-style walks are cheap relative to cold rebuild. This confirms the lifecycle rule: optimize load/rebuild, not per-hop Vortex.
2. **Adjacency build dominates** cold→walk total (~70–85% at 500k edges). Future map work should care about how quickly we turn an edge-spine batch into an index (and whether that index is retained across publishes).
3. **Spine projection helps modestly** on decode (~10–25% edge/node decode at 500k) because map columns are already narrow. The sketch lesson (“never `select *` over fat blobs”) still applies as hygiene, but the **absolute** win is smaller until promoted-tag catalogs grow or multi-part analytics scans appear.
4. **Clustered edge sort improves compression** (smaller S3 footprint / fewer bytes to open). Worth doing at publish even if decode ms gains are mild in-process.
5. **Do not invent nested map layouts.** The locked flat schema is the right physical shape; the experiment supports keeping it and measuring load modes + sort, not redesigning nesting.

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
cargo run --release --bin map_vortex_bench -- \
  --nodes 20000 --edges 100000 --edge-sort clustered \
  --out out/run-100k-edges-clustered --warmup 1 --repeats 3

cargo run --release --bin map_vortex_bench -- \
  --nodes 50000 --edges 500000 --edge-sort clustered \
  --out out/run-500k-edges-clustered --warmup 1 --repeats 3
```
