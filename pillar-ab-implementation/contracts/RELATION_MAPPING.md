# Relation mapping — Fusion camelCase wire ↔ Motadata Dest storage

**Canonical on `writer_stream.v1` / `graph_write_intent.v1`:** Fusion/OneOps **eleven** stored edge types (camelCase).  
**Dest `graph_edge.v1` today:** Motadata **fifteen** SCREAMING_SNAKE `edge_type` values (unchanged until Dest schemas are refreshed).

GraphWriter / publish_map maps intent → Dest using this table. Reverse mapping is for lab fixtures migrating off snake_case `ingest.v1`.

---

## 1. Fusion eleven (wire / intent enum)

| Wire `relation` | Plain meaning (Fusion SKG) | Reverse name (docs only) |
|-----------------|----------------------------|---------------------------|
| `composedOf` | Whole → part composition | `partOf` |
| `contains` | Containment (detach lifecycle) | `containedIn` |
| `runsOn` | Workload executes on host/runtime substrate | `runs` |
| `dependsOn` | Functional need | `usedBy` |
| `communicatesWith` | Observed traffic / talk-to | (often symmetric) |
| `realizes` | Service spine / realization | `realizedBy` |
| `memberOf` | Membership in cluster/group | `hasMember` |
| `manages` | Control-plane manages target (not blast-radius) | `managedBy` |
| `ownedBy` | Ownership → Party | `owns` |
| `locatedIn` | Placement → Facility | `houses` |
| `succeedsLifecycleOf` | Lifecycle successor (`lifecycleSubtype`) | `succeededBy` |

Computed-only (never on write intent): `impactedBy`, `reaches`, `sharesFailureDomain`, `criticalPath`.

---

## 2. Map Fusion → Motadata `graph_edge.v1.edge_type`

| Fusion wire | Motadata Dest `edge_type` | Direction note |
|-------------|---------------------------|----------------|
| `dependsOn` | `DEPENDS_ON` | Same arrow (dependent → provider) |
| `runsOn` | `RUNS_ON` | Same arrow |
| `communicatesWith` | `COMMUNICATES_WITH` | Same |
| `memberOf` | `MEMBER_OF` | Same |
| `composedOf` | `PART_OF` | **Flip endpoints** when writing Motadata: Fusion `composedOf(A→B)` (A contains B) ↔ Motadata `PART_OF(B→A)` (B is part of A). Prefer storing Motadata as child→parent `PART_OF` to match existing PoC fixtures. |
| `contains` | *(no Motadata twin)* | PoC: phased skip or map to `PART_OF` only when product agrees; default **skip** until Dest enum expands |
| `realizes` | *(no Motadata twin)* | Skip / quarantine until Dest enum expands |
| `manages` | *(no Motadata twin)* | Skip until Dest enum expands |
| `ownedBy` | *(no Motadata twin)* | Skip until Dest enum expands |
| `locatedIn` | `HOSTED_ON` *(weak)* | Only when Facility≈hypervisor semantics; else skip |
| `succeedsLifecycleOf` | *(no Motadata twin)* | Skip until Dest enum expands |

---

## 3. Legacy Motadata fifteen → Fusion wire (fixture migration)

| Legacy ingest `relation` (snake) | Motadata storage | Fusion wire |
|----------------------------------|------------------|-------------|
| `depends_on` | `DEPENDS_ON` | `dependsOn` |
| `runs_on` | `RUNS_ON` | `runsOn` |
| `communicates_with` | `COMMUNICATES_WITH` | `communicatesWith` |
| `member_of` | `MEMBER_OF` | `memberOf` |
| `part_of` | `PART_OF` | Prefer emit Fusion `composedOf` with **flipped** endpoints (parent→child), or keep documenting `partOf` as reverse-only |
| `hosted_on` | `HOSTED_ON` | Prefer `runsOn` when guest→hypervisor; else keep Motadata-only until Dest refresh |
| `mounts` | `MOUNTS` | No Fusion twin — Motadata-only / skip on new wire |
| `connects_to` | `CONNECTS_TO` | Often `communicatesWith` if L4/L7 talk; else Motadata-only |
| `backs` | `BACKS` | Motadata-only |
| `uses` | `USES` | Prefer `dependsOn` when functional need; else Motadata-only |
| `routes_through` | `ROUTES_THROUGH` | Motadata-only |
| `authenticates_via` | `AUTHENTICATES_VIA` | Motadata-only (or `dependsOn` + attributes) |
| `monitored_by` | `MONITORED_BY` | Often `manages` reverse — Motadata-only until `manages` lands in Dest |
| `backed_up_by` | `BACKED_UP_BY` | Motadata-only / `succeedsLifecycleOf` subtype `backup` when migrating |
| `clustered_with` | `CLUSTERED_WITH` | Often `memberOf` shared parent — Motadata-only |

---

## 4. Evidence mapping (optional helper)

Legacy PoC `discovered_via.evidence_type` → Fusion `evidenceSource` (heuristic):

| Legacy | Prefer `evidenceSource` |
|--------|-------------------------|
| `authoritative` | `agent` / `api` / `discovery` |
| `declared` | `iac` / `service_mapping_session` / `manual` |
| `corroborating` | `traffic` / `log_inference` |

Confidence floors (Fusion defaults): agent/api 0.95 · discovery 0.90 · iac 0.85 · traffic 0.75 · log_inference 0.70 · ai_inferred 0.60 · manual 1.00 (TTL required).

---

## 5. Wave-1 writers

Emit / admit on the new wire first: `runsOn`, `dependsOn`, `communicatesWith`, `composedOf` (↔ `PART_OF`), `memberOf`. Other Fusion types may appear on the schema enum but Dest publish **skips** until Motadata `graph_edge.v1` grows or Dest is remodeled.
