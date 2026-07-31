# Ingest Data Format — What to Provide (Frozen Corpus PoC)

**Audience:** Data owners preparing logs, metrics, traces for ingestion PoC  
**Build order:** **Federated pipeline first (F1)**, then **Lean bundle writer (L0)** from the **same** normalized stream  
**Related:** [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) §3.4 · [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md)

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
  "signal_class": "metric_sample",
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

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | Yes | Always `"ingest.v1"` |
| `ts` | ISO-8601 UTC | Yes | Event time |
| `tenant` | string | Yes | e.g. `"default"` |
| `ci_id` | string | Yes | Stable CI / service id (must match topology) |
| `ci_type` | string | Yes | e.g. `Service`, `Pod`, `HypervisorHost` |
| `signal_class` | enum | Yes | See §2 |
| `name` | string | Yes | Metric name, log type, span operation, etc. |
| `value` | number | Usually | Numeric value; use `1.0` for boolean events |
| `threshold` | number \| null | If known | For detect / anomaly marking |
| `severity` | number | Optional | Normalized severity or ratio |
| `labels` | object | Optional | Trace ids, route, host, raw metadata |
| `raw_ref` | string | Optional | Pointer to original record |

---

## 2. `signal_class` values

| Class | Federated use | Lean use |
|-------|---------------|----------|
| `metric_sample` | Structural tier (Murphy/Panorama context) | Anomaly detect input |
| `anomaly` | Pre-marked crossing (optional) | `A-ANOM` |
| `event` | Speed tier + evidence | `A-EVT` (UC-2/4 class) |
| `trace_span` | **Required for Nezha** — Dragonfly `tg:` / `pc:` | Optional |
| `topo_update` | Structural graph refresh | `A-TOPO` refresh |

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

Maps to `signal_class: "event"`.

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
  "signal_class": "trace_span",
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

Use existing ObserveOps shape:

```json
{
  "nodes": [{ "id": "orders-api", "type": "Service", "layer": "application" }],
  "edges": [{ "from": "orders-api", "to": "payment-service", "type": "calls" }]
}
```

File: `topology.json` beside the incident stream.  
Federated: structural tier / DashMap LOS context.  
Lean: `topology.json` in bundle.

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
- [ ] `ci_id` values exist in `topology.json`
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

| Motadata source | `signal_class` | `ci_id` |
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
