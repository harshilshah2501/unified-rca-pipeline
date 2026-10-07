"""Pillar B map write package — GraphWriter and helpers.

Call order for the happy path:
  GraphWriter.load_estate_bootstrap → write_topo_stream → publish_map
  → optional maintain_map → publish_map again

Depends on ``ab_shared`` only (gate, Dest, ingest sources, schemas). Do not import
from Pillar A sketch code. Diagnose / Scope should read Dest ``map/`` via
``snapshot.load_snapshot`` + ``neighbors`` — they must not call write APIs.

See ``docs/Codebase-go-through.md`` and ``reference/canvases/pillar-b-poc-navigator.canvas.tsx``.
"""
