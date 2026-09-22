# Sample estate: customer checkout

**What this folder is:** Hand-authored **lab stand-in** for a Motadata customer estate — a small “customer checkout” service map (`checkout-api`, host, JVM, `payments-db`, business service). Not a live CMDB export and not Detect CaseSeed.

**Contract vs files:** `ingest.v1` is the **JSON schema / wire contract** (field names + `fact_kind` enum). In production, GraphWriter would subscribe to a post-E2 **`ingest.v1` stream** (bus TBD — NATS optional, Vector, etc.). In this PoC, that stream is **files**:

| Production idea | Lab stand-in in this folder |
|-----------------|-------------------------------|
| Continuous post-E2 `ingest.v1` feed (topo lines) | `stream.resolved.jsonl` |
| Same feed with DROP/NOOP lines mixed in | `stream.reject.jsonl` |
| Optional declared starting map | `topology.bootstrap.json` |

Package context: [`../../../docs/README.md`](../../../docs/README.md) · expected-vs-actual narratives: [`SAMPLE_IO.md`](./SAMPLE_IO.md) · team demo: [`../../../docs/TEAM_WALKTHROUGH.md`](../../../docs/TEAM_WALKTHROUGH.md).

---

## Layout

```text
customer_checkout/
├── topology.bootstrap.json      ← optional starting nodes/edges (not CaseSeed)
├── walk_chain.bootstrap.json    ← longer chain for walk-only tests (not Case A spine)
├── stream.resolved.jsonl        ← Case A: five topo_update WRITE lines (post-E2 shape)
├── stream.reject.jsonl          ← Case B: DROP + NOOP lines + bootstrap still kept
├── SAMPLE_IO.md                 ← Case A/B expected vs actual narrative
├── README.md                    ← this file
├── expected/                    ← single-object shape samples (not asserted goldens)
│   ├── ingest.example.json
│   ├── graph_node.example.json
│   ├── graph_edge.example.json
│   └── change_fact.example.json
└── cases/
    ├── case_a_map_spine/        ← PoC core — golden node/edge spine after build
    │   └── expected_spine.json
    ├── case_b_rejects/          ← PoC core — golden DROP reasons + absent CIs
    │   └── expected_rejects.json
    ├── stub_case_path/          ← NOT PoC core — Detect→Localize harness fixtures
    │   ├── signal_storm.json
    │   └── expected_case_path.json
    └── stub_diagnose_close/     ← NOT PoC core — Identify/Package harness fixtures
        └── expected_verdict.json
```

---

## Files (what each is for)

| Path | Role | PoC core? |
|------|------|-----------|
| `topology.bootstrap.json` | Declared starting estate loaded before the stream | Yes (Case A/B) |
| `stream.resolved.jsonl` | Lab tape of **admitted** `topo_update` lines (`identity.status=resolved`) | Yes — Case A input |
| `stream.reject.jsonl` | Lab tape mixing DROP (`unattributed` / never-CI / bad relation) and NOOP (`metric_sample`, …) | Yes — Case B input |
| `walk_chain.bootstrap.json` | Extra multi-hop estate for `test_map_walk` only | Walk tests |
| `cases/case_a_map_spine/expected_spine.json` | Golden **spine** (ci_id / relation only) after Case A publish | Yes |
| `cases/case_b_rejects/expected_rejects.json` | Golden reject **codes** + CIs that must not appear | Yes |
| `cases/stub_case_path/` | Stub Detect storm → CaseSeed / WorkingSet / LeafClaim | **No** — optional harness ([`MAP_P2_CASE_PATH.md`](../../../docs/MAP_P2_CASE_PATH.md)) |
| `cases/stub_diagnose_close/` | Stub EvidenceBundle / VerdictCard close | **No** — optional harness ([`MAP_P3_DIAGNOSE_CLOSE.md`](../../../docs/MAP_P3_DIAGNOSE_CLOSE.md)) |
| `expected/*.example.json` | Human shape samples for schemas | No — not asserted |

`make test-graph` asserts Case A/B spines. Stub harnesses run under `make test-all` but are **not** the knowledge-graph mission.

Mixed metric + topo stream for optional A∥B read-join: `integration/sample_estate/customer_checkout/stream.resolved.jsonl`.
