# Action 6 — Mutation lifecycle (Milestone B)

**Status:** **CLOSED** (2026-10-13) — [Report 21](../reports/21-action6-milestone-b-close.md). Milestone A remains frozen. Segmented CSR+CSC is a **conditional** candidate for localized mutations under [`action6-synthetic-mutation-envelope.md`](./action6-synthetic-mutation-envelope.md).

**Central question:**

> Can **segmented CSR+CSC** preserve the traversal and memory advantages of conventional CSR+CSC while substantially reducing the cost of publishing topology mutations?

**Baseline (frozen):** conventional `csr_csc` under approved envelope — [Report 17](../reports/17-milestone-a-close.md).  
**Hypothesis under test:** adaptive node-group **segmented CSR+CSC** with incremental reconstruction, atomic snapshot publication, pinned readers — see ADR [`../reports/Map_Vortex_Graph_Architecture_Decision_Record.md`](../reports/Map_Vortex_Graph_Architecture_Decision_Record.md).  
**First ladder:** [Report 18](../reports/18-action6-mutation-lifecycle.md) — locality-dependent \(T_{\mathrm{mutation\text{-}visible}}\) gains.

---

## 0. Architectural position (preserve)

| Role | Choice | Status |
| ---- | ------ | ------ |
| Serve baseline | conventional `csr_csc` | **Frozen** (Milestone A) |
| Recovery-speed reference | `hash` | **Frozen** |
| Milestone B candidate | segmented CSR+CSC | **Conditional** — earns complexity only when mutations are sufficiently localized |
| Three-layout reopen | — | **Not allowed** unless production evidence contradicts the approved envelope |

**Candidate policy (lab, under synthetic mutation envelope):** `mut_localized` (10 inserts / 2 deletes) → segmented wins on \(T_{\mathrm{mutation\text{-}visible}}\) at 1M and 5M; `mut_medium` / all-segment-touch → conventional full rebuild is as-fast or faster. Not a Motadata production routing rule until measured churn is available.

---

## 1. What we are *not* reopening

| Locked by Milestone A | Role |
| --------------------- | ---- |
| Envelope `motadata_like_hubby` + `scope_policy_mixed` | Workload assumption |
| Conventional hot-index baseline = **`csr_csc`** | Steady-state query + concurrency |
| `hash` as recovery-speed reference | T_cold-ready only |
| Action 1–5 reports + `out/design-v3/action{1,3,4,5}` | Reference benchmarks — preserve |

---

## 2. Three timings (keep separate)

| Symbol | Meaning | Milestone A analogue |
| ------ | ------- | -------------------- |
| \(T_{\mathrm{cold\text{-}ready}}\) | Reconstruct graph from Vortex parts to first query-ready snapshot | Action 4 T_ready |
| \(T_{\mathrm{mutation\text{-}visible}}\) | Accepted topology mutation → appears in a **published** snapshot | **Action 6** |
| \(T_{\mathrm{query}}\) | Traversal against a **pinned consistent** snapshot | Action 3/5 query |

A design may improve one while degrading another. Report each separately; never collapse into a single “winner” number.

---

## 3. Candidates

| Candidate | Description |
| --------- | ----------- |
| `csr_csc` | Conventional monolithic CSR+CSC — **full rebuild** on every mutation batch (Milestone A baseline) |
| `segmented_csr_csc` | Node-group segments; rebuild **only affected** segments; publish new snapshot (Arc swap) |

### Implementation hypothesis boundary

**Current v0** rebuilds a touched segment by rescanning the authoritative edge list and filtering by segment membership. Report 18 therefore measures the benefit of **skipping untouched segment reconstruction**, not the full benefit of per-segment edge journals.

**Per-segment edge journals** (or other affected-edge indexes) are a **separate optimization hypothesis**. Do not fold their assumed speedups into current conclusions. They would add consistency and recovery obligations of their own.

---

## 4. Residual priority order (after Report 18)

1. **Atomic publication with pinned readers** — prove readers see either the complete old snapshot or the complete new snapshot; never mixed forward/reverse adjacency from different generations.  
2. **Memory amplification during publication** — peak RSS while old pins retain the previous snapshot and the next is built. Retained-index size alone is insufficient.  
3. **Failure, durability, and replay** — **NEXT GATE** (after Report 19). Crash before/during/after publish; which generation is authoritative; how unapplied mutations recover.  
4. **Mutation realism** — Motadata-representative batch sizes and locality (intake §4 when available) **or** approved synthetic mutation envelope: [`action6-synthetic-mutation-envelope.md`](./action6-synthetic-mutation-envelope.md).  
5. **5M thin ladder** — scale check under that mutation envelope while the edge-list rescan implementation remains in force.

**Report 19 closed priorities 1–2 for the 1M lab model** (atomic publish + dual-hold RSS). That is positive evidence for the lab `Arc`-swap publication mechanism under overlap — **not** a crash-consistency or Motadata capacity guarantee.

### Priority 3 failure matrix (proposed test requirements)

| Failure point | Required verification |
| ------------- | --------------------- |
| Before mutation persistence | Recovery retains previous committed generation; uncommitted changes are not presented as committed |
| After mutation persistence, before publication | Recovery can replay or reconstruct the intended new state |
| During snapshot construction | Incomplete snapshot is never served as committed state |
| During or immediately after publication | Recovery identifies a valid committed generation; no mixed CSR/CSC |
| After publication, before replay progress is durably recorded | Replay does not lose mutations or double-apply in a way that changes graph semantics |

Independent oracle after each recovery: typed-edge multiset, duplicates, CSR⇔CSC symmetry, generation identity. Also record recovery time and mutations lost/replayed.

**Lab durability model only** — does not claim Motadata already ships this commit protocol. Per-segment journals stay out of this gate.

**Most valuable next result:** durable recovery correctness at publication boundaries — not another isolated speedup.

---

## 5. Run matrix

| Factor | Levels |
| ------ | ------ |
| Estate | `hubby` (envelope), scale **1M** primary; **5M** thin ladder |
| Mutation batches | Small localized (10/2), medium (1k/200), large (all-touch) |
| Segment count | 16, 64, 256 (sensitivity) |
| Overlap | (a) mutation alone; (b) concurrent pinned readers during rebuild+publish |
| Metrics | \(T_{\mathrm{mutation\text{-}visible}}\) p50/p95; dual-hold peak RSS; atomicity checks; \(T_{\mathrm{query}}\) on pinned snapshot |

**Exit gate:** **Met** — [Report 21](../reports/21-action6-milestone-b-close.md). Segmented CSR+CSC is worth the complexity only under localized mutation batches (`mut_localized`); keep conventional `csr_csc` as serve baseline and for all-touch publishes.

---

## 6. Artifacts

| Path | Role |
| ---- | ---- |
| [`../map-vortex-bench/src/segmented.rs`](../map-vortex-bench/src/segmented.rs) | Segmented CSR+CSC + snapshot publish |
| [`../map-vortex-bench/scripts/action6_mutation.sh`](../map-vortex-bench/scripts/action6_mutation.sh) | Speed ladder |
| [`../map-vortex-bench/scripts/action6_overlap.sh`](../map-vortex-bench/scripts/action6_overlap.sh) | Atomicity + dual-hold RSS |
| [`../reports/18-action6-mutation-lifecycle.md`](../reports/18-action6-mutation-lifecycle.md) | First locality ladder |
| [`../reports/19-action6-atomic-publish.md`](../reports/19-action6-atomic-publish.md) | Overlap / memory residual (priorities 1–2) |
| [`../map-vortex-bench/scripts/action6_durability.sh`](../map-vortex-bench/scripts/action6_durability.sh) | Priority 3 failure/replay ladder |
| [`../reports/20-action6-durability-replay.md`](../reports/20-action6-durability-replay.md) | Durability / replay residual |
| [`action6-synthetic-mutation-envelope.md`](./action6-synthetic-mutation-envelope.md) | Priority 4 — approved synthetic mutation envelope |
| [`../reports/21-action6-5m-thin-ladder.md`](../reports/21-action6-5m-thin-ladder.md) | Priority 5 — 5M thin ladder |
| [`../reports/21-action6-milestone-b-close.md`](../reports/21-action6-milestone-b-close.md) | **Action 6 / Milestone B close** |

---

## 7. Revision

| Date | Change |
| ---- | ------ |
| 2026-10-13 | Opened from Milestone A freeze |
| 2026-10-13 | Report 18 locality finding; residual priority order + journal hypothesis boundary locked |
| 2026-10-13 | Report 19 closed priorities 1–2; priority 3 failure matrix locked as next gate |
| 2026-10-13 | Report 20 closed priority 3 (lab durability); priorities 4–5 + Report 21 close |
