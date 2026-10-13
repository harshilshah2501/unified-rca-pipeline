# Decision-validation sprint (post Stage 4.2)

**Status:** proposed program lock for closing synthetic benchmarking — **not** a Motadata production architecture approval.  
**Basis:** [Report 10](../reports/10-design-v3-comprehensive.md), [Report 11](../reports/11-map-vortex-engineering-brief.md), [Architecture Decision Record](../reports/Map_Vortex_Graph_Architecture_Decision_Record.md).  
**Rule:** This is a **focused decision-validation sprint**, not another broad exploration of graph architectures.

---

## 0. Freeze the candidate set

Stop introducing new primary-benchmark layouts.

| Candidate | Role after Stages 3.5–4.2 |
| --------- | ------------------------- |
| **`hash`** | Fastest reconstruction; expensive reverse. Control + legitimate candidate for explicitly forward-only product modes. |
| **`hash_bi`** | Faster reconstruction than CSR+CSC in synthetic screens; efficient bidirectional traversal. |
| **`csr_csc`** | Slower reconstruction; substantially smaller retained index; efficient bidirectional traversal. |

**Out of the primary sprint matrix:** standalone `csr`, `hybrid` (keep available for mutation follow-ups), segmented CSR+CSC (Milestone B only).

These patterns are **synthetic observations**, not production conclusions.

**Current shortlist for bidirectional Scope / blast-radius:** `hash_bi` versus `csr_csc`. Retain `hash` as control and for forward-only modes.

---

## 1. Define what winning means (product input — blocking)

The bench currently measures several dimensions without a Motadata-approved rule for choosing among them. Without product requirements we can draw a **Pareto frontier** but cannot objectively select a winner (for example, a 20 µs reverse gap may be irrelevant if both pass the query SLO while recovery time and memory do not).

### Priority stack for Motadata Map

| Priority | Dimension | Why it matters |
| -------- | --------- | -------------- |
| P0 | Correctness | All layouts must represent the same graph |
| P0 | Forward / reverse query SLO | Scope and blast-radius must stay responsive |
| P0 | Cold-to-hot recovery time | Service readiness after restart / failover |
| P0 | Peak memory | Rebuild must fit the deployment memory budget |
| P1 | Retained index memory | Steady-state capacity |
| P1 | Concurrency | Real queries run simultaneously |
| P1 | Mutation-to-visibility | Topology freshness |
| P2 | CPU consumption | Operating cost and contention |

### Missing Motadata decisions (must be filled or explicitly waived)

For each P0/P1 row, product/ops must state a number, a range, or an approved “synthetic operating envelope” waiver:

- Query mix (forward vs reverse vs dependency / typed Scope walks)  
- Latency SLO (p95 / p99 targets per class)  
- Recovery-time budget (`T_ready`)  
- Peak RSS ceiling during rebuild and during dual-snapshot overlap  
- Freshness / bounded-staleness budget (if mutation is in scope)  
- Supported scale envelope (do not extrapolate 5M → 20M/50M without evidence)

### Constraint-based selection (not weighted scoring)

1. Eliminate any candidate that fails correctness, query SLO, recovery-time SLO, or peak-memory limits.  
2. Among survivors, prefer the costs Motadata cares about most under the stated operating envelope (recovery vs retained memory vs reverse share).

| Operating condition | Likely winner (synthetic hint only) | Confidence |
| ------------------- | ----------------------------------- | ---------- |
| Predominantly forward-only; recovery speed dominates | `hash` | Supported by synthetic results |
| Bidirectional; recovery matters more than retained memory | `hash_bi` | Supported by synthetic results |
| Bidirectional; memory efficiency matters | `csr_csc` | Supported by synthetic results |
| Frequent mutations with strict visibility | Localized → segmented candidate; all-touch → conventional `csr_csc` | Action 6 closed under synthetic mutation envelope ([Report 21](../reports/21-action6-milestone-b-close.md)) |
| Concurrent production workload | Undetermined | Concurrency not validated |

---

## 2. Six prioritized actions

### Action 1 — Strengthen correctness (P0 — blocking)

**Intent:** No performance ranking is final until candidates pass an **independent** correctness oracle that is stronger than walk-checksum-only.

**Evidence note (Stage 4.2):** The Stage 4.2 screen `status.log` recorded **no** `FAIL` / `correctness_ok=false` cells under the existing forward walk checksum vs hash. That does **not** mean the oracle is sufficient. Walk checksum equivalence ≠ full typed multigraph proof. Older or ad-hoc natural-order suspicions must be re-audited under the new oracle; if none reproduce, document exclusion with explanation rather than leaving a vague “anomaly” open.

**Require the oracle to check:**

1. Exact node and edge counts.  
2. Directed typed-edge **multiset** equality (including duplicate occurrences).  
3. Forward / reverse adjacency symmetry (`B ∈ Out(A)` iff `A ∈ In(B)` for every typed occurrence, per layout semantics).  
4. Reachable-node equivalence for all benchmark queries.  
5. Correctness across **clustered** and **natural** edge ordering.

Also confirm degree-percentile definitions: Stage 4.2 seeds use out-degree percentiles among **sources with edges** (`p10` / `p50` / `p90`; reverse-heavy also **max-hub**)—not all nodes. Re-check power-law estate stats against that definition.

**Exit gate:** Every candidate passes the independent oracle. Failed natural-order cells are fixed and rerun, or excluded with a documented explanation.

**Status (2026-10-13):** **PASSED** — see [Report 12](../reports/12-action1-correctness-oracle.md). Defect found: `sort_aware` dropped arcs on natural order (`HashMap::insert` overwrite); fixed to extend buckets. Re-ran clustered + natural for `hash` / `hash_bi` / `csr_csc` at 100k and 500k (uniform, hubby, power_law).

### Action 2 — Representative Motadata graph / workload characteristics (P0)

Synthetic families remain modeling assumptions. Prefer anonymized structural statistics over raw customer topology:

| Property | Why |
| -------- | --- |
| Nodes and edges | Scale |
| In-/out-degree distributions | Hub concentration |
| Edge-type frequencies | Typed traversal |
| Duplicate-edge frequency | Multigraph correctness |
| Connected components | Traversal shape |
| Traversal depth distribution | Query cost |
| Forward / reverse query proportions | Index selection |
| Mutation rate and burst size | Update economics |

**Most important missing input:** actual Scope workload mix. If production is ~forward-only, `hash` stays central; if reverse / blast-radius is operationally important, `hash_bi` / `csr_csc` dominate.

**Exit gate:** At least one representative estate profile **and** one representative query profile — **or** an explicitly approved synthetic operating envelope if production data is unavailable.

**Status (2026-10-13):** **PASSED** — see [Report 13](../reports/13-action2-operating-envelope.md). Waiver path B signed (Harshil Shah — Motadata product, Pillar B eng, ObserveOps / RCA):

- Intake: [`action2-motadata-workload-intake.md`](./action2-motadata-workload-intake.md) (§5–§6)  
- Approved envelope: [`action2-synthetic-operating-envelope.md`](./action2-synthetic-operating-envelope.md) — estate `motadata_like_hubby` + query `scope_policy_mixed` (70% forward / 20% reverse / 10% both)

Actions 3–5 proceed under this envelope; winners remain **envelope-conditional**, not Motadata-wide locks.

### Action 3 — Statistically credible final comparison (P0)

Do **not** expand the architecture matrix. Run only:

`hash` vs `hash_bi` vs `csr_csc`

Identical snapshots, identical traces, identical hardware.

| Factor | Final experiment |
| ------ | ---------------- |
| Layouts | 3 |
| Scales | 1M, 5M |
| Graph shapes | Uniform, hub-heavy, **`motadata_like_hubby`** (Action 2 approved envelope) |
| Edge ordering | Clustered (natural only as correctness control) |
| Query workloads | Forward-dominant, balanced, reverse-heavy, plus weighted **`scope_policy_mixed`** (Action 2 approved) |
| Build repetitions | ≥ 20 (recommendation; not established by prior reports) |
| Query samples | Enough for p95/p99 with stated confidence |
| Concurrency | 1, 4, 16 readers (recommendation for Action 5 overlap) |

Record **distributions and confidence intervals**, not winners from a single p95.

Per candidate measure: build time, first-query readiness, forward / reverse / dependency-chain latency, peak RSS, retained index bytes, CPU.

**Exit gate:** Relative performance and memory trade-offs are reproducible; uncertainty small enough to support the decision.

**Status (2026-10-13):** **PASSED** — [Report 14](../reports/14-action3-final-compare.md). 33/33 cells OK. Under approved envelope, **`csr_csc`** wins envelope-weighted latency and steady index; `hash` wins build p50 but loses on reverse; `hash_bi` is latency runner-up at higher memory. Matrix: [`action3-run-matrix.md`](./action3-run-matrix.md).

### Action 4 — Real cold-to-hot recovery (P0)

`process_cold` alone does not prove cold OS page cache or remote-tier reads.

Measure readiness as:

\[
T_{\text{ready}} = T_{\text{read/decode}} + T_{\text{index build}} + T_{\text{publish}}
\]

accounting for overlap. Distinguish:

| Label | Meaning |
| ----- | ------- |
| Process-cold | Fresh process; filesystem cache may be warm |
| Disk-cold | Must read from local storage (cache dropped / equivalent) |
| Remote-cold | Must retrieve from Motadata’s configured remote Dest tier |

Include memory peak during load and construction.

**Exit gate:** We know which layout reaches query-ready fastest under **intended deployment conditions**, not only which builds fastest after decode.

**Status (2026-10-13):** **PASSED** — [Report 15](../reports/15-action4-cold-recovery.md). Fastest T_ready is **`hash`** on every coldness tier; `csr_csc` is slowest to ready. Real Dest remote-cold still deferred (`remote_proxy` lab only).

### Action 5 — Concurrency and memory (P0)

Existing evidence is largely single-reader. Measure:

| Measurement | Required observation |
| ----------- | -------------------- |
| Query throughput | Queries/sec vs concurrency |
| Query tail latency | p95 and p99 |
| Peak RSS | During construction and publication |
| Memory amplification | Old + new indexes temporarily coexisting |
| CPU saturation | Compute-limited or not |
| Recovery interference | Rebuild impact on in-flight queries |

Illustrative Stage 4.2 5M hubby balanced (synthetic screen, not final):

| Metric | `hash_bi` | `csr_csc` |
| ------ | --------: | --------: |
| Build | ~6.88 s | ~10.58 s |
| Reverse p95 | ~0.051 ms | ~0.030 ms |
| Retained index (estimate) | ~1.13 GB | ~0.51 GB |

**Exit gate:** Every remaining candidate satisfies peak-memory and query SLO under expected concurrency.

**Status (2026-10-13):** **PASSED** — [Report 16](../reports/16-action5-concurrency.md). Under concurrent readers, **`csr_csc`** keeps the highest QPS and best p95/p99; `hash` reverse tails collapse.

### Action 6 — Mutation lifecycle economics (P1 for read-layout pick; P0 before production architecture approval)

Preference from architecture discussion: incremental reconstruction → atomic publication → bounded staleness. Conventional monolithic `csr_csc` does **not** automatically provide efficient incremental reconstruction; that needs a **segmented** candidate (Milestone B).

For the three conventional layouts (and later segmented), compare mutation-to-visibility, update/rebuild cost, peak memory during publication, query interference, crash recovery/replay, and CPU per committed mutation. Same mutation batch across candidates.

**Exit gate:** Know whether the selected read layout can meet freshness without unacceptable maintenance cost — or explicitly defer mutation to Milestone B while choosing a **read-mostly** baseline first.

**Status (2026-10-13):** **CLOSED** — [Report 21](../reports/21-action6-milestone-b-close.md). Segmented CSR+CSC retained as **conditional** candidate for localized mutations (`mut_localized`); conventional `csr_csc` remains serve baseline. Spec: [`action6-mutation-lifecycle.md`](./action6-mutation-lifecycle.md).

---

## 3. Additional issues to record (not all need large experiments now)

1. **Query semantics** — directed typed multigraph; eventually include Scope edge-type filters, depth, direction changes, duplicates, temporal versions—not only bare reachability.  
2. **Memory accounting** — report both estimated retained index **and** process RSS; include temps, metadata, overlapping snapshots.  
3. **Graph growth** — state the supported scale envelope; do not extrapolate 5M → 20M/50M without evidence.  
4. **Failure behavior** — construction failure, interrupted publication, crash with pending topology changes.

Document as assumptions or production acceptance gates when not measured immediately.

---

## 4. Finish line — two milestones

### Milestone A — Close the benchmarking study — **FROZEN**

Complete Actions **1–5** — **done** ([Report 17](../reports/17-milestone-a-close.md)).

Deliverable locked: constraint-based winner among `hash` / `hash_bi` / `csr_csc` for the **approved** operating envelope — conventional baseline **`csr_csc`**; recovery reference **`hash`**.

### Milestone B — Validate the production architecture — **CLOSED (conditional)**

Complete Action **6** — **done** ([Report 21](../reports/21-action6-milestone-b-close.md)).

**Outcome:** Conventional serve winner (`csr_csc`) deploys as baseline; segmented CSR+CSC is a **conditional** evolution for localized mutation publish windows under the approved synthetic mutation envelope — not a universal replacement.

**Distinction (locked):** the fastest graph to reconstruct is not the fastest graph to serve; the best mutable production architecture remains locality-conditional.

---

## 5. Final recommendation (this sprint)

1. **Freeze** the candidate set; stop new primary layout variants.  
2. **Fix / strengthen correctness** first (Action 1).  
3. **Obtain** representative workload information or an approved synthetic envelope (Action 2) — **done** (waiver).  
4. Run a **focused** final comparison of the three candidates (Actions 3–5).  
5. Treat mutation / segmented designs as **Milestone B**, unless Motadata requires mutation in the initial winner criteria.

**The most important missing input is not another data structure.** It is a precise product-level definition of success: query mix, latency requirements, recovery-time budget, memory ceiling, and freshness requirement.
