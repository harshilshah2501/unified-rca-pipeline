# Pipeline parity — Lean vs Federated (fair compare)

**Status:** PoC contract (shared detect + divergent RCA)  
**Related:** [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) · [`ingestion-poc/detect/`](../ingestion-poc/detect/)

---

## One-sentence rule

**Same front half (collect + detect) for both engines. Different back half (who finds the root).**

```
Collect → Detect (shared) → Lean RCA
                         → Federated RCA (Murphy + Nezha)
```

On the **fair scoreboard**, Federated does **not** get credit for Panorama detection. Hop-1 consumes the shared detect output (`shared_detect`).

---

## What each side gets

| Step | Shared? | Output |
|------|---------|--------|
| Collect / topology | Yes | Same UC metrics + `topology.json` |
| Detect | Yes | `anomalies` + `symptom_seed` from [`threshold_detect`](../ingestion-poc/detect/threshold_detect.py) |
| Find root | No | Lean walk / rules vs Federated Murphy (+ Nezha) |

Head-to-head Lean vs Federated is decided by the RCA step. Detect is timed and shown, but **identical on both sides**, so it cancels in the delta.

---

## Scoreboard fields (`run_meta.json`)

| Field | Meaning |
|-------|---------|
| `pipeline_profile` | `parity-shared-detect` (fair baseline) |
| `detect_source` | `shared_threshold` |
| `detect_latency_ms` | Shared detector wall time (= **`C_detect`**) |
| `C_detect_ms` | Explicit cost-model alias of `detect_latency_ms` |
| `latency_ms` | RCA-only wall time (localize) |
| `system_latency_ms` | `detect_latency_ms + latency_ms` |
| `by_anomaly_class` | Counts by class (`error_rate` / `performance` / `resource` / …) — D3 |
| `change_near_onset` | True if a change feed hit the onset window — D2 |
| `change_count_in_window` | Number of changes in that window (0 if no feed) |

Optional per-UC change feed: `datasets/observeops/UC-N/changes.jsonl` (see UC-1 sample).

---

## Later — real ingestion RCA (not this pass)

When we move off synthetic UC bundles:

1. Replace pre-baked / corpus-derived streams with **actual ingested data** (Vector collect).
2. Use **real Panorama** (or product-equivalent multi-observer detect) where the Federated product path needs it — and measure that cost honestly.
3. Stop treating frozen `anomalies.json` / `symptom_seed.json` as a live front door.

This pass only makes the compare **fair**. The next pass makes the front door **real**.

---

## What this pass does *not* do

- Put Panorama inside Lean
- Live SNMP/APM production ingest
- Treat Federated’s old ~0.02 ms synthetic “panorama” hop as product detection
