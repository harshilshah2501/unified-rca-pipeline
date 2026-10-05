# E8 Scope — map walk policy (product brief)

**Status:** Draft for product and engineering alignment. **Does not** add a new walk API surface in code yet; it locks how **Scope** should walk the **hot present map** when building a **WorkingSet** from a **CaseSeed**.

**Related:** [`GRAPH_QNA.md`](./GRAPH_QNA.md) (G41 pipeline split, G5 ERROR/SLOWDOWN slice) · [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md) (walks on hot, not S3 per hop) · PoC stub [`scope.py`](../pillar-b/poc/graph/case_path/scope.py) · walk helpers [`neighbors.py`](../pillar-b/poc/graph/neighbors.py)

---

## 1. What this document is for

**E8 Scope** is the first stage that **read-joins** the two independent writer rooms:

- **`map/`** (Pillar B) — topology: who depends on whom, who runs where.
- **`history/`** (Pillar A) — compact metric sketches for the same configuration items (`entity_id` ≡ graph `ci_id` after Identity).

Scope **walks the map** from the **CaseSeed** tip to produce a **bounded WorkingSet**: neighborhood configuration items, edges used in that neighborhood, candidate paths toward common leaf types (for example Database, Host), optional sketch references inside the case time window, and an **evidence budget** so later Identify does not unbound the case.

Scope **does not** pick the root-cause leaf. **E9 Localize** consumes the WorkingSet and emits a **LeafClaim** (`path_from_seed`, `claim_ci_id`). See §6.

Detect (**E6**) and Curate (**E7**) do **not** perform this walk. They only produce **Signals** and a **CaseSeed** (seed CI, detect class, time window).

---

## 2. Inputs and execution surface

| Input | Source | Notes |
|-------|--------|--------|
| **CaseSeed** | E7 Curate | `seed_ci_id`, `detect_class`, `window_start` / `window_end`, `tenant`, `case_id` |
| **Present map** | GraphWriter hot state (rebuilt from cold via `load_map` on start/recovery) | Walk APIs read **adjacency in memory**, not one S3/Vortex fetch per hop |
| **Sketches** | `history/` for `entity_id` in the walked set | Same join key as map; window from CaseSeed (policy may pad ±N minutes) |

**Rule (lifecycle):** Cold Vortex parts under `map/` are for **checkpoint load** and analytics-style column reads. Interactive Scope walks use **hot** graph state after load or live `write_topo_stream` upserts. See [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md).

---

## 3. Default Scope walk policy (all detect classes)

These are **platform defaults** when tenant policy does not override. The PoC stub uses the same shape in `build_working_set()` (`hops=2`, `direction="out"`, `confidence_bearing_only=True`).

| Knob | Default | Purpose |
|------|---------|---------|
| **Start node** | `CaseSeed.seed_ci_id` | Symptom / tip CI from Curate |
| **Hop budget** | **2** (reachable set); path search may use **hops + 1** for leaf typing | Keeps WorkingSet small; deep enough for typical service → database |
| **Direction** | **`out`** | Follow dependency / call direction from symptom toward deps (seed → downstream) |
| **Include seed** | **Yes** | Seed is always in `ci_ids` |
| **Relation filter** | **Detect-class profile** (§4); if unset, all fifteen catalog relations that pass triplet allowlist | See [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md) |
| **Confidence filter** | **`confidence_bearing_only = true`** | Skip edges with `maintain_status == hard_downgraded` (E5 Maintain) |
| **Max paths per leaf type** | **10** | Cap `paths_to_databases` / `paths_to_hosts` list size |
| **Node type filter** | **Soft** (post-walk or during path targets) | Prefer paths ending at configured leaf types; do not delete mid-hop nodes from reachable set unless policy says so |
| **Time window** | CaseSeed `window_start` … `window_end` | Used for sketch join and later event/log budgets; **does not** time-filter edges on v1 map (validity is on edge columns; future: intersect walk with edge validity window) |
| **Sketch join** | All walked `ci_ids` | Attach digest/baseline refs for Identify; empty if history unavailable |

**WorkingSet outputs (map side):** `ci_ids`, `neighbor_ids`, `edges`, `paths_to_databases`, `paths_to_hosts`, `evidence_budget` (counts + flags). Optional `sketch_refs` when a sketch provider is wired (integration harness or product retrieval layer).

---

## 4. Detect-class walk profiles (relation and direction)

Full estate storage keeps **all fifteen** relation names. Scope **does not** need every relation for every incident class. Profiles choose which **edge types** participate in the BFS and path search.

Legend: **Core** = always in Scope for this class; **Optional** = include if present and within hop budget; **Defer** = omit from Scope walk (other RCA stories or E10 only).

### 4.1 ERROR / AVAILABILITY (application fault, errors, down)

Aligns with [`GRAPH_QNA.md`](./GRAPH_QNA.md) G5 (service + dependency map).

| Setting | Value |
|---------|--------|
| **Direction** | `out` (symptom → dependencies); add `both` on **one** hop for `runs_on` if seed is a Service and host context is required |
| **Core relations** | `depends_on`, `communicates_with`, `uses` |
| **Composition / hosting** | `part_of`, `runs_on` |
| **Optional** | `member_of`, `clustered_with` (only if cluster context is in CaseSeed labels) |
| **Defer for Scope** | `mounts`, `connects_to`, `backs`, `backed_up_by`, `hosted_on`, `routes_through`, `authenticates_via`, `monitored_by` |
| **Path targets (precompute)** | `Database`, then `Host`, then `Runtime` / `Middleware` |
| **Typical hop budget** | 2 (default); 3 for large microservice estates (policy) |

### 4.2 SLOWDOWN (latency, saturation without hard error)

Same **relation core** as ERROR/SLOWDOWN slice in G5. Scope may **widen** sketch join to upstream callers if Signals implicate ingress (Curate label `ingress_ci_id` → optional second mini-walk `in` on `communicates_with` for one hop only).

| Setting | Value |
|---------|--------|
| **Direction** | `out` default; optional `in` hop-1 on `communicates_with` when seed is mid-tier |
| **Core relations** | Same as §4.1 |
| **Path targets** | `Database`, `Queue`, `Host` (queue when latency story names async handoff) |

### 4.3 SATURATION (resource exhaustion on a box or pool)

| Setting | Value |
|---------|--------|
| **Direction** | `out` and **`in`** (who shares this host/pool) |
| **Core relations** | `runs_on`, `hosted_on`, `part_of`, `member_of`, `clustered_with` |
| **Also** | `depends_on` one hop from seed if seed is Service |
| **Defer for Scope** | Backup/monitor edges unless detect class is MONITORING_UNAVAILABLE |
| **Path targets** | `Host`, `HypervisorHost` (when in map), shared `Database` |

### 4.4 MONITORING_UNAVAILABLE / infrastructure contention

| Setting | Value |
|---------|--------|
| **Direction** | `both` within hop budget |
| **Core relations** | `monitored_by`, `runs_on`, `hosted_on`, `connects_to`, `mounts`, `routes_through` |
| **Defer** | Pure app `depends_on` chains unless CaseSeed seed is still an app Service |
| **Path targets** | Collector / monitor CI types, `NetworkPort`, `Datastore` as typed in map |

### 4.5 ANOMALY (generic door C, class not refined)

| Setting | Value |
|---------|--------|
| **Direction** | `out`, hops **1** (minimal neighborhood) |
| **Relations** | `depends_on`, `runs_on` only |
| **Path targets** | None required; Localize may fall back to seed |

Tenant **policy JSON** (future) should override rows in this section without changing the fifteen-name storage enum.

---

## 5. Confidence and Maintain interaction

**E5 Maintain** may mark edges `hard_downgraded` when topology confidence drops (stale trace, contradicted dependency, and similar).

| `confidence_bearing_only` | Scope behavior |
|----------------------------|----------------|
| **true** (default) | Exclude hard-downgraded edges from BFS and `find_paths`. WorkingSet may shrink; Localize must tolerate missing Database paths. |
| **false** (lab / break-glass) | Include downgraded edges; `evidence_budget` records the flag so Package can show low confidence. |

**Teaching golden:** when all edges into `payments-db` are hard-downgraded, Scope still returns seed and hosts, but **no** Database path → Localize falls back to deepest Host or seed ([`MAP_P2_CASE_PATH.md`](../pillar-b/docs/MAP_P2_CASE_PATH.md)).

---

## 6. E9 Localize — how it uses the walk (not a second full estate scan)

Localize **does not** re-walk the entire tenant map. It **consumes** the WorkingSet produced at Scope:

| Step | Behavior |
|------|----------|
| **Primary** | Use precomputed `paths_to_databases` / `paths_to_hosts` (longest path wins in PoC teaching heuristic) |
| **Optional deepen** | If Scope used hop budget 1 but policy allows 2, Localize may call the same walk helpers **once** on hot map with the **same** relation profile — still bounded |
| **Output** | **LeafClaim**: `claim_ci_id`, `path_from_seed`, `alternatives`, rationale |
| **Not in Localize** | Sketch storm merge, new seed pick, or unbounded BFS |

Product **Retrieval** layer (future) should expose Scope as “build WorkingSet from CaseSeed + policy” and Localize as “LeafClaim from WorkingSet,” both against hot map handles — not direct S3. See [`GRAPH_QNA.md`](./GRAPH_QNA.md) G27–G28 retrieval notes.

---

## 7. Evidence budget (case bounding)

Scope attaches a small **evidence_budget** object so E10 Identify and event cite paths stay finite:

| Field | Typical cap / meaning |
|-------|------------------------|
| `max_hops` | Same as Scope hop budget |
| `max_cis` | `len(ci_ids)` at Scope time; hard cap e.g. **64** (product default TBD) |
| `max_edges` | Edge rows returned; hard cap e.g. **128** |
| `max_sketch_refs` | One row per (ci, metric) or per ci; cap e.g. **32** |
| `confidence_bearing_only` | Echo Scope flag |

Identify must not expand the case beyond this budget without an explicit operator “widen scope” action (new CaseSeed or policy bump).

---

## 8. Step-by-step example (customer_checkout teaching estate)

**CaseSeed (E7):** seed `checkout-api`, `detect_class=ERROR`, window around first down.

**Scope (E8) with default policy:**

1. Load hot map (already in GraphWriter process).
2. BFS `out`, hops=2, relations `{depends_on, communicates_with, uses, part_of, runs_on}`, confidence bearing only.
3. Reachable CIs: `checkout-api`, `payments-db`, `linux-server-app-01`, `bs-checkout`, …
4. `find_paths` → `[checkout-api, payments-db]`, `[checkout-api, linux-server-app-01]`.
5. Join sketches for those CIs in CaseSeed window → attach refs on checkout-api (and neighbors as available).
6. Emit **WorkingSet** + evidence budget.

**Localize (E9):**

1. Pick deepest Database path → `payments-db`, path `[checkout-api, payments-db]`.
2. Emit **LeafClaim** for Identify.

---

## 9. PoC vs product gap

| Area | PoC today | Product intent |
|------|-----------|----------------|
| Walk implementation | Python `neighbors` / `reachable_ci_ids` / `find_paths` on JSON snapshot | Hot adjacency in GraphWriter service (Rust map-vortex hot + index) |
| Relation profile | **Wired** — `walk_profiles.resolve_walk_profile` + `build_working_set` (§4); proof: ERROR excludes `monitored_by` | Same tables in Retrieval / GraphWriter service |
| Sketch join | Optional `sketch_provider` callback | Retrieval reads `history/` by tenant + ci_ids + window |
| Policy overrides | Explicit `hops` / `direction` / `relations` kwargs on Scope | Tenant policy JSON on hops, relations, caps |

**Still open:** document Retrieval API names when the walk brief in [`MAP_WRITER_VORTEX_COHESION.md`](./MAP_WRITER_VORTEX_COHESION.md) is expanded; optional SLOWDOWN ingress mini-walk (`in` on `communicates_with`).

PoC modules: [`walk_profiles.py`](../pillar-b/poc/graph/case_path/walk_profiles.py) · [`scope.py`](../pillar-b/poc/graph/case_path/scope.py) · test `test_error_profile_excludes_monitored_by_from_working_set` in [`test_case_path.py`](../pillar-b/poc/graph/tests/unit/test_case_path.py).

---

## 10. Summary table (quick reference)

| Stage | Walks map? | Typical hops | Picks leaf? |
|-------|------------|--------------|-------------|
| E6 Detect | No | — | No |
| E7 Curate | No | — | No (sets seed) |
| **E8 Scope** | **Yes** | **2** (class-dependent) | **No** |
| E9 Localize | Reuses WorkingSet; optional bounded re-walk | Same budget | **Yes** (LeafClaim) |
| E10 Identify | Cites CIs on path | — | No |

**One line:** **Scope walks the hot floor plan from the seed with a detect-class relation profile and hop cap; Localize chooses which room on that bounded plan to investigate first.**
