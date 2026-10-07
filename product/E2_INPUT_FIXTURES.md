# Post-E2 writer input fixtures — what Pillar A and Pillar B consume

**Audience:** Anyone wiring lab tests, replay scripts, or hand-off samples for the Pillar A sketch writer or the Pillar B graph writer.  
**Scope:** What the stream looks like **after E2 Identity** — `identity` already stamped.

**Status:** **Target wire** is [`writer_stream.v1`](./contracts/schemas/writer_stream_v1.schema.json) with **no `fact_kind`** — regulators fire on **optional blocks** ([`WRITER_REGULATOR.md`](./contracts/WRITER_REGULATOR.md)). Lab JSONL under `sample_estate/` may still use deprecated `ingest.v1` until fixtures migrate; PoC GraphWriter/SketchWriter code still filters that legacy shape. The pillar PoC **does not implement E1 Collect or E2 Identity**; fixtures simulate post-E2 traffic with `identity.status: resolved`. That stub is **not** the same as `identity.status: synthesized`, which both pillars **reject**.

**Doc tier:** Tier 2 implementer I/O (**I/O-2** in [`docs/observeops/OUR_HLD_TIER1.md`](../docs/observeops/OUR_HLD_TIER1.md)). Upstream wire: [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) (**I/O-1**). Pillar B output: [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md) (**I/O-3**).

---

## One wire format, two regulators (target)

After **E2 Identity**, every admitted Motadata writer line is **`writer_stream.v1`**. There is **no router enum**. GraphRegulator and SketchRegulator each look for **presence of optional blocks**.

| Stream shape | SketchRegulator (Pillar A) | GraphRegulator (Pillar B) | Other primary consumers |
|--------------|----------------------------|---------------------------|-------------------------|
| `metric` block present | Admit → `sketch_admit_intent` → `sketch.v1` | NOOP (unless `topology` also present) | **E6 Detect** · Lean/Federated structural |
| `topology` block present (`relation` + `src_ci_id` + `dst_ci_id`) | NOOP (unless `metric` also present) | Admit → `graph_write_intent` → `graph_edge.v1` | **E3 Topology** only |
| `anomaly` / `event` / `span` only | NOOP | NOOP | **E6–E10** · reference engines — see [presence cheat sheet](#writer-stream-presence-cheat-sheet) |
| Both `topology` and `metric` | **Both fire** | **Both fire** | Dual-write on one line is allowed |

Join key after bind: **`tenant` + CI id** on the stream ≡ **`entity_id`** on sketches ≡ graph node id on `map/` (`ci.ci_id` on `writer_stream.v1`; lab `ingest.v1` still says top-level `ci_id`).

Normative schemas: [`writer_stream_v1.schema.json`](./contracts/schemas/writer_stream_v1.schema.json) (target) · [`ingest_v1.schema.json`](./contracts/schemas/ingest_v1.schema.json) (deprecated lab).  
Reject reasons: [`IDENTIFIED_STREAM_REJECT.md`](./contracts/IDENTIFIED_STREAM_REJECT.md).  
Full E2 contract: [`LLD-E2-Identity.md`](../docs/observeops/LLD-E2-Identity.md).  
Ingest envelope overview: [`INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) §2.

---

## Writer-stream presence cheat sheet {#writer-stream-presence-cheat-sheet}

<a id="fact_kind-cheat-sheet"></a>

> **Hub note:** Older links to `#fact_kind-cheat-sheet` land here. **`fact_kind` is retired** for Motadata writer fan-out. Routing is **presence of optional blocks** on `writer_stream.v1`. Lab-only `ingest.v1` mapping is in [Legacy lab `ingest.v1`](#legacy-lab-ingestv1) below.

Every admitted **`writer_stream.v1`** line carries an envelope (`schema_version`, `ts`, `tenant`, `identity`) plus **zero or more** optional blocks. Regulators do **not** read a router string.

**Schema:** [`contracts/schemas/writer_stream_v1.schema.json`](./contracts/schemas/writer_stream_v1.schema.json) · **rules:** [`WRITER_REGULATOR.md`](./contracts/WRITER_REGULATOR.md)

```text
Optional blocks:  topology | metric | anomaly | event | span
```

### Who consumes each block

| Block present | Primary ObserveOps consumer(s) | Pillar A / B |
|---------------|--------------------------------|--------------|
| `metric` | **E4 Stores** (sketch history) · **E6 Detect** | **SketchRegulator admits** · GraphRegulator NOOP unless `topology` also present |
| `topology` | **E3 Topology** (`map/`) | SketchRegulator NOOP unless `metric` also present · **GraphRegulator admits** |
| `anomaly` | **E6 Detect** · **E7 Curate** | Both regulators **NOOP** |
| `event` | **E4 Stores** (evidence) · **E10 Identify** | Both regulators **NOOP** |
| `span` | **E9 Localize** · **E10 Identify** · future topology emitters | Both regulators **NOOP** — never invent edges from peer labels alone |

**Spine on every line:** `schema_version`, `ts`, `tenant`, `identity`. Subject CI usually under `ci` (`ci_id`, `ci_type`). Topology endpoints live under `topology.*` — not invented from `span` / `metric` labels ([WRITER_REGULATOR](./contracts/WRITER_REGULATOR.md) §2).

### Field cheat (by block)

| Block | Key fields |
|-------|------------|
| `metric` | `name`, `value`; optional labels / `trace_id` for exemplars |
| `topology` | `relation` (Fusion camelCase), `src_ci_id`, `dst_ci_id`; optional types / evidence |
| `anomaly` | `name`, `value`, `threshold`, `severity` |
| `event` | `name`, `value` (often `1.0`) |
| `span` | `name`, duration `value`; labels for trace / peers |

### Target examples (`writer_stream.v1`)

**1 · Metric (SketchRegulator)**

```json
{
  "schema_version": "writer_stream.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci": { "ci_id": "checkout-api", "ci_type": "Service" },
  "metric": {
    "name": "request.latency_ms",
    "value": 92.1,
    "labels": { "source": "lab-node", "trace_id": "abc123" }
  },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

**2 · Topology (GraphRegulator)**

```json
{
  "schema_version": "writer_stream.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci": { "ci_id": "checkout-api", "ci_type": "Service" },
  "topology": {
    "relation": "communicatesWith",
    "src_ci_id": "checkout-api",
    "dst_ci_id": "payments-db",
    "src_ci_type": "Service",
    "dst_ci_type": "Database",
    "evidenceSource": "discovery"
  },
  "identity": { "status": "resolved", "bind_source": "apm" }
}
```

Fusion camelCase → Motadata SCREAMING_SNAKE at Dest: [`RELATION_MAPPING.md`](./contracts/RELATION_MAPPING.md). Endpoint pairing: [`EDGE_TRIPLET_ALLOWLIST.md`](./contracts/EDGE_TRIPLET_ALLOWLIST.md).

**3 · Dual-fire (both blocks on one line)** — both regulators admit.

**4 · Span / event / anomaly only** — A/B writers NOOP; other stages may consume (see table above). Do **not** invent `topology` from `span.labels["peer.service"]` inside GraphWriter.

### Mixed stream (product intent)

```text
metric      →  SketchRegulator  →  history/
topology    →  GraphRegulator   →  map/
metric+topo →  both             →  history/ + map/
```

Lab mixed tape (still legacy `ingest.v1` until migrated): [`integration/sample_estate/customer_checkout/stream.resolved.jsonl`](./integration/sample_estate/customer_checkout/stream.resolved.jsonl).

### Reserved / future concerns (not writer blocks today)

Do **not** invent ad-hoc router strings. Future change / CMDB / ticket payloads join by `tenant` + CI id via ServiceOps — not as Alert vertices on `map/`.

| Concern | Intended consumer | Purpose |
|---------|-------------------|---------|
| Change feed | **E5 Maintain** · ServiceOps | Deploy / change correlation |
| CMDB sync | **E2 Identity** enrichment | Discovery overlay — same `ci_id` namespace |
| Ticket | **E11 Package** egress | ITSM record on shared keys |

---

## Legacy lab `ingest.v1` {#legacy-lab-ingestv1}

> **Deprecated for Motadata writer fan-out.** PoC code and `sample_estate` JSONL may still stamp **`fact_kind`**. Treat the table below as a **migration map** to presence blocks — not the target contract.

| Legacy `fact_kind` | Target `writer_stream.v1` block | Lab Pillar A | Lab Pillar B |
|--------------------|---------------------------------|--------------|--------------|
| `metric_sample` | `metric` | Admit | NOOP |
| `topo_update` | `topology` | NOOP | Admit |
| `anomaly` | `anomaly` | NOOP | NOOP |
| `event` | `event` | NOOP | NOOP |
| `trace_span` | `span` | NOOP | NOOP |

**Schema enum (lab only):** [`ingest_v1.schema.json`](./contracts/schemas/ingest_v1.schema.json) — `metric_sample | anomaly | event | trace_span | topo_update`.

### Legacy field cheat

| Legacy `fact_kind` | `name` usually means | Key fields beyond spine |
|--------------------|----------------------|-------------------------|
| `metric_sample` | Metric name | `value`; optional `labels.trace_id` |
| `topo_update` | Often omitted | `relation`, `src_ci_id`, `dst_ci_id` (snake_case Motadata names on lab wire) |
| `anomaly` | Monitor / metric that crossed | `value`, `threshold`, `severity` |
| `event` | Event / log type | `value` (often `1.0`) |
| `trace_span` | Span operation / route | `value` = duration (ms); peer labels |

Sample tape: [`ingestion-poc/vector/samples/ingest.v1.example.jsonl`](../ingestion-poc/vector/samples/ingest.v1.example.jsonl).

### Legacy examples (PoC fixtures still look like this)

#### 1 · `metric_sample`

**Typical emitters:** Prometheus scrape, OTLP metrics, ObserveOps corpus metric replay.

**Lab consumers:** Pillar A SketchWriter · **E6 Detect** · Lean/Federated structural.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.latency_ms",
  "value": 92.1,
  "labels": { "source": "lab-node", "trace_id": "abc123" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

Lab wave-1 metric names: `request.latency_ms`, `cpu.utilization_pct`. E4 aggregates many lines into one `sketch.v1` row — the line is not the sketch.

#### 2 · `topo_update`

**Typical emitters:** Topology crawler, catalog sync, discovery adapters.

**Lab consumers:** Pillar B GraphWriter only.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "communicates_with",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "payments-db",
  "identity": { "status": "resolved", "bind_source": "apm" }
}
```

PoC does **not** derive `relation` from `trace_span` — upstream must emit topology (legacy `topo_update` or target `topology` block).

#### 3 · `anomaly`

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:00Z",
  "tenant": "default",
  "ci_id": "orders-api",
  "ci_type": "Service",
  "fact_kind": "anomaly",
  "name": "http.error_rate",
  "value": 0.42,
  "threshold": 0.05,
  "severity": 8.4,
  "labels": { "layer": "app" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

#### 4 · `event`

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T09:59:58Z",
  "tenant": "default",
  "ci_id": "switch-core-01:GigE0/2",
  "ci_type": "NetworkPort",
  "fact_kind": "event",
  "name": "linkDown",
  "value": 1.0,
  "labels": { "proto": "snmp" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

#### 5 · `trace_span`

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:01Z",
  "tenant": "default",
  "ci_id": "orders-api",
  "ci_type": "Service",
  "fact_kind": "trace_span",
  "name": "POST /checkout",
  "value": 1200.0,
  "labels": {
    "route": "POST /checkout",
    "trace_id": "abc123",
    "span_id": "span-7",
    "peer.service": "inventory-api"
  },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

### Mixed JSONL (lab today)

```text
metric_sample  →  SketchWriter  →  history/
topo_update    →  GraphWriter   →  map/
```

Fixture: [`integration/sample_estate/customer_checkout/stream.resolved.jsonl`](./integration/sample_estate/customer_checkout/stream.resolved.jsonl).

Pretty-printed legacy reference (same file in all three fixture trees):

| Copy |
|------|
| [`pillar-a/poc/sample_estate/customer_checkout/expected/ingest.example.json`](./pillar-a/poc/sample_estate/customer_checkout/expected/ingest.example.json) |
| [`pillar-b/poc/sample_estate/customer_checkout/expected/ingest.example.json`](./pillar-b/poc/sample_estate/customer_checkout/expected/ingest.example.json) |
| [`integration/sample_estate/customer_checkout/expected/ingest.example.json`](./integration/sample_estate/customer_checkout/expected/ingest.example.json) |

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.latency_ms",
  "value": 92.1,
  "labels": { "source": "lab-node" },
  "identity": {
    "status": "resolved",
    "bind_source": "topology_lookup",
    "aliases": ["svc:checkout-api"]
  }
}
```

---

## Side by side — lab fixtures still on `ingest.v1`

Both lines are valid post-E2 **legacy** records. Pass both in one JSONL for integration tests; each pillar keeps only its class. Target equivalents use `metric` / `topology` blocks — [presence cheat sheet](#writer-stream-presence-cheat-sheet).

### Pillar A — `metric_sample` (sketch input)

From [`pillar-a/poc/sample_estate/customer_checkout/stream.metrics.resolved.jsonl`](./pillar-a/poc/sample_estate/customer_checkout/stream.metrics.resolved.jsonl):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.latency_ms",
  "value": 92.1,
  "labels": { "source": "lab-node" },
  "identity": {
    "status": "resolved",
    "bind_source": "topology_lookup",
    "aliases": ["svc:checkout-api"]
  }
}
```

**Writer expects:** `identity.status` = `resolved`; wave-1 metric names (`request.latency_ms`, `cpu.utilization_pct` in the lab).  
**Output room:** `history/` → `sketch.v1`.

### Pillar B — `topo_update` (edge input)

From [`pillar-b/poc/sample_estate/customer_checkout/stream.resolved.jsonl`](./pillar-b/poc/sample_estate/customer_checkout/stream.resolved.jsonl):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "communicates_with",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "payments-db",
  "identity": {
    "status": "resolved",
    "bind_source": "apm"
  }
}
```

**Writer expects:** `relation`, `src_ci_id`, `dst_ci_id`, `identity.status` = `resolved`; Motadata catalog relation (fifteen names; pairing via [`EDGE_TRIPLET_ALLOWLIST.md`](./contracts/EDGE_TRIPLET_ALLOWLIST.md)).  
**Output room:** `map/` → `graph_edge.v1` inside `GraphSnapshot`.  
**Also load:** [`pillar-b/poc/sample_estate/customer_checkout/topology.bootstrap.json`](./pillar-b/poc/sample_estate/customer_checkout/topology.bootstrap.json) for declared bootstrap nodes and edges before streaming updates.

Pillar B **does not infer** edges from spans inside the PoC — the relationship must already be explicit (`topology` block on target wire, or legacy `topo_update` / seed topology).

---

## Fixture file map

```text
pillar-ab-implementation/
├── pillar-a/poc/sample_estate/customer_checkout/
│   ├── expected/ingest.example.json     ← legacy five-class examples (pretty)
│   ├── stream.metrics.resolved.jsonl    ← Pillar A happy path (metric only)
│   ├── stream.resolved.jsonl            ← same as metrics file (alias)
│   └── stream.reject.jsonl              ← negative cases for A gate
├── pillar-b/poc/sample_estate/customer_checkout/
│   ├── expected/ingest.example.json
│   ├── topology.bootstrap.json               ← declared estate bootstrap (not from E2)
│   ├── stream.resolved.jsonl            ← Pillar B happy path (topo only)
│   └── stream.reject.jsonl              ← negative cases for B gate
└── integration/sample_estate/customer_checkout/
    ├── expected/ingest.example.json
    ├── stream.resolved.jsonl            ← mixed metric + topo (read-join harness)
    ├── stream.reject.jsonl
    └── topology.bootstrap.json
```

| File | Use when |
|------|----------|
| `pillar-a/.../stream.metrics.resolved.jsonl` | Unit tests and `make publish-map` (alias: `make flush`) for Pillar A only |
| `pillar-b/.../stream.resolved.jsonl` | Unit tests and `python -m graph.cli_publish_map` for Pillar B only |
| `integration/.../stream.resolved.jsonl` | After both pillars are green — WorkingSet read-join demo |
| `*/stream.reject.jsonl` | Gate tests: unresolved, synthesized, never-CI types, unknown relations |

Mixed metric + topo in one file is **fixture packaging** for the A+B demo, not a claim that sketches store edges. See [`contracts/GRAPH_QNA.md`](./contracts/GRAPH_QNA.md) G31.

---

## Identity overlay — what E2 adds

Same line as E1, plus:

```json
"identity": {
  "status": "resolved",
  "bind_source": "topology_lookup",
  "aliases": ["monitor-88", "svc:checkout-api"]
}
```

| `identity.status` | Pillar A / B writers | Meaning |
|-------------------|----------------------|---------|
| `resolved` | **Admit** | Bind succeeded; safe join key for production sketch and map writes |
| `unattributed` | **Reject** (`identity_unresolved`) | No CI mapping; kept on unattributed queue upstream, not in map/sketch |
| `synthesized` | **Reject** (`identity_synthesized`) | Placeholder CI for visibility; not an E9 localize or ticket target |

Lab happy-path fixtures use **`resolved` only**. Negative tapes in `stream.reject.jsonl` exercise the other statuses.

---

## Real pipeline vs lab stub

```text
TARGET (Motadata writer fan-out):
  E1 Collect  →  E2 Identity  →  writer_stream.v1 (+ identity)
                                      ├─ metric block     →  SketchRegulator  →  history/
                                      └─ topology block   →  GraphRegulator   →  map/
                                      (both blocks on one line → both fire)

LAB PoC (what exists today until fixtures migrate):
  sample_estate/customer_checkout/stream.*.jsonl   ← hand-authored as if E2 already ran
       ├─ fact_kind=metric_sample  →  SketchWriter
       └─ fact_kind=topo_update    →  GraphWriter (+ topology.bootstrap.json)
```

Shared stub code both pillars import: `poc/ab_shared/identity_gate.py` (`ResolvedOnlyGate`), `ingest_source.py` (`JsonlIngestSource`).

---

## Upstream replay samples (optional, separate from lab fixtures)

Corpus-scale streams under `datasets/ingest_samples/` come from ingestion PoC converters. They may **lack** the full `identity` overlay — those are E1-ish replay outputs, not the pillar lab checkout tapes.

| Suite | Path pattern |
|-------|----------------|
| ObserveOps replay | `datasets/ingest_samples/observeops-replay/UC-*/stream.jsonl` |
| Motadata ingest | `datasets/ingest_samples/motadata-ingest/incidents/*/stream.jsonl` |

To feed pillar writers from replay, add an E2-normalize step (or hand-stamp `identity.status: resolved`) so lines match the shapes above.

---

## Related

| Doc | Topic |
|-----|--------|
| [`docs/observeops/OUR_HLD_TIER1.md`](../docs/observeops/OUR_HLD_TIER1.md) | Tier 1 vs Tier 2; implementer I/O chain I/O-1 … I/O-4 |
| [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) | E1 envelope (**I/O-1**); links here for post-E2 examples |
| [`contracts/WRITER_REGULATOR.md`](./contracts/WRITER_REGULATOR.md) | Target fan-out — presence predicates, no `fact_kind` |
| [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md) | Pillar B `map/` output keys after GraphWriter flush (**I/O-3**) |
| [`docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) | Pillar A `history/` sketch output (**I/O-4**) |
| [`scope/MOTADATA_3PILLARS_MERGED_SCOPE.md`](./scope/MOTADATA_3PILLARS_MERGED_SCOPE.md) §B5–B6 | What we expect from E1 and E2 |
| [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) | Phase 0 fixtures and parallel writers |
| [`discussion/04-raw-data-identity-lut-open-questions.md`](./discussion/04-raw-data-identity-lut-open-questions.md) | LUT misses, quarantine, synthesized vs resolved policy |
