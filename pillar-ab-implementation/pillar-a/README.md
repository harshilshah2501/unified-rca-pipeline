# Pillar A — Percentiles / sketch store (teammate package)

**Owner:** Pillar A (statistics + `sketch.v1`)  
**Status:** Self-contained hand-off from Unified-RCA `pillar-ab-implementation/`  
**Does not include:** Pillar B graph code, join/integration harness, Pillar C agent

This directory is what you unzip and work in. It has contracts, teaching docs, reference canvases, and a unit-tested PoC.

---

## Quick start

```bash
cd pillar-a/poc
python3 -m venv .venv
make install
make test-all
```

Expected: shared + sketch unit tests pass (no graph/join).

---

## Layout

```text
pillar-a/
├── README.md                 ← you are here
├── HANDOFF.md                ← scope, locked leanings, open work
├── contracts/
│   ├── schemas/
│   │   ├── ingest_v1.schema.json
│   │   └── sketch_v1.schema.json
│   ├── IDENTIFIED_STREAM_REJECT.md
│   └── GATE_B_DEST_PROFILE.md   ← history/ room for sketches
├── docs/
│   ├── PILLAR_A_PERCENTILES_DEEP_DIVE.md   ← start here (inputs → process → artifacts)
│   ├── GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md  ← full brief; sketch FAQ Q15–Q30
│   ├── end-to-end-algorithm-walkthrough.md
│   └── sketch-exemplars-visual.html
├── reference/canvases/
│   ├── pillar-a-poc-walkthrough.canvas.tsx    ← Cursor Canvas: placement / admit / FP
│   └── pillar-a-debugger-moves.canvas.tsx     ← Cursor Canvas: accumulate / reject / Detect
└── poc/
    ├── ab_shared/     ← stubs: identity gate, season, dest, ingest, schema
    ├── sketch/        ← Pillar A writer + read API
    ├── fixtures/lab_checkout/   ← metric-only streams (no topo_update)
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
3. Contract brief FAQ Q15–Q35 (sketches, Detect, FP, S3/Vortex, **merge / raw / shift-left**) in `docs/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`  
   · condensed source: `docs/Sketches_Merging_RawData_QnA.pdf`  
4. Canvases under `reference/canvases/` (open in Cursor Canvas if available)

---

## Out of scope for this zip

- Graph nodes/edges (`graph_node.v1`, `graph_edge.v1`) — Pillar B  
- Join / WorkingSet / door_c harness — `integration/` in the parent monorepo  
- Production Vortex wiring, E6 Detect product path, Pillar C ReAct
