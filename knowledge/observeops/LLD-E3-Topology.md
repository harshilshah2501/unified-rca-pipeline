# LLD-E3 — Topology

**Status:** Draft for review
**Version:** v1.1
**Owner:** ObserveOps RCA engineering
**Parent:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §8 (E3 Topology contract), §5 (crosswalk: E3 is part of the 5-stage "Ingest" phase)
**Related surfaces:** [Our HLD](./observeops-pipeline-hld.html) · [Fusion](./observeops-fusion-guide.html) (Graph Explained tab) · Motadata Pillar B [`pillar-b/README.md`](../../pillar-ab-implementation/pillar-b/README.md) · [`MAP_WRITE_READ_RECORD.md`](../../pillar-ab-implementation/contracts/MAP_WRITE_READ_RECORD.md)
**Schema source (target map shape):** [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) — node/edge/identity/index/fault-signature model + per-edge provenance. Worked example: [`observeops-ci-graph.html`](./observeops-ci-graph.html) (authored illustration, not live E3 output).
**Gate checklist (per HLD §18):** stage ID/purpose referenced ✓ · concrete schema/API defined ✓ (§2–§3 bakeoff · §10 Motadata) · acceptance test from corpus/lab replay ✓ (§7 bakeoff · §10 PoC) · evidence-maturity tag stated ✓

> **Motadata writer SoT:** GraphRegulator admits when a **`topology` block** is present on `writer_stream.v1` (no `fact_kind`) — [`WRITER_REGULATOR.md`](../../pillar-ab-implementation/contracts/WRITER_REGULATOR.md). Lab JSONL may still use legacy `ingest.v1` + `fact_kind=topo_update` (Pillar B dual-admit). Bakeoff corpus `topology.json` (§2) is a separate load path.

---

## 0. Dual path — Motadata map vs bakeoff load

Do not treat these as one schema. E3 is the **sole writer of the topology / `map/` room**. Pillar A writes `history/` sketches in parallel after E2 — that does not make a second graph writer ([`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G12).

| Surface | Owns | Does not own |
|---|---|---|
| [Pipeline HLD](./OBSERVEOPS_PIPELINE_HLD.md) | E3 purpose, I/O object (`GraphSnapshot`), ADR D1 | Per-edge provenance field tables |
| [Operational-graph chapter](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) | **Target** node/edge/identity/signature shape (`evidence_type`, `refresh`, `confidence`, fault signatures) | Bakeoff runtime format |
| **This LLD — Motadata path (§10)** | Pillar B GraphWriter: `writer_stream.v1` `topology` block (or lab `topo_update`) + optional bootstrap → `graph_snapshot.v1` under Dest `map/`; NOOP / WRITE / DROP; wave-1 relations | Continuous live discovery crawler (Design) |
| **This LLD — bakeoff path (§2–§3)** | What Lean and Federated **load today**: corpus `topology.json` + `InvocationGraph` / `RelationshipGraph` | Motadata Dest keys / `graph_*.v1` |
| [Fusion](./observeops-fusion-guide.html) | Clickable walk of the pipeline (and the map) | The written spec |

**Relation-name honesty:** bakeoff corpus edges may use names such as `hosted_by`, `uplink_to`, `stored_on`. Motadata catalog / wave-1 use snake_case names such as `hosted_on`, `runs_on`, `depends_on`, `communicates_with`, `part_of` ([`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G4/G8 · Pillar B `edge_catalog.py`). Same *ideas*, different wire names — do not silently equate them.

Worked illustration of the **target** schema: [`observeops-ci-graph.html`](./observeops-ci-graph.html) (authored, not live E3). Merging that schema onto bakeoff `topology.json` is a future LLD revision.

---

## 1. Purpose and boundary (from HLD §8)

E3 Topology maintains a walkable dependency graph so E6 Detect, E7 Curate, and E9 Localize can reason about neighborhoods instead of isolated CIs. Per HLD §9's contract catalog, `GraphSnapshot` fans out to `E6, E7, E9` and E9 also has a dotted (advisory, not blocking) dependency drawn directly from E3.

After E2 Identity, Motadata fabric **fans out in parallel**: E3 Topology ∥ E4 Stores ([`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G12). E3 does not wait for sketches; sketches do not emit edges.

**Trigger:** continuous updates + periodic refresh (design intent — see §5 for bakeoff reality; §10 for Pillar B stream upsert).
**Inputs:** `IdentifiedRecord` (from E2), discovery relations, optional CMDB enrichment.
**Outputs:** `GraphSnapshot` — Motadata: versioned `graph_snapshot.v1` in `map/`; bakeoff: in-memory Lean/Fed graph objects (§3).
**Preconditions:** identity keys must exist (E2 has run). Motadata writers additionally require `identity.status=resolved`.
**Postconditions:** queryable neighbors, directionality, depth.
**Failure if missing:** E9 Localize cannot reason over propagation — no walk target.
**Degradation:** stale graph increases ambiguity and misranking risk at E9. Product freshness defaults for `declared` edges: soft-stale **7 days**, hard-downgrade **30 days** (operational-graph decision #4; §6). Bakeoff engines still lack markers (§5).

## 2. Input schema — bakeoff `topology.json`

This is the **implemented corpus shape** — what bakeoff and lab runs actually load. It does **not** yet carry operational-graph chapter fields (`evidence_type`, `refresh`, `confidence`, nested `rca.fault_signatures`). Those live on the authored CI illustration, not here. Motadata stream shape is `writer_stream.v1` + `topology` block (§10; lab may still use `ingest.v1` + `topo_update`), not this JSON file.

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

Reference: [`lean-pipeline/core_engine/lean/invocation_graph.py`](../../lean-pipeline/core_engine/lean/invocation_graph.py). Trusts `topology.json`'s edges completely — **no edge derivation, no typed-ID fallback rules**. This is the "typed IDs when cheap" half of D1: the corpus already gives clean typed edges, so Lean does the cheap thing and takes them as-is.

Directly consumed in production path: `graph = InvocationGraph.from_topology(bundle["topology"])` in [`lean-pipeline/core_engine/observeops/engine.py:32`](../../lean-pipeline/core_engine/observeops/engine.py), immediately handed to `best_first_walk()` (E9). **Architecture note:** in this repo, E3's graph construction and E9's walk happen inside one function call, not as separately staged services — the HLD models them as contract-separated stages; the implementation is currently a monolith that satisfies the same data contract. Worth knowing before assuming E3 is independently deployable today.

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

Reference: [`federated-pipeline/murphy/graph.py`](../../federated-pipeline/murphy/graph.py). Two edge sources, both active:

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

**Declared-edge freshness (Motadata / operational graph — locked 2026-08-17):** for `declared` edges, soft-stale after **7 days** without corroborating signal or CMDB re-sync, hard-downgrade (exclude from confidence-bearing localize) after **30 days**. Any CMDB pull that still lists the edge resets the clock. Source: [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) §3 / decision log #4 (also Fusion). This is the numeric target the Pipeline HLD used to leave open (“no numeric target yet”).

**Bakeoff engines (Lean / Federated) today:** this LLD’s §5 notes that classic `topology.json` loaders still carry **no** staleness marker in code — so the 7d/30d policy is **not yet measured** on the UC bakeoff path. Pillar B PoC writes `valid_from` / `valid_to` on edges and has an E5-shaped maintain stub; wiring that to the 7d/30d clocks is follow-on work, not a reason to leave the product number blank here.

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

Per HLD §16: E3 maps to **FR-C (topology/time)**, and (jointly with E5) **FR-I/J (operability/freshness)**. Product freshness numbers for `declared` edges are locked in §6 (7d / 30d); bakeoff engine code still lacks a measured marker (§5).

## 9. Open decisions carried to future revisions

- **Operational-graph provenance is not on this `topology.json`.** Merging `evidence_type` / `refresh` / signatures onto the corpus format is an LLD revision after an ADR, not a docs-only fix. Until then, that chapter’s §3 is the target; this file is the runtime.
- **No staleness/freshness marker on `GraphSnapshot`.** Neither engine's graph object carries a timestamp or version. Before this can be called "Done," decide the minimum viable marker (e.g., `topology.json`'s own file mtime, or an explicit `snapshot_ts` field written by whichever process last refreshed it).
- **No topology crawler exists.** `INGESTION_POC_PLAN.md` D3 is Planned, not built. Every current run — bakeoff and lab — uses a static, hand-authored or synthetically-generated `topology.json`. Live discovery is a real, open piece of work, not a documentation gap.
- **CMDB enrichment is entirely unimplemented,** consistent with the HLD calling it optional — but worth stating plainly rather than letting "optional" imply "partially done."
- **Lean's `node_types` lookup has no guard for a `to`-only node** (§5) — low risk on the frozen corpus (nodes list is complete there) but a real risk if E3 is ever fed a partial/derived topology the way Federated's builder tolerates.

## 10. Motadata Pillar B path — `graph_*.v1` / Dest `map/` (primary Motadata contract)

For Motadata unified fabric, E3 Topology is implemented by the Pillar B GraphWriter under [`pillar-ab-implementation/pillar-b/poc/graph/`](../../pillar-ab-implementation/pillar-b/poc/graph/). This is the **Motadata write path** for `map/`. Bakeoff §2–§3 remains the Lean/Federated load path — neither replaces the other.

| | |
|--|--|
| **IN** | Optional `topology.bootstrap.json` + post-E2 stream with topology claim (`writer_stream.v1` `topology` block, or lab `ingest.v1` `topo_update`) and `identity.status=resolved` ([`E2_INPUT_FIXTURES.md`](../../pillar-ab-implementation/E2_INPUT_FIXTURES.md) · [`WRITER_REGULATOR.md`](../../pillar-ab-implementation/contracts/WRITER_REGULATOR.md)) |
| **OUT** | `graph_snapshot.v1` + `nodes.jsonl` / `edges.jsonl` via Gate B Dest (`map/…`) — [`MAP_WRITE_READ_RECORD.md`](../../pillar-ab-implementation/contracts/MAP_WRITE_READ_RECORD.md) |
| **Admit** | **NOOP** — no topology claim (no `topology` block / not legacy `topo_update`; metric/event/span/anomaly-only lines) · **WRITE** — wave-1 emit · **DROP** — unresolved/synthesized identity, never-CI types, unknown relation · phased map-NOOP — catalog relation not yet wave-1 ([`pillar-b/README.md`](../../pillar-ab-implementation/pillar-b/README.md)) |
| **Wave-1 emit** | `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of` |
| **E5 stub** | [`maintain.py`](../../pillar-ab-implementation/pillar-b/poc/graph/maintain.py) `maintain_graph_validity` — expire `valid_to`, drop stale corroborating; does **not** create edges ([`LLD-E5-Maintain.md`](./LLD-E5-Maintain.md)) |

**Acceptance (PoC):**

```bash
cd pillar-ab-implementation/pillar-b/poc && make install && make test-graph
```

Pass criteria: schema-valid nodes/edges/snapshot; CI-only vertices (Alert/Change rejected); wave-1 relations emitted; `neighbors("checkout-api")` reaches host/db from `sample_estate/customer_checkout/`. Schemas: [`pillar-ab-implementation/contracts/schemas/`](../../pillar-ab-implementation/contracts/schemas/). Guide: [`SAMPLE_IO.md`](../../pillar-ab-implementation/pillar-b/poc/sample_estate/customer_checkout/SAMPLE_IO.md). Hub walkthrough: [`graphwriter-io-walkthrough.html`](../fabric/graphwriter-io-walkthrough.html).

**Design gaps (honest):** continuous derivation at per-edge `refresh` cadence is not lab-built; unresolved-bucket → discovery feedback into E3 is Design-level (operational-graph §4 E2/E3).

---

*Part of the LLD backlog defined in [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §18. Siblings: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) · [`LLD-E4-Stores.md`](./LLD-E4-Stores.md) · [`LLD-E5-Maintain.md`](./LLD-E5-Maintain.md).*
