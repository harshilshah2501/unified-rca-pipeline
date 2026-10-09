# ObserveOps pipeline — High-Level Design (HLD)

**Status:** Approved for build (see §13 sign-off table — D5 remains Review, not blocking)
**Version:** v1.1 (patch on v1.0 — identity-join addendum, D1–D4 Signed, D-E2-1, E1/E2 LLD Done; see §17)
**Owners:** ObserveOps RCA engineering
**Date:** 2026-08-13
**Scope (in):** 3-phase / 11-stage engineering pipeline (E1–E11), Detect-class plug-ins, inter-stage contracts, evidence-maturity model, Fabric identity namespace that ServiceOps can join later
**Scope (out):** Layer I productization, remediation execution, collector-specific implementation details, CMDB/change/ticket Collect sources this pass, per-block LLD schemas for E3–E11 (E1/E2 closed; see §18)
**Normative:** Stage responsibilities, I/O contracts, ADR defaults, HLD-to-LLD gates, stage-vocabulary crosswalk (§5), identity namespace (§11.1)
**Informative:** Vendor maps, lab references, teaching hubs (L0 launchpads: [`dt-davis-category-hub.html`](../dt-davis-category-hub.html) · [`dd-detect-category-hub.html`](../dd-detect-category-hub.html) · [`ed-ai-team-hub.html`](../ed-ai-team-hub.html))

**Browser:** [`observeops-pipeline-hld.html`](./observeops-pipeline-hld.html) · `:8765/observeops-pipeline-hld.html` (Our HLD — summary; this markdown is the written spec)
**Also:** [Fusion](./observeops-fusion-guide.html) (same pipeline, clickable) · [operational graph](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) (chapter — the map those steps walk) · [example map](./observeops-ci-graph.html) · [shift-left](./observeops-shift-left-architecture.html) (where work runs, not a second pipeline) · [Motadata 3 pillars vs E1–E11](../motadata-3pillars-vs-shift-left.html) (PDF → SaaS column; A+B = P1 stores, C = optional P3)

---

## 0. Why this revision exists

v0.2 (Status: Review) was a strong first-pass HLD but had three structural gaps surfaced by a full docs-hub audit on 2026-08-13:

1. No documented mapping between the **5-stage product vocabulary** (`Ingest → Detect → Localize → Identify → Verify`, used throughout [`README.md`](./README.md), [`NAVIGATION.md`](../NAVIGATION.md), [`RCA_WORKFLOW_AND_NEXT.md`](../RCA_WORKFLOW_AND_NEXT.md)) and this document's **11-stage engineering vocabulary** (`E1–E11`). Readers moving between the two had to infer the mapping themselves.
2. NFR targets were sketches ("throughput", "latency budgets") with no numbers, even though quantified targets already exist in [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](./multi-telemetry-rca-functional-and-acceptance-criteria.md) §6.
3. Two of five ADRs (D3, D4) were marked "Must be Signed" and three (D1, D2, D5) "Review," despite the corresponding behavior already being implemented and shipped per [`ROADMAP.md`](../ROADMAP.md) (Ship phase — Done).

v1.0 closes (1) and (2) directly and proposes resolution for (3) with cited evidence. It also folds in the Datadog-side Detect-category evidence-maturity split (RESOURCE_CONTENTION / AVAILABILITY / MONITORING_UNAVAILABLE landed 2026-08-13 as local-only labs, distinct from the MCP-grounded ERROR/SLOWDOWN pair) so the HLD's Detect-class matrix (§9) doesn't imply uniform evidence strength across categories.

v1.1 is a patch, not a rewrite. It freezes a **ServiceOps-joinable identity namespace** (§11.1) so later CMDB/change/ticket records can share `tenant`+`ci_id` without a schema break, signs D1–D4 on the v1.0 evidence, records Fabric ADR **D-E2-1** (bind-miss policy), clarifies that HLD `IdentifiedRecord` is an overlay on `ingest.v1` (not a second on-wire format this pass), and closes [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) / [`LLD-E2-Identity.md`](./LLD-E2-Identity.md). Collect still admits **telemetry only**; ServiceOps remains E11 egress plus a future identity join, not a second Collect path.

## 1. Problem and destination

From continuous telemetry on a service chain, the pipeline must reliably surface: what broke (fault class), where it broke (leaf entity/service/operation), and what evidence to open next, without re-collecting the estate on every alert. This HLD defines our subsystem contracts; DT/DD unveil material is reference context, not architecture authority.

## 2. Goals and non-goals

**Goals**

- Define the 11 engineering stages (E1–E11) as independently testable contracts, each with explicit inputs, outputs, and degradation behavior.
- Make the relationship between "the pipeline" as product stakeholders describe it (5 stages) and "the pipeline" as engineers build it (11 stages) explicit and lookup-able (§5).
- Establish evidence-maturity as a first-class concept: not every Detect class or lab has the same proof strength, and the HLD should say so rather than imply uniformity.
- Give each stage a traceable line to FR/AC and to at least one lab or bakeoff artifact that exercises it.

**Non-goals**

- This HLD does not productize Layer I (Timeline/MTL/Bits) — those remain optional explainers per §4.
- This HLD does not fix remediation, auto-close, or write-path automation.
- This HLD does not mandate a specific storage engine, message bus, or vendor SDK — those are LLD-level (§16).
- This HLD does not claim ObserveOps is a finalized GTM commitment; Lean's role here is the primary **evaluation** engine on this corpus per [ADR-001](../ADR-001-lean-primary-engine.md), not a shipped product decision.

## 3. Architecture principles

Derived from [`lean-pipeline/docs/ARCHITECTURE.md`](../../lean-pipeline/docs/ARCHITECTURE.md):

- Reproducibility is mandatory for evaluation paths.
- Verifiability is mandatory (tier/evidence trail must be inspectable).
- Causal validity is claimed only after scoped checks succeed.
- Earliest anomaly is not automatically root cause.
- Layer I artifacts are optional explainers; Layer E must stand alone.
- **Evidence maturity is stated, not assumed** (new in v1.0): a Detect class or lab counts as MCP/vendor-grounded, locally-observed-only, or planned, and every reference to lab proof in this document names which one (§9.1).

## 4. System context (C4 level 1)

<div class="ud-viz" id="hld-c4-context">
  <div class="ud-cap">System context — who feeds the pipeline and who consumes the verdict</div>
  <div class="ud-rails three">
    <div class="ud-panel">
      <h5>Outside the product</h5>
      <div class="ud-flow" style="margin-top:.35rem;">
        <span class="ud-chip soft">Agents · OTLP · logs</span>
      </div>
      <div class="ud-down">↓</div>
      <div class="ud-flow">
        <span class="ud-chip soft">CMDB (optional)</span>
      </div>
      <p class="ud-note" style="margin:.55rem 0 0;">CMDB enriches; discovery remains the default.</p>
    </div>
    <div class="ud-panel accent">
      <h5>ObserveOps pipeline (required)</h5>
      <div class="ud-flow" style="margin-top:.35rem;">
        <span class="ud-chip hit">P1 Fabric<br><small style="opacity:.75">E1–E5</small></span>
        <span class="ud-arrow">→</span>
        <span class="ud-chip">P2 Case<br><small style="opacity:.75">E6–E8</small></span>
        <span class="ud-arrow">→</span>
        <span class="ud-chip">P3 Diagnose<br><small style="opacity:.75">E9–E11</small></span>
      </div>
      <p class="ud-note" style="margin:.55rem 0 0;">Ingress is Collect (E1). Egress is Package (E11).</p>
    </div>
    <div class="ud-panel warn">
      <h5>Consumers</h5>
      <div class="ud-flow" style="margin-top:.35rem;">
        <span class="ud-chip warn">Operator · ServiceOps</span>
      </div>
      <div class="ud-down">⇣ optional</div>
      <div class="ud-flow">
        <span class="ud-chip soft">Layer I · Timeline / MTL / Bits</span>
      </div>
      <p class="ud-note" style="margin:.55rem 0 0;">Layer I retells evidence; it is not required for a verdict.</p>
    </div>
  </div>
</div>

Ingress is E1 Collect. Egress is E11 Package to operator verdict card and optional incident handoff. CMDB remains optional enrichment; discovery-first default remains valid.


**Identity-join (v1.1):** `Operator_ServiceOps` consumes E11 today. The same `tenant`+`ci_id` that E2 stamps is the join key a future ServiceOps ticket or CMDB CI must use — not a second identity plane and not a parallel Collect. E1 still admits telemetry only this pass. Reserved unused `fact_kind` names (`change_event`, `cmdb_sync`, `ticket`) exist so those sources can land later without colliding with today's enum.

## 5. Stage-vocabulary crosswalk (normative — new in v1.0)

Three vocabularies describe this same pipeline at different altitudes. This table is the single source of truth for translating between them; every other doc that uses any of these names should be read against this row, not re-derive its own mapping.

| 5-stage product model (README/NAVIGATION/WORKFLOW) | 11-stage engineering model (this HLD) | Vendor-teaching "5+3+3" / Clock language (Dynatrace/Datadog hubs, `urca-glossary.html`) |
|---|---|---|
| **Ingest** — collect & normalize telemetry into RCA-ready artifacts | **E1 Collect → E2 Identity → E3 Topology → E4 Stores → E5 Maintain** (all of P1) | **Clock A / Always-on fabric** (5 stages: F) |
| **Detect** — decide *something is wrong* and raise a seed | **E6 Detect** (start of P2) | Fabric hands off to **Triage** (T) |
| *(no product-level name; folded into Detect→Localize handoff)* | **E7 Curate → E8 Scope** (rest of P2) | **Triage** (3 stages: T) |
| **Localize** — decide *which CI / service* | **E9 Localize** (start of P3) | **Clock B / Diagnose** begins (D) |
| **Identify** — name *what kind of failure* (and optionally *which path*) | **E10 Identify** | **Diagnose** (D) |
| **Verify** — decide how strongly we claim cause | **Spans E10 (evidence/confidence rationale) through E11 Package (verdict handoff)** — Verify is not a separate E-stage; it is the confidence/tier judgment made while producing `EvidenceBundle` and closed out when `VerdictCard` is rendered | **Diagnose** close (D) |

Reading rules:

1. **Ingest is a phase, not a stage.** When a product doc says "Ingest is Partial (lab strong)" (per [`RCA_WORKFLOW_AND_NEXT.md`](../RCA_WORKFLOW_AND_NEXT.md) §2), that status is a rollup over E1–E5 individually, which can be at different readiness levels — check §6 below per stage before assuming uniform readiness.
2. **Verify has no dedicated E-stage.** It is a cross-cutting judgment (evidentiary tier, CARE, scoped causal check) that lives inside E10's evidence-gathering and gets locked at E11's packaging. Do not look for an `E-Verify` stage — it does not exist by design.
5-bit shorthand: **Ingest=E1–E5, Detect=E6, (Curate+Scope)=E7–E8, Localize=E9, Identify=E10, Verify=E10→E11.**
3. **"5+3+3" in vendor-teaching docs and "P1(5)+P2(3)+P3(3)" here are the same partition**, just named for vendor-native chronology (F/T/D) vs our stage IDs (E1–E11). They are not two different pipeline shapes.
4. **Normalize is E2 Identity.** Fabric teaching docs say Collect → Normalize; that Normalize stage is this HLD's E2, not a twelfth stage and not E10 Identify. [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) is the Normalize LLD.

## 6. Layer model (do not collapse)

| Layer | Runs | Required for product RCA? | Contract |
|-------|------|----------------------------|----------|
| **E Engineering** | Continuous (P1) + per-case (P2/P3) | Yes | Must localize a leaf without MTL/Bits |
| **I Interpret** | Per run or optional UI | No | Timeline/MTL/Bits retell evidence, not replace E-stages |

Layer I artifacts:

- Timeline
- MTL workbook
- Bits review

## 7. Three-phase and 11-stage overview

| Phase | Stage count | Stage IDs | Alias |
|------|-------------|-----------|-------|
| **P1 Always-on fabric** | 5 | E1-E5 | Clock A fabric / F |
| **P2 Case opens** | 3 | E6-E8 | Triage / T |
| **P3 Diagnose and close** | 3 | E9-E11 | Clock B / D |

<div class="ud-viz" id="hld-e1-e11-overview">
  <div class="ud-cap">Eleven stages · three phases (same pipeline, left to right then down)</div>
  <div class="ud-panel accent" style="margin-bottom:.75rem;">
    <h5>P1 · Always-on fabric</h5>
    <div class="ud-flow">
      <span class="ud-chip hit">E1 Collect</span>
      <span class="ud-arrow">→</span>
      <span class="ud-chip hit">E2 Identity</span>
      <span class="ud-arrow">→</span>
      <span class="ud-chip">E3 Topology</span>
      <span class="ud-arrow">∥</span>
      <span class="ud-chip">E4 Stores</span>
      <span class="ud-arrow">→</span>
      <span class="ud-chip">E5 Maintain</span>
    </div>
    <p class="ud-note" style="margin:.45rem 0 0;">After Identity, Topology and Stores both run; Maintain refreshes both.</p>
  </div>
  <div class="ud-down">↓ Detect reads topology + stores</div>
  <div class="ud-panel" style="margin-bottom:.75rem;">
    <h5>P2 · Case opens</h5>
    <div class="ud-flow">
      <span class="ud-chip">E6 Detect</span>
      <span class="ud-arrow">→</span>
      <span class="ud-chip">E7 Curate</span>
      <span class="ud-arrow">→</span>
      <span class="ud-chip">E8 Scope</span>
    </div>
  </div>
  <div class="ud-down">↓ Working set into diagnose</div>
  <div class="ud-panel">
    <h5>P3 · Diagnose and close</h5>
    <div class="ud-flow">
      <span class="ud-chip">E9 Localize</span>
      <span class="ud-arrow">→</span>
      <span class="ud-chip">E10 Identify</span>
      <span class="ud-arrow">→</span>
      <span class="ud-chip hit">E11 Package</span>
    </div>
    <p class="ud-note" style="margin:.45rem 0 0;">Localize still consults Topology and Stores (dashed reads in the written contracts).</p>
  </div>
</div>

## 8. Stage catalog (formal contracts)

The same template applies to every stage:

- Purpose
- Trigger
- Inputs
- Outputs
- Preconditions
- Postconditions
- Failure if missing
- Degradation behavior
- NFR sketch
- Reference implementation
- Lab proof (tagged with evidence maturity — see §9.1 legend)

### E1 Collect (P1)
- Purpose: ingest edge telemetry payloads from agents/OTLP/log streams. Owns **wire-format admission only** — it does not bind CIs (that is E2) and does not admit CMDB/change/ticket sources this pass.
- Trigger: continuous.
- Inputs: external telemetry envelopes.
- Outputs: `TelemetryEnvelope` (on-wire: `ingest.v1` JSONL). Source-asserted `ci_id`/`ci_type` are carried, not validated against topology.
- Preconditions: source auth/config available.
- Postconditions: incoming events are accepted into ingestion path as well-formed `ingest.v1` lines. Unknown `fact_kind` and schema-version mismatch reject or dead-letter (do not guess). Reserved unused classes: `change_event`, `cmdb_sync`, `ticket`.
- Failure if missing: no data enters pipeline.
- Degradation: partial source loss still allows scoped RCA on remaining sources.
- NFR sketch: sustained ingest throughput ≥ platform peak (validated, not just designed for — FR-K1/AC); backpressure safety with no correlation-affecting signal loss during soak. Measured bakeoff EPS is Grounded evidence, not a live product SLA ([`LLD-E1-Collect.md`](./LLD-E1-Collect.md) §6).
- Reference implementation: lean ingest bundle path; federated demo ingest stubs; Vector/Python fan-out smoke.
- Lab proof: both ERROR and SLOWDOWN runs depend on successful ingest. **[Grounded — MCP/vendor evidence]**
- LLD: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) — **Done** (2026-08-13)

### E2 Identity (P1)
- Purpose: stamp join keys so records are correlation-ready. Fabric alias: **Normalize**.
- Trigger: continuous per record.
- Inputs: `TelemetryEnvelope`.
- Outputs: `IdentifiedRecord` — this pass, an **overlay on the same `ingest.v1` line** (`tenant`+`ci_id`+`ci_type`, plus `identity.status` / `identity.bind_source` / `identity.aliases`). Not a second on-wire format. `service`/`env`/`version` stay optional `labels` (D-E2-2).
- Preconditions: identity strategy configured.
- Postconditions: each record is joinable with topology, stores, and a future ServiceOps CI/ticket on the same `ci_id`.
- Failure if missing: cross-modal joins collapse.
- Degradation: unresolved records move to unattributed queue (query surface over `identity.status != resolved`); they are never silently dropped (FR-B1). Synthesized placeholders are **not** localize or ServiceOps-ticket targets (D-E2-1).
- NFR sketch: entity-resolution accuracy ≥ 95% of resolvable signals (FR/AC §6) — the bar to hit and measure, not a result claimed; low-latency enrichment, deterministic keying.
- Reference implementation: topology `ci_type` lookup (ObserveOps corpus); CI bind table + plugin fallbacks (Motadata).
- Lab proof: DD/DT joins require identity before detect/localize. **[Grounded]**
- LLD: [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) — **Done** (2026-08-13)

### E3 Topology (P1)
- Purpose: maintain walkable dependency graph for neighborhood reasoning.
- Graph extension (Draft): interactive [Fusion](./observeops-fusion-guide.html) then normative [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) · worked example [`observeops-ci-graph.html`](./observeops-ci-graph.html). Schema is Grounded as an authored artifact; live E3 discovery remains Design-level. Does **not** replace this contract.
- Motadata fabric: after E2, **E3 Topology ∥ E4 Stores** — Pillar B GraphWriter admits post-E2 **`writer_stream.v1`** lines when a **`topology`** block is present ([`WRITER_REGULATOR.md`](../../pillar-ab-implementation/contracts/WRITER_REGULATOR.md); no Collect `fact_kind` router) and writes versioned `GraphSnapshot` under `map/`; see [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) §10.
- Trigger: continuous updates + periodic refresh.
- Inputs: `IdentifiedRecord`, discovery relations, optional CMDB enrich.
- Outputs: `GraphSnapshot`.
- Preconditions: identity keys must exist.
- Postconditions: queryable neighbors, directionality, depth.
- Failure if missing: localize cannot reason over propagation.
- Degradation: stale graph increases ambiguity and misranking risk.
- NFR sketch: freshness window and bounded staleness — product default for **`declared` edges**: soft-stale after **7 days**, hard-downgrade after **30 days** without corroboration or CMDB re-sync (operational-graph decision #4 · [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) §6). Bakeoff engines still lack markers.
- Reference implementation: lean graph walk; federated KG analog; Motadata Pillar B GraphWriter.
- Lab proof: ERROR cascades and SLOWDOWN path depth require topology. **[Grounded]**

### E4 Stores (P1)
- Purpose: persist queryable evidence over time under shared identity.
- Motadata fabric: Pillar A SketchWriter admits when a **`metric`** block is present on **`writer_stream.v1`** → `sketch.v1` in `history/` (**metrics-only**); parallel to E3, not sequential after it. Logs/traces use other evidence surfaces — see [`LLD-E4-Stores.md`](./LLD-E4-Stores.md) §0 · wire SoT [`WRITER_REGULATOR.md`](../../pillar-ab-implementation/contracts/WRITER_REGULATOR.md).
- Trigger: continuous writes.
- Inputs: `IdentifiedRecord`.
- Outputs: modality-specific query surfaces and history (Motadata: sketches; bakeoff: Lean/Fed stores).
- Preconditions: storage backends available.
- Postconditions: time-sliced evidence retrievable by CI and tags.
- Failure if missing: detect and identify have no historical evidence.
- Degradation: missing modality produces thin evidence bundles.
- NFR sketch: retention and query latency budgets (no numeric target yet — flag for LLD-E4 Done gate).
- Reference implementation: lean datasets and store abstractions; federated stores; Motadata Pillar A.
- Lab proof: MTL-like queries and identify evidence depend on E4. **[Grounded]**

### E5 Maintain (P1)
- Purpose: keep estate fresh (retention, indexing, discovery freshness, deploy feed).
- Motadata: maintains **`map/` validity** and **`history/` baselines** separately — does not create edges and does not merge rooms ([`LLD-E5-Maintain.md`](./LLD-E5-Maintain.md)).
- Trigger: scheduled/continuous maintenance.
- Inputs: store/index metadata, discovery updates, change feeds.
- Outputs: freshness baseline and maintain state.
- Preconditions: E3 and E4 operating.
- Postconditions: pipeline remains detect-ready.
- Failure if missing: data drift/staleness silently degrades RCA quality.
- Degradation: larger correlation windows needed, confidence drops.
- NFR sketch: index freshness and lifecycle correctness — declared-edge 7d/30d defaults live under E3/E5 (above); broader retention still open for LLD-E5 Done.
- Reference implementation: explicit in our HLD even when vendor stages differ; Pillar B `maintain_graph_validity` stub.
- Lab proof: not always visible in single run, but prerequisite for reliability. **[Design-level — no dedicated lab]**

### E6 Detect (P2)
- Purpose: emit fault signals for a configured Detect class.
- Trigger: per observation window or rule evaluation.
- Inputs: `GraphSnapshot`, store queries.
- Outputs: `Signal`.
- Preconditions: identity + stores + topology queryable.
- Postconditions: candidate fault signals exist, but no root cause claim.
- Failure if missing: no case opens automatically.
- Degradation: partial detection can be operator-seeded at scope/localize; **negative Detect (no signal fires) is a valid, documented outcome for some classes, not a defect** — see RESOURCE_CONTENTION evidence in §9.1.
- NFR sketch: detection latency and false-positive control; time-to-RCA p95 ≤ correlation window + target seconds (FR-K2, needs a filled number before LLD-E6).
- Reference implementation: rule/anomaly doors in both study lenses.
- Lab proof: ERROR has direct doors; SLOWDOWN may require alternate door. **[Grounded for ERROR/SLOWDOWN; Local-only for RESOURCE_CONTENTION/AVAILABILITY/MONITORING_UNAVAILABLE]**

### E7 Curate (P2)
- Purpose: collapse correlated signals into one case seed.
- Trigger: on detect signal arrival.
- Inputs: `Signal`, `GraphSnapshot`.
- Outputs: `CaseSeed`.
- Preconditions: at least one signal and merge policy available.
- Postconditions: one seed with merge rationale is emitted.
- Failure if missing: signal storm leaks directly to operators.
- Degradation: multiple seeds possible only under explicit policy override.
- NFR sketch: cross-telemetry grouping (one fault → one incident) ≥ 95% of scenarios (FR/AC §6); bounded merge latency, deterministic grouping.
- Reference implementation: required in our default policy (D3 — see §11, proposed Signed).
- Lab proof: DD multi-hot-service fog demonstrates need. **[Grounded]**

### E8 Scope (P2)
- Purpose: lock investigation working set (time + candidates + env/version).
- Trigger: on curated seed.
- Inputs: `CaseSeed`, topology/store context.
- Outputs: `WorkingSet`.
- Preconditions: seed must exist.
- Postconditions: bounded diagnosis domain established.
- Failure if missing: diagnose runs globally, noisy and expensive.
- Degradation: loose scopes increase ranking ambiguity.
- NFR sketch: scope build latency and candidate cap (no numeric target yet — flag for LLD-E8).
- Reference implementation: Tailor equivalent in 5+3+3 lens.
- Lab proof: both ERROR and SLOWDOWN rely on narrowed windows. **[Grounded]**

### E9 Localize (P3)
- Purpose: choose leaf claim based on Detect class semantics.
- Trigger: per scoped case.
- Inputs: `WorkingSet`, `GraphSnapshot`, store evidence.
- Outputs: `LeafClaim`.
- Preconditions: scoped candidate set available.
- Postconditions: one top leaf hypothesis returned.
- Failure if missing: no actionable root-cause target.
- Degradation: can return ranked candidates with lower confidence.
- NFR sketch: root-cause accuracy (top-1 = injected CI) ≥ 90% across scenario suite (FR/AC §6); deterministic ranking under fixed scope.
- Reference implementation: lean path walk; federated hop-to-hop narrowing.
- Lab proof: deepest error leaf for ERROR; self-time leaf for SLOWDOWN. **[Grounded]**

### E10 Identify (P3)
- Purpose: corroborate/rank leaf with multimodal evidence.
- Trigger: on leaf claim.
- Inputs: `LeafClaim`, `WorkingSet`, store queries.
- Outputs: `EvidenceBundle`.
- Preconditions: leaf claim exists and evidence stores reachable.
- Postconditions: evidence pointers and confidence rationale available. This is where **Verify** (5-stage model) is actually decided — evidentiary tier 1/2/3, CARE, scoped causal check (§5 note 2).
- Failure if missing: verdict exists but cannot be trusted/explained.
- Degradation: single-modality bundle allowed with explicit incompleteness note.
- NFR sketch: no-false-blame localization (S3-type: app-only fault, healthy infra) must pass — pass/fail gate, not a percentage (FR/AC §6); evidence lookup latency and reproducibility.
- Reference implementation: lean tier/signature checks; federated fusion evidence.
- Lab proof: KeyError stack/log/trace and SLOWDOWN self-time/CPU pointers. **[Grounded]**

### E11 Package (P3)
- Purpose: render operator-facing verdict handoff.
- Trigger: on evidence bundle completion.
- Inputs: `EvidenceBundle`.
- Outputs: `VerdictCard` and optional incident payload/narrative.
- Preconditions: leaf and evidence must be present.
- Postconditions: case is operationally consumable.
- Failure if missing: RCA output remains engineering-only and unclosed.
- Degradation: thin card allowed only when evidence completeness is flagged.
- NFR sketch: handoff latency and schema stability; alert-noise reduction ≥ 70% fewer actionable items than raw signals (FR/AC §6, informative for Package framing).
- Reference implementation: Problem-like card; optional Bits-style narrative.
- Lab proof: package behavior differs by vendor but remains required in our policy (D4 — see §11, proposed Signed). **[Grounded]**

## 9. Information contracts and worked flows

Directional object catalog:

- `TelemetryEnvelope` (E1 -> E2) — on-wire `ingest.v1`
- `IdentifiedRecord` (E2 -> E3,E4) — same `ingest.v1` line after identity overlay (`identity.*`); not a second schema this pass. Motadata fabric **fans out in parallel** after E2 (E3 Topology ∥ E4 Stores), not a forced E3-then-E4 sequence ([`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G12).
- `GraphSnapshot` (E3 -> E6,E7,E9)
- StoreEvidence / sketches (E4 -> E6,E9,E10) — Motadata Detect door C reads `sketch.v1`; case path joins `map/` ∥ `history/` at E8
- `Signal` (E6 -> E7)
- `CaseSeed` (E7 -> E8)
- `WorkingSet` (E8 -> E9)
- `LeafClaim` (E9 -> E10)
- `EvidenceBundle` (E10 -> E11)
- `VerdictCard` (E11 -> Operator/Incident)

Worked handoff examples:

### ERROR handoff (visual)

<div class="ud-viz" id="hld-error-handoff">
  <div class="ud-cap">ERROR path — what each stage passes forward</div>
  <div class="ud-strip">
    <div class="ud-seg base"><span class="ud-lab">E1</span><span class="ud-val">Telemetry envelope</span></div>
    <div class="ud-seg"><span class="ud-lab">E2</span><span class="ud-val">Identified service / route</span></div>
    <div class="ud-seg fault"><span class="ud-lab">E6</span><span class="ud-val">Error signal</span></div>
    <div class="ud-seg"><span class="ud-lab">E7</span><span class="ud-val">Curated seed</span></div>
    <div class="ud-seg"><span class="ud-lab">E8</span><span class="ud-val">Scoped call chain</span></div>
    <div class="ud-seg fault"><span class="ud-lab">E9</span><span class="ud-val">Deepest error leaf</span></div>
    <div class="ud-seg"><span class="ud-lab">E10</span><span class="ud-val">Stack / log / trace evidence</span></div>
    <div class="ud-seg base"><span class="ud-lab">E11</span><span class="ud-val">Verdict</span></div>
  </div>
  <p class="ud-note">Left to right is the handoff order for an ERROR-class case (E3–E5 stay in the fabric underneath).</p>
</div>

### SLOWDOWN handoff (visual)

<div class="ud-viz" id="hld-slowdown-handoff">
  <div class="ud-cap">SLOWDOWN path — what each stage passes forward</div>
  <div class="ud-strip">
    <div class="ud-seg base"><span class="ud-lab">E1</span><span class="ud-val">Telemetry envelope</span></div>
    <div class="ud-seg"><span class="ud-lab">E2</span><span class="ud-val">Identified op / version</span></div>
    <div class="ud-seg fault"><span class="ud-lab">E6</span><span class="ud-val">Latency signal or alternate seed</span></div>
    <div class="ud-seg"><span class="ud-lab">E7</span><span class="ud-val">Curated seed</span></div>
    <div class="ud-seg"><span class="ud-lab">E8</span><span class="ud-val">Scoped interval</span></div>
    <div class="ud-seg fault"><span class="ud-lab">E9</span><span class="ud-val">Longest self-time leaf</span></div>
    <div class="ud-seg"><span class="ud-lab">E10</span><span class="ud-val">Span self-time + CPU corroboration</span></div>
    <div class="ud-seg base"><span class="ud-lab">E11</span><span class="ud-val">Verdict</span></div>
  </div>
  <p class="ud-note">Same stage order as ERROR; Detect and Localize emphasize latency / self-time instead of error rate.</p>
</div>

## 9.1 Evidence-maturity legend (new in v1.0)

Every "Lab proof" line in §8 and every row in §10 is tagged with one of these levels. Do not read a **Local-only** tag as equivalent proof strength to **Grounded** — the gap is intentional and documented at the source (each local lab page carries its own "Detect honesty" note).

| Tag | Meaning | Current examples |
|---|---|---|
| **Grounded** | Vendor MCP/API pull or bakeoff scoreboard backs the claim; reproducible via cited run ID | ERROR/SLOWDOWN on both DT and DD; ObserveOps UC bakeoff (`adr001-rerun-20260723`) |
| **Local-only** | Break/heal script run and timestamped, but no vendor MCP/API pull this session — native Detect-door outcome (including negative Detect) not yet confirmed against the vendor UI/API | DD RESOURCE_CONTENTION, AVAILABILITY, MONITORING_UNAVAILABLE (2026-08-13; agent-task status `agent_task → promote after Observed run`) |
| **Design-level** | No dedicated lab exercises this stage directly; asserted from architecture necessity | E5 Maintain |
| **Planned** | Named in a backlog, not yet run | none currently open in this HLD's scope |

Promotion path: a **Local-only** lab is promoted to **Grounded** by pulling the corresponding vendor MCP/API evidence and updating the category's `mtlDoc`/`bitsDoc` entry in [`dd-detect-categories.js`](../dd-detect-categories.js) — see the three `docs/agent-tasks/dd-*.md` prompts for the exact promotion checklist.

## 10. Detect-class plug-in matrix

| Detect class | E6 feature focus | E9 leaf rule | E10 evidence emphasis | Evidence maturity (this repo, 2026-08-13) |
|--------------|------------------|--------------|------------------------|---------------------------------------------|
| **ERROR** | error rate, status:error | deepest error leaf | stack, logs, error spans | Grounded (DT + DD) |
| **SLOWDOWN** | duration, p95, saturation cues | longest self-time leaf | self-time spans, CPU/service latency | Grounded (DT + DD) |
| **AVAILABILITY** | process/container down, caller cascade | first-down entity in the caller chain | process/container check, caller APM failures | Grounded (DT) · Local-only (DD) |
| **MONITORING_UNAVAILABLE** | telemetry gap while process stays up | entity with the coverage gap | absence-of-signal pattern, cross-modal comparison | Grounded (DT) · Local-only (DD) |
| **RESOURCE_CONTENTION** | CPU/memory saturation, semantic (no universal vendor stamp) | contended entity even if symptom is negative | host pack / infra Watchdog signal, or explicit negative-Detect note | Grounded (DT) · Local-only (DD) |

Curate, Scope, and Package remain unchanged across classes. This pipeline's own E6 Detect stage does **not** require a 1:1 vendor category stamp to consider a class supported — RESOURCE_CONTENTION explicitly treats a negative Detect outcome (symptom present, no alert fires) as a valid, honestly-reported result rather than a gap to be papered over.

## 11. Cross-cutting concerns

- Single identity thread: E2 keys must map to E3 nodes and E4 query keys **and** to a future ServiceOps CI / ticket on the same `ci_id`.
- Parallel modalities: metrics, traces, logs can remain separate query planes with shared identity.
- Volatility gradient: P1 high churn, P2 episodic grouping, P3 locked working sets.
- Layer boundary: Layer I can consume outputs, never gate E-stage progression.

### 11.1 Identity namespace (v1.1 — ServiceOps-joinable)

One namespace for ObserveOps RCA and later ServiceOps joins. Collect still produces telemetry only; this section freezes the keys so CMDB/change/ticket can attach later without a schema break.

| Field | Role |
|---|---|
| `tenant` + `ci_id` | Primary join key for E3, E4, E9, E11, and a future ServiceOps ticket/CI |
| `ci_type` | Extensible taxonomy (additive; corpus six plus `Host` / `Monitor` / `Unknown`) |
| `identity.status` | `resolved` \| `unattributed` \| `synthesized` |
| `identity.bind_source` | How the bind was chosen (audit, not a competing key) |
| `identity.aliases` | Source-native keys (hostname, IP, monitor id, `object.name`, later CMDB id) that ServiceOps can match |
| `labels.service` / `labels.env` / `labels.version` | Optional Unified-Service-Tags-style hints; **not** required top-level (D-E2-2) |

Rules:

- Aliases live on the identity record. They are not competing primary keys.
- E11 Package later creates a ServiceOps incident **on this same `ci_id`** (FR-J1). Collect/Normalize must not emit unstable or invented roots that would become tickets.
- `identity.status != resolved` is not a localize target and not a ServiceOps-ticket target (D-E2-1).
- Reserved unused `fact_kind` values this pass: `change_event`, `cmdb_sync`, `ticket`. Do not implement those Collect sources here.

## 12. Implementation map (internal engineering)

| Stage band | Lean (primary ObserveOps eval engine) | Federated (optional path) | Future ingest path |
|------------|----------------------------------------|----------------------------|--------------------|
| E1-E5 | `lean-pipeline/core_engine/observeops/ingest/` and data bundle flow | `federated-pipeline/poc/` stores and adapters | [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) |
| E6-E8 | detect/rules + case seed logic in lean orchestrator | Panorama-triggered entry + orchestrator narrowing | same signal model target |
| E9-E11 | `lean-pipeline/core_engine/observeops/engine.py` tiered escalation | Murphy -> Nezha -> fused verdict | pluggable if contracts preserved |
| Visual reference | [`eleven-subsystem-mechanisms.html`](../eleven-subsystem-mechanisms.html) (canvas variant: [`eleven-subsystem-mechanisms-storyboard.html`](../eleven-subsystem-mechanisms-storyboard.html)) | same mechanisms page | same stage contracts |

Lean and federated differ in diagnosis mechanics but both map to the same P3 stage contracts.

## 13. ADRs and open decisions

| Decision | Default in HLD | v0.2 status | v1.0 proposed | v1.1 status | Evidence |
|----------|----------------|-------------|---------------|-------------|----------|
| D1 Topology model | Hybrid: derived edges first, typed IDs when cheap | Review | Proposed: Signed | **Signed** | Lean's `InvocationGraph` (`topology.json`) already ships typed CI classes (NetworkPort, HypervisorHost, Datastore, VM, GuestOS, Service) — hybrid model in production on the bakeoff |
| D2 Store geometry | Separate product queries, shared identity | Review | Proposed: Signed | **Signed** | DT/DD teaching hubs: separate Metrics/APM/Logs (or Grail) rails joined by shared identity tags — matches E4 as-implemented |
| D3 Curate strength | Required: must emit one seed by default | Must be Signed | Proposed: Signed | **Signed** | Lean orchestrator case-seed logic shipped (ROADMAP Ship — Done); DD multi-hot-service fog lab (§8 E7) |
| D4 Package policy | Required verdict card for close; narrative optional | Must be Signed | Proposed: Signed | **Signed** | Lean CLI/HTTP SRE report fields shipped (ROADMAP Ship — Done) |
| D5 AI placement | Optional door in Detect and optional narrator in Package | Review | Review | **Review (unchanged)** | Nothing in the repo commits to an AI door or narrator. A **third geometry** is now documented as teaching evidence, not an ADR flip: Edge Delta persistent AI Team + Issue/Overview (Public framing + Observed UI 2026-08-14) — see [`ed-ai-team-hub.html`](../ed-ai-team-hub.html) |
| D-E2-1 Bind-miss policy | Synthesize a flagged placeholder; do not treat it as a localize/ticket target. Schema-invalid poison is E1 dead-letter, not E2 synthesis | — | Open in LLD-E2 draft | **Signed** | Converters already synthesize (`Unknown` / `monitor-{id}`); Vector docs said dead-letter. v1.1 reconciles: keep synthesis for observability of misses; `identity.status != resolved` is not an E9/E11/ServiceOps CI. FR-B1 unattributed queue is the query surface, not silent drop |
| D-E2-2 Service tags | `service` / `env` / `version` stay optional `labels`; primary join key remains `tenant`+`ci_id` | — | Open in LLD-E2 draft | **Signed** | Avoids an `ingest.v1` required-field break on the frozen corpus; Unified Service Tags remain recommended labels, not a second identity plane |

**Sign-off note (v1.1):** D1–D4, D-E2-1, and D-E2-2 are Signed. D5 stays Review (the 2026-08-14 Edge Delta teaching annex does not flip it).

## 14. Failure modes and degradation

- E6 sparse/empty signals: P2 may stall; classify as detect coverage gap, not localize defect. **Exception:** for RESOURCE_CONTENTION-class semantics, an empty E6 can be the correct outcome (§9.1) — check evidence-maturity tag before treating an empty signal as a gap.
- E7 skipped: multi-service signal fog reaches operator with no primary seed.
- E3 stale graph: localize may choose wrong neighborhood/leaf.
- E4 modality loss: identify produces thin bundle and package must flag incompleteness.
- E5 lag: freshness decay causes delayed or inconsistent detection.

## 15. NFR baseline ownership

HLD ownership allocation, now with targets pulled from [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](./multi-telemetry-rca-functional-and-acceptance-criteria.md) §6 where they exist (targets quantified further in LLD):

- **P1 (E1-E5):** ingest throughput ≥ platform peak (soak-validated) — E1 bakeoff EPS numbers are Grounded evidence, not a live product SLA ([`LLD-E1-Collect.md`](./LLD-E1-Collect.md) §6); entity-resolution accuracy ≥ 95% of resolvable signals — the bar to **measure** (`resolved / resolvable` on a labeled bind set), not a result claimed ([`LLD-E2-Identity.md`](./LLD-E2-Identity.md) §7); retention/indexing freshness (no number yet — LLD-E3/E4/E5 to fill).
- **P2 (E6-E8):** cross-telemetry grouping ≥ 95% of scenarios; correlation latency = time-to-RCA p95 ≤ correlation window + target seconds (number to be filled before LLD-E6); deterministic grouping.
- **P3 (E9-E11):** root-cause accuracy (top-1) ≥ 90%; no-false-blame localization must pass (pass/fail); alert-noise reduction ≥ 70% fewer actionable items; diagnosis latency, reproducibility, evidence completeness (LLD-E9/E10/E11 to quantify latency).

These targets originate in the Motadata multi-telemetry FR/AC spec, not from this pipeline's own measurement yet — treat them as **the bar to hit**, not **a result already achieved**. Current bakeoff evidence (ADR-001: both engines 5/5 root-CI on UC-1..UC-5) is consistent with the ≥90% accuracy target on that small corpus but is not a substitute for measuring against this larger target set.

## 16. Traceability appendix (light)

| Stage band | Closest FR/AC mapping |
|------------|------------------------|
| E1-E2 | FR-A (ingest/normalize), FR-B (entity resolution) |
| E3-E5 | FR-C (topology/time), FR-I/J (operability/freshness) |
| E6-E8 | FR-D (correlation and dedupe) |
| E9-E10 | FR-E/F (root cause + evidence) |
| E11 | FR-G/H (incident output and operator handoff) |

Primary FR/AC reference: [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](./multi-telemetry-rca-functional-and-acceptance-criteria.md).

## 17. Revision history

| Version | Date | Change |
|---|---|---|
| v0.2 | 2026-08-13 (earlier same day) | First formal draft: C4 diagram, 11-stage catalog, contracts, ADRs (mostly Review), LLD backlog |
| v1.0 | 2026-08-13 | Full rewrite following docs-hub audit: added §5 stage-vocabulary crosswalk (normative), added §9.1 evidence-maturity legend, extended §10 Detect-class matrix with DD local-only categories, filled §15 NFR targets from FR/AC §6, proposed sign-off for D1–D4 with cited evidence (§13), added §0/§2 (why-this-revision, goals/non-goals). HTML companion `observeops-pipeline-hld.html` **resynced same day** — crosswalk section, E6 evidence-maturity note, and ADR sign-off proposals added there; this markdown remains the canonical full text (NFR targets, evidence-maturity legend, revision history live only here). |
| v1.1 | 2026-08-13 | Patch (not a rewrite): §4 identity-join note; §5 rule 4 (Normalize = E2); §8 E1/E2 tightened (telemetry-only Collect; `IdentifiedRecord` overlay); §11.1 identity namespace; D1–D4 Signed; D-E2-1 / D-E2-2 Signed; D5 still Review; LLD-E1 and LLD-E2 marked Done. HTML companion resynced. |
| v1.1a | 2026-08-14 | Teaching annex only: Edge Delta L0 hub added as a third independent vendor lens. D5 stays Review; evidence column cites ED AI Team geometry. No contract or ADR flip. |
| v1.1b | 2026-09-17 | P1 LLD realign: §8 E3 freshness 7d/30d; Motadata E3∥E4 fan-out; §9 object catalog note; LLD-E3/E4 dual-path Drafts; LLD-E5 Maintain Design stub. |

## 18. LLD backlog and HLD-to-LLD gate

LLD backlog:

1. [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) — **Done** (2026-08-13; Collect / `ingest.v1`)
2. [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) — **Done** (2026-08-13; Normalize / Identity overlay)
3. [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) — **Draft for review** (v1.1 dual-path: Motadata `map/` + bakeoff load)
4. [`LLD-E4-Stores.md`](./LLD-E4-Stores.md) — **Draft for review** (v1.1 dual-path: Motadata sketches + bakeoff stores)
5. [`LLD-E5-Maintain.md`](./LLD-E5-Maintain.md) — **Design-level stub** (v0.1)
6. `LLD-E6-Detect` — backlog
7. `LLD-E7-Curate` — backlog
8. `LLD-E8-Scope` — backlog
9. `LLD-E9-Localize` — backlog
10. `LLD-E10-Identify` — backlog
11. `LLD-E11-Package` — backlog

Gate for each LLD:

- references stage ID and purpose from this HLD,
- defines concrete schema/API for each I/O object it owns,
- includes one acceptance test path from ObserveOps corpus/lab replay,
- states the evidence-maturity tag (§9.1) for whatever lab/bakeoff run backs its acceptance test.

Layer I docs are not `LLD-E*` unless investigation notebook is productized later.

## 19. References and annexes

- Canonical compare: [`COMPARABLE_PIPELINE_DT_DD.md`](../COMPARABLE_PIPELINE_DT_DD.md)
- Edge Delta L0 (independent third lens): [`ed-ai-team-hub.html`](../ed-ai-team-hub.html) · [`EDGEDELTA_PRODUCTION_PIPELINE.md`](../EDGEDELTA_PRODUCTION_PIPELINE.md) · [`edgedelta-tenant-evidence-2026-08-14.md`](../edgedelta-tenant-evidence-2026-08-14.md). Geometry compare (not a third lab): [`comparable-pipeline-dt-dd.html`](../comparable-pipeline-dt-dd.html) §0.
- Federated vs 5+3+3 gap analysis: [`FEDERATED_VS_DT_PIPELINE_GAPS.md`](../FEDERATED_VS_DT_PIPELINE_GAPS.md)
- Mechanisms visual: [`eleven-subsystem-mechanisms.html`](../eleven-subsystem-mechanisms.html) · storyboard variant: [`eleven-subsystem-mechanisms-storyboard.html`](../eleven-subsystem-mechanisms-storyboard.html)
- DD Detect-category evidence source: [`dd-detect-categories.js`](../dd-detect-categories.js), [`dd-detect-category-hub.html`](../dd-detect-category-hub.html)
- Glossary aliases: [`urca-glossary.html`](./urca-glossary.html)
- FR/AC targets: [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](./multi-telemetry-rca-functional-and-acceptance-criteria.md)
- HTML companion: [`observeops-pipeline-hld.html`](./observeops-pipeline-hld.html) *(resynced to v1.1 — summary view; this file is canonical)*
- Collect / Normalize LLDs: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](./LLD-E2-Identity.md)
- Envelope + identity overlay: [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md)

---

## Doc hub contract (navigation)

Global site bar (`doc-nav.js`) remains the single site menu. Flat links stay on the bar; vendor and bakeoff pages nest under dropdown groups:

`Docs index` · `Glossary` · `Our HLD` · **Vendor survey** (DT hub · DD hub · ED hub · Obs 1.0/2.0/3.0 · DT vs DD vs ED) · **Bakeoff** (Fed vs DT · Lean · Federated eval) · `Motadata FR/AC` · `PoC console`
