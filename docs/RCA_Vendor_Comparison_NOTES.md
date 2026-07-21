# RCA Vendor Comparison — Claim Notes (companion to PDF)

**PDF survey:** [`RCA_Vendor_Comparison.pdf`](./RCA_Vendor_Comparison.pdf)  
**White-space thesis (edited):** [`two-step-rca-white-space.md`](./two-step-rca-white-space.md)  
**Status:** Soft corrections only — do not treat the PDF as obsolete; use this note when wording decks or PRDs.

---

## Keep from the PDF (strong)

- Three philosophies: Dynatrace deterministic topology, Datadog statistical correlation, BigPanda alert/change correlation.
- Dynatrace ≈ Lean trade-off (deterministic walk), **not** Murphy (Gibbs).
- Accuracy is industry-weak (self-reported); Causal Validity is where vendors diverge most.
- Ranked design suggestions: change-signal, network depth, error-rate, don’t over-invest in cyclic deps, Step-2 path diff as stretch.

## Soften / clarify when citing

| PDF statement | Prefer this wording |
|---------------|---------------------|
| “None of them automate Step 2” | None ship **Nezha-style expected-vs-actual path diff fused into the RCA verdict**; vendors still assist manual “why” (hotspots, pivots, AI) |
| Code-level row = Partial for Dynatrace/Datadog | Partial = **data exists / UI helps**; Not Covered for **automated expected-vs-actual in the verdict** |
| “Our design Covered” on fault types | Mark **PoC-proven** vs **PRD-aspirational** separately against UC bakeoff evidence |
| Section 2.9 / CARE baseline reuse for Nezha | Path baselines are **new Nezha-class cost**; CARE PoC today ≠ continuous healthy-path store |

## Alignment with five-stage workflow

See [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md):

`Ingest → Detect → Localize → Identify → Verify`
