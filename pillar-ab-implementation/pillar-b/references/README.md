# Pillar B — product references (OneOps / Fusion SaaS)

**Optional library — not required to run or evaluate the Pillar B PoC.** Cold readers start at [`../README.md`](../README.md) / [`../docs/README.md`](../docs/README.md), not here.

**What this folder is:** Motadata leadership HTML briefs about the **Service-Centric Knowledge Graph** (configuration-item catalog + relationship vocabulary) and how that model compares to enterprise CMDB incumbents (ServiceNow, BMC Helix, OpenText UCMDB). Also Edge Delta → Motadata comparator notes.

**What this folder is not:** The live Pillar B **implementation source of truth**. Wire shapes, PoC dest keys, and the locked sit-down enum live under the **slice** [`../../contracts/`](../../contracts/). Lab code and fixtures live under [`../poc/`](../poc/). Package `contracts/` holds **schema symlinks only**.

**How to open the HTML:** Prefer a small local server (pages are large and interactive):

```bash
cd pillar-ab-implementation/pillar-b/references
python3 -m http.server 8771
# → http://127.0.0.1:8771/
```

Filenames may still include a trailing ` 1` from download; treat that as cosmetic.

---

## Files at a glance

| File | One-line job | Audience |
|------|--------------|----------|
| [`ED-MD-New.md`](./ED-MD-New.md) | **Primary** Edge Delta → Motadata comparator (restructured Parts A–G + diagrams) | Engineers comparing ED to ObserveOps |
| [`ED to MD Mapping.md`](./ED%20to%20MD%20Mapping.md) | **Earlier draft** — prefer `ED-MD-New.md`; kept as research notes / hub diagram companion | Archive / cross-check only |
| [`fusion-saas-cmdb-philosophy-vs-incumbents 1.html`](./fusion-saas-cmdb-philosophy-vs-incumbents%201.html) | Why ServiceNow / BMC / UCMDB relationship models hurt, and the Fusion philosophy instead | Product / leadership |
| [`oneops-ci-ontology 1.html`](./oneops-ci-ontology%201.html) | Frozen **v0.1** OneOps CI ontology — classes, eleven stored edges, write-time allowlist, launch gates | Product + architecture |
| [`fusion-saas-skg-edge-spec 1.html`](./fusion-saas-skg-edge-spec%201.html) | Technical **edge specification** — eleven ground-truth stored relations + four computed at query time | Engineers locking vocabulary |
| [`fusion-saas-skg-edge-validation 1.html`](./fusion-saas-skg-edge-validation%201.html) | Same fifteen edges **cross-checked** against incumbent CMDB catalogs; wins, gaps, v0.2 ideas | Engineers validating coverage |
| [`oneops-ci-class-mapping.html`](./oneops-ci-class-mapping.html) | Tables: **our CI classes** vs ServiceNow’s large class list | Implementers mapping inventory |

Suggested reading order: **philosophy → ontology → edge spec → edge validation → class mapping**.

---

## What each file does

### 1. `fusion-saas-cmdb-philosophy-vs-incumbents 1.html`

**Title:** Fusion SaaS · CMDB Philosophy Compared to the Incumbents · Motadata

Explains, in plain English:

- What a CMDB is supposed to do (blast radius, change risk, cost attribution).
- How ServiceNow, BMC Helix, and OpenText UCMDB each model relationships differently, and what that costs operators.
- The Fusion design stance: a **small clean graph**, evidence on edges, and anti-patterns drawn from twenty years of CMDB pain.
- The same **eleven stored + four computed** edge story as the edge spec, without the schema deep dive.

Use this when you need the **why**, not the enum table.

### 2. `oneops-ci-ontology 1.html`

**Title:** The OneOps CI Ontology · v0.1 · Motadata

The broader **product contract** for “what an enterprise runs”:

- Problem / market / thesis for OneOps.
- A frozen **v0.1** model: on the order of **thirty-seven concrete classes** (plus abstract parents), **eleven stored** relationship types, and a **write-time allowlist** that rejects illegal class–relation combinations.
- Architecture risks, launch criteria, churn risks, and appendices (version register, cross-platform alignment).

Use this when you need the **full ontology story** (classes + edges + product gates) in one place.

### 3. `fusion-saas-skg-edge-spec 1.html`

**Title:** Fusion SaaS · SKG Edge Specification · Motadata

The **relationship vocabulary** as a technical spec:

- **Eleven stored edges** (ground truth the map can persist), including names such as `composedOf`, `contains`, `runsOn`, `dependsOn`, `communicatesWith`, `realizes`, `memberOf`, `manages`, `ownedBy`, `locatedIn`, `succeedsLifecycleOf`.
- **Four computed edges** (operational truth at query time, not durable map rows): `impactedBy`, `reaches`, `sharesFailureDomain`, `criticalPath`.
- Shared edge metadata (for example confidence / evidence) and a **triplet** allowlist idea (which class pairs may carry which relation).

Use this when locking **which arrows exist** in the product SKG.

### 4. `fusion-saas-skg-edge-validation 1.html`

**Title:** Fusion SaaS · SKG Edge Cross-Validation · Motadata

Companion to the edge spec. For each of the fifteen Fusion edges it asks: **where does this live** in ServiceNow `cmdb_rel_type`, BMC Helix CDM, and UCMDB UDM?

- Argues that a **smaller typed set** can still cover incumbent concepts when semantics, evidence, and traversal are separated.
- Lists where Fusion wins and where **v0.2** should harden (gaps vs incumbents).
- Records what is **not** recommended for v0.2.

Use this when someone asks “are eleven edges enough?” with evidence.

### 5. `oneops-ci-class-mapping.html`

**Title:** CI Classes · Ours, ServiceNow's, and the Map · Motadata

Three large tables:

1. **Our** CI classes (on the order of sixty in this pack).
2. ServiceNow’s much larger CI class inventory.
3. **Which of theirs lands on which of ours.**

Use this for **inventory / CMDB import mapping**, not for Pillar B PoC flush keys.

---

## Shared model across these HTMLs

Across the Fusion / OneOps pack, the product story is consistent:

| Kind | Count | Role |
|------|-------|------|
| Stored edges | **Eleven** | Durable map facts (ground truth) |
| Computed edges | **Four** | Blast radius, reachability, failure domain, critical path — derived when asking, not stored as ordinary topology rows |
| CI classes | Ontology ~**37+** concrete; mapping table ~**62** | What may appear as a configuration-item vertex |

That design agrees with our ObserveOps / Pillar B teaching on one important point: **blast radius and case correlations are not the same job as durable CI–CI topology.** Curate / Package relationship words stay off the map room.

---

## Relation to Pillar B contracts (do not conflate)

| Topic | This `references/` folder | Canonical for the PoC / sit-down |
|--------|---------------------------|----------------------------------|
| Edge names | camelCase product names (11 stored + 4 computed) | snake_case **fifteen** storage enum in [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) §4.2 |
| Node / edge samples | Not here | [`GRAPH_NODE_EDGE_SAMPLES.md`](../../contracts/GRAPH_NODE_EDGE_SAMPLES.md) |
| Fabric rules FAQ | Not here | [`GRAPH_QNA.md`](../../contracts/GRAPH_QNA.md) |
| What GraphWriter writes under `map/` | Not here | [`MAP_WRITE_READ_RECORD.md`](../../contracts/MAP_WRITE_READ_RECORD.md) |
| Dest profile | Not here | [`GATE_B_DEST_PROFILE.md`](../../contracts/GATE_B_DEST_PROFILE.md) |
| Reject codes | Not here | [`IDENTIFIED_STREAM_REJECT.md`](../../contracts/IDENTIFIED_STREAM_REJECT.md) |
| Lab input after Identity | Not here | [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md) |

Until product and implementers **explicitly reconcile** the Fusion/OneOps vocabulary with the GRAPH_CONTRACT enum, treat these HTMLs as **upstream product reference** and the `contracts/` tree as what Pillar B code and fixtures follow today.

Package overview: [`../README.md`](../README.md).
