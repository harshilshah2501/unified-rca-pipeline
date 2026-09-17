# Motadata 3 pillars — study Q&A

**Date:** 2026-08-19  
**Status:** Study notes from the mapping discussion. Not an HLD rewrite. **D5 stays Review.**  
**Objective:** ObserveOps E1–E11 is our pipeline (vendor research). The Motadata 4-page PDF is a **leadership requirements** sketch. Map their boxes onto our stages; name conflicts; record resolutions. See [§10 ToDo](#10-todo--leadership-pdf-vs-our-pipeline).  
**Hub page (formatted):** [`motadata-3pillars-study-qna.html`](./motadata-3pillars-study-qna.html) · [`:8765`](http://127.0.0.1:8765/motadata-3pillars-study-qna.html)

**Read with:** [implementation scope](../../pillar-ab-implementation/scope/MOTADATA_3PILLARS_IMPLEMENTATION_SCOPE.md) · [slice README](../../pillar-ab-implementation/README.md) · [`MOTADATA_3PILLARS_VS_SHIFT_LEFT.md`](./MOTADATA_3PILLARS_VS_SHIFT_LEFT.md) · [explained HTML](./motadata-3pillars-architecture.html) · [job map](./motadata-3pillars-vs-shift-left.html) · [shift-left](../observeops-shift-left-architecture.html) · operational graph [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](../OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md)

Issue ≠ Problem ≠ Bits ≠ Incident. Thread ≠ Issue.

---

## 1. Letters: pillar vs door vs Gate vs phase

**Q. Are A, B, and C doors, phases, or pillars?**

Three lettered systems. They do not line up 1:1. Bare A/B/C on the mapping page means **pillar** unless the word **door** or **Gate** is in front.

| Letter | Kind | What it is | Not |
|--------|------|------------|-----|
| **Pillar A / B / C** | Motadata PDF products | A = percentile sketches · B = knowledge graph · C = Rust ReAct agent | Not Detect doors. Not phases. Not Gates. |
| **Door A / B / C** | E6 Detect entry points | A = Node trigger · B = Gateway trigger · C = platform monitor | Not pillars. **Door C reads Pillar A; it is not Pillar C.** |
| **Gate A / B / C / D** | Shift-left checkpoints | A = Node vs Gateway · B = dest profile · C = which Detect classes are platform-only · D = Layer I on/off | Gate D ≠ HLD **D5** |
| **P1 / P2 / P3** | HLD phases | P1 E1–E5 · P2 E6–E8 · P3 E9–E11 | Never written as A/B/C |
| **Clock A / Clock B** | Always-on vs on-incident | Clock A ≈ P1 · Clock B ≈ P3 | Clock B is not Pillar B |

“C is Clock B” was a bad sentence. It meant **Pillar C runs in P3**, not that C is a phase or a door.

**Q. Where do the pillars sit?**

Pillar A and Pillar B are always-on **P1 stores** (write). P2/P3 only read them. Pillar C is optional **P3 / Layer I**. **P2 has no Motadata pillar.**

---

## 2. What the three pillars are

**Q. What are the three pillars in the Motadata PDF?**

Products, not phases:

- **A — Percentiles:** compact “is this weird?” store  
- **B — Knowledge graph:** typed “who is connected / what changed?” map  
- **C — Rust ReAct agent:** bounded diagnose/close (our Layer I, opt-in)

The PDF is **centralize-then-analyze** (SaaS column). It does not specify Node E1–E2, mask/Drain, Detect door A, or Gateway door B.

---

## 3. Pillar A pipeline (sketches)

**Q. What does `Telemetry → windowing → seasonal baseline → T-Digest + bucket sketch → Vortex/S3 → O(1) query index` mean?**

Only **Pillar A’s write path**. Goal: p95 / “normal for this slot” **without replaying weeks of raw samples**.

| Term | Meaning |
|------|---------|
| **Windowing** | Chop the stream into slices (PDF: **1m / 5m / 1h / 1d**). One sketch row per `metric_id` + `entity_id` + `window` + `season_key`. **Not** Node Identity (E2). After the bus, on the SaaS engine. |
| **Seasonal baseline** | Usual range for **this hour of this weekday** (`season_key`). Stops business cycles looking like outages. Refresh is **E5**, not Detect. |
| **T-Digest** | Mergeable distribution summary → **p50 / p95 / p99**. Combine windows without keeping every sample. |
| **Bucket sketch** | Fixed histogram bins. Deterministic, cheap for histogram queries and alert rules. PDF keeps **both** T-Digest and buckets. |
| **Vortex/S3** | Durable lake for those rows. For us: **one dest profile**, not the only E4 (Gate B open). |
| **O(1)** | Cost does **not** grow with historical **sample count**. Still a bounded key lookup + deserialize a sketch. |

Consumers: dashboards, **E6 door C**, **E10** `get_metric_baseline()`. Pillar A does not name the leaf (E9).

---

## 4. “Entities” that are not CIs

**Q. Motadata lists Container, Pod, Database, Deployment, Network, Change, Alert, Incident, … as entities. Many have no persistent unique id. Wrong?**

The **CI bar** is right: localize and ticket need a **stable id** (or a scoped id + validity window) on `tenant`+`ci_id`. Motadata used “entity” for **any typed graph vertex**, including events.

| Kind | Examples | Verdict |
|------|----------|---------|
| Durable CIs | Service, Host, Customer, BusinessService; Database **if** instance/cluster is named | Pass the CI test |
| Ephemeral runtime | Pod (k8s UID while alive), Container (this run), Process (pid is not identity) | Graph nodes **for a while**, not ServiceOps roots |
| Underspecified | Database, Deployment, Network | Pause until you pick the id (instance vs cluster; k8s Deployment vs release vs runbook; NIC/subnet/LB vs “Network”) |
| Events reified as nodes | Change, Alert, Incident, ITSMTicket, Metric, LogPattern, Trace | **Not CIs.** Fact/evidence/case objects |

Our HLD is stricter: E9/E11 only `identity.status = resolved`. D-E2-1: synthesized/unresolved ≠ ticket. Change/ticket are reserved `signal_class`, not Collect this pass.

---

## 5. Motadata edges — job buckets (not one topology)

**Q. How do we segregate `CALLS · DEPENDS_ON · RUNS_ON · CONTAINS · CONNECTS_TO · PRODUCES · CONSUMES · AFFECTS · CHANGED_BY · DEPLOYED_AS · TRIGGERED · CORRELATED_WITH · RESOLVED_BY`?**

Four jobs. Only **1–2** belong on **E3 `GraphSnapshot`**.

**1. Structure (CI–CI, often authoritative)**  
`CONTAINS`, `RUNS_ON`, `DEPLOYED_AS` (only if you pick **one** meaning: k8s resource **or** release). Our analogues: `part_of` / `runs_on` / `hosted_on`.

**2. Runtime / contract (CI–CI, service-map core)**  
`CALLS`, `DEPENDS_ON`, `CONNECTS_TO`, `PRODUCES` / `CONSUMES`. `CALLS` is the service map; `DEPENDS_ON` is wider.

**3. Change hitch (CI–event)**  
`CHANGED_BY`, `TRIGGERED`, `DEPLOYED_AS` in the **release** sense. Change is a **fact with a time**, not a CMDB CI.

**4. Case / close (not E3)**  
`AFFECTS` → derived blast radius at **E9/E11**.  
`CORRELATED_WITH` → **E7 Curate** (one `CaseSeed`; D3).  
`RESOLVED_BY` → **E11 Package**.

Motadata folding Curate into Pillar B is exactly `CORRELATED_WITH` on the graph. We do not.

**Q. Can the same edges be bucketed upstream / downstream / peer?**

**Only buckets 1–2, and only relative to a seed.** Upstream/downstream is a **walk orientation**, not a property of every Motadata edge type. `RUNS_ON` / `CONTAINS` are **vertical**. **Peer** is same-tier (`clustered_with`) — Motadata did not name it. `CHANGED_BY`, `TRIGGERED`, `CORRELATED_WITH`, `RESOLVED_BY`, `AFFECTS` are **not** upstream/downstream.

---

## 6. Alert on the graph vs E6 Signal

**Q. You said Motadata reifies Alert as a graph node, but alerts are E6 Signals, not entities?**

Both. Two uses of “node”:

- **CI node** — `tenant`+`ci_id`, leaf, maybe ticket. **Alert is not this.**  
- **Fact / event vertex** — Motadata draws Detect output on the map so they can store `TRIGGERED` / `CORRELATED_WITH`.

For us: Detect **emits** a `Signal` (E6). It **points at** a CI. It is **not** a vertex in `GraphSnapshot`. Curate merges signals (E7). Same split for Incident (`CaseSeed` / later ticket) and Change (fact, not localize target).

**Q. Do Dynatrace / Datadog / Edge Delta have fact/event nodes on the map, besides CI/entity nodes?**

**They have the objects. They do not treat them as topology vertices.** Join is **identity + time**, not `Alert` as a neighbor of `Service` on the same graph.

| Vendor | Map (CI/entity plane) | Event / case objects (not map vertices) | How they join |
|--------|------------------------|------------------------------------------|----------------|
| **Dynatrace** | **Smartscape** — hosts, processes, services, k8s, … (`entityId`) | **Davis Event** (Detect), **Problem** (package). Events also live in **Grail** by `entityId` + time | Problem/Event **points at** `entityId`. Davis **walks Smartscape**, then **pulls Grail**. Event is not a Smartscape type you hop like HOST→SERVICE |
| **Datadog** | **Service Map** — services / APM peers (tags, not Smartscape) | **Monitor** / **Watchdog** (Detect doors). **Incident** / **Bits** optional. Husky holds traces/logs as an *event store*, not an alert graph | Tags / `service`. Map does not store the monitor as a node. Alert ≠ Incident (**Observed**) |
| **Edge Delta** | **eBPF / pipeline service map** — who talks to whom | **Monitor** (Detect). **Issue** / Overview thread (their package, not our E11) | Issue **about** a service/pipeline. Not an extra node type on the service map |
| **Motadata PDF** | Same graph as events | Alert, Incident, Change, ITSMTicket listed as **entities** | `TRIGGERED` / `CORRELATED_WITH` / `RESOLVED_BY` as **edges** |
| **Ours** | **E3** CIs only | **E6 `Signal`**, **E7 `CaseSeed`**, **E11 `VerdictCard`** | Pointer from signal → `ci_id`. Same split as DT/DD/ED, not Motadata |

So: DT/DD/ED match **column 3** (map ∥ event/case store). Motadata is the outlier that **reifies** Detect/case onto Pillar B. We refuse that. Deploy/change **events** still exist (DT entity events, DD change events, our reserved `change_event`) — as **facts on a CI**, not as a second Smartscape.

---

## 7. Service map vs Smartscape vs ours vs Motadata

**Q. Is Motadata’s knowledge graph Smartscape or a service map?**

Closer to **Smartscape’s job** than to a **service map**. It is neither product.

A **service map** is usually one layer: services + `CALLS` (Datadog APM, ED eBPF). Hop budget. No host→pod→process, no Change/Alert vertices.

**Smartscape** is Dynatrace’s typed multi-layer topology; Davis walks it, then pulls **Grail** on the same `entityId`. Map ∥ lake.

Motadata Pillar B aims at that RCA walk, then **also** hangs Change/Alert/Incident as vertices.

**Q. 3rd design or 4th?**

If the count is this table: **(1) service map, (2) Smartscape, (3) ours, (4) Motadata.** Motadata is **not** design 3.

| | **1 Service map** | **2 Smartscape** | **3 Ours — E3 operational graph** | **4 Motadata Pillar B** |
|--|-------------------|------------------|-------------------------------------|-------------------------|
| **Job** | Who talks to whom (hop budget) | Walk *where* the fault sits, then fetch evidence | Same walk job as Smartscape, with **auditable** edges | Same walk job, then continue the walk onto Change / Alert / Incident vertices |
| **Layers** | One: services (sometimes processes) | Many: host / process / service / k8s / … | Many: CI stack (`tier` + `instance_scope`). Illustration ≠ required CI list | Many: mixes durable CIs, ephemeral runtime, and event types in one entity list |
| **Nodes** | Services | Dynatrace entities | **CIs only** (`tenant`+`ci_id`). Not Alert, Incident, ticket, or Change-as-CI | CIs **and** Alert, Incident, Change, ITSMTicket, Metric, Trace, LogPattern as “entities” |
| **Identity** | `service` (+ tags). Soft | One `entityId` on **map and lake** | `tenant`+`ci_id`. Aliases on the identity record. Unresolved ≠ localize/ticket (**D-E2-1**) | `entity_id` + `entity_type` + `tenant_id`. Persistence not specified per type |
| **Edges** | `CALLS` / inferred `DEPENDS_ON` from traces or eBPF | Typed relationships OneAgent keeps fresh | 15 types (`depends_on`, `runs_on`, `communicates_with`, …) each with provenance: `authoritative` \| `declared` \| `corroborating` | `CALLS` · `DEPENDS_ON` · `RUNS_ON` · `CONTAINS` · … plus `TRIGGERED` · `CORRELATED_WITH` · `RESOLVED_BY` · `AFFECTS` |
| **Time** | “Current” map; often lags | Live discovery; not a lake rebuild | Edges: `refresh` cadence; `declared` can stale (**E5**). Nodes are CIs, not `valid_from` event facts | `valid_from` / `valid_to` on **nodes and edges** (graph history). Not Detect time |
| **Not on the map** | Host→pod→process, Change, Alert | Alert/Problem are Davis objects, not Smartscape vertex types in the service-map sense | **E6 `Signal`**, **E7 `CaseSeed`**, **E11 `VerdictCard`**. Change is reserved `signal_class`, not Collect | Almost nothing: they reify Detect/case/ticket onto the same graph |
| **Who walks** | Human / APM UI. Does **not** name the leaf | Davis neighborhood walk | **E8** hop budget · **E9** leaf rule. Gateway **assist** may emit a call-graph; **SaaS owns** the snapshot | Rust ReAct agent (Pillar C) *and* the documented traversal recipe. PDF is SaaS-only |
| **Locus** | APM/eBPF UI | SaaS | Node cues; Gateway **assist** = thin call-map; **SaaS owns** snapshot | PDF is SaaS column only |
| **Evidence store** | Traces in APM (same product rail) | Sibling: **Grail**, same `entityId` | Sibling: **E4 dest(s)**, same `ci_id` (**D2**). Map does not rebuild from the lake | Sibling: **Vortex/S3** sketches + graph. Agent must not dump the lake (retrieval layer = our E8) |
| **What it is not** | Not RCA | Not a generic CMDB dump | Not Motadata’s Alert/Incident vertices; not “the lake” | Not a classic service map; not our stage split (Curate/Package live on the graph) |

**Subset:** service map ⊂ Smartscape-shaped CI graph ⊂ Motadata if you add event nodes. Column 3 is the **middle**. Column 4 is the middle **plus** event vertices and case edges.

**Q. Should the final design be a hybrid of 3 and 4? How do they merge?**

**Yes: one graph, two planes — column 3’s CI plane is canonical; column 4’s extras are either folded into E3/E5 as *time on CI edges*, or kept off E3 as P2/P3 objects.** Not “union every Motadata entity type.”

Compare 3 vs 4 before merging:

| Topic | 3 (ours) | 4 (Motadata) | Merge |
|--------|----------|--------------|--------|
| Node kinds | CIs only | CIs + events | **Keep 3.** Ephemeral CIs (Pod) allowed only with a **validity window** + parent CI. Alert/Incident/ticket stay off E3. |
| Graph time | `refresh` + E5 decay | `valid_from` / `valid_to` | **Take 4’s job, keep 3’s names or adopt both.** Validity is **E3/E5**, never E6. Needed so a dead pod does not look like a live CI. |
| Provenance | `authoritative` / `declared` / `corroborating` | `confidence` + `source` | **Keep 3** (richer). Map Motadata `source` → `discovered_via`. |
| Structure + runtime edges | 15 typed CI–CI edges | `CONTAINS` `RUNS_ON` `CALLS` `DEPENDS_ON` … | **Keep 3’s catalog.** Motadata names are aliases into buckets 1–2 (structure / runtime). |
| Change | Reserved `change_event`; not Collect this pass | `Change` vertex + `CHANGED_BY` | **Take 4 as a fact, not a CI.** Join `change_id` → CI via `CHANGED_BY`. Not an E9 ticket root. |
| Alert / Incident | `Signal` / `CaseSeed` | Vertices + `TRIGGERED` / `CORRELATED_WITH` | **Keep 3.** Those Motadata edges **are** E6/E7, not topology. |
| Impact / close | Derived at E9/E11 | `AFFECTS` / `RESOLVED_BY` stored | **Keep 3.** Do not persist blast radius or resolver as E3 edges. |
| Walker | E8/E9; Layer I optional (**D5 Review**) | ReAct agent walks the graph | **Keep 3.** Traversal *recipe* from 4 informs E9; the agent is not the graph. |
| Store | Dest-agnostic E4; graph is not the lake | Vortex/S3 holds graph + sketches | **Keep 3 + Gate B.** Same `ci_id` / `entity_id` namespace as Pillar A sketches. |

Each **topic** below is context for that row (what it is and why it is needed). The table above is the merge.

### Node kinds

**What:** What is allowed to be a **vertex** on the graph. A **CI node** is something with `tenant`+`ci_id` that E9 may name as a leaf and E11 may ticket. A **fact/event vertex** is a time-stamped object (Alert, Incident, Change-as-entity) drawn as if it were a neighbor of a service.

**Why:** If Alert is a vertex, Curate and Detect leak into E3 and you cannot tell “who exists in the estate” from “what fired this minute.” If only eternal CMDB CIs are vertices, a Pod that lived for ten minutes cannot appear on the walk at all.


### Graph time

**What:** When a **map fact** was true: “this pod existed,” “this `RUNS_ON` held.” Motadata names it `valid_from` / `valid_to`. We already have per-edge `refresh` and E5 decay (declared 7d/30d). **Not** “when the alert fired” (that is E6) and **not** the E8 investigation corridor.

**Why:** Without it, a replaced pod or a stale `declared` cluster membership still looks live, and E9 walks a ghost. Topology history is P1 work; Detect must not be the first place time appears on the map.


### Provenance

**What:** *Why we believe this edge.* Our three **epistemic** types: `authoritative` (owner system: inventory, mount table), `declared` (CMDB said so, nothing observed it), `corroborating` (inferred from traces/flows). Plus `confidence`, `discovered_via`, `refresh`. Motadata stores `confidence` + `source`.

**Why:** Half a real graph is inference. If the operator cannot see that `app → db` came from a sampled trace, the verdict’s confidence is decoration. Ranking should degrade when the path walks `declared` / `corroborating` (specified, not lab-validated yet).


### Structure + runtime edges

**What:** CI–CI relationship **types**. **Structure** = stack (`CONTAINS`, `RUNS_ON`, `part_of`). **Runtime / contract** = who talks to whom (`CALLS`, `DEPENDS_ON`, `PRODUCES`/`CONSUMES`). Our catalog has 15 names (`depends_on`, `runs_on`, `communicates_with`, …). Motadata’s `CALLS`… list is the same two buckets plus case edges (those are *not* this topic).

**Why:** E8 hop budget and E9 leaf search need typed walks (down the stack vs along callers). A service map is only the runtime bucket. RCA needs both.


### Change

**What:** “Something in the estate was modified” — deploy, config, git SHA, change ticket. Motadata makes **Change a vertex** with `CHANGED_BY`. We reserved `change_event` as a `signal_class` and **do not Collect it this pass**.

**Why:** The Motadata walk *deps → recent changes → abnormal metrics* is how you stop blaming the symptom app for a bad release. That hitch is real. Making Change a **CI** (ticket root, eternal id) is not: a change is an **operation with a time**, not a host.


### Alert / Incident

**What:** Detect output vs case object. **Alert / Event / Signal** = “something looks wrong now” (E6). **Incident / Problem / CaseSeed** = curated one-case (E7). Motadata draws both as vertices and links them with `TRIGGERED` / `CORRELATED_WITH`.

**Why:** DT/DD/ED keep these **off** Smartscape / Service Map and join by identity. If we copy Motadata, E3 becomes the case bus, D3 Curate disappears into an edge, and every storm pollutes the topology.


### Impact / close

**What:** **Impact** (`AFFECTS`) = blast radius: who hurts if this leaf is down. **Close** (`RESOLVED_BY`) = ticket, verdict, or person that closed the case. Motadata stores both as graph edges. We **compute** impact when packaging (E9/E11) and **emit** close as `VerdictCard` / optional ITSM (E11).

**Why:** Blast radius depends on the *current* walk and the *current* seed. Persisting `AFFECTS` as a standing topology edge goes stale the next deploy. `RESOLVED_BY` is a case outcome, not “who contains whom.”


### Walker

**What:** **Who reads** the graph to name a leaf. Ours: **E8** cuts hops/time, **E9** applies a leaf rule (deepest-error, longest self-time, …); Layer I / ReAct is optional (**D5 Review**). Motadata: the **Rust agent** walks, with a written recipe (Incident → service → deps → changes → metrics).

**Why:** If the agent *is* the graph, operator path dies and D5 flips. The recipe is still useful as **E9 search order**, not as a product that owns topology.


### Store

**What:** Where the map and the evidence live. Dynatrace: Smartscape ∥ Grail. Ours: **E3** ∥ **E4 dests**, same `ci_id` (**D2**). Motadata: **Vortex/S3** holds graph **and** sketches (both rooms).

**Why:** One warehouse is simpler to demo and easier to lock in as “the” lake. We stay dest-agnostic (Gate B): Vortex may be **one** dest profile. Sketches are an E4 **modality**, not a second map. The agent must not scan the lake (that bound is **E8**).


---

**Merged solution (one E3 `GraphSnapshot`):**

1. **Vertices** = CIs (`tenant`+`ci_id`), including time-bounded runtime CIs (Pod/Container) with `valid_from`/`valid_to` (or equivalent) and a `scope_parent`. No Alert, Incident, ITSMTicket, Metric, Trace, LogPattern vertices.  
2. **CI–CI edges** = our 15 types + Motadata buckets 1–2, each with provenance **and** a validity window. Service-map `CALLS` is one family (`communicates_with`), not the whole graph.  
3. **Change** = optional **fact records** (not CIs) attached by `CHANGED_BY`, admitted later as `change_event`, not E1 this pass.  
4. **Detect / Curate / Package** stay E6 / E7 / E11. The Motadata walk “Incident → service → deps → changes → metrics” is **how E9 reads** the CI graph + facts + E4, not extra vertex types.  
5. **P2 still has no pillar.** Retrieval bounds stay E8. Pillar C stays opt-in Layer I. **Do not flip D5.**

That is Smartscape’s job (column 2/3) with Motadata’s **temporal CI edges** and **change hitch**, without Motadata’s **event-node bus**.

**Q. Pillar B ≈ Smartscape. Do we have anything parallel to Grail?**

**Yes: E4 Stores.** We did not brand a first-party lake. Dynatrace’s split is **Smartscape (map) ∥ Grail (evidence)** on one `entityId`. Ours is **E3 `GraphSnapshot` (map) ∥ E4 dest query surfaces (evidence)** on one `ci_id` (**D2 Signed**). The map does not rebuild from the lake.

Motadata **Vortex/S3** puts both rooms in one product: “historical observability” (sketches / history) **and** the knowledge graph. That is Grail **plus** Smartscape in one warehouse. We keep the rooms separate.

| Dynatrace | Motadata Vortex/S3 | Ours |
|-----------|-------------------|------|
| Smartscape | Graph builder → graph tables | **E3** |
| Grail (metrics/logs/traces/events) | Historical observability, including **Pillar A sketches** | **E4** (tenant dest in Q1; Gate B: not only Vortex) |
| Shared `entityId` | Shared `entity_id` | Shared `tenant`+`ci_id` |

**Pillar A (T-Digest / buckets / seasonal)** is not a third map. It is a **compact history modality that lives in E4** (and is refreshed by E5). Dashboards, **E6 door C**, and **E10** `get_metric_baseline()` read it the way Davis reads Grail after a Smartscape walk.

What we do **not** have yet: a named ObserveOps lake SKU, numeric E4 retention/latency NFRs (LLD-E4 still Draft), or a requirement that E4 be Vortex. Q1 dest *is* the store. Locus: Node/Gateway **buffer**, they are not Grail.

---

## 8. `valid_from` / `valid_to` — graph time, not Detect

**Q. Time bounds are not part of the knowledge graph; they appear at E6 Detect, right?**

**No.** Motadata `valid_from` / `valid_to` are **when a graph fact was true** (edge/node history). That is **E3 write + E5 Maintain**. Our analogue: per-edge **`refresh`**, declared-edge decay (7d soft / 30d hard). We did not copy the Motadata field names; we copied the job.

**E6** is a **different clock**: when the `Signal` fired. **E8** locks the investigation corridor.

| Clock | Stage | Meaning |
|--------|--------|---------|
| Edge/node validity | E3, E5 | Was this CI–CI fact true *then*? |
| Signal time | E6 | When did we decide something is wrong? |
| Case window | E8 | What interval may E9/E10 query? |

Do not merge these three. Graph time stays **P1**. Detect time stays **P2**.

---

## 9. Locked takeaways

- Pillars ≠ doors ≠ Gates ≠ phases.  
- Door C consumes Pillar A; it is not Pillar C.  
- Alert = `Signal` (E6), not a CI.  
- Canonical graph = SaaS E3; Gateway assist may look like a service map.  
- Hybrid 3+4 = temporal **CI** graph + Change-as-fact; **not** Motadata’s event vertices.  
- **Do not flip D5.** Operator E9–E11 must work with Pillar C off.

---

## 10. ToDo — leadership PDF vs our pipeline

**Q. What are we actually supposed to do with the Motadata PDF?**

We already designed a pipeline called **ObserveOps**: eleven stages named E1 through E11 (Collect → … → Package). That design came from studying vendors (Dynatrace, Datadog, Edge Delta), not from this Motadata PDF.

Leadership then handed us a 4-page requirements sketch: [`KR Plan/Motadata_Observability_3_Pillars_Architecture.pdf`](../../KR%20Plan/Motadata_Observability_3_Pillars_Architecture.pdf). It describes three products (percentile store, knowledge graph, Rust ReAct agent) and a SaaS stack that starts at a streaming bus called NATS.

**ToDo** is not “rebuild Motadata.” It is: put each PDF box next to the matching ObserveOps stage; say where they agree; where they fight, write a resolution that does **not** throw away our eleven-stage clock. The compact twin is the [job map](./motadata-3pillars-vs-shift-left.html).

### Terms this section uses (read once)

- **Node** — software on the customer machine (or sidecar) that first sees telemetry. **SaaS** — our (or Motadata’s) hosted side. **Shift-left** means: do as much Collect / Identity / optional Detect as we can *on the Node* (or an optional Gateway) *before* data is sent over TLS to SaaS. The Motadata PDF only draws the SaaS side.
- **E1 Collect** — admit raw telemetry. **E2 Identity** — attach a stable id: `tenant` (which customer) + `ci_id` (which configuration item, e.g. the checkout service). The on-the-wire record shape is **`ingest.v1`**.
- **E3** — the topology map (`GraphSnapshot`). **E4** — evidence stores (metrics/logs/traces, and compact percentile “sketches”). **E6 Detect** can fire in three places we call **doors**: A on the Node, B on a Gateway, C on the platform. **E7 Curate** merges many alerts into one case (`CaseSeed`). **E8** bounds what we may query. **E9–E11** localize, identify, and package a `VerdictCard`.
- **NATS** — in the PDF, a message bus: collectors publish telemetry, SaaS engines subscribe. It is a pipe, not identity and not Detect.
- **Block-2** — the August–November 2026-27 OKRs in the KR Plan spreadsheet. “Obj 1” is the first objective on that sheet (ship Node Collect + Identity).
- **D5** — our HLD decision on whether an LLM/agent is the default way to package a case. It stays **Review**: the operator path (no agent) must always work. **Do not flip D5.**
- **Hybrid 3+4** — not a new product name. It is the bundle of resolutions for conflicts 2–5: keep our CI-only map; take Motadata’s *time on map edges* and sketches-in-the-store; refuse Alert-as-a-map-node and “the agent is Curate and Package.”

The PDF does **not** mention Node Collect, mask/redact, Drain (log-pattern reduce), Detect on the Node, or an optional Gateway. That **omission** is why conflict 1 exists — not because the PDF forbids those steps.

**Already maps (not a fight):** their percentile sketches are the same *job* as our E4 compact history (Pillar A). Their “walk the graph to find where the fault sits” is the same *job* as E3 + E9 (Pillar B’s job). Their “don’t dump the whole lake into the agent” is E8. Their “evidence, not LLM assertion” is E10. Their explain/ticket is E11 (we call the artifact a `VerdictCard`). Restarting machines / auto-remediate is **not** Package in our HLD.

### Register (eight conflicts)

Sketches ≠ map. **Sketches** = compact percentile history (Grail-like, E4). **Map** = who-is-connected graph (Smartscape-like, E3). Motadata Vortex+S3 draws **both rooms in one product**.

| # | Topic | Leadership (PDF) | Ours | Fight | Resolution | Remarks |
|---|--------|------------------|------|-------|------------|---------|
| 1 | Where does processing start? | Telemetry → **NATS** → percentile engine and graph builder (page 1). Collectors unnamed. Windowing after the bus. | Node redacts, Drain, binds `tenant`+`ci_id` **before TLS**. Optional Detect on the Node (door A). | **Not a PDF claim.** The drawing starts named engines after NATS; collectors before NATS are unnamed. It does not say “nothing intelligent happens on the Node.” | We still specify the Node (E1–E2, optional door A). NATS, if used, is a pipe for already-identified `ingest.v1` records — it does not replace Collect/Identity. | **Gap / mapping risk**, same family as #8. Someone *could* misread the picture as the full product; the PDF itself is silent, not opposed. Local NATS on the Node is allowed as a buffer. Block-2 obj 1: prove lab egress. |
| 2 | One warehouse or two rooms? (historical vs knowledge graph) | **Vortex + S3** = Historical Observability **and** Knowledge Graph (page 1–2). | **Two rooms**, same id: E3 = map; E4 = evidence (including sketches). Map is not rebuilt from the lake. | One warehouse vs split stores. | Vortex may be **one** tenant dest (Gate B), not the only lake. Sketches live in E4, not as a second topology. | **Do not swap labels:** sketches ≠ Smartscape. Map ≠ Grail. Dynatrace: Smartscape ∥ Grail. We: E3 ∥ E4. |
| 3 | Entities on the map — Alerts, tickets, events | Page 2 **entities** include Alert, Incident, Change, ITSMTicket, Metric, Trace. Edges: TRIGGERED, CORRELATED_WITH, RESOLVED_BY. | Map = **CIs only**. Alert = E6 `Signal` pointing at a CI. Tickets = E11 output. | Detect/case objects drawn as neighbors of services. | Keep CI plane. Take **graph time** (`valid_from`/`to`) on CI edges (E3/E5). Change = fact later, not a CI. | DT/DD/ED also keep Events/Problems off the topology map. Block-2 obj 2: GraphSnapshot without event vertices. |
| 4 | Who merges a storm into one case? (deduplication) | `CORRELATED_WITH` on the graph; agent tool `deduplicate_incident()` (page 2–3). | **E7 Curate** must emit one `CaseSeed` **before** diagnose (**D3**). | Dedup lives inside the agent / on the map. | Merge rationale on the **case**, not as an E3 edge. Agent never first-merges a storm. | “Deduplication” here means one case from many signals, not log-line Drain. Block-2 obj 3. |
| 5 | Is ReAct the RCA engine? | Page 1–3: Rust ReAct agent is the closer; tools include remediate. | Operator **E9–E11** always on. Agent = optional Layer I. **D5 stays Review.** | PDF default = agent. Ours default = deterministic close. | Use their **walk order** (service → deps → metrics) as E9 search. Do not require ReAct to execute it. Remediate out of this clock. | Pillar C ≠ Detect door C. Block-2 obj 4: three classes with Layer I **off**. |
| 6 | Where does Detect run? | Thresholds / alerts on sketches **after Vortex** (page 1 Pillar A). No Node trigger. | Three **doors**: A Node, B Gateway, C platform (reads sketches). | PDF only drew platform Detect. | Build door C as specified. Still build A and B. **Gate C** = which classes stay platform-only. | Door C **reads** Pillar A; it is **not** Pillar C (the agent). Disk-full can be door A; weekday p95 is door C. |
| 7 | Are tickets and remediations ingest? | Telemetry line includes **ITSM**. Stack ends Explain / ITSM / Remediate. Tools: `create_ticket()`, `execute_remediation()`. | E1 = **telemetry only**. Ticket = optional E11 egress. Remediate **not** in E1–E11. | Wrong stage: ticket/fix drawn as ingest or as the same loop as Package. | Do not Collect ServiceNow. Do not restart pods from E11 this pass. | Change tickets as *facts* later is conflict 3, not Collect. |
| 8 | Who creates `entity_id`? | Sketch and graph rows already have `entity_id` / `tenant_id` (page 1–2). No bind step. | **E2 Identity** creates `tenant`+`ci_id`. Unresolved ≠ ticket (**D-E2-1**). | Gap, not a fight: PDF assumes the id exists. | Bind on the Node (or bind-miss queue) **before** A/B writes. | Same lab proof as #1. Motadata `entity_id` ≈ our `ci_id` **after** bind. |

Longer explanation of each row follows.

---

### Conflict 1 — Where does processing start?

**Where in the PDF:** page 1, §1 Executive Architecture. They never say “central bus.” They draw **Telemetry → Streaming Layer — NATS → Percentile Engine | Graph Builder → Vortex**. Windowing and T-Digest sit after NATS. Collectors are unnamed.

**Conflict:** The PDF **does not claim** that intelligence starts only after NATS. Page 1 names engines *after* a streaming layer; it does not describe what collectors do *before* publish, and it does not forbid redact or identity on the Node. The mapping gap is: we must still write those Node steps; they are simply **not in the picture**.

**Example:** A pod log line contains a bearer token. The PDF does not say “send the token through NATS.” It also does not say “redact on the Node.” We still redact and stamp `ci_id=checkout-api` on the Node; NATS (if any) may carry the cleaned `ingest.v1` record.

**Resolution:** We do **not** delay redact, Drain, or identity until after a central bus just because those boxes are missing from page 1. We keep **shift-left**: the Node still redacts secrets and stamps `tenant` + `ci_id` *before* data leaves the machine. The Motadata drawing is a **SaaS-side stack** (percentile engine, graph builder, Vortex, agent). It is not a statement that the Node is empty.

If we use NATS at all, it is a **message hop**: records already went through Collect (and Identity where we bind). NATS does not replace E1 or E2. A NATS process *on* the Node is allowed as a local buffer.

So E1 then E2 stay **our** work — the PDF is **silent**, not opposed.

**Still ToDo (Block-2, objective 1 — “Shift-left Node fabric”):** in the lab, show a Kubernetes and a VM stream leaving the Node as `ingest.v1` with `tenant` and `ci_id` filled in, and with secrets not in the egress. That proves the PDF stack can sit *on top of* our edge, rather than instead of it.

---

### Conflict 2 — One warehouse or two rooms?

**Where in the PDF:** page 1 stack **Vortex + S3 — Historical Observability + Knowledge Graph**; page 2 “Vortex/S3 is the durable analytical graph store.”

**Conflict:** They put sketches *and* the map in one product. We split **E3 map ∥ E4 dests** (D2). The map does not rebuild from the lake. Q1 dest is whatever the tenant already uses.

**Example:** “Give me p95 for `checkout-api` this Monday 9am” is an **E4** sketch lookup. “Who does checkout call?” is an **E3** edge walk. Same `ci_id`. You do not discover callers by scanning Vortex traces to *invent* the topology at query time.

**Resolution:** Do not put the map tables and the metric/log history in one mandatory warehouse named Vortex. Keep **two rooms** that share the same id (`tenant` + `ci_id`):

- Room 1 is **E3** — who exists and how CIs connect (the map).
- Room 2 is **E4** — time-series evidence, including Motadata’s compact percentile sketches as one extra *kind* of history, not a second map.

**Vortex + S3** in the PDF may be *one* tenant destination we can write to (we call that decision **Gate B**: which storage product is this tenant’s dest). It is not required to be the only dest, and the graph must not be *rebuilt* by querying the lake at RCA time.

**Still ToDo (production depth):** finish LLD-E4 (Stores is still Draft); prove Gate B dests beyond `files.v1` (Vortex and/or S3) on a Motadata-shaped path.

**Lab / PoC (done for Block-2 sketch path):** Pillar A sketch writer exists under [`pillar-ab-implementation/pillar-a/poc/`](../../pillar-ab-implementation/pillar-a/) and lands sketches in the `history/` room via Gate B **`files.v1`** (a non-Vortex dest). That satisfies “show at least one dest that is not Vortex” for the lab; it does **not** close production Vortex+S3 temperature jobs.

---

### Conflict 3 — Is an Alert a node on the map?

**Where in the PDF:** page 2 **Core entities** lists Change, Alert, Incident, ITSMTicket next to Service and Host. Edges include `TRIGGERED`, `CORRELATED_WITH`, `RESOLVED_BY`.

**Conflict:** They draw Detect/case objects as graph neighbors of CIs. Our map is **CIs only**. Alert is an E6 `Signal` that *points at* a CI. DT/DD/ED keep Events/Problems/Monitors off the topology map too.

**Example:** Checkout p95 crosses a threshold. PDF: new vertex `Alert-8831` with edge `TRIGGERED` → Service checkout. Us: `Signal` `{ci_id: checkout-api, class: SLOWDOWN}`. The graph still has checkout → payments (`communicates_with`). The alert is not a third node you hop through.

**Resolution:** The map stays **CIs only** (services, hosts, pods-with-a-parent-and-a-time-window, …). An Alert stays an E6 Detect output (`Signal`) that *names* a `ci_id`. We *do* take one Motadata idea: **when a map fact was true** (`valid_from` / `valid_to` on CI nodes and CI–CI edges), written by E3 and refreshed by E5 — that is not “when the alert fired” (E6).

A **Change** (deploy, config, ticket) is a timed fact we may attach later with something like `CHANGED_BY`. It is not a configuration item we localize or ticket, and we do not ingest change tickets as Collect in this pass.

**Still ToDo (Block-2, objective 2 — P1 stores):** ship a `GraphSnapshot` that has validity + provenance on CI edges, and that does **not** contain Alert/Incident vertices.

---

### Conflict 4 — Who merges a storm into one case?

**Where in the PDF:** page 2 edge `CORRELATED_WITH`; page 3 tool `deduplicate_incident()` on the Rust agent.

**Conflict:** They fold Curate into Pillar C. We require **E7** one `CaseSeed` (**D3**) *before* diagnose. The agent must not be the first place five alerts become one incident.

**Example:** Host CPU high, checkout 5xx, and payments timeout fire in one minute. PDF agent calls `deduplicate_incident()` while walking. Us: E7 already emitted one `CaseSeed` with merge rationale; E8 then cuts hops/time; E9 walks that seed.

**Resolution:** Merging a storm stays **E7 Curate**, a required stage **before** any diagnose walk and **before** any optional agent (**D3** in the HLD: one seed per case). Motadata’s `CORRELATED_WITH` is the *sentence we store on the case* (“these three signals are the same incident because…”), not a permanent edge on the topology map.

**Still ToDo (Block-2, objective 3 — case open without an LLM):** emit one `CaseSeed` per correlated storm, with that merge rationale written down.

---

### Conflict 5 — Is ReAct the RCA engine?

**Where in the PDF:** page 1 ends at **Rust RCA Agent**; page 3 state machine Observe → Retrieve → … → Decide, plus `execute_remediation()`.

**Conflict:** The PDF’s default closer is the agent. Ours is deterministic E9–E11. **D5 stays Review.** Layer I is optional (Gate D). Operator path must work with Pillar C **off**.

**Example:** Same checkout 5xx. PDF: ReAct loops `query_graph()` / `get_metric_baseline()` until it names a leaf and maybe remediates. Us: E9 applies a leaf rule on the CI graph (their walk *recipe*: service → deps → metrics); E10 pulls sketches/logs; E11 writes a `VerdictCard`. No LLM required.

**Resolution:** Copy Motadata’s **search order** (start at the affected service, walk dependencies, look at recent changes, then abnormal metrics) as how **E9 Localize** walks *our* CI graph plus E4 evidence. Do **not** make the Rust ReAct agent the default engine that performs that walk. **D5 stays Review**: Layer I (an optional agent) may be added later behind **Gate D** (on/off). Until then, and even after, E9–E11 must produce a `VerdictCard` with the agent **off**. Auto-remediation (`execute_remediation`) is outside this eleven-stage clock.

**Still ToDo (Block-2, objective 4 — deterministic RCA close):** close three Detect classes on the operator path, Layer I off. Do not schedule the ReAct agent in this block.

---

### Conflict 6 — Where does Detect run?

**Where in the PDF:** page 1 Pillar A table field **thresholds — Anomaly detection boundaries**; consumers include **alerts**. All of that sits after Vortex. No Node trigger.

**Conflict:** That is only **door C** (platform monitor on sketches). We also have **door A** (Node) and **door B** (Gateway). Door C *reads* Pillar A; it is **not** Pillar C.

**Example:** Disk full on a VM can fire on the Node in seconds (door A). “p95 for this weekday-hour is weird” needs sketches, so it waits for door C. Both are Detect. The PDF only drew the second.

**Resolution:** Build the PDF’s sketch-based alerting as **door C** (a monitor on the platform that *reads* Pillar A sketches). Separately keep **door A** (Node can fire when the machine already knows, e.g. disk full) and **door B** (optional Gateway). Write **Gate C**: which Detect *classes* are allowed only on the platform. Door C consumes Pillar A; it is not Motadata Pillar C (the agent).

**Still ToDo:** write the Gate C decision; show door C firing on at least two Detect classes (for example ERROR and SLOWDOWN).

---

### Conflict 7 — Are tickets and remediations ingest?

**Where in the PDF:** page 1 Telemetry line includes **ITSM**; stack ends **Explain / ITSM / Remediate**. Page 3 tools `create_ticket()` and `execute_remediation()`.

**Conflict:** They list ITSM with Collect, and remediation in the same loop as Package. We Collect **telemetry only**. Ticket is E11 egress (or a later join). Remediation is **out of E1–E11**.

**Example:** A ServiceNow change ticket is not an `ingest.v1` log line. We may *emit* a ticket when packaging a verdict. We do not restart a pod from E11 this pass.

**Resolution:** **E1 Collect** this pass is logs/metrics/traces/events from the estate — not ServiceNow tickets. Creating a ticket is an **E11 Package** *output* (optional). Executing a fix (restart, scale, patch) is **not** one of E1–E11; it may reuse policy ideas later but it is out of this pipeline.

**Still ToDo:** keep that boundary in Block-2 (objective 4 lists ReAct, remediation, and ITSM-as-Collect as out of scope).

---

### Conflict 8 — Who creates `entity_id`?

**Where in the PDF:** page 1 sketch fields `entity_id`; page 2 graph `entity_id` / `entity_type` / `tenant_id`. No bind overlay, no “unresolved” state.

**Conflict:** Not a fight — a **gap**. They assume every row already has a stable id. We have E2 Identity: unresolved/synthesized ids are not ticket roots (**D-E2-1**).

**Example:** A log with only `pod_name=web-7f2` and no service. PDF sketch row still wants `entity_id`. Us: bind to `ci_id` when we can; if we cannot, do not localize or ticket that id.

**Resolution:** **E2 Identity** runs before any sketch row or graph node is written. If we cannot bind a stable `ci_id`, we do not treat that id as a localize target or a ticket root (rule **D-E2-1**). Motadata’s `entity_id` is the same *kind* of key once bound; they just skipped drawing the bind step.

**Still ToDo:** same as conflict 1 — prove `ingest.v1` already carries `tenant` + `ci_id` on the Node. That is the precondition for Pillars A and B.

---

Open until Block-2 work finishes: **D5** and **Gate D** stay Review (the optional agent stays off by default). The written specs for Topology (LLD-E3) and Stores (LLD-E4) stay Draft until those stores actually exist in the lab.
