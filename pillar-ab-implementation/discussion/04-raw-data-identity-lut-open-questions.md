# Discussion 04 — Raw data, identity lookups, and open questions for the team

**Date:** 2026-08-27  
**Status:** Discussion input — **not** a locked contract.  
**Audience:** Motadata / ObserveOps owners who need to decide how long we keep raw samples, how Identity resolves names into configuration items, and what Pillar A (percentiles / sketches) and Pillar B (topology) may admit.  
**Source synthesis:** [`../Raw_Data_Handling.pdf`](../Raw_Data_Handling.pdf) (six cases, Edge Delta check, shift-left vs zero-raw).  
**Also aligned with:** [`../../docs/observeops/LLD-E2-Identity.md`](../../docs/observeops/LLD-E2-Identity.md) · [`../../docs/GRAPH_QNA.md`](../../docs/GRAPH_QNA.md) (§9 merge / raw) · graph contract evidence types · Dynatrace-shaped bind miss policies in vendor docs.

---

## 1. Why we are meeting

Pillar A deliberately **compresses then discards** raw metric samples into a sketch (T-Digest + buckets + seasonal baseline). That is irreversible: anything the sketch did not keep is gone. Most of Detect and RCA can live on sketches. A few operational cases still need **some** raw (or a rebuild path). The sharpest **live pipeline** case is **late identity resolution**: a sample arrives before we know which configuration item it belongs to.

This note turns the PDF’s open list into **vote-ready questions**: each one has context, why it bites, options, and **our proposed leaning** for the room to accept, amend, or reject.

---

## 2. Terms (plain language — use these in the meeting)

| Short name | Meaning |
|------------|---------|
| **Raw sample** | One admitted measurement or event before sketch compression (exact value + timestamp + labels). |
| **Sketch** | Lossy summary in the `history/` room (`sketch.v1`). Good for percentiles and Detect; cannot recreate every original point. |
| **Identity (E2)** | Pipeline stage that stamps each record with `tenant` + `ci_id` (same string as sketch `entity_id`) and `identity.status`. |
| **Look-up table (LUT)** | The bind table Identity uses: raw labels (monitor id, `service.name`, host name, …) → stable `ci_id`. Teaching shorthand from Dynatrace-shaped docs; in ObserveOps this is **E2’s bind table**, not a third store room beside `map/` and `history/`. |
| **LUT miss** | Incoming labels do not hit any row yet — Identity cannot stamp `resolved`. |
| **Quarantine buffer** | A **bounded** hold of unresolved raw samples (hours–days). When Identity later resolves, we **replay** those samples into the sketch writer and merge into the original window. Not a full compliance archive. |
| **Unattributed queue** | Query surface over records with `identity.status` not `resolved` (LLD-E2 / FR-B1). They are **not** silently dropped from visibility — but Pillar A/B writers still must not treat them as production join keys. |
| **Evidence strength** (graph) | Who owns a topology fact: **authoritative** (inventory / system of record), **declared** (CMDB / catalog), **corroborating** (telemetry suggests). Separate from LUT miss policy. |
| **Shift-left** | Reduce volume at the edge (mask, filter, enrich) **before** centralizing. |
| **Zero-raw retention** | After admit, discard raw once the sketch exists. Independent from shift-left. |
| **Rehydration** | Edge Delta’s name for an on-demand job that pulls full-fidelity archived events from cold object storage back into a destination. Broader than our quarantine idea. |

**Do not confuse:**

- **Rooms** (`map/` vs `history/`) ≠ **temperature** (Vortex hot vs S3 cold).
- **LUT / Auto-create / Orphan / Soft-match** = what to do when a **name does not bind** to a CI.
- **`evidence_type`** = who owns or suggests an **edge** on the map. Not a 1:1 map onto Auto-create / Orphan / Soft-match.

---

## 3. Background the room should share

### 3.1 Six cases where raw would still help

From the PDF. Sketches alone cannot answer these:

| # | Case | Why the sketch fails |
|---|------|----------------------|
| 1 | Bug in aggregation logic | Wrong digest / window / season → every Detect verdict wrong until rebuild from raw. |
| 2 | Late identity resolution | Unresolved samples never enter sketches; if identity arrives later, those samples are gone unless buffered. |
| 3 | Brand-new metric | Catalog did not allow that `metric_id` yet — no historical sketch to backfill. |
| 4 | Forensic / compliance / legal | Need the exact value at an exact time, not a percentile. |
| 5 | ML training / algorithm backtest | New features often need samples nobody pre-aggregated. |
| 6 | Drill-down beyond one exemplar | One exemplar ≠ every request in a hot bin. |

### 3.2 Which cases touch the **live** RCA pipeline

| # | Ongoing impact? | Nature of the fix |
|---|-----------------|-------------------|
| **1** | **Most severe** — live Detect is wrong continuously | One-time: patch code + backfill damaged windows |
| **2** | **Yes — real coverage gap** while unresolved | Needs a **repeatable structural loop** (quarantine → resolve → replay → merge) |
| **3** | Partial | Config add to metric catalog; forward path self-heals; baselines grow via E5 (seasonal maintenance). Not an identity loop |
| 4 | No | Human / legal, backward-looking |
| 5 | Indirect | Human redeploys a model later |
| 6 | No | Terminal investigation |

**Case 3 is not Case 2.** Case 2 fails the gate `identity.status == resolved` (owned by E2). Case 3 fails `metric_id` in the allowed catalog (owned by schema / config). E2 does not need to change when a metric is added.

### 3.3 Case 2 corrected: a **race**, not “Topology then Identity”

Three independent sources can strengthen identity / topology facts in any order:

| Source | Strength | Typical owner |
|--------|----------|---------------|
| Inventory scan | **authoritative** | Agent process inventory, cgroup, Kubernetes API |
| CMDB / catalog sync | **declared** | CMDB, service catalog, Helm, Terraform |
| Telemetry accumulation | **corroborating** | Repeated spans / logs |

**Asymmetry that matters:** only **authoritative** or **declared** evidence should produce `identity.status = resolved` for production join. Corroborating alone typically justifies **synthesized** at best. Graph rule **D-E2-1**: synthesized / unattributed identities are **not** E9 leaf or ServiceOps ticket targets. Pillar A and Pillar B writers admit **`resolved` only** (PoC `ResolvedOnlyGate`).

So two sub-cases hide under “late identity”:

| Sub-case | What happens | Real risk? |
|----------|--------------|------------|
| Entity already in CMDB/catalog; labels not matched yet | Resolves when **declared** sync hits the LUT — often near-instant | Low — quarantine barely matters |
| Entity genuinely new / ephemeral; only telemetry has seen it | Stuck on corroborating; needs an **inventory** (authoritative) scan before buffer expiry | **High — real design gap** |

**Design question is buffer duration and miss policy**, not “whether a loop exists.”

Once resolved, replay can **merge** into the original window’s T-Digest (digests merge by design). Buckets merge only if `bucket_schema_version` still matches.

### 3.4 Edge Delta reality check (from the PDF)

Edge Delta **does** shift-left at the agent (mask, filter, enrich) but **does not** choose zero-raw retention: full-fidelity events go to cold object storage; **Rehydrations** pull them back on demand (forensic, investigation, backfill).

Implication for us: shift-left and “keep only sketches” are **two decisions**. A **narrow quarantine** for Case 2 is the same *principle* as Rehydration at much smaller scope — not a commitment to Edge Delta’s full archive product.

### 3.5 How LUT miss policies relate (Dynatrace-shaped language)

When raw labels miss the LUT:

| Policy | Job |
|--------|-----|
| **Auto-create** | Mint a new CI + LUT row (“seen ⇒ exists”) |
| **Orphan** | Keep telemetry unbound / quarantine — no production join key yet |
| **Soft-match** | Alias the label onto an **existing** `ci_id` |

That is **node-identity bind** fallback. It is **not** `evidence_type` on an edge.

ObserveOps today (LLD-E2 Signed default): prefer **synthesize flagged placeholders** + **unattributed queue** rather than poison dead-letter; do **not** use synthesized as localize/ticket targets. Pillar A/B still reject non-`resolved` for sketch / map production writes.

---

## 4. Open questions for the team

For each question: **context → why it matters → options → proposed leaning → what we need from the room**.

---

### Q1 — Quarantine buffer duration (Case 2)

**Context.** Unresolved samples that never enter a quarantine are permanently missing from sketches for that window. The PDF’s loop is: miss LUT → hold raw in a bounded buffer → whichever of inventory / catalog resolves first updates the LUT → replay → merge into the original `window_start` / `season_key`.

**Why it matters.** Catalog-known entities resolve fast; **novel** entities only resolve when an inventory scan runs. Buffer too short → permanent sketch holes on new services/hosts. Buffer too long → cost, privacy surface, and “almost a raw lake.”

**Options.**

1. **Hours** (for example 4–12h) — cheap; high loss if inventory is daily.  
2. **About one day** (24h) — covers many overnight inventory cadences.  
3. **Few days** (48–72h) — safer for slow discovery; closer to a mini-archive.  
4. **No quarantine** — accept permanent gaps; rely on Auto-create or synthesized-only paths (hurts sketch coverage or D-E2-1 discipline).

**Proposed leaning.** Start discussion at **24 hours** tenant-default, with a metric: “% of quarantined samples resolved before expiry” split by **catalog-known vs novel**. Raise to 72h only if inventory SLAs prove slower. Cap hard (no indefinite hold). Expired samples leave a **countable gap** signal (not silent).

**Ask the room.** What is Motadata’s realistic **inventory discovery SLA** for a brand-new CI? That number should set the default more than aesthetics.

---

### Q2 — Catalog / CMDB sync cadence (declared evidence)

**Context.** For entities already in CMDB/catalog, late bind is usually “LUT not updated yet,” not “entity unknown to the world.”

**Why it matters.** If declared sync is frequent enough, quarantine is almost idle for catalog-known traffic. Engineering and ops attention then concentrates on **novel** entities (Q1 high-risk sub-case).

**Options.**

1. Treat catalog sync as **near-real-time** (seconds–minutes) and document quarantine as mainly for novel CIs.  
2. Accept **batch** sync (hourly/daily) and size quarantine to cover the batch delay even for catalog-known.  
3. Soft-match aggressively so catalog names alias quickly without waiting for a full sync job.

**Proposed leaning.** **(1)** for Motadata-shaped SaaS: declared sync should be fast enough that catalog-known Case 2 is rare. Quarantine sizing is justified by **inventory lag for novel CIs**, not by CMDB batch windows. Soft-match (Q3) is a separate policy, not a substitute for sync health.

**Ask the room.** What is today’s Motadata catalog / monitor-bind refresh interval in lab and in production intent?

---

### Q3 — LUT miss policy for production joins (Auto-create vs Orphan vs Soft-match)

**Context.** Dynatrace-shaped pipelines name three miss behaviors. ObserveOps LLD-E2 Signed path synthesizes flagged placeholders and keeps an unattributed queue; Pillar A/B admit **resolved only**.

**Why it matters.** This decides whether a brand-new `service.name` immediately gets a sketch series (Auto-create), waits in quarantine (Orphan-like), or attaches to an existing CI (Soft-match). Wrong choice either **pollutes** the map with junk nodes or **blinds** Detect on real new services.

**Options.**

| Policy | Sketch / map effect | Risk |
|--------|---------------------|------|
| **Auto-create** as `resolved` | Immediate Pillar A/B writes | Map spam; weak CIs become ticket targets unless gated |
| **Orphan + quarantine** | No production write until authoritative/declared resolve | Coverage gap until Q1 buffer wins or expires |
| **Synthesize** (`identity.status=synthesized`) | Visible on unattributed queue; **rejected** by Pillar A/B gates | No sketch hole “filled” with fake production keys; matches D-E2-1 |
| **Soft-match** | Joins existing `ci_id` | Wrong alias → wrong Detect / wrong Localize root |

**Proposed leaning (combined).**

1. **Default miss:** emit **synthesized** or **unattributed** (LLD-E2), **never** poison-drop; **do not** admit to Pillar A/B.  
2. **Hold raw in quarantine** (Q1) keyed by unresolved identity keys.  
3. Promote to **`resolved`** only when **declared** or **authoritative** evidence updates the LUT.  
4. **Auto-create** as `resolved` only under an explicit product flag (lab / “discovery mode”), not as Motadata default for ticketable CIs.  
5. **Soft-match** only with high-confidence rules (normalized name + tenant + type); always auditable; prefer human/catalog confirmation for ticketable roots.

**Ask the room.** Confirm: production Detect/Localize must **not** treat Auto-create-from-telemetry alone as a ServiceOps-ticket CI unless inventory/catalog later upgrades evidence.

---

### Q4 — Who owns and refreshes the LUT?

**Context.** Bind is E2’s job. Sources that *feed* the LUT are inventory, CMDB/catalog, and (weakly) telemetry. Pillar A and Pillar B are **consumers** of already-stamped `resolved` records — they must not each maintain a private bind table.

**Why it matters.** Duplicate LUTs drift; sketch `entity_id` and graph `ci_id` stop meaning the same string (breaks WorkingSet join).

**Options.**

1. **Single E2 LUT service** (or Motadata equivalent) — writers only see stamped streams.  
2. Each pillar maintains aliases — rejected by current contract.  
3. Topology (E3) owns nodes; E2 owns bind rows; both share `ci_id` space with clear write APIs.

**Proposed leaning.** **(1)+(3):** one bind LUT owned by Identity (E2); Topology publishes / consumes the same `ci_id` space; inventory and catalog **writers** update LUT rows with evidence strength; telemetry may propose candidates but does not alone flip `resolved` (see Q3). Pillar A/B never import each other’s packages for bind.

**Ask the room.** Name the Motadata component that is the system of record for “monitor id / label → CI” today (bind builder, CMDB sync, other).

---

### Q5 — Aggregation-bug runbook (Case 1)

**Context.** Case 1 is the worst live failure mode: every Detect verdict is wrong until fixed. Fix shape is simple (patch + rebuild) but needs **raw or an alternate rebuild source**.

**Why it matters.** Without a rehearsed path, an aggregation bug becomes an incident with no clean recovery.

**Options.**

1. Formal runbook: detect bad `sketch_algo_version` / window bug → stop bad writer → rebuild windows from retained raw or from prior good sketches where possible → invalidate bad Vortex/hot rows.  
2. Rely on ad-hoc engineer heroics.  
3. Keep a longer raw tier **only** to support Case 1 (costly).

**Proposed leaning.** **(1) now** as process, independent of full Rehydration. Rebuild sources in order of preference: (a) still-open quarantine / short raw buffer, (b) cold full-fidelity if Motadata later keeps it (Q6), (c) accept irrecoverable windows and mark Detect coverage gaps. Track `sketch_algo_version` on every row so Detect can refuse mixed bad versions.

**Ask the room.** Is Case 1 recovery a **P0 operational requirement** for Motadata Observability 3.0, or an accepted rare loss?

---

### Q6 — Scope of raw retention (quarantine only vs Edge Delta–style archive)

**Context.** Edge Delta archives full-fidelity events and rehydrates on demand (forensic, investigation, backfill). Our Case 2 loop only needs a **narrow** buffer.

**Why it matters.** Full archive = real infrastructure, cost, and retention policy. Quarantine-only = smaller build, leaves Cases 4–6 and most of Case 1/3 backfill weak.

**Options.**

1. **Quarantine only** (hours–days, discard on resolve or expiry) — solves Case 2 structural loop.  
2. **Quarantine + optional short hot raw** (for example minutes–hours) for exemplar / debug — still not compliance.  
3. **Full cold raw archive + rehydration job** (Edge Delta–like) — covers Cases 1, 3–6 when product wants them.  
4. **Sketch-only, no quarantine** — accept permanent Case 2 holes.

**Proposed leaning for this PoC / near-term Motadata lean.** **(1)** as the design we document and can stub in lab; **(2)** optional later; **(3)** as an **explicit Motadata product decision** (compliance / sales), not required to prove Pillar A/B writers. PoC continues to use file / memory dest for sketches and map; quarantine can be a **lab folder or in-memory TTL map**, not real S3 Rehydration.

**Ask the room.** Which Q33/Q35 rows in [`GRAPH_QNA.md`](../../docs/GRAPH_QNA.md) must stay in scope for GA vs explicitly “out of Observability 3.0 Detect path”?

---

### Q7 — Bucket schema discipline on quarantine replay

**Context.** Digest merge on replay is clean. Bucket merge fails if `bucket_schema_version` changed between original window and replay (same failure mode as merging two incompatible bucket schemas generally).

**Why it matters.** Silent wrong histograms poison shape-style views even when p95 from the digest is fine.

**Options.**

1. **Hard rule:** never change `bucket_schema_version` under the same logical sketch key; new schema ⇒ new key / migration job.  
2. On version mismatch at replay: merge **digest only**; drop or recompute buckets; mark buckets incomplete.  
3. Keep raw long enough to always rebuild buckets after schema change.

**Proposed leaning.** **(1) as policy** + **(2) as runtime safety**. Replay must compare versions; mismatch ⇒ digest merge allowed, buckets not merged, row flagged. Do not require (3) unless Q6 chooses a real raw archive.

**Ask the room.** Confirm bucket bounds for wave-1 metrics are frozen enough that (1) is realistic.

---

### Q8 — Where quarantine lives relative to NATS / E2 / writers

**Context.** Motadata PDF places a streaming bus (NATS) before percentile and graph engines. ObserveOps: both pillars read **after** Identity. Quarantine is about **unresolved** samples — so it sits **at or just after E2**, not inside Pillar A or B packages.

**Why it matters.** If each pillar invents its own quarantine, replay and merge diverge.

**Options.**

1. Quarantine owned by **Identity / admission** — single buffer; on resolve, republish resolved `ingest.v1` onto the post-E2 stream (NATS or lab equivalent) so A and B both see normal resolved traffic.  
2. Quarantine owned by Pillar A only (sketch coverage) — topology still gaps.  
3. Quarantine inside cold S3 with rehydration workers (Edge Delta–scale).

**Proposed leaning.** **(1).** Identity (or Motadata bind service) owns the buffer; resolution republishes **resolved** records once; Pillar A and Pillar B stay dumb `ResolvedOnlyGate` consumers. Lab PoC may stub this as a TTL dict + replay hook without NATS.

**Ask the room.** Agree that Pillar A/B packages stay free of LUT/quarantine ownership (keeps independence for the A/B PoC).

---

### Q9 — PoC scope vs Motadata production (what we implement now)

**Context.** Current Pillar A/B PoC uses `ResolvedOnlyGate` + file/memory dest. No real LUT service, no quarantine TTL, no Vortex/S3.

**Why it matters.** Team should not confuse “contract leaning” with “already coded.”

| Topic | Contract leaning (this doc) | PoC today | Proposed PoC next (optional) |
|-------|-----------------------------|-----------|------------------------------|
| LUT | E2-owned bind table | Fixtures already `resolved` | Tiny in-memory LUT + miss → synthesized |
| Quarantine | Bounded TTL + replay | Not implemented | Lab TTL map + merge test for Case 2 |
| Raw archive | Product decision (Q6) | Not implemented | Out of PoC unless room votes (3) |
| Pillar writers | Resolved only | Implemented | Unchanged |
| Dest | files / later Vortex+S3 | `FileDest` / `MemoryDest` | Optional lab dual-temperature dest later |

**Proposed leaning.** Keep A/B writer PoCs **independent** and green. Add a **small shared identity/quarantine lab stub** only if the room wants Case 2 demonstrated — not as a blocker for GraphWriter / sketch flush work.

**Ask the room.** Vote: demonstrate Case 2 in lab this quarter, or document-only until Motadata bind ownership is named?

---

## 4.5 Anticipated counter-question — “How do exemplars work if we keep no raw?”

**The pushback.** If Pillar A discards raw metric samples after building the sketch, how can an operator still open “one real request” from a hot latency bin?

**Short answer.** An **exemplar is not a raw lake**. It is a **tiny pointer kept on the sketch at write time** — typically one `trace_id` (or request id) attached to a histogram bucket — chosen while the writer still sees each sample. After that, the sample values themselves can be discarded. Detect still does not need exemplars; they only speed **investigation after** a fire.

### What “no raw” does and does not mean

| Phrase | Means | Does **not** mean |
|--------|--------|-------------------|
| Discard raw **metric samples** | Do not keep every latency number for that window forever | Never looked at the sample stream |
| Keep an **exemplar** | Store ~one id per hot bin (or per policy) **inside / beside** `sketch.v1` | Keep every request in that bin |
| Optional in v1 | Room may ship Detect on digest + baseline first | Exemplars are impossible without S3 raw archive |

Flow:

```text
Resolved samples stream (this window)
        │
        ├─► update T-Digest
        ├─► increment bucket counts
        └─► optionally remember (bin → trace_id) for 1+ samples in that bin
                │
                ▼
        flush sketch.v1  →  discard the rest of the raw sample list
                │
                ▼
        later: Detect fires on digest vs baseline
                │
                ▼
        UI: hot bin → click exemplar trace_id → open that span in the trace product
```

So exemplars are facilitated by **sampling pointers while compressing**, not by **re-reading a metric raw archive**.

### What you still cannot do (honest limit = Case 6)

| Need | With exemplars only | Needs more than exemplars |
|------|---------------------|---------------------------|
| Fire Detect (p95 vs season) | Not required | Digest + baseline |
| “Which bin is hot?” | Buckets | — |
| “Open **one** slow request” | Exemplar `trace_id` | — |
| “List **all** requests in that bin” / forensic exact values | **No** | Full events / raw / rehydration (PDF Case 6 / 4) |

That limit is intentional: Observability 3.0 trades “every request forever” for bounded storage. Case 6 in the PDF is exactly “beyond one exemplar.”

### Traces vs metric raw (do not collapse these)

- **Metric raw** = the latency (or CPU) sample list used to build the sketch. Aggressive discard is the Pillar A lean.  
- **Trace / span store** = separate product retention. The exemplar only needs a **stable id** that still resolves in that store when the operator clicks.  
If Motadata keeps APM traces for N days but discards metric samples after sketch flush, exemplars still work for those N days. If tracing is off or the span aged out, the pointer is a dead link — Detect and topology still work; drill-down does not.

### Ready reply in the room

> We are not saying “never see raw.” The sketch writer sees each resolved sample **once**, updates digest and buckets, and may **keep a trace id on the hot bin**. Then we drop the sample list. That gives click-through to one request without a metric raw lake. Want every request in the bin, or legal exact replay — that is a different retention product (Q6), not a reason to keep all metric raw for Detect.

Canonical detail: [`GRAPH_QNA.md`](../../docs/GRAPH_QNA.md) **G22**, **G28**, **G29** · visual: [`sketch-exemplars-visual.html`](../../docs/fabric/sketch-exemplars-visual.html).

---

## 5. One-page vote card (copy into the meeting notes)

| ID | Question | Proposed leaning | Vote (Y / amend / N) |
|----|----------|------------------|----------------------|
| Q1 | Quarantine TTL | 24h default; measure resolve-before-expiry | |
| Q2 | Catalog sync | Fast declared sync; quarantine sized for novel CIs | |
| Q3 | LUT miss | Synthesize + quarantine; resolve only on authoritative/declared; Auto-create not default ticketable | |
| Q4 | LUT owner | Single E2 / Motadata bind service; A/B consumers only | |
| Q5 | Case 1 | Formal backfill runbook; version stamps on sketches | |
| Q6 | Raw scope | Quarantine-first; full rehydration = separate product call | |
| Q7 | Buckets on replay | Schema immutable per key; mismatch ⇒ digest-only merge | |
| Q8 | Buffer placement | At Identity; republish resolved once to A∥B | |
| Q9 | PoC | Writers stay resolved-only; Case 2 stub optional | |

---

## 6. What is already locked (do not re-litigate here)

These are settled elsewhere; this discussion assumes them:

- Pillar A and Pillar B are **parallel writers after Identity** — not merged products.  
- Same `tenant` + `ci_id` ≡ sketch `entity_id`.  
- Writers admit **resolved** rows only for production map/history.  
- D-E2-1: non-resolved is not localize / ServiceOps ticket target.  
- Sketches do not carry edges; map does not replace sketches.  
- Shift-left (volume) and sketch retention (lifespan) are **separate** levers.

Canonical graph/sketch field locks: [`../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md).  
Prior discussion trail: `01`–`03` in this folder.

---

## 7. Suggested reading order for attendees (15 minutes)

1. This document §§1–3, §4.5 (exemplars counter-Q), and the vote card (§5).  
2. PDF §§5–8 ([`Raw_Data_Handling.pdf`](../Raw_Data_Handling.pdf)) for the race diagram and Edge Delta check.  
3. [`LLD-E2-Identity.md`](../../docs/observeops/LLD-E2-Identity.md) §4 (D-E2-1).  
4. [`GRAPH_QNA.md`](../../docs/GRAPH_QNA.md) G22 / G28 / G29 (exemplars) and G35–G37 (raw / shift-left).

---

## 8. After the meeting

Update this file’s status to **Voted** and record decisions under each Q (one short paragraph each). If Q6 chooses full raw archive, open a follow-on note for retention tiers and rehydration job shape — do not overload Pillar A/B implementation plans with that until voted.
