# Discussion 02 — No Vortex proto yet; share impeccable definitions

**Date:** 2026-08-20  
**Prompt (user):** No Vortex `.proto` / table API exists. Will sit with stakeholders to finalize expected entities and edges — need impeccable definitions and a clear format to share.

## Decision

**Logical schema first.** Protobuf (or Parquet/JSON tables) is an encoding applied **after** the room freezes field tables.

## What to bring to the sit-down

1. Entity definition (what is / is not a CI)
2. Primary ID = `tenant` + `ci_id` (`entity_id` alias only)
3. Edge definition + provenance meanings
4. JSON examples: `graph_node.v1`, `graph_edge.v1`
5. Explicit “not on the graph” list

## Artifact created

`contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md` (later updated for rich graph + one-row sketch).

## Format ladder

| Stage | Format |
|-------|--------|
| Meeting now | JSON + field tables |
| After Signed | LLD-E3 / LLD-E4 field tables |
| When Vortex exists | Generate `.proto` / DDL from Signed tables |
