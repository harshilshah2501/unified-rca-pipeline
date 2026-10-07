# Discussion 03 — Owner locks: graph + sketch

**Date:** 2026-08-20  

## Locks

| Topic | Choice |
|-------|--------|
| Graph (entities / edges) | Richer CI catalog + **15 edge types** + full provenance; accept slower freeze |
| Vortex | Logical schema first — no `.proto` yet |
| Sketch row | One row: T-Digest + explicit buckets + seasonal baseline |

## Mitigations recorded

- Schema may declare all 15 relations on day one
- Lab writers may **emit** a subset first (wave 1 / wave 2)
- Sketch key: `(tenant, entity_id, metric_id, window, season_key, window_start)`
- Start windows: `1m` + `5m`; season_key lean: hour-of-week (`Thu-09:00`)

## Still open for the stakeholder room

1. Final closed `ci_type` enum for wave 1  
2. Whether `tier` / `instance_scope` are day-one required  
3. First two sketch metrics + bucket bounds  
4. Sole GraphSnapshot writer  
5. Timestamp format (RFC3339 vs unix millis)

## Canonical brief after this lock

`contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`
