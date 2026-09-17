# Pillar B PoC

Lab Topology writer: resolved `topo_update` → `GraphSnapshot` → Gate B **`files.v1`** under `map/`.

## Run

```bash
make install && make test-all
make flush    # seed + stream.resolved.jsonl → poc/out/<tenant>/map/
```

## Dest keys

| Dest key | Encoding |
|----------|----------|
| `map/graph_snapshot.json` | Pretty JSON `graph_snapshot.v1` |
| `map/nodes.jsonl` | One `graph_node.v1` per line |
| `map/edges.jsonl` | One `graph_edge.v1` per line |

## Guide links

| Doc | Why |
|-----|-----|
| [`../README.md`](../README.md) | Package I/O, admit NOOP/WRITE/DROP, reading order |
| [`fixtures/lab_checkout/SAMPLE_IO.md`](./fixtures/lab_checkout/SAMPLE_IO.md) | Expected spines vs live flush |
| [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md) | Post-E2 `signal_class` router (A vs B) |
| [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md) | Normative map write/read |
| [GraphWriter walkthrough](http://127.0.0.1:8765/graphwriter-io-walkthrough.html) | Hub Site tab (seven steps) |

**Admit reminder:** GraphWriter admits only `topo_update` with resolved identity. `metric_sample`, `event`, `trace_span`, and `anomaly` are silent NOOP here (Pillar A sketches are metrics-only; logs/traces need other history surfaces if stored).
