# Pillar B PoC — lab runbook

**Doc job:** how to install, test, and flush this lab.  
**Not this page:** package I/O / admit table → [`../README.md`](../README.md). Stage eval → [`../docs/MAP_P1_FABRIC_EVAL.md`](../docs/MAP_P1_FABRIC_EVAL.md). Code tour → [`../docs/Codebase-go-through.md`](../docs/Codebase-go-through.md). Doc map → [`../docs/README.md`](../docs/README.md).

Lab Topology writer: resolved `topo_update` → `GraphSnapshot` → Gate B **`files.v1`** under `map/`.

## Run

```bash
make install && make test-all
make publish-map    # bootstrap + stream.resolved.jsonl → poc/out/<tenant>/map/
```

## Dest keys after flush

| Dest key | Encoding |
|----------|----------|
| `map/graph_snapshot.json` | Pretty JSON `graph_snapshot.v1` |
| `map/nodes.jsonl` | One `graph_node.v1` per line |
| `map/edges.jsonl` | One `graph_edge.v1` per line |

Fixtures and Case A/B goldens: [`fixtures/lab_checkout/SAMPLE_IO.md`](./fixtures/lab_checkout/SAMPLE_IO.md).
