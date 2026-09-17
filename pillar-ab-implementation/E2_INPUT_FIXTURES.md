# Post-E2 ingest fixtures — what Pillar A and Pillar B consume

**Audience:** Anyone wiring lab tests, replay scripts, or hand-off samples for the Pillar A sketch writer or the Pillar B graph writer.  
**Scope:** The **`ingest.v1`** JSON lines that look like **E2 Identity output** — the stream both pillars read after Collect and Identity have already run upstream.

**Status:** The pillar PoC **does not implement E1 Collect or E2 Identity**. Lab fixtures **simulate** post-E2 traffic by shipping lines with `identity.status: resolved` already stamped. That stub is what people often call “synthesized input” in lab conversation — it is **not** the same as `identity.status: synthesized`, which real E2 may emit on lookup-table misses and which both pillars **reject**.

**Doc tier:** Tier 2 implementer I/O (**I/O-2** in [`docs/observeops/OUR_HLD_TIER1.md`](../docs/observeops/OUR_HLD_TIER1.md)). Upstream wire spec: [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) (**I/O-1**). Pillar B output: [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md) (**I/O-3**).

---

## One wire format, two writer filters

After **E2 Identity (Normalize)**, every admitted line is still **`ingest.v1`**. E2 adds an **`identity`** object on the same object — not a second on-wire format.

**Pillar A (E4 sketch writer)** and **Pillar B (E3 graph writer)** read the **same stream shape**. They differ only by **`signal_class`** (two consumers on the fabric path — full consumer map in [`signal_class` cheat sheet](#signal_class-cheat-sheet)):

| `signal_class` | Pillar A | Pillar B | Other primary consumers (not A/B) |
|----------------|----------|----------|-----------------------------------|
| `metric_sample` | Admit → `sketch.v1` | Silent skip | **E6 Detect** · Lean/Federated structural |
| `topo_update` | Silent skip | Admit → `graph_edge.v1` | **E3 Topology** only |
| `anomaly`, `event`, `trace_span`, … | Skip | Skip | **E6–E10** · reference engines — see cheat sheet |

Join key after bind: **`tenant` + `ci_id`** on ingest ≡ **`entity_id`** on sketches ≡ graph node id on `map/`.

Normative schema: [`contracts/schemas/ingest_v1.schema.json`](./contracts/schemas/ingest_v1.schema.json).  
Reject reasons when identity or catalog checks fail: [`contracts/IDENTIFIED_STREAM_REJECT.md`](./contracts/IDENTIFIED_STREAM_REJECT.md).  
Full E2 contract (production): [`docs/observeops/LLD-E2-Identity.md`](../docs/observeops/LLD-E2-Identity.md).  
Ingest envelope overview: [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) §2.

---

## `signal_class` cheat sheet

Every admitted **`ingest.v1`** line carries **`signal_class`** as a snake_case string. It routes the row — like declaring what *kind* of fact the line is. It is **not** a separate object and **not** MELTS or RED on the wire (RED metrics arrive as many **`metric_sample`** lines).

**Schema enum (writers + PoC):** [`contracts/schemas/ingest_v1.schema.json`](./contracts/schemas/ingest_v1.schema.json)

```text
metric_sample | anomaly | event | trace_span | topo_update
```

**Reserved (do not emit):** `change_event`, `cmdb_sync`, `ticket` — see [Reserved classes](#reserved-signal_class-values) below.

### Who consumes each class

`signal_class` is the **router label** on the shared `ingest.v1` stream. After E2 Identity, different pipeline stages (and reference engines) subscribe to different classes. Pillar A and Pillar B are only two consumers on the Motadata fabric path.

| `signal_class` | Primary ObserveOps consumer(s) | Reference / PoC implementation | Pillar A / B PoC |
|----------------|--------------------------------|--------------------------------|------------------|
| `metric_sample` | **E4 Stores** (sketch history) · **E6 Detect** (evaluate samples vs baseline / threshold) | Pillar A `SketchWriter` · `ingestion-poc/detect/threshold_detect.py` (recomputes from samples; ignores pre-baked `anomaly`) · Lean + Federated **structural** tier · Federated `metric_slice.jsonl` | **Pillar A admits** · Pillar B skips |
| `topo_update` | **E3 Topology** (graph edges on `map/`) | Pillar B `GraphWriter` · corpus `topology.json` (primary seed in lab) · `topo_updates.jsonl` audit fan-out · Lean **A-TOPO** refresh | Pillar A skips · **Pillar B admits** |
| `anomaly` | **E6 Detect** · **E7 Curate** (when signal already marked) | ObserveOps replay may pre-tag crossings · Lean **A-ANOM** · Federated structural + **speed** tier · shared Detect may **ignore** these when recomputing from `metric_sample` | Both pillars **skip** |
| `event` | **E4 Stores** (evidence history) · **E10 Identify** (log / event corroboration) | Lean **A-EVT** bundle writer · Federated structural + speed tier | Both pillars **skip** |
| `trace_span` | **E9 Localize** · **E10 Identify** (error leaf / self-time evidence) | Federated **Nezha / speed tier** (required — `tg:` / `pc:` pattern keys) · structural tier · future adapters may emit `topo_update` (not in Pillar B PoC today) | Both pillars **skip** |

Normative stage map (E1 view): [`docs/observeops/LLD-E1-Collect.md`](../docs/observeops/LLD-E1-Collect.md) §2.1. Fabric writer filter rules: [`contracts/GRAPH_QNA.md`](./contracts/GRAPH_QNA.md) G31.

**Spine on every line:** `schema_version`, `ts`, `tenant`, `ci_id`, `ci_type`, `signal_class`. After E2 add **`identity`**. Unknown `signal_class` → **E1 Collect** reject / dead-letter (do not guess).

### Field cheat (by class)

| `signal_class` | `name` usually means | Key fields beyond spine |
|----------------|----------------------|-------------------------|
| `metric_sample` | Metric name | `value`; optional `labels.trace_id` for exemplars |
| `topo_update` | Often omitted | `relation`, `src_ci_id`, `dst_ci_id` |
| `anomaly` | Monitor / metric that crossed | `value`, `threshold`, `severity` |
| `event` | Event / log type | `value` (often `1.0`) |
| `trace_span` | Span operation / route | `value` = duration (ms); `labels` for trace ids / peers |

Sample tape with multiple classes: [`ingestion-poc/vector/samples/ingest.v1.example.jsonl`](../ingestion-poc/vector/samples/ingest.v1.example.jsonl).

### 1 · `metric_sample`

**Typical emitters:** Prometheus scrape, OTLP metrics, ObserveOps corpus metric replay, Motadata numeric export.

**Consumers:** **E4 Stores** → Pillar A aggregates into `sketch.v1` in `history/` · **E6 Detect** reads sketch baselines or live samples · Lean/Federated structural sinks for evaluation engines (not the Motadata pillar path).

One numeric measurement after bind. Pillar A lab input.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "metric_sample",
  "name": "request.latency_ms",
  "value": 92.1,
  "labels": { "source": "lab-node", "trace_id": "abc123" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

Lab wave-1 metric names: `request.latency_ms`, `cpu.utilization_pct`. E4 aggregates many lines into one `sketch.v1` row — the line is not the sketch.

### 2 · `topo_update`

**Typical emitters:** Topology crawler audit fan-out, service-catalog sync, future discovery adapters (inventory / APM → explicit edge).

**Consumers:** **E3 Topology only** → Pillar B `GraphWriter` → `graph_edge.v1` on `map/`. E1 Collect and E4 sketch writer **do not** act on these lines ([`LLD-E1-Collect.md`](../docs/observeops/LLD-E1-Collect.md) §4).

One explicit relationship. Pillar B lab input.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "topo_update",
  "relation": "communicates_with",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "payments-db",
  "identity": { "status": "resolved", "bind_source": "apm" }
}
```

PoC does **not** derive `relation` from `trace_span` — upstream must emit `topo_update` (or use seed topology).

### 3 · `anomaly`

**Typical emitters:** Replay converter pre-tags threshold crossings; optional Vector transform detect (live path often defers to E6).

**Consumers:** **E6 Detect** · **E7 Curate** · Lean **A-ANOM** · Federated speed/structural tiers. Shared `threshold_detect.py` may **skip** pre-baked `anomaly` rows when recomputing from `metric_sample`. **Not** consumed by Pillar A/B writers.

Pre-marked threshold crossing.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:00Z",
  "tenant": "default",
  "ci_id": "orders-api",
  "ci_type": "Service",
  "signal_class": "anomaly",
  "name": "http.error_rate",
  "value": 0.42,
  "threshold": 0.05,
  "severity": 8.4,
  "labels": { "layer": "app" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

### 4 · `event`

**Typical emitters:** Log lines, SNMP traps, structured syslog, Motadata alert/export events.

**Consumers:** **E4 Stores** (evidence retention) · **E10 Identify** (corroboration — e.g. log patterns vs fault signatures) · Lean **A-EVT** · Federated structural + speed tier. **Not** Pillar A/B PoC writers.

Discrete log / SNMP / alert-style occurrence.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T09:59:58Z",
  "tenant": "default",
  "ci_id": "switch-core-01:GigE0/2",
  "ci_type": "NetworkPort",
  "signal_class": "event",
  "name": "linkDown",
  "value": 1.0,
  "labels": { "proto": "snmp" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

### 5 · `trace_span`

**Typical emitters:** OTLP/Jaeger/Zipkin replay, Datadog-style APM span export.

**Consumers:** **E9 Localize** · **E10 Identify** (deepest error leaf, self-time) · Federated **Nezha / speed tier** (required for call-graph keys). Peer labels (`peer.service`, etc.) are **inputs to future** `topo_update` emitters — Pillar B PoC does **not** consume spans directly.

One span with duration.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:01Z",
  "tenant": "default",
  "ci_id": "orders-api",
  "ci_type": "Service",
  "signal_class": "trace_span",
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

### Mixed JSONL (integration lab)

One file may interleave classes; each pillar filters by `signal_class`:

```text
metric_sample  →  SketchWriter  →  history/
metric_sample  →  SketchWriter  →  history/
topo_update    →  GraphWriter   →  map/
```

Fixture: [`integration/fixtures/lab_checkout/stream.resolved.jsonl`](./integration/fixtures/lab_checkout/stream.resolved.jsonl).

### Reserved `signal_class` values

Do **not** emit in the current pass. E1 rejects unknown classes.

| Class | Intended future consumer | Purpose |
|-------|--------------------------|---------|
| `change_event` | **E5 Maintain** · ServiceOps change correlation | Deploy / change feed |
| `cmdb_sync` | **E2 Identity** enrichment · optional CMDB overlay | Discovery snapshot or delta — same `ci_id` namespace |
| `ticket` | **E11 Package** egress · ServiceOps join | ITSM / incident record on shared `tenant` + `ci_id` |

See [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) §2.1 · [`docs/observeops/LLD-E1-Collect.md`](../docs/observeops/LLD-E1-Collect.md) §2.2.

---

Pretty-printed reference (same file in all three fixture trees):

| Copy |
|------|
| [`pillar-a/poc/fixtures/lab_checkout/expected/ingest.example.json`](./pillar-a/poc/fixtures/lab_checkout/expected/ingest.example.json) |
| [`pillar-b/poc/fixtures/lab_checkout/expected/ingest.example.json`](./pillar-b/poc/fixtures/lab_checkout/expected/ingest.example.json) |
| [`integration/fixtures/lab_checkout/expected/ingest.example.json`](./integration/fixtures/lab_checkout/expected/ingest.example.json) |

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "metric_sample",
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

## Side by side — one metric line and one topology line

Both lines are valid post-E2 **`ingest.v1`** records. Pass both in one JSONL file for integration tests; each pillar keeps only its class.

### Pillar A — `metric_sample` (sketch input)

From [`pillar-a/poc/fixtures/lab_checkout/stream.metrics.resolved.jsonl`](./pillar-a/poc/fixtures/lab_checkout/stream.metrics.resolved.jsonl):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "metric_sample",
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

From [`pillar-b/poc/fixtures/lab_checkout/stream.resolved.jsonl`](./pillar-b/poc/fixtures/lab_checkout/stream.resolved.jsonl):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "topo_update",
  "relation": "communicates_with",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "payments-db",
  "identity": {
    "status": "resolved",
    "bind_source": "apm"
  }
}
```

**Writer expects:** `relation`, `src_ci_id`, `dst_ci_id`, `identity.status` = `resolved`; wave-1 relation names (`runs_on`, `depends_on`, `communicates_with`, `part_of`, `hosted_on` in the lab).  
**Output room:** `map/` → `graph_edge.v1` inside `GraphSnapshot`.  
**Also load:** [`pillar-b/poc/fixtures/lab_checkout/topology.seed.json`](./pillar-b/poc/fixtures/lab_checkout/topology.seed.json) for declared baseline nodes and edges before streaming updates.

Pillar B **does not infer** `relation` from spans inside the PoC — the relationship must already be explicit on the `topo_update` line (or in seed topology). Upstream adapters or future E3 derivation produce those lines.

---

## Fixture file map

```text
pillar-ab-implementation/
├── pillar-a/poc/fixtures/lab_checkout/
│   ├── expected/ingest.example.json     ← canonical pretty example
│   ├── stream.metrics.resolved.jsonl    ← Pillar A happy path (metric only)
│   ├── stream.resolved.jsonl            ← same as metrics file (alias)
│   └── stream.reject.jsonl              ← negative cases for A gate
├── pillar-b/poc/fixtures/lab_checkout/
│   ├── expected/ingest.example.json
│   ├── topology.seed.json               ← declared graph seed (not from E2)
│   ├── stream.resolved.jsonl            ← Pillar B happy path (topo only)
│   └── stream.reject.jsonl              ← negative cases for B gate
└── integration/fixtures/lab_checkout/
    ├── expected/ingest.example.json
    ├── stream.resolved.jsonl            ← mixed metric + topo (read-join harness)
    ├── stream.reject.jsonl
    └── topology.seed.json
```

| File | Use when |
|------|----------|
| `pillar-a/.../stream.metrics.resolved.jsonl` | Unit tests and `make flush` for Pillar A only |
| `pillar-b/.../stream.resolved.jsonl` | Unit tests and `python -m graph.cli_flush` for Pillar B only |
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
PRODUCTION (not built inside pillar-a/ or pillar-b/ packages):
  E1 Collect  →  E2 Identity  →  post-E2 ingest.v1 JSONL (+ identity overlay)
                                      ├─ metric_sample  →  Pillar A  →  history/
                                      └─ topo_update    →  Pillar B  →  map/

LAB PoC (what exists today):
  fixtures/lab_checkout/stream.*.jsonl   ← hand-authored as if E2 already ran
       ├─ metric lines  →  SketchWriter
       └─ topo lines    →  GraphWriter (+ topology.seed.json)
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
| [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) | E1 envelope, delivery options, identity overlay (**I/O-1**); links here for `signal_class` examples |
| [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md) | Pillar B `map/` output keys after GraphWriter flush (**I/O-3**) |
| [`docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) | Pillar A `history/` sketch output (**I/O-4**) |
| [`scope/MOTADATA_3PILLARS_MERGED_SCOPE.md`](./scope/MOTADATA_3PILLARS_MERGED_SCOPE.md) §B5–B6 | What we expect from E1 and E2 |
| [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) | Phase 0 fixtures and parallel writers |
| [`discussion/04-raw-data-identity-lut-open-questions.md`](./discussion/04-raw-data-identity-lut-open-questions.md) | LUT misses, quarantine, synthesized vs resolved policy |
