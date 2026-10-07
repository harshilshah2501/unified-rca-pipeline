# Discussion 01 — Open questions for Pillar A + Pillar B

**Date:** 2026-08-20  
**Prompt (user):** Focus on Pillar A and Pillar B; open questions on (1) typed entities/IDs/metadata/edges, (2) Vortex schema mapping, (3) sketch row format.

## Outcome

Three topics discussed; choices later locked in discussion 03:

| Topic | Decision (later locked) |
|-------|-------------------------|
| Entities + edges | Rich CI catalog + 15 edge types + provenance (not a minimal 4-edge MVP) |
| Vortex encoding | Logical schema first (JSON field tables; encode to protobuf later) |
| Sketch row | One row with T-Digest + buckets + seasonal baseline |

## Key points captured

- Same `tenant`+`ci_id` for graph and sketches
- CI-only vertices; Alert/Incident not on E3
- Gate B: Vortex may be one dest, not mandatory lake
- Freeze semantics before Vortex tooling

## Follow-on

See `02-logical-schema-first-shareable-definitions.md` and `03-owner-locks-graph-and-sketch.md`.
