# OpenObserve UC fairness checklist

**Purpose:** Make Lean × Federated × OO citations **credible** on ObserveOps UC-1..UC-5.  
**Slice A playbook:** [`SLICE_A_OO_UC_FAIRNESS.md`](./SLICE_A_OO_UC_FAIRNESS.md)  
**Fair results (2026-07-27):** [`../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) · [`../benchmarking/results/comparison/reports/OO/fair/`](../benchmarking/results/comparison/reports/OO/fair/)

OO is **not** automatic RCA: alerts are compulsory; shift-to-now may be required for Analysis windows. That is allowed — but alerts must **not coach the answer**.

---

## Fair Slice A outcome (done)

| Engine | Root vs pack GT |
|--------|-----------------|
| Lean | **5/5** |
| Federated | **5/5** |
| OpenObserve (fair) | **1/5** (UC-5 only; UC-5 anti-FP pass) |

Contaminated 2026-07-24 OO “5/5 narrative” is **withdrawn** for Localize claims.

---

## Before claiming OO Localize accuracy

| # | Check | Pass criteria | Slice A 2026-07-27 |
|---|--------|---------------|--------------------|
| 1 | **No GT in alert text** | No `root_ci_gt`, `signature_gt`, or GT root as “the answer” | ✓ fair alerts |
| 2 | **Symptom-only alert** | Fires on symptom metric | ✓ |
| 3 | **Same synthetic story** | Same UC packs / thresholds (or document deltas) | ✓ parity + shift noted |
| 4 | **Past/shift path documented** | Note past-trigger or `shift-to-now` | ✓ shift-to-now |
| 5 | **Extractable verdict** | Blind one-line OO root before Lean/Fed | ✓ |
| 6 | **UC-5 anti-FP** | Must not blame healthy infra | ✓ pass |
| 7 | **Re-pull after scrub** | New write-ups after fair alerts | ✓ `OO/fair/` |
| 8 | **Fair push** | `--fair` (no GT tags on records) | ✓ |

---

## After scrub — how to score fairly

| Axis | Lean / Fed | OO |
|------|------------|-----|
| Root | `verdict.root_ci == GT` | Human map of OO “Potential Cause” → CI id |
| Signature | enum match | Optional prose class match |
| Repro / latency | Machine | Out of scope unless OO exposes stable API |

Keep **report richness** as a separate axis; do not merge into Motadata or ADR scoreboards.

---

## Operator one-liner

> Alerts raise the incident; **RCA must discover the root** — never paste GT into the alert body.

*Updated: 2026-07-27 — fair Slice A complete (OO 1/5)*
