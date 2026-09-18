# Pillar A + Pillar B — implementation plan

**Status:** Phase 0 done; packages split (2026-08-27). Owner packages under [`pillar-a/`](./pillar-a/) and [`pillar-b/`](./pillar-b/).  
**Contract brief:** [`contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) · fabric Q&A: [`contracts/GRAPH_QNA.md`](./contracts/GRAPH_QNA.md)

## Design principle

Each pillar is a **standalone package**: design, implement, and unit-test without waiting for the other pillar or for real E1/E2/Vortex.

**A and B are never merged** in the pipeline. After Identity (E2) they are **parallel independent writers** into two rooms (`history/` vs `map/`). Diagnose joins them at **read time** into a bounded WorkingSet by `tenant` + `ci_id` ≡ `entity_id`. There is no sync job and no combined A∪B writer package.

| Rule | Practice |
|------|----------|
| Contract-first | JSON schemas + reject rules under `contracts/` |
| Stub prerequisites | `ab_shared`: ingest, identity gate, dest, clock, season |
| Module unit tests | No Vortex / NATS / sibling pillar |
| Read-join last (optional) | `integration/` imports graph + sketch **read** APIs only — not a product merge |
| Parallel after Phase 0 | A and B proceed independently |

## Two rooms, one identity namespace

| Room | Pillar | Artifacts |
|------|--------|-----------|
| `history/` | A (E4) | `sketch.v1` |
| `map/` | B (E3) | `graph_node.v1` / `graph_edge.v1` → `GraphSnapshot` |

Sketches never carry edges. Join = WorkingSet at read, not folder sync.

## Implementation order

```text
0a Contracts + fixtures
0b Shared stubs + unit tests
0c Tooling (venv, pytest, deps)
   └── Phase 0 EXIT GATE
1  Pillar B modules   ⎫ parallel independent packages
2  Pillar A modules   ⎭
3  Optional read-join harness (integration/) — after both unit-green
4  Harden (Gate B note, change_fact, LLD notes)
```

### Pillar B module order

1. `ci_qualify` → 2. `edge_catalog` → 3. `provenance` → 4. `graph_builder` → 5. `snapshot` → 6. `neighbors` (+ `change_fact`)

### Pillar A module order

1. `metric_admit` → 2. `windowing` → 3. `digest` → 4. `buckets` → 5. `baseline` → 6. `sketch_flush` → 7. `sketch_read`

Subsystem plans: Cursor `pillar_a_subsystem_plan` · `pillar_b_subsystem_plan`.

## Phase 0 outcomes (done)

| Check | Location |
|-------|----------|
| Schemas (SoT) | `contracts/schemas/*.schema.json` — package mirrors are **symlinks**; `make check-schemas` |
| Reject list | `contracts/IDENTIFIED_STREAM_REJECT.md` |
| Gate B profile | `contracts/GATE_B_DEST_PROFILE.md` |
| Map write/read (JSON) | `contracts/MAP_WRITE_READ_RECORD.md` + `schemas/graph_snapshot_v1.schema.json` |
| Fixtures | per-package `poc/sample_estate/customer_checkout/` · map: [`E2_INPUT_FIXTURES.md`](./E2_INPUT_FIXTURES.md) |
| Stubs | per-package `poc/ab_shared/` |
| Independence | graph/sketch unit tests + import AST check |

## How to run

```bash
cd pillar-ab-implementation/pillar-a/poc && make install && make test-all
cd pillar-ab-implementation/pillar-b/poc && make install && make test-all
```

Archived combined tree: `_archive/pillar-ab-combined-poc-2026-08/` (do not expand).

## Defaults (wave 1)

- Dest: files under `poc/out/<tenant>/{map,history}/`
- CI types: Service, Host, Runtime, named Database, BusinessService, …
- Edges emitted: `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`
- Metrics: `request.latency_ms`, `cpu.utilization_pct`; windows `1m`+`5m`; `season_key` = hour-of-week

## Team discussion (not locked in this plan)

| Note | Topic |
|------|--------|
| [`discussion/04-raw-data-identity-lut-open-questions.md`](./discussion/04-raw-data-identity-lut-open-questions.md) | Raw retention, Identity look-up table (LUT) misses, quarantine replay — vote card for the room |
| [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md) | Pillar B map JSON write/read keys (`graph_snapshot.json` / jsonl); Vortex/S3 later |
| [`Raw_Data_Handling.pdf`](./Raw_Data_Handling.pdf) | Source synthesis (six cases, Edge Delta check) |

## Out of this milestone

Pillar C / ReAct, D5 flip, production Vortex wiring, E6 Detect product path, E7 Curate.
