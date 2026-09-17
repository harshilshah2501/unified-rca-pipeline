# P1 map fabric eval — E1–E5 (Increment 1)

**Doc job:** Increment 1 **eval contract** — stage matrix (map lens), terminology, proofs and honest gaps.  
**Not this page:** file-by-file code tour → [`Codebase-go-through.md`](./Codebase-go-through.md). Package I/O front door → [`../README.md`](../README.md). Doc map → [`README.md`](./README.md).

**Scope:** Always-on fabric only — how Collect → Identity → GraphWriter → `map/` (plus Maintain) behaves for the knowledge-graph PoC.  
**Not in this guide:** P2/P3 case-path map reads (CaseSeed → WorkingSet → leaf path). That is the next increment.

**Run proofs:**

```bash
cd pillar-ab-implementation/pillar-b/poc
make test-all
# includes graph/tests/unit/test_p1_map_fabric.py
```

---

## Terminology (do not blur)

| Term | Meaning | Not |
|------|---------|-----|
| **Estate bootstrap** (`topology.bootstrap.json`, `GraphWriter.load_estate_bootstrap`) | Optional lab/CMDB-style **starting map** before the `topo_update` stream | Not E7 CaseSeed |
| **`topo_update` stream** | Continuous Motadata map WRITE path after E2 Identity | — |
| **CaseSeed** | P2 · E7 Curate tip for Scope | Does **not** write `map/` |
| **Admit** | Per-line decision a writer makes when an `ingest.v1` record arrives: what to do with *this* line | Not “admission control” / authn; not Collect wire validation; not “the line was accepted into Motadata” |

**Admit (GraphWriter sense), in one sentence:** for each stream line, GraphWriter chooses **NOOP**, **WRITE**, or **DROP** (plus phased skip) — that choice *is* “admit.” Hub tab name “Admit” means this outcome table, not a separate product stage.

Spine for E3: **optional estate bootstrap + `topo_update` → nodes/edges + provenance → `GraphSnapshot` publish**.

---

## Stage matrix (map lens)

| Stage | Map interaction | PoC proof | Honest gap |
|-------|-----------------|-----------|------------|
| **E1 Collect** | **None** — wire admit only; does not write or read `map/` | Fixture lines carry `schema_version=ingest.v1` + known `signal_class` spine; GraphWriter never “Collect-rejects” | Live Collect Done elsewhere; Pillar B **simulates** post-E2 |
| **E2 Identity** | **Gate into writers** — `ResolvedOnlyGate`; Design: read `telemetry_key_index` | Unresolved / synthesized `topo_update` → **DROP** (reject tape); never silent map write | Full LUT + unresolved→discovery feedback = Design |
| **E3 Topology** | **Sole `map/` writer** | NOOP / WRITE / DROP / phased skip / upsert idempotency (below) | Live continuous discovery = Design; PoC = bootstrap + stream upsert |
| **E4 Stores** | **Orthogonal** — Pillar A `history/` sketches | Mixed tape leaves map spine unchanged for metric/event/trace/anomaly | Log/trace history ≠ `sketch.v1` |
| **E5 Maintain** | **Validity on existing edges** — does not create edges | Expire `valid_to`; stale corroborating; declared soft 7d / hard 30d (Design-numeric, fixture clock) | Full discovery re-derive = Design |

---

## E3 GraphWriter admit outcomes

**Reminder — “admit” here:** not a pipeline stage and not “user was allowed in.” It is GraphWriter’s **per-line triage** after Identity: skip quietly (NOOP), mutate the map (WRITE), or reject with a code (DROP). The hub step labeled *Admit* is this table.

Aligned with hub Admit language and [`../README.md`](../README.md):

| Outcome | When | Effect |
|---------|------|--------|
| **NOOP** | `signal_class` ≠ `topo_update` | No state change, no reject row |
| **WRITE** | Resolved identity + CI vertex + wave-1 relation emit | Upsert node(s) + edge → flush `map/` |
| **DROP** | Unresolved/synthesized identity; never-CI type; unknown relation | Append `writer.rejects`; map unchanged |
| **Phased map-NOOP** | Catalog relation not in wave-1 (e.g. `mounts`) | No write; usually not a DROP |
| **Upsert idempotency** | Same resolved `topo_update` replayed | Same `edge_id` replace key; no duplicate edges |

Wave-1 emit set: `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`.

**E1 vs E3 reject boundary:** unknown / reserved `signal_class` on the wire is a **Collect** concern. GraphWriter treats non-`topo_update` as **NOOP**, not DROP. Do not count Collect rejects as GraphWriter DROPs.

---

## Fixtures and acceptance

| Artifact | Role |
|----------|------|
| [`poc/fixtures/lab_checkout/topology.bootstrap.json`](./poc/fixtures/lab_checkout/topology.bootstrap.json) | Estate bootstrap |
| [`poc/fixtures/lab_checkout/stream.resolved.jsonl`](./poc/fixtures/lab_checkout/stream.resolved.jsonl) | Case A WRITE spine |
| [`poc/fixtures/lab_checkout/stream.reject.jsonl`](./poc/fixtures/lab_checkout/stream.reject.jsonl) | Case B DROP + NOOP mix |
| [`poc/fixtures/lab_checkout/SAMPLE_IO.md`](./poc/fixtures/lab_checkout/SAMPLE_IO.md) | Expected vs actual |

---

## Design stubs called out in code/docs

- **`telemetry_key_index`** — Identity→graph join surface (LLD-E2); PoC does not implement the LUT.
- **Live discovery crawler** — Motadata E3 continuous path; PoC uses bootstrap + `topo_update` upsert only.
- **Declared 7d / 30d clocks** — product defaults from operational graph; PoC injects them as labeled Design-numeric constants in [`../poc/graph/maintain.py`](../poc/graph/maintain.py).

---

## Related

- Doc map: [`README.md`](./README.md)  
- Package I/O: [`../README.md`](../README.md)  
- Code tour: [`Codebase-go-through.md`](./Codebase-go-through.md)  
- Hub: [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter)  
- LLD-E3: [`../../../docs/observeops/LLD-E3-Topology.md`](../../../docs/observeops/LLD-E3-Topology.md)  
- LLD-E5 stub: [`../../../docs/observeops/LLD-E5-Maintain.md`](../../../docs/observeops/LLD-E5-Maintain.md)  
- Map contract (slice SoT): [`../../contracts/MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md)
