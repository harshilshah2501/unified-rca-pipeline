# Pillar A hand-off notes

**Date:** 2026-08-27  
**From:** Unified-RCA / ObserveOps Pillar A+B slice  
**To:** Pillar A owner (teammate)

## Locked leanings (do not flip casually)

1. **`sketch.v1` one hybrid row:** T-Digest + buckets + seasonal baseline under  
   `(tenant, entity_id, metric_id, window, season_key, window_start)`.  
2. **`entity_id` = graph `ci_id`** after Identity bind — same string.  
3. **Detect (door C) = digest p95 vs seasonal baseline.** Buckets/exemplars are after-fire investigate.  
4. **Motadata-shaped lake needs both temperatures:** cold durable (S3) + hot lookup (Vortex).  
   Lab FileDest `history/` + `sketch_read` are stand-ins.  
5. **Admit only `identity.status = resolved`** metric samples.  
6. **D5 stays Review** (operator path works with agent off). Pillar C is out of this package.  
7. **Merge digests, not average p95s.** Bucket merge only with identical `bucket_schema_version` / bounds ([`GRAPH_QNA.md`](./docs/GRAPH_QNA.md) G33–G34).  
8. **Shift-left and sketch compression are two levers** (volume vs lifespan). Detect hot path = sketch; raw rebuild cases need an explicit buffer decision (GRAPH_QNA G35–G37).

## Wave-1 PoC defaults

| Item | Value |
|------|--------|
| Metrics | `request.latency_ms`, `cpu.utilization_pct` |
| Windows | `1m` + `5m` |
| `season_key` | hour-of-week, e.g. `Thu-03:00` (`HourOfWeekSeason`) |
| Bucket schema | `latency_v1` bounds `[0,50,100,200,500,1000,2000]` |
| Dest room | `history/` → `sketches.jsonl` |

## Known PoC gaps (good next work)

| Gap | Notes |
|-----|--------|
| First flush still self-seeds when no prior history | Need multi-window / multi-day history for real Detect contrast (debugger Move 3); E5 `refresh_seasonal_baselines` rebuilds from Dest |
| No `trace_id` / exemplars | Optional; pass through admit when events carry ids |
| No real Vortex/S3 | Keep contract; dest profile is files for now |

~~Baseline mixes 1m and 5m~~ — **fixed:** baseline key includes `window`.
~~`refresh_baselines` is a stub~~ — **landed:** `sketch/maintain.py` + `SketchWriter.refresh_baselines(dest)`.

## False-positive filtering (not “all at E5”)

| Junk | Stage |
|------|--------|
| Bad identity / unknown metric | **Admit** |
| Busy hour looks like outage | **E6 Detect** using baseline **E5 refreshes** |
| Duplicate signals after fire | **E7 Curate** (not in this package) |

## How this package relates to Pillar B

- You do **not** need graph code to unit-test sketches.  
- A and B are **parallel writers**, never merged as one product.  
- Optional **read-time join** (same `tenant`+`ci_id`, WorkingSet) lives in the monorepo `integration/` folder — a join harness, not a package merge.  
- Mixed lab tapes that included `topo_update` were split: this zip’s fixtures are **metric-only**.

## Suggested first tasks

1. `make test-all` — green baseline.  
2. Read deep dive §5–7 + [`docs/GRAPH_QNA.md`](./docs/GRAPH_QNA.md) (fan-out G12–G13, Detect G24–G25, sketch-merge/raw G33–G37).  
3. `make flush` — lab FileDest write under `poc/out/`.  
4. Optional: admit `trace_id` → exemplar on hot bin (still not required for Detect).  
5. Optional: multi-day fixture history so Detect contrast does not rely on same-run seeding.

## Contact / monorepo paths (if you have full repo access)

| Item | Path |
|------|------|
| This package | `pillar-ab-implementation/pillar-a/` |
| Pillar B | `pillar-ab-implementation/pillar-b/` |
| Join | `pillar-ab-implementation/integration/` |
| Canonical brief | `pillar-ab-implementation/contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md` |
| Fabric Q&A | Slice `pillar-ab-implementation/contracts/GRAPH_QNA.md` (package `docs/GRAPH_QNA.md` may still point there for the zip) |
| Repo hygiene | `docs/REPO_HYGIENE.md` |
