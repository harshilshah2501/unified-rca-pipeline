# Edge triplet allowlist — wave-1 write contract

**Status:** Locked for Motadata Pillar B GraphWriter (2026-09-28).  
**Priority:** First-class write gate alongside identity and relation catalog.  
**Companion:** [`WRITER_REGULATOR.md`](./WRITER_REGULATOR.md) · [`RELATION_MAPPING.md`](./RELATION_MAPPING.md) · [`IDENTIFIED_STREAM_REJECT.md`](./IDENTIFIED_STREAM_REJECT.md)  
**North star:** Fusion / OneOps full `(sourceClass, edge, targetClass)` matrix under `pillar-b/reference/` (Task 06) — not fully enumerated here yet.

---

## 1. Locked choices

| Decision | Choice |
|----------|--------|
| Strictness | **Hard reject** — illegal triplet → DROP (`illegal_edge_triplet`), not warn-and-write |
| Type grain | **Motadata storage types** (`service`, `host`, `process`, `db`, …) after `to_storage_type` |
| Missing / unknown endpoint type | **DROP edge** (`missing_endpoint_type`) — do not invent `Service` for a missing `dst_ci_type` |
| `memberOf` | **Deferred** — not wave-1 emit until a collection / group CI type exists |
| `contains` (Fusion) | **Dest-skip** — no Motadata twin; do not smuggle into `PART_OF` / `MEMBER_OF` |
| Scope | Wave-1 Motadata emit relations only: `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of` |

A write is legal only when `(src_storage_type, relation, dst_storage_type)` is on the allowlist below. Unknown triplets are not “fixed on walk.”

---

## 2. When the check runs

After GraphWriter has:

1. `fact_kind == topo_update` (lab) or GraphRegulator admitted a topology block (target wire),
2. `identity.status == resolved`,
3. both endpoints are CI-eligible (`may_emit_vertex`),
4. `relation` is wave-1 **emit** (not unknown, not phased skip),

then resolve types and check the triplet **before** upserting the edge.

**Type resolution order** (per endpoint):

1. Existing map node’s Motadata `type` if the CI is already on `GraphState`, else  
2. Stream field (`ci_type` / `src_ci_type` / `dst_ci_type`) mapped with `to_storage_type`, else  
3. **`missing_endpoint_type`** — DROP; do not default the destination to `Service`.

---

## 3. Reject codes

| Code | When |
|------|------|
| `missing_endpoint_type` | Source or destination storage type cannot be resolved |
| `illegal_edge_triplet` | Both types known, but `(src, relation, dst)` is not on the allowlist |

Existing codes unchanged: `identity_*`, `never_ci_vertex`, `unknown_relation`.

---

## 4. Allowlist (Motadata storage types × ingest `relation`)

Direction is **Motadata Dest arrow** (same as today’s `graph_edge.v1`):

- `runs_on` / `hosted_on` / `depends_on` / `communicates_with`: Fusion camelCase same arrow (`runsOn`, …).  
- `part_of`: Motadata **child → parent**. Fusion `composedOf` is parent → child; publish **flips** endpoints ([`RELATION_MAPPING.md`](./RELATION_MAPPING.md)).

### 4.1 `runs_on` (guest executes on substrate)

| Source | Target | Why valid |
|--------|--------|-----------|
| `process` | `host`, `node` | Runtime / OS process on machine |
| `service` | `host`, `node` | App service hosted on machine |
| `pod` | `host`, `node` | Workload on node |
| `container` | `host`, `node` | Container on host/node |
| `db` | `host`, `node` | Database instance on machine |
| `queue` | `host`, `node` | Broker process on machine |

### 4.2 `hosted_on` (guest / VM on hypervisor family)

| Source | Target | Why valid |
|--------|--------|-----------|
| `host` | `host` | Guest OS / VM → hypervisor (both stored as `host` today) |
| `service`, `process`, `pod`, `container`, `db`, `queue` | `host` | Same family as `runs_on` when the product stamps `hosted_on` |

### 4.3 `depends_on` (declared functional need)

| Source | Target | Why valid |
|--------|--------|-----------|
| `service` | `service`, `db`, `queue`, `endpoint`, `business_service` | Service needs provider |
| `business_service` | `service`, `db`, `queue` | Business offering needs app/data |
| `pod`, `k8s_deployment` | `service`, `db`, `queue`, `endpoint` | Workload needs dependency |
| `customer` | `business_service`, `service` | Optional tenant → offering (rare in lab) |

### 4.4 `communicates_with` (observed traffic)

| Source | Target | Why valid |
|--------|--------|-----------|
| Any of `service`, `host`, `pod`, `container`, `db`, `queue`, `endpoint`, `network`, `node`, `process` | Same set | Peer talk; **not** auto-promoted to `depends_on` |

### 4.5 `part_of` (Motadata child → parent)

| Source (child) | Target (parent) | Why valid |
|----------------|-----------------|-----------|
| `service` | `business_service` | App is part of business service |
| `process`, `container`, `volume` | `host`, `pod`, `service`, `db` | Structural part; part dies with whole |
| `endpoint` | `service`, `host` | Bound endpoint of a service/host |
| `pod` | `k8s_deployment`, `namespace` | Workload under deploy/namespace when modeled as composition |

---

## 5. Why some pairings are invalid (teaching table)

| Claimed edge | Example | Reject / redirect | Why |
|--------------|---------|-------------------|-----|
| `runs_on` | `service` → `service` | `illegal_edge_triplet` | Hosting is guest→substrate, not peer apps |
| `runs_on` | `service` → `business_service` | `illegal_edge_triplet` | Business layer is not a runtime host; use `part_of` / `depends_on` |
| `depends_on` | `service` → `host` | `illegal_edge_triplet` | That is hosting — use `runs_on` / `hosted_on` |
| `depends_on` | inferred only from APM peer | (do not emit) | Raw traffic is `communicates_with`; do not invent `depends_on` |
| `part_of` | `business_service` → `service` | `illegal_edge_triplet` | Wrong Motadata direction; child→parent only |
| `part_of` | Namespace→Pod as “contains” | Dest-skip / not allowlisted as relocate semantics | Fusion `contains` (detach lifecycle) ≠ `composedOf`; no Motadata twin yet |
| `member_of` | any | phased skip (not wave-1) | No collection CI type in Motadata wave-1 |
| `communicates_with` | promoted to `depends_on` | N/A (writers must not) | Talk ≠ declared need; blast-radius must not treat talk as depend |
| any | missing `dst_ci_type` and CI not on map | `missing_endpoint_type` | Guessing `Service` poisons the allowlist |

Anti-patterns locked from Fusion philosophy (enforce by absence from the allowlist):

1. Hosting ≠ `depends_on`  
2. Raw traffic ≠ `depends_on`  
3. Realization / control-plane ownership ≠ `depends_on` / `part_of` until Dest has `realizes` / `manages`

---

## 6. Implementation pointer

- Code: `pillar-b/poc/graph/edge_triplets.py` (`check_edge_triplet`) called from `graph_builder.apply_topo_stream` and bootstrap edge load.  
- Tests: `pillar-b/poc/graph/tests/unit/test_edge_triplets.py`.

When Dest schemas grow Fusion classes, widen this table (or switch grain to Fusion class before `to_storage_type`) without changing reject code names.
