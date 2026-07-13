# Architecture — Federated Graph Topology

**Scope:** Federated pipeline. Motadata ObserveOps primary engine is lean ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)).

## Overview

The federated PoC uses **two storage tiers** and a **three-step pipeline**, connected by an **orchestrator** that is not part of either storage tier.

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (coordination)                   │
│   trigger routing · schema translation · narrowing · fusion     │
└────────────┬──────────────────────────────────────┬─────────────┘
             │ query path                           │
   ┌─────────▼──────────┐              ┌───────────▼────────────┐
   │  STRUCTURAL TIER    │             │      SPEED TIER        │
   │  (Knowledge Graph)  │             │    (Event Graph)       │
   │                     │             │                        │
   │  Vortex/Arrow CSR   │             │   DragonflyDB          │
   │  + DashMap LSM      │             │   ZSETs + HSETs + Lua  │
   │                     │             │                        │
   │  Panorama (Step 1)  │             │   Nezha (Step 3)       │
   │  Murphy   (Step 2)  │             │                        │
   └─────────▲──────────┘              └───────────▲────────────┘
             │ write path B                          │ write path A
             └──────────────┬────────────────────────┘
                    NATS → Rust normalizer
```



## Storage tiers



### Speed tier — Event Graph (Dragonfly / Nezha)

**Role:** Ingest high-velocity traces, logs, and metrics. Build temporal execution graphs per request.


| Property          | Value                                                  |
| ----------------- | ------------------------------------------------------ |
| Storage           | DragonflyDB (shared-nothing, multi-threaded in-memory) |
| Question answered | *What happened, when, along which execution path?*     |
| Algorithm         | Nezha — expected vs. actual pattern scoring            |


**Data model:**


| Key pattern                                 | Type | Contents                                                               |
| ------------------------------------------- | ---- | ---------------------------------------------------------------------- |
| `tg:{tenant}:{trace_id}:{minute}`           | ZSET | Temporal event ordering per trace                                      |
| `pc:{phase}:{tenant}:{hash(pattern) % 256}` | HSET | Pattern occurrence counts; `phase` = `fault-free` or `fault-suffering` |


Sharding by `hash(pattern) % 256` prevents hot-key bottlenecks. Server-side Lua scripts compute Nezha scores (`Score = S_C / (S_C + S_P)`) on the data layer to minimize network round-trips.

### Structural tier — Knowledge Graph (Vortex/Arrow + DashMap)

**Role:** Store persistent service topology, health observations, and metric time series. Support graph traversals and property updates.


| Property          | Value                                                    |
| ----------------- | -------------------------------------------------------- |
| Graph storage     | Vortex/Arrow CSR format (vectorized BFS traversals)      |
| Property storage  | DashMap lock-free LSM (~100 updates/sec/entity)          |
| Question answered | *Who is unhealthy, and why across the dependency graph?* |
| Algorithms        | Panorama (Step 1), Murphy (Step 2)                       |


**Algorithm mapping:**

- **Panorama** — DashMap LOS stores observer→subject health evidence; bounded-look-back majority voting flags gray failures.
- **Murphy** — Vortex CSR graph holds dependency edges; DashMap holds per-entity metric time series; counterfactual MRF + Gibbs sampling localizes macro root cause.

> **PoC note:** Reference implementations use in-process stores. PoC targets DashMap + Arrow CSR locally; Vortex replaces Arrow at production scale.



## Pipeline steps (execution order)

These are **not** the same as storage tier labels. During an incident, execution runs structural tier first, speed tier last.


| Step | Algorithm | Storage tier | Question                                   |
| ---- | --------- | ------------ | ------------------------------------------ |
| 1    | Panorama  | Structural   | Who is unhealthy right now?                |
| 2    | Murphy    | Structural   | Which upstream entity caused this symptom? |
| 3    | Nezha     | Speed        | Which code-path event patterns shifted?    |


See [learning dissections](./dissections/Panorama_dissection.md) for algorithm-level detail.

---



## Write path (continuous)

Raw telemetry splits into **two parallel streams** at ingestion. They do not merge at the storage layer.

### Stream A → Speed tier (Nezha)

```
NATS → Rust normalizer → Dragonfly
```


| Stage     | Input                  | Output                                                                      |
| --------- | ---------------------- | --------------------------------------------------------------------------- |
| Ingest    | Raw trace spans + logs | —                                                                           |
| Normalize | Span/log records       | `Event { trace_id, span_id, timestamp, service, event_type, pattern_hash }` |
| Store     | Events                 | `tg:` ZSETs + `pc:` HSETs keyed by tenant, trace, minute, phase             |




### Stream B → Structural tier (Panorama + Murphy)

```
NATS → Rust normalizer → DashMap LOS + DashMap metrics + Vortex CSR
```


| Consumer | Input                                                    | Store                                  |
| -------- | -------------------------------------------------------- | -------------------------------------- |
| Panorama | Observer reports (`peer@2 saw peer@1 as UNHEALTHY:30`)   | DashMap LOS, keyed by observer→subject |
| Murphy   | Per-entity metric time series (CPU%, latency, drop rate) | DashMap property store                 |
| Murphy   | Topology/dependency edges (service A calls service B)    | Vortex/Arrow CSR graph                 |


**Separation invariant:** The speed tier never sees health verdicts. The structural tier never sees individual trace spans. Only the orchestrator holds cross-tier context.

---



## Query path (per incident)


| Hop | Component    | Input                                                             | Output                                                      |
| --- | ------------ | ----------------------------------------------------------------- | ----------------------------------------------------------- |
| 1   | Panorama     | Accumulated LOS evidence for an entity                            | Gray-failure flag: `{ entity, evidence_score, timestamp }`  |
| 2   | Orchestrator | Panorama flag                                                     | Murphy invocation decision + symptom payload                |
| 3   | Murphy       | `{ flagged_entity, symptom_metric }` + CSR graph + metric history | Posterior: `{ entity_i: probability_i, ... }`               |
| 4   | Orchestrator | Murphy ranked entities                                            | Nezha scope: `{ service, time_window, phase }`              |
| 5   | Nezha        | Scoped query → 256 concurrent Lua calls on `tg:` / `pc:` keys     | Ranked pairs: `{ expected_pattern, actual_pattern, score }` |
| 6   | Orchestrator | Panorama + Murphy + Nezha outputs                                 | Fused RCA verdict                                           |


Hop payload schemas are defined in [ORCHESTRATOR.md](./ORCHESTRATOR.md).

---



## Technology stack


| Layer           | PoC                                                | Production vision               |
| --------------- | -------------------------------------------------- | ------------------------------- |
| Ingest          | NATS + Rust                                        | NATS + Rust shard router        |
| Speed tier      | DragonflyDB (1–3 nodes)                            | DragonflyDB fleet (1K–5K nodes) |
| Structural tier | DashMap + Arrow CSR in-process                     | DashMap LSM + Vortex            |
| Algorithms      | Panorama (Go), Murphy (Python), Nezha (Python/Lua) | Same algorithms, storage-backed |
| Orchestrator    | Rust service                                       | Rust service, HA cluster        |
| API             | HTTP/gRPC verdict endpoint                         | Same + SRE dashboard            |


