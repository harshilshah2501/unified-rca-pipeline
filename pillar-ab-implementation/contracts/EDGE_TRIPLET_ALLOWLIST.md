# Edge triplet allowlist — Motadata fifteen-relation write contract

**Status:** Locked for Motadata Pillar B GraphWriter (2026-09-28; full fifteen catalog 2026-09-28).  
**Priority:** First-class write gate alongside identity and relation catalog.  
**Companion:** [`WRITER_REGULATOR.md`](./WRITER_REGULATOR.md) · [`RELATION_MAPPING.md`](./RELATION_MAPPING.md) · [`IDENTIFIED_STREAM_REJECT.md`](./IDENTIFIED_STREAM_REJECT.md)  
**North star:** Fusion / OneOps class matrix under `pillar-b/reference/` (Task 06) for richer grain later.

---

## 1. Locked choices

| Decision | Choice |
|----------|--------|
| Relation scope | **All fifteen** Motadata catalog relations — pairing is defined here for every name; **no wave-1 / wave-2 split** on this contract |
| Strictness | **Hard reject** — illegal triplet → DROP (`illegal_edge_triplet`), not warn-and-write |
| Type grain | **Motadata storage types** (`service`, `host`, `process`, `db`, …) after `to_storage_type` |
| Missing / unknown endpoint type | **DROP edge** (`missing_endpoint_type`) — do not invent `Service` |
| Fusion-only edges (`contains`, `realizes`, `manages`, …) | Not Motadata Dest names — out of this table until Dest enum grows ([`RELATION_MAPPING.md`](./RELATION_MAPPING.md)) |

A write is legal only when `(src_storage_type, relation, dst_storage_type)` is on the allowlist below. Unknown triplets are not “fixed on walk.”

**Fifteen ingest names:** `depends_on`, `runs_on`, `mounts`, `connects_to`, `backs`, `uses`, `hosted_on`, `member_of`, `part_of`, `routes_through`, `authenticates_via`, `monitored_by`, `backed_up_by`, `clustered_with`, `communicates_with`.

---

## 2. Admit order (four checks)

GraphWriter only writes a **topology claim**: two endpoint ids + one relation. Target wire: optional `topology` block on `writer_stream.v1` (no `fact_kind`). Lab still uses flat `topo_update` lines until migrated — same checks.

| # | Check | Question | Pass | Fail |
|---|--------|----------|------|------|
| **1** | Complete claim | Are `src_ci_id`, `dst_ci_id`, and `relation` all present? | Continue | GraphWriter **NOOP** |
| **2** | Resolved | Is `identity.status = resolved`? | Continue | **DROP** `identity_*` |
| **3** | CI on the map | May each endpoint be a configuration-item vertex (not Alert / Metric / ticket / …)? | Continue | **DROP** `never_ci_vertex` |
| **4** | Edge quality | Relation in the fifteen-name catalog + both Motadata types known + pair on §4? | **WRITE** | See §2.2 |

Flush later still validates Dest JSON Schema shapes. That is publish hygiene, not admit triage.

### 2.1 Why check 3 is not the same as check 2

| Check | Owns | Meaning |
|-------|------|---------|
| **Resolved (2)** | Identity / bind | Joinable subject `(tenant, ci_id)`? |
| **CI on the map (3)** | Topology catalog | Allowed as a `map/` vertex at all? |

Resolved on the **line subject** does not prove both endpoints are CIs (e.g. resolved Service with `dst_ci_type = Alert` → check 3 DROP). Until Identity locks “never resolve / never name non-CI ends,” GraphWriter keeps `never_ci_vertex`.

### 2.2 Check 4 — edge quality

| Sub-check | Question | Fail |
|-----------|----------|------|
| Relation in catalog | Name one of the fifteen? | **DROP** `unknown_relation` |
| Types known | Motadata class for src and dst? | **DROP** `missing_endpoint_type` |
| Pairing legal | `(src_type, relation, dst_type)` on §4? | **DROP** `illegal_edge_triplet` |

**Type resolution** (per endpoint): map node type → else stream `ci_type` / `src_ci_type` / `dst_ci_type` → else missing (never invent `Service`).

### 2.3 Example

`checkout-api` (Service) `depends_on` `payments-db` (Database), resolved → WRITE.  
Same claim but destination Host → DROP `illegal_edge_triplet` (hosting is `runs_on` / `hosted_on`).

---

## 3. Reject codes (this contract)

| Code | When |
|------|------|
| `missing_endpoint_type` | Endpoint Motadata type cannot be resolved |
| `illegal_edge_triplet` | Types known but pair not on §4 |

Also on the admit path: `identity_*`, `never_ci_vertex`, `unknown_relation` ([`IDENTIFIED_STREAM_REJECT.md`](./IDENTIFIED_STREAM_REJECT.md)).

---

## 4. Allowlist — all fifteen Motadata relations

Direction is **Motadata Dest arrow** (`graph_edge.v1`). Fusion camelCase twins (where they exist) keep the same arrow except `part_of` ↔ Fusion `composedOf` (**flip** at publish — child→parent stored).

### 4.1 `runs_on` — guest executes on substrate

Source is the **guest**; target is the **machine**. Never `host`/`node` as source.

| Source | Target |
|--------|--------|
| `process`, `service`, `pod`, `container`, `db`, `queue` | `host`, `node` |

### 4.2 `hosted_on` — guest / VM on hypervisor family

Source sits on a host; target is always `host`. Never host→process/service/pod.

| Source | Target |
|--------|--------|
| `host` | `host` |
| `service`, `process`, `pod`, `container`, `db`, `queue` | `host` |

### 4.3 `depends_on` — declared functional need

| Source | Target |
|--------|--------|
| `service` | `service`, `db`, `queue`, `endpoint`, `business_service` |
| `business_service` | `service`, `db`, `queue` |
| `pod`, `k8s_deployment` | `service`, `db`, `queue`, `endpoint` |
| `customer` | `business_service`, `service` |

### 4.4 `uses` — soft dependency (often catalog “uses”)

Same pairs as `depends_on`. Prefer `depends_on` when the need is hard functional; `uses` when the source stamps a weaker claim. Pairing gate is identical so writers cannot sneak hosting via `uses`.

### 4.5 `communicates_with` — observed traffic

| Source | Target |
|--------|--------|
| Any of `service`, `host`, `pod`, `container`, `db`, `queue`, `endpoint`, `network`, `node`, `process` | Same set |

Do **not** auto-promote to `depends_on`.

### 4.6 `connects_to` — L2/L3 / adjacency

| Source | Target |
|--------|--------|
| `host`, `node`, `network`, `endpoint`, `service` | `host`, `node`, `network`, `endpoint`, `service` |

Stricter than `communicates_with` (no process/pod/db/queue as fabric adjacency ends).

### 4.7 `part_of` — Motadata child → parent

Composition is **always different types**: child is a finer grain than parent. Same-type `part_of` (e.g. `host`→`host`, `service`→`service`) is **illegal** — peers use `clustered_with` or `communicates_with`, not composition.

| Source (child) | Target (parent) |
|----------------|-----------------|
| `service` | `business_service` |
| `process`, `container`, `volume` | `host`, `pod`, `service`, `db` |
| `endpoint` | `service`, `host` |
| `pod` | `k8s_deployment`, `namespace` |

### 4.8 `member_of` — membership in a collection

Motadata has no first-class `cluster` type yet. Collections are modeled with existing types:

| Source (member) | Target (collection) |
|-----------------|---------------------|
| `host`, `node`, `pod`, `service`, `db`, `queue`, `network` | `namespace`, `service`, `business_service`, `k8s_deployment` |

Invalid: Pod → Node as `member_of` (that is `runs_on`).

### 4.9 `mounts` — mounts a volume / filesystem

| Source | Target |
|--------|--------|
| `host`, `pod`, `container`, `service`, `process` | `volume` |

### 4.10 `backs` — A provides backing capacity for B

| Source (backer) | Target (backed) |
|-----------------|-----------------|
| `db`, `volume`, `host`, `service` | `db`, `volume`, `host`, `service` |

### 4.11 `backed_up_by` — A is backed up by B

| Source | Target (backup sink / job) |
|--------|----------------------------|
| `db`, `volume`, `host`, `service` | `service`, `host`, `db`, `volume` |

### 4.12 `routes_through` — path via middlebox / hop

| Source | Target (hop) |
|--------|--------------|
| `service`, `host`, `pod`, `endpoint` | `network`, `service`, `host`, `endpoint` |

### 4.13 `authenticates_via` — auth dependency

| Source | Target (IdP / auth service) |
|--------|-----------------------------|
| `service`, `host`, `pod`, `customer` | `service`, `endpoint` |

### 4.14 `monitored_by` — observed by collector / monitor

| Source (observed CI) | Target (monitor) |
|----------------------|------------------|
| Any of `service`, `host`, `pod`, `container`, `db`, `queue`, `endpoint`, `network`, `node`, `process`, `business_service`, `k8s_deployment`, `namespace`, `volume`, `customer` | `service` |

Monitor endpoints are Motadata `service` (or Monitor→`service` ingest alias) until a dedicated monitor type exists.

### 4.15 `clustered_with` — peer in same tier / HA set

Symmetric peer pairs (same storage type both ends):

| Source | Target |
|--------|--------|
| `host` | `host` |
| `node` | `node` |
| `service` | `service` |
| `db` | `db` |
| `pod` | `pod` |
| `queue` | `queue` |

Prefer `member_of` shared parent when the product has a real group CI.

---

## 5. Semantic invalidity (direction + grain)

The allowlist is not only “known types.” It encodes **who may be the arrow head**. Flipping guest/substrate or composing same grain is `illegal_edge_triplet`.

### 5.1 Hosting — guest → substrate only

`runs_on` / `hosted_on` mean the **source runs or sits on** the destination.

| Illegal claim | Why |
|---------------|-----|
| `host` `runs_on` `service` | Substrate cannot run on a guest |
| `host` `runs_on` `pod` / `process` / `container` | Same — wrong direction |
| `host` `hosted_on` `process` | Host is not hosted on a process |
| `host` `hosted_on` `service` / `pod` | Same — wrong direction |
| `service` `runs_on` `service` | Destination must be `host` / `node` |

Legal shapes: `service|process|pod|…` → `host|node` for `runs_on`; guest/`host` → `host` for `hosted_on` (VM on hypervisor).

### 5.2 `part_of` — child → parent, different types

| Illegal claim | Why |
|---------------|-----|
| `host` `part_of` `host` | Same type is not composition |
| `service` `part_of` `service` | Same — use `clustered_with` / `communicates_with` for peers |
| `business_service` `part_of` `service` | Wrong Motadata arrow (parent→child) |

### 5.3 Teaching table (other common mistakes)

| Claimed edge | Example | Reject | Why |
|--------------|---------|--------|-----|
| `depends_on` / `uses` | `service` → `host` | `illegal_edge_triplet` | Hosting — use `runs_on` / `hosted_on` |
| `member_of` | `pod` → `node` | `illegal_edge_triplet` | Use `runs_on` |
| `mounts` | `service` → `service` | `illegal_edge_triplet` | Mount target must be `volume` |
| `clustered_with` | `service` → `db` | `illegal_edge_triplet` | Peers must be same tier type |
| `communicates_with` | auto-promoted to `depends_on` | (do not emit) | Talk ≠ declared need |
| any | missing types | `missing_endpoint_type` | No invented `Service` |

Fusion anti-patterns still hold: hosting ≠ `depends_on`; raw traffic ≠ `depends_on`; realization / control-plane ownership wait for Dest `realizes` / `manages`.

---

## 6. Implementation pointer

- Code: `pillar-b/poc/graph/edge_triplets.py` (`check_edge_triplet`) — matrices for all fifteen.  
- Catalog: `edge_catalog.classify_relation` — emit any of the fifteen; unknown → `unknown_relation`.  
- Tests: `pillar-b/poc/graph/tests/unit/test_edge_triplets.py`, `test_edge_catalog.py`.

When Dest adds richer CI classes (e.g. Cluster), widen §4.8 without renaming reject codes.
