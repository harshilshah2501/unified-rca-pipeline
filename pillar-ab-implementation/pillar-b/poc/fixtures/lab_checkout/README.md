# Pillar B lab fixtures (`fixtures/lab_checkout/`)

Full post-E2 ingest map (A + B, metric vs topo lines, identity overlay): [`../../../../E2_INPUT_FIXTURES.md`](../../../../E2_INPUT_FIXTURES.md).

| File | Purpose |
|------|---------|
| `topology.seed.json` | Declared nodes + edges loaded before stream ingest |
| `stream.resolved.jsonl` | **Topo-only** happy path (`topo_update`, identity resolved) |
| `stream.reject.jsonl` | Reject tape: unresolved/synthesized identity, never-CI types, unknown relations; non-topo lines (`metric_sample`, plus optional `event` / `trace_span`) verify **NOOP** |
| [`SAMPLE_IO.md`](./SAMPLE_IO.md) | Sample inputs ↔ expected spines / reject outcomes (NOOP / WRITE / DROP) |
| `cases/happy_path/expected_spine.json` | Golden node/edge spine for Case A |
| `cases/reject_tape/expected_rejects.json` | Golden reject reasons + absent CIs for Case B |
| `expected/*.example.json` | Single-object shape samples (not asserted goldens) |

Expected vs actual: `make test-graph` runs `graph/tests/unit/test_sample_io.py`.

**NOOP reminder:** `metric_sample`, `event`, `trace_span`, and `anomaly` never mutate `map/` here. Pillar A sketches are **metrics-only**; logs/traces need other history contracts if Motadata stores them always-on.

Mixed metric + topo stream for read-join harness: `integration/fixtures/lab_checkout/stream.resolved.jsonl`.
