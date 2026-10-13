# Report 13 — Action 2: Motadata workload intake + proposed synthetic envelope

**Priority:** P0 for the decision-validation sprint (blocks Motadata-claimed winners in Actions 3–5).

**Status:** **PASSED** (2026-10-13) — synthetic envelope approved via intake waiver (path B). Still not a Motadata-wide production lock; winners stay envelope-conditional.

## What Action 2 requires

Exit gate (from [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md)):

> At least one representative estate profile **and** one representative query profile — **or** an explicitly approved synthetic operating envelope if production data is unavailable.

No anonymized Motadata tenant dumps or Scope call histograms were available in-repo. Action 2 therefore ships:

1. An intake form for product/SRE to fill or waive.  
2. A **proposed** synthetic envelope grounded in the Scope walk policy and Stage 4 synthetics.

## Deliverables

| Artifact | Role |
| -------- | ---- |
| [`../design-v3/action2-motadata-workload-intake.md`](../design-v3/action2-motadata-workload-intake.md) | Anonymized estate + Scope mix questionnaire + waiver |
| [`../design-v3/action2-synthetic-operating-envelope.md`](../design-v3/action2-synthetic-operating-envelope.md) | Proposed `motadata_like_hubby` + `scope_policy_mixed` |

## Approved envelope (summary)

| Dimension | Label | Content |
| --------- | ----- | ------- |
| Estate | `motadata_like_hubby` | Hubby shape (1% sources ≈ 50% edges), mean out-degree 5, scales 1M / 5M |
| Query mix | `scope_policy_mixed` | **70%** forward (`out`, hops=2), **20%** reverse (`in`), **10%** both / bidirectional budgets |

**Why reverse is not zero:** [`../../contracts/MAP_SCOPE_WALK_POLICY.md`](../../contracts/MAP_SCOPE_WALK_POLICY.md) defaults to outbound hops=2, but saturation, monitoring, and optional slowdown ingress need inbound or both. That keeps `hash_bi` / `csr_csc` in the Milestone A race.

**Why this is not a Motadata lock:** shares are policy-derived proposals, not measured production percentages. Until intake §6 is signed (filled stats **or** waiver), Action 3 reports must say **envelope-conditional**.

## Lab mapping

| Envelope mode | Existing Stage 4 profile |
| ------------- | ------------------------ |
| Primary score row | `forward_dominant` / `forward_heavy` |
| Weighted Milestone A score | `0.7 × forward + 0.2 × reverse + 0.1 × balanced` (or implement `scope_policy_mixed`) |
| Stress only | Pure `reverse_heavy` — separate row |

See also [`../design-v3/stage4/workload-profiles.md`](../design-v3/stage4/workload-profiles.md).

## Gate call

| Check | Result |
| ----- | ------ |
| Intake template published | **Yes** |
| Synthetic envelope proposed with named estate + query profile | **Yes** |
| Motadata / delegated owner signed §6 | **Yes** — Harshil Shah (product, Pillar B, ObserveOps), 2026-10-13; waiver path B |

**Next:** Action 3 — statistically credible `hash` vs `hash_bi` vs `csr_csc` under `motadata_like_hubby` + `scope_policy_mixed`.

## Links

- Program: [`../design-v3/decision-validation-sprint.md`](../design-v3/decision-validation-sprint.md)  
- Gates: [`../design-v3/gates.md`](../design-v3/gates.md)  
- Prior: [Report 12](./12-action1-correctness-oracle.md) (Action 1 PASSED)
