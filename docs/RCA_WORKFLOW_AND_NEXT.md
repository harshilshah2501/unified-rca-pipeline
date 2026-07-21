# RCA Workflow & Next Action Items

**Status:** Active plan after vendor survey + white-space review (2026-07-21)  
**Related:** [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) · [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) · [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) §5.4 · [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) · [`two-step-rca-white-space.md`](./two-step-rca-white-space.md)

---

## 1. Canonical workflow (product + PoC)

```
Ingest → Detect → Localize → Identify → Verify
```

| Stage | Job (one sentence) | Lean path (current) | Federated path (current / optional) |
|-------|--------------------|---------------------|-------------------------------------|
| **Ingest** | Collect & normalize telemetry into RCA-ready artifacts | Bundle / future Vector L0 | Same stream → F1 speed + structural sinks |
| **Detect** | Decide *something is wrong* and raise a seed | Threshold / events / alerts → `A-ANOM` + `A-SEED` | Shared detect **or** Panorama gray-failure |
| **Localize** | Decide *which CI / service* | Best-first walk + rules | Murphy (+ fusion) |
| **Identify** | Name *what kind of failure* (and optionally *which path*) | Signature / rules | Signature + optional **Nezha / execution-pattern diff** (Step 2) |
| **Verify** | Decide how strongly we claim cause | Evidentiary Tier 1/2/3 + CARE → scoped causal | Murphy posterior / fusion confidence; bakeoff GT |

**Vendor survey mapping:** most commercial tools automate **Detect + Localize** well and leave deep **Identify** (execution-path) partly manual. Our white-space thesis is scoped automated Identify after Localize — see [`two-step-rca-white-space.md`](./two-step-rca-white-space.md).

**Two-step shorthand vs five-stage:**

| Two-step language | Five-stage stages |
|-------------------|-------------------|
| Step 1 “where” | Detect → Localize |
| Step 2 “what happened there” | Identify → (optional deep path) Verify |

---

## 2. What is already closed vs open

| Stage | Closed? | Evidence / gap |
|-------|---------|----------------|
| Localize + Identify (classic UC bakeoff) | **Mostly closed** | Lean + Federated 5/5 on ObserveOps; Lean packaged |
| Verify (tiers / GT) | **PoC closed** | Bakeoff + CARE/Tier-3 scoped |
| Detect (real front door) | **Partial** | Shared threshold + **D2/D3**; Motadata thresholds / live Panorama still open |
| Ingest (product-shaped) | **Partial** | UC + Motadata → `ingest.v1` + F1 + **N4/N5 writers**; Motadata GT/CI-bind + live detect still open |
| Identify Step-2 path diff | **Open / stretch** | Needs traces + baseline + data gates |

---

## 3. Next action items (ordered)

### Now — Ingest (critical path)

| # | Action | Exit criteria | Owner focus |
|---|--------|---------------|-------------|
| N1 | Receive Motadata frozen JSON (logs, metrics, traces, spans + ID dictionaries) | **Done locally** — `datasets/ingest_samples/jsonl_resolved/` (gitignored; names already resolved) | Data |
| N2 | Build `motadata_to_ingest_v1.py` | **Done** — [`ingestion-poc/adapters/motadata_to_ingest_v1.py`](../ingestion-poc/adapters/motadata_to_ingest_v1.py); smoke → `motadata-ingest/stream.jsonl` | Eng |
| N3 | Vector F1 skeleton: read `stream.jsonl` → detect + structural sink | **Done** — [`ingestion-poc/pipeline/f1_run.py`](../ingestion-poc/pipeline/f1_run.py); UC-1 seed/anomaly match frozen; Motadata fan-out OK | Eng |
| N4 | Federated-first store writers (metric slice; Dragonfly stub OK without traces) | **Done** — [`federated_store_writer.py`](../ingestion-poc/builders/federated_store_writer.py); `metric_slice.jsonl` + `speed_tier_stub.jsonl` + timing | Eng |
| N5 | Lean bundle writer on **same** stream (L0) | **Done** — [`lean_bundle_writer.py`](../ingestion-poc/builders/lean_bundle_writer.py); UC-1..5 diagnose root match via `n45_chain.py` | Eng |

### Next — Detect (cheap wins from vendor survey)

| # | Action | Exit criteria |
|---|--------|---------------|
| D1 | Keep shared threshold detect as mandatory front door | Timed `C_detect` on scoreboard (in progress via F1 `detect_meta`) |
| D2 | **Change-induced signal** (deploy/config near onset) | **Done** — [`change_near_onset.py`](../ingestion-poc/detect/change_near_onset.py) → `change_context.json`; samples under `detect/samples/` |
| D3 | Explicit **error-rate** anomaly class (distinct from latency) | **Done** — `anomaly_class` on crossings (`error_rate` / `performance` / `resource` / …) |
| D4 | Optional Panorama only when gray-failure corpus exists | `detect_source=panorama` measured |

### Then — Localize / Identify / Verify (only if ingest regresses or micro track)

| # | Action | Exit criteria |
|---|--------|---------------|
| L1 | Re-score Lean vs Federated on Motadata-normalized incidents | COMPARISON + GT convention |
| I1 | Signature coverage for Motadata fault vocabulary | Signature match contract |
| I2 | **Stretch:** scoped execution-pattern diff after Localize | White-space doc mechanism; justification gates |
| V1 | Keep evidentiary tiers; version baselines for repro | Replay bit-stability |

### Explicitly later (do not block ingest)

- Cyclic-dependency solver (industry-wide open; measure pain first).
- Full Nezha fleet path materialization before Localize.
- 1B EPS / hyperscaler sizing.

---

## 4. Decision rules (carry forward)

1. **Lean-primary** for classic infra until data says otherwise ([ADR-001](./ADR-001-lean-primary-engine.md)).
2. **Same ingest stream / F1 sinks for both engines** ([PIPELINE_PARITY.md](./PIPELINE_PARITY.md); Vector **or** Python fan-out → N4 + N5 — [INGESTION_PIPELINE_VECTOR.md](./INGESTION_PIPELINE_VECTOR.md) §5.4).
3. **Federated / Step-2 path diff** only after [`FEDERATED_JUSTIFICATION_REPORT.md`](./FEDERATED_JUSTIFICATION_REPORT.md) gates.
4. Prefer **Detect cheap wins** (change signal, error-rate) before expensive Identify depth.

---

## 5. Immediate three tasks (current)

N1–N5 ingest smoke + **D2/D3 detect cheap wins** are done on **WSL** (Python F1 fan-out by default; Vector optional). Next:

1. **Motadata depth** — thresholds / CI-bind / topology / GT so product dumps can Localize (not only fan-out).
2. **D1 scoreboard** — surface timed `C_detect` + `by_anomaly_class` / `change_near_onset` on bakeoff `run_meta`.
3. **Lab** — pro6000 standing Vector+Dragonfly EPS; optional Federated bakeoff reading N4 `metric_slice`.

```bash
# Shared fabric reminder: one F1 → N4 + N5 (see INGESTION_PIPELINE_VECTOR §5.4)
python3 ingestion-poc/builders/n45_chain.py --suite UC-1 \
  --changes ingestion-poc/detect/samples/changes_uc1_near.jsonl
```

*Doc status synced: 2026-07-21 (F1 fabric note + D2/D3).*
