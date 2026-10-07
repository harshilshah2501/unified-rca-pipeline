# LLD-E4 — Stores

**Status:** Draft for review
**Version:** v1.1
**Owner:** ObserveOps RCA engineering
**Parent:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §8 (E4 Stores contract), §5 (crosswalk: E4 is part of the 5-stage "Ingest" phase)
**Related:** Motadata Pillar A [`pillar-a/`](../../pillar-ab-implementation/pillar-a/) · [`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) · [`E2_INPUT_FIXTURES.md`](../../pillar-ab-implementation/E2_INPUT_FIXTURES.md)
**Gate checklist (per HLD §18):** stage ID/purpose referenced ✓ · concrete schema/API defined ✓ (§1 Motadata · §2 bakeoff) · acceptance test ✓ (§5 bakeoff · §8 PoC) · evidence-maturity tag stated ✓

> **Motadata writer SoT:** SketchRegulator admits when a **`metric` block** is present on `writer_stream.v1` (no `fact_kind`) — [`WRITER_REGULATOR.md`](../../pillar-ab-implementation/contracts/WRITER_REGULATOR.md). Lab fixtures may still use legacy `ingest.v1` + `fact_kind=metric_sample`. Bakeoff UC JSON (§2) is a separate evidence path.

---

## 0. Dual path — Motadata history vs bakeoff evidence stores

E4 is part of always-on fabric. After E2, Motadata runs **E4 Stores ∥ E3 Topology** (same `writer_stream.v1`, different presence predicates: `metric` vs `topology`). Rooms stay independent: `history/` never syncs continuously into `map/` ([`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G16).

| Path | What E4 means | Primary artifact |
|------|----------------|------------------|
| **Motadata Pillar A (§1, §8)** | Metric sketch history for Detect door C and WorkingSet joins | `sketch.v1` rows under Dest `history/` — **metrics-only** |
| **Bakeoff Lean / Federated (§2)** | Reference-engine evidence bundles / structural+speed stores | Flat UC JSON / in-memory Fed stores — multi-modality |

Do not equate “E4 Stores” with “all MELTS in one sketch.” Logs (`event`) and traces (`trace_span`) still matter for Identify on bakeoff/reference paths; they **silent-skip** at Pillar A SketchWriter (G31). Future Motadata log/trace history would be **other history row types**, not an expansion of `sketch.v1`.

---

## 1. Purpose and boundary (from HLD §8)

E4 Stores persists queryable evidence over time under the shared identity E2 established, so E6 Detect and E10 Identify have historical evidence to reason over (and E9 has an advisory dotted dependency on it per HLD §9's contract diagram, same as E3).

**Motadata fabric job (Pillar A):** admit lines with a `metric` block (lab: `fact_kind=metric_sample`) and resolved identity → aggregate into windowed `sketch.v1` (T-Digest + buckets + seasonal baseline). Sketches do **not** carry edges (`src_ci_id` / `dst_ci_id` / `relation` forbidden).

**Trigger:** continuous writes.
**Inputs:** `IdentifiedRecord` (E2's output).
**Outputs:** Motadata — `sketch.v1` / `history/`; bakeoff — modality-specific query surfaces (§2).
**Preconditions:** storage backends available (PoC: Gate B `files.v1`).
**Postconditions:** time-sliced evidence retrievable by CI (`entity_id` ≡ `ci_id`) and tags.
**Failure if missing:** E6 Detect and E10 Identify have no historical evidence to work from.
**Degradation:** missing modality produces thin evidence bundles (E10 is supposed to flag this explicitly, per HLD §8 E10).

Operational-graph §4 says E4 may **read** shared identity / plane applicability from the graph. That is join-key / applicability context — **not** “sketch rows contain topology.”

## 2. Two bakeoff store implementations — genuinely different maturity, not just different code

Unlike E1–E3, where both engines implement roughly comparable mechanisms, **bakeoff E4 is where Lean and Federated diverge sharply**, and this LLD reports that honestly rather than smoothing it over. Motadata Pillar A (§8) is a third, product-shaped path.

### 2.1 Lean — flat files, no store abstraction at all

There is no `Store` class, no index, no TTL, no query API anywhere in `lean-pipeline/core_engine`. "Storage" is: a per-UC directory of frozen JSON files, read fully into memory once per `diagnose` call.

```python
def load_bundle(uc_id: str, corpus_dir: Path) -> dict:
    base = corpus_dir / uc_id
    events_path = base / "events.json"
    events = json.loads(events_path.read_text()) if events_path.exists() else {"events": []}
    return {
        "uc_id": uc_id,
        "topology": json.loads((base / "topology.json").read_text()),
        "anomalies": json.loads((base / "anomalies.json").read_text()),
        "events": events,
        "symptom_seed": json.loads((base / "symptom_seed.json").read_text()),
        "ground_truth": json.loads((base / "ground_truth.json").read_text()),
    }
```

Reference: [`lean-pipeline/core_engine/observeops/ingest/bundle.py`](../../lean-pipeline/core_engine/observeops/ingest/bundle.py). The only "query surfaces" are two small helper functions over the fully-loaded dict:

- `anomaly_by_ci_signal(bundle) -> dict[(ci, signal), anomaly]` — the closest thing to an indexed lookup E4 has on the Lean side.
- `crossed_anomalies(bundle) -> list[anomaly]` — filters to `crossed == True` only.

**Write path** (how a bundle gets materialized in the first place): [`ingestion-poc/builders/lean_bundle_writer.py`](../../ingestion-poc/builders/lean_bundle_writer.py) — "N5," takes an `ingest.v1` stream plus topology/ground-truth/events and writes an ObserveOps-shaped UC directory that `load_bundle()` can read. This is a **one-shot batch write**, not a continuously-updated store — there is no append/upsert semantic, no retention window, no compaction.

**What this means concretely:** E4's HLD postcondition — "time-sliced evidence retrievable by CI and tags" — is true for Lean only in the weakest sense: the whole bundle *is* the time slice (bounded to one UC's frozen window), and "retrieval" is an in-memory dict comprehension over data that's already fully loaded. There is no mechanism to query "give me CI X's evidence for the last 15 minutes" without loading the entire bundle first.

### 2.2 Federated — two-tier design, partially implemented as PoC stand-ins

[`STORAGE_TIERS.md`](../../federated-pipeline/docs/STORAGE_TIERS.md) describes the production vision (Vortex/Arrow CSR + DashMap structural tier; DragonflyDB speed tier). **PoC today implements approximations of both, explicitly labeled as stand-ins in that same doc** — this LLD does not treat the PoC code as if it were the production design.

**Structural tier (PoC):**

```python
@dataclass
class StructuralStore:
    """PoC stand-in for DashMap LOS + property store + CSR edges."""
    los: list[ObserverReport]
    metrics: list[MetricPoint]
    edges: list[TopologyEdge]
    entities: set[str]
```

Reference: [`federated-pipeline/poc/stores/structural.py`](../../federated-pipeline/poc/stores/structural.py) — in-memory, no persistence across process restarts.

**`MetricStore` — the one real queryable interface in this repo:**

```python
class MetricStore(ABC):
    def get_historical_metrics(self, entity_id, metric_name, end_time, lookback_days=7) -> list[MetricSample]: ...
    def get_current_metrics(self, entity_id, incident_time) -> dict[str, float]: ...
    def get_entity_metadata(self, app_id) -> list[Entity]: ...
    def compute_historical_stats(self, entity_id, end_time, lookback_days=7) -> dict[str, tuple[float, float]]: ...
    def list_metric_names(self, entity_id, end_time, lookback_days=7) -> list[str]: ...

class DictMetricStore(MetricStore):
    """Dict-backed concrete implementation."""
```

Reference: [`federated-pipeline/murphy/store.py`](../../federated-pipeline/murphy/store.py). This is the only store in the repo with an actual **time-windowed query contract** (`lookback_days`, `end_time`) — it computes `compute_historical_stats` (mean/std) that `RelationshipGraph.prune_candidates` (E3, §3.2) consumes directly for anomaly filtering. A second concrete implementation, `CsvMetricStore` ([`federated-pipeline/murphy/adapters/csv_store.py`](../../federated-pipeline/murphy/adapters/csv_store.py)), backs the same interface from DeathStarBench CSV/Parquet traces — same query contract, different backing data, which is exactly the kind of interface-stable swap E4's contract is supposed to allow.

**Speed tier (PoC → real Dragonfly):**

| Key pattern | Type | Contents |
|---|---|---|
| `tg:{tenant}:{trace_id}:{minute}` | ZSET | Temporal event ordering per trace |
| `pc:{phase}:{tenant}:{hash(pattern)%256}` | HSET | Pattern counts; `phase` = `fault-free` \| `fault-suffering` |

Write path: [`ingestion-poc/builders/federated_store_writer.py`](../../ingestion-poc/builders/federated_store_writer.py) ("N4") — writes a **file-backed** metric slice + topology edges + Dragonfly-key stub by default (no Redis required for smoke), records timing in `store_meta.json`. Real Dragonfly load is opt-in via [`ingestion-poc/lab/metric_slice_read.py`](../../ingestion-poc/lab/metric_slice_read.py) `--load-dragonfly`.

## 3. NFR baseline and measured evidence

HLD §15 sets "retention and query latency budgets" as the P1 target for E4, with no number filled in at HLD level. Two real measurements exist and are cited here — this is the correct home for them, more than E1, since these specifically measure the *store* write path, not just ingest admission:

| Measurement | Value | Run | Caveat |
|---|---|---|---|
| Dragonfly soak — sustained write EPS | **67,084.8 EPS**, p99 write **0.379 ms**, 120 s, 16 workers | `cost-pro6000-20260721Tsoak` | This is the report's own stated **headline gate** for the store path — treat it as the number to cite, not the raw Vector/fan-out EPS from E1 |
| Sink bytes / extrapolated GB-day | L0: 3,097.75 GB/day · F1: 6,768.97 GB/day | `cost-pro6000-20260721Tfinal` | **Explicitly extrapolated from sink write rate, not retention-backed** — the cost report says this itself; do not read it as a measured retention/storage-capacity result |

**No retention policy, TTL, or indexing has been implemented anywhere** in either store (Lean has no store to apply one to; Federated's `StructuralStore`/`DictMetricStore` are unbounded in-memory lists that grow for the process lifetime). This matches the HLD's own unfilled NFR — this LLD confirms the gap is real, not just undocumented.

**Evidence maturity: Grounded** for the EPS/latency numbers (measured, cited run IDs); **Local/extrapolated, clearly labeled** for GB/day; **none** for retention/TTL (nothing exists to measure).

## 4. Failure modes and degradation

| Condition | Behavior today | Status |
|---|---|---|
| `events.json` missing | Guarded: `.exists()` check, falls back to `{"events": []}` | Grounded — implemented, matches HLD's documented degradation ("missing modality produces thin evidence bundles"). **Correction during verification:** every UC in the current corpus (`UC-1..UC-5`, `UC-3b`) actually ships an `events.json` file — the "required on UC-2/4/3b" framing in older docs describes which UCs' *ground truth* depends on events, not which UCs physically have the file. The `.exists()` guard is still real, defensive code; it's just not exercised by any missing-file case in the corpus as it stands today |
| `topology.json` / `anomalies.json` / `symptom_seed.json` / `ground_truth.json` missing | **Unguarded** `.read_text()` — raises `FileNotFoundError` and the whole diagnose call fails hard | **Gap.** The HLD's stated degradation behavior ("missing modality produces thin evidence bundles") is only actually implemented for the one modality (`events.json`) that the corpus itself already treats as optional. A missing *required* file does not degrade — it crashes. This is worth a decision, not silent inconsistency: either narrow the HLD's degradation claim to "optional modalities only," or add graceful handling for the required files too |
| Federated `DictMetricStore` queried for an entity/metric never added | Returns empty list / empty dict (no exception) | Grounded — implemented, genuinely graceful |
| Process restart (Federated PoC stores) | All in-memory state lost — `StructuralStore` and `DictMetricStore` have no persistence | Grounded as a known PoC limitation (matches `STORAGE_TIERS.md`'s own "PoC today: in-memory... Vortex/DashMap/NATS Rust path is deferred" framing) |

## 5. Acceptance test (evidence maturity: Grounded)

**Lean path:**

```python
from pathlib import Path
from core_engine.observeops.ingest.bundle import load_bundle, anomaly_by_ci_signal, crossed_anomalies

for uc in ["UC-1", "UC-2", "UC-3", "UC-4", "UC-5"]:
    bundle = load_bundle(uc, Path("datasets/observeops"))
    idx = anomaly_by_ci_signal(bundle)
    assert all(isinstance(k, tuple) and len(k) == 2 for k in idx)
    assert all(a["crossed"] for a in crossed_anomalies(bundle))
```

Pass criteria: loads without error for every UC-1..UC-5 (every current corpus UC ships `events.json`; the `.exists()` guard remains defensive for optional/missing-file degradation — see §4). The `(ci, signal)` index is well-formed, and `crossed_anomalies` never returns an anomaly with `crossed: false`.

**Federated path:**

```bash
python3 ingestion-poc/builders/n45_chain.py --suite UC-1 --skip-diagnose
```

This is the real chain — `f1_run.run_f1()` (N1–N3 fan-out) → `federated_store_writer.write_federated_stores()` (N4) → `lean_bundle_writer.write_lean_bundle()` (N5), per [`ingestion-poc/builders/n45_chain.py`](../../ingestion-poc/builders/n45_chain.py). (Calling `write_federated_stores` directly, or via bare `f1_run.py`, does **not** exercise N4 — `f1_run.py` alone only does the N1–N3 sink fan-out; the store-writer call has to come from the chain script or its own CLI.)

Pass criteria: `ingestion-poc/out/f1-smoke/UC-1/federated_stores/` is written with `store_meta.json` recording a timing, plus the metric-slice + topology-edge output files, per [`ingestion-poc/builders/federated_store_writer.py`](../../ingestion-poc/builders/federated_store_writer.py)'s `write_federated_stores()` contract.

**Evidence maturity: Grounded** — both paths are repo-executable against real corpus/lab data, not hypothetical.

## 6. Traceability

Per HLD §16: E4 maps to **FR-C (topology/time)** jointly with E3, and (jointly with E5) **FR-I/J (operability/freshness)**.

## 7. Open decisions carried to future revisions

- **Lean's required-file loading has no degradation path** (§4) — decide whether to implement graceful handling or narrow the HLD's E4 degradation claim to match reality.
- **No retention/TTL/indexing exists anywhere** — this is the same gap the HLD itself left numerically unfilled; this LLD confirms there is no code to point a number at yet. A minimal retention policy (even a fixed window) should land before E4 can be called "Done."
- **Federated stores have no persistence across restarts.** Acceptable for PoC per `STORAGE_TIERS.md`'s own framing, but should be explicitly re-confirmed as in-scope-or-not before any live (non-replay) deployment, since E1's live Vector configs assume something is durably receiving their output.
- **GB/day figures are extrapolated, not measured** — do not let them drift into being cited as a capacity SLA in a later doc; the cost report itself already carries this caveat, and this LLD preserves it rather than losing it in a later summary.

## 8. Motadata Pillar A path — `sketch.v1` / Dest `history/` (primary Motadata contract)

The Motadata Pillar A PoC under [`pillar-ab-implementation/pillar-a/poc/sketch/`](../../pillar-ab-implementation/pillar-a/poc/sketch/) writes hybrid `sketch.v1` rows (T-Digest + buckets + seasonal baseline) through the Gate B **`files.v1`** dest (`history/sketches.jsonl`). This is the **Motadata E4 write path**. Bakeoff §2 remains Lean/Federated reference evidence — neither replaces the other.

| | |
|--|--|
| **Admits** | `metric` block present (lab: `metric_sample`) + `identity.status=resolved` |
| **Silent skip** | topology-only / event / span / anomaly lines (no metric claim) |
| **Must not** | Emit edges; write into `map/` |
| **Join** | `entity_id` ≡ graph `ci_id` at read time (E8 Scope / integration harness) |

A and B remain **parallel writers**; optional WorkingSet read-join lives under [`integration/`](../../pillar-ab-implementation/integration/), not a combined writer package. Deep dive: [`PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../fabric/PILLAR_A_PERCENTILES_DEEP_DIVE.md).

**Acceptance (PoC):**

```bash
cd pillar-ab-implementation/pillar-a/poc && make install && make test-sketch
# optional later, after both unit suites are green:
# cd pillar-ab-implementation/integration && … (read-join harness)
```

Pass criteria: schema-valid rows without topology edges; wave-1 metrics only; `get_window_percentiles` / `get_metric_baseline` over fixture stream. Identity join with graph is covered by the optional `integration/` harness — not by a combined `poc/` tree. Schemas: [`pillar-ab-implementation/contracts/schemas/sketch_v1.schema.json`](../../pillar-ab-implementation/contracts/schemas/sketch_v1.schema.json). Plan: [`IMPLEMENTATION_PLAN.md`](../../pillar-ab-implementation/IMPLEMENTATION_PLAN.md).

---

*Part of the LLD backlog defined in [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §18. Siblings: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) · [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) · [`LLD-E5-Maintain.md`](./LLD-E5-Maintain.md).*
