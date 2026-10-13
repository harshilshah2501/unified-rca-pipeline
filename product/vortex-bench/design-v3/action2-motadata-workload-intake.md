# Action 2 — Motadata graph & Scope workload intake

**Purpose:** Collect **anonymized** structural and workload statistics so Milestone A can choose among `hash` / `hash_bi` / `csr_csc` under a **stated operating envelope** — not under unlabeled synthetic assumptions.

**Do not** export raw customer topology or entity names. Aggregates and histograms are enough.

**Owner:** Motadata product / SRE / Pillar B engineering (fill or waive).  
**Consumer:** Design v3 decision-validation sprint ([`decision-validation-sprint.md`](./decision-validation-sprint.md)).  
**Related product brief:** [`../../contracts/MAP_SCOPE_WALK_POLICY.md`](../../contracts/MAP_SCOPE_WALK_POLICY.md).  
**Action 2 status:** **PASSED** (2026-10-13) — waiver path B; envelope approved for Milestone A only.

---



## 1. How to use this form

1. Fill §2–§4 with measured or best-estimate values (label each cell **measured** / **estimated** / **unknown**).
2. If data cannot be shared, mark §5 waiver and review the synthetic envelope in [`action2-synthetic-operating-envelope.md`](./action2-synthetic-operating-envelope.md).
3. Sign §6. Winners remain **envelope-conditional** (not Motadata-wide locks) until real stats replace this waiver.

---



## 2. Estate structure (anonymized)


| Property                                | Value | Units / notes                                                    | Confidence                     |
| --------------------------------------- | ----- | ---------------------------------------------------------------- | ------------------------------ |
| Typical tenant node count               |       | nodes                                                            | measured / estimated / unknown |
| Typical tenant edge count               |       | directed typed edges                                             |                                |
| p50 / p90 / p99 / max **out**-degree    |       | among sources with ≥1 edge                                       |                                |
| p50 / p90 / p99 / max **in**-degree     |       | among sinks with ≥1 edge                                         |                                |
| Top 1% sources’ share of edges          |       | fraction 0–1                                                     |                                |
| Duplicate typed-edge rate               |       | fraction of edges that are 2nd+ occurrence of `(src, type, tgt)` |                                |
| Weak connected component count (approx) |       | undirected                                                       |                                |
| Dominant edge types (top 5)             |       | name + share                                                     |                                |
| CI type mix (top 5)                     |       | e.g. service / host / database shares                            |                                |
| Layering / hierarchy present?           |       | yes/no + brief                                                   |                                |


Optional: attach a **histogram CSV** (degree bucket → count) with no identifiers.

---



## 3. Scope / query workload (most important)

Scope defaults in the product brief are **forward (**`out`**), hops = 2**, with **some detect classes requiring inbound or both** (saturation, monitoring, optional slowdown ingress). Fill production reality:


| Question                                                                   | Answer                     | Confidence |
| -------------------------------------------------------------------------- | -------------------------- | ---------- |
| Share of Scope walks that are **forward-only** (`out`)                     | % of cases / of walk calls |            |
| Share that use **inbound** or **both** (blast / “who runs here” / ingress) | %                          |            |
| Typical hop budget in production                                           | hops                       |            |
| p95 WorkingSet size (CI count)                                             | nodes                      |            |
| Concurrent Scope walks per GraphWriter process (peak)                      | readers                    |            |
| Are reverse/blast walks on the **critical path** for any GA detect class?  | yes/no + which classes     |            |


If you cannot measure percentages, give an ordered judgment:

1. Primary mode: _______________________
2. Secondary mode: _______________________
3. Rare / stress only: _______________________

---



## 4. Mutation / freshness (feeds Action 6; optional for read-layout pick)


| Property                                              | Value   | Confidence |
| ----------------------------------------------------- | ------- | ---------- |
| Steady-state edge mutations / minute (typical tenant) |         |            |
| Burst size (edges changed in a publish window)        |         |            |
| Acceptable topology staleness after mutation          | seconds |            |
| Publish / rebuild allowed to block Scope?             | yes/no  |            |


---



## 5. Waiver (if production stats unavailable)

- [x] We **cannot** provide §2–§3 for this sprint.  
- [x] We **approve** the synthetic operating envelope in [`action2-synthetic-operating-envelope.md`](./action2-synthetic-operating-envelope.md) for Milestone A only.  
- [x] We understand Milestone A winners are **envelope-conditional**, not Motadata-wide locks.

---



## 6. Sign-off


| Role             | Name         | Date       | Decision |
| ---------------- | ------------ | ---------- | -------- |
| Motadata product | Harshil Shah | 2026-10-13 | **approved synthetic envelope** (waiver; §2–§3 not provided) |
| Pillar B eng     | Harshil Shah | 2026-10-13 | **approved synthetic envelope** |
| ObserveOps / RCA | Harshil Shah | 2026-10-13 | **approved synthetic envelope** |


