# Pillar A + Pillar B — implementation plan

**Status:** Phase 0–merge PoC landed under [`poc/`](./poc/).  
**Contract brief:** [`contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md)

## Design principle

Each pillar is a **standalone package**: design, implement, and unit-test without waiting for the other pillar or for real E1/E2/Vortex.

| Rule | Practice |
|------|----------|
| Contract-first | JSON schemas + reject rules under `contracts/` |
| Stub prerequisites | `ab_shared`: ingest, identity gate, dest, clock, season |
| Module unit tests | No Vortex / NATS / sibling pillar |
| Merge last | `join/` imports graph + sketch **read** APIs only |
| Parallel after Phase 0 | A and B proceed independently |

## What “merge” means

Two write rooms, one identity namespace (`tenant` + `ci_id` / `entity_id`). Sketches never carry edges.

## Implementation order

```text
0a Contracts + fixtures
0b Shared stubs + unit tests
0c Tooling (venv, pytest, deps)
   └── Phase 0 EXIT GATE
1  Pillar B modules   ⎫ parallel
2  Pillar A modules   ⎭
3  Join / merge harness
4  Harden (Gate B note, change_fact, LLD notes)
```

### Pillar B module order

1. `ci_qualify` → 2. `edge_catalog` → 3. `provenance` → 4. `graph_builder` → 5. `snapshot` → 6. `neighbors` (+ `change_fact`)

### Pillar A module order

1. `metric_admit` → 2. `windowing` → 3. `digest` → 4. `buckets` → 5. `baseline` → 6. `sketch_flush` → 7. `sketch_read`

## Phase 0 outcomes (done)

| Check | Location |
|-------|----------|
| Schemas | `contracts/schemas/*.schema.json` |
| Reject list | `contracts/IDENTIFIED_STREAM_REJECT.md` |
| Gate B profile | `contracts/GATE_B_DEST_PROFILE.md` |
| Fixtures | `poc/fixtures/lab_checkout/` |
| Stubs | `poc/ab_shared/` |
| Independence | graph/sketch unit tests + import AST check |

## How to run

```bash
# Prefer owner packages (combined poc/ archived 2026-08-27)
cd pillar-ab-implementation/pillar-a/poc && make install && make test-all
cd pillar-ab-implementation/pillar-b/poc && make install && make test-all
```

Archived combined tree: `_archive/pillar-ab-combined-poc-2026-08/`.

## Defaults (wave 1)

- Dest: files under `poc/out/<tenant>/{map,history}/`
- CI types: Service, Host, Runtime, named Database, BusinessService, …
- Edges emitted: `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`
- Metrics: `request.latency_ms`, `cpu.utilization_pct`; windows `1m`+`5m`; `season_key` = hour-of-week

## Out of this milestone

Pillar C / ReAct, D5 flip, production Vortex wiring, E6 Detect product path, E7 Curate.
