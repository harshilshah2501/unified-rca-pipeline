# Architecture Rationale

**ObserveOps note:** Lean is the primary evaluation engine for ObserveOps classic infra ([ADR-001](../../docs/ADR-001-lean-primary-engine.md); not a finalized product commitment). This rationale justifies the **federated** three-paper synthesis as an optional / research hybrid — not the ObserveOps default. Implementable shipping-state overview: [`ARCHITECTURE.md`](./ARCHITECTURE.md). Limits: [`LIMITATIONS_AND_FUTURE.md`](./LIMITATIONS_AND_FUTURE.md).

Design decisions, novelty claims, and paper-level analysis behind the federated architecture. For hop contracts see [ORCHESTRATOR.md](./ORCHESTRATOR.md); for storage vision see [STORAGE_TIERS.md](./STORAGE_TIERS.md).

---

## Core novelty claim

**No existing deployment combines Panorama, Murphy, and Nezha.**

Each paper is a standalone system, built and evaluated independently, with no cross-citation or integration:

| Paper | Year | Gap it leaves | Points at (but doesn't integrate) |
|-------|------|---------------|-------------------------------------|
| **Panorama** (OSDI '18) | 2018 | No causality tracking; no recovery actions | Tracing systems (Dapper, X-Trace) as complementary |
| **Murphy** (SIGCOMM '23) | 2023 | Time-separated cause/effect, metastable failures, thread-local faults | Finer-grained telemetry (Nezha's territory) |
| **Nezha** (FSE '23) | 2023 | Relies on external anomaly-detection triggers | Robust detectors like USAD — functionally Panorama's role |

The federated pipeline — **Panorama detects → Murphy macro-localizes → Nezha micro-localizes** — is a synthesis, not something from the literature or any known commercial platform. The **orchestrator** that connects them is a genuinely new contribution.

---

## What each paper contributes

Each paper is a **system** (research prototype) built around one core **algorithm**, not a protocol or specification:

| System | Core algorithm | Data representation | Validated on |
|--------|----------------|---------------------|--------------|
| Panorama | Bounded-look-back majority voting | LOS evidence graph (observer→subject) | ZooKeeper, HDFS |
| Murphy | Counterfactual MRF + Gibbs sampling | Cyclic dependency graph + metric time series | Production cloud telemetry |
| Nezha | Expected vs. actual pattern scoring (`S_C / (S_C + S_P)`) | Per-trace event graph | TrainTicket, Online Boutique |

None define a wire protocol, interchange format, or formal spec. Interoperability (schemas, trigger contracts, confidence formats) must be designed — see [ORCHESTRATOR.md](./ORCHESTRATOR.md).

---

## Why three algorithms are necessary but not sufficient

Each paper's limitations point at a gap only an orchestrating layer can close:

### a) No causality glue between tiers

- Panorama detects gray failures via evidence but does **not** track causality between components.
- Murphy reasons about causality but only across a pre-defined dependency graph — it doesn't decide **when** to fire.
- Nezha ranks event patterns within a trace's span tree but doesn't know which service to inspect.

The handoff logic (Detection → Macro → Micro) is pure orchestration, not derived from any paper.

### b) Trigger-to-algorithm routing / arbitration

Panorama flags gray failures. Murphy can also self-trigger via threshold-based symptom scanning. A coordinator must reconcile independent detectors to avoid duplicate or conflicting RCA passes.

### c) Confidence / conflict resolution

| Algorithm | Output type | Confidence semantics |
|-----------|-------------|---------------------|
| Panorama | Boolean / evidence score | Observer consensus strength |
| Murphy | Posterior distribution | Gibbs sampling probability |
| Nezha | Ranked pattern pair | Pattern drift score |

Fusing these into one SRE-facing verdict requires a layer none of the papers specify.

### d) Feedback loop / state sharing

| Algorithm | Data lifecycle |
|-----------|----------------|
| Panorama | Continuous LOS accumulation |
| Murphy | Per-incident retrain on 1-week lookback |
| Nezha | Separate fault-free baseline + fault-suffering window |

An orchestrator must manage what data each tier sees and when.

---

## Tier naming — resolved

Two orderings were conflated in early drafts:

| Ordering | What it measures | Old label |
|----------|------------------|-----------|
| **Storage role** | Data velocity and retention | Tier 1 = Event graph, Tier 2 = Knowledge graph |
| **Execution flow** | What runs during an incident | Panorama → Murphy → Nezha |

**Resolution (adopted):**

- **Storage tiers** use role names only: **Speed tier** (event graph) and **Structural tier** (knowledge graph). No numbers.
- **Pipeline steps** use sequence numbers matching the dissection docs: Step 1 (Panorama) → Step 2 (Murphy) → Step 3 (Nezha).
- **Orchestrator** is explicitly separate — not a storage tier.

This matches [Panorama_dissection.md](./dissections/Panorama_dissection.md) (Tier 1), [Murphy_dissection.md](./dissections/Murphy_dissection.md) (Tier 2), and [Nezha-dissection.md](./dissections/Nezha-dissection.md) (Tier 3) for pipeline steps, while avoiding the false impression that "Tier 1 storage = step 1."

---

## Why two storage tiers

The speed/structural split follows a standard lambda-architecture pattern:

| | Speed tier | Structural tier |
|---|------------|-----------------|
| Velocity | Per-event writes (100K–1B EPS) | Per-entity updates (~100/sec/entity) |
| Retention | Minutes (hot window) | Days–weeks (topology, metrics) |
| Query pattern | Pattern scoring over trace windows | Graph traversal + statistical inference |
| Algorithms | Nezha only | Panorama + Murphy |

Merging them would force either the event store to hold topology (wrong access pattern) or the knowledge graph to ingest every span (impossible at scale).

---

## Open questions logged for PoC

These are tracked as open decisions in [REQUIREMENTS.md](./REQUIREMENTS.md):

- **OD-1** — Murphy trigger source (Panorama-only vs. dual-trigger arbitration)
- **OD-2** — Nezha baseline collection strategy
- **OD-3** — Fusion weighting and conflict resolution
- **OD-4** — Benchmark priority for validation
