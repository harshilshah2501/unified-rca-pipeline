# ObserveOps HLD — Stages, Signals, and the Operational Graph

**Status:** Draft for review — 9 open questions resolved 2026-08-17, see §7
**Version:** v0.2
**Date:** 2026-08-17
**Chapter of:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) (Pipeline HLD — Approved for build). This file is **not** a second HLD.
**Hub:** [Our HLD](./observeops-pipeline-hld.html) · interactive [`observeops-fusion-guide.html`](./observeops-fusion-guide.html) · [`observeops-ci-graph.html`](./observeops-ci-graph.html) · [`OBSERVEOPS_USE_CASES.md`](./OBSERVEOPS_USE_CASES.md)
**Source dump:** [`Pratik-docs/`](./Pratik-docs/) (original filenames; this copy is the stable URL)
**Scope (in):** per-use-case stage behaviour for the initial 8-use-case catalog; the operational-graph schema, its construction, and its consumption across E1–E11
**Scope (out):** LLD schemas, collector implementation, remediation, Layer I productization, storage-engine selection

---

## 0. How to read this chapter

This file is **not a second HLD**. There is one written spec: the [Pipeline HLD](./OBSERVEOPS_PIPELINE_HLD.md). This chapter is extra detail on the **map** those eleven steps walk — who is connected to whom, how we know a connection is real, and how Detect through Package use that map.

[Our HLD](./observeops-pipeline-hld.html) is the door. [Fusion](./observeops-fusion-guide.html) is the same pipeline, clickable.

| Surface | What it is |
|---|---|
| [Fusion](./observeops-fusion-guide.html) | The eleven steps, clickable. Pick a use case. |
| **This chapter** | How the map is recorded and used, including per-use-case rows for E6–E11 |
| [Example map](./observeops-ci-graph.html) | 33 CIs / 40 connections we drew. Live E3 does not emit this yet. |
| [Pipeline HLD](./OBSERVEOPS_PIPELINE_HLD.md) | What each step is for, and which design choices are signed. If this chapter disagrees on a step’s job, **that file wins**. |

Fusion tabs map onto this chapter (same numbers, same Detect classes — Fusion does not invent a parallel catalog):

| Fusion tab | This chapter | Open Fusion when you want… |
|---|---|---|
| Use Cases | §2.3 catalog + the eight rows in §5 | to pick a UC and see it as a card before reading tables |
| Pipeline & Graph | §4 (E1–E5, same job for every UC) · §5 (E6–E11 per UC) | to walk one UC through what each step takes in and puts out |
| Graph Explained | §3 (node / edge / identity / signatures) | the plain-language walk of how a connection is recorded |
| POC Roadmap | Lab sequencing only — **not** this chapter’s schema | a build order |

Fusion does **not** add steps. If Fusion and this chapter disagree on what a step is *for*, **the Pipeline HLD wins**. If they disagree on map shape or a per-UC E6–E11 row, **this chapter wins**.

Suggested order: Fusion → Pipeline HLD. Open this chapter only if you need how a connection is recorded.

---

## 1. Purpose and lineage

This document **extends and operationalizes** the [Pipeline HLD](./OBSERVEOPS_PIPELINE_HLD.md). It does **not** replace it, and it does not propose a new pipeline shape.

The 11 stages (E1–E11), their order, their purposes, their output objects, and the three-phase partition (P1/P2/P3) are all **unchanged and locked**. Anyone reading this document who finds a discrepancy with the Pipeline HLD should treat the Pipeline HLD as authoritative on stage semantics and treat this document as authoritative only on the two things it adds:

1. **Per-use-case detail** — what concretely happens at E6–E11 for each of the 8 approved initial use cases, with real signal names rather than placeholders.
2. **Operational-graph detail** — the schema of the CI/topology dependency graph, how E3 builds it from telemetry, and how every downstream stage consumes it.

The second point is the centre of gravity here. The graph is not a supporting subsystem in this architecture; it is the thing that makes localization defensible. A detector that fires without a graph produces an alert. A detector that fires *with* a graph — a graph that can say which entity sits beneath the symptom, why we believe that edge exists, and how strong that belief is — produces a root cause. **The operational graph is the moat.** Section 3 is written accordingly and is the longest section in this document.

### 1.1 What is new versus the Pipeline HLD

| Area | Pipeline HLD says | This document adds |
|---|---|---|
| Stage catalog | 11 formal contracts, one per stage | Per-use-case IN/OUT for the 6 case-time stages (E6–E11) |
| Detect classes | 5 classes with leaf rules and evidence maturity | Mapping of all 8 use cases onto those 5 classes, incl. the sub-signature problem |
| E3 Topology | "maintain walkable dependency graph"; `GraphSnapshot`; D1 Signed | Full node/edge/identity/index/derivation/fault-signature schema and per-stage consumption model |
| Graph freshness | "freshness window and bounded staleness (no numeric target yet)" | Per-edge `refresh` cadence carried on the edge itself; decay as an E5 responsibility; **7d soft-stale / 30d hard-downgrade for `declared` edges, resolved §7 #4** |

---

## 2. Vocabulary and invariants

### 2.1 Three invariants that must not drift

These are restatements of Pipeline HLD §5. They are repeated here because they are the three things readers most often get wrong when moving between our internal vocabulary and vendor-teaching material.

**Invariant 1 — "Ingest" is a phase, not a stage.**
When a product doc or a roadmap says "Ingest is partial", that is a rollup over five independent stages: E1 Collect, E2 Identity, E3 Topology, E4 Stores, E5 Maintain. Those five sit at different readiness levels and are allowed to. E1 and E2 have closed LLDs; E5 has no dedicated lab at all. Never read a single Ingest status as uniform readiness across P1.

**Invariant 2 — "Normalize" is E2 Identity, and it is early.**
Vendor-teaching material (and our own DT/DD hubs) uses `Collect → Normalize` as the opening pair. That Normalize stage is this pipeline's **E2 Identity**, sitting second in P1. It is not a twelfth stage, and it is emphatically not E10 Identify. The name collision between "Normalize/Identity" (E2, early, stamps `tenant`+`ci_id`) and "Identify" (E10, late, corroborates the leaf) is the single highest-frequency reader error in this corpus.

E2 is also an **overlay, not a schema rewrite**. The identity pass annotates the record with `identity.*` fields; the raw payload survives intact. This late-binding property is what lets a record be re-bound later when the graph improves, without having destroyed the original.

**Invariant 3 — "Verify" has no dedicated stage, by design.**
There is no `E-Verify`. Verification is the confidence judgment — evidentiary tier, CARE, scoped causal check — made *inside* E10 Identify while the `EvidenceBundle` is assembled, and locked when E11 Package renders the `VerdictCard`. Looking for a Verify stage in the stage list is looking for something that was deliberately not built.

### 2.2 Evidence-maturity legend (reused verbatim from Pipeline HLD §9.1)

Every claim in this document that goes beyond what the repo has already proven carries one of these four tags. This applies to the new per-use-case rows in §5 exactly as it applies to the stage contracts in Pipeline HLD §8.

| Tag | Meaning |
|---|---|
| **Grounded** | Vendor MCP/API pull or bakeoff scoreboard backs the claim; reproducible via a cited run |
| **Local-only** | Break/heal script run and timestamped in this team's lab, but no vendor MCP/API confirmation yet |
| **Design-level** | Specified from architectural necessity; no lab exercises it directly |
| **Planned** | Named in a backlog, not yet run |

A **Local-only** tag is not a weaker way of saying Grounded. The gap is intentional and is documented at source.

**One additional honesty note specific to this document.** The operational-graph schema described in §3 is Grounded *as an artifact* — it exists, fully populated, in this repo ([`linux-server-ci-telemetry.json`](./linux-server-ci-telemetry.json), 33 CIs / 40 edges / 228 telemetry keys / 125 fault signatures). But that artifact was **authored**, not emitted by a running E3. The claim "E3 discovers these edges live from the telemetry stream at the stated refresh cadence" is **Design-level**. Do not conflate the two. The schema is proven; the pipeline that produces it continuously is specified.

### 2.3 The 8 use cases are not all peers — say so plainly

The initial catalog has 8 entries. E6 Detect has 5 classification buckets. These numbers do not reconcile by accident, and the document should not pretend they do. Walk the same eight on Fusion → **Use Cases**. They are **not** Edge Delta’s 10 AI Team jobs (ObserveOps UC-8 = host network saturation; ED UC8 = K8s troubleshooting).

**Use cases 1–5 sit at Detect-class granularity.** Each one maps 1:1 onto an E6 bucket:

| # | Use case | Detect class |
|---|---|---|
| 1 | Error rate increase on a service | `ERROR` |
| 2 | Response time / latency slowdown | `SLOWDOWN` |
| 3 | Resource contention (CPU / memory / disk) | `RESOURCE_CONTENTION` |
| 4 | Availability — service or host down | `AVAILABILITY` |
| 5 | Monitoring / telemetry pipeline unavailable | `MONITORING_UNAVAILABLE` |

**Use cases 6–8 are finer-grained fault signatures, not classes.** All three classify as `RESOURCE_CONTENTION` at E6:

| # | Use case | Detect class | Distinguished starting at |
|---|---|---|---|
| 6 | Disk latency high on host | `RESOURCE_CONTENTION` (host-tier sub-signature) | E9 / E10 |
| 7 | Disk storage / usage increase | `RESOURCE_CONTENTION` (host-tier sub-signature) | E9 / E10 |
| 8 | Network traffic sent/received high on host | `RESOURCE_CONTENTION` (host-tier sub-signature) | E9 / E10 |

This grouping is not a simplification we invented; it matches how the vendors themselves bucket host-tier saturation — Datadog's default host monitor pack groups CPU, disk, memory and network together under a single `monitor_pack:host`.

The practical consequence is precise and worth stating twice: **E6 cannot tell use cases 3, 6, 7 and 8 apart.** All four raise a `RESOURCE_CONTENTION` `Signal`. They diverge at **E9 Localize**, where the specific triggering metric selects a different contended entity, and at **E10 Identify**, where the specific triggering metric becomes part of the evidence and selects a different fault signature from the graph. A design that tries to force four separate Detect classes here would be inventing taxonomy that neither our labs nor the vendors support.

Two of these sub-signatures also carry documented **escalation paths** across class boundaries, which E10 must be able to represent:

- **#7 disk usage → `AVAILABILITY`.** A filesystem reaching 100% produces write failures. `system.filesystem.usage` saturating is a contention symptom; `Remounting filesystem read-only` / `No space left on device` in the log stream is the moment it becomes an availability fault.
- **#8 network throughput → `SLOWDOWN` or `AVAILABILITY`.** Saturated links produce timeouts (slowdown) before they produce packet loss and link-down (availability).

---

## 3. The operational graph — the moat

Plain-language companion: Fusion → **Graph Explained** (Overview / Schema Reference / Gaps). This section is normative.

### 3.1 What it is, and what makes it different

The operational graph is a continuously-maintained, typed, directed dependency graph of configuration items, built from the same telemetry stream that feeds detection — not imported from a CMDB on a nightly batch. E3 Topology owns it. Every stage from E6 onward reads it.

Most observability vendors ship a topology map. The differentiator here is not that we have a graph; it is **what each edge carries**. Every relationship in this schema records *how it was discovered, from which signal, with what directional reasoning, and at what strength*. An edge is not an assertion — it is an assertion **plus its provenance**.

This matters commercially and technically for the same reason:

- A vendor topology map says `app-runtime-jvm → postgresql-db`. When localization is wrong, the operator has no way to interrogate why the graph believed that.
- This schema says `app-runtime-jvm -[uses]-> postgresql-db`, discovered via `distributed-trace/db-client`, on fields `db.system` / `server.address` / `server.port` / `peer.service`, direction inferred client→server, evidence type **corroborating**, confidence **medium**, refreshed on trace arrival. When localization is wrong, the operator can see that this edge was inferred from traces rather than read from an authoritative inventory, and can weigh the verdict accordingly.

**That per-edge provenance is the moat.** It is the difference between a graph that asserts and a graph that can be audited. It is also what makes the confidence number on a `VerdictCard` mean something instead of being a decorative percentage.

The corollary is a product requirement, not an implementation detail: **`evidence_type` must be visible in the UI and the API, per edge.** A graph is only as trustworthy as its weakest edge, and the operator is entitled to see which edge that is. In the reference worked example the split is 18 `authoritative` / 3 `declared` / 19 `corroborating` across 40 edges — meaning roughly half the graph is inference. Hiding that would be dishonest; surfacing it is the feature.

### 3.2 Portability — schema is the deliverable, not the CI list

This platform is a multi-tenant observability SaaS. Tenants run VMware, AWS, Kubernetes, bare metal, and combinations nobody planned for. The graph schema must therefore be **CI-taxonomy-agnostic**.

The reference worked example in this repo ([`observeops-ci-graph.html`](./observeops-ci-graph.html) / [`linux-server-ci-telemetry.json`](./linux-server-ci-telemetry.json)) instantiates the schema over a VMware + Linux estate: 33 CIs spanning hypervisor, storage fabric, network, OS, middleware, data and business-service tiers. **That CI list is an illustration, not the target.** What ships is the schema; what varies per tenant is the population.

Throughout this section, concrete names from the worked example appear as *examples of shape*, never as required entities.

### 3.3 The six load-bearing structures

#### 3.3.1 Node model — what a CI is

Every node carries:

```
ci_id, ci_name, ci_type, ci_class, tier, instance_scope,
monitored_via, kpi_catalog_ref, identity, telemetry, rca
```

`tier` is a taxonomy of architectural layers and is the portable part. The worked example uses 12 tiers — `business_service, technical_service, middleware, runtime, data, container_platform, os, virtualization, storage, network, identity_security, external_dependency`. For a cloud-native tenant the same idea projects onto a different ladder: `business_service → technical_service → compute/container → managed_data_service → network → identity`. The tier *names* are tenant-shaped; the tier *concept* — an ordered stack that localization can descend — is universal and is what E9 depends on.

`instance_scope` (`single` vs `multi-instance`) is the field that makes host-tier use cases tractable. A filesystem, an iSCSI LUN, an NFS mount, a TLS certificate and a JVM instance are all multi-instance: there are many per host, and telemetry must resolve to the right one. This is why use case #6 (disk latency, per-device) and #7 (disk usage, per-mountpoint) cannot be answered at host granularity alone.

`monitored_via` is an explicit list of how this CI is observed (`agent (/proc & /sys)`, `SSH`, `SNMP`, `vCenter API`, `service map (top-down discovery)`, …). It is the field that tells E6 whether a negative detect is meaningful or merely uninstrumented.

##### Signal-class applicability — declare the absence

Each node carries all **13 telemetry signal classes** — a deliberate superset of MELT:

`availability · performance · logs · traces · flows_packets · events · synthetic · config_topology · change_deployment · profiles · security_posture · rum · hardware_sensors`

Each class is marked `applicable: true|false` per CI, and **when false it carries a stated reason**. Example from the worked example: `linux-server` marks `rum` as `applicable: false, reason: "not a user-facing CI"`.

This is a pattern E4 Stores should follow directly, and it is more important than it looks. Knowing that a CI *does not emit* a signal class — and why — is what separates "we have no trace data for this entity because it is a SAN switch" from "we have no trace data for this entity because we are blind". The first is a fact; the second is use case #5. A schema that silently omits inapplicable classes cannot tell them apart.

#### 3.3.2 Edge model — typed relationships with provenance

The worked example carries **15 edge types**:

`depends_on · runs_on · mounts · connects_to · backs · uses · hosted_on · member_of · part_of · routes_through · authenticates_via · monitored_by · backed_up_by · clustered_with · communicates_with`

Every edge carries a `discovered_via` provenance block:

| Field | Purpose | Example value |
|---|---|---|
| `telemetry_source` | Which stream produced this edge | `lldp/cdp-neighbor + arp` |
| `signal_fields` | Exact fields matched | `lldpRemSysName`, `lldpLocPortId`, `cdpCacheDeviceId` |
| `endpoint_binding` | How each end resolved to a CI | `host.name -> linux-server` / `host.id -> linux-vm` |
| `direction_inference` | Why the arrow points this way | `software -> from, host -> to` |
| `evidence_type` | `authoritative` \| `declared` \| `corroborating` | `authoritative` |
| `confidence` | `high` \| `medium` \| `low` \| `n/a` | `high` |
| `refresh` | Re-derivation cadence | `poll 5m` |

Plus `criticality` (`critical`/`high`/`medium`/`low`), and where applicable `weight` and `redundancy` (e.g. active-passive).

The three evidence types are not a gradient of quality so much as three different epistemic sources, and they behave differently under failure:

- **`authoritative`** — read from a system that *owns* the fact. Hypervisor inventory knows which VM is on which host. A mount table knows what is mounted. `linux-server -[runs_on]-> linux-vm` (agent/process-inventory/cgroup) and `vmfs-datastore -[depends_on]-> san-storage-array` (multipath/scsi-inventory) are authoritative. These edges are stable and safe to walk without corroboration.
- **`declared`** — asserted by inventory or CMDB with no telemetry backing. `esxi-host -[member_of]-> vsphere-cluster` carries `confidence: n/a` precisely because nothing observed it; something declared it. These edges are the ones that go stale silently.
- **`corroborating`** — inferred from observed behaviour. `app-runtime-jvm -[uses]-> postgresql-db` from distributed traces, `linux-server -[depends_on]-> dns-service` from resolver config and DNS query logs, `linux-server -[routes_through]-> firewall` from routing table and flow. These are the edges that make the graph rich and the edges that most need their provenance shown, because they are inferred from a sample of behaviour and can be wrong at the margins.

**Design-level note:** the ranking rule "prefer `authoritative` edges when walking, and degrade confidence when a localization path traverses a `corroborating` or `declared` edge" is architecturally implied by this schema but is not yet implemented or lab-validated. It should be an explicit E9 ranking input.

#### 3.3.3 Identity model — resolve to exactly one CI, or to nothing

Every node carries an `identity` block with ordered `match_rules`. The principle is stated in the schema itself:

> Resolve every telemetry payload to exactly one CI via ordered `match_rules`; instance keys require their host (`scope_parent`) to resolve first.

Supported match strategies: `exact · normalized · regex · cidr · range · composite · hierarchical`.
Supported scope levels: `host · interface · filesystem · disk · cpu · process · service · instance · endpoint`.
Resolution order: highest-priority matching rule wins; ties broken by scope specificity, then confidence.
Normalization rules are explicit: `host.name → lowercase, strip domain`; MAC → lowercase colon-separated; IP → canonical.

A rule looks like this (from `linux-server`, priority 0):

```
telemetry_key: host.name  ·  maps_to_ci_attribute: hostname
match_strategy: normalized  ·  scope: host  ·  priority: 0
confidence: high  ·  normalization: "lowercase, strip domain"
resolves_to: linux-server
```

**The ambiguity policy is the invariant that matters:**

> If more than one CI matches, or none does, emit to an **unresolved bucket** keyed by raw attributes. **Never silently mis-attach.**

The fallback hierarchy is ordered and explicit: `exact id → normalized host → cidr/subnet → network segment CI → tag → service CI → unresolved bucket`.

This is the same invariant E2 Identity already states in the Pipeline HLD ("unresolved records move to unattributed queue; they are never silently dropped"; `identity.status != resolved` is not a localize target and not a ServiceOps-ticket target, per D-E2-1). The graph schema and the pipeline agree here, which is the point — one identity thread, two documents, no divergence.

#### 3.3.4 Telemetry key index — one lookup, one CI

A flat reverse index over every telemetry key the estate can emit. The worked example carries **228 entries**, split 188 host-scoped / 40 instance-scoped. Each entry:

```
telemetry_key → signal_class, scope, binding_keys, instance_key,
                resolves_to_ci, scope_parent_via, match_strategy, confidence
```

Two real entries, showing the host/instance split:

| `telemetry_key` | scope | `binding_keys` | `resolves_to_ci` | `scope_parent_via` | strategy |
|---|---|---|---|---|---|
| `system.cpu.utilization` | host | `host.name` | `linux-server` | — | normalized |
| `system.disk.io.latency` | instance | `host.name`, `<instance_key>` | `linux-server` | `host.name` | composite |

This index is the mechanism that makes E2's in-stream `ci_id` stamping viable at ingest volume. Without it, binding a datapoint means evaluating match rules across the CI population; with it, binding is a single hash lookup plus (for instance-scoped keys) a parent resolution. The 188/40 split is itself informative: most keys bind at host scope in one hop, and the instance-scoped minority is exactly where the composite two-step is needed — and exactly where use cases 6 and 7 live.

#### 3.3.5 Root-relationship derivation — how E3 finds edges without a CMDB

For each potential relationship, the schema carries a **ranked list of derivation methods**, each tagged with source, field, layer, confidence, evidence type and rank. The method legend:

`host routing table · host ARP/neighbor · LLDP/CDP · switch CAM/MAC (SNMP) · traceroute · NetFlow/IPFIX · mount/iscsi tables · socket/conntrack peer · hypervisor inventory · resolver/NTP/DHCP/auth config · service logs · distributed trace`

A worked entry — deriving `nginx-web-server -[runs_on]-> linux-server`:

| Rank | Method | Source | Field | Gives | Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Host process/cgroup inventory | `ps`, `systemd-cgls`, container runtime | process/unit/container → workload identity | workloads running ON this host | os | high | authoritative |
| 2 | Listening-socket owner | `ss -tanp` | LISTEN port → owning process | service bound on the host | L4 | high | authoritative |

Each related CI also carries `hop`, `directness` (`direct`/`indirect`), `direction` (`upstream`/`downstream`) and `role` (e.g. `blast-radius / dependent`), so multi-hop paths are addressable with their path recorded rather than recomputed.

This structure is what makes **discovery-first** a real architectural position rather than a slogan. CMDB remains optional enrichment (Pipeline HLD §4, D1 Signed: "hybrid, derived edges first, typed IDs when cheap"). The ranked-methods table is the operational content of that decision — it says exactly which observation to try first, and what to fall back to.

#### 3.3.6 Fault signatures — the E9/E10 fuel

Every node carries an `rca` block:

```
is_root_cause_candidate : bool
blast_radius_impact     : high | medium | low
primary_health_signal   : telemetry_key
fault_signatures[]      : { symptom,
                            symptom_signals[],
                            likely_root_cause_ci,
                            confirm_with_signals[],
                            correlate_upstream[],
                            blast_radius_downstream[] }
```

The worked example carries **125 pre-named signatures** spanning the full stack — from `CPU ready / co-stop (host contention)`, `memory ballooning / swap`, `datastore latency spike`, `APD/PDL (all-paths-down)`, `port CRC errors / SFP degradation` at the infrastructure tiers, through `OOM-kill`, `inode exhaustion`, `remount read-only on error` at the OS tier, `connection pool exhaustion`, `checkpoint I/O storm`, `GC pause / heap exhaustion` at data and runtime tiers, `NotReady node` and `CNI failure` at the container platform, up to `aggregate 5xx breach`, `latency SLO breach` and `error-budget exhaustion` at the technical- and business-service tiers.

This is the structure that turns a graph walk into a diagnosis:

- **`correlate_upstream[]` → root-cause candidates.** These are the entities to interrogate when this symptom appears here.
- **`blast_radius_downstream[]` → impact radius.** These are the entities to expect collateral symptoms on, and the ones E11 reports as impact.
- **`confirm_with_signals[]` → the corroboration list.** This is E10's shopping list, pre-computed.

A concrete signature, from `linux-server`:

```
symptom               : "memory exhaustion / OOM-kill"
symptom_signals       : system.disk.io.latency, system.network.io
likely_root_cause_ci  : linux-server
confirm_with_signals  : system.cpu.utilization, system.memory.usage, system.load.1m
correlate_upstream    : linux-vm, iscsi-lun, nfs-share, access-switch, … (14 CIs)
blast_radius_downstream: app-runtime-jvm, nginx-web-server, postgresql-db,
                         container-runtime, local-filesystem, cluster-vip
```

Paired with the log pattern catalog on the same node — `Out of memory: Killed process (\d+)` tagged `event_type: oom_kill`, `indicates_failure_mode: "memory exhaustion / OOM-kill"`, `maps_to_ci_via: host.name + process.pid` — the signature and the log pattern join on the failure-mode string. That join is how E10 corroborates a metric-derived leaf with log evidence without a human writing a correlation rule.

**Directional convention (reuse verbatim from the graph UI):** **▲ upstream = root-cause candidate direction · ▼ downstream = blast radius.** Every stage that walks the graph must respect this convention, and every UI that renders it must use these symbols.

### 3.4 Which stages touch the graph

| Stage | Relationship to the graph | Detail |
|---|---|---|
| **E1 Collect** | — | No graph interaction by design. Wire-format admission only. Source-asserted `ci_id` is carried, never validated against the graph here. |
| **E2 Identity** | **Reads** (+ feeds back) | Reads `telemetry_key_index` and `match_rules` to stamp `tenant`+`ci_id`. Unresolved records feed the unresolved bucket, which is a **graph-improvement input**, not just an error queue. |
| **E3 Topology** | **BUILDS / UPDATES** | Owns node creation, edge derivation via ranked methods, provenance stamping, and `GraphSnapshot` emission. The only writer. |
| **E4 Stores** | **Reads** | Uses `ci_id` as the shared join key across the three query planes. Uses per-CI signal-class applicability to know which planes a CI legitimately has no data in. |
| **E5 Maintain** | **Updates** | Edge freshness against per-edge `refresh` cadence; decay/expiry of stale edges; discovery freshness baseline. Does not create edges. |
| **E6 Detect** | **Reads** | Signal-class applicability gates which detectors are meaningful per CI; `primary_health_signal` gives the per-CI health metric. |
| **E7 Curate** | **Reads** | Edge adjacency and `criticality` are the merge evidence — correlated signals on adjacent CIs collapse into one seed. |
| **E8 Scope** | **Reads** | N-hop neighborhood walk from the seed CI produces the bounded candidate set. This is the stage that makes diagnosis affordable. |
| **E9 Localize** | **Reads** | Descends ▼ / ascends ▲ per Detect-class leaf rule; `correlate_upstream[]` supplies candidates; edge `evidence_type` should modulate ranking confidence *(Design-level)*. |
| **E10 Identify** | **Reads** | `confirm_with_signals[]` is the corroboration list; log `key_patterns` join the leaf's fault signature on failure-mode. |
| **E11 Package** | **Reads** (+ feedback *(Design-level)*) | `blast_radius_downstream[]` renders impact; weakest traversed `evidence_type` bounds the stated confidence. Operator confirm/reject as a graph-quality feedback signal is **proposed, not built**. |

Read that column as: **one writer, one maintainer, nine readers.** That asymmetry is deliberate and should be preserved — a graph with multiple writers cannot maintain coherent provenance.

### 3.5 Operator feedback loop into E3 (Design-level — resolved 2026-08-17, decision log #9)

E11 already shows the operator which edges were traversed to reach a verdict (§3.1). When the operator confirms or rejects a `VerdictCard`, that reaction is attached to the *specific path*, not to the verdict as an undifferentiated whole — a rejection can mean "wrong topology" or "right topology, wrong diagnosis," and the graph must be able to tell those apart.

**Feedback event, emitted at E11:**

```
GraphFeedbackEvent {
  verdict_id, outcome: confirmed | rejected | corrected(new_root_ci),
  path_edges: [ { from, to, edge_type, evidence_type_at_time } ],
  matched_signature: fault_signature_id,
  leaf_ci, operator_id, timestamp
}
```

**How E3 consumes it — a rolling trust score, not a single-event rewrite:**

- Only `corroborating` and `declared` edges are eligible for downgrade. An `authoritative` edge is sourced from a system of record; if it keeps showing up in rejected verdicts, the topology is almost certainly right and the fault-signature match is the more likely culprit — feedback on an authoritative-edge path routes to a **signature-quality queue** (flags the matched `fault_signature` for review), not to the edge.
- A `corroborating`/`declared` edge that accumulates a reject-rate above threshold (proposed: ≥40% rejected, minimum 3 independent verdicts in the trailing window) gets its `confidence` downgraded one notch, or is scheduled for earlier-than-cadence re-derivation. **Never auto-deleted** — deletion only happens if the next scheduled E3 derivation pass fails to re-confirm it.
- Minimum sample size (≥3) before any downgrade fires — a single operator's misclick must not move the graph.

**Where this sits in the pipeline:** this is not a new numbered stage — it reuses the same feedback-channel shape E2's unresolved bucket already has into E3 (§4, E2), just triggered from E11 instead of E2. Two feedback channels into the same writer, both Design-level, both following the same "never silently rewrite, always require corroboration" discipline.

**Maturity: Design-level.** Specified here, not built, not lab-validated. Needs an ADR before LLD-E3 picks it up.

---

## 4. Stage-by-stage design — E1–E5 (P1 Always-on fabric)

P1 stages are **signal-differentiated, not fault-differentiated**. They run continuously and identically regardless of which use case is about to occur — indeed, before any fault is known to exist. Per an explicit decision already taken with the user, each P1 stage therefore gets **one IN/OUT contract**, not eight.

Interactive walk of these five contracts: Fusion → **Pipeline & Graph** (left rail, E1–E5). The use-case pills on that tab do not change P1 I/O.

### E1 Collect

**Purpose (Pipeline HLD, unchanged):** wire-format admission only. Telemetry this pass; no CI binding, no CMDB/change/ticket sources.

| | |
|---|---|
| **IN** | External telemetry envelopes from agents / OTLP / log streams. Source-asserted `ci_id`/`ci_type` carried but **not** validated. |
| **OUT** | `TelemetryEnvelope` — on-wire `ingest.v1` JSONL. Unknown `signal_class` and schema-version mismatch reject or dead-letter; never guess. Reserved-unused classes: `change_event`, `cmdb_sync`, `ticket`. |
| **Graph interaction** | **None, by design.** Binding is E2's job. E1 validating against the graph would couple admission to graph freshness and make ingest fail when discovery lags. |

### E2 Identity (Normalize)

**Purpose (Pipeline HLD, unchanged):** stamp `tenant` + `ci_id` in-stream, in the same pass as the operators (Transform / Filter / Sample / Enrich / Mask / Pre-process / Pre-aggregate). Unresolved records queue, never drop. Overlay, not schema rewrite.

| | |
|---|---|
| **IN** | `TelemetryEnvelope`. |
| **OUT** | `IdentifiedRecord` — the same `ingest.v1` line plus an `identity.*` overlay: `tenant`, `ci_id`, `ci_type`, `identity.status` ∈ {`resolved`, `unattributed`, `synthesized`}, `identity.bind_source`, `identity.aliases`. `service`/`env`/`version` remain optional `labels` (D-E2-2). |
| **Graph interaction** | **Reads** the `telemetry_key_index` (one lookup for host-scoped keys; composite lookup plus `scope_parent_via` resolution for instance-scoped keys) and the per-CI `match_rules`. **Feeds back:** the unresolved bucket is a first-class E3 input — a persistent unresolved key pattern is evidence of a CI the graph does not yet know about. |

The bind path is worth stating concretely because it is where the two structures meet: an arriving `system.cpu.utilization` datapoint carries `host.name`; the index resolves it host-scope in one hop. An arriving `system.disk.io.latency` datapoint carries `host.name` **and** a device instance key; the index resolves the parent via `host.name` first, then the instance. If the parent fails to resolve, the instance cannot resolve either, and the record goes to the unresolved bucket rather than being attached to the host as if it were host-scoped. That failure mode — silently flattening an instance metric to its host — is precisely what use cases 6 and 7 cannot tolerate.

### E3 Topology

**Purpose (Pipeline HLD, unchanged):** build and maintain the walkable dependency graph, kept current continuously off the same stream — not a batch CMDB import. Discovery-first; CMDB optional enrichment. **This is where the operational graph is built.**

| | |
|---|---|
| **IN** | `IdentifiedRecord` stream; discovery relations (LLDP/CDP, ARP, routing tables, mount/iscsi tables, socket/conntrack, hypervisor inventory, distributed traces); optional CMDB enrichment; unresolved-bucket patterns from E2. |
| **OUT** | `GraphSnapshot` — nodes with the full node model, typed edges each carrying a complete `discovered_via` provenance block. |
| **Graph interaction** | **Builds and updates. Sole writer.** Executes the ranked derivation methods per relationship, stamps `evidence_type`/`confidence`/`refresh` per edge, resolves both endpoints through the telemetry key index. |

**Design-level:** the continuous-derivation loop — running the ranked methods on a live stream at each edge's stated `refresh` cadence — is specified by this schema but has no lab. The schema is Grounded as an artifact; the live builder is not.

### E4 Stores

**Purpose (Pipeline HLD, unchanged):** metrics, traces and logs as **separate query planes under one shared identity** (`ci_id`). Deliberately not a single wide-event fabric — this is shared-identity federation (D2 Signed).

| | |
|---|---|
| **IN** | `IdentifiedRecord`. |
| **OUT** | Modality-specific query surfaces, time-sliced and retrievable by `ci_id` and tags. |
| **Graph interaction** | **Reads.** `ci_id` is the shared partition/join key across all three planes. Per-CI signal-class applicability tells the store layer which planes a CI is *expected* to be absent from — the distinction that makes an absence interpretable. |

The applicability pattern belongs here explicitly. A SAN fabric switch has no `traces` plane and never will; a business service has no `hardware_sensors`. Recording those as declared non-applicable, with a reason, is what lets E6 treat a *different* absence — telemetry that should be arriving and is not — as use case #5 rather than as normal.

### E5 Maintain

**Purpose (Pipeline HLD, unchanged):** retention, indexing, discovery freshness — a running property of the fabric, not a batch pass.

| | |
|---|---|
| **IN** | Store/index metadata, discovery updates, change feeds, per-edge `refresh` cadences. |
| **OUT** | Freshness baseline; maintain state; edge staleness flags. |
| **Graph interaction** | **Updates.** Enforces per-edge `refresh` (`poll 5m` on authoritative inventory edges; trace-arrival-driven on corroborating trace edges), decays edges that miss their window, and expires edges whose derivation method stops producing. Does not create edges. |

`declared` edges deserve specific attention from E5, because they are the ones that decay invisibly: nothing observed them, so nothing stops observing them. An `esxi-host -[member_of]-> vsphere-cluster` edge with `confidence: n/a` will remain in the graph, cheerfully wrong, until something explicitly revalidates it. **Resolved 2026-08-17 (decision log #4):** a `declared` edge is soft-flagged as stale after **7 days** without any corroborating signal or CMDB re-sync touching it, and hard-downgraded (excluded from any confidence-bearing localization path) after **30 days**. Any CMDB pull that still includes the edge resets the clock, even if the edge itself is unchanged. This is a proposed starting default, not yet lab-validated — tune per tenant once real staleness behavior is observed. This is the concrete content behind the Pipeline HLD's open item "freshness window and bounded staleness (no numeric target yet — flag for LLD-E3)".

E5 remains **Design-level** overall, exactly as in the Pipeline HLD — no dedicated lab exercises it.

---

## 5. Stage-by-stage design — E6–E11 (P2 Case opens, P3 Diagnose and close)

From E6 onward the pipeline is fault-differentiated, so each stage gets all 8 use cases as rows.

Interactive walk of these rows: Fusion → **Pipeline & Graph**, select a use case, then E6–E11.

Reading note: rows for use cases 3, 6, 7, 8 are identical at E6 and largely identical at E7 — that is the taxonomy point from §2.3 made visible, not an editing oversight.

### E6 Detect (P2)

**Purpose (Pipeline HLD, unchanged):** raise a fault `Signal` per Detect class. No root-cause claim yet. **A negative Detect — symptom present, nothing fires — is a valid, honestly-reported outcome, not a defect.**

| Use case | IN | OUT | Operational graph interaction | Maturity |
|---|---|---|---|---|
| **1 Error rate** | `http.server.errors.5xx`, `service.request.error_rate`, span `status:error` rate over window | `Signal{class: ERROR, ci_id, window, magnitude}` | Reads signal-class applicability (`traces`/`logs` applicable on this CI); reads `primary_health_signal` | Grounded (DT+DD) |
| **2 Slowdown** | `http.server.request.duration` p95, `service.latency.p95`, `db.transaction.duration`, `http.client.request.duration` | `Signal{class: SLOWDOWN, ci_id, window, p95 delta}` | Same; plus edge `criticality` to prioritise critical-path services | Grounded (DT+DD) |
| **3 Resource contention** | `system.cpu.utilization`, `system.memory.usage`, `system.load.1m`, `node.cpu.pressure`, `node.memory.pressure`, `vm.cpu.ready`, `vm.cpu.costop`, `vm.mem.ballooned` | `Signal{class: RESOURCE_CONTENTION, ci_id}` **or explicit negative-Detect note** | Reads `monitored_via` to decide whether a negative Detect is meaningful or merely uninstrumented | Grounded (DT) · Local-only (DD) |
| **4 Availability** | `<ci>.up` (e.g. `linux-server.up`, `postgresql-db.up`), `node.condition.ready`, `ifOperStatus`, `corosync.ring.status` | `Signal{class: AVAILABILITY, ci_id, first_down_ts}` | Reads inbound edges to identify affected callers before localization | Grounded (DT) · Local-only (DD) |
| **5 Monitoring unavailable** | `collector.ingest.lag`, `agent.heartbeat.state`, `collector.poll.failure.rate`, `collector.metrics.rate`; absence-of-signal against expected cadence | `Signal{class: MONITORING_UNAVAILABLE, ci_id, gap_window}` | **Critical read:** signal-class applicability distinguishes "declared not-applicable" from "expected but absent". Without it this class is undecidable | Grounded (DT) · Local-only (DD) |
| **6 Disk latency** | `system.disk.io.latency` (instance-scoped), `vm.disk.latency`, `datastore.totalReadLatency` / `totalWriteLatency`, `array.volume.latency`, `nfs.client.ops.latency` | `Signal{class: RESOURCE_CONTENTION}` — **same bucket as #3** | Reads `instance_scope: multi-instance` so the signal binds to the device, not the host | Grounded (DT) · Local-only (DD) |
| **7 Disk usage** | `system.filesystem.usage`, `system.filesystem.inodes.usage` (both instance-scoped, mountpoint-keyed) | `Signal{class: RESOURCE_CONTENTION}` — same bucket | Same instance-scope read; mountpoint is the instance key | Grounded (DT) · Local-only (DD) |
| **8 Network throughput** | `system.network.io`, `system.network.errors`, `interface.utilization`, `ifInErrors` / `ifOutErrors`, `esxi.net.droppedRx`, `flow.bytes`, `tcp.retransmits` | `Signal{class: RESOURCE_CONTENTION}` — same bucket | Reads `connects_to` / `routes_through` / `communicates_with` edges to know which link this interface belongs to | Grounded (DT) · Local-only (DD) |

**Design-level across this table:** specific thresholds, baselining method and window lengths are not specified here and are not validated in this repo. Every row states *which signal*, not *at what value*. Thresholds belong in LLD-E6 and in the tenant-level KPI catalog.

### E7 Curate (P2)

**Purpose (Pipeline HLD, unchanged):** collapse correlated signals into one case seed with merge rationale. Skip it and signal fog reaches the operator.

| Use case | IN | OUT | Operational graph interaction | Maturity |
|---|---|---|---|---|
| **1 Error rate** | N `ERROR` signals across a call chain (e.g. `customer-web-portal`, `web-hosting-svc`, `nginx-web-server`, `app-runtime-jvm`) | One `CaseSeed`, seeded at the most-upstream-symptomatic CI, with merge rationale naming the edges traversed | Walks `depends_on` / `communicates_with` edges to prove the signals are adjacent, not coincidental | Grounded (DD multi-hot-service fog lab) |
| **2 Slowdown** | N `SLOWDOWN` signals along a latency path | One `CaseSeed` + path | Same walk; edge `criticality` breaks ties between concurrent candidate seeds | Grounded |
| **3 Resource contention** | `RESOURCE_CONTENTION` on a host plus derived symptoms on its tenants (`app-runtime-jvm`, `postgresql-db`, `nginx-web-server`) | One `CaseSeed` — host contention with dependent-workload symptoms attached | `runs_on` edges (authoritative) prove the tenancy relationship that justifies the merge | Grounded (DT) · Local-only (DD) |
| **4 Availability** | A down signal plus a cascade of caller failures | One `CaseSeed` anchored on the down entity, callers attached as consequences | Inbound-edge fan-in identifies the cascade; `redundancy` (e.g. active-passive) explains why some callers did **not** fail | Grounded (DT) · Local-only (DD) |
| **5 Monitoring unavailable** | Gap signals on several CIs sharing one collector | One `CaseSeed` on the **collector**, not on each blind CI | `monitored_by` edges are the merge key — this is the edge type that exists specifically for this case | Grounded (DT) · Local-only (DD) |
| **6 Disk latency** | Latency signals at several storage tiers (`local-filesystem` → `vmfs-datastore` → `san-storage-array` → `fc-fabric-switch`) | One `CaseSeed` spanning the storage path | `depends_on` / `mounts` chain (all authoritative) is the merge evidence | Grounded (DT) · Local-only (DD) |
| **7 Disk usage** | Usage signals on one or more mountpoints, possibly plus a datastore-full signal | One `CaseSeed`; if `Remounting filesystem read-only` also appears, seed carries an **escalation-to-AVAILABILITY annotation** (not a reclassification — decision log #6) | `part_of` (filesystem→host) and `depends_on` (filesystem→datastore) bound the merge | Design-level (annotation mechanism proposed, not built) |
| **8 Network throughput** | Throughput/error signals on host NIC and on the attached switch port | One `CaseSeed` across the link | `connects_to` edges (authoritative, LLDP/CDP+ARP) pair host interface to switch port | Grounded (DT) · Local-only (DD) |

### E8 Scope (P2)

**Purpose (Pipeline HLD, unchanged):** lock the working set — time window, candidate CI set, env and version. Bounds the cost of diagnosis. **Uses the operational graph to bound the candidate set.**

| Use case | IN | OUT | Operational graph interaction | Maturity |
|---|---|---|---|---|
| **1 Error rate** | `CaseSeed` + graph | `WorkingSet{window, candidates, env, version}` — candidates = call-chain closure downstream of the seed | ▼ downstream walk over `depends_on`/`uses`/`communicates_with` from the seed service | Grounded |
| **2 Slowdown** | `CaseSeed` + graph | `WorkingSet` scoped to the latency path plus its hosting tier | ▼ walk, then one ▲ hop to include `runs_on` hosts (slowdown often originates a tier below) | Grounded |
| **3 Resource contention** | `CaseSeed` on host or hypervisor | `WorkingSet` = contended CI + all workloads running on it + its virtualization parents | ▼ over `runs_on` (tenants), ▲ over `hosted_on`/`member_of` (hypervisor, cluster) — the noisy-neighbor path | Grounded (DT) · Local-only (DD) |
| **4 Availability** | `CaseSeed` on the down entity | `WorkingSet` = down entity + full inbound caller closure | ▲ inbound closure; `redundancy` marks callers expected to survive | Grounded (DT) · Local-only (DD) |
| **5 Monitoring unavailable** | `CaseSeed` on collector | `WorkingSet` = collector + every CI with a `monitored_by` edge to it + the network path to them | `monitored_by` fan-out, plus `connects_to`/`routes_through` to separate "collector broken" from "network partition" | Grounded (DT) · Local-only (DD) |
| **6 Disk latency** | `CaseSeed` on storage path | `WorkingSet` = full storage dependency chain, host through array through fabric | ▼ over `mounts`/`depends_on` to the array; then `connects_to` to the fabric switch | Grounded (DT) · Local-only (DD) |
| **7 Disk usage** | `CaseSeed` on filesystem instance(s) | `WorkingSet` = mountpoint + host + backing datastore (**v1 scope**); writer-process attribution deferred to a later round (decision log #8) | `part_of` up to host, `depends_on` down to datastore. The `runs_on` sideways walk to find the writing process is specified but out of scope for v1 | Deferred to later round (decision #8) |
| **8 Network throughput** | `CaseSeed` on interface/link | `WorkingSet` = host + NIC + switch port + upstream router/firewall + top flow peers | `connects_to` chain plus `flows_packets` peers resolved through the telemetry key index | Grounded (DT) · Local-only (DD) |

**Resolved 2026-08-17 (decision log #5):** the candidate cap and hop-depth limit per Detect class, proposed as a tunable starting default:

| Detect class | Hop-depth cap | Candidate cap | Why |
|---|---|---|---|
| ERROR | 6 | 150 | call-chain closure rarely needs more |
| SLOWDOWN | 7 | 150 | call-chain + 1 host hop |
| RESOURCE_CONTENTION (incl. UC-6/7/8) | 3–4 | 300 | must fit the full co-tenant fan-out on a contended host |
| AVAILABILITY | 5 | 500 | blast radius must not be under-scoped |
| MONITORING_UNAVAILABLE | 2 | 1000 | a dead collector can serve very many CIs |

**Attached rule:** if a walk hits its cap, `WorkingSet.capped = true` is set and E11 must render "scoped to N of possibly-more candidates" rather than silently presenting a complete picture — the same never-silently-drop discipline already used for E2's unresolved bucket and E3's ambiguous-match policy. Not yet lab-validated; on the reference 33-CI graph none of these caps bind. The Pipeline HLD flagged this for LLD-E8.

### E9 Localize (P3)

**Purpose (Pipeline HLD, unchanged):** pick the leaf CI by Detect-class rule. **Earliest anomaly is NOT automatically the cause.** Bar: top-1 ≥ 90%. **Walks the operational graph to find the leaf.**

| Use case | IN | OUT | Operational graph interaction | Maturity |
|---|---|---|---|---|
| **1 Error rate** | `WorkingSet` + error evidence | `LeafClaim{ci_id}` = **deepest error leaf** | ▼ descend `depends_on`/`uses` while error persists; stop at the last CI still showing errors (e.g. portal → app-hosting → JVM → **postgresql-db**) | Grounded |
| **2 Slowdown** | `WorkingSet` + span self-time | `LeafClaim` = **longest self-time leaf** | Same ▼ descent, ranked by self-time not total time — this is what excludes the callers that are merely waiting | Grounded |
| **3 Resource contention** | `WorkingSet` + saturation metrics | `LeafClaim` = **contended entity**, even if the symptom on it is negative | ▲ ascend `runs_on`→`hosted_on` from the symptomatic workload to the saturated host or hypervisor; `vm.cpu.ready`/`vm.cpu.costop` elevated on the guest with the host busy indicts the **hypervisor**, not the guest | Grounded (DT) · Local-only (DD) |
| **4 Availability** | `WorkingSet` + up/down states + timestamps | `LeafClaim` = **first-down entity in the caller chain** | ▲ walk inbound edges ordered by `first_down_ts`; the earliest-down entity with no down upstream is the leaf | Grounded (DT) · Local-only (DD) |
| **5 Monitoring unavailable** | `WorkingSet` + gap windows | `LeafClaim` = **entity with the coverage gap** | If all CIs behind one `monitored_by` edge went blind together, the leaf is the **collector**; if one went blind alone, the leaf is that CI | Grounded (DT) · Local-only (DD) |
| **6 Disk latency** | `WorkingSet` + per-tier latency | `LeafClaim` = deepest storage tier where latency originates | ▼ descend `mounts`→`depends_on`→`connects_to`; compare `system.disk.io.latency` vs `datastore.totalReadLatency` vs `array.volume.latency` vs `fc.port.crc_errors` — latency present at the array but not the fabric indicts the **array** | Design-level (tier-comparison rule is proposed) |
| **7 Disk usage** | `WorkingSet` + `system.filesystem.usage` per mountpoint | `LeafClaim` = the **filesystem instance**, not the host | Instance-scoped resolution via `scope_parent_via: host.name`; `part_of` edge names the host for context but the leaf is the mountpoint | Design-level |
| **8 Network throughput** | `WorkingSet` + interface counters and flows | `LeafClaim` = the **saturated link endpoint** (**v1 scope**); top-talker attribution deferred to a later round (decision log #8) | Compare `interface.utilization` at each `connects_to` hop. `flow.bytes`-by-peer talker identification is specified but out of scope for v1; `tcp.retransmits`/`flow.drops` still distinguish saturation from loss | Deferred to later round (decision #8) |

**Design-level, applies to every row:** edge `evidence_type` should modulate ranking confidence — a leaf reached only through `corroborating` edges is a weaker claim than one reached through `authoritative` edges. This follows directly from the schema and is not yet implemented.

### E10 Identify (P3)

**Purpose (Pipeline HLD, unchanged):** corroborate the leaf across modalities (metrics + logs + traces together) and decide how strongly cause is claimed — evidentiary tier, CARE, scoped causal check. **This is where Verify actually happens.** No-false-blame is a pass/fail gate.

Every row below draws `confirm_with_signals[]` from the leaf CI's matched fault signature. That list is pre-computed in the graph; E10 executes it rather than deriving it.

| Use case | IN | OUT | Operational graph interaction | Maturity |
|---|---|---|---|---|
| **1 Error rate** | `LeafClaim` + stores | `EvidenceBundle`: error spans, stack traces, log patterns (`Exception\|ERROR .* at .*\(.*\.java`, `FATAL: .* too many connections`, `" 5\d\d "`), error-rate delta | Matches leaf + symptom to a fault signature (e.g. `connection pool exhaustion` on `postgresql-db`); log `key_patterns` join on `indicates_failure_mode` | Grounded |
| **2 Slowdown** | `LeafClaim` + stores | `EvidenceBundle`: span self-time distribution, `jvm.gc.pause`, `db.transaction.duration`, `Full GC .* \d{3,}ms\|GC pause`, CPU corroboration | Signature `GC pause / heap exhaustion (OOM)` or `long-running / locking queries`; `confirm_with_signals` supplies the metric list | Grounded |
| **3 Resource contention** | `LeafClaim` + stores | `EvidenceBundle`: `system.cpu.utilization`, `system.memory.usage`, `system.load.1m`, `Out of memory: Killed process (\d+)`, `vm.cpu.ready`, `esxi.cpu.utilization` | Signature `CPU saturation / run-queue backlog`, `memory exhaustion / OOM-kill`, or `physical CPU/memory saturation (noisy neighbor)` at the ESXi tier | Grounded (DT) · Local-only (DD) |
| **4 Availability** | `LeafClaim` + stores | `EvidenceBundle`: process/container check, `systemd.*Failed to start\|entered failed state`, `kernel: .* segfault at`, caller APM failure spans, `boot.id` change | Signature `host down / kernel panic`, `NotReady node`, or `vpxd service down`; `blast_radius_downstream` cross-checks that the observed casualties match the predicted ones | Grounded (DT) · Local-only (DD) |
| **5 Monitoring unavailable** | `LeafClaim` + stores | `EvidenceBundle`: **absence-of-signal pattern** + cross-modal comparison — entity still answering on one plane while another plane is silent; `poll .* timeout\|failed to collect`, `queue .* full\|drop` | Signature `agent heartbeat lost`, `poll timeout`, `ingest backlog`; signal-class applicability proves the missing plane was expected | Grounded (DT) · Local-only (DD) |
| **6 Disk latency** | `LeafClaim` + stores | `EvidenceBundle`: latency at the indicted tier, `blk_update_request: I/O error\|critical medium error`, `high iowait`, `array.cache.hit_ratio`, `fc.port.crc_errors` | Signature `datastore latency spike`, `disk/RAID degradation`, `cache battery failure (write-through penalty)`, or `ISL congestion` | Design-level (tier attribution unvalidated) |
| **7 Disk usage** | `LeafClaim` + stores | `EvidenceBundle`: `system.filesystem.usage` trend, `system.filesystem.inodes.usage`, `No space left on device\|filesystem .* full`, `Remounting filesystem read-only\|EXT4-fs error` | Signature `filesystem full`, `inode exhaustion`, `remount read-only on error`, or `WAL / disk full` if the leaf is the DB. **Escalation:** read-only remount is **annotated** onto the `RESOURCE_CONTENTION` case as AVAILABILITY-shaped supplementary evidence — the case is not reclassified (decision log #6) | Design-level (annotation mechanism proposed, not built) |
| **8 Network throughput** | `LeafClaim` + stores | `EvidenceBundle`: `interface.utilization`, `ifInErrors`/`ifOutErrors`, `tcp.retransmits`, `tcp.rtt`, `flow.drops`, `Link is Down\|NIC Link is Down`, `esxi.net.droppedRx` | Signature `uplink saturation`, `NIC errors / link down`, `port flap`, or `ISL congestion`. **Escalation:** retransmits+latency or link-down are **annotated** as SLOWDOWN/AVAILABILITY-shaped supplementary evidence — the case is not reclassified (decision log #6) | Design-level (annotation mechanism proposed, not built) |

**No-false-blame is the gate.** The S3-type test — an application-only fault on healthy infrastructure — must not produce an infrastructure verdict. `blast_radius_downstream` is the structural check: if the graph predicts casualties that were not observed, the leaf claim is probably wrong and confidence must drop rather than the prediction being quietly ignored.

**Resolved 2026-08-17 (decision log #6):** when a case escalates across Detect-class boundaries mid-diagnosis (UC-7 disk-usage → availability-shaped outcome; UC-8 network-throughput → slowdown/availability-shaped outcome), E10 **annotates, it does not reclassify.** The original Detect class and the leaf rule E9 already committed to stay authoritative for this case; the escalation is recorded as supplementary evidence (new symptom + timestamp) on the same `EvidenceBundle`, not a class switch that would re-run E9 under different rules.

### E11 Package (P3)

**Purpose (Pipeline HLD, unchanged):** render the verdict handoff and lock the confidence judgment. Thin cards allowed **only** with incompleteness explicitly flagged.

| Use case | IN | OUT | Operational graph interaction | Maturity |
|---|---|---|---|---|
| **1 Error rate** | `EvidenceBundle` | `VerdictCard`: leaf CI, failure mode, error spans/stack, impacted callers, confidence + tier | `blast_radius_downstream` renders impact; weakest traversed `evidence_type` bounds stated confidence | Grounded |
| **2 Slowdown** | `EvidenceBundle` | `VerdictCard`: leaf CI, self-time attribution, latency path, confidence | Path rendered with per-edge `evidence_type` so the operator sees which hops were inferred | Grounded |
| **3 Resource contention** | `EvidenceBundle` | `VerdictCard`: contended CI, saturating resource, affected tenant workloads | `runs_on` fan-out gives the tenant list; noisy-neighbor cases name the co-tenant explicitly | Grounded (DT) · Local-only (DD) |
| **4 Availability** | `EvidenceBundle` | `VerdictCard`: first-down entity, down-since, cascade list, surviving-redundancy note | `blast_radius_downstream` + `redundancy` explains both what failed and what did not | Grounded (DT) · Local-only (DD) |
| **5 Monitoring unavailable** | `EvidenceBundle` | `VerdictCard`: blind entities, gap window, **explicit "we are blind, not down" statement** | `monitored_by` fan-out enumerates exactly which CIs lost coverage — the scope of the blindness | Grounded (DT) · Local-only (DD) |
| **6 Disk latency** | `EvidenceBundle` | `VerdictCard`: indicted storage tier, latency comparison across tiers, affected mounts and workloads | Storage chain rendered tier by tier with each hop's `evidence_type` | Design-level |
| **7 Disk usage** | `EvidenceBundle` | `VerdictCard`: mountpoint, usage/inode trend, time-to-exhaustion, **escalation warning if read-only remount observed** | `part_of` + `runs_on` name the host and the workloads that will fail on write | Design-level |
| **8 Network throughput** | `EvidenceBundle` | `VerdictCard`: saturated link, direction, error/retransmit context (top talkers deferred to a later round, decision log #8) | `connects_to` chain renders the physical path; flow peers resolved to CI names, not bare IPs | Design-level |

**Universal E11 rule (Design-level, proposed here):** the confidence stated on a `VerdictCard` **cannot exceed the weakest `evidence_type` on the localization path**. A leaf reached through a `declared` edge with `confidence: n/a` cannot be packaged as high confidence, no matter how strong the metric evidence on the leaf itself is. This is the packaging-side expression of the §3.1 principle and it is the mechanism that makes the moat visible to the customer.

---

## 6. End-to-end worked example — use case #3, resource contention

Walk the same scenario on Fusion → **Pipeline & Graph** with use case #3 selected. This section is the normative write-up.

Scenario: on a VMware + Linux estate matching the reference worked example, the ESXi host underneath a production VM becomes CPU-saturated by a co-tenant. The Linux guest's own CPU metrics look unremarkable. Application latency rises.

This is the case that separates a graph-backed pipeline from a threshold-backed one, because **the symptomatic CI and the causal CI are two tiers apart and the causal CI's symptom is only visible from the guest's perspective** (`vm.cpu.ready` / `vm.cpu.costop`).

| Stage | What happens | Concrete detail |
|---|---|---|
| **E1 Collect** | Telemetry admitted as `ingest.v1`, no binding | Agent metrics from `linux-server`, vCenter API metrics for `linux-vm` / `esxi-host`, JVM metrics from `app-runtime-jvm` |
| **E2 Identity** | `tenant`+`ci_id` stamped in-stream | `system.cpu.utilization` + `host.name` → `linux-server` (host scope, one lookup). `vm.cpu.ready` + `host.name` → `linux-vm`. `jvm.gc.pause` + `host.name` + `service.instance.id` → `app-runtime-jvm` (composite, parent resolved first) |
| **E3 Topology** | Graph already current | `app-runtime-jvm -[runs_on]-> linux-server` (authoritative, agent/cgroup, `poll 5m`); `linux-server -[runs_on]-> linux-vm` (authoritative); `linux-vm -[hosted_on]-> esxi-host` (authoritative, hypervisor inventory); `esxi-host -[member_of]-> vsphere-cluster` (**declared**, `confidence: n/a`) |
| **E4 Stores** | Three planes queryable under shared `ci_id` | Metrics for all four CIs; logs for `linux-server` and `app-runtime-jvm`; traces for the JVM. `esxi-host` correctly has no `traces` plane — declared not-applicable, not missing |
| **E5 Maintain** | Freshness held | Authoritative `runs_on`/`hosted_on` edges within their 5m refresh. The `member_of` cluster edge is `declared` and stale-risk — flagged |
| **E6 Detect** | `RESOURCE_CONTENTION` signal | `esxi.cpu.utilization` saturated; `vm.cpu.ready` and `vm.cpu.costop` elevated on `linux-vm`. **`system.cpu.utilization` on `linux-server` is normal** — the guest cannot see that it is being starved. A `SLOWDOWN` signal also fires on `app-runtime-jvm` |
| **E7 Curate** | Two signals → one seed | Merge justified by the authoritative `runs_on` → `hosted_on` chain linking the slow JVM to the contended hypervisor. Rationale records the two edges traversed. Without this the operator sees two unrelated alerts |
| **E8 Scope** | Working set locked | ▲ over `runs_on`/`hosted_on` to `esxi-host` and `vsphere-cluster`; ▼ over `runs_on` from `esxi-host` to every co-tenant VM. Window = symptom onset ± correlation window. This ▼ leg is what finds the noisy neighbor |
| **E9 Localize** | Leaf = `esxi-host` | Leaf rule: **contended entity, even if its own symptom is negative**. `vm.cpu.ready` elevated on the guest with `esxi.cpu.utilization` saturated on the host indicts the hypervisor. Earliest anomaly was arguably the JVM latency — correctly rejected as effect, not cause |
| **E10 Identify** | Corroborate + set tier | Matched signature: `physical CPU/memory saturation (noisy neighbor)` on `esxi-host`. `confirm_with_signals` → `esxi.cpu.utilization`, `esxi.mem.usage`, `esxi.mem.balloon`. `correlate_upstream` → `vsphere-cluster` (DRS imbalance?). `blast_radius_downstream` → all VMs on the host; observed casualties checked against predicted. Cross-modal: no OOM or fs-error log patterns on `linux-server` — consistent with contention rather than a guest fault. **No-false-blame holds:** the JVM is not blamed |
| **E11 Package** | Verdict rendered | Leaf `esxi-host`; failure mode noisy-neighbor CPU contention; impact = co-tenant VMs from `blast_radius_downstream`; evidence = the four confirm signals plus the negative guest-side check. **Confidence bounded by the weakest edge traversed** — the localization path used only `authoritative` edges, so confidence is not degraded; had it needed the `declared` `member_of` edge to reach a cluster-level conclusion, it would have been |

The load-bearing observation: **every stage from E7 onward consumed the graph, and the diagnosis is impossible without it.** A rule engine looking only at metrics sees a slow JVM on a healthy host and a busy hypervisor, with nothing connecting them. The `runs_on` → `hosted_on` chain is the connection, and the fact that both edges are `authoritative` is why the verdict can be stated with confidence rather than hedged.

---

## 7. Decision log — resolved 2026-08-17

All 9 items below were open questions in v0.1. Resolved in a review pass with the document owner; each decision is also reflected inline at its owning section (cross-referenced below).

| # | Question | Decision | Where else this shows up |
|---|---|---|---|
| **1** | Are the §5 metric names (sourced from the reference graph's 228-entry telemetry key index, no KPI catalog to check against) canonical? | **Placeholder, not canonical.** Shape-correct, treated as unverified until reconciled against a real KPI catalog before LLD work starts. | §2.2 honesty note |
| **2** | Units and numeric thresholds are unreconciled — blocks E6 threshold specification | **Deferred with #1**, same reconciliation pass. LLD-E6 stays blocked on it, as it already was. | §5 E6 |
| **3** | Should edge `evidence_type` formally modulate E9 ranking and cap E11 confidence? | **Deferred.** Left as a documented open question — not committed either way until real localization runs exist to see how often it would matter. Revisit once E9/E10 have production data. | §3.3.2, §5 E9/E11 |
| **4** | Maximum age before a `declared` edge is downgraded or flagged | **7 days → soft-flag stale, 30 days → hard-downgrade.** Resets on any CMDB re-sync that still includes the edge. Proposed default, not lab-validated. | §4 E5 |
| **5** | `WorkingSet` candidate cap and per-class hop-depth limit | **Per-Detect-class table set** (ERROR 6/150, SLOWDOWN 7/150, RESOURCE_CONTENTION 3–4/300, AVAILABILITY 5/500, MONITORING_UNAVAILABLE 2/1000), with a `WorkingSet.capped` flag so a bounded walk is never silently presented as complete. Proposed default, not lab-validated. | §5 E8 |
| **6** | Cross-class escalation (#7 → `AVAILABILITY`, #8 → `SLOWDOWN`/`AVAILABILITY`) — reclassify or annotate? | **Annotate, do not reclassify.** The Detect class and leaf rule E9 already committed to stay authoritative; escalation is recorded as supplementary evidence on the same `EvidenceBundle`. | §5 E10 |
| **7** | Two field-name shapes for fault signatures (`rca` block vs. flattened top-level array) | **Per-CI nested `rca.fault_signatures[]` is canonical** — matches how E9/E10 actually access it (walk to a leaf, read that leaf's own signatures). The flat array becomes a generated/derived view for analytics, not separately authored. Applies at LLD-E3; the reference JSON itself is unchanged by this document. | §3.3.6 |
| **8** | Writer attribution (#7) and top-talker attribution (#8) — in scope for the initial set? | **Deferred to a later use-case round.** UC-7/UC-8 ship at "disk is full" / "link is saturated" granularity for the initial set; attribution is a follow-on enhancement once the core pipeline is proven. | §5 E8/E9 (rows stay Design-level, now explicitly out-of-scope-for-v1 rather than merely unscheduled) |
| **9** | Operator confirm/reject on a `VerdictCard` as a graph-quality feedback signal into E3 | **Designed now, not just noted** — see new §3.5. Full `GraphFeedbackEvent` shape, rolling per-edge trust score, authoritative-edge rejections route to a signature-quality queue instead of downgrading topology, minimum sample size of 3 before any downgrade. Still Design-level: specified, not built, needs an ADR before LLD-E3 picks it up. | §3.5 (new) |

---

## 8. References

- Parent: [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) — normative on stage semantics · hub HTML [`observeops-pipeline-hld.html`](./observeops-pipeline-hld.html)
- Interactive companion: [`observeops-fusion-guide.html`](./observeops-fusion-guide.html) — tabs map in §0
- Use-case catalog: [`OBSERVEOPS_USE_CASES.md`](./OBSERVEOPS_USE_CASES.md) v1
- Reference operational graph (worked example): [`linux-server-ci-telemetry.json`](./linux-server-ci-telemetry.json) · [`observeops-ci-graph.html`](./observeops-ci-graph.html)
- Pipeline diagram: [`observeops-pipeline-diagram.html`](./observeops-pipeline-diagram.html)
- Closed LLDs: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](./LLD-E2-Identity.md)
- Drafts for review: [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) · [`LLD-E4-Stores.md`](./LLD-E4-Stores.md)
