# RCA Workflow & Next Action Items

**Status:** Active plan after vendor survey + white-space review (2026-07-21)  
**Related:** [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) · [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) · [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) · [`RCA_Vendor_Comparison_NOTES.md`](./RCA_Vendor_Comparison_NOTES.md)

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
| Detect (real front door) | **Partial** | Shared threshold on corpus; Motadata/live still open |
| Ingest (product-shaped) | **Partial** | UC JSONL + Motadata adapter smoke (`motadata-ingest/`); Vector F1 / Lean L0 next |
| Identify Step-2 path diff | **Open / stretch** | Needs traces + baseline + data gates |

---

## 3. Next action items (ordered)

### Now — Ingest (critical path)

| # | Action | Exit criteria | Owner focus |
|---|--------|---------------|-------------|
| N1 | Receive Motadata frozen JSON (logs, metrics, traces, spans + ID dictionaries) | **Done locally** — `datasets/ingest_samples/jsonl_resolved/` (gitignored; names already resolved) | Data |
| N2 | Build `motadata_to_ingest_v1.py` | **Done** — [`ingestion-poc/adapters/motadata_to_ingest_v1.py`](../ingestion-poc/adapters/motadata_to_ingest_v1.py); smoke → `motadata-ingest/stream.jsonl` | Eng |
| N3 | Vector F1 skeleton: read `stream.jsonl` → detect + structural sink | UC-1 / Motadata sample end-to-end smoke | Eng |
| N4 | Federated-first store writers (metric slice; Dragonfly stub OK without traces) | Artifacts written; timing in meta | Eng |
| N5 | Lean bundle writer on **same** stream (L0) | Lean diagnose PASS on converted Motadata or UC replay | Eng |

### Next — Detect (cheap wins from vendor survey)

| # | Action | Exit criteria |
|---|--------|---------------|
| D1 | Keep shared threshold detect as mandatory front door | Timed `C_detect` on scoreboard |
| D2 | **Change-induced signal** (deploy/config near onset) | “Change in window?” feature on candidates |
| D3 | Explicit **error-rate** anomaly class (distinct from latency) | Detect emits error-rate crossings |
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
2. **Same ingest stream** for both engines ([PIPELINE_PARITY.md](./PIPELINE_PARITY.md)).
3. **Federated / Step-2 path diff** only after [`FEDERATED_JUSTIFICATION_REPORT.md`](./FEDERATED_JUSTIFICATION_REPORT.md) gates.
4. Prefer **Detect cheap wins** (change signal, error-rate) before expensive Identify depth.

---

## 5. Immediate three tasks (current)

N1–N2 are done (local Motadata under `jsonl_resolved/` → smoke `ingest.v1` via adapter). Next:

1. **N3** — Vector F1 skeleton: read `datasets/ingest_samples/motadata-ingest/stream.jsonl` (or ObserveOps replay) → detect + structural sink.
2. **N4** — Federated-first store writers (metric slice; Dragonfly stub OK without full traces).
3. **N5** — Lean `lean_bundle_writer` on the **same** stream; diagnose PASS on UC replay and/or Motadata subset.

**Still open after N3–N5:** Motadata CI-bind / topology / GT (monitors ↔ services); Detect cheap wins (D2–D3). Large Motadata dumps stay **local only** (gitignored; do not push).

Hardware: **pro6000-server** (16c / 125GiB) for N3–N5 load tests.

*Doc status synced: 2026-07-21.*
