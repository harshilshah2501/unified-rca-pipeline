# Map / sketch writers + Vortex Dest cohesion

- **Status:** **Locked** discussion decision (2026-10-05). Not a Signed product freeze for sketch physical layout.
- **Companions:** [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md) · [`MAP_VORTEX_COLUMNAR_SCHEMA.md`](./MAP_VORTEX_COLUMNAR_SCHEMA.md) · [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md)

## 1. What is locked

1. **One Dest temperature for Motadata cold:** `vortex_s3.v1` (Vortex parts on S3 / Dest). Applies to present `map/` now; `history/` sketches reuse the **same packing + Dest façade pattern** when their columnar lock is ready — not a second temperature.
2. **Two writers stay separate:** GraphWriter (E3 Topology → `map/`) and SketchWriter (E4 Stores → `history/`). Join is at **read** by Dest `tenant` + `entity_id`. Do not merge admit into one writer.
3. **`files.v1` (JSON / JSONL) is lab / debug**, not Motadata cold SoT. Same logical rows; optional twin (like debug `.arrow`), not a second schema.
4. **GraphWriter product verbs stay stable** while cold backend moves to Vortex. Language of the hot orchestrator (Python PoC vs Rust) is **not** locked by this note.
5. **Walks always use a loaded present map** (hot-shaped rows / in-memory tables). Never open Vortex per neighbor. A dedicated write/walk interaction brief for Diagnose / Scope is **deferred**.

## 2. GraphWriter verb inventory (stable names)

```text
load_estate_bootstrap → write_topo_stream → publish_map
                      → optional maintain_map → publish_map again
```

| Verb | Meaning |
|------|---------|
| `load_estate_bootstrap` | Optional declared seed into hot |
| `write_topo_stream` | Admit NOOP / WRITE / DROP into hot (no Dest PUT per line) |
| `publish_map` | Checkpoint hot → cold Dest for that version |
| `maintain_map` | E5 validity on hot; caller publishes again |
| Load (today: `load_snapshot` / `load_map`) | Rebuild walkable present estate from cold |

Target meaning of `publish_map` under Motadata Dest: build flat Arrow columns → write `.vortex` parts → write `manifest.json` → update `latest.json` ([`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md) §6).

## 3. Cold interface (landed)

| Piece | Role |
|-------|------|
| Rust `map_vortex_cold` | `publish` / `load` — `graph_snapshot.v1` JSON ↔ parts + manifest + latest |
| Python [`graph/cold_vortex.py`](../pillar-b/poc/graph/cold_vortex.py) | Subprocess bridge |
| `GraphWriter.publish_map(..., profile=…)` | `files.v1` (default) or `vortex_s3.v1` (FileDest) |
| `load_snapshot` | Auto-detects `latest.json` on FileDest map room |

Env: `POC_MAP_DEST_PROFILE=files.v1|vortex_s3.v1`, optional `MAP_VORTEX_COLD=/path/to/binary`.

## 4. Explicitly deferred

- Full map **walk / WorkingSet** product API brief (neighbors, paths, Diagnose binding).
- SketchWriter physical Vortex column lock and flush wiring.
- Signing sketch.v2 / exemplars / RED.
- Choosing Python vs Rust as the sole hot-admit runtime.
- Making `vortex_s3.v1` the Python lab default (unit tests stay on `files.v1` / MemoryDest).
