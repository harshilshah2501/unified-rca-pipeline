# Pillar B — sample estate inputs / expected outputs

**Purpose:** Freeze what GraphWriter should produce from this sample estate (customer checkout), then compare **expected** (JSON under `cases/`) to **actual** (live writer flush) in unit tests.

**Doc job:** Case A/B goldens only. Stage matrix → [`../../../docs/MAP_P1_FABRIC_EVAL.md`](../../../docs/MAP_P1_FABRIC_EVAL.md). Doc map → [`../../../docs/README.md`](../../../docs/README.md).

**P1 entry:** deep fabric eval guide linked above. Case A/B below remain **E3 acceptance** spines — not the full P1 matrix.

**Router (post-E2):** GraphWriter admits only `topo_update`. Other `signal_class` values (`metric_sample`, `event`, `trace_span`, `anomaly`, …) are **NOOP** (silent skip) — see [`../../../../E2_INPUT_FIXTURES.md`](../../../../E2_INPUT_FIXTURES.md). Hub framing: [Our HLD · GraphWriter · Admit](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter) (NOOP / WRITE / DROP).

**How comparison works:** Full `graph_node.v1` / `graph_edge.v1` objects carry provenance and display fields that can grow without changing the estate map. Tests therefore compare a **spine**:

| Artifact | Compared fields |
|----------|-----------------|
| Node | `ci_id`, `ci_type`, `identity_status` |
| Edge | `edge_id`, `src_ci_id`, `relation`, `dst_ci_id` |
| Snapshot | `tenant`, `version` + sorted nodes/edges |

Helper: [`../../graph/compare.py`](../../graph/compare.py). Tests: [`../../graph/tests/unit/test_sample_io.py`](../../graph/tests/unit/test_sample_io.py).

```bash
cd pillar-ab-implementation/pillar-b/poc
make test-graph   # includes expected vs actual
```

---

## Case A — happy path

| | Path |
|--|------|
| **Input bootstrap** | [`../topology.bootstrap.json`](../topology.bootstrap.json) |
| **Input stream** | [`../stream.resolved.jsonl`](../stream.resolved.jsonl) |
| **Expected spine** | [`cases/happy_path/expected_spine.json`](./cases/happy_path/expected_spine.json) |
| **Actual** | `GraphWriter.load_estate_bootstrap` → `write_topo_stream` → `publish_map` → `graph_snapshot.v1` |

### Input graph (bootstrap nodes + relations)

| Node `ci_id` | `ci_type` |
|--------------|-----------|
| `bs-checkout` | BusinessService |
| `checkout-api` | Service |
| `linux-server-app-01` | Host |
| `app-runtime-jvm` | Runtime |
| `payments-db` | Database |

| `src` | `relation` | `dst` |
|-------|------------|-------|
| checkout-api | runs_on | linux-server-app-01 |
| app-runtime-jvm | runs_on | linux-server-app-01 |
| checkout-api | depends_on | payments-db |
| checkout-api | part_of | bs-checkout |
| checkout-api | communicates_with | payments-db |

The stream repeats the same five `topo_update` facts with `identity.status=resolved` (and richer `bind_source` for provenance). Estate bootstrap + stream must not invent a sixth relation.

### Expected vs actual (spine)

| Check | Expected | Actual (test) |
|-------|----------|---------------|
| Node count | 5 | equals expected list |
| Edge count | 5 | equals expected list |
| Rejects | `[]` | `writer.rejects == []` |
| Neighbor example | checkout-api reaches payments-db | covered by existing writer tests + edge row |

Expected edge ids (stable replace keys):

- `e_checkout-api_runs_on_linux-server-app-01`
- `e_app-runtime-jvm_runs_on_linux-server-app-01`
- `e_checkout-api_depends_on_payments-db`
- `e_checkout-api_part_of_bs-checkout`
- `e_checkout-api_communicates_with_payments-db`

---

## Case B — reject tape

| | Path |
|--|------|
| **Input bootstrap** | [`../topology.bootstrap.json`](../topology.bootstrap.json) |
| **Input stream** | [`../stream.reject.jsonl`](../stream.reject.jsonl) |
| **Expected** | [`cases/reject_tape/expected_rejects.json`](./cases/reject_tape/expected_rejects.json) |

### Input lines that must not become map vertices/edges

| Line intent | Action | Why |
|-------------|--------|-----|
| `topo_update` + `identity.unattributed` | **DROP** | `identity_unresolved` |
| `topo_update` + `identity.synthesized` | **DROP** | `identity_synthesized` |
| `ci_type=Alert` or `Change` | **DROP** | `never_ci_vertex` |
| `relation=CORRELATED_WITH` | **DROP** | `unknown_relation` |
| `metric_sample` lines | **NOOP** | Silent skip — Pillar A’s job (not counted as rejects) |
| `event` / `trace_span` / `anomaly` | **NOOP** | Silent skip — not map work; not `sketch.v1` either (see E2 cheat sheet) |

### Expected vs actual

| Check | Expected | Actual (test) |
|-------|----------|---------------|
| Distinct reject reasons | four codes listed in golden | sorted set equality |
| Reject count | 5 | `len(writer.rejects)` |
| Must not appear | alert-1, chg-1, synth-topo, unresolved-topo | absent from snapshot nodes |
| Bootstrap estate | five bootstrap CIs still present | all `ci_id`s still on snapshot |

---

## What is *not* in the golden spine

Illustrative single-object samples under [`expected/`](./expected/) (`graph_node.example.json`, …) remain **shape examples** for humans reading schemas. They are not the case goldens and are not asserted by `test_sample_io.py`.

Full publish under `poc/out/<tenant>/map/` after `make publish-map` still writes complete `graph_snapshot.json` / `nodes.jsonl` / `edges.jsonl` (including `discovered_via`). Spine equality is the PoC’s regression contract for “did we build the right estate map?”
