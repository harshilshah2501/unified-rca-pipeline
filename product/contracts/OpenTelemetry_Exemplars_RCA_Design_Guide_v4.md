# OpenTelemetry Exemplars for RCA

**A visual design guide for graph-guided RCA with RED triage, T-Digest, explicit buckets, exemplars, traces, and reconstructable raw evidence**

> **One-sentence model**  
> Graph tells RCA where to look. RED + KPI catalog tell it which health lane matters. Sketch tells it what changed. Exemplar points to one real observation. Trace explains one execution. Raw evidence enables exact recomputation when summaries are insufficient.

![Complete RCA evidence ladder](assets/evidence_ladder.png)

*Figure 1 - Complete RCA evidence ladder.*

## Why this revision matters

The earlier design correctly linked sketches to traces with exemplars. This revision adds two missing pieces: **RED as the service-health triage layer**, and an explicit **raw-evidence tier** for cases where lossy sketches cannot answer forensic or re-analysis questions.

---

## 1. Start from the existing sketch contract

The existing Graph + Sketch contract already gives us the right compact unit: one logical sketch row per tenant, entity, metric, window, season slot, and concrete window start. The row carries a **T-Digest**, **explicit buckets**, and a **seasonal baseline**. The new design does not replace that structure; it adds bounded execution pointers and a clearer evidence hierarchy.

![One measurement updates multiple evidence structures in parallel](assets/parallel_consequences.png)

*Figure 2 - One measurement updates distribution, bucket population, and exemplar selection in parallel.*

| Component | Best for |
|---|---|
| **T-Digest** | Approximate percentiles and tail position: p50, p95, p99. |
| **Explicit buckets** | Stable range counts and seeing where population mass moved. |
| **Seasonal baseline** | Deciding whether the current window deviates from expected behavior. |
| **Exemplar extension** | Preserving a bounded jump-off from aggregate evidence to a concrete execution. |

---

## 2. What an exemplar gives you - exactly

![Exemplar truth: exact pointer for the retained observation, not root-cause proof](assets/exemplar_truth.png)

*Figure 3 - The exemplar trace is exact for the retained observation, but not automatically the root-cause trace.*

> **Sharpened takeaway**  
> If an exemplar contains `trace_id=T123` and `span_id=S45`, those are the exact identifiers for the retained measurement. What is uncertain is not the pointer; it is the interpretation. `T123` is one concrete execution from the same statistical population, not proof that it explains the whole bucket or incident.

### 2.1 Investigation starting point, not verdict

- Bucket count tells us how many requests landed in a range.
- Exemplar tells us one actual observation that contributed to the metric point.
- Trace tells us what happened in that one execution.
- RCA uses that execution to strengthen, reject, or redirect a hypothesis and then continues the evidence walk.

> **Do not say**  
> "The exemplar represents the bucket" or "this trace is the RCA trace."  
> Better wording: **"This is one real trace from the affected metric region worth inspecting."**


---

## 3. Developer lifecycle - how the SDK captures and carries trace correlation

The most important implementation point is that application code normally **does not search for a trace ID and manually attach it to the metric**. The OpenTelemetry Context is the bridge. In Java, metric measurements default to the current `Context`; the active span is stored in that context, and its `SpanContext` contains the exact `trace_id` and `span_id`. The Metrics SDK can use that context when evaluating and recording exemplars. [1][6][7]

![Developer lifecycle from metric recording to exemplar and trace drill-down](assets/developer_lifecycle.png)

*Figure 4 - Developer lifecycle: record the measurement while the request span is current; OTel carries the trace context into exemplar selection and export.*

### 3.1 What the application developer actually does

For request-driven code, the developer's responsibility is mainly to preserve the correct active span/context and record the metric with **low-cardinality metric attributes**. The application should not add `trace_id` or `span_id` as ordinary metric attributes because that creates a high-cardinality metric dimension. Exemplars are the correlation mechanism.

```java
LongHistogram latencyMs =
    meter.histogramBuilder("request.latency_ms")
        .ofLongs()
        .setUnit("ms")
        .setDescription("Checkout request latency")
        .build();

Span span = tracer.spanBuilder("POST /checkout")
    .setSpanKind(SpanKind.SERVER)
    .startSpan();

long started = System.nanoTime();

try (Scope ignored = span.makeCurrent()) {
    checkout();

    long elapsedMs =
        TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started);

    latencyMs.record(
        elapsedMs,
        Attributes.builder()
            .put("http.request.method", "POST")
            .put("http.route", "/checkout")
            .build());

} catch (Throwable t) {
    span.recordException(t);
    span.setStatus(StatusCode.ERROR);
    throw t;
} finally {
    span.end();
}
```

The critical line is not a trace-ID lookup. It is that `latencyMs.record(...)` executes **while the request span is current**. In the Java API, metric recording uses `Context.current()` by default unless an explicit context is supplied. [6]

> **Developer rule**  
> Keep the correct span current when recording the measurement. Let OTel carry the correlation. Do not create a second, timestamp-based metrics-to-traces join in application code.

### 3.2 What the Metrics SDK does internally

For the same `870 ms` measurement, two paths happen in parallel:

1. **Aggregation path** - update histogram count/sum/bucket state (and, in our architecture, feed the T-Digest/sketch pipeline).
2. **Exemplar path** - inspect the measurement context, apply the `ExemplarFilter`, offer the eligible observation to the configured `ExemplarReservoir`, and, if retained, preserve its value/time plus trace/span correlation.

With the `TraceBased` filter, a measurement recorded under a sampled span is eligible to compete. If the reservoir retains it, the exported exemplar can carry the exact `trace_id` and `span_id` from that span context. [1][2]

```text
request span is current
    trace_id = T123
    span_id  = S45
          |
          v
histogram.record(870 ms)
          |
          +----> aggregation: increment bucket/count/sum
          |
          +----> exemplar filter: eligible?
                         |
                         v
                    reservoir
                         |
                         v
                retained exemplar
                value = 870
                trace_id = T123
                span_id  = S45
```

### 3.3 What is exported over OTLP

The metric stream and trace stream remain separate. The histogram data point can contain explicit bounds, bucket counts and an `exemplars[]` collection. Each exported exemplar carries the retained value, timestamp, filtered attributes and optional `trace_id` / `span_id`. The trace itself is exported through the trace pipeline. [2]

A simplified metric payload looks like:

```json
{
  "metric": "request.latency_ms",
  "explicit_bounds": [0, 50, 100, 200, 500, 1000, 2000],
  "bucket_counts": [0, 100, 460, 220, 110, 95, 14, 1],
  "exemplars": [
    {
      "value": 870,
      "time_unix_nano": "...",
      "trace_id": "T123",
      "span_id": "S45"
    }
  ]
}
```

One useful implementation detail: OTLP exemplar data does **not need to carry our `bucket_index` field**. The sketch writer can infer it from `exemplar.value` using the same `explicit_bounds`. For `870 ms` with the boundaries above, it resolves to bucket index `5`, the interval `(500,1000]`.

### 3.4 What the sketch writer does

The sketch writer consumes the exported metric point and converts it into the application contract rather than trying to rediscover the trace relationship:

```text
OTLP histogram datapoint
  bounds[N]
  bucket_counts[N+1]
  exemplars[]
        |
        v
Sketch writer
  update/merge T-Digest
  persist OTel-native bucket counts
  run baseline/anomaly evaluation
  for each retained exemplar:
      derive bucket_index(value, bounds)
      persist value + timestamp + trace_id + span_id
        |
        v
sketch.v2
```

That gives the write side a clean contract: **OTel owns request context propagation and metric-to-span correlation; the sketch writer owns statistical persistence and the RCA-friendly row shape.**

### 3.5 What RCA does later

RCA comes from the other direction. It typically reaches an `entity_id` through the knowledge graph, narrows the evidence using the investigation type / RED lane / KPI catalog, reads the relevant sketch window, and only then follows an exemplar:

```text
Graph node
  -> RED / KPI selection
  -> sketch window
  -> anomalous bucket
  -> exemplar trace_id=T123, span_id=S45
  -> Trace Backend.getTrace(T123)
  -> inspect span S45 and surrounding call path
  -> form next hypothesis
  -> return to Graph / next evidence source
```

The exemplar therefore removes a fragile correlation problem. RCA does **not** have to search the trace store by approximate timestamp and hope to find a matching request. It already has the exact identifiers for the retained observation.

### 3.6 Failure modes developers must understand

| Situation | Result |
|---|---|
| Measurement recorded while sampled span is current | Trace-correlated exemplar is possible. |
| Measurement recorded with no active span | Metric still records; exemplar may have no trace/span correlation. |
| Active span exists but is not sampled and filter is `TraceBased` | Measurement is not eligible for a trace-based exemplar. |
| `trace_id` is added as a normal metric label | Avoid: creates high-cardinality metric series. |
| Collector tail sampler later drops the trace | Exemplar may be valid but trace lookup can return unavailable. |
| Application already head-dropped the trace | Collector cannot reconstruct or tail-sample a trace it never received. |

### 3.7 Developer checklist

- Keep request span/context propagation correct across threads, executors and async boundaries.
- Record request metrics while the intended span is current.
- Keep ordinary metric attributes low-cardinality.
- Use OTel exemplars for trace/span correlation instead of `trace_id` labels.
- Align explicit histogram bounds with the sketch `bucket_schema_version`.
- Treat exported exemplar IDs as exact for that retained observation, not as a root-cause verdict.
- Make trace lookup tolerant of `trace unavailable` when downstream tail sampling is used.
- Contract-test the sketch writer's `bucket_index(value, bounds)` logic, especially boundary values and overflow.

---

## 4. Filter vs reservoir - the two selection decisions

OpenTelemetry separates exemplar sampling into two hooks. The filter controls eligibility; the reservoir controls bounded retention among eligible measurements. The OTel Metrics SDK recommends `TraceBased` as the default filter, and supports bucket-aware exemplar sampling for histogram aggregations. [1]

![Filter vs reservoir](assets/filter_reservoir.png)

| Stage | Question | Design choice |
|---|---|---|
| **ExemplarFilter** | Can this measurement compete? | `TraceBased`: only measurements recorded under sampled span context are eligible. |
| **Bucket alignment** | Which statistical region owns it? | Use the same explicit histogram boundaries as the stored sketch. |
| **ExemplarReservoir** | Which eligible measurement survives? | OTel baseline: aligned bounded reservoir. RCA extension: deterministic scenario-aware winner. |

> **RCA extension**  
> Keep OTel eligibility and bucket alignment, but let the winner policy prefer diagnostic usefulness. For **SLOWDOWN**, severe latency can outrank an ordinary request; for **FAULT**, an error/timeout trace can outrank a slower success. `selection_hint` remains heuristic metadata, not a verdict.

---

## 5. OTel-native bucket semantics

For explicit histograms, **N boundaries produce N+1 mutually exclusive bucket counts**. The lower bound is exclusive and the upper bound is inclusive. Aligning the sketch contract to this rule removes ambiguity between metric aggregation and exemplar bucket indexing. [1][2]

```text
bounds = [0, 50, 100, 200, 500, 1000, 2000]

index 0  (-inf, 0]
index 1  (0, 50]
index 2  (50, 100]
index 3  (100, 200]
index 4  (200, 500]
index 5  (500, 1000]
index 6  (1000, 2000]
index 7  (2000, +inf)
```

> **Invariants**
>
> - `N bounds => N+1 counts`
> - Counts are **per-bucket**, not cumulative.
> - `exemplar.bucket_index = i` refers to exactly the same region as `counts[i]`.
> - The parent row `bucket_schema_version` is the single source of bucket semantics.

---

## 6. RED belongs above the sketch mechanics

**RED** stands for **Rate, Errors, and Duration**. It is a service-oriented first-pass health model: Rate asks whether traffic changed, Errors asks whether failures increased, and Duration asks whether latency changed. Grafana describes RED as especially applicable to services and microservice environments. [4]

![RED service-health triage](assets/red_triage.png)

*Figure 5 - RED narrows the service-health lane before deeper sketch inspection.*

> **Design decision**  
> RCA reaches an entity from the graph, uses the investigation type + KPI catalog to identify the relevant RED lane, and only then reads the corresponding sketches. This avoids scanning every metric blindly.

### 5.1 Do not force one sketch shape onto all RED metrics

| RED lane | Evidence shape |
|---|---|
| **Duration** | Naturally distributional. T-Digest + explicit latency buckets + baseline + exemplars are a strong fit. |
| **Rate** | Usually a scalar/rate series. Baseline, deviation, trend and change-point evidence may matter more than a histogram. |
| **Errors** | Often count or ratio based. Error exemplars/traces can be highly useful, but the primary sketch may be scalar/rate. |
| **KPI catalog** | Version the RED-to-metric mapping per service/entity type so triage is deterministic and explainable. |

---

## 7. Sampling determines whether exemplar drill-down works

A metric-side trace pointer is useful only if the trace remains retrievable. Head sampling decides early and cannot use the full trace outcome. Tail sampling can keep traces based on latency, errors, or span attributes after seeing all or most of the trace. A collector cannot recover a trace that an upstream SDK never exported. [3][5]

![Head vs tail sampling](assets/sampling.png)

*Figure 6 - Head vs tail sampling and the dangling-exemplar caveat.*

> **Important caveat**  
> `TraceBased` exemplar eligibility and final backend trace retention are different decisions. With Collector tail sampling, a valid exemplar pointer may occasionally become dangling if the trace is later dropped. Your lookup contract must handle **"trace unavailable"** cleanly.

---

## 8. Sketches cannot reconstruct the raw series

T-Digest, explicit buckets, and exemplars are intentionally **lossy**. They preserve different summaries and a bounded number of original observations, but many different raw datasets can produce the same or near-identical summaries. Therefore the original values, ordering, timestamps, and attributes cannot be uniquely reconstructed after the raw events are discarded.

![Reconstruction capability by evidence layer](assets/reconstruction_matrix.png)

*Figure 7 - Reconstruction capability by evidence layer.*

> **Practical rule**  
> Use sketches to answer **"what changed?"** and exemplars/traces to answer **"show me a concrete execution."** Use raw evidence only when the question requires exact recomputation, alternative bucketing, replay, or complete forensic chronology.

---

## 9. Use tiered evidence retention, not one giant store

![Evidence retention tiers](assets/retention_tiers.png)

*Figure 8 - Long-lived compact summaries, sampled execution evidence, and short-lived reconstructable raw data.*

The clean architecture is tiered. Sketches are compact and can be retained for long periods. Traces are retained according to sampling and diagnostic policy. Raw measurements/events are the expensive fidelity tier and can use shorter default retention. This makes exact reconstruction possible without turning every metric window into a permanent raw archive.

> **Anomaly-aware preservation**  
> Because the sketch writer already evaluates baseline deviation, an anomalous window can optionally extend or pin raw retention around `[window - delta, window + delta]`. This is an operational retention policy, not part of the statistical meaning of `sketch.v2`.

### 8.1 Raw store minimum capability

- Original value and event timestamp.
- Enough identity/attributes to re-join tenant + entity + metric.
- Optional trace/span correlation when present.
- Clear retention, privacy and compliance boundaries.
- Ability to re-query/re-bucket/recompute without depending on the lossy sketch.

---

## 10. Proposed `sketch.v2`

The sketch remains a compact evidence row. Exemplars are top-level bounded evidence pointers; they do not turn the sketch into a trace index. Row anomaly state and exemplar selection hints answer different questions.

![sketch.v2 logical structure](assets/schema_v2.png)

*Figure 9 - `sketch.v2` logical structure.*

```text
sketch.v2
  identity/window: tenant, entity_id, metric_id, window, season_key, window_start/end
  tdigest: compression, encoding, bytes/centroids
  buckets: bucket_schema_version, bounds[N], counts[N+1]
  baseline: expected p50/p95/p99 (or profile-specific baseline)
  anomaly: row-level result
  exemplars[]:
    bucket_index, value, timestamp, trace_id, span_id
    selection_hint { reason, confidence }
```

> **Boundaries**
>
> - For v1 of the exemplar extension: maximum one exemplar per bucket.
> - `selection_hint` belongs to the exemplar only.
> - Trace/span attributes stay in the trace backend.
> - Raw observations stay in the raw evidence store.

---

## 11. Checkout slowdown - complete evidence descent

![Checkout slowdown evidence descent](assets/end_to_end_slowdown.png)

*Figure 10 - Statistical evidence leads to an execution trace, which leads to the next graph hop.*

### 10.1 Why the loop matters

If trace `T123` spends 705 ms in `inventory-api`, RCA should **not** declare `inventory-api` the root cause. The trace is directional evidence. RCA returns to the knowledge graph, moves to `inventory-api`, narrows its KPIs, and inspects the matching time window. Repeated independent evidence across graph, sketches, traces, and optionally raw data raises confidence.

> **Mental model**  
> Graph narrows **where** -> RED narrows **the symptom** -> KPI catalog narrows **metrics** -> Sketch establishes **population abnormality** -> Exemplar picks **a concrete case** -> Trace shows **one execution** -> Raw evidence escalates to **exact re-analysis** -> investigation returns to Graph.

---

## 12. Design decisions from the study

| Decision | Freeze candidate |
|---|---|
| **Exemplar meaning** | Exact trace/span for the retained observation; not a root-cause verdict. |
| **Logical placement** | Top-level `exemplars[]` in the same sketch row for quick evidence access. |
| **Cardinality** | At most one exemplar per bucket in the first version. |
| **Bucket semantics** | OTel-native `N bounds -> N+1` non-cumulative counts. |
| **Eligibility baseline** | `TraceBased` exemplar filter. |
| **Retention baseline** | Bucket-aligned reservoir structure; custom scenario-aware winner policy. |
| **Scenario source** | Combination of metric semantics, detector verdict, and active RCA context; high-confidence detector may override. |
| **Anomaly state** | Belongs to the sketch row and is produced by baseline comparison. |
| **RED role** | Service-health triage layer before deep sketch inspection. |
| **Raw reconstruction** | Not possible from sketches alone; preserve a separate raw evidence tier for exact re-analysis. |
| **RCA behavior** | Trace evidence chooses what to inspect next; it does not terminate reasoning. |

---

## 13. Q&A - the important misconceptions

### Does an exemplar give the exact trace ID?

Yes, when trace context is present it gives the exact trace/span context for that retained measurement. It does **not** guarantee that execution explains the incident.

### Can one exemplar represent an entire bucket?

No. It is one original measurement from the bucket population. The count represents the population.

### Does `TraceBased` mean "keep the slowest"?

No. `TraceBased` only controls eligibility based on sampled span context. Reservoir logic decides what survives.

### Can Collector tail sampling recover a trace dropped by head sampling?

No. If upstream never exports it, downstream cannot resurrect it.

### Can T-Digest + buckets reconstruct raw values?

No. They can approximate distribution and range counts, but exact raw observations require separate retention.

### Where does RED fit?

Between graph context and deep sketch inspection. It identifies whether Rate, Errors, or Duration is the relevant service-health lane.

### Should Rate and Errors always use the same distribution sketch as Duration?

No. Use metric-semantic profiles; rate/error evidence may be scalar/rate oriented while Duration remains distribution oriented.

---

## 14. Open implementation items

- Define the language-SDK integration path for a custom bucket-aligned `ExemplarReservoir`.
- Freeze `selection_hint.reason` enum and confidence semantics.
- Define dangling-exemplar behavior in the trace lookup contract.
- Choose tail-sampling policies and resource budgets for the lab.
- Version bucket boundary tables per metric family.
- Define RED-to-KPI mappings per request-driven `ci_type`.
- Introduce metric profile types: distribution vs scalar/rate rather than forcing one universal shape.
- Define raw evidence store fields, default retention and anomaly-aware extension policy.
- Benchmark sketch row size and Vortex physical representation for T-Digest bytes + bounded exemplars.
- Add contract tests: `counts.length == bounds.length + 1`; `exemplar.bucket_index < counts.length`.

---

## 15. Sources

1. OpenTelemetry Metrics SDK - exemplars, filters and reservoirs  
   https://opentelemetry.io/docs/specs/otel/metrics/sdk/
2. OpenTelemetry Metrics Data Model - exemplar fields and histogram semantics  
   https://opentelemetry.io/docs/specs/otel/metrics/data-model/
3. OpenTelemetry Sampling - head and tail sampling concepts  
   https://opentelemetry.io/docs/concepts/sampling/
4. Grafana - RED method: Rate, Errors, Duration for services  
   https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
5. OpenTelemetry - Tail sampling in the Collector  
   https://opentelemetry.io/blog/2022/tail-sampling/
6. OpenTelemetry Java API - Context and metric recording  
   https://opentelemetry.io/docs/languages/java/api/
7. OpenTelemetry Trace API - SpanContext, TraceId and SpanId  
   https://opentelemetry.io/docs/specs/otel/trace/api/

> **Status**  
> This document is a design guide and freeze candidate. The RED integration, raw retention policy, custom exemplar winner logic, and physical Vortex encoding remain implementation choices until signed.
