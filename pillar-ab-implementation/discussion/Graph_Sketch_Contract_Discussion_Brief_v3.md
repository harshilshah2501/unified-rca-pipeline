# Graph + Sketch Contract - Revised Discussion Brief v3

**Updated freeze candidate incorporating OTel-aligned exemplars, RED service-health triage, OTel bucket semantics, graph-guided RCA evidence descent, and reconstructable raw-evidence retention.**

**Status:** Discussion Draft - Revision - 2026-10-01

> **Revision scope**  
> Graph/entity/edge decisions from the 2026-08-20 brief remain intact unless explicitly changed below. This revision updates the Sketch Row contract and adds exemplar/trace-correlation rules. It is still not Signed.

---

## 00 Owner leanings - revision

| Topic | Revised choice |
|---|---|
| **Graph** | Keep rich CI graph: stable `tenant + ci_id` identity, richer `ci_type`, 15 relations, edge provenance. |
| **Sketch** | One logical row = T-Digest + OTel-aligned explicit buckets + seasonal baseline + row anomaly state + bounded exemplars. |
| **Exemplars** | `TraceBased` eligibility; bucket-aligned retention; maximum one exemplar per bucket in first version. |
| **RCA use** | Graph -> KPI catalog -> relevant sketch -> exemplar -> trace -> new hypothesis -> graph. |
| **Encoding** | Logical schema first; JSON examples now; bytes/protobuf/DDL after Signed. |

---

## 01 Locked non-negotiables carried forward

- CI-only vertices: Alert, Incident, ITSMTicket, Metric, Trace, LogPattern, and Change-as-CI are not `GraphSnapshot` vertices.
- Primary identity remains `tenant + ci_id`; sketch `entity_id` is the same resolved CI identity after bind.
- The graph and sketch/history layers remain separate substrates joined through identity and time.
- D5 remains Review.
- The logical contract is frozen before choosing protobuf/Vortex physical encoding.

---

## 02 Entities

An entity is a resolved configuration item with stable `tenant + ci_id` that may be localized or ticketed. Facts/events such as alerts, traces, incidents, changes, and log patterns are evidence attached by identity/time; they are not topology vertices.

| Field | Rule |
|---|---|
| `tenant` | namespace |
| `ci_id` | stable within tenant |
| `entity_id` | alias of `ci_id` after identity bind; not a second root key |
| `identity_status` | `resolved` required for `GraphSnapshot` |

### 2.1 CI type families

| Family | Examples | Why needed |
|---|---|---|
| Business / service | `BusinessService`, `Service` | symptom seed; ERROR/SLOWDOWN |
| Runtime / middleware | `Runtime`, `Middleware` | app-stack depth |
| Data | `Database`, `Datastore` | DB/storage leaves |
| Compute / OS | `Host`, `GuestOS`, `VirtualMachine`, `HypervisorHost` | contention/hosting walks |
| Container | `Pod`, `Container` | ephemeral; `scope_parent` + validity |
| Storage / network | `NetworkPort`, filesystem/LUN-class CI | disk/network localization |
| Observation | Monitor / collector CI | `MONITORING_UNAVAILABLE` |

### 2.2 Node metadata

```text
tenant, ci_id, ci_type, ci_name,
identity_status ∈ {resolved, unattributed, synthesized}

ci_class
tier
instance_scope
scope_parent
monitored_via[]
kpi_catalog_ref
aliases[]
labels{}
valid_from / valid_to
```

> **Writer rule**  
> `GraphSnapshot` vertices only with `identity_status = resolved`. `kpi_catalog_ref` remains the preferred bridge from a graph node to investigation-relevant sketch metrics.

---

## 03 Edges - 15 relation types

| relation | Plain meaning | Typical walk use |
|---|---|---|
| `depends_on` | A needs B | ERROR / dependency descent |
| `runs_on` | A executes on B | contention / tenancy |
| `mounts` | A mounts B | disk path |
| `connects_to` | L2/L3 adjacency | network |
| `backs` | A backs B | storage |
| `uses` | A uses B | trace-derived dependency |
| `hosted_on` | guest/VM on hypervisor | virtualization ascent |
| `member_of` | A in cluster/group | cluster scope |
| `part_of` | child of parent | composition |
| `routes_through` | path via middlebox | network path |
| `authenticates_via` | auth dependency | identity path |
| `monitored_by` | observed by collector | monitoring unavailable |
| `backed_up_by` | backup target | DR context |
| `clustered_with` | peer same tier | peer / HA |
| `communicates_with` | calls / talks to | service map |

### 3.1 Edge provenance

Every edge remains a typed, directed, auditable relationship between two resolved CIs. `discovered_via` captures how the relationship was learned, confidence, source fields, endpoint binding, direction inference, refresh cadence, validity, and optional criticality.

---

## 04 Sketch row - revised

One sketch row remains one logical record for the full key below. The revision preserves the existing **T-Digest + buckets + seasonal baseline** model, adds row-level anomaly state already produced during write-time baseline comparison, and adds bounded OTel-style exemplars for metric-to-trace correlation.

```text
logical key:
(tenant,
 entity_id [= ci_id],
 metric_id,
 window,
 season_key,
 window_start)
```

| Part | Meaning | v2 rule |
|---|---|---|
| `metric_id` | named metric stream | e.g. `request.latency_ms` |
| `entity_id` | same resolved identity as graph `ci_id` | must be resolved |
| `window` | slice length | start 1m + 5m; allow 1h / 1d |
| `season_key` | baseline calendar slot | hour-of-week in tenant TZ |
| `window_start` | concrete slice identity | required |
| `anomaly` | row-level baseline result | whole sketch window, not exemplar-level |

![Revised sketch.v2 logical structure](assets/schema_v2.png)

*Figure 1 - Revised `sketch.v2` logical structure.*

### 4.1 Body - one logical row

| Component | Purpose |
|---|---|
| T-Digest | mergeable approximate quantiles (p50/p95/p99) |
| Explicit buckets | fixed range population counts |
| Seasonal baseline | expected quantiles for `season_key` |
| Anomaly state | write-time statement about the sketch/window |
| `Exemplars[]` | bounded evidence pointers to concrete trace/span executions |

### 4.2 OTel-aligned explicit bucket semantics - NEW LOCK

Adopt OpenTelemetry explicit histogram semantics in the logical contract. This corrects the 2026-08-20 example, which had seven bounds but only six counts.

```text
N explicit bounds -> N + 1 counts
counts are per-bucket, not cumulative

bounds = [0, 50, 100, 200, 500, 1000, 2000]

0: (-∞,0]
1: (0,50]
2: (50,100]
3: (100,200]
4: (200,500]
5: (500,1000]
6: (1000,2000]
7: (2000,+∞)
```

> **Invariant**  
> `counts.length == bounds.length + 1`. `exemplar.bucket_index` uses the same index space.

### 4.3 Exemplar semantics - NEW

An exemplar is one retained original measurement that provides concrete context for an aggregate. It is an investigation starting point, not proof that the chosen trace explains the entire bucket.

| Field | Meaning / rule |
|---|---|
| `bucket_index` | row-scoped reference to the parent bucket definition |
| `value` | original measurement value |
| `timestamp` | observation time |
| `trace_id` | lookup key into trace backend |
| `span_id` | operation inside the trace |
| `selection_hint.reason` | heuristic reason this exemplar was retained |
| `selection_hint.confidence` | heuristic confidence; supporting evidence only |

> **Cardinality lock**  
> First version: at most one exemplar per bucket. Empty buckets need no exemplar entry. `exemplars.length <= bucket_count`.

### 4.4 Exemplar selection policy - NEW

![Eligibility and retention are separate decisions](assets/filter_reservoir.png)

*Figure 2 - Eligibility and retention are separate decisions.*

Closest OTel-native baseline: `TraceBased ExemplarFilter + AlignedHistogramBucketExemplarReservoir`. The custom RCA extension may replace uniform/last-seen bucket winner selection with a deterministic scenario-aware policy while preserving bucket alignment.

| Scenario | Retention preference (illustrative) |
|---|---|
| **SLOWDOWN** | extreme latency > long downstream span > contention evidence > error |
| **FAULT** | error > timeout > dependency failure > extreme latency |
| **RESOURCE** | saturation/contention > extreme delay > error |
| **NETWORK** | loss/timeout/network delay > general latency |

The scenario is resolved outside the reservoir from a combination of metric semantics, detector verdict, and active RCA context. Very high-confidence detector evidence may override the active case context. Exact weighting remains an implementation policy, not part of the sketch storage contract.

### 4.5 `sketch.v2` JSON example

```json
{
  "schema_version": "sketch.v2",
  "tenant": "default",
  "entity_id": "checkout-api",
  "entity_type": "Service",
  "metric_id": "request.latency_ms",
  "window": "5m",
  "window_start": "2026-08-20T03:30:00Z",
  "window_end": "2026-08-20T03:35:00Z",
  "season_key": "Thu-09:00",
  "sample_count": 1000,
  "tdigest": {
    "compression": 100,
    "encoding": "tdigest_bytes",
    "data": "<opaque-bytes>"
  },
  "buckets": {
    "bucket_schema_version": "latency_v1",
    "bounds": [0, 50, 100, 200, 500, 1000, 2000],
    "counts": [0, 100, 460, 220, 110, 95, 14, 1]
  },
  "baseline": {
    "baseline_version": "seasonal_v1",
    "expected_p50": 88.0,
    "expected_p95": 170.0,
    "expected_p99": 320.0
  },
  "anomaly": {
    "is_anomalous": true
  },
  "exemplars": [
    {
      "bucket_index": 5,
      "value": 870.0,
      "timestamp": "2026-08-20T03:32:14.381Z",
      "trace_id": "T123",
      "span_id": "S45",
      "selection_hint": {
        "reason": "slowdown",
        "confidence": 0.91
      }
    }
  ]
}
```

---

## 05 Knowledge graph vs history / event evidence

The topology graph remains the estate map. Sketches remain compact metric history. Traces remain event/execution evidence. The new exemplar link does not make Trace a `GraphSnapshot` vertex.

| Substrate | Stored unit | Join / use |
|---|---|---|
| Knowledge / topology graph | resolved CIs + durable relations | RCA graph walk by `tenant + ci_id` |
| Sketch history | metric/entity/window evidence row | graph -> sketch by `entity_id + time + metric` |
| Trace store | trace/span executions | sketch -> trace by `trace_id` (+ `span_id`) |
| Signals / cases | alerts, incidents, verdicts | correlation/dedupe; not topology vertices |

![Graph-guided evidence descent](assets/evidence_descent.png)

*Figure 3 - Graph-guided evidence descent and return loop.*

---

## 06 RCA read path - NEW

RCA should not start by scanning all sketches or jumping directly to exemplars. It starts from graph context, narrows metrics by investigation type and `kpi_catalog_ref`, then inspects only relevant sketch rows in the investigation time window.

```text
Graph node (entity_id)
  -> investigation type
  -> KPI catalog
  -> relevant metric_ids
  -> sketch rows in inspect window
  -> anomalous/relevant sketch
  -> T-Digest + buckets + baseline
  -> relevant exemplar
  -> trace_id / span_id
  -> trace backend
  -> new hypothesis
  -> return to graph
```

> **Interpretation rule**  
> Trace evidence is directional evidence for the next inspection. Do not conclude root cause from a single exemplar trace.

---

## 07 Sampling interaction - NEW

![Head and tail sampling interaction](assets/sampling.png)

*Figure 4 - Head and tail sampling interaction with exemplar usefulness.*

Head sampling may discard a rare slow/error trace before the final outcome is known. Collector tail sampling can retain traces based on complete latency/error evidence only if the trace reaches the collector. `TraceBased` exemplar eligibility occurs earlier than the final downstream tail-retention decision, so a stored exemplar may occasionally point to a trace that is not ultimately retained.

> **Implementation rule**  
> Trace lookup must tolerate **"trace unavailable"**. If that rate is material, mitigate through sampling policy or reconciliation - not by bloating the sketch row.

---

## 08 Decision log - 2026-10-01

| ID | Decision | Rationale |
|---|---|---|
| D-S1 | Same logical row | Keep exemplars in the sketch row for fast evidence access; bounded cardinality prevents the row becoming a trace index. |
| D-S2 | One exemplar per bucket | First implementation uses at most one exemplar per explicit histogram bucket. |
| D-S3 | Top-level `exemplars[]` | Keep bucket statistics pure; exemplars are a top-level evidence list carrying `bucket_index`. |
| D-S4 | Parent owns bucket schema | Do not duplicate `bucket_schema_version` inside each exemplar. |
| D-S5 | OTel N+1 semantics | N bounds -> N+1 non-cumulative counts. |
| D-S6 | `TraceBased` baseline | Preferred eligibility filter for metric-to-trace correlation. |
| D-S7 | Scenario-aware retention | Custom RCA winner policy may prioritize different evidence for SLOWDOWN vs FAULT. |
| D-S8 | `selection_hint` is heuristic | Store reason/confidence on exemplar only; not a row anomaly verdict or RCA conclusion. |
| D-S9 | Graph-first RCA | Use investigation type/KPI catalog before reading sketch evidence. |
| D-S10 | Trace is evidence, not graph node | `trace_id/span_id` point into trace backend; the graph remains CI-only. |

---

## 09 Open questions for implementation

- Exact `selection_hint.reason` closed enum for v2.
- Concrete SDK language implementation for custom `ExemplarReservoir` and View wiring.
- Tail-sampling policy and expected dangling-exemplar rate.
- First signed bucket boundary tables for latency and CPU metric families.
- Whether anomaly needs additional fields beyond `is_anomalous` (score, baseline deviation, detector version).
- Vortex physical layout for `tdigest` bytes + exemplar list and row-size benchmark.
- Trace backend lookup API and retention guarantees.

---

## 10 What you say in one minute - revised

> **Leadership summary**  
> We keep a rich CI-only knowledge graph and a separate compact metric-history layer. Each sketch row now combines T-Digest, OTel-aligned explicit buckets, seasonal baseline, write-time anomaly state, and a bounded set of trace-linked exemplars. RCA walks the graph, narrows KPIs, inspects relevant sketches, and uses an exemplar only as a concrete jump into trace evidence; the trace then guides the next graph/evidence inspection. Exemplars accelerate evidence descent - they do not replace RCA reasoning.

---

## Appendix A - Normative rules for `sketch.v2`

| Rule | Requirement |
|---|---|
| Identity | `entity_id` must be the same resolved identity as graph `ci_id` after bind. |
| Window | Exemplars reported with a sketch should occur within that row's window. |
| Buckets | bounds strictly increasing; `counts.length = bounds.length + 1`; counts non-cumulative. |
| Exemplar index | `0 <= bucket_index < counts.length`. |
| Cardinality | at most one exemplar per bucket in first version. |
| Hints | `selection_hint` is heuristic; consumers must not treat it as root-cause truth. |
| Trace lookup | `trace_id` addresses trace backend; `span_id` localizes the relevant operation. |
| Topology | no Trace / Metric / Alert / Incident vertices are introduced by this revision. |

---

## Appendix B - External references used for exemplar alignment

- OpenTelemetry Metrics SDK - Exemplars, filters, reservoirs, explicit histograms
- OpenTelemetry Metrics Data Model - histogram bucket inclusivity and exemplar fields
- OpenTelemetry Sampling concepts

---

## 09 RED Service-Health Triage - NEW

RED (**Rate, Errors, Duration**) is adopted as the service-health triage layer between graph context and deep sketch inspection for request-driven services. It does not replace the KPI catalog; it narrows which KPI lane should be inspected first.

![RED triage precedes deep sketch inspection](assets/red_triage.png)

*Figure 5 - RED triage precedes deep sketch inspection.*

> **Contract rule**  
> Graph -> investigation type/KPI catalog -> RED lane -> relevant sketch rows. Do not scan all metrics by default. Duration may use the distribution sketch profile; Rate and Errors may use scalar/rate profiles rather than forcing T-Digest + histogram semantics onto every metric.

---

## 10 Raw Reconstruction and Evidence Retention - NEW

The sketch row is explicitly classified as **lossy historical evidence**. T-Digest, explicit buckets, baselines, and bounded exemplars cannot reconstruct the complete original measurement sequence after raw observations are discarded. Exact re-bucketing, replay, complete timestamp/attribute recovery, or forensic recomputation therefore requires a separate raw metric/event evidence store or another system of record that retains the original observations.

![Evidence retention tiers](assets/retention_tiers.png)

*Figure 6 - Evidence retention tiers: compact sketches, policy-retained traces, short-lived raw evidence.*

> **Retention rule**  
> Default path: long-lived sketches + policy-retained traces + shorter raw retention. Optional optimization: when the sketch writer marks a window anomalous, extend/pin raw retention for a bounded interval around that window. Raw retention policy is operational and must not change sketch statistical meaning.

---

## 11 Additional Freeze Decisions - NEW

- Exemplar `trace_id/span_id` is exact for the retained observation, but is not a root-cause verdict or a statistical representative of the full bucket.
- RED is a triage layer; the KPI catalog remains the versioned mapping from investigation type/entity class to concrete metrics.
- Metric profile may be **distribution** (e.g. Duration) or **scalar/rate** (e.g. Rate/Error ratio). Do not require one universal payload shape.
- Raw reconstruction is out of scope for `sketch.v2` itself; a separate raw evidence store is required for exact re-analysis.
- RCA evidence descent is **Graph -> RED/KPI -> Sketch -> Exemplar -> Trace -> optional Raw -> back to Graph/new hypothesis**.

---

## 12 Additional Open Items - NEW

- Define RED-to-KPI mappings per request-driven `ci_type` and investigation type.
- Define distribution vs scalar/rate sketch profiles and their baseline fields.
- Define raw evidence store minimum fields, default retention, anomaly-aware extension, privacy and compliance constraints.
- Define exact-reanalysis query path and how RCA requests raw evidence only when summary evidence is insufficient.

---

## Appendix C - Added External References

- OpenTelemetry Metrics SDK: https://opentelemetry.io/docs/specs/otel/metrics/sdk/
- OpenTelemetry Metrics Data Model: https://opentelemetry.io/docs/specs/otel/metrics/data-model/
- OpenTelemetry Sampling: https://opentelemetry.io/docs/concepts/sampling/
- Grafana RED method guidance: https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
