# Sample estate: customer checkout

**What this folder is:** Hand-authored **sample estate data** for the PoC’s teaching scenario — a small “customer checkout” service map (`checkout-api`, host, JVM, `payments-db`, business service). Not a live CMDB export and not CaseSeed.

**Doc job:** inventory of files here. Expected-vs-actual narratives: [`SAMPLE_IO.md`](./SAMPLE_IO.md). Package context: [`../../../docs/README.md`](../../../docs/README.md).

Post-E2 signal router (A + B): [`../../../../E2_INPUT_FIXTURES.md`](../../../../E2_INPUT_FIXTURES.md).

| File | Purpose |
|------|---------|
| `topology.bootstrap.json` | Declared starting map for this estate — not CaseSeed |
| `walk_chain.bootstrap.json` | Multi-hop chain for Part B walk tests (not Case A spine) |
| `stream.resolved.jsonl` | Happy-path `topo_update` lines (Case A) |
| `stream.reject.jsonl` | DROP / NOOP tape (Case B) |
| [`SAMPLE_IO.md`](./SAMPLE_IO.md) | Case A/B expected spines / reject outcomes |
| `cases/increment2/` | Increment 2 storm + expected CaseSeed/WorkingSet/LeafClaim spine |
| `cases/increment3/` | Increment 3 expected EvidenceBundle/VerdictCard spine |
| `cases/happy_path/expected_spine.json` | Golden node/edge spine for Case A |
| `cases/reject_tape/expected_rejects.json` | Golden reject reasons + absent CIs for Case B |
| `expected/*.example.json` | Single-object shape samples (not asserted goldens) |

`make test-graph` runs sample I/O plus Part B `test_map_walk.py`.

Mixed metric + topo stream for read-join: `integration/sample_estate/customer_checkout/stream.resolved.jsonl`.
