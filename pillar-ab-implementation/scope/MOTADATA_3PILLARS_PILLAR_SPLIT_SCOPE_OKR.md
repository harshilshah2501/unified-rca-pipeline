# Motadata 3 pillars explained -> implementation scope and gap register

> **Superseded for sharing:** use the merged guide  
> [`../deliverables/Motadata_3Pillars_Merged_Implementation_Guide.pdf`](../deliverables/Motadata_3Pillars_Merged_Implementation_Guide.pdf)  
> (canonical markdown: [`MOTADATA_3PILLARS_MERGED_SCOPE.md`](../../docs/MOTADATA_3PILLARS_MERGED_SCOPE.md)).  
> Slice home: [`pillar-ab-implementation/`](../README.md).  
> This file remains as the shorter Gaps-only draft that was merged in.

**Date:** 2026-08-20  
**Audience:** engineering + management  
**Source context:** `KR Plan/Motadata_Observability_3_Pillars_Architecture_Explained.pdf`  
**Companion docs:** `MOTADATA_3PILLARS_IMPLEMENTATION_SCOPE.md`, `../../MOTADATA_3PILLARS_STUDY_QNA.md`, `../../OBSERVEOPS_PIPELINE_HLD.md`

---

## 1) Purpose of this document

This document is the plain-language, implementation-first version of the Motadata explained PDF mapping.  
It answers five detailed Pillar-A questions, defines Pillar-B scope, and lists gaps/unknowns with clear ownership tracks:

- **Pillar 1 owner (teammate):** statistics + graph builder data plane
- **Pillar 2 owner (you):** entities + edges + changes graph semantics

The intent is to remove "riddle statements" by always stating **What, Why, How**.

---

## 2) Two-pillar split used in this plan

### Pillar 1 (Teammate): T-Digest + explicit buckets + seasonal baselines + graph-builder write path

Scope in practice:
- metric sample selection
- sketching (T-Digest + buckets)
- seasonal baseline generation
- sketch row schema per metric/entity/window/season
- write path to S3 (durable archive) and read indexing via Vortex (analytical retrieval)
- access control ("who reads it")

### Pillar 2 (You): entities + edges + changes

Scope in practice:
- CI/entity definitions and identity constraints
- relationship/edge model with provenance and validity
- change facts and change-to-CI linkage rules
- graph shape constraints for localize/package consumers

---

## 3) Pillar 1 deep-dive (What / Why / How)

## 3.1 How samples are chosen?

**What**  
Choose metric samples by deterministic keys:
- `tenant`
- `entity_id` (or `ci_id` equivalent after E2 identity)
- `metric_id`
- `window` (for example 1m, 5m, 1h, 1d)
- timestamp

Only resolved identity rows are sketch-writer eligible.

**Why**  
Without deterministic sample admission, percentile and baseline outputs become non-reproducible across runs and teams.

**How**  
1. Admit only `ingest.v1` metric lines with `identity.status = resolved`.
2. Normalize metric naming (`request.latency_ms`, `cpu.utilization_pct`, etc.).
3. Assign each point to one or more configured windows (multi-resolution allowed).
4. Derive `season_key` from timestamp (for example `Mon-09:00`, `Fri-18:00`).
5. Feed sample value into:
   - T-Digest state for the key
   - explicit bucket histogram for the key
   - seasonal baseline accumulator for the key

---

## 3.2 What does T-Digest do? What is "mergeable p50/p95/p99"?

**What**  
T-Digest is a compressed representation of a value distribution.  
It supports fast quantile queries (`p50`, `p95`, `p99`) without storing all raw samples.

**Why**  
Raw history scans become too expensive at scale. T-Digest gives near-real-time percentile lookup with bounded storage.

**How**  
1. Each key `(tenant, entity_id, metric_id, window, season_key)` has a digest state.
2. New values update centroids (compression step).
3. Query asks for quantile `q` and returns estimate from digest.
4. **Mergeable** means digest A + digest B -> digest AB:
   - merge per host -> per service
   - merge per minute -> per 5-minute rollup
   - merge shard results -> tenant/global aggregate

Operational meaning:
- `p50`: median behavior (normal center)
- `p95`: high-tail service behavior (SLO-sensitive)
- `p99`: rare tail stress/spike behavior

---

## 3.3 How explicit bucketing is done?

**What**  
Explicit bucketing is a fixed histogram with predefined boundaries.

**Why**  
Buckets make thresholding, alert rules, and "which range dominates?" questions deterministic and easy to explain.

**How**  
1. Define bucket sets per metric family:
   - latency: `[0-50), [50-100), [100-200), ...`
   - CPU%: `[0-20), [20-40), [40-60), ...`
2. For each sample, increment exactly one bucket count.
3. Keep total count, min/max, and optional sum for sanity checks.
4. Version bucket policy (`bucket_schema_version`) to prevent silent drift.
5. Never mix bucket versions in one logical sketch key.

---

## 3.4 Sketch row format: one row per metric + entity + window + season_key -> Vortex/S3

**What**  
Each row is a compact statistical state for one logical key.

**Why**  
This shape is the contract that allows:
- durable archival in S3
- analytical read/index in Vortex
- reproducible E6/E10 retrieval without raw re-scan

**How (recommended schema v1)**

```json
{
  "schema_version": "sketch.v1",
  "tenant": "default",
  "entity_id": "checkout-api",
  "entity_type": "Service",
  "metric_id": "request.latency_ms",
  "window": "5m",
  "window_start": "2026-08-20T03:30:00Z",
  "window_end": "2026-08-20T03:35:00Z",
  "season_key": "Thu-09:00",
  "tdigest": {
    "compression": 100,
    "centroids": [
      {"m": 92.1, "w": 14},
      {"m": 145.3, "w": 9}
    ]
  },
  "buckets": {
    "bucket_schema_version": "latency_v1",
    "counts": [12, 19, 5, 1, 0, 0],
    "bounds": [0, 50, 100, 200, 500, 1000, 2000]
  },
  "baseline": {
    "expected_p50": 88.0,
    "expected_p95": 170.0,
    "expected_p99": 320.0,
    "baseline_version": "seasonal_v1"
  },
  "sample_count": 23,
  "ingest_trace": {
    "writer": "pillar-a-sketch-writer",
    "written_at": "2026-08-20T03:35:05Z"
  }
}
```

### S3 write model

- Partition recommendation:
  - `tenant=.../metric_id=.../window=.../date=YYYY-MM-DD/`
- Write mode:
  - append immutable rows (no in-place mutation)
  - idempotent object naming using key hash + window end
- Rollups:
  - optional periodic compaction by day/week

### Vortex indexing/read model

- Primary lookup index:
  - `(tenant, entity_id, metric_id, window, season_key, window_start)`
- Secondary filters:
  - `entity_type`, date range
- Query patterns to optimize first:
  1. latest p95 for entity+metric
  2. compare current window vs seasonal baseline
  3. retrieve N prior windows for trend

---

## 3.5 How "WHO READS IT" is handled?

**What**  
A role-based read policy for sketch data.

**Why**  
Different consumers need different access levels; unrestricted reads risk data leakage and noisy operations.

**How (minimum RBAC plan)**

- `role_observability_reader`
  - read sketch rows and baselines
  - no policy changes
- `role_detect_engine`
  - read for door-C thresholding
  - service account only
- `role_rca_engine`
  - read for E10 evidence correlation
- `role_admin_data`
  - manage retention, index configs, and schema versions

Controls:
1. tenant-scoped authorization mandatory
2. audit log for each read query (who/what/when)
3. deny-by-default for cross-tenant reads
4. schema-version compatibility checks before query execution

---

## 4) Pillar 2 deep-dive (What / Why / How)

## 4.1 Entities

**What**  
CIs with stable identity (`tenant + ci_id`) and typed class (`Service`, `Host`, optional `Pod` with validity window).

**Why**  
Localize/package must point to durable operational targets, not transient noise objects.

**How**
- allow only resolved identity records for canonical graph vertices
- enforce `ci_type` catalog + versioning
- carry aliases as metadata, not alternative primary keys

## 4.2 Edges

**What**  
Typed CI-CI relationships (for example `depends_on`, `runs_on`, `communicates_with`) with provenance and validity.

**Why**  
E8/E9 walk quality depends on relationship semantics and freshness.

**How**
- each edge stores:
  - source/target IDs
  - relation type
  - provenance (`authoritative|declared|corroborating`)
  - `valid_from`, `valid_to` or equivalent freshness fields

## 4.3 Changes

**What**  
Time-bound facts linked to CIs (deploy/config/release/change-ticket references).

**Why**  
Change context improves root-cause explainability without polluting CI topology.

**How**
- store change as fact records, not CI vertices
- link by CI identity and time overlap
- keep change ingestion out of E1 for this block; attach via reserved path/future phase

---

## 5) Gaps / unknowns and candidate resolutions

## 5.1 Pillar 1 gaps (Teammate)

1. **Metric catalog not frozen**  
   - Resolution: approve initial metric shortlist + metric naming standard
2. **Bucket boundaries undefined per metric family**  
   - Resolution: publish `bucket_schema_version` per family
3. **Season-key policy not fixed**  
   - Resolution: start with hour-of-week key; revise only with version bump
4. **S3 partition/idempotency policy not frozen**  
   - Resolution: define path template + deterministic object key
5. **Vortex index plan not explicit**  
   - Resolution: lock 3 priority query patterns and design index around them
6. **Reader roles not codified**  
   - Resolution: publish RBAC matrix and service-account boundaries

## 5.2 Pillar 2 gaps (You)

1. **Entity type taxonomy not frozen for v1**  
   - Resolution: freeze minimal set (Service, Host; optional Pod with guardrails)
2. **Edge catalog still broad/ambiguous**  
   - Resolution: freeze mandatory edge set for v1 and defer extras
3. **Edge freshness/validity semantics not finalized**  
   - Resolution: choose explicit validity model and TTL/decay rules
4. **Change-fact model not contractually defined**  
   - Resolution: define `change.fact.v1` structure + CI/time link rules
5. **Graph write ownership and publication cadence unclear**  
   - Resolution: define E3 writer owner + E5 refresh cadence and SLA

---

## 6) Final implementation scope summary

In scope now:
- Pillar 1 statistical plane and its storage/retrieval/access contracts
- Pillar 2 CI graph and change-fact semantics
- Mapping to existing E3-E5 workstream with explicit stage boundaries

Out of scope now:
- making ReAct mandatory (D5 remains Review)
- remediation execution in this block
- treating alert/incident/ticket as E3 topology vertices

---

## 7) Deliverables from this plan

1. This canonical markdown spec  
2. Final shareable PDF in `KR Plan/`  
3. Follow-up link from docs hub/index as needed

