# Motadata 3 pillars mapped onto ObserveOps E1–E11

**Status:** Working map (2026-08-18) — not a claim Motadata already built our pipeline  
**Source:** [`KR Plan/Motadata_Observability_3_Pillars_Architecture.pdf`](../../KR%20Plan/Motadata_Observability_3_Pillars_Architecture.pdf) (4 pages)  
**Target:** same HLD clock, shift-left locus — [explained HTML](./motadata-3pillars-architecture.html) · [job map](./motadata-3pillars-vs-shift-left.html) · [`:8765`](http://127.0.0.1:8765/motadata-3pillars-architecture.html)  
**Explained (diagrams + what/why/how):** [HTML](./motadata-3pillars-architecture.html) · [`:8765`](http://127.0.0.1:8765/motadata-3pillars-architecture.html) · [A4 PDF](../print/motadata-3pillars-architecture-explained-A4.pdf) (also [`KR Plan/Motadata_Observability_3_Pillars_Architecture_Explained.pdf`](../../KR%20Plan/Motadata_Observability_3_Pillars_Architecture_Explained.pdf))
**Job-map print:** [A4 PDF](../print/motadata-3pillars-vs-shift-left-A4.pdf) · [print HTML](../print/motadata-3pillars-vs-shift-left-A4.html)  
**Contracts:** [`OBSERVEOPS_PIPELINE_HLD.md`](../OBSERVEOPS_PIPELINE_HLD.md) · locus [`observeops-shift-left-architecture.html`](../observeops-shift-left-architecture.html)  
**Study Q&A (2026-08-19):** [HTML](./motadata-3pillars-study-qna.html) · [`MOTADATA_3PILLARS_STUDY_QNA.md`](./MOTADATA_3PILLARS_STUDY_QNA.md) — pillars vs doors, sketches, CI vs event nodes, service map / Smartscape / E3 / Motadata, graph time ≠ Detect time.

This is a **job map**. Pillars are store / RCA-algorithm choices. Shift-left is *where* E1–E6 execute. Same clock; different hop.

**A / B / C are not one series.** Three lettered systems sit on this page. They do not line up 1:1.

| Letter | Kind | What it is | Not |
|--------|------|------------|-----|
| **Pillar A / B / C** | Motadata PDF products | A = percentile sketches · B = knowledge graph · C = Rust ReAct agent | Not Detect doors. Not phases. Not Gates. |
| **Door A / B / C** | E6 Detect entry points | A = Node trigger · B = Gateway trigger · C = platform monitor | Not pillars. Door C *reads* Pillar A; it is not Pillar C. |
| **Gate A / B / C / D** | Shift-left decision checkpoints | A = Node vs Gateway · B = dest profile · C = which Detect classes are platform-only · D = Layer I on/off | Not pillars. Not doors. Gate D ≠ HLD **D5**. |
| **P1 / P2 / P3** | HLD phases | P1 fabric E1–E5 · P2 case-open E6–E8 · P3 diagnose/close E9–E11 | Never written as A/B/C. |
| **Clock A / Clock B** | Always-on vs on-incident | Clock A ≈ P1 · Clock B ≈ P3 | Clock B is not Pillar B. |

Bare “A”, “B”, or “C” on this page always means **pillar** unless the word **door** or **Gate** is in front.

---

## 0. One-line assignment

**Pillar A and Pillar B belong to P1 (always-on fabric). Pillar C belongs to P3 (diagnose/close). P2 has no Motadata pillar** — it only *reads* Pillars A and B.

| | |
|--|--|
| **Pillar A + B** | P1 stores (write path) |
| **Pillar C** | P3 diagnose (optional Layer I) |
| **P2** | Reads Pillars A+B; not a third pillar |
| **Build Pillar C** | After E7–E8; Gate D / D5 optional |

The PDF is **centralize-then-analyze**: Telemetry → NATS → percentile + graph builders → Vortex/S3 → bounded retrieval → Rust ReAct agent → Explain / ITSM / Remediate. That fills the **SaaS column** of the shift-left diagram. It does **not** specify the left column (OTel Node E1–E2, mask/Drain, Detect **door A**, optional Gateway **door B**).

---

## 0.1 Five Motadata machines (what / why / how → our steps)

These are the boxes on the PDF’s executive stack. Full diagrams: [explained HTML](./motadata-3pillars-architecture.html).

| Machine | What | Why | How | Writes | Reads | Not |
|---------|------|-----|-----|--------|-------|-----|
| **T-Digest + buckets + seasonal baselines** | Compact “is this weird for this hour of this weekday?” — mergeable percentiles, cheap histogram, calendar-aware expected range | Cannot scan weeks of samples per alert; Monday 9am ≠ outage | Window samples; fold into T-Digest *and* fixed bins; key baseline by hour-of-day × weekday | **E4** sketches · **E5** season refresh | **E6 door C** · **E10** `get_metric_baseline()` | E1/E2 (needs identity) · E9 leaf rule |
| **Graph builder — entities + edges + changes** | Typed RCA map: who exists, how they connect, what changed (`valid_from`/`to`, confidence) | Alert without a map is not RCA | Upsert typed **CI** nodes/edges; Motadata PDF may draw Change/Alert on the map — **our lock:** Change = `change_fact.v1` (not a CI vertex); Alert = E6 Signal (not a map node); walk service → deps → change facts → abnormal metrics → candidates | **E3** `GraphSnapshot` · **E5** versions/writeback | **E8** hop/time · **E9** walk · **E10** `query_graph()` | E6 Detect (fires Signals — not “Alert as GraphSnapshot node”) · E11 executor |
| **Vortex + S3** | Durable lake: historical observability (sketches) + knowledge graph (map). Same `entity_id` | Builders are useless if results evaporate; no expensive historical UPDATE | A and B write in parallel; S3 cold, Vortex analytical; agent never dumps the lake | **E4** dest (one profile, Gate B open) · E3 tables live here | everything downstream via retrieval | Node/Gateway (buffers, not the lake) · not the only dest |
| **RCA retrieval layer** | Bounded fetch of baseline + graph + events + changes = our `WorkingSet` | Unscoped walks hallucinate and explode cost | From curated seed: k hops, time window, evidence budget | **is E8 Scope** | needs **E7** one `CaseSeed` first; feeds E9/E10 | not a pillar (P2 has none) |
| **Rust RCA agent (bounded ReAct)** | Reason → typed tool → reason again. LLM proposes; policy authorizes | Not “LLM + observability”; evidence and policy constrain | Observe, retrieve A+B, correlate, hypothesize, validate, decide. Timeouts, audit, dry-run, cancel | plays **E9–E11** (Layer I, opt-in) | tools only inside WorkingSet | P1 · **E7 Curate** · remediation · **do not flip D5** |

**Operator path always on:** A+B → E7 → E8 → deterministic E9–E11 must work with the agent off.

---

## 1. Which phase owns each pillar

A pillar is not a phase. **Pillar A** and **Pillar B** are always-on P1 stores. P2/P3 only read them. **Pillar C** runs in P3 (Clock B — diagnose/close) as optional Layer I. It is not Detect **door C**.

| Pillar | Owns (write path) | Read by | Does not own |
|--------|-------------------|---------|--------------|
| **A · Percentiles** | P1 **E4** sketch store · P1 **E5** seasonal refresh | P2 **E6 door C** (thresholds) · P3 **E10** `get_metric_baseline()` | E1/E2 (needs identity first) · E9 leaf rule |
| **B · Knowledge graph** | P1 **E3** `GraphSnapshot` · P1 **E5** versions / change facts / writeback | P2 **E8** hop/time budget · P3 **E9** walk · P3 **E10** `query_graph()` | E6 Detect (Alert is a Signal, not a `GraphSnapshot` vertex) · E11 executor |
| **C · Rust ReAct agent** | P3 **E9** Localize · P3 **E10** Identify · P3 **E11** Package (explain/ticket) | Tools read A+B via **E8**-bounded retrieval | P1 fabric · P2 **E7** Curate (keep as a stage) · remediation |

**P2 has no Motadata pillar.** Case-open (E6–E8) is not Pillar A, B, or C. Detect **door C** (platform thresholds) is a *consumer* of **Pillar A** (sketches). Scope knobs are the PDF’s “RCA retrieval layer.” Curate stays a required stage (**D3**) in front of **Pillar C** — do not implement it only as `deduplicate_incident()`.

### Pillar jobs in one paragraph each

- **A Percentiles** — T-Digest + buckets + seasonal baseline on Vortex/S3. Consumers: dashboards, alerts, agent. Thresholds are platform Detect (door C). Seasonal update is E5 freshness. Windowing sits after the bus — not Node E2.
- **B Knowledge graph** — Typed entities and edges on Vortex/S3 match “SaaS owns `GraphSnapshot`; Gateway only assists.” Also mixes Change (E5), Alert (E6), Incident / ITSMTicket (E7/E11) into the same store. Traversal recipe is E9’s walk.
- **C Rust ReAct agent** — Observe → retrieve baseline/graph → correlate → hypothesize → validate → act. That is Localize + Identify + Package with tools. `deduplicate_incident` leaks into E7. `execute_remediation` is outside E1–E11. LLM proposes; policy authorizes — Layer I shape; D5 stays Review.

---

## 2. Recommended implementation order

Do **not** ship A → B → C as three products. A and B are **parallel P1 writers** after E2 keys exist. C is last and opt-in (Gate D / D5 Review). Aligns with shift-left Gates A–D and LLD-E1/E2 already Done.

| Seq | Build | HLD stages | Exit |
|-----|--------|------------|------|
| **0** | Edge admit + identity (PDF is silent — we still need this) | E1 Collect · E2 Identity (Node) | `ingest.v1` with `tenant`+`ci_id`. LLD-E1/E2 Done. No pillar yet. |
| **1** | Ingest path into SaaS (NATS optional) | E1 SaaS ingest · E4 write path | Shaped stream lands. Gate B: Vortex/S3 may be **one** dest, not the only dest. |
| **2** | Pillar A **∥** Pillar B | A: E4 sketches + E5 season · B: E3 graph + E5 change feed | Query p95 by `entity_id` without raw scan. `GraphSnapshot` walkable. Same `entity_id` namespace. |
| **3** | Platform Detect on sketches | E6 door C | Gate C: which classes are platform-only. Doors A/B still separate (Node/Gateway). |
| **4** | Case open without an LLM | E7 Curate · E8 Scope (retrieval layer) | One `CaseSeed` (D3). `WorkingSet` with time/entity/hop/evidence budget. |
| **5** | Deterministic diagnose + close | E9 Localize · E10 Identify · E11 `VerdictCard` | Operator path works using A+B only. D4 Package required. No agent yet. |
| **6** | Pillar C as Layer I (opt-in) | Same E9–E11, tools only inside the `WorkingSet` | Gate D: default off. LLM proposes; policy authorizes. Never owns E7 or E1. |
| **7** | Remediation (later, not this clock) | Outside E1–E11 | Reuse policy/audit/idempotency. Do not call it Package. |

So: **identity → stores (A+B) → detect/curate/scope → deterministic RCA → optional agent.**

---

## 3. E1–E11 vs the PDF

Fit: **Covered** = same job exists. **Partial** = analogous block, different locus or missing contract.

| Stage | PDF implementation | Our shift-left locus | Fit |
|-------|--------------------|----------------------|-----|
| E1 Collect | Telemetry in (logs/metrics/APM/eBPF/events/**ITSM**) → NATS | OTel Node receivers + SaaS cloud ingest; telemetry-only this pass | Partial · bus after sources; ITSM-as-Collect conflicts |
| E2 Identity | `entity_id` on sketches and graph nodes; no bind overlay named | Node: k8sattributes / mask / Drain; SaaS bind-miss queue only | Partial · identity implied, not an edge Normalize stage |
| E3 Topology | Pillar B: typed entities/edges, `valid_from`/`to`, confidence, source | SaaS canonical `GraphSnapshot`; Gateway assist optional | **Covered** · SaaS graph matches; no Gateway assist described |
| E4 Stores | Vortex + S3: historical observability + percentile sketches | Ingest API + tenant dest fan-out (dest is Q1 store) | Partial · first-party lake vs dest-agnostic (Gate B open) |
| E5 Maintain | Seasonal keys; graph versions; outcomes written back | SaaS OpAMP fleet + retention; agents execute | Partial · freshness yes; fleet/config channel absent |
| E6 Detect | thresholds / anomaly bounds on sketches; Alert entity | Door A Node · Door B Gateway · Door C platform | Partial · door C only; no edge triggers |
| E7 Curate | `CORRELATED_WITH`; `deduplicate_incident()` tool on the agent | SaaS required one `CaseSeed` (D3 Signed) before diagnose | Partial · merge is a tool, not a required pre-agent stage |
| E8 Scope | Retrieval bounded by time, entity, hop count, evidence budget | SaaS Tailor: `WorkingSet` from seed + graph + dest corridor | Partial · same knobs, folded into agent retrieve not a `WorkingSet` object |
| E9 Localize | Incident → service → deps → changes → abnormal metrics → candidates | SaaS/operator leaf rule (ERROR deepest-error, SLOWDOWN self-time) | **Covered** · graph walk is the leaf search; agent is the actor |
| E10 Identify | Retrieve baseline + traces/log patterns; validate hypothesis; evidence not LLM assertion | Multimodal dest query; Verify decided here | **Covered** · baseline + graph constrain the claim |
| E11 Package | Explain / `create_ticket` / ITSM; also Remediate | `VerdictCard` required (D4); narrator optional (D5); dest UI is not Package | Partial · ticket ≈ Package; remediation is out of HLD scope |

---

## 4. Operating loop vs our phases

| PDF loop step | HLD phase / stage | Shift-left hop |
|---------------|-------------------|----------------|
| Telemetry | P1 E1 (admission) | Unspecified collectors — not OTel Node |
| NATS streaming | ingest bus (between E1 and E4) | SaaS / Motadata fabric — not Gateway |
| Percentile engine | E4 sketches + E6 door C + E5 season | SaaS after the bus |
| Graph builder | E3 + change facts (E5) | SaaS Vortex/S3 |
| RCA retrieval layer | E8 Scope knobs | SaaS index in front of Vortex |
| Rust RCA agent | E9 → E10 (and some E7) | SaaS; our Layer I is optional |
| Explain / ITSM | E11 Package | SaaS |
| Remediate | outside E1–E11 | not on the shift-left page |
| Outcome → graph context | E5 writeback + E3 version | SaaS closed loop |

---

## 5. Conflicts with locked (or Review) HLD defaults

Working ToDo (leadership ask vs resolution): [study Q&A §10](./motadata-3pillars-study-qna.html#todo) · [`MOTADATA_3PILLARS_STUDY_QNA.md`](./MOTADATA_3PILLARS_STUDY_QNA.md#10-todo--leadership-pdf-vs-our-pipeline).

| Topic | PDF | Our HLD / shift-left | Handle |
|-------|-----|----------------------|--------|
| Where processing runs | Central bus then Vortex | Shape + mask + optional door A before TLS | Keep shift-left; treat PDF as SaaS half |
| Store | Vortex + S3 is the lake | Q1 dest-agnostic fan-out (Gate B open) | Vortex can be one dest profile, not the only E4 |
| Detect doors | Alerting on sketches (platform) | Both doors; Node-first default is Open (Gate C) | PDF implements door C. Doors A/B still ours to build |
| AI / D5 | Agent is the RCA engine | D5 Review; operator path always on; Layer I optional | **Do not flip D5** because the PDF is agentic |
| Curate D3 | Dedupe as an agent tool | Required one seed before diagnose | Keep E7 in front of the agent, not inside it |
| E1 sources | ITSM listed with telemetry | Telemetry-only Collect; ticket is reserved `signal_class` | ITSM stays E11 egress / future join, not E1 |
| Remediation | `execute_remediation()` with policy | HLD scope-out: no remediation execution | Policy pattern is reusable; executor is not E11 |

---

## 6. What to take vs what not to copy

**Take:** mergeable percentile sketches as an E4 modality; typed RCA graph with `valid_from`/`to` (graph time, E3/E5 — not E6) and confidence as E3; bounded retrieval as E8; hypothesis-plus-evidence language for E10; LLM never owns authorization if Layer I ships.

**Do not copy:** skipping Node E1–E2; treating NATS+Vortex as the whole product; folding Curate into the agent; making ReAct the default Package path; calling ITSM or remediation Collect; Alert/Incident as E3 vertices.

**Hybrid (design 3 + 4):** one `GraphSnapshot` = our CI plane + Motadata temporal CI edges + Change-as-fact. Four-column compare and merge rules: [study Q&A](./motadata-3pillars-study-qna.html) §7 · [`MOTADATA_3PILLARS_STUDY_QNA.md`](./MOTADATA_3PILLARS_STUDY_QNA.md).

Formal contracts stay on [`OBSERVEOPS_PIPELINE_HLD.md`](../OBSERVEOPS_PIPELINE_HLD.md). This PDF is a Motadata implementation sketch of the **SaaS column**, not a rewrite of the clock.
