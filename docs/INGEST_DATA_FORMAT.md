# Ingest Data Format — What to Provide (Frozen Corpus PoC)

**Audience:** Data owners preparing logs, metrics, traces for ingestion PoC  
**Tier:** Tier 2 implementer I/O (**I/O-1**) — see [`observeops/OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md). Pillar lab fixtures: [`../pillar-ab-implementation/E2_INPUT_FIXTURES.md`](../pillar-ab-implementation/E2_INPUT_FIXTURES.md) (**I/O-2**).
**Machine schema (JSON Schema):** [`../pillar-ab-implementation/contracts/schemas/ingest_v1.schema.json`](../pillar-ab-implementation/contracts/schemas/ingest_v1.schema.json) — validators use this file; keep prose below aligned with it.
**Build order:** **Federated pipeline first (F1)**, then **Lean bundle writer (L0)** from the **same** normalized stream  
**Related:** [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) §3.4 · [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) · HLD v1.1 [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §11.1 · [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) (Normalize) · spoken **fact kind** notes: [`fabric/INGEST_FACT_KINDS_DISCUSSION.md`](./fabric/INGEST_FACT_KINDS_DISCUSSION.md)

---

## 1. One canonical format (target)

All sources should land as **`ingest.v1` JSONL** — one JSON object per line, time-ordered.

**Example:** [`ingestion-poc/vector/samples/ingest.v1.example.jsonl`](../ingestion-poc/vector/samples/ingest.v1.example.jsonl)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:01Z",
  "tenant": "default",
  "ci_id": "orders-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.p95_latency_ms",
  "value": 1450.0,
  "threshold": 1000.0,
  "severity": 1.45,
  "labels": {
    "source": "replay",
    "trace_id": "abc123",
    "span_id": "span-7",
    "parent_span_id": "span-2",
    "route": "POST /checkout"
  },
  "raw_ref": "optional/path/to/original.line"
}
```

### Required fields

**Two layers (do not conflate):**

1. **JSON Schema minimal** (`ingest_v1.schema.json` `required[]`): `schema_version`, `ts`, `tenant`, `ci_id`, `fact_kind` — what validators enforce today.
2. **Product / PoC prose (this table):** also expect `ci_type` on healthy lines. Expect `name` for `metric_sample` / `anomaly` / `event` / `trace_span`; **`topo_update` often omits `name`** and uses `relation` / `src_ci_id` / `dst_ci_id` instead (see §2).

| Field | Type | Schema `required` | Product expect | Notes |
|-------|------|-------------------|----------------|-------|
| `schema_version` | string | Yes | Yes | Always `"ingest.v1"` |
| `ts` | ISO-8601 UTC | Yes | Yes | Event time |
| `tenant` | string | Yes | Yes | e.g. `"default"` |
| `ci_id` | string | Yes | Yes | Stable CI / service id after E2. At E1 this may be source-asserted or a placeholder; E2 resolves it. Primary join key with `tenant` for topology, stores, and a future ServiceOps ticket |
| `ci_type` | string | No (property defined) | Yes | e.g. `Service`, `HypervisorHost`. Additive taxonomy — see [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) §3 |
| `fact_kind` | enum | Yes | Yes | Router label (spoken: **fact kind**). Admitted now: §2. Reserved unused: §2.1 |
| `name` | string | No (property defined) | Usually | Metric / event / span name. Often omitted on `topo_update` |
| `value` | number | No | Usually | Numeric value; use `1.0` for boolean events; duration_ms for spans |
| `threshold` | number \| null | No (extra field; schema allows via `additionalProperties`) | If known | For detect / anomaly marking |
| `severity` | number or string | No (extra field) | Optional | Lab fixtures sometimes use a number ratio, sometimes a string level — both parse; prefer a number when you mean a ratio |
| `relation` / `src_ci_id` / `dst_ci_id` | string | No | Required for healthy `topo_update` | Edge assertion fields — see §2 |
| `labels` | object | No | Optional | Trace ids, route, host, raw metadata. Schema: string values only |
| `raw_ref` | string | No (extra field) | Optional | Pointer to original record |
| `identity` | object | No | After E2 | Overlay — §2.2 |

---

## 2. `fact_kind` values (fact kinds)

Wire field name is **`fact_kind`** (router label for who should care about the line). Full JSON examples and Pillar A/B routing: [`pillar-ab-implementation/E2_INPUT_FIXTURES.md`](../pillar-ab-implementation/E2_INPUT_FIXTURES.md#fact_kind-cheat-sheet) (**I/O-2**). Discussion (logs → `event`): [`fabric/INGEST_FACT_KINDS_DISCUSSION.md`](./fabric/INGEST_FACT_KINDS_DISCUSSION.md).

| Fact kind (`fact_kind`) | Federated use | Lean use | Primary consumer (ObserveOps) | Kind-specific fields |
|----------------------------|---------------|----------|-------------------------------|----------------------|
| `metric_sample` | Structural tier (Murphy/Panorama context) | Anomaly detect input | **E4 Stores** · **E6 Detect** | `name`, `value` |
| `anomaly` | Structural + speed tier | `A-ANOM` | **E6 Detect** · **E7 Curate** | `name`, `value`, `threshold`, `severity` |
| `event` | Structural + speed tier | `A-EVT` | **E4 Stores** · **E10 Identify** | `name` (includes **logs**), `value` often `1.0` |
| `trace_span` | **Required for Nezha** — speed tier (`tg:` / `pc:`) | Optional | **E9 Localize** · **E10 Identify** | `name`, `value` = duration_ms, trace labels |
| `topo_update` | Structural graph refresh | `A-TOPO` refresh | **E3 Topology** only | `relation`, `src_ci_id`, `dst_ci_id` (`name` optional) |

Schema enum matches this five-value set exactly (`ingest_v1.schema.json`). There is **no** separate `log` kind — raw logs map to `event` (§5).

### 2.1 Reserved `fact_kind` values (do not emit this pass)

Named so later ServiceOps / CMDB sources do not collide with today's enum. Collectors for these are **out of E1 this pass**. Unknown classes (not in §2 and not in this table) must be rejected or dead-lettered — do not guess. See [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) §2.2.

| Class | Future producer | Intended consumer |
|-------|-----------------|-------------------|
| `change_event` | Change / deploy feed | **E5 Maintain** · ServiceOps |
| `cmdb_sync` | CMDB / discovery snapshot or delta | **E2 Identity** / catalog enrichment |
| `ticket` | ServiceOps incident / ITSM record | **E11 Package** join on `ci_id` |

### 2.2 Identity overlay (E2 Normalize — not a second on-wire format)

After E2, the same `ingest.v1` line carries an `identity` object. HLD `IdentifiedRecord` **is** this overlay. Full contract: [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) §3. Until converters emit it, Motadata `labels.bound` and ObserveOps `"Unknown"` `ci_type` are the implemented proxies.

```json
"identity": {
  "status": "resolved",
  "bind_source": "object.name",
  "aliases": ["monitor-88", "esxi-host-01.lab.local"]
}
```

| `identity.status` | Meaning | May be E9 leaf / ServiceOps ticket CI? |
|-------------------|---------|----------------------------------------|
| `resolved` | Bind succeeded against topology or named bind-table entry | Yes |
| `unattributed` | No CI mapping; record kept (FR-B1 queue) | No |
| `synthesized` | Placeholder id invented for visibility (`Unknown`, `monitor-{id}`, plugin fallback) | No |

`service` / `env` / `version` stay optional `labels` (HLD D-E2-2). Primary join key is `tenant`+`ci_id`.

Poison envelopes (bad JSON, wrong `schema_version`, unknown `fact_kind`) are **E1 dead-letter**, not E2 synthesis. DLQ implementation is Vector D5.

---

## 3. What we need from you (preferred delivery)

### Option A — **Best:** pre-normalized `ingest.v1` JSONL (recommended)

Deliver one folder per incident:

```
datasets/ingest_samples/<suite>/<incident_id>/
  stream.jsonl          # ingest.v1 — primary ingest input
  topology.json         # A-TOPO (same shape as ObserveOps)
  ground_truth.json     # eval only — root_ci, signature, tags
  manifest.json         # optional: EPS, window, source notes
```

We replay `stream.jsonl` through Vector → Federated F1 sinks → then Lean bundle writer.

### Option B — **Raw samples + we convert**

Place native files under `raw/`; adapters live in [`ingestion-poc/adapters/`](../ingestion-poc/adapters/) (Motadata) and [`ingestion-poc/replay/`](../ingestion-poc/replay/) (ObserveOps):

```
datasets/ingest_samples/<suite>/<incident_id>/
  raw/
    metrics/            # see §4
    logs.jsonl          # see §5
    traces.jsonl        # see §6
  topology.json
  ground_truth.json
```

**Motadata exception (bulk export):** flat suite under `datasets/ingest_samples/jsonl_resolved/` (logs/metrics/traces/spans JSONL) → convert with `motadata_to_ingest_v1.py` → `motadata-ingest/stream.jsonl`. See §11.

---

## 4. Metrics — acceptable raw formats

| Format | Accept? | Notes |
|--------|---------|-------|
| **ObserveOps metric JSON** (existing corpus) | **Yes — preferred for M1** | `{ ci, signal, threshold, points:[{timestamp,value}] }` — already in `datasets/observeops/` |
| **JSONL metric samples** | Yes | `{ "ts", "ci_id", "name", "value", "threshold"? }` per line |
| **Prometheus exposition text** | Yes | We scrape or parse via Vector `prometheus_scrape` |
| **CSV** | Yes | Columns: `timestamp,ci_id,metric_name,value[,threshold]` |
| **OTLP metrics JSON** | Yes | Export from collector; adapter maps resource attrs → `ci_id` |

**Minimum for Federated structural tier:** time series per CI with enough pre-incident baseline + incident window (Murphy needs lookback).

---

## 5. Logs — acceptable raw formats

| Format | Accept? | Notes |
|--------|---------|-------|
| **JSONL** | **Preferred** | `{ "timestamp", "service" or "ci_id", "level", "message", ... }` |
| **ObserveOps events.json** | Yes | `{ events: [{ timestamp, ci, event_type, severity, message }] }` |
| **Syslog RFC5424** | Yes | Vector syslog source |
| Plain text files | OK with parser | Need stable service/host field for CI bind |

Maps to `fact_kind: "event"` (**fact kind** `event`). There is **no** separate `log` value in the five-kind enum — see [`fabric/INGEST_FACT_KINDS_DISCUSSION.md`](./fabric/INGEST_FACT_KINDS_DISCUSSION.md) §2.

---

## 6. Traces — acceptable raw formats (Federated / Nezha)

**Required for Federated speed tier** if Nezha hop must be real (not stubbed).

| Format | Accept? | Notes |
|--------|---------|-------|
| **ingest.v1 `trace_span` lines** | **Preferred** | See §6.1 |
| **OTLP JSON** (traces) | Yes | From OpenTelemetry collector export |
| **Jaeger JSON** | Yes | Adapter extracts spans |
| Zipkin JSON | Yes | Lighter adapter |

### 6.1 Minimal trace_span shape (if you pre-convert)

One line per span:

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:01.123Z",
  "tenant": "default",
  "ci_id": "checkout-service",
  "ci_type": "Service",
  "fact_kind": "trace_span",
  "name": "POST /checkout",
  "value": 842.0,
  "threshold": null,
  "labels": {
    "trace_id": "4bf92f3577b34da6",
    "span_id": "00f067aa0ba902b7",
    "parent_span_id": "00f067aa0ba902b6",
    "http.status_code": "503",
    "peer_service": "payment-service"
  }
}
```

`value` = duration_ms (or latency). Builders derive Nezha pattern keys from span sequences per trace.

---

## 7. Topology (both engines)

**Two shapes — do not mix them up:**

| Shape | Where | Role |
|-------|-------|------|
| ObserveOps `topology.json` (this section) | Beside incident stream for Lean / Federated bakeoff | Seed graph for classic-infra UC packs — edge field often `type: "calls"` |
| Motadata Pillar B `topo_update` lines + optional `topology.bootstrap.json` | Pillar B sample estate | Wave-1 relations (`runs_on`, `depends_on`, …) → Dest `map/` — see I/O-2 / I/O-3 |

Use existing ObserveOps shape for Federated/Lean incident folders:

```json
{
  "nodes": [{ "id": "orders-api", "type": "Service", "layer": "application" }],
  "edges": [{ "from": "orders-api", "to": "payment-service", "type": "calls" }]
}
```

File: `topology.json` beside the incident stream.  
Federated: structural tier / DashMap LOS context.  
Lean: `topology.json` in bundle.

Motadata GraphWriter does **not** read this ObserveOps `topology.json` as its primary map write path — it admits `ingest.v1` with `fact_kind=topo_update` (plus lab bootstrap).
---

## 8. Build order (Federated first, then Lean)

Same `stream.jsonl`; different sinks:

```
stream.jsonl (ingest.v1)
       │
       ▼
    Vector
       ├──► F1: speed_tier_builder → Dragonfly (tg:/pc:)     [Federated first]
       ├──► structural feed → metric store / KG slice         [Murphy/Panorama]
       ├──► detect → A-ANOM + A-SEED
       └──► L0: lean_bundle_writer → Lean bundle             [second step]
```

Lean does **not** need Dragonfly keys for classic infra; it consumes the **bundle** built from the same stream.

---

## 9. Microservice justification suite (for Federated gates)

For [`FEDERATED_JUSTIFICATION_REPORT.md`](./FEDERATED_JUSTIFICATION_REPORT.md), each incident should tag `ground_truth.json`:

```json
{
  "root_ci": "payment-service",
  "signature": "dependency_timeout",
  "incident_class": "retry_storm",
  "gray_failure": true,
  "contributor_cis": []
}
```

| `incident_class` | Why Federated might win |
|------------------|-------------------------|
| `retry_storm` | Path noise, threshold-only miss |
| `path_regression` | Nezha pattern drift |
| `deploy_churn` | Topology churn + ambiguous onset |
| `cross_svc_contention` | Earliest-alert trap |

---

## 10. Checklist before handoff

- [ ] All events have UTC `ts`
- [ ] After E2, resolved `ci_id` values exist in `topology.json` (E1 may carry unresolved ids; those must not become localize/ticket targets)
- [ ] Every line has `schema_version == "ingest.v1"` and a §2 `fact_kind` (not a reserved §2.1 class unless you are delivering a future source by agreement)
- [ ] Incident window includes **baseline + fault** (≥15–30 min baseline for metrics)
- [ ] Traces include `trace_id` + `span_id` + `parent_span_id` (Federated)
- [ ] `ground_truth.json` per incident for scoring
- [ ] No secrets in sample files (tokens, PII)

---

## 11. Quick start — existing converters

### ObserveOps UC → `ingest.v1` (M1 eval path)

```bash
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all
# → datasets/ingest_samples/observeops-replay/UC-{1..5}/stream.jsonl
```

Converter: [`ingestion-poc/replay/observeops_to_ingest_v1.py`](../ingestion-poc/replay/observeops_to_ingest_v1.py)  
Output: [`datasets/ingest_samples/observeops-replay/`](../datasets/ingest_samples/observeops-replay/)

### Motadata ClickHouse export → `ingest.v1` (product-shaped path)

Local dumps live in [`datasets/ingest_samples/jsonl_resolved/`](../datasets/ingest_samples/jsonl_resolved/) (**gitignored** large `.jsonl`; do not push).

**Depth (2026-07-21):** CI-bind + threshold catalog + span-derived `http.error_rate` → Localize smoke `motadata-apm-001`.

```bash
# CI-bind + APM incident (Lean root match)
python3 ingestion-poc/adapters/build_motadata_incident.py

# Base convert (applies ci_bind + thresholds when present)
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
```

| Artifact | Path |
|----------|------|
| CI bind | `motadata-ingest/ci_bind.json` |
| Thresholds | `ingestion-poc/adapters/motadata_threshold_catalog.json` |
| APM incident | `motadata-ingest/incidents/motadata-apm-001/` |

Adapter: [`motadata_to_ingest_v1.py`](../ingestion-poc/adapters/motadata_to_ingest_v1.py) · [README](../ingestion-poc/adapters/README.md)

| Motadata source | `fact_kind` | `ci_id` |
|-----------------|----------------|---------|
| `log.jsonl` | `event` | hostname / `event_source` |
| `metric_numeric.jsonl` | `metric_sample` (+ threshold) | bound name or `monitor-{id}` |
| `metric_string.jsonl` | `event` | bound name or `monitor-{id}` |
| `trace.jsonl` / `span.jsonl` | `trace_span` | service name |
| span-derived | `metric_sample` | service name |

**Gaps:** Broader Motadata GT (human-labeled packs beyond the current L1 **7**, plus pending `motadata-deps-001`) and live change feed still open. Motadata signatures `app_error_rate` / `ping_degradation` / `host_cpu_saturation` + inventory topology are **Done** for the L1 packs.

---

## 12. References

- Vector skeleton: [`ingestion-poc/vector/`](../ingestion-poc/vector/)
- Detect: [`ingestion-poc/detect/`](../ingestion-poc/detect/)
- Storage tiers: [`federated-pipeline/docs/STORAGE_TIERS.md`](../federated-pipeline/docs/STORAGE_TIERS.md)
- Collect LLD: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md)
- Normalize / Identity LLD: [`LLD-E2-Identity.md`](./LLD-E2-Identity.md)
