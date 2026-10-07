# Motadata 3 pillars mapped onto ObserveOps E1–E11

**Status:** Working map (2026-08-18) — not a claim Motadata already built our pipeline  
**Source:** [`KR Plan/Motadata_Observability_3_Pillars_Architecture.pdf`](../KR%20Plan/Motadata_Observability_3_Pillars_Architecture.pdf) (4 pages)  
**Target:** same HLD clock, shift-left locus — [HTML](./motadata-3pillars-vs-shift-left.html) · [`:8765`](http://127.0.0.1:8765/motadata-3pillars-vs-shift-left.html)  
**Print:** [A4 PDF](../exports/motadata-3pillars-vs-shift-left-A4.pdf) (4 pages · paper layout) · [print HTML](./print/motadata-3pillars-vs-shift-left-A4.html)  
**Contracts:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) · locus [`observeops-shift-left-architecture.html`](./observeops-shift-left-architecture.html)  
**D5:** stays Review. Operator path always on.

This is a **job map**. Pillars are store / RCA-algorithm choices. Shift-left is *where* E1–E6 execute. Same clock; different hop.

---

## 0. One-line assignment

**A and B belong to P1 (always-on fabric). C belongs to P3 (diagnose/close). P2 has no Motadata pillar** — it only *reads* A and B.

| | |
|--|--|
| **A + B** | P1 stores (write path) |
| **C** | P3 diagnose (optional Layer I) |
| **P2** | Reads A+B; not a third pillar |
| **Build C** | After E7–E8; Gate D / D5 optional |

The PDF is **centralize-then-analyze**: Telemetry → NATS → percentile + graph builders → Vortex/S3 → bounded retrieval → Rust ReAct agent → Explain / ITSM / Remediate. That fills the **SaaS column** of the shift-left diagram. It does **not** specify the left column (OTel Node E1–E2, mask/Drain, door A, optional Gateway door B).

---

## 1. Which phase owns each pillar

A pillar is not a phase. A and B are always-on P1 stores. P2/P3 only read them. C is Clock B (diagnose/close), optional Layer I.

| Pillar | Owns (write path) | Read by | Does not own |
|--------|-------------------|---------|--------------|
| **A · Percentiles** | P1 **E4** sketch store · P1 **E5** seasonal refresh | P2 **E6 door C** (thresholds) · P3 **E10** `get_metric_baseline()` | E1/E2 (needs identity first) · E9 leaf rule |
| **B · Knowledge graph** | P1 **E3** `GraphSnapshot` · P1 **E5** versions / changes / writeback | P2 **E8** hop/time budget · P3 **E9** walk · P3 **E10** `query_graph()` | E6 Detect (Alert is a node, not the detector) · E11 executor |
| **C · Rust ReAct agent** | P3 **E9** Localize · P3 **E10** Identify · P3 **E11** Package (explain/ticket) | Tools read A+B via **E8**-bounded retrieval | P1 fabric · P2 **E7** Curate (keep as a stage) · remediation |

**P2 has no Motadata pillar.** Case-open (E6–E8) is not A, B, or C. Door C is a consumer of A. Scope knobs are the PDF’s “RCA retrieval layer.” Curate stays a required stage (**D3**) in front of C — do not implement it only as `deduplicate_incident()`.

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

**Take:** mergeable percentile sketches as an E4 modality; typed RCA graph with `valid_from`/`to` and confidence as E3; bounded retrieval as E8; hypothesis-plus-evidence language for E10; LLM never owns authorization if Layer I ships.

**Do not copy:** skipping Node E1–E2; treating NATS+Vortex as the whole product; folding Curate into the agent; making ReAct the default Package path; calling ITSM or remediation Collect.

Formal contracts stay on [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md). This PDF is a Motadata implementation sketch of the **SaaS column**, not a rewrite of the clock.
