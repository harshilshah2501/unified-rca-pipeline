# Ingestion Pipeline Design — Vector as Shared Fabric

**Status:** Design (not implemented end-to-end)  
**Scope:** **Ingestion + detection front door** — builds RCA-ready graphs / incident windows **and** marks anomalies / seeds. Does **not** implement Lean or Federated localization.  
**Related:** [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) · [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) · [`RCA-learning-cheatsheet.md`](../RCA-learning-cheatsheet.md) §1c–§3 · [`federated-pipeline/docs/STORAGE_TIERS.md`](../federated-pipeline/docs/STORAGE_TIERS.md) · [`NAVIGATION.md`](./NAVIGATION.md)

---

## 1. Boundary (read first)

```
 Collectors / APIs / replay files
              │
              ▼
┌─────────────────────────────────────────┐
│         INGESTION PIPELINE              │
│  Vector (collect → transform → route)   │
│  + DETECTION front door (required)      │
│      thresholds / alerts / optional     │
│      richer detector (≠ Lean itself)    │
│  + post-Vector graph builders           │
│  + topology crawler (beside Vector)     │
└─────────────────────────────────────────┘
              │
              ▼  RCA-ready artifacts (graphs / windows
                 + symptom_seed + crossed anomalies)
     ┌────────┴────────┐
     ▼                 ▼
  Lean RCA         Federated RCA
  (localize)       (detect-in-stack via Panorama
                    + localize; or reuse shared
                    detection front door)
```

| Layer | Owns | Does not own |
|-------|------|----------------|
| **Ingestion + detection** | Collect, normalize, **mark anomalies / raise seeds**, route, materialize stores/slices | Root-cause decision (who is *the* root) |
| **RCA — Lean** | Localize over prepared graphs/windows | Fleet-wide collection; **primary anomaly detection** |
| **RCA — Federated** | May include Panorama as in-stack detector **or** consume shared front-door detections; then Murphy/Nezha | Replacing shared collect fabric |

**Why detection must be in-system (product):** Lean never invents crossings. Without a detector/alerter, `diagnose` is never triggered. PoC hides this by pre-baking `anomalies.json` + `symptom_seed.json`.

**Today’s PoC:** ingestion + detection are largely **synthesized** (`datasets/observeops/*/`). This design replaces that synthesis with a real (or replay-driven) Vector-based path **including an explicit detection stage** for cost measurement and later product.

---

## 1b) Detection front door (required; not Panorama-inside-Lean)

| Option | What it is | Fits Lean | Fits Federated | Relative detect cost |
|--------|------------|-----------|----------------|----------------------|
| **A. Threshold / alert rules** | Metric/event vs threshold → `crossed` + seed | Default for classic infra | Usable as trigger | ★★ (usually cheapest) |
| **B. Vector transform detect** | Remap/filter marks `signal_class: anomaly` | Good with ingest PoC | Same | ★★–★★★ |
| **C. Existing ObserveOps alerter** | Product already raises tickets | Best reuse | Same | ★ (if already paid) |
| **D. Panorama-class gray-failure detector** | Observer/majority voting | Optional later if thresholds miss gray failures | Native federated hop | ★★★★ |

**Product recommendation:** ship **A/B/C as mandatory** for Lean path; treat **D as optional upgrade** (Federated track or Lean add-on), not a Lean prerequisite.

**Cost impact (important):** detection runs on **streams** (continuous), while Lean RCA runs on **incidents** (sparse). So `C_detect` often dominates `C_rca_runtime` in steady state — especially if you choose Panorama-class detection for every ticket. That is why Lean’s advantage remains “cheap localization,” but **total system cost must include detection**.

```
Total ops cost ≈ C_collect + C_detect + C_normalize + C_store + C_query_feed + C_ops
                 + C_rca_runtime
```

PoC bakeoff compared mainly `C_rca_runtime` (+ synthetic inputs). Ingestion PoC must measure **`C_detect` explicitly** (threshold path vs richer detector profile).

---

## 2. Design goals

1. **One ingest fabric** for both RCA consumers (not two collector fleets).  
2. **Explicit detection stage** before Lean (and optionally shared with Federated).  
3. **Lean-cheap by default** — optional Federated / Panorama-class sinks add cost only when enabled.  
4. **Measurable** — same profiles feed Lean-only vs dual-sink; detection profile (threshold vs rich) is a separate cost axis.  
5. **Schema-stable handoff** — RCA engines consume versioned artifact contracts, not raw vendor formats.  
6. Align with deferred Phase C “normalizer / dual-stream” vision without locking to NATS-only.

---

## 3. RCA-ready artifact contracts (what ingestion must emit)

Ingestion succeeds when these artifacts exist and stay fresh enough for diagnose. Field names below are **contract targets**; adapters may map to today’s bundle JSON.

### 3.1 Shared / core

| Artifact ID | Description | Typical store |
|-------------|-------------|---------------|
| `A-TOPO` | Typed CI topology graph (nodes + typed edges) | Structural store / file snapshot |
| `A-ANOM` | Anomaly / threshold-crossing windows (CI, metric, onset, value, threshold) | Hot TS / incident slice |
| `A-SEED` | Symptom seed (starting CI + incident time) | Incident record |
| `A-EVT` | Structured events (optional; SNMP/syslog-style lines bound to CI) | Hot event log / file |

### 3.2 Lean consumer view

Lean diagnose (today) expects a **bundle** equivalent to:

| File / object | Maps from | Required |
|---------------|-----------|----------|
| `topology.json` | `A-TOPO` | Yes |
| `anomalies.json` | `A-ANOM` | Yes |
| `symptom_seed.json` | `A-SEED` | Yes |
| `events.json` | `A-EVT` | UC-2 / UC-4 / UC-3b class |
| `ground_truth.json` | Eval only — **not** produced by product ingest | Eval only |

Lean does **not** require a high-velocity execution event graph for classic infra.

### 3.3 Federated consumer view

| Artifact | Maps from | Used by |
|----------|-----------|---------|
| Structural / knowledge graph slice | `A-TOPO` (+ metric associations) | Murphy / Panorama context |
| Metric / LOS-style windows | `A-ANOM` (+ continuous series) | Murphy SimulatedStore → prod store |
| Speed-tier event graph keys | Derived from `A-EVT` + traces/logs | Nezha (`tg:` / `pc:` style) |
| Detection / trigger context | Alert or Panorama-like flag | Orchestrator hop 1 |

Federated **adds** continuous high-volume event/path materialization on top of the shared core.

### 3.4 Canonical intermediate event (Vector output schema)

All Vector transforms should converge toward a common envelope before sinks diverge:

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T12:00:00Z",
  "tenant": "default",
  "ci_id": "esxi-host-01",
  "ci_type": "HypervisorHost",
  "signal_class": "anomaly|event|metric_sample|trace_span|topo_update",
  "name": "cpu.usage.average",
  "value": 92.0,
  "threshold": 80.0,
  "severity": 1.15,
  "labels": { "source": "vector", "uc_hint": null },
  "raw_ref": "optional pointer to original bytes"
}
```

Topology updates use `signal_class: "topo_update"` with edge payloads in `labels` / nested `topo` object (see §5).

---

## 4. Topology path (beside Vector)

Vector is weak as a **CMDB/topology crawler**. Treat topology as a **sibling ingest path** that still lands in the same structural store.

```
vCenter / CMDB / K8s API / static export
        │
        ▼
 Topology crawler (small service / cron)
        │
        ▼
  A-TOPO writer ──► structural store / topology.json snapshot
        │
        └── optional: emit topo_update events into Vector for audit fan-out
```

| Source | PoC | Product |
|--------|-----|---------|
| Static export from ObserveOps corpus | Primary | Fallback / lab |
| vCenter / inventory API | Stub | Primary for classic infra |
| K8s / service map | Out of ObserveOps classic scope | Federated microservice track |

**Rule:** RCA never parses vendor topology APIs directly; it only reads `A-TOPO`.

---

## 5. Vector topology (shared collect → split sinks)

```
                    ┌── transform: parse_metrics ──┐
 sources ──────────►│── transform: parse_logs    ──┼── remap → ingest.v1 ──┬── sink: lean_incident
                    └── transform: parse_events  ──┘                       ├── sink: speed_tier_feed
                                                                           ├── sink: anom_store
                                                                           └── sink: archive (optional)
 topology crawler ──────────────────────────────────────────────────────────► A-TOPO store
```

### 5.1 Sources (PoC → product)

| Source type | PoC use | Product use |
|-------------|---------|-------------|
| `file` / `demo_logs` | Replay UC-derived JSONL | Debug |
| `http_server` | Push synthetic load | Webhooks |
| `syslog` / `socket` | Lab SNMP/syslog | Edge |
| `prometheus_scrape` | Metrics scrape | Classic + cloud |
| `opentelemetry` / Datadog agent | Optional | Preferred unified OT |

### 5.2 Transforms (normalize + CI bind)

| Transform | Responsibility |
|-----------|----------------|
| Parse | Vendor → fields |
| **CI bind** | Map host/IP/VM name → `ci_id` via lookup table from `A-TOPO` |
| Threshold / anomaly detect | Or pass through pre-detected anomalies |
| Filter | Drop noise; sample traces for Federated path |
| Route tags | `route=lean|federated_speed|both` |

CI bind failure → dead-letter sink (do not invent roots in RCA).

### 5.3 Sinks → post-Vector builders

| Sink (Vector) | Post-processor | Artifact | Consumer |
|---------------|----------------|----------|----------|
| HTTP / file → incident dir | `lean_bundle_writer` | Lean UC-shaped bundle | Lean RCA |
| Redis / Dragonfly / Kafka | `speed_tier_builder` | `tg:` / `pc:` (or equiv.) | Federated / Nezha |
| TSDB / Redis | `anomaly_indexer` | `A-ANOM` windows | Lean + Murphy |
| Object store | Archive | Raw / replay | Cost PoC, audit |
| (not Vector) Topology writer | `topo_builder` | `A-TOPO` | Both |

**Vector stops at delivery to sinks.** Graph materialization (especially Nezha keys and CSR/KG) is **post-Vector**.

---

## 6. Profiles: Lean-only vs dual-sink (cost PoC)

### 6.0 Input mode preference: saved replay first, live later

| Mode | Role in Ingestion PoC | Prefer when |
|------|----------------------|-------------|
| **Saved / exported replay** (JSONL, corpus-derived, recorded streams) | **Primary** for L0 vs F1 cost compare | Need identical bytes, repeatable EPS, fair Lean-only vs dual-sink attribution |
| **Live** (syslog scrape, OT, lab agents) | **Secondary** smoke / ops realism | Validating collectors, CI-bind, backpressure — not for headline cost tables |
| **Both** | Phased | D1–D2 = replay; D3+ optional live parallel track |

**Recommendation:** use **saved exported / synthetic replay as the PoC contract** (same input → two sink profiles). Add live later as a supplement, not as the fairness baseline — live traffic makes L0 vs F1 cost deltas confounded by input variance.

### 6.1 Sink profiles
|---------|----------------------|-------------------------------|
| **L0** Lean-only | lean_incident + anom_store + A-TOPO | Baseline ★★ |
| **F1** Dual-sink | L0 + speed_tier_feed (+ higher event/trace volume) | ★★★★–★★★★★ |
| **F2** Federated-heavy | F1 + unsampled traces/logs | Max (microservice track) |

Same source replay; only sink/filter config changes → fair **ingestion** cost comparison (RCA accuracy already measured separately).

Metrics to collect on Vector + builders: events/s, CPU, RSS, sink lag, GB/day, drop/retry, CI-bind miss rate.

---

## 7. Mapping to current repo artifacts

| Current PoC stand-in | Vector-era replacement |
|----------------------|------------------------|
| Frozen `datasets/observeops/UC-*` | Replay JSONL → Vector → writers (still can freeze outputs for RCA bakeoff) |
| `observeops_federated` adapter inventing stores | Adapter reads **stores fed by Vector builders** |
| Python `IngestNormalizer` stub | Vector transforms + thin builder sidecars |
| Deferred “NATS → Rust normalizer” | Vector aggregator (NATS/Kafka source optional later) |

RCA bakeoff can stay on frozen bundles until ingest PoC proves parity; then optionally point Lean/Federated at live slices.

---

## 8. Non-goals

- Implementing Panorama / Murphy / Nezha / Lean inside Vector.  
- Using Vector as the structural graph database.  
- Claiming 1B EPS from a laptop Vector run.  
- Merging ObserveOps UC scoreboards with ingest cost metrics.

---

## 9. Implementation phases (documentation roadmap)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **D0** | This design + skeleton config | **Done (this doc)** |
| **D1** | JSONL replay of one UC through Vector → lean bundle writer | Planned — see [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) M1 |
| **D2** | Cost harness: L0 vs F1 profiles, `cost_report.md` | Planned — M2 |
| **D3** | Topology crawler stub + CI bind table | Planned — M1/M2 |
| **D4** | Federated speed-tier builder from Vector Redis/Kafka sink | Planned — M3 |
| **D5** | Product hardening (HA aggregator, auth, DLQ) | Later |

Skeleton config: [`../ingestion-poc/vector/`](../ingestion-poc/vector/).

---

## 10. Decision summary

| Question | Answer |
|----------|--------|
| Use Vector for ingestion PoC? | **Yes** — shared collect/normalize/route |
| Use Vector for product ingest? | **Yes** — default fabric; Lean-cheap sinks; Federated optional sinks |
| Suitable for Lean consumer? | **High** — matches light artifact set |
| Suitable for Federated consumer? | **High as feeder**; structural KG + Nezha key builders remain post-Vector |
| Replaces RCA? | **No** |

---

## 11. References

- Vector: https://github.com/vectordotdev/vector · https://vector.dev/docs/  
- Repo storage vision: [`../federated-pipeline/docs/STORAGE_TIERS.md`](../federated-pipeline/docs/STORAGE_TIERS.md)  
- Lean bundle layout: [`../datasets/observeops/README.md`](../datasets/observeops/README.md)  
- Cost PoC plan: [`../RCA-learning-cheatsheet.md`](../RCA-learning-cheatsheet.md) §3  
- Federated Phase C deferral: [`../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md`](../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md)
