# LLD-E3 — Topology

**Status:** Draft for review
**Version:** v1.0
**Owner:** ObserveOps RCA engineering
**Parent:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §8 (E3 Topology contract), §5 (crosswalk: E3 is part of the 5-stage "Ingest" phase)
**Related surfaces:** [Our HLD](./observeops-pipeline-hld.html) · [Fusion](./observeops-fusion-guide.html) (Graph Explained tab) · schema source below.
**Schema source (Draft, not yet merged into this LLD):** [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) — node/edge/identity/index/fault-signature model + per-edge provenance. Worked example: [`observeops-ci-graph.html`](./observeops-ci-graph.html) · [`linux-server-ci-telemetry.json`](./linux-server-ci-telemetry.json) (authored illustration, not live E3 output).
**Gate checklist (per HLD §18):** stage ID/purpose referenced ✓ · concrete schema/API defined ✓ (§2–§3) · acceptance test from corpus/lab replay ✓ (§6) · evidence-maturity tag stated ✓ (§6, §7)

---

## 0. What this LLD owns vs the operational-graph chapter

Do not treat these as one schema. The Pipeline HLD says what E3 is *for*. This LLD is what bakeoff actually loads. The operational-graph chapter is the *target* map shape — not merged here yet.

| Surface | Owns | Does not own |
|---|---|---|
| [Pipeline HLD](./OBSERVEOPS_PIPELINE_HLD.md) | E3 purpose, I/O object (`GraphSnapshot`), ADR D1 | Per-edge provenance fields |
| [Operational-graph chapter](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) | **Target** node/edge/identity/signature shape (`evidence_type`, `refresh`, `confidence`, fault signatures) | Bakeoff runtime format |
| **This LLD** | What Lean and Federated **load today**: corpus `topology.json` + the two `GraphSnapshot` implementations in §3 | Those target provenance fields |
| [Fusion](./observeops-fusion-guide.html) | Clickable walk of the pipeline (and the map) | The written spec |

Worked illustration of the **target** schema: [`observeops-ci-graph.html`](./observeops-ci-graph.html) · [`linux-server-ci-telemetry.json`](./linux-server-ci-telemetry.json) (authored, not live E3). Merging that schema onto `topology.json` is a future LLD revision, not something this draft already did.

---

## 1. Purpose and boundary (from HLD §8)

E3 Topology maintains a walkable dependency graph so E6 Detect, E7 Curate, and E9 Localize can reason about neighborhoods instead of isolated CIs. Per HLD §9's contract catalog, `GraphSnapshot` fans out to `E6, E7, E9` and E9 also has a dotted (advisory, not blocking) dependency drawn directly from E3.

**Trigger:** continuous updates + periodic refresh (design intent — see §5 for what's actually implemented).
**Inputs:** `IdentifiedRecord` (from E2), discovery relations, optional CMDB enrichment.
**Outputs:** `GraphSnapshot`.
**Preconditions:** identity keys must exist (E2 has run).
**Postconditions:** queryable neighbors, directionality, depth.
**Failure if missing:** E9 Localize cannot reason over propagation — no walk target.
**Degradation:** stale graph increases ambiguity and misranking risk at E9.

## 2. Input schema — `topology.json`

This is the **implemented corpus shape** — what bakeoff and lab runs actually load. It does **not** yet carry operational-graph chapter fields (`evidence_type`, `refresh`, `confidence`, nested `rca.fault_signatures`). Those live on the authored CI illustration, not here.

Same shape across both engines and the whole ObserveOps corpus:

```json
{
  "nodes": [
    { "id": "esxi-host-01", "type": "HypervisorHost", "name": "ESXi Host 01" }
  ],
  "edges": [
    { "from": "orders-api", "to": "guest-os-vm-app-01", "relation": "runs_on" }
  ]
}
```

Real `ci_type` values in this corpus (from `datasets/observeops/UC-1/topology.json`): `NetworkPort`, `HypervisorHost`, `Datastore`, `VirtualMachine`, `GuestOS`, `Service`. Real `relation` values across UC-1..UC-5 (checked directly against every `topology.json` in the corpus): `runs_on`, `hosted_by`, `uplink_to`, `stored_on` — matching the "Network device → ESXi host → VM → guest OS → application (+ shared datastore)" model described in [`README.md`](./README.md) §"What topology does the ObserveOps corpus use?". Edges are directed `from → to`, and — this is a load-bearing detail — **`from`/`to` already encode effect→cause direction** (a service `runs_on` a guest OS, which is `hosted_by` a host): the topology file itself is authored as an upstream-pointing graph, not a generic undirected dependency map.

## 3. Two `GraphSnapshot` implementations (both real, deliberately different)

This is the clearest evidence in the repo for HLD ADR **D1 (topology model: hybrid — derived edges first, typed IDs when cheap)** — the two engines resolve that hybrid differently, and both are legitimate readings of it.

### 3.1 Lean — `InvocationGraph` (typed IDs, no derivation)

```python
@dataclass
class InvocationGraph:
    upstream: dict[str, list[str]]   # effect_id -> [cause_id, ...]
    node_types: dict[str, str]       # id -> ci_type

    @classmethod
    def from_topology(cls, topology: dict) -> InvocationGraph:
        upstream = {n["id"]: [] for n in topology["nodes"]}
        node_types = {n["id"]: n["type"] for n in topology["nodes"]}
        for edge in topology["edges"]:
            upstream.setdefault(edge["from"], []).append(edge["to"])
        return cls(upstream=upstream, node_types=node_types)

    def upstream_of(self, node_id: str) -> list[str]: ...
    def collect_upstream(self, start: str) -> list[str]: ...  # BFS, discovery order
```

Reference: [`lean-pipeline/core_engine/lean/invocation_graph.py`](../lean-pipeline/core_engine/lean/invocation_graph.py). Trusts `topology.json`'s edges completely — **no edge derivation, no typed-ID fallback rules**. This is the "typed IDs when cheap" half of D1: the corpus already gives clean typed edges, so Lean does the cheap thing and takes them as-is.

Directly consumed in production path: `graph = InvocationGraph.from_topology(bundle["topology"])` in [`lean-pipeline/core_engine/observeops/engine.py:32`](../lean-pipeline/core_engine/observeops/engine.py), immediately handed to `best_first_walk()` (E9). **Architecture note:** in this repo, E3's graph construction and E9's walk happen inside one function call, not as separately staged services — the HLD models them as contract-separated stages; the implementation is currently a monolith that satisfies the same data contract. Worth knowing before assuming E3 is independently deployable today.

### 3.2 Federated — `RelationshipGraph` (typed IDs + derived edges)

```python
class RelationshipGraph:
    def __init__(self, max_hops: int = 5):
        self._graph = nx.DiGraph()   # cyclic directed, networkx-backed

    def add_edge(self, src_id, dst_id, bidirectional: bool = True): ...
    def bfs_from(self, start_id, max_hops=None) -> set[str]: ...
    def prune_candidates(self, symptom_entity, current_metrics, historical_stats,
                          threshold_stdevs=1.0) -> set[str]: ...
    def build_from_monitoring_db(self, app_id, monitoring_db) -> None: ...
```

Reference: [`federated-pipeline/murphy/graph.py`](../federated-pipeline/murphy/graph.py). Two edge sources, both active:

1. **Explicit edges** from entity metadata (`meta["neighbors"]`, `meta["directed_edges"]`) — the "typed IDs when cheap" case, same as Lean.
2. **Type-based derived edges** (`_add_default_edges`) — a fixed rule table keyed by `entity_type` (`flow`, `vm`, `microservice`, `host`, `nic`, `container`) that wires edges even when no explicit edge was given (e.g. every `vm` connects to its `host_id` and `nic_ids` automatically). This is the "derived edges first" half of D1 — Federated will still produce a usable graph when the source only gives loosely-typed entities with metadata, not a fully pre-wired topology.

Edges default to **bidirectional** (`bidirectional=True`), unlike Lean's strictly directed effect→cause edges — except for `microservice` upstream/downstream edges, which respect `causal_direction: caller_to_callee` and become directed when set. `prune_candidates()` additionally filters the BFS neighborhood by a `threshold_stdevs`-based anomaly check against `historical_stats` — a capability Lean's `InvocationGraph` does not have (Lean's ranking happens one layer up, in `search.py`'s `best_first_walk`, not inside the graph object itself).

### 3.3 Side-by-side

| | Lean `InvocationGraph` | Federated `RelationshipGraph` |
|---|---|---|
| Backing | Plain dicts | `networkx.DiGraph` |
| Edge source | Explicit `topology.json` edges only | Explicit metadata edges **+** type-based derivation rules |
| Directionality | Strictly directed (effect→cause) | Bidirectional by default; directed only for causal microservice edges |
| Traversal | `collect_upstream` (BFS, unranked) — ranking happens in `search.py` | `bfs_from` (max-hop-bounded) + `prune_candidates` (anomaly-filtered) + `shortest_path_subgraph` |
| Cycle handling | Not addressed — corpus topology is acyclic in practice | Explicitly "cyclic directed" by design (docstring) |
| Node cap | None | `_MAX_GRAPH_ENTITIES = 10_000` guard in `build_from_monitoring_db` |

## 4. `GraphSnapshot` contract (as actually produced)

| Field | Lean | Federated |
|---|---|---|
| Nodes | `node_types: dict[id, ci_type]` | `RelationshipGraph._entities: dict[id, Entity]` |
| Edges | `upstream: dict[id, list[id]]` | `networkx.DiGraph` internal adjacency |
| Freshness marker | **None** — no timestamp, version, or staleness field on the snapshot itself | **None** — same gap |
| Depth/query API | `upstream_of`, `collect_upstream` | `neighbors`, `in_neighbors`, `bfs_from`, `shortest_path_subgraph`, `shortest_path_hops` |

## 5. Failure modes and degradation

| Condition | Behavior today | Status |
|---|---|---|
| `ci_id` in an edge not present in `nodes` | Lean: `upstream.setdefault(...)` still creates the key implicitly if it's a `from`; if it only ever appears as a `to`, it has no entry in `node_types` and typing falls back silently to whatever the caller does with a missing dict key (KeyError risk in unguarded lookups) | **Partial — not a clean degradation path** |
| Topology snapshot goes stale (deploy happened, `topology.json` not refreshed) | **No detection mechanism exists.** Both graph builders trust whatever `topology.json` they're handed; there is no timestamp, checksum, or refresh trigger anywhere in `invocation_graph.py` or `graph.py` | **Design-level — not implemented.** This is the concrete form of the HLD's own stated risk ("stale graph increases ambiguity and misranking risk") — today that risk is entirely unmitigated in code, only mitigated by the corpus being frozen (so staleness can't occur in the bakeoff) |
| Topology crawler (live discovery) | Documented in [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) §4 as a "small service / cron" sibling to Vector | **Design-level — no crawler code exists anywhere in this repo.** `INGESTION_POC_PLAN.md`'s own D3 milestone ("Topology crawler stub + CI bind table") is listed as **Planned**, not Done |
| CMDB enrichment | HLD calls it optional; `INGESTION_PIPELINE_VECTOR.md` §4 lists vCenter/CMDB as "Stub" | **Design-level — no CMDB integration code exists.** Static corpus export remains the only implemented source |

## 6. NFR baseline

HLD §8/§15 leaves E3's "freshness window and bounded staleness" numerically unfilled. This LLD does not invent a number, because **no staleness-tracking code exists to measure against one** (§5) — filling in a target before the mechanism exists would be aspirational, not grounded. This is an explicit gap, not an oversight.

## 7. Acceptance test (evidence maturity: Grounded)

```python
from pathlib import Path
from core_engine.observeops.ingest.bundle import load_bundle
from core_engine.lean.invocation_graph import InvocationGraph
import json

for uc in ["UC-1", "UC-2", "UC-3", "UC-4", "UC-5"]:
    bundle = load_bundle(uc, Path("datasets/observeops"))
    graph = InvocationGraph.from_topology(bundle["topology"])
    gt = json.loads((Path("datasets/observeops") / uc / "ground_truth.json").read_text())
    seed_ci = bundle["symptom_seed"]["ci"]
    reachable = graph.collect_upstream(seed_ci)
    assert gt["root_ci"] in reachable or gt["root_ci"] == seed_ci, (
        f"{uc}: root_ci {gt['root_ci']!r} not reachable from seed {seed_ci!r}"
    )
```

**Pass criteria:** for every UC-1..UC-5, the ground-truth root CI is either the symptom seed itself or reachable via `collect_upstream` from it. This is the load-bearing correctness property for the whole pipeline — if it fails, E9 Localize can never produce the right answer no matter how good its ranking is, because the candidate wouldn't be in the search space at all.

**Evidence maturity: Grounded.** This exact property already holds in production: `engine.py` performs this walk on every `diagnose` call, and the ADR-001 bakeoff scoreboard (`adr001-rerun-20260723`, cited in [`ADR-001-lean-primary-engine.md`](../ADR-001-lean-primary-engine.md)) reports **5/5 root-CI matches on UC-1..UC-5** — which is only possible if this reachability property held for every UC in that run. This LLD's acceptance test makes that implicit precondition explicit and independently checkable, rather than inferring it from the final score.

## 8. Traceability

Per HLD §16: E3 maps to **FR-C (topology/time)**, and (jointly with E5) **FR-I/J (operability/freshness)** — the freshness half is unmet today per §5/§6.

## 9. Open decisions carried to future revisions

- **Operational-graph provenance is not on this `topology.json`.** Merging `evidence_type` / `refresh` / signatures onto the corpus format is an LLD revision after an ADR, not a docs-only fix. Until then, that chapter’s §3 is the target; this file is the runtime.
- **No staleness/freshness marker on `GraphSnapshot`.** Neither engine's graph object carries a timestamp or version. Before this can be called "Done," decide the minimum viable marker (e.g., `topology.json`'s own file mtime, or an explicit `snapshot_ts` field written by whichever process last refreshed it).
- **No topology crawler exists.** `INGESTION_POC_PLAN.md` D3 is Planned, not built. Every current run — bakeoff and lab — uses a static, hand-authored or synthetically-generated `topology.json`. Live discovery is a real, open piece of work, not a documentation gap.
- **CMDB enrichment is entirely unimplemented,** consistent with the HLD calling it optional — but worth stating plainly rather than letting "optional" imply "partially done."
- **Lean's `node_types` lookup has no guard for a `to`-only node** (§5) — low risk on the frozen corpus (nodes list is complete there) but a real risk if E3 is ever fed a partial/derived topology the way Federated's builder tolerates.

## 10. Pillar A/B PoC acceptance (graph_*.v1 bridge)

The Motadata Pillar B PoC under [`pillar-ab-implementation/poc/graph/`](../pillar-ab-implementation/poc/graph/) emits logical `graph_node.v1` / `graph_edge.v1` and a versioned `GraphSnapshot` via the Gate B file dest. It does **not** replace the bakeoff `topology.json` loader in §2–§3; it is the bridge toward the operational-graph target schema.

**Acceptance (PoC):**

```bash
cd pillar-ab-implementation/poc && make install && make test-graph
```

Pass criteria: schema-valid nodes/edges; CI-only vertices (Alert/Change rejected); wave-1 relations emitted; `neighbors("checkout-api")` reaches host/db from `fixtures/lab_checkout/`. Schemas: [`pillar-ab-implementation/contracts/schemas/`](../pillar-ab-implementation/contracts/schemas/). Plan: [`IMPLEMENTATION_PLAN.md`](../pillar-ab-implementation/IMPLEMENTATION_PLAN.md).

---

*Part of the LLD backlog defined in [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §18. Siblings: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) · [`LLD-E4-Stores.md`](./LLD-E4-Stores.md).*
