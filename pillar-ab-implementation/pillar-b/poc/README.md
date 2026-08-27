# Pillar B PoC

Lab Topology writer: resolved `topo_update` → `GraphSnapshot` → Gate B **`files.v1`** under `map/`.

```bash
make install && make test-all
```

| Dest key | Encoding |
|----------|----------|
| `map/graph_snapshot.json` | Pretty JSON `graph_snapshot.v1` |
| `map/nodes.jsonl` | One `graph_node.v1` per line |
| `map/edges.jsonl` | One `graph_edge.v1` per line |

Normative contract: [`../contracts/MAP_WRITE_READ_RECORD.md`](../contracts/MAP_WRITE_READ_RECORD.md).  
Package overview: [`../README.md`](../README.md).
