# Writer regulator — post-E2 fan-out (no `fact_kind`)

**Status:** Supersedes `ingest.v1` + `fact_kind` admit routing for Motadata writer microservices.  
**Wire:** [`schemas/writer_stream_v1.schema.json`](./schemas/writer_stream_v1.schema.json)  
**Intents:** [`schemas/graph_write_intent_v1.schema.json`](./schemas/graph_write_intent_v1.schema.json) · [`schemas/sketch_admit_intent_v1.schema.json`](./schemas/sketch_admit_intent_v1.schema.json)  
**Relation map:** [`RELATION_MAPPING.md`](./RELATION_MAPPING.md)  
**References:** Fusion/OneOps SKG edge spec + CI ontology under `pillar-b/reference/`

---

## 1. Why this exists

Post-E2 there is **no stage that stamps a router enum** (`fact_kind`). Collect / adapters emit a **common JSON stream**. Each writer microservice runs a **regulator (orchestrator)** that:

1. Reads `writer_stream.v1`.
2. Decides whether this writer should care (**presence predicates** on optional blocks).
3. Projects a **writer-specific intent** object.
4. Hands that intent to the writer (GraphWriter / SketchWriter / …).

```text
                writer_stream.v1   (common, no fact_kind)
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  GraphRegulator   SketchRegulator   (future…)
         │               │
         ▼               ▼
 graph_write_intent  sketch_admit_intent
         │               │
         ▼               ▼
    GraphWriter      SketchWriter
```

One stream line **may** carry both `topology` and `metric` blocks. **Both regulators fire.** Topology change is handled by GraphWriter; metrics by SketchWriter.

---

## 2. GraphRegulator

### Admit predicate (MUST)

Admit iff **all** of:

1. `identity.status === "resolved"`.
2. `topology` object is present.
3. `topology.relation`, `topology.src_ci_id`, `topology.dst_ci_id` are non-empty.
4. `topology.relation` is one of the Fusion **eleven** stored camelCase types (schema enum).

Otherwise: **NOOP** (no `graph_write_intent`). Do **not** DROP for “wrong fact kind” — there is no fact kind. Unknown relation → reject/quarantine at GraphWriter or regulator (product choice); schema validation should catch it at the boundary.

### Explicit non-admits (teaching locks)

| Shape | GraphRegulator |
|-------|----------------|
| `metric` only, even with `labels.peer.service` | **NOOP** — never invent `communicatesWith` |
| `span` only with peer labels | **NOOP** — upstream must emit a `topology` block |
| `event` / `anomaly` only | **NOOP** |
| `topology` present but `identity.status` ≠ `resolved` | **NOOP** (MUST) |

### Projection → `graph_write_intent.v1`

Copy / normalize:

| Intent field | From stream |
|--------------|-------------|
| `tenant`, `ts` | envelope |
| `relation`, `src_ci_id`, `dst_ci_id` | `topology.*` |
| `src_ci_type`, `dst_ci_type` | `topology.*` when present |
| `evidenceSource`, `confidence`, `lastObserved`, `ttl` | `topology.*` (default `evidenceSource` if omitted: product default, e.g. `discovery`) |
| `lifecycleSubtype`, `attributes` | `topology.*` when present |
| `identity` | envelope (`status` must be `resolved`) |

Dest publish still maps camelCase → Motadata `graph_edge.v1` SCREAMING_SNAKE via [`RELATION_MAPPING.md`](./RELATION_MAPPING.md) until Dest schemas are refreshed.

**Endpoint pairing:** GraphWriter (and GraphRegulator when wired) hard-rejects illegal `(src_type, relation, dst_type)` triplets — [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md).

---

## 3. SketchRegulator

### Admit predicate (this pass)

Admit when `metric` is present with:

- numeric `metric.value`, and  
- non-empty `metric.metric_id` **or** `metric.name`.

Subject CI: `ci.ci_id` (required for a useful admit; if missing, NOOP or quarantine — SketchWriter existing behavior).

**Deferred:** finer rules (skip when only topo, identity gates for sketches, etc.). Operator lock: do not block GraphWriter contracts on sketch edge cases.

### Projection → `sketch_admit_intent.v1`

| Intent field | From stream |
|--------------|-------------|
| `tenant`, `ts`, `identity` | envelope |
| `ci_id`, `ci_type` | `ci.*` |
| `metric_id` | `metric.metric_id` else `metric.name` |
| `value`, `labels` | `metric.*` |

---

## 4. Other blocks (`event`, `span`, `anomaly`)

Carried on `writer_stream.v1` for downstream Detect / Diagnose / evidence stores. **Neither** GraphRegulator nor SketchRegulator admits them in this pass. They do not become edges or sketch rows via these two writers.

---

## 5. Supersession of `ingest.v1` / `fact_kind`

| Old | New |
|-----|-----|
| `ingest.v1` + required `fact_kind` | `writer_stream.v1` + optional blocks |
| GraphWriter filters `fact_kind == topo_update` | GraphRegulator filters on `topology` triple |
| SketchWriter filters `fact_kind == metric_sample` | SketchRegulator filters on `metric` block |
| Snake_case ingest `relation` (`runs_on`) | Canonical wire `relation` camelCase (`runsOn`) |

Lab fixtures and the stream→graph demo still mention `fact_kind` until migrated. Treat those as **legacy teaching**; new writer work targets `writer_stream.v1`.

---

## 6. Examples

### Topology-only (GraphRegulator fires)

```json
{
  "schema_version": "writer_stream.v1",
  "ts": "2026-08-20T03:29:50Z",
  "tenant": "default",
  "identity": { "status": "resolved", "bind_source": "inventory" },
  "ci": { "ci_id": "app-runtime-jvm", "ci_type": "Runtime" },
  "topology": {
    "relation": "runsOn",
    "src_ci_id": "app-runtime-jvm",
    "dst_ci_id": "linux-server-app-01",
    "evidenceSource": "agent",
    "confidence": 0.95
  }
}
```

### Metric + topology on one line (both regulators fire)

```json
{
  "schema_version": "writer_stream.v1",
  "ts": "2026-08-20T03:30:08Z",
  "tenant": "default",
  "identity": { "status": "resolved", "bind_source": "service-catalog" },
  "ci": { "ci_id": "checkout-api", "ci_type": "Service" },
  "topology": {
    "relation": "dependsOn",
    "src_ci_id": "checkout-api",
    "dst_ci_id": "payments-db",
    "evidenceSource": "iac",
    "confidence": 0.85
  },
  "metric": {
    "name": "request.latency_ms",
    "value": 92.1,
    "labels": { "trace_id": "abc123" }
  }
}
```

### Span without topology (GraphRegulator NOOP)

```json
{
  "schema_version": "writer_stream.v1",
  "ts": "2026-08-20T03:30:10Z",
  "tenant": "default",
  "identity": { "status": "resolved", "bind_source": "apm" },
  "ci": { "ci_id": "checkout-api", "ci_type": "Service" },
  "span": {
    "name": "POST /checkout",
    "value": 210.0,
    "labels": { "trace_id": "abc123", "peer.service": "payments-db" }
  }
}
```
