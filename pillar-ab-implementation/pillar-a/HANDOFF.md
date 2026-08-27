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
| Baseline mixes 1m and 5m in one accumulator | Prefer baseline key that includes `window` or separate accumulators |
| First flush self-seeds baseline | Need multi-window / multi-day history for real Detect contrast (debugger Move 3 pattern) |
| No `trace_id` / exemplars | Optional; pass through admit when events carry ids |
| `refresh_baselines` is a stub | E5 Maintain story |
| No real Vortex/S3 | Keep contract; dest profile is files for now |

## False-positive filtering (not “all at E5”)

| Junk | Stage |
|------|--------|
| Bad identity / unknown metric | **Admit** |
| Busy hour looks like outage | **E6 Detect** using baseline **E5 refreshes** |
| Duplicate signals after fire | **E7 Curate** (not in this package) |

## How this package relates to Pillar B

- You do **not** need graph code to unit-test sketches.  
- Integration (same `tenant`+`ci_id`, WorkingSet) lives in the monorepo `integration/` folder when both pillars merge.  
- Mixed lab tapes that included `topo_update` were split: this zip’s fixtures are **metric-only**.

## Suggested first tasks

1. `make test-all` — green baseline.  
2. Read deep dive §5–7 + [`docs/GRAPH_QNA.md`](./docs/GRAPH_QNA.md) sections on fan-out / Detect / merge (G12–G13, G24–G25, G33–G37).  
3. Fix baseline key so 1m/5m do not share one seasonal accumulator.  
4. Add a unit test: prior window expected_p95 vs spike current_p95 (Detect contrast).  
5. Optional: admit `trace_id` → exemplar on hot bin (still not required for Detect).

## Contact / monorepo paths (if you have full repo access)

| Item | Path |
|------|------|
| This package | `pillar-ab-implementation/pillar-a/` |
| Pillar B | `pillar-ab-implementation/pillar-b/` |
| Join | `pillar-ab-implementation/integration/` |
| Canonical brief | `pillar-ab-implementation/contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md` |
| Fabric Q&A | `docs/GRAPH_QNA.md` (also under this package `docs/` via symlink) |
| Repo hygiene | `docs/REPO_HYGIENE.md` |
