# Action 6 priority 4 — Synthetic mutation operating envelope

**Status:** **APPROVED for Milestone B / Action 6 closure** (2026-10-13) via waiver — Motadata production mutation histograms were not available.  
**Limitation:** Shares and batch sizes are **policy-derived lab assumptions** grounded in Report 18 locality findings, not measured Motadata churn.

**Purpose:** State an explicit mutation envelope so Action 6 decisions are not unlabeled synthetic assumptions.

---

## 1. Why a synthetic envelope

Action 2 approved a **query/estate** envelope (`motadata_like_hubby` + `scope_policy_mixed`) but left mutation rates blank (intake §4). Report 18 showed segmentation is **locality-dependent**:

- Small batches that touch a minority of segments → segmented \(T_{\mathrm{mutation\text{-}visible}}\) improves (~2×).  
- Large batches that touch every segment → segmented loses to conventional full rebuild.

Without production batch-size/locality stats, Milestone B must either stop or adopt an **approved synthetic mutation envelope** (same pattern as Action 2 waiver).

---

## 2. Approved mutation profiles (lab)

| Profile | Inserts / deletes per batch | Intent | Role in decision |
| ------- | ---------------------------: | ------ | ---------------- |
| `mut_localized` | **10 / 2** | Fine-grained topology edits (few endpoints) | **Primary** — where segmented is hypothesized to win |
| `mut_medium` | **1000 / 200** | Larger publish window | **Sensitivity** — often all-touch at low segment counts |
| `mut_all_touch` | sized to force ≥90% segments rebuilt | Stress / anti-pattern | **Control only** — not a Motadata claim |

**Estate / query context (unchanged from Action 2):** `motadata_like_hubby` + `scope_policy_mixed` for read-path checks.  
**Segment counts under test:** 64 (primary candidate), 256 (sensitivity).  
**Scales:** 1M (Reports 18–20), **5M thin ladder** (priority 5).

---

## 3. Acceptance criteria for Action 6 closure

Under `mut_localized` at 1M and 5M (hubby, 64 segments unless noted):

1. Segmented \(T_{\mathrm{mutation\text{-}visible}}\) p50 **strictly better** than conventional full rebuild.  
2. Priorities 1–3 lab properties remain true (atomic publish, dual-hold RSS reported, durability model).  
3. Conventional `csr_csc` remains the **serve baseline** (Milestone A frozen).  
4. Decision language must say: **conditional on this mutation envelope** — not Motadata-wide lock.

If `mut_localized` fails at 5M, or only `mut_medium`/`mut_all_touch` are believed production-like later, **retain segmented as experimental** and keep conventional `csr_csc` as serving baseline.

---

## 4. Waiver / sign-off

- [x] Production mutation batch sizes and locality **cannot** be provided for this sprint.  
- [x] We **approve** this synthetic mutation envelope for Action 6 / Milestone B closure only.  
- [x] We understand segmented CSR+CSC remains **envelope-conditional**, not a Motadata-wide architecture lock.  
- [x] Per-segment edge journals stay a **separate** hypothesis (not required for this closure).

| Role | Name | Date | Decision |
| ---- | ---- | ---- | -------- |
| Motadata product | Harshil Shah | 2026-10-13 | **approved synthetic mutation envelope** (waiver) |
| Pillar B eng | Harshil Shah | 2026-10-13 | **approved synthetic mutation envelope** |
| ObserveOps / RCA | Harshil Shah | 2026-10-13 | **approved synthetic mutation envelope** |

---

## 5. Revision

| Date | Change |
| ---- | ------ |
| 2026-10-13 | Initial envelope from Report 18 locality split + Action 2 waiver pattern |
