# Pillar B — Knowledge graph (owner package)

**Owner:** Harshil / Pillar B (entities + edges + changes)  
**Sibling:** [`../pillar-a/`](../pillar-a/) (teammate percentiles package)  
**Join:** [`../integration/`](../integration/)

## Quick start

```bash
cd pillar-b/poc
python3 -m venv .venv
make install
make test-all
```

## Layout

- `contracts/` — ingest + graph_node/edge/change_fact schemas  
- `docs/` — graph contract brief + node/edge samples  
- `poc/graph/` — CI qualify, edges, builder, snapshot, neighbors  
- `poc/ab_shared/` — identity gate, dest, ingest stubs  
- `poc/fixtures/` — topo_update stream + topology.seed.json  

## Placement

Post-Identity (E2). Parallel to Pillar A sketch write. Emits `GraphSnapshot` into dest `map/`.
