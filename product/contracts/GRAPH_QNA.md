# Graph + sketch contract Q&A — E1–E5 always-on fabric

**Purpose:** Cold-reader answers for the graph/sketch contract across the **always-on fabric** (Collect → Identity → Topology ∥ Stores → Maintain), without dumping clarifications at the end of the sit-down brief.

**Status:** Living Q&A for the graph/sketch contract (E1–E5 always-on fabric).

> **Motadata writer fan-out (2026-09-23):** Target wire is [`WRITER_REGULATOR.md`](./WRITER_REGULATOR.md) (`writer_stream.v1`, presence predicates, **no `fact_kind`**). Answers below that still mention `fact_kind` describe the **legacy lab / Collect corpus** path until fixtures migrate — not the new GraphWriter/SketchWriter contracts.

**Parent brief (lock list + schemas):** [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md)

**Locked catches to protect while reading:**

1. **Sketches do not emit edges.** `sketch.v1` has no `src_ci_id` / `dst_ci_id` / `relation`.
2. **Two orthogonal fan-outs.** Stream branch after **E2**; destination choice at **E4 Stores** — do not collapse them.
3. **Rooms ≠ temperature.** `map/` / `history/` are content; Vortex / S3 are hot/cold when that dest is chosen.
4. **Identity bind is upstream.** Pillar A/B writers assume look-up / LUT-like stamping already happened at **E2** (or quarantine); they do not own the bind table.

**Companions:** [`data-shape-journey.html`](../../docs/fabric/data-shape-journey.html) (E1–E11 data evolution) · [`inventory-catalog-on-the-map.html`](../../docs/fabric/inventory-catalog-on-the-map.html) (inventory vs catalog → map) · [`sketch-exemplars-visual.html`](../../docs/fabric/sketch-exemplars-visual.html) (RED + exemplars · OTel vs ObserveOps) · [`e1-e5-pipeline-architecture.html`](../../docs/fabric/e1-e5-pipeline-architecture.html) · [`vortex-s3-interaction.html`](../../docs/fabric/vortex-s3-interaction.html) · [`map-history-storage-blocks.html`](../../docs/fabric/map-history-storage-blocks.html) · [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) · [`Sketches_Merging_RawData_QnA.pdf`](../../docs/fabric/Sketches_Merging_RawData_QnA.pdf)

---

## 1. How to use this Q&A and the sit-down

### G1. What does “sit-down” mean (§7)?

**A.** A **decision meeting** with the people who must vote this brief to **Signed** — not a pipeline stage and not a product feature.

This whole document is the one-pager for that meeting: freeze which Motadata names may become topology nodes, lock the configuration-item catalog and fifteen edge types, and lock the sketch row shape. Status stays “owner leanings locked” until **the room votes**. §7 (“Format for the sit-down”) only answers: what do we bring into that meeting (JSON field tables now; `.proto` / DDL after Signed when Vortex needs encoding).

---

## 2. GraphSnapshot and what is (not) on the map

### G2. Is `GraphSnapshot` our term or a vendor / library term (§8)?

**A.** **Ours** — ObserveOps / Pipeline HLD language, not Dynatrace, Datadog, Edge Delta, or an open-source graph product.

**E3 Topology**’s main output object is `GraphSnapshot`: the versioned, walkable map of configuration-item nodes and edges that Detect, Curate, and Localize read. Motadata’s “knowledge graph” maps onto that **job**; the name `GraphSnapshot` is our contract label. So when §8 says events do not become vertices on `GraphSnapshot`, it means they do not become vertices on **our** topology snapshot — they join by `tenant` + `ci_id` (and time) as evidence instead.

### G3. Do sketches store edges? Can Alert / Incident / ticket be graph nodes? (§2, §5.3, §8)

**A. No and no.**

- A **`sketch.v1`** row is one configuration item + one metric + one time window. It has `entity_id` (same string as map `entity_id` / ingest `ci_id` after bind). It does **not** have `source_id`, `target_id`, or `edge_type`. Join map and history later by identity and time within the Dest tenant.
- **Alert, Incident, ITSMTicket, Metric, Trace, LogPattern, Change-as-configuration-item** are **not** `graph_node.v1` vertices. They are facts / evidence / case objects that hitch the walk; long-lived tickets point *at* durable configuration items (`service`, `host`, named `db`, …), they are not the map themselves.

### G4. Are `CORRELATED_WITH`, `RESOLVED_BY`, or blast-radius `AFFECTS` topology edges? (§4.1)

**A. No.** Those words appear elsewhere in the pipeline; they are **not** Pillar B / `GraphSnapshot` edges.

| Word | What it actually is |
|------|---------------------|
| `CORRELATED_WITH` (Curate) | Signals / cases belonging together — not two estate configuration items |
| `RESOLVED_BY` (Package) | Verdict / ticket closed that case — packaging outcome |
| `AFFECTS` as stored blast radius | Impact computed or asserted at investigation time — not a durable map fact we freeze on the CI graph |

Motadata product words such as `CALLS` / `RUNS_ON` map **into** the fifteen-relation enum as aliases. We do not keep two edge vocabularies in storage.

### G5. For ERROR / SLOWDOWN only, which nodes and edges matter? Why do `CORRELATED_WITH` / `RESOLVED_BY` / `AFFECTS` feel odd? (§2–4)

**A. Those three are not knowledge-graph relations.** They are **event / case graph** words (Curate, Package, investigation-time blast radius). §4.1 already excludes them from `graph_edge.v1`. They are **not** in the fifteen-relation enum. They feel odd next to `depends_on` / `runs_on` because Motadata’s PDF drew them on the same picture as estate topology — we keep them off the map.

**ERROR / SLOWDOWN knowledge-graph slice** (what Localize actually walks for app fault / latency):

| Layer | Qualify | Defer / skip for this case |
|-------|---------|----------------------------|
| **Nodes** | `Service`, optional `BusinessService` / `Customer`; named `Database` / `Queue` when they are deps; optional `Runtime` / `Middleware`; `Host` only if you need hosting for self-time or shared-box context; ephemeral `Pod`/`Container` only with `scope_parent` | Disk / fabric / hypervisor / Monitor items (`NetworkPort`, `Datastore`, `HypervisorHost`, `monitored_by` collectors) — those belong to disk, network, contention, MONITORING_UNAVAILABLE walks |
| **Never nodes** | — | Alert, Incident, ticket, Metric, Trace, Change-as-CI (signals hitch the walk; they are not vertices) |
| **Edges (writers emit)** | **Core:** `depends_on`, `communicates_with` (and `uses` if you keep a separate trace-inferred name). **Composition / hosting:** `part_of`, `runs_on` when the leaf may sit on a box. Optional: `member_of` / `clustered_with` if the estate is clustered | `mounts`, `connects_to`, `backs`, `backed_up_by`, `hosted_on`, `routes_through`, `authenticates_via`, `monitored_by` — not required to localize ERROR/SLOWDOWN |
| **Not topology edges** | — | `CORRELATED_WITH`, `RESOLVED_BY`, stored `AFFECTS` |

**Practical cut:** ~**4–6 relations** for ERROR/SLOWDOWN writers (lab wave 1 already starts here: `depends_on`, `communicates_with`, `part_of`, `runs_on`, plus `hosted_on` only if VMs matter). That is **phased emission** (§4.6), not deleting the fifteen from the schema. Keep the full enum in storage so disk/network/contention cases do not force a second vocabulary later. Do not shrink the schema to ERROR/SLOWDOWN-only unless the room explicitly votes to postpone other Detect classes.

**One line:** ERROR/SLOWDOWN needs a **service + dependency / call map**; the other eleven relations exist for **other walks**, not because Curate/Package belong on Pillar B.

---

## 3. Edge catalog — schema, waves, provenance, mapping

### G6. What does “schema is rich on day one; writers grow” mean (§4.6)?

**A.** Two different clocks.

- **Rich on day one:** the JSON Schema already lists **all fifteen** `relation` names as a closed enum (and Vortex tables / LLD enums can be created once). Storage vocabulary does not keep changing when a new relation appears later.
- **Writers grow:** the code that *emits* edges does **not** have to produce all fifteen on day one. Lab wave 1 may emit only five relations because those are the sources we have; more writers come online as inventory / fabric / backup sources appear.

Without the split you either ship a tiny schema and migrate forever, or wait until every discovery source exists before shipping anything. Freeze the vocabulary now; fill the data gradually. Same idea as Q4’s wave table.

### G7. What are Lab wave 1 / wave 2 / Later based on (§4.6)?

**A.** A **pragmatic lab emission schedule**, not Motadata product phases and not a standards taxonomy. Schema already lists all fifteen relations; writers only emit what discovery sources can prove.

| Phase | Relations (examples) | Why that group |
|-------|----------------------|----------------|
| **Lab wave 1** | `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of` | Hosting, composition, and service dependency — usually available early from process inventory, Kubernetes ownership, catalog / APM. |
| **Lab wave 2** | `mounts`, `connects_to`, `monitored_by`, `member_of`, `uses` | Needs disk / mount inventory, L2/L3 adjacency, monitor registry, cluster membership, richer inferred “uses.” |
| **Later** | `backs`, `backed_up_by`, `clustered_with`, `routes_through`, `authenticates_via`, … | Backup, HA peer, fabric path, auth path — sources often missing until later integrations. |

Wave names are **our sequencing** so Topology “Done” is not blocked on every source existing on day one. Schema stays rich; writers grow.

### G8. What do `evidence_type` values mean — is it “claimed + verified” vs “claimed only” vs “inferred”? (§4.4)

**A.** Ranking of strength is right; the **claimed / verified** framing is not. These values say **how Topology learned the edge**, not whether Identify / Verify (later diagnose) confirmed a root-cause hypothesis.

| `evidence_type` | Means | Closer wording | Not this |
|-----------------|-------|----------------|----------|
| **`authoritative`** | A **system of record owns** the fact (agent process inventory / cgroup, Kubernetes API, vCenter, …). Prefer when available. | **Owned by inventory** — the inventory *is* the evidence. | Not “we ran Verify and proved RCA.” |
| **`declared`** | A **human or config asserted** it (CMDB, service catalog, Helm, Terraform). Believed until contradicted; not live observation. | **Asserted in config** — the catalog entry *is* evidence, but weaker / not observed. | Not “claimed with zero evidence.” |
| **`corroborating`** | **Telemetry suggests** it (trace call graph, repeated log fields, eBPF peer map). Useful for discovery; weaker alone. | **Inferred from telemetry.** Still stored as an edge row; just weaker provenance. | Not “invisible / not a real edge.” |

**Strength order:** authoritative > declared > corroborating.

**Examples:** cgroup says JVM runs on host → `authoritative` `runs_on`. Catalog says API depends on DB → `declared` `depends_on`. Spans show A calling B → `corroborating` `communicates_with` until inventory confirms.

### G9. Do `valid_from` / `valid_to` live inside provenance? (§4.3–4.4)

**A. No.** On Motadata-aligned `graph_edge.v1`, **`valid_from` / `valid_to` are sibling fields** next to `edge_type`. There is **no** nested `discovered_via` on the stored edge. Audit uses Snowflake `evidence_event_id`. Upsert identity is `(source_id, edge_type, target_id)`; `edge_id` is a snowflake reused on refresh.

### G10. How does Topology decide `relation` from inventory, catalog, or telemetry? (§4.3–4.4)

**A.** It does **not** invent free-text names. It picks one of the **fifteen closed enum** values by applying a **mapping rule** to the source, then stamps `discovered_via.evidence_type` from the source class.

| Source | Everyday meaning | Typical `relation` | `evidence_type` |
|--------|------------------|--------------------|-----------------|
| **Inventory** | System of record **owns** the fact (agent cgroup, Kubernetes API, vCenter) | Often hosting / ownership: `runs_on`, `part_of`, `hosted_on` | **`authoritative`** |
| **Catalog** | Human or config **asserted** it (CMDB, service catalog, Helm, Terraform) | Often dependency: `depends_on` | **`declared`** |
| **Telemetry** | Live data **suggests** it (APM spans, logs, eBPF) | Often talk/use: `communicates_with`, `uses` | **`corroborating`** |

**Three examples (same estate):**

1. Agent cgroup: JVM `app-runtime-jvm` on host `linux-server-app-01` → **`runs_on`**, authoritative.  
2. Service catalog: `checkout-api` needs `payments-db` → **`depends_on`**, declared.  
3. Spans: `checkout-api` repeatedly calls `inventory-api` → **`communicates_with`**, corroborating (often short `valid_to` until inventory confirms).

Prefer authoritative when inventory already has the fact. Catalog fills declared deps. Telemetry discovers candidates. The §4.5 JSON samples are exactly these three stories.

### G11. Inventory / catalog / telemetry — is that “already on the map” vs “first time” vs “live infer”? Same as Auto-create / Orphan / Soft-match? (§4.4–4.5)

**A. Close on telemetry; wrong on inventory and catalog. And not the same knob as Auto-create / Orphan / Soft-match.**

**What the three sources mean** (how we **learned the relationship**, after both ends are already resolved CIs):

| Source | Meaning | Not meaning |
|--------|---------|-------------|
| **Inventory** | A **system of record** that *owns* the fact (agent process/cgroup, Kubernetes API, vCenter, mount table). → usually `evidence_type: authoritative` | “This edge is already in-use on the topology for other entities.” The graph may or may not have held this arc before; that is refresh history, not the definition of inventory. |
| **Catalog** | A **config / CMDB / service-catalog assertion** (“checkout needs payments-db”). → `declared` | “Secondary pool only when inventory has no entry” or “first-time encounter.” Catalog can be the *only* source forever for a declared dep; inventory never has to invent that arrow. |
| **Telemetry** | **Live observation** suggests the link (spans, logs, eBPF peers). → `corroborating` | “Inventory would have known it if it were real.” Telemetry often discovers peers inventory never owned. |

So your three-edge story (JVM `runs_on` host · catalog `depends_on` · span `communicates_with`) is still the right teaching. The rewrite “inventory = in-use, catalog = first-time CMDB fill, telemetry = live infer” **collapses two axes** (source class vs whether we have seen the arc before).

**Preconditions:** for all three edges, Topology already has **both endpoints as resolved CIs**. Provenance answers *why we believe the arc*, not *whether the nodes exist*.

**Same estate — one example per source** (matches §4.5 samples):

1. **Inventory → `runs_on` (authoritative)**  
   **Fact:** JVM `app-runtime-jvm` lives on host `linux-server-app-01`.  
   **How we know:** The agent on that host reads process / cgroup inventory and reports “this workload is running here.” That inventory **owns** hosting — it is not guessing from spans.  
   **Edge:** `app-runtime-jvm` --`runs_on`→ `linux-server-app-01` · `evidence_type: authoritative`, source `agent/process-inventory/cgroup`.  
   **Not this:** “We already had some other `runs_on` edges on the map, so this is inventory.” Being already on the map is history; inventory is *who owned the fact*.

2. **Catalog → `depends_on` (declared)**  
   **Fact:** Service `checkout-api` needs database `payments-db`.  
   **How we know:** Service catalog / CMDB / Terraform says so. Nobody watched a call in this second. A human or config **asserted** the dependency.  
   **Edge:** `checkout-api` --`depends_on`→ `payments-db` · `evidence_type: declared`, source `service-catalog/sync`.  
   **Not this:** “Inventory had no hosting row, so we fell back to catalog.” Catalog is not a miss-handler for inventory. This arrow can stay **declared-only** forever; process inventory never invents “checkout needs payments.”

3. **Telemetry → `communicates_with` (corroborating)**  
   **Fact:** `checkout-api` talks to `inventory-api`.  
   **How we know:** APM spans keep showing client `checkout-api` with `span.peer.service=inventory-api`. Nothing in inventory or CMDB owns that peer link yet; live traffic **suggests** it.  
   **Edge:** `checkout-api` --`communicates_with`→ `inventory-api` · `evidence_type: corroborating`, `signal_fields` include the peer service, often a short `valid_to` while spans keep appearing.  
   **This matches “infer from live data.”**

| Case | Who spoke | Relation | Trust stamp |
|------|-----------|----------|-------------|
| Agent saw JVM on host | Inventory owns it | `runs_on` | authoritative |
| CMDB said checkout needs DB | Catalog asserted it | `depends_on` | declared |
| Spans showed checkout → inventory | Telemetry suggested it | `communicates_with` | corroborating |

**Auto-create / Orphan / Soft-match** (Phase-1 Topology bind on the Dynatrace-shaped pipeline — LUT miss when a raw label like `inv-svc-v2` does not hit `entityId`):

| Policy | Job |
|--------|-----|
| **Auto-create** | Mint a **new** node + LUT row (“seen ⇒ exists”) |
| **Orphan** | Keep telemetry **unbound** — no production join key |
| **Soft-match** | Alias the label onto an **existing** `entityId` |

That is a **node-identity bind** fallback when the lookup table misses. It is **not** `evidence_type` on an edge. Resonance is only emotional: both are “what do we do when certainty is incomplete.” Do not map Auto-create→authoritative, Orphan→declared, Soft-match→corroborating (or any fixed 1:1). You can auto-create a service from spans and still stamp the call edge `corroborating`; you can soft-match a host name and still write `runs_on` as `authoritative` from cgroup once both ends resolve.

**One line:** inventory / catalog / telemetry = **who owns or suggests the relationship**; Auto-create / Orphan / Soft-match = **what to do when a name does not yet bind to a CI**.

---

## 4. Always-on fabric E1–E5 — two fan-outs and writer placement

### G12. Is “E4 fan-out” the place where the pipeline splits?

**A. No.** There are **two** fan-outs. Only one of them is the stream branch.

```text
Stream fan-out (after E2):
  E1 Collect → E2 Identity → ┬→ E3 Topology (Pillar B)      → map / GraphSnapshot
                              └→ E4 Stores sketches (Pillar A) → history / sketch.v1

Destination fan-out (E4 product choice):
  Writers call Dest.put(room, …) → files.v1  |  Vortex+S3  |  Motadata store  |  …
```

| Insight | Correct reading |
|---------|-----------------|
| Dynatrace analogy | OneAgent → Smartscape ∥ Grail — parallel writers, not Smartscape→Grail chain |
| Where the stream branches | **After E2**, not “at E4 as a sequential stage” |
| What E4 still is | **Stores** — Pillar A’s sketch write stage, **sibling** to E3, not deleted |
| What “E4 destination fan-out” means on the Vortex/S3 block diagram | Which **lake product** receives rows — not where Identity first splits |

**One line:** fan-out after Identity; E3 = map writer; E4 = sketch writer; dest choice is a second, orthogonal fork.

### G13. Where does Pillar A (sketch write) sit vs Collect / Identity / Topology? Is it post-E2 and pre-E3, or overlapping? (§5–6)

**A.** Pillar A’s **write path** is **fully after Identity (E2)** and **parallel to Topology (E3)** — not a gate between them, and not inside either stage.

| Stage | Does Pillar A do this job? |
|-------|----------------------------|
| **E2 Identity** | **No.** Sketch writer only **checks** `identity.status = resolved` and **copies** `ci_id` → `entity_id`. It does not bind names. |
| **E3 Topology** | **No.** Sketches do not emit `runs_on`, `depends_on`, or any edge. |
| **E4 sketch store** | **Yes.** That is Pillar A. |

**One line:** post-E2, sibling to E3 — not overlapping E2 or E3. Any “overlap” feeling in the lab is from a **mixed fixture file** or later **join** checks, not from the sketch writer living inside Identity or Topology.

Teaching: [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) · visual: [`e1-e5-pipeline-architecture.html`](../../docs/fabric/e1-e5-pipeline-architecture.html).

### G14. Does “E4 destination” mean `map/` and `history/` (§6)?

**A. No.** That collapses the axes.

| Term | Means |
|------|--------|
| **E4 destination** | **Which physical product** receives the written rows — Vortex/S3, a lab file dest, an existing Motadata store, or another lake. That is **destination fan-out**. |
| **`map/` / `history/`** | **What kind of row** — knowledge-graph map vs historical sketches. |

Both rooms can land in the **same** destination (for example both in Vortex/S3). Destination fan-out is “write to product X or Y,” not “map vs history.” Prefer room names **`map/`** and **`history/`** — not “Room 1 / Room 2.”

### G15. Are the two rooms the same thing as Vortex + S3 (§6)?

**A. No — orthogonal axes.** Do not read “both hold the same data at different temperatures” as “map vs history.”

| Axis | Partitions | Share | Do not share |
|------|------------|-------|--------------|
| **Rooms (content)** | `map/` vs `history/` | Same identity namespace (`tenant` + `ci_id` / `entity_id`) | Different row shapes and facts |
| **Vortex + S3 (temperature)** | Hot engine vs cold cellar *when this E4 dest is chosen* | Same kinds of rows as they age (spill / federated scan) | Latency and durability tier |

Both rooms can live **inside** Vortex while hot and **age into** S3. Vortex is not `map/`; S3 is not `history/`.

Visual: [`vortex-s3-interaction.html`](../../docs/fabric/vortex-s3-interaction.html) (shows **both** fan-outs + `map/` / `history/` naming).

### G38. What do we assume about Identity / look-up (LUT-like) stamping before Pillar A and Pillar B?

**A.** For Motadata Pillar A/B (and this PoC), we treat **E2 Identity as already done** on the stream the writers see. Explicit understanding:

| Assumption | Meaning |
|------------|---------|
| **Bind is E2’s job** | A look-up / bind table (Dynatrace-shaped docs call this a **LUT**) turns raw labels (monitor id, `service.name`, host name, …) into a stable **`ci_id`**. That table is **not** a third store room beside `map/` / `history/`, and **not** owned by Pillar A or Pillar B. |
| **Writers see stamped records** | Production / PoC happy-path input is `ingest.v1` with `identity.status = resolved` and `tenant` + `ci_id` already set. Sketch `entity_id` **is that same string** — copy, do not re-bind. |
| **Unresolved does not enter production map/history** | `ResolvedOnlyGate` (PoC) rejects unresolved / synthesized. Those records may sit on an **unattributed queue** and/or a **bounded Identity quarantine** for later replay (discussion 04) — still **E2 / admission**, not sketch or graph packages. |
| **Corroborating telemetry alone ≠ resolved** | Inventory (**authoritative**) or catalog (**declared**) may promote a bind to `resolved`. Span/log accumulation alone typically stays weaker (`synthesized`) and is not a ticketable Localize leaf (D-E2-1). |
| **PoC fixtures** | Lab streams are **pre-resolved** on purpose so A/B unit tests do not need a live LUT service. That is a test stub of “E2 already ran,” not a claim that Motadata skips Identity in production. |

**What we are *not* assuming:** that Auto-create-from-telemetry is the default Motadata ticketable CI; that each pillar keeps its own private bind table; that “optional raw in history/” is how Identity lag is fixed.

**One line:** LUT-like stamping = E2; A∥B only admit resolved and write rooms.

See also: [`LLD-E2-Identity.md`](../../docs/observeops/LLD-E2-Identity.md) · [`../discussion/04-raw-data-identity-lut-open-questions.md`](../discussion/04-raw-data-identity-lut-open-questions.md) · G11 (miss policies ≠ evidence_type).

---

## 5. map/ and history/ — rooms, R/W, no sync

### G16. How are `map/` and `history/` stored? Sub-blocks, R/W, sync? (§6, Gate B dest)

**A.** After E2, two **independent writers** fill two **rooms**. There is **no continuous sync** that copies map ↔ history. Diagnose joins them by identity at **read** time.

| Room | Pillar | Sub-blocks | Analogy |
|------|--------|------------|---------|
| **`map/`** | B (E3) | `graph_node.v1`, `graph_edge.v1`, packaged as `GraphSnapshot` | Smartscape-like |
| **`history/`** | A (E4) | `sketch.v1` (T-Digest + buckets + baseline); lab `sketches.jsonl` | Grail-like history (sketches, not forever-raw) |

**Writes**

| Who | Room | Operation |
|-----|------|-----------|
| E3 Topology | `map/` | `Dest.put("map", …)` — nodes/edges / snapshot |
| E4 Sketch writer | `history/` | `Dest.put("history", "sketches.jsonl", …)` — sketch rows |
| E5 Maintain | both, separately | Seasonal baselines into A; validity/decay on B — **not** merging rooms |

**Reads**

| Who | Room | Need |
|-----|------|------|
| E6 Detect door C | history (primary) | digest p95 vs seasonal baseline |
| E8 Scope | both | `WorkingSet` = map neighbors + history sketches for those `ci_id`s |
| E9 / E10 | both | walk / `query_graph` + `get_metric_baseline` (+ optional hot-bin) |
| Optional Pillar C | WorkingSet only | same tools; no S3 dump |

**Join key:** Dest `tenant` + map `entity_id` ≡ sketch `entity_id` (ingest still says `ci_id`). Motadata node/edge rows do **not** carry `tenant`. Bind/LUT-like work is **E2 Identity**, not a third store room.

**Physical dest:** lab files, Motadata store, or Vortex+S3 — same logical rooms; hot/cold is temperature (§6).

Visuals: [`map-history-storage-blocks.html`](../../docs/fabric/map-history-storage-blocks.html) · [`map-history-storage-animation.html`](../../docs/fabric/map-history-storage-animation.html) · [`e1-e5-pipeline-architecture.html`](../../docs/fabric/e1-e5-pipeline-architecture.html).

**One line:** two rooms, two writers; join at WorkingSet — never sync folders into each other.

### G39. Why prefer `map/` / `history/` over “Room 1 / Room 2”?

**A.** “Room 1 / Room 2” was teaching shorthand on early Motadata-shaped diagrams. It forced readers to remember which number was graph vs sketches, and it collided with “two temperatures” language.

| Prefer | Means | Writer |
|--------|--------|--------|
| **`map/`** | Knowledge-graph content (`graph_node.v1`, `graph_edge.v1`, `GraphSnapshot`) | Pillar B / E3 |
| **`history/`** | Sketch / historical observability (`sketch.v1`; optional change facts) | Pillar A / E4 |

If an older slide still says Room 1 / Room 2: **Room 2 ≈ `map/`**, **Room 1 ≈ `history/`**. New docs and the Vortex interaction diagram use folder names only.

---

## 6. Motadata-shaped lake — Vortex, S3, hybrid schema, readers

### G17. Motadata-shaped Pillar A lake — do we need both S3 and Vortex, or is either optional? (§6, deep-dive §7.3–7.4)

**A.** **Both jobs are required** in the Motadata-shaped destination — not pick-one.

| Temperature | Product (Motadata-shaped) | Job |
|-------------|---------------------------|-----|
| **Cold** | S3 | Durable history — append immutable rows; do not rewrite giant raw sample lakes |
| **Hot** | Vortex | Interactive lookup — latest p95, Detect compare, graph walk, trends without raw scan |

Same logical rooms; two temperatures. Labs may use **local JSONL** as a cold stand-in and an in-process reader as a hot stand-in; that does not mean production drops either layer.

**One line:** S3 = remember; Vortex = query fast. Diagnose uses retrieval / WorkingSet — not ad-hoc S3 dumps.

Deep dive: [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../../docs/fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md) §7.3–7.4.

### G18. Is Vortex strictly schema-based? What if Host and Pod need different fields? (§6.1)

**A.** We lock a **hybrid** model — not fully strict, not schema-less.

- **Spine (strict):** every node/edge/sketch must carry the shared join and walk keys (`tenant` + `ci_id` / `entity_id`, closed `ci_type` / `relation`, identity status, and so on). That is what makes Localize and Retrieval fast and safe.
- **Attributes (flexible):** type-specific extras may differ (Pod `scope_parent`, Host aliases, edge `signal_fields`, `labels`, …). The JSON Schemas allow extras on purpose (`additionalProperties: true`).
- **Promotion rule:** if a field becomes a common filter or walk key, promote it onto the spine in a later schema version; do not invent a new free-text relation name to carry metadata.

Vortex (when chosen as the E4 dest) is the analytical store **under this logical contract**. Physical column layout can follow after Signed; Motadata Vortex DDL is not frozen yet.

**One line:** identity and relation types are rigid; decorations are not.

### G19. Who reads Vortex / S3 — and what does “agent” mean here (§6)?

**A.** Diagnose never opens the lake as a dump.

1. **Retrieval** queries Vortex (Vortex may federate cold S3) and builds a bounded **`WorkingSet`**.
2. **Deterministic Localize / Identify** consume that `WorkingSet`.
3. Motadata’s optional **Rust ReAct agent** (Pillar C / Layer I) is **one more client of retrieval** — tool calls stay inside that budget.

“Agent” in Motadata materials means that ReAct diagnose loop. It is **not** Collect, Topology, E4 writers, or “any HTTP caller.” Operator E9–E11 must work with ReAct **off**. Product rule: diagnose path does not open S3 directly and does not hop-scan Vortex raw.

### G20. Why does this brief avoid “Gate B” / Gate A–D vocabulary?

**A.** Those labels are **shift-left build-order checkpoints** (Node vs Gateway; which dest product; which Detect classes are platform-only; Layer I on/off). They belong on the Motadata ↔ shift-left job-map pages.

The sit-down brief freezes **row shapes** and identity rules. For storage it only needs plain language: **E4 destination** (Vortex/S3 is one allowed product, not the only lake forever). Dropping “Gate B” into the brief without defining it imports a second vocabulary a cold reader never saw. Substance kept; Gate label left on the build-order pages. PoC file dest profile: [`GATE_B_DEST_PROFILE.md`](./GATE_B_DEST_PROFILE.md). Map JSON keys/encoding: [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md).

### G40. What is the “Vortex query layer” vs the rooms?

**A.** Inside the Motadata-shaped dest, **rooms hold rows**; the **query layer is how diagnose asks for a bounded slice**.

| Piece | Job |
|-------|-----|
| **`map/` / `history/` inside Vortex** | Stored facts (graph + sketches), hot copies |
| **Vortex query layer** | Walk / filter / join those rooms (and federate cold S3 if needed) into one **`WorkingSet`** |
| **Retrieval** | Calls that query layer with hop/time/metric budgets — does not open S3 itself |
| **Localize / optional ReAct** | Consume the `WorkingSet` only |

So “query layer” is **not** a third room and **not** a second Identity bind. It is the read API above the same rooms writers filled after the two fan-outs.

Visual: [`vortex-s3-interaction.html`](../../docs/fabric/vortex-s3-interaction.html).

### G41. Is `graph_snapshot.v1` a columnar Vortex table?

**A. No.** Only **`map_nodes`** and **`map_edges`** are columnar tables. `graph_snapshot.v1` is a **packaged envelope** (`tenant` + `version` + full node/edge object arrays) used as the PoC read unit. On Motadata cold dest, the generation index is `map_snapshot_manifest.v1` + `latest.json`, not a third Vortex table.

Teaching: [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md) §1 · columns [`MAP_VORTEX_COLUMNAR_SCHEMA.md`](./MAP_VORTEX_COLUMNAR_SCHEMA.md).

### G42. Does `upsert_topo` / `write_topo_stream` write `.vortex` files?

**A. Hot yes, cold no.** Stream upserts mutate in-process Vortex/Arrow **Arrays** and adjacency. They do **not** PUT a new immutable `.vortex` object per line. Cold parts appear only on **`publish_map`** (new version + manifest + `latest`).

### G43. Can two edges share the same pair of nodes?

**A. Yes if `edge_type` differs; no if the typed arc is the same.** Upsert key is `(source_id, edge_type, target_id)`. Example: `DEPENDS_ON` and `COMMUNICATES_WITH` between the same ends are two rows; a second `DEPENDS_ON` **refreshes** the first (`edge_id` reused).

### G44. Is removal only `maintain_map`?

**A. Two levels.** (1) **`maintain_map`** — automatic validity / freshness on `valid_from` / `valid_to` and stale policy (E5-shaped). (2) **Explicit retire / remove** — intentional close (separate verb); retiring a **node** must close all **active incident edges**. Neither patches old cold `.vortex` files; next `publish_map` writes a new version.

Full lock: [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md) §5.

---

## 7. Sketch row shape — windows, digest, buckets, baseline, Detect

### G21. Must a sketch row carry `window`, `window_start`, and `window_end` (§5.4)?

**A. No — do not store all three as independent sources of truth.**

- **`window_start`** is **mandatory** (part of the uniqueness key).
- You need **exactly one of** `window` (duration string, e.g. `"5m"`) **or** `window_end` (RFC3339) — not both as separately authored fields.
- Because `window` is already in the row key, the canonical example keeps `window` and omits `window_end`. A reader can always derive the missing boundary: `window_end = window_start + window` (or the reverse).

Carrying all three independently invites `window_start + window ≠ window_end` with no clear winner.

### G22. Why T-Digest + buckets + baseline together? Are exemplars an alternate? (§5.2.1)

**A.** Three **different questions** about one metric window; all three belong in `sketch.v1` for season-aware Detect without keeping every raw sample.

- **T-Digest:** magnitude **this window** (mergeable percentiles).
- **Buckets:** histogram **this window** (same samples, fixed bins).
- **Baseline:** expected percentiles for **this `season_key`** from history.

Digest + buckets = same samples. Baseline = past windows, not this slice alone. Dropping baseline → false alarms on busy hours; dropping buckets → weak heatmap/rules; dropping digest → no mergeable p95.

**Exemplars** (GCP / OpenTelemetry) = optional **trace id on a histogram bin** for click-through to one request. **Not** a substitute for digest or baseline. Not required in v1 `sketch.v1` unless the room adds it later. See [`sketch-exemplars-visual.html`](../../docs/fabric/sketch-exemplars-visual.html).

### G23. Digest and buckets use the same raw samples — so what is the difference? (§5.2)

**A.** Same **input**, different **leftover**. Like two photographs of the same room from different angles. Neither keeps the raw list forever.

| | **T-Digest** | **Buckets** |
|--|--------------|-------------|
| **What it stores** | Approximate **distribution** as weighted centroids | Exact **counts** in **fixed** value ranges you chose ahead of time |
| **Natural answer** | “About what is p50 / p95 / p99?” | “How many samples fell in `[100, 200)` ms?” |
| **Bin edges** | Soft / adaptive (algorithm places mass where samples are) | Hard / declared (e.g. 0, 50, 100, 200, 500, …) |
| **Tail percentiles** | Designed to stay usable as you merge windows | Only as good as your bin edges; coarse tail bins lose precision |
| **Merge across windows** | Digests merge cleanly into a longer-window digest | Counts add **only if** both windows used the same `bucket_schema_version` / bounds |
| **Charts / simple rules** | Possible but awkward (“is p95 high?”) | Natural (“count above 500”, heatmap by bin) |

**Same 23 samples, two readouts.** Buckets might say: 2 in `[0, 50)`, 8 in `[50, 100)`, 10 in `[100, 200)`, 2 in `[200, 500)`, 1 in `[500, 1000)`. You see **where the mass sits**; you do **not** get a precise p95 without guessing inside a bin. T-Digest might say p50 ≈ 100 ms, p95 ≈ 400 ms, p99 ≈ 900 ms. You get **percentiles** and can **merge** this 5-minute digest with the next ones; you do **not** get a stable “how many in `[100, 200)`” without also keeping buckets.

**Why both:** “How bad as a percentile?” and “How is mass split across fixed bins?” are different products of the same data. Detect / merge history lean on **digest** (+ baseline for season). Heatmap / “count in bin X” / attaching an **exemplar** to a bin lean on **buckets**. One is a **smooth distribution sketch**; the other is a **histogram**.

### G24. Is T-Digest + baseline enough for Detect? Why keep buckets? Why not Detect only on buckets? (§5.2.1)

**A.** For **our** Motadata-shaped Detect (percentile vs season): **yes — digest + baseline is enough to fire.** Buckets are not in that ratio.

| Job | Uses |
|-----|------|
| **Detect** — “abnormal for this season?” | Digest current p95 **vs** baseline expected p95 |
| **Investigate after fire** | Buckets (which range) + optional exemplars (which `trace_id`) |

**Vice versa:** Detect on **bin counts vs seasonal bin baselines** is a *different* design (shape Detect). It can also avoid raw scans **if** bucket counts are already stored in `sketch.v1`. We did **not** choose it as the primary door-C path because Pillar A Detect is **quantile-language** (p95/p99), and digests are built for that.

**Correction on “mergeable” as the moat vs buckets:** both digests and fixed-bound buckets merge without raw replay (buckets: add counts). The sharper contrast is **quantile-native Detect** and better tail percentiles than coarse bins — not “only digests merge.” The latency killer is **Detect without any precomputed sketch** (scanning raw history), not “buckets force raw.”

### G25. Is sketch anomaly detection the same as Phase-2 Detect? What about Door A / B / C?

**A.** Same story, **two clocks** — not two competing products.

| Clock | Stages | Role |
|-------|--------|------|
| **P1 write** | E4 / E5 | Build `sketch.v1` (digest, buckets, baseline; optional exemplars) |
| **P2 read** | E6–E8 | **E6 Detect** reads sketches; door **C** = platform monitor (digest vs baseline) → `Signal` → Curate → Scope |

**Door A / B / C** = E6 **entry points** (still live vocabulary on Motadata ↔ shift-left pages):

| Door | Where Detect can fire |
|------|------------------------|
| **A** | Node (local trigger, e.g. disk full) |
| **B** | Gateway (optional) |
| **C** | Platform reading Pillar A sketches |

**Do not confuse:** Door C ≠ **Pillar C** (Rust ReAct agent). Door C ≠ **Gate C** (build-order checkpoint). *Door C reads Pillar A; it is not Pillar C.*

This walkthrough-style Detect (digest vs baseline) **is** door C when mapped onto the pipeline. Doors A/B still ours to build; Motadata PDF mainly drew platform Detect.

See also **G41** — how E6 fires on `history/` alone when sketches carry no edges.

### G41. How does E6 Detect work on `history/` sketches alone — with no edges in the sketch row?

**A.** **E6 does not need edges.** Detect and Localize answer different questions on purpose.

| Stage | Question | Reads | Needs `map/` edges? |
|-------|----------|-------|---------------------|
| **E6 Detect** (door C) | Is **this configuration item’s metric** abnormal **for this time-of-week**? | `history/` only | **No** |
| **E8 Scope** | What bounded evidence belongs in this case? | `map/` + `history/` | Yes — neighbors from graph |
| **E9 Localize** | From the symptom CI, **where** should we walk next? | `map/` (+ WorkingSet) | **Yes** — typed edge walk |

**What one `sketch.v1` row is.** After E4, each closed window produces one **self-contained stat card**:

```text
(tenant, entity_id, metric_id, window, window_start, season_key)
  → tdigest     (current p50 / p95 / p99 for this window)
  → baseline    (expected p50 / p95 / p99 for this season_key)
  → buckets     (optional — investigation after fire)
```

The row carries **who** and **what** (`entity_id` ≡ graph `ci_id` after E2 bind; `metric_id`; `entity_type`; `season_key`). It does **not** carry **who talks to whom**. The schema forbids edge fields on sketches (`src_ci_id`, `dst_ci_id`, `relation` are not sketch keys). See **G3**.

**What door C actually computes.** A scalar comparison on that row — no hop, no neighbor lookup:

```python
ratio = current_p95 / baseline.expected_p95
fired = ratio > threshold   # e.g. 1.5×
```

Walkthrough example ([`end-to-end-algorithm-walkthrough.md`](../pillar-a/docs/end-to-end-algorithm-walkthrough.md)): `454.8 / 172.6 = 2.64×` → **ABNORMAL** for `Thu-09:00` on that entity. PoC stub: [`integration/join/harness.py`](../integration/join/harness.py) → `door_c_flags()` loads percentiles + baseline for one `(entity_id, metric_id)` and compares p95 to expected p95 — no graph import.

**What Detect can emit without edges.** A **`Signal`** roughly meaning:

> On **checkout-api**, **request.latency_ms** in this **5m** window is **2.6×** the seasonal p95 — class **SLOWDOWN**.

That is enough to **fire an anomaly**. It is **not** enough to **localize root cause** — and that is intentional. Detect is **per-CI, per-metric thresholding** (platform monitor on pre-aggregated sketches), not Smartscape traversal.

**Where edges enter the pipeline.**

```text
E4 Sketch writer  → history/   one row per entity × metric × window
E3 Topology       → map/       nodes + edges (relationships)

E6 Detect         → history/ only → Signal(s)
E7 Curate         → correlate / dedupe Signals → CaseSeed
E8 Scope          → first read-join: seed CI + map/ neighbors + history/ snippets → WorkingSet
E9 Localize       → walk map/ edges (depends_on, runs_on, …)
E10 Identify      → corroborate with more sketches on walked CIs
```

Visual read-path table: [`map-history-storage-blocks.html`](../../docs/fabric/map-history-storage-blocks.html).

Normative Scope walk knobs (hops, detect-class relation profiles, confidence filter): [`MAP_SCOPE_WALK_POLICY.md`](./MAP_SCOPE_WALK_POLICY.md).

**Lab-shaped example.** After flush, `history/sketches.jsonl` may contain:

- `checkout-api` · `request.latency_ms` · p95 well above seasonal expected → **fires**
- `payments-db` · `cpu.utilization_pct` · normal → **silent**
- `linux-server-app-01` · `cpu.utilization_pct` · may fire independently later

Each fires from **its own sketch row**. E7 Curate may group correlated Signals into one case. E8 Scope picks a seed CI, pulls **neighbors from `map/`**, and attaches **their** sketch snippets. E9 walks `depends_on` / `runs_on` to decide leaf vs upstream. None of that graph logic belongs inside E6.

**Why the split is deliberate.**

1. **Detect must stay cheap** — scan hot sketch rows, compare two numbers, emit Signal; no graph walk on every window for every CI×metric.
2. **Rooms stay independent** — sketches merge and age as time-series facts; topology is a slow-changing structure fact. Edges in sketches would duplicate `map/` and break the parallel-writer model (**G16**).
3. **Detect can fire on incomplete topology** — “checkout-api is slow” still fires even if `map/` is stale; Localize quality degrades, but firing does not block.

**One line:** **E6 Detect = “is this thermometer reading abnormal for this hour of the week?”** **E9 Localize = “given a hot thermometer, which rooms are connected on the floor plan?”** The thermometer (`sketch.v1`) has location id + reading; the floor plan (`GraphSnapshot`) has relationships. Detect uses the thermometer alone; RCA joins both at **E8+**.

See also **G42** — MELTS vs aggregated stream vs `sketch.v1` (three different layers).

### G42. MELTS vs aggregated stream vs `sketch.v1` — are sketches the same as “aggregated stream instead of MELTS”?

**A.** **No.** Those three names sit on **different axes**. MELTS is not replaced by aggregated stream; sketches are not the same as either — they are a **deeper, platform-side compression** of the **Metrics (M)** path into `history/`.

| Layer | What it answers | Where in the pipeline | Example in our docs |
|-------|-----------------|----------------------|---------------------|
| **MELTS** | What **modality** is this? (Metrics, Events, Logs, Traces, Spans) | Taxonomy at collect — not a pipeline stage | [`MELTS_MODALITY_IMPORTANCE.md`](../../docs/reference/MELTS_MODALITY_IMPORTANCE.md) |
| **Aggregated / shaped stream** | How much **raw volume** still ships after edge shaping? | Shift-left — Node / Gateway **before** central SaaS | Edge Delta: `parsed + tagged rows → aggregated stream → shaped MELT over TLS`; ObserveOps: **shaped stream** ([`observeops-shift-left-architecture.html`](../../docs/observeops/observeops-shift-left-architecture.html)) |
| **`sketch.v1` (`history/`)** | What **compact metric history** does E6 door C read? | **E4 Stores** — Pillar A after E2 Identity | T-Digest + buckets + seasonal baseline per `(entity_id, metric_id, window, season_key)` |

**MELTS stays inside an aggregated stream.** Edge shaping reduces volume; it does not abolish modalities. A shaped stream can still carry metrics, logs, spans, and events — just parsed, tagged, and often rolled up.

**Pipeline order (metrics path).**

```text
Sources (MELTS-shaped telemetry)
    ↓  shift-left (optional)
Shaped / aggregated stream     ← rollups, dedup, mask — still telemetry records
    ↓  E1 Collect
ingest.v1  (fact_kind: metric_sample | event | trace_span | topo_update | …)
    ↓  E2 Identity
    ├─► E3 Topology  → map/
    └─► E4 Sketch writer  → history/sketch.v1   ← second aggregation; metrics only
            ↓
        E6 Detect (door C): p95 vs seasonal baseline on sketch rows
```

**At E3/E4, writers use `fact_kind`, not MELTS letters** (**G31**). Pillar A admits `metric_sample` and builds sketches; Pillar B admits `topo_update`; other classes are skipped or routed to other store surfaces. PoC fixtures may still be **one sample per `metric_sample` line** — E4 **aggregates those samples into windowed sketch rows**; that is not the same object as the edge aggregated stream.

**Only the Metrics path becomes `sketch.v1`.** Events, logs, and traces do not land in sketch rows (non-metric lines are silent-skipped by Pillar A; schema forbids edge fields). Other modalities need other evidence surfaces (Lean bundle files, future execution graph, etc.) — out of the A/B freeze for topology + sketches (**GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md** §8).

**Two compounding levers (not competing strategies)** — **G37**:

| Lever | Where | Question it answers |
|-------|-------|---------------------|
| **Shift-left / aggregated stream** | Edge, before SaaS | “Should this much raw travel at all?” |
| **Pillar A sketch (E4)** | SaaS, after admit | “Once metric samples are here, do we keep raw or compress into `history/`?” |

Industry “warm tier aggregated rollups” (**G36**) is closer in *spirit* to sketches than edge aggregated stream is — but our **`sketch.v1`** is **quantile-native** (T-Digest + seasonal baseline for door C), not a generic multi-modality rollup table.

**One line:** **MELTS** = what you collect · **aggregated stream** = how much you ship early · **`sketch.v1`** = what Pillar A stores so E6 never rescans raw metric samples. See **G41** for why E6 reads sketches without graph edges.

### G26. Comparative objectives / inputs / outputs — digest, buckets, baseline, exemplars (§5)

| | **T-Digest** | **Buckets** | **Seasonal baseline** | **Exemplars** |
|--|--------------|-------------|------------------------|---------------|
| **Objective** | This window’s mergeable percentiles | This window’s fixed-bin counts | Usual percentiles for this `season_key` | Point from a hot bin to one request |
| **Inputs** | This window’s latency **values** | Same latency values | **Past** windows’ percentiles (same season) | This window’s events `(latency, trace_id)` |
| **Outputs** | Approx p50/p95/p99 | `bounds` + `counts` | `expected_p50/p95/p99` | `trace_id` on a bin |
| **Detect (door C)?** | **Yes** (current p95) | Optional / alternate | **Yes** (expected p95) | **No** |
| **After Detect?** | Corroboration | **Yes** (hot range) | Context | **Yes** (open trace) |

**One line:** digest + baseline → fire; buckets → where the mass is; exemplars → which request.

### G27. What is a heatmap here, and how do we use it?

**A.** A **heatmap** is a chart where **color = how much** on a grid (often time × latency bin). Buckets supply the counts; the heatmap is the **picture** of those counts over time so you see where mass sat after Detect fires. Useful for investigation and for UI dots that may carry exemplars. **Not** required to compute the p95-vs-season Detect ratio itself.

### G28. How is `season_key` computed? Do raw samples feed baseline and exemplars? (§5.1, walkthrough FAQ)

**A.**

- **`season_key`:** hour-of-week from a timezone-aware timestamp, e.g. `"Thu-09:00"` (`strftime('%a')` + floored hour). PoC: `HourOfWeekSeason`.
- **Baseline:** built from **past** windows with that key — **not** this incident window’s raw list. Current timestamp only chooses which baseline to attach.
- **Exemplars:** from **this** window’s identity-bearing events `(latency, trace_id)` — not from digest centroids, and not “Detect on a 1% metric sample.”

### G29. We initially planned no exemplars. Now they are optional — what value do they add *after* Detect? (§5.2.1)

**A.** Exemplars add **investigation speed**, not Detect capability.

| Stage | Needed for decision? | What exemplars add |
|------|-----------------------|--------------------|
| **Detect (door C)** — “is current p95 abnormal for this season?” | **No** | Detect still uses digest + baseline. Exemplars do not change fire/no-fire. |
| **After Detect** — “what request should I inspect first?” | **Yes, if available** | A concrete `trace_id` (or request id) tied to a hot bucket, so the operator pivots straight into one slow request instead of broad searching. |

**Why this matters in practice**

- Without exemplars: “latency is bad” → open traces/logs and hunt broadly.
- With exemplars: “latency is bad” + “start with these trace ids from the abnormal range.”
- Result: faster first actionable hypothesis, less triage drift.

**What exemplars do not replace**

- Not a substitute for digest (window percentile estimate),
- not a substitute for baseline (season expectation),
- not a substitute for buckets (range distribution).

**When optional exemplars are worth enabling first**

- high-traffic services where many traces exist per minute,
- teams that already debug by traces,
- repeated SLOWDOWN investigations where “which request?” is the bottleneck.

**When skipping exemplars is acceptable in v1**

- low-traffic services,
- sparse or expensive tracing,
- teams already resolving with metrics + topology + logs.

**One line:** keep exemplars optional in `sketch.v1`; treat them as **post-Detect acceleration**, not a Detect dependency.

---

## 8. Pillar A lab admit and false-positive filtering

### G30. Lab “3 latency + 2 CPU” vs “field mapping in admit” — two sub-jobs or one? (§5, PoC `metric_admit`)

**A.** **One job**, two ways to read the same admit step — not two pipeline stages or two teams.

| What you see | What it is |
|--------------|------------|
| “3 latency + 2 CPU metric lines” | **Which lab inputs** feed the single path: admit → window → digest + buckets → baseline → `sketch.v1` |
| “Field mapping in `admit_metric`” | **How each line’s fields** are read inside that same admit step (`ci_id` → `entity_id`, `name` → `metric_id`, gate on `identity.status`, …) |

Pillar A consumes **whole identified metric lines** (already stamped at E2). It does not split “timestamp goes to team A, identity goes to team B.”

**One line:** first table = example inputs; second table = field wiring — same admit job.

### G31. Why does the lab file mix metrics and `topo_update` lines? Does Pillar A reject topology? (§5.3, lab fixture)

**A.** The shared lab stream is a **mixed tape** for the whole A+B demo: metric samples **and** topology updates in one JSONL file.

| Line kind | Pillar A | Pillar B |
|-----------|----------|----------|
| `fact_kind: metric_sample` | Admit → sketch writer (`sketch.v1`) | **Silent skip (NOOP)** |
| `fact_kind: topo_update` | **Silent skip (NOOP)** — not a reject | Admit → graph builder (**WRITE** if catalog checks pass) |
| `event` / `trace_span` / `anomaly` | Silent skip (not `sketch.v1`) | **Silent skip (NOOP)** — case path / other stores |

Topology rows (`runs_on`, `depends_on`, …) are **not** sketch inputs and **never** become `sketch.v1` fields. “One file feeds both products” is **fixture packaging**, not a claim that sketches store edges. Full consumer map: [`E2_INPUT_FIXTURES.md`](../E2_INPUT_FIXTURES.md).

### G32. Where are false positives filtered — is it E5 Maintain? (§5.2.1, E6, E7)

**A.** **Not all at E5.** Different “false” things stop at different stages:

| Kind of junk / false alarm | Where it stops | Stage |
|----------------------------|----------------|-------|
| Unresolved / synthesized identity | Never enters a sketch | **Admit** on Pillar A write |
| Unknown metric / missing value | `SketchWriter.rejects` | **Admit** |
| Non-metric lines (topo, events) | Silent skip | **Admit** |
| Busy hour looks like an outage | Digest p95 vs **seasonal** baseline expected p95 | **E6 Detect (door C)** reads baseline that **E5 refreshes** |
| Duplicate / related signals after fire | Case merge | **E7 Curate** — not the sketch store |

**E5’s job:** refresh seasonal baselines (and graph validity/decay on the B side). It **prepares** the expected range Detect compares against; it does **not** sit after Detect deleting bad `Signal`s.

**One line:** admit filters input junk; E6 applies season-aware Detect; E5 keeps baselines honest; Curate cleans the case storm after fire.

---

## 9. Merge, raw retention, and Observability 3.0 shift-left

### G33. Why do we need to merge two sketches? (§5.2)

**A.** After Pillar A builds a sketch, **raw samples for that window are gone** (Motadata Observability 3.0 lean: compress then discard). Merging existing sketches is how you get a **coarser window** or **wider scope** later without a raw rescan.

When merge is the mechanism:

| Use | Example |
|-----|---------|
| **Multi-resolution rollups** | Twelve 1-minute digests → one 5-minute digest |
| **Fleet-wide aggregation** | Per-pod digests → one service-wide p95 |
| **Distributed shards** | Parallel partial digests → one global percentile |

**Underlying rule:** you **cannot average percentiles** and get a correct answer. The median of five medians is not the true combined median. Merge works because it recombines the **underlying weighted distributions** (T-Digest centroids), not the summary numbers.

**One line:** raw is gone → merge sketches; never average p95s.

Source exercise: [`Sketches_Merging_RawData_QnA.pdf`](../../docs/fabric/Sketches_Merging_RawData_QnA.pdf) Q1.

### G34. Why isn’t merging buckets as smooth as merging digests? (§5.2)

**A.** A T-Digest **centroid describes itself**. A bucket **count only means something if you already know the bin edges**.

| | **T-Digest** | **Buckets** |
|--|--------------|-------------|
| **Merge operation** | Pool centroids, re-compress | Add counts index-by-index |
| **Requires matching structure?** | No | **Yes** — bounds / `bucket_schema_version` must be identical |
| **If bounds differ** | Still merges correctly | **Silently wrong** — sums unrelated ranges under the same index |
| **If schema upgrades later** | Old + new digests can still merge | Old counts cannot be upgraded without raw |

**Concrete failure:** schema A bin 2 = `[100, 200)` ms; schema B bin 2 = `[100, 150)` ms. Adding those counts invents a fake range.

**Discipline, not a bug to “fix”:** digest mergeability is a property of the algorithm. Bucket “mergeability” only holds if you **never change `bucket_schema_version` under the same logical key**. Break that once → no way back without raw samples.

**Subtitle nuance:** buckets do not always “resist” merge — they merge fine when the schema is stable. They **require enforcement**, unlike digests.

**One line:** same `bucket_schema_version` + bounds, or do not add counts across versions.

Source: PDF Q2.

### G35. When do we still need to recompute from raw data? (§5, deep dive)

**A.** Sketches are **irreversible compression**. Anything the sketch did not keep is gone once raw is discarded.

| Scenario | Why the sketch cannot answer |
|----------|------------------------------|
| Bug in aggregation / wrong window / season | Every sketch built wrong; fix = rebuild from raw |
| Late identity resolution | Unresolved samples never entered the sketch; days-later bind cannot resurrect them |
| Brand-new metric | Nothing sketched that metric at write time — no backfill from digests |
| Forensic / compliance / legal | Need exact value at exact timestamp, not a percentile estimate |
| ML training / new algorithm backtesting | Features nobody pre-aggregated |
| Drill-down beyond one exemplar | Exemplar = one request per bin; all requests in a hot bin need events |

**Product tension:** Observability 3.0 Detect/RCA can treat **hot = sketch**. The cases above only work if Motadata either keeps a **short raw buffer**, or **explicitly accepts those scenarios fail**. The sit-down should name which rows stay in scope (brief open questions).

**One line:** sketches are enough for season-aware Detect; they are not a time machine for every possible later question.

Source: PDF Q3.

### G36. What is standard industry practice for keeping raw data?

**A.** Most observability platforms converge on **tiered retention** (context for Motadata, not our freeze by itself):

| Tier | What’s kept | Typical window | Why |
|------|-------------|----------------|-----|
| **Hot / raw** | Full-fidelity samples | Metrics ~15 days; logs 7–30 days; traces hours–few days | Expensive at full resolution |
| **Warm / downsampled** | Aggregated rollups | Metrics ~13–15 months; logs 30–90 days searchable | Trends / capacity |
| **Cold / archived** | Compressed, often not indexed | Months–years (compliance) | Legal/audit |
| **Deleted** | Nothing | After retention | Cost + privacy |

Traces are usually shortest-lived at full fidelity (volume → sample at ingest).

Motadata Observability 3.0 (G37) can be **more aggressive** than this table for the **operational Detect path** — hot query tier = sketch — while still optionally buffering raw for selected cases in G35.

Source: PDF Q4.

### G37. Do merge / raw rules change under Observability 3.0 shift-left? (§6)

**A.** **Same goals (cost + noise), two different levers** — they **compound**, they are not competing retention strategies.

| Lever | Where it acts | What it reduces | Mechanism | Question it answers |
|-------|---------------|-----------------|-----------|---------------------|
| **Shift-left** | Edge (Node, optional Gateway) — before centralizing | **Volume** — how much raw is collected/sent | Mask, Drain/templating, filter at source | “Should this data travel to SaaS at all?” |
| **Pillar A sketch retention** | SaaS center — after admit | **Lifespan** — how long admitted raw stays raw | Build sketch, discard sample | “Now that it’s here, do we still need the raw copy?” |

**Three-stage funnel** (each stage discards more):

1. **Node / Gateway (shift-left)** — reduce volume before egress.  
2. **SaaS admission (E1/E2)** — only resolved-identity, cataloged numeric samples past the gate.  
3. **Pillar A sketch writer (E4)** — compress into T-Digest / buckets / baseline; discard raw **metric samples** for the Detect path. Hot analytical tier = **sketch on Vortex**, not a raw sample lake. **Late identity (Case 2)** is a separate, bounded quarantine at **Identity (E2)** → replay → merge into sketches — not “Pillar A keeps a raw lake,” and not Edge Delta full rehydration by default (see discussion [`04-raw-data-identity-lut-open-questions.md`](../discussion/04-raw-data-identity-lut-open-questions.md)).

**Not a contradiction:** a short Fluent Bit–style **disk buffer** at the edge is **delivery resilience** (survive blips; minutes–hours; not meant for Detect queries). That is not the same as industry “hot raw retention” for RCA.

**One line:** shift-left = send less; Pillar A = keep raw less long; Detect reads sketches; unresolved bind uses a narrow Identity quarantine, not a second sketch schema.

Source: PDF Q5. Aligns with deep dive §7.3–7.4 (cold S3 sketches + hot Vortex).

---

## Maintenance

- **New clarifications** — append a new `G#` at the **end of the matching section** (or add a section if the theme is new). Keep section flow coherent; do not dump unsorted bullets at the file bottom.
- **Open decisions** stay in the discussion brief (§10), not this Q&A.
