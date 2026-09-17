# Pillar B lab fixtures (`fixtures/lab_checkout/`)

**Doc job:** inventory of files in this folder. Expected-vs-actual narratives live in [`SAMPLE_IO.md`](./SAMPLE_IO.md). Package / stage context: [`../../../docs/README.md`](../../../docs/README.md).

Full post-E2 ingest map (A + B): [`../../../../E2_INPUT_FIXTURES.md`](../../../../E2_INPUT_FIXTURES.md).

| File | Purpose |
|------|---------|
| `topology.bootstrap.json` | Declared estate bootstrap (nodes + edges) loaded before stream ingest — not CaseSeed |
| `stream.resolved.jsonl` | **Topo-only** happy path (`topo_update`, identity resolved) |
| `stream.reject.jsonl` | Reject tape + non-topo lines that must **NOOP** on the map |
| [`SAMPLE_IO.md`](./SAMPLE_IO.md) | Case A/B expected spines / reject outcomes |
| `cases/happy_path/expected_spine.json` | Golden node/edge spine for Case A |
| `cases/reject_tape/expected_rejects.json` | Golden reject reasons + absent CIs for Case B |
| `expected/*.example.json` | Single-object shape samples (not asserted goldens) |

`make test-graph` runs `graph/tests/unit/test_sample_io.py`.

Mixed metric + topo stream for read-join: `integration/fixtures/lab_checkout/stream.resolved.jsonl`.
