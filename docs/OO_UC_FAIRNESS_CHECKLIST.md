# OpenObserve UC fairness checklist

**Purpose:** Make Lean × Federated × OO citations **credible** on ObserveOps UC-1..UC-5.  
**Related:** [`../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md)

OO is **not** automatic RCA: alerts are compulsory; past-window incidents may need an explicit enable. That is allowed — but alerts must **not coach the answer**.

---

## Before claiming OO Localize accuracy

| # | Check | Pass criteria |
|---|--------|---------------|
| 1 | **No GT in alert text** | Alert title/description must **not** contain `root_ci_gt`, `signature_gt`, `ground_truth`, or the exact GT root CI / signature strings as “the answer” |
| 2 | **Symptom-only alert** | Alert fires on the **symptom** metric (e.g. `orders-api` latency/errors), not on the root CI alone |
| 3 | **Same synthetic story** | Same UC windows / thresholds as Lean/Fed packs (or document deltas) |
| 4 | **Past-incident path documented** | Note if past-data trigger was required (age, flag flipped) |
| 5 | **Extractable verdict** | Write down OO’s claimed root CI (+ fault class) in one line **before** reading Lean/Fed reports |
| 6 | **UC-5 anti-FP** | OO must not blame healthy infra when GT is `orders-api` |
| 7 | **Re-pull after scrub** | Especially **UC-1** (current export embeds GT in alert) — regenerate OO write-up after scrubbing |

---

## UC-1 known contamination (current export)

`reports/OO/uc1_esxi_cpu_contention` quotes alert text:

`Root Cause (root_ci_gt=esxi-host-01, signature_gt=cpu_contention): …`

→ Treat current UC-1 OO pass as **narrative alignment**, not independent Localize proof, until checklist #1/#7 are done.

---

## After scrub — how to score fairly

| Axis | Lean / Fed | OO |
|------|------------|-----|
| Root | `verdict.root_ci == GT` | Human map of OO “Potential Cause” → CI id |
| Signature | enum match | Optional prose class match |
| Repro / latency | Machine | Out of scope unless OO exposes stable API |

Keep **report richness** as a separate axis (OO often wins prose); do not merge into Motadata or ADR scoreboards.

---

## Operator one-liner

> Alerts raise the incident; **RCA must discover the root** — never paste GT into the alert body.

*Added: 2026-07-24*
