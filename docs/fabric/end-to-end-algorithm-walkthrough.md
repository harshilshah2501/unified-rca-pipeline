# End-to-End Algorithm Walkthrough

This document explains how `tdigest-test.py` turns raw latency events into a
`sketch.v1` record and then uses that record to detect and localize an incident.
The code generates synthetic data so the pipeline can be run repeatedly without
a production data source.

## Pipeline Overview

```text
raw events this window  (latency_ms, trace_id)     window_start timestamp
        |                                                    |
        +--> T-Digest --------> p50 / p95 / p99               |
        |                                                    |
        +--> fixed buckets ---> counts                       |
        |         |                                          |
        |         +--> exemplars (one trace_id per bin)       |
        |                                                    v
        |                                           season_key (e.g. Thu-09:00)
        |                                                    |
        |                                                    v
        |                              PAST windows with same season_key
        |                              (not this window's raw samples)
        |                                                    |
        |                                                    v
        |                                         seasonal baseline
        |                                         (expected p50/p95/p99)
        v
T-Digest + buckets (+ exemplars) + baseline + metadata  -->  sketch.v1
        |
        +--> DETECT:    digest p95  vs  baseline expected p95
        +--> LOCALIZE:  heaviest high-latency bin + its exemplar trace
```

**Important:** baseline is **not** built from this window’s raw events. Exemplars **are** taken from this window’s events (each event must carry a real `trace_id`). T-Digest and buckets both read the same current-window latencies; they answer different questions:

| Algorithm | Stores or computes | Best for |
| --- | --- | --- |
| T-Digest | Compact weighted centroids | Percentiles such as p95 and p99 |
| Buckets | Counts in fixed latency ranges | Distribution shape and localization |
| Seasonal baseline | Expected percentiles from history | Contextual anomaly detection |

## Stage 0: Generate The Input Data

The call in the main program is:

```python
samples = stage0_ingest(spike=True)
```

Because `spike=True`, the function creates two groups of latency values:

```python
normal = np.random.lognormal(mean=5.4, sigma=0.4, size=4900)
slow = np.random.lognormal(mean=7.0, sigma=0.4, size=100)
```

Therefore:

```text
4,900 normal latencies
+  100 slow latencies
---------------------
5,000 total latencies
```

The two arrays are concatenated and shuffled:

```python
latencies = np.concatenate([normal, slow])
np.random.shuffle(latencies)
```

Each value is paired with a trace ID:

```python
trace_ids = [f"trace-{i:06d}" for i in range(len(latencies))]
samples = list(zip(latencies, trace_ids))
```

A resulting event has this shape:

```python
(181.8, "trace-000000")
```

The first item is the latency in milliseconds. The second item identifies the
original request. `np.random.seed(7)` makes the generated sequence repeatable.

The trace ID is useful for investigation, but T-Digest receives only the
latency value.

## Stage 1: Build T-Digest

The digest is initialized with `delta=0.1`:

```python
digest = TDigest(delta=0.1)
for latency, _trace_id in samples:
    digest.update(latency)
```

### What A Centroid Contains

A centroid is a compact summary with a mean and a count:

```text
{ "mean": representative latency, "count": represented samples }
```

The serialized form in the project uses `m` for mean and `w` for count:

```json
{ "m": 116.67, "w": 3.0 }
```

### Hand-Worked Centroid Example

Suppose nearby input values are `100`, `120`, and `130` milliseconds.
Initially, the first value creates:

```text
mean = 100, count = 1
```

When `120` is accepted into that centroid:

```text
new_count = 1 + 1 = 2
new_mean  = 100 + (120 - 100) / 2 = 110
```

When `130` is accepted:

```text
new_count = 2 + 1 = 3
new_mean  = 110 + (130 - 110) / 3 = 116.67
```

The centroid now represents three values with the same mean as their arithmetic
average:

```text
{ mean: 116.67, count: 3 }
```

For a weighted update, where an incoming centroid has weight `w`, the formulas
are:

```text
new_count = old_count + w
new_mean  = old_mean + w * (value - old_mean) / new_count
```

### How Compression Chooses Centroids

For each incoming latency, the library finds a nearby centroid. It merges the
value when that centroid is still below its size limit; otherwise it creates a
new centroid. The limit depends on the value's quantile position:

```text
threshold(q) = 4 * total_count * delta * q * (1 - q)
```

Here `q` is the centroid's approximate position from 0 to 1. Since
`q * (1 - q)` is smaller near 0 and 1, tail centroids remain relatively small.
That gives T-Digest more detail near p95, p99, and other extreme percentiles.
Centroids near the middle can represent more samples.

The result from this run is approximately:

```text
5,000 input latencies -> 101 centroids
```

The exact count depends on the library version and update/compression behavior.
The raw samples are not retained inside the digest.

### Read Percentiles From The Digest

The script asks for three percentiles:

```python
p50 = digest.percentile(50)
p95 = digest.percentile(95)
p99 = digest.percentile(99)
```

Conceptually, the target positions in 5,000 samples are:

| Percentile | Target region |
| --- | ---: |
| p50 | Around sample 2,500 in sorted order |
| p95 | Around sample 4,750 |
| p99 | Around sample 4,950 |

T-Digest walks centroids in sorted order, accumulates their counts, and
interpolates between neighboring centroid means when a target falls between
them. It does not sort and retain all 5,000 values for the query.

For this incident-shaped window, the output is approximately:

```text
p50 = 222.3 ms
p95 = 454.8 ms
p99 = 1164.9 ms
```

These are estimates. The useful tradeoff is that the digest is much smaller
than the raw event list and can be merged with other digests.

## Stage 2: Build Fixed Buckets And Exemplars

The bucket boundaries are:

```python
BOUNDS = [0, 50, 100, 200, 500, 1000, 2000]
```

They define these half-open ranges:

```text
[0, 50)       0 <= latency < 50
[50, 100)     50 <= latency < 100
[100, 200)    100 <= latency < 200
[200, 500)    200 <= latency < 500
[500, 1000)   500 <= latency < 1000
[1000, 2000)  1000 <= latency < 2000
```

For example, a latency of `181.8` belongs to `[100, 200)`, while a latency of
`500` belongs to `[500, 1000)`.

The counts are computed with NumPy:

```python
latencies = np.array([lat for lat, _ in samples])
counts, _ = np.histogram(latencies, bins=BOUNDS)
```

The same samples also provide one exemplar trace ID per bin. The current code
keeps the first event encountered in each bin:

```python
if BOUNDS[i] <= latency < BOUNDS[i + 1]:
    if exemplars[i] is None:
        exemplars[i] = trace_id
```

For example, if the first event in `[200, 500)` is:

```python
(241.6, "trace-000001")
```

then that bin stores `trace-000001` as its exemplar. The exemplar is not a
representative statistical value; it is a concrete request to inspect.

This run produces approximately:

| Bin | Count | Exemplar |
| --- | ---: | --- |
| `[0, 50)` | 0 | None |
| `[50, 100)` | 131 | `trace-000016` |
| `[100, 200)` | 1,851 | `trace-000000` |
| `[200, 500)` | 2,836 | `trace-000001` |
| `[500, 1,000)` | 117 | `trace-000023` |
| `[1,000, 2,000)` | 58 | `trace-000040` |

The six bucket counts sum to 4,993. The remaining 7 values are at least
2,000 ms and are outside the configured bucket range. T-Digest still includes
those values, which is an important difference between the two summaries.

## Stage 3: Build A Seasonal Baseline

The baseline must describe normal historical traffic, not the current incident.
The pipeline generates 12 prior windows using the non-spike distribution:

```python
for _ in range(12):
    historical_window = stage0_ingest_quiet()
```

Each historical window gets its own p50, p95, and p99 using NumPy's exact
percentile calculation. The baseline then takes the mean of those 12 values:

```python
baseline = {
    "expected_p50": mean(all_historical_p50),
    "expected_p95": mean(all_historical_p95),
    "expected_p99": mean(all_historical_p99),
}
```

The resulting baseline is:

```json
{
  "baseline_version": "seasonal_v1",
  "expected_p50": 90.4,
  "expected_p95": 172.6,
  "expected_p99": 549.2
}
```

The key distinction is:

```text
current digest     = current 5-minute window, including the incident
seasonal baseline  = 12 previous normal Thu-09:00 windows
```

## Stage 4: Assemble One `sketch.v1` Row

The pipeline stores metadata and all three summaries together:

```json
{
  "schema_version": "sketch.v1",
  "entity_id": "checkout-api",
  "metric_id": "request.latency_ms",
  "window": "5m",
  "sample_count": 5000,
  "tdigest": "compressed percentile summary",
  "buckets": "fixed counts and exemplars",
  "baseline": "expected seasonal percentiles"
}
```

The digest portion stores centroid data such as:

```json
{
  "compression": 0.1,
  "encoding": "centroids_json",
  "centroids": [
    { "m": 53.85, "w": 1.0 },
    { "m": 56.47, "w": 1.0 },
    { "m": 60.1, "w": 1.0 }
  ]
}
```

In the demonstration output, only a few centroids are printed followed by
`"... more"`; a production record would need a real serialization policy for
the complete digest.

## Stage 5: Detect And Localize

Detection compares the current p95 to the seasonal expected p95:

```python
ratio = digest_percentiles["p95"] / baseline["expected_p95"]
abnormal = ratio > 1.5
```

Using the values from this run:

```text
ratio = 454.8 / 172.6
      = 2.64x
```

Since `2.64 > 1.5`, the verdict is `ABNORMAL` for `Thu-09:00`.

Detection uses T-Digest because p95 is compactly available from the digest.
Localization then uses buckets because bucket counts show where the latency
mass is concentrated:

```text
high-latency bins: [200, 500), [500, 1000), [1000, 2000)
heaviest bin:     [200, 500) with 2,836 samples
exemplar:         trace-000001
```

An operator or RCA system can now open `trace-000001` and inspect one concrete
request. The workflow moves from an aggregate signal to a candidate request:

```text
T-Digest detects the abnormal percentile
Buckets locate the affected latency range
Exemplar points to a real request
Trace inspection investigates the cause
```

## Why The Algorithms Work Together

No single structure provides every capability:

- T-Digest gives accurate, mergeable percentile estimates but does not retain
  trace IDs or explain which range contains the most traffic.
- Buckets make distribution regions and exemplars easy to inspect, but their
  percentile estimates are coarse and values outside the top bound are omitted.
- The seasonal baseline provides context, because a latency can be normal for
  one time period and abnormal for another.

Together, they produce a compact record that supports both fast detection and
practical investigation.

## One-Page Summary

```text
1. Generate 4,900 normal + 100 slow = 5,000 current latencies.
2. Feed each latency into T-Digest; keep roughly 101 weighted centroids.
3. Read approximate p50, p95, and p99 from the sorted centroids.
4. Count the same latencies into fixed bins and keep one trace exemplar/bin.
5. Compute expected percentiles from 12 prior normal seasonal windows.
6. Store digest, buckets, baseline, and metadata in sketch.v1.
7. Compare current p95 with expected p95; 2.64x exceeds the 1.5x threshold.
8. Choose the busiest high-latency bucket and inspect its exemplar trace.
```

---

## FAQ

### Q1. How is `season_key` computed? What does it look like?

**A.** From the window’s timestamp (timezone-aware), using **hour-of-week** in the tenant timezone.

In the PoC helper (`HourOfWeekSeason`):

```python
# e.g. 2026-08-20T09:17:00+00:00  (a Thursday)
return f"{ts.strftime('%a')}-{ts.hour:02d}:00"
# -> "Thu-09:00"
```

| Piece | Meaning |
|-------|---------|
| `Thu` | Weekday abbreviation from the timestamp |
| `09:00` | Clock hour floored (minutes/seconds dropped) |

**What it looks like in the sketch row:** a short string such as `"Thu-09:00"`, `"Mon-14:00"`, `"Sun-02:00"`. Schema pattern in the contract: `^[A-Z][a-z]{2}-[0-2][0-9]:[0-5][0-9]$`.

**Why it exists:** Tuesday 09:00 traffic ≠ Sunday 02:00. Detect compares this window’s percentiles to the baseline stored under the **same** `season_key`, not to “all history forever.”

In this walkthrough the demo labels the slot `Thu-09:00` and builds the baseline from 12 prior **quiet** windows treated as that same season. Production would derive `season_key` from each window’s real `window_start` and accumulate baselines per key over time (Maintain / E5).

### Q2. Do raw samples also feed the baseline and the exemplars?

**A. Exemplars: yes (this window). Baseline: no (not this window’s raw list).**

| Consumer | Input | Not this |
|----------|--------|----------|
| **T-Digest** | This window’s **latency values** | Does not keep `trace_id` |
| **Buckets** | This window’s **latency values** → bin counts | — |
| **Exemplars** | This window’s **full events** `(latency, trace_id)` — pick one `trace_id` per bin (demo: first seen in that bin) | Not built from the digest; not from a random subsample of the series |
| **Seasonal baseline** | **Past** windows that share this `season_key` (their p50/p95/p99, then mean) | **Not** the current incident window’s raw samples |

So the old “raw events fan out three ways into digest / buckets / baseline” picture was misleading. Correct fan-out:

- **This window’s latencies** → digest + bucket counts.
- **This window’s (latency, trace_id)** → exemplars hanging on bins.
- **This window’s timestamp** → `season_key` → **lookup / attach** baseline built earlier from **history**.

### Q3. “Exemplars don’t operate on sampled data” — is that right?

**A.** Yes, in the sense that matters for RCA.

- Exemplars are **not** another statistical summary of the latency distribution (unlike digest or bucket counts).
- They need **identity-bearing events**: at least latency + a real `trace_id` (and ideally span context). You cannot invent an exemplar from T-Digest centroids alone.
- They are also **not** “we randomly sampled 1% of metrics for Detect.” Detect still uses digest + baseline. Exemplars are an optional **pointer** from a hot bin to one concrete request for investigation.

In this demo, every one of the 5,000 events can update counts; each bin keeps **one** exemplar (first hit). That is “one representative request per bin,” not “operate on a downsampled metric stream.” Production may keep a small set of exemplars per bin (e.g. max latency in bin); still event-linked, still not a replacement for digest/baseline.

### Q4. Reminder: what is enough for Detect vs investigate?

**A.** Digest + baseline → Detect (p95 vs expected). Buckets + exemplars → after Detect, which range and which trace to open. That split is general for this percentile-vs-season design, not only this synthetic run.
