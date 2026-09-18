# Pillar A — Percentiles / sketch store (teammate package)

**Owner:** Pillar A (statistics + `sketch.v1`)  
**Status:** Self-contained hand-off from Unified-RCA `pillar-ab-implementation/`  
**Does not include:** Pillar B graph code, read-join harness, Pillar C agent

This directory is what you unzip and work in. It has contracts, teaching docs, reference canvases, and a unit-tested PoC.

A and B are **parallel writers** after Identity — never merged as one product. Optional WorkingSet join lives in the monorepo `integration/` folder only.

---

## Quick start

```bash
cd pillar-a/poc
python3 -m venv .venv
make install
make test-all
make flush          # optional: FileDest history/sketches.jsonl from sample estate
```

Expected: shared + sketch unit tests pass (no graph/join).

---

## Inputs / outputs (I/O)

| | Pillar A |
|--|----------|
| **Stage** | E4 Stores (parallel to E3 Topology) |
| **Room** | `history/` |
| **Input** | `ingest.v1` with `signal_class=metric_sample`, `identity.status=resolved` |
| **Rejects** | `identity_unresolved`, `identity_synthesized`, `unknown_metric_id` |
| **Silent skip** | Non-metric lines (`topo_update`, …) |
| **Output** | `sketch.v1` → `Dest.put("history", "sketches.jsonl", …)` |
| **Logical key** | `(tenant, entity_id, metric_id, window, season_key, window_start)` |
| **Must not carry** | `src_ci_id` / `dst_ci_id` / `relation` |
| **Read helpers** | `get_window_percentiles` / `get_metric_baseline` |

Wave-1 metrics: `request.latency_ms`, `cpu.utilization_pct`. Windows: `1m` + `5m`. `season_key` = hour-of-week.

---

## Layout

```text
pillar-a/
├── README.md                 ← you are here
├── HANDOFF.md                ← scope, locked leanings, open work
├── contracts/
│   ├── schemas/                 ← symlinks → ../../../contracts/schemas/ (SoT)
│   │   ├── ingest_v1.schema.json
│   │   └── sketch_v1.schema.json
│   ├── MAP_WRITE_READ_RECORD.md ← symlink → ../../contracts/ (SoT)
│   ├── IDENTIFIED_STREAM_REJECT.md ← symlink → SoT
│   └── GATE_B_DEST_PROFILE.md   ← symlink → SoT (history/ room for sketches)
├── docs/
│   ├── PILLAR_A_PERCENTILES_DEEP_DIVE.md   ← start here (inputs → process → artifacts)
│   ├── GRAPH_QNA.md                        ← fabric Q&A (E1–E5)
│   ├── GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md
│   ├── end-to-end-algorithm-walkthrough.md
│   └── sketch-exemplars-visual.html
├── reference/canvases/
│   ├── pillar-a-poc-walkthrough.canvas.tsx
│   └── pillar-a-debugger-moves.canvas.tsx
└── poc/
    ├── ab_shared/     ← stubs: identity gate, season, dest, ingest, schema
    ├── sketch/        ← Pillar A writer + read API
    ├── sample_estate/customer_checkout/   ← metric-only streams (no topo_update); see ../E2_INPUT_FIXTURES.md
    ├── Makefile
    └── requirements.txt
```

---

## What Pillar A owns

| Write | Read (later pipeline) |
|-------|------------------------|
| E4 sketch rows (`sketch.v1`) | E6 Detect door C (digest vs baseline) |
| E5 seasonal baseline refresh (stub in PoC) | E8/E10 investigate (buckets; exemplars optional) |

**Placement:** post-Identity (E2), **parallel** to Topology (E3). Not inside E2 or E3.

**One row holds:** T-Digest + explicit buckets + seasonal baseline. Exemplars optional later.

---

## PoC code spine

```text
ingest.v1 metric_sample (identity resolved)
  → metric_admit.admit_metric
  → windowing.assignments (1m + 5m) + HourOfWeekSeason
  → TDigestAdapter + Histogram
  → SketchWriter.build_row / flush → dest history/sketches.jsonl
  → sketch_read.get_window_percentiles / get_metric_baseline
```

Fixtures are **metric-only** (topo lines removed so you do not need Pillar B).

---

## Docs reading order

1. `HANDOFF.md` — scope and open work  
2. `docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md` — cold-reader deep dive  
3. **`docs/GRAPH_QNA.md`** — fabric Q&A (placement G12–G13, Detect G24–G25, sketch-merge/raw G33–G37)  
4. Contract brief for sit-down lock list: `docs/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md` (§10 = stubs → GRAPH_QNA)  
5. Condensed merge/raw exercise: `docs/Sketches_Merging_RawData_QnA.pdf`  
6. Canvases under `reference/canvases/`

---

## Out of scope for this zip

- Graph nodes/edges (`graph_node.v1`, `graph_edge.v1`) — Pillar B  
- Read-join / WorkingSet / door_c harness — `integration/` in the parent monorepo (not an A∪B merge)  
- Production Vortex wiring, E6 Detect product path, Pillar C ReAct
