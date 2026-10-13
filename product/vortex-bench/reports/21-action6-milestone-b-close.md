# Report 21 — Action 6 / Milestone B close

**Date:** 2026-10-13  
**Status:** **CLOSED** for the stated envelopes — envelope-conditional decision recorded.  
**Does not reopen Milestone A.** Serve baseline remains conventional **`csr_csc`**; recovery-speed reference remains **`hash`**.

---

## 1. Question answered

> Can segmented CSR+CSC preserve conventional CSR+CSC serve advantages while reducing mutation-to-visibility cost?

**Answer under the approved synthetic mutation envelope:**  
**Yes, conditionally** — retain segmented CSR+CSC as a **Milestone B candidate for localized mutations** (`mut_localized`). Do **not** adopt it as a universal replacement for conventional `csr_csc`. Do **not** introduce per-segment edge journals in this closure.

---

## 2. Envelopes in force

| Envelope | Document | Role |
| -------- | -------- | ---- |
| Query / estate (Milestone A) | [`../design-v3/action2-synthetic-operating-envelope.md`](../design-v3/action2-synthetic-operating-envelope.md) | Frozen serve path |
| Mutation (Milestone B) | [`../design-v3/action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md) | **Waiver-approved** synthetic; not measured Motadata churn |

---

## 3. Evidence map

| Priority | Report | Result |
| -------- | ------ | ------ |
| Locality / \(T_{\mathrm{mutation\text{-}visible}}\) | [18](./18-action6-mutation-lifecycle.md) | Localized win (~2× at 1M); all-touch lose |
| Atomic publish + dual-hold RSS | [19](./19-action6-atomic-publish.md) | PASSED lab model; ~1.7–1.8× dual-hold |
| Durability / replay | [20](./20-action6-durability-replay.md) | PASSED lab durability model (not Motadata protocol) |
| Mutation realism | envelope doc | Synthetic waiver (production histograms unavailable) |
| 5M thin ladder | [21a](./21-action6-5m-thin-ladder.md) | Localized win holds (~0.38–0.41 seg/conv); medium ≈ tie/loss |

### 5M headline (hubby)

| Profile | Segs | Conv T_mut p50 | Seg T_mut p50 | Ratio |
| ------- | ---: | -------------: | ------------: | ----: |
| `mut_localized` (10/2) | 64 | 4480 ms | **1839 ms** | **0.41** |
| `mut_localized` (10/2) | 256 | 4390 ms | **1679 ms** | **0.38** |
| `mut_medium` (1000/200) | 64 | 6813 ms | 6931 ms | 1.02 |

---

## 4. Acceptance criteria check

From the mutation envelope:

| Criterion | Met? |
| --------- | ---- |
| Under `mut_localized`, segmented T_mut p50 strictly better than conventional at 1M and 5M | **Yes** |
| Priorities 1–3 lab properties documented | **Yes** (Reports 19–20) |
| Conventional `csr_csc` remains serve baseline | **Yes** (Milestone A frozen) |
| Decision language is envelope-conditional | **Yes** (this report) |

---

## 5. Final Action 6 decision

```text
Adopt conditionally for validated localized-mutation workloads
        │
        ├── Serving path: keep conventional csr_csc (Milestone A)
        ├── Mutation path candidate: segmented csr_csc when batches are localized
        ├── If batches are medium/all-touch: prefer conventional full rebuild
        └── Per-segment journals: NOT adopted — separate hypothesis remains open
```

**Retain as experimental / conditional candidate** with explicit routing guidance:

1. **Serve / concurrent Scope walks:** conventional `csr_csc` (frozen).  
2. **Cold→ready speed reference:** `hash` (frozen).  
3. **Localized mutation publish windows (`mut_localized`):** segmented CSR+CSC is justified by lab evidence at 1M and 5M.  
4. **Large / all-segment-touch publishes:** conventional full rebuild is simpler and as-fast or faster.  
5. **Production Motadata:** still requires measured mutation locality before promoting segmented beyond “conditional candidate.”

This is **not** a Motadata-wide architecture lock and **not** a claim that Vortex cold layout changes.

---

## 6. Explicit non-goals (closed without pursuing)

- Reopening `hash` / `hash_bi` / `csr_csc` selection.  
- Folding per-segment edge journals into this decision.  
- Claiming Motadata production durability equals the lab commit model.  
- Claiming universal superiority of segmented CSR+CSC.

---

## 7. Architecture position after closure

| Role | Choice | Status |
| ---- | ------ | ------ |
| Serve baseline | conventional `csr_csc` | **Frozen** (Milestone A) |
| Recovery-speed reference | `hash` | **Frozen** |
| Segmented CSR+CSC | Conditional Milestone B candidate for **localized** mutations | **Closed as conditional adopt** under synthetic mutation envelope |
| Per-segment journals | Separate optimization hypothesis | **Still open / not required** |

---

## 8. Links

- Program one-stop (cold readers): [Report 22](./22-program-one-stop.md)  
- Program: [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md)  
- Mutation envelope: [`../design-v3/action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md)  
- Milestone A: [Report 17](./17-milestone-a-close.md)  
- ADR: [`Map_Vortex_Graph_Architecture_Decision_Record.md`](./Map_Vortex_Graph_Architecture_Decision_Record.md)
