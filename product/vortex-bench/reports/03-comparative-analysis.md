# Report 03 — Comparative analysis: sketch vs map Vortex benches

- **Program hub:** [`../README.md`](../README.md)
- **Inputs:** [`01-sketch-physical-layout.md`](./01-sketch-physical-layout.md) · [`02-map-load-adjacency.md`](./02-map-load-adjacency.md)
- **Vortex units (shared):** Zone (~8k rows, prune) · Flat chunk (~2 MB uncompressed / column, decode) · Buffered run (~1 MB compressed, I/O)

---

## 1. Program objective — why two different experiments?

Both Dest rooms will use Vortex. That does **not** mean both need the same bench.

| | Sketches | Map |
|--|----------|-----|
| **Why experiment at all?** | Logical sketch.v2 is a rich evidence object. Physical layout can accidentally make every “find bad window” scan decode digests and exemplars. | Logical map schema is already flat and locked. Product walks are hot; the risk is a slow **cold→hot** rebuild, or wasting time on nested-layout redesign. |
| **Objective** | Pick a physical shape + projection rules so Stage‑1 RCA stays cheap and Stage‑2/3 evidence stays available. | Measure load → adjacency → first walk; keep schema; improve projection and publish clustering. |
| **What “done” means** | Freeze candidate for sketch Vortex columns (spine vs evidence), not a new Detect model. | Confidence that Scope lifecycle (hot walks) is right, and a short list of publish/load knobs that matter. |

Shared program goal: **Motadata cold storage that matches how ObserveOps actually reads**—staged investigate for history, rebuild-once walk-many for map—under one Vortex Dest temperature.

---

## 2. Same engine, different jobs

| | Sketches (`history/`) | Map (`map/`) |
|--|----------------------|--------------|
| **Writer** | SketchWriter (Pillar A) | GraphWriter (Pillar B) |
| **Row shape** | Wide evidence row (digest + buckets + baseline + optional exemplars) | Narrow flat CI / edge rows (locked) |
| **Dominant reader** | Staged RCA / Detect investigate | Cold load → hot adjacency → Scope BFS |
| **Per-hop Vortex?** | No (read sketch windows by key) | **No** (walks on hot index) |
| **Fat columns?** | Yes (T‑Digest bytes, exemplar lists) | No (Utf8 ids + small tags + u64 clocks) |
| **Experiment focus** | Physical layout + projection stages | Load mode + edge clustering + rebuild cost |

Vortex’s three layers apply to both Dest rooms. The **optimization target** differs.

---

## 3. What each experiment proved

### Sketches

- Stage‑1 `select *` over a wide sketch row is catastrophic (~5–10× Stage‑1 decode at 100k rows).
- Spine-only projections make nested (`A`) and flat (`D`) similar at Stage‑1.
- Progressive Stage‑2/3 favors **flat evidence columns** (`D`) over one nested cold struct (`C`).
- Dest file split (`E`) isolates Stage‑1 but needs row-selective cold reads before it wins Stage‑2/3.

**Provisional physical direction:** logical nested sketch.v2; physical **hot spine + flat on-demand evidence**.

### Map

- After adjacency exists, BFS cost is negligible vs cold rebuild — lifecycle docs are right.
- **Adjacency build**, not Vortex decode, dominates cold→walk at 100k–1000k edges.
- Spine vs full projection is a modest decode win (thin columns); still the correct default for walk rebuild.
- Clustering edges at publish shrinks edge parts (~10–27% across 100k–1000k) and, more importantly, cuts cold→walk time by ~28% → ~50–60% as edge count grows — mostly via faster adjacency build (see report 02 scale sweep).
- A **sort-aware** adjacency builder adds another ~28–37% adj-build cut on clustered parts (near-zero on natural). Hubby estates (1% hubs → ~50% of edges) still benefit from clustered publish (~30–50% under naive rebuild).

**Provisional physical direction:** keep locked flat tables; optimize **publish sort + spine load + sort-aware hot rebuild + index reuse**.

---

## 4. Shared design rules (Motadata Vortex)

These rules should stay common across rooms:

1. **Logical contract ≠ physical decode set.** Project only columns the current stage needs.
2. **Never default interactive paths to `select *`.** Especially fatal when fat columns exist (sketches); still wrong for map hygiene.
3. **Cluster rows for the predicates you will prune on.** Sketches: entity/metric/window. Map edges: source/type/target.
4. **Do not open cold Vortex on the interactive inner loop.** Sketch investigate reads selected windows; map walks use hot adjacency.
5. **Measure bytes + decode + next-stage cost**, not schema aesthetics.

---

## 5. Divergent decisions (do not copy blindly)

| Temptation | Sketch answer | Map answer |
|------------|---------------|------------|
| Nested structs for “clean API” | OK logically; physical prefer flat evidence columns | **Reject** — already flat; nesting adds no value |
| Split Dest objects (spine vs evidence) | Candidate after selective cold read | Low priority — two tables already (`nodes` / `edges`) |
| A–E layout matrix | Primary experiment | **Wrong experiment** |
| Exemplars / T‑Digest packing | Core size/decode problem | N/A |
| Adjacency / BFS | N/A | Core rebuild problem |

---

## 6. How this fits the RCA ladder

```text
Graph / map (hot after cold load)
        ↓
RED / KPI
        ↓
Sketch hot spine          ← sketch bench Stage 1
        ↓
Distribution evidence     ← sketch bench Stage 2
        ↓
Exemplars                 ← sketch bench Stage 3
        ↓
Trace store / raw         ← outside Vortex history/map
```

Map bench sits at the **top of the ladder** (estate availability). Sketch bench sits in the **middle descent**. They share Vortex technology and Dest temperature (`vortex_s3.v1` intent) but not the same physical schema problem.

---

## 7. Priority backlog

| Priority | Work | Owner lens |
|----------|------|------------|
| P0 | Keep sketch Stage‑1 projection discipline in any Retrieval design | Pillar A / Detect-investigate |
| P0 | Keep map walks on hot adjacency; spine-load on rebuild | Pillar B / Scope |
| P1 | Freeze candidate sketch physical columns (`D`-like) when signing sketch.v2 | Pillar A + contracts |
| P1 | Publish-time edge clustering in `map_vortex` / GraphWriter publish | Pillar B |
| P2 | Zone filter pushdown benches (both rooms) + `natural` vs `clustered` sketch sort | vortex-bench |
| P2 | 1M sketch rows + 1M map edges; optional S3 range-get instrumentation | vortex-bench |
| P3 | Map multi-part publish sizing | Pillar B |

---

## 8. Final comparative verdict

**Use one Vortex Dest temperature and one engineering discipline (project, cluster, measure). Use two physical playbooks:**

- **History / sketches:** redesign around a hot spine so Stage‑1 never decodes digest/exemplars.
- **Map / graph:** keep the locked flat schema; spend effort on cold→hot rebuild and publish clustering, not on nested layout variants.

Copying the sketch A–E matrix onto map would optimize the wrong bottleneck. Copying map’s “flat is enough” complacency onto sketches would leave Stage‑1 `select *` as a latent production foot-gun.
