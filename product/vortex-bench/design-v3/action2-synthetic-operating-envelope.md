# Action 2 — Proposed synthetic operating envelope (Milestone A)

**Status:** **APPROVED** (2026-10-13) — Motadata / Pillar B / ObserveOps signed waiver path B in [`action2-motadata-workload-intake.md`](./action2-motadata-workload-intake.md) §5–§6.  
**Use:** Actions 3–5 score **under this envelope only**. Reports must say envelope-conditional (not Motadata-wide production lock).

**Grounding (cold-reader):**

| Source | What it contributes |
| ------ | ------------------- |
| [`../../contracts/MAP_SCOPE_WALK_POLICY.md`](../../contracts/MAP_SCOPE_WALK_POLICY.md) | Default walk = **outbound**, **hops = 2**; saturation / monitoring / optional slowdown ingress need **inbound** or **both** |
| Design v3 Stages 3–4 synthetics | Hubby / mixed / power-law power shapes; density lock mean out-degree ≈ **5** |
| Report 10 / eng brief ([`../reports/11-map-vortex-engineering-brief.md`](../reports/11-map-vortex-engineering-brief.md)) | Layout freeze candidates; hubby as Motadata-shaped **hypothesis** |

---

## 1. Estate profile (structure)

**Name:** `motadata_like_hubby` (approved synthetic label).

| Parameter | Value | Rationale |
| --------- | ----- | --------- |
| Shape | **hubby** (1% of sources carry ~50% of edges) | Matches Motadata-like concentration used in Stage 3–4; not a claim of measured Motadata shares |
| Mean out-degree | **5** | Density lock from Stage 4.0 |
| Scales for Milestone A | **1M** and **5M** nodes (edges ≈ 5× nodes) | Thin 5M ladder already exercised in Stage 4.2 |
| Duplicate edges | **off** for decision runs (unless Motadata reports material duplicates) | Keeps Action 1 / Action 3 comparable |
| Secondary stress shape | power-law α≈2.1 (optional; not Motadata claim) | Worst-case concentration only |

**Not claimed:** exact Motadata p99 degree, component count, or CI type mix. Those stay in the intake form.

---

## 2. Query / Scope profile (workload)

**Name:** `scope_policy_mixed` (approved synthetic label).

Product brief says Scope is **not** reverse-zero and **not** reverse-primary:

| Mode | Share of scored walk calls (proposed) | Aligns with |
| ---- | -------------------------------------- | ----------- |
| Forward BFS / scan (`out`, hops=2) | **70%** | Default Scope direction |
| Reverse BFS / scan (`in`, hops=2) | **20%** | Saturation / monitoring / ingress-style walks |
| Bidirectional or both-direction budgets | **10%** | Classes that need blast + dependency in one WorkingSet |

**Lab mapping to existing Vortex query profiles:**

| Envelope mode | Bench query profile to weight |
| ------------- | ----------------------------- |
| Forward-dominant production claim | Use `forward_heavy` as **primary** score row |
| Envelope scoring for Milestone A | Prefer a **weighted** score: `0.7 × forward_heavy + 0.2 × reverse_heavy + 0.1 × balanced` (or implement `scope_policy_mixed` in the runner) |
| Stress only | Pure `reverse_heavy` / `scan_heavy` — report separately; do **not** treat as Motadata primary |

**Hop budget:** 2 (match Scope default). Deeper hops are out of Milestone A decision scope unless Motadata says otherwise.

**Concurrency (provisional):** single-reader latency first; multi-reader after layout pick (Action 5).

---

## 3. Layout freeze under this envelope (reminder)

Frozen for Milestone A comparison (unchanged):

- `hash`
- `hash_bi`
- `csr_csc`

`csr` alone and `hybrid` stay archived / deferred.

**Envelope implication (hypothesis, to be tested in Action 3–4):**

- Forward-heavy share favors layouts that do not pay full reverse index cost on every read.  
- Non-zero reverse/both share (≈30% combined) keeps **`hash_bi` / `csr_csc`** in the race — do **not** drop bidirectional candidates based on “Scope is out-only.”

---

## 4. Winning criteria under this envelope

Same sprint gates, but scores must cite this envelope name:

1. Correctness: Action 1 oracle still green.  
2. Latency: weighted profile (§2) p50/p95 at 1M and 5M.  
3. Memory: RSS / edge bytes within Stage 4.0 ladder expectations.  
4. Winner declaration must say: **“winner under `motadata_like_hubby` + `scope_policy_mixed`”** — not “Motadata production lock.”

---

## 5. Exit criteria for Action 2

Action 2 is **complete** when **either**:

- **A.** Motadata fills intake §2–§3 with measured/estimated stats, **or**  
- **B.** Motadata (or delegated eng owner) checks the waiver in intake §5 and signs §6 approving this envelope.

**Current state:** §5 waiver checked; §6 signed by Harshil Shah (Motadata product, Pillar B eng, ObserveOps / RCA) on 2026-10-13 → Action 2 **PASSED**.

---

## 6. Revision

| Date | Change |
| ---- | ------ |
| 2026-10-13 | Initial proposal from Scope walk policy + Stage 4 synthetics |
| 2026-10-13 | Approved via intake waiver (path B); Action 2 PASSED |
