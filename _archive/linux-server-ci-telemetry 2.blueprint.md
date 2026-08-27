# Blueprint: `linux-server-ci-telemetry 2.json`

This document explains the JSON as a **CI-centric telemetry knowledge graph blueprint**.

## 1) Envelope / Metadata layer

Top-level identity fields:

- `schema_version`
- `artifact_type`
- `generated_for`
- `graph_model`
- `_status`
- `cross_references`

Purpose:

- Identifies what this artifact is.
- Captures generation status and expected sibling references (for example CI relations or KPI catalog).

---

## 2) Taxonomy + Resolution policy layer

Main blocks:

- `signal_classes`
- `identity_model`

`identity_model` defines:

- Match strategies (`exact`, `normalized`, `composite`, etc.)
- Scope levels (`host`, `instance`, etc.)
- Normalization rules
- Ambiguity policy

Purpose:

- Defines the binding rules before CI-specific entries are evaluated.
- Prevents silent mis-attachment of telemetry.

---

## 3) Relationship semantics layer

Main blocks:

- `relationship_telemetry`
- `root_relationship_derivation`

`relationship_telemetry` provides generic relation inference contracts:

- Edge type
- Source telemetry
- Required signal fields
- Direction inference
- Evidence type

`root_relationship_derivation` provides root-CI-specific derivation playbooks:

- Root CI context (`root_ci`)
- Related CI, relation, hop/directness, role
- Ranked derivation methods with source/field/confidence/evidence type

Purpose:

- Explains **how relationships are proven**, not just listed.

---

## 4) Instance data layer (materialized graph content)

Main blocks:

- `ci_telemetry` (CI nodes)
- `edges` (CI-to-CI relationships)
- `telemetry_key_index` (runtime key resolver index)
- `fault_signatures` (symptom-to-cause templates)

### `ci_telemetry`

Per-CI entries include:

- CI identity (`ci_id`, `ci_name`, `ci_type`, `ci_class`, `tier`)
- Monitoring context (`monitored_via`, `kpi_catalog_ref`)
- CI-level identity mapping details (`identity.match_rules`)
- Telemetry/RCA context (`telemetry`, `rca`, etc.)

### `edges`

Concrete relationship assertions:

- `from`
- `to`
- `type`
- `criticality`
- `discovered_via`

### `telemetry_key_index`

Operational lookup for payload resolution:

- Telemetry key and scope
- Match strategy/confidence
- Resolved CI target
- Parent scoping and instance-key details where needed

### `fault_signatures`

RCA guidance templates:

- Symptom
- Candidate root cause CIs
- Confirmation checks/signals
- Severity and blast radius

Purpose:

- Converts policy into runnable CI binding + RCA content.

---

## 5) Governance / quality layer

Main blocks:

- `unresolved_strategy`
- `coverage_summary`

`unresolved_strategy` defines fallback and unresolved handling (no guess-attach).

`coverage_summary` tracks:

- Coverage counts
- Evidence type mix
- Known gaps
- Assumptions and enrichment status

Purpose:

- Makes binding quality observable and auditable.

---

## End-to-end mental flow

Read this JSON in the following order:

1. `identity_model` + `signal_classes` (interpretation policy)
2. `relationship_telemetry` + `root_relationship_derivation` (relationship derivation rules)
3. `ci_telemetry` (node catalog)
4. `telemetry_key_index` (runtime resolver)
5. `edges` (materialized relationships)
6. `fault_signatures` (RCA reasoning templates)
7. `unresolved_strategy` + `coverage_summary` (quality guardrails)

---

## Compact nesting map

- Document metadata
- Interpretation policy
  - Signal taxonomy
  - Identity resolution policy
- Relationship derivation policy
  - Generic edge inference
  - Root-CI-specific derivation
- Materialized graph + resolver
  - CI nodes
  - Edges
  - Telemetry key index
  - Fault signatures
- Quality controls
  - Unresolved handling
  - Coverage summary
