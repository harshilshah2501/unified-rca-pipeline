# Fault-type coverage by bucket — vs Dynatrace & Datadog

**Status:** Evaluation note (2026-07-21)  
**Related:** [`RCA_Vendor_Comparison_NOTES.md`](./RCA_Vendor_Comparison_NOTES.md) · [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf) · [`two-step-rca-white-space.md`](./two-step-rca-white-space.md) · [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md)

This note rolls vendor survey fault types into **four buckets** and places **our design** next to **Dynatrace** and **Datadog** (BigPanda called out only where it uniquely wins a bucket).

**Scoring discipline:** vendor “Covered” = product surface. Ours = **PoC-proven** (ObserveOps bakeoff) vs **design/plan**. Do not mark aspirational Federated/Nezha rows as Covered in decks.

---

## 1. The four buckets

| Bucket | Fault types inside | What unifies them | Stage map |
|--------|--------------------|-------------------|-----------|
| **1. Symptom signals** | Availability/Outage, Error Rate, Performance/Slowdown | What you notice first — not yet where/why | **Detect** |
| **2. Infrastructure / platform** | Resource Contention, Network Faults, Storage/Noisy-Neighbor | Shared physical/virtual resource layer below a single app | Mostly **Localize** |
| **3. Application / topology** | Dependency/Downstream, Cyclic/Tangled deps, Code-level execution path | How services/code are structured or connected | **Localize → Identify** |
| **4. External trigger** | Change-induced, Security incidents | Outside action (deploy/config or adversary), not organic behavior | Orthogonal (origin feed) |

Detection difficulty tracks the same ladder: Bucket 1 = one metric + threshold → Bucket 2 = right telemetry layer / cross-entity → Bucket 3 = graph or pattern-match → Bucket 4 = **separate** data source outside ops telemetry.

---

## 2. Rollup vs Dynatrace / Datadog / us

| Bucket | Dynatrace | Datadog | BigPanda (context) | **Our design (honest)** |
|--------|-----------|---------|--------------------|-------------------------|
| **1 Symptom** (3) | 3 Covered | 3 Covered | 3 Partial | **3 Covered at detect layer** (D3 `anomaly_class=error_rate`); product still needs live error metrics |
| **2 Infrastructure** (3) | 2 Covered, 1 Partial | 2 Covered, 1 Partial | 2 Partial, 1 Not | **2 Covered, 1 Partial** (UC-1/2/3 PoC-strong) |
| **3 Application** (3) | 1 Covered, 1 Partial, 1 Not | 1 Covered, 1 Partial, 1 Not | 1 Partial, 2 Not | **1 Covered, 2 Not** (deps yes; cyclic + path-diff Not) |
| **4 External** (2) | 1 Not, 1 Covered | 1 Not, 1 Partial | **1 Covered, 1 Not** (wins change) | **Change: Partial** (D2 feature + sample feed; needs real CI/CD). Security: **Not** |

### What the flat table hid

- **Buckets 1–2** are where the market (and we) cluster — the “solved” Localize/Detect band for classic infra.
- **Bucket 3** is uniformly weakest — Nezha-style fused path-diff and cyclic-deps live here; vendors assist Step 2 in UI, we do not yet automate it in the verdict.
- **Bucket 4** was our empty bucket; **D2** now emits `change_near_onset` when a change feed is present. Closing the product gap still needs a real CI/CD/audit trail (BigPanda’s specialty). Security remains Not.

---

## 3. Per-bucket detail (us vs DT / DD)

### Bucket 1 — Symptom (Detect)

| Fault | Signal | Dynatrace / Datadog | Us |
|-------|--------|---------------------|-----|
| Availability / Outage | Heartbeat / health fail | Covered | Covered (events / hard signals; UC-class) |
| Error rate | Failed/success ratio | Covered | **Covered (detect)** — D3 `anomaly_class=error_rate` (e.g. UC-4/5 `error_rate_5xx`) |
| Performance / Slowdown | Latency p95/p99 vs SLO | Covered | Covered (threshold `metric_sample` / UC latency) |

### Bucket 2 — Infrastructure (Localize)

| Fault | Dynatrace / Datadog | Us (PoC) |
|-------|---------------------|----------|
| Resource contention | Covered (host/hypervisor metrics) | **Covered** — UC-1 `cpu_contention` |
| Network faults | Covered / Partial (SNMP depth varies) | **Covered** — UC-2 `link_failure`; vendor note still asks for deeper net |
| Storage / noisy-neighbor | Partial (needs cross-entity) | **Covered on UC-3** as Localize+signature; still hard as pure single-service detect |

Philosophy: Lean ≈ **Dynatrace-shaped** (deterministic typed topology walk), not Datadog-shaped (learned deviation ranking). Coverage parity ≠ same mechanism.

### Bucket 3 — Application / topology (Localize → Identify)

| Fault | Dynatrace / Datadog | Us |
|-------|---------------------|-----|
| Dependency / downstream | Covered (service map / correlation) | **Covered** on typed CI graph (classic infra deps) |
| Cyclic / tangled deps | Not | **Not** (explicitly later; measure pain first) |
| Code-level execution path | **Partial** = deep traces/UI help; **Not** = Nezha fused expected-vs-actual in verdict | **Not** — stretch Step-2 after Localize ([`two-step-rca-white-space.md`](./two-step-rca-white-space.md)) |

We are **tied in the weak band** with DT/DD on Bucket 3 — not uniquely behind. Differentiation only if scoped path-diff ships after data gates.

### Bucket 4 — External (outside ops telemetry)

| Fault | Dynatrace | Datadog | Us |
|-------|-----------|---------|-----|
| Change-induced | Often Not / weak | Often Partial | **Partial** — D2 `change_context.json` when change feed provided; needs real CI/CD ingest |
| Security | Stronger portfolio coverage | Partial | **Not** — out of ObserveOps MVP unless SIEM feed added |

---

## 4. Spectrum one-liner

```
Difficulty →
B1 ████████░░  market + us
B2 ███████░░░  market + us
B3 ███░░░░░░░  everyone weak (graph / pattern)
B4 █░░░░░░░░░  us empty; DT/DD partial; BigPanda owns change
```

**Stakeholder line:** We match Dynatrace/Datadog where the market is crowded (symptom + infra Localize). We share their Application/Identify weakness. We uniquely fail External triggers — fix **change-signal (D2)** before selling Step-2 white space as the main differentiator; add **error-rate (D3)** for Bucket-1 parity.

---

## 5. Priority order (coverage, not ingest)

| Priority | Action | Bucket | Notes |
|----------|--------|--------|-------|
| 1 | **D2** Change near onset | 4 | **Done (detect feature)** — product still needs real change feed |
| 2 | **D3** Explicit error-rate class | 1 | **Done** — `anomaly_class=error_rate` |
| 3 | Motadata GT / CI-bind + bakeoff `C_detect` meta | 1–2 | Next engineering |
| 4 | Scoped execution-path diff | 3 | Stretch; after justification gates |
| 5 | Security feed | 4 | Optional; not Lean MVP |

---

*Synced: 2026-07-21 (F1 fabric note + D2/D3)*
