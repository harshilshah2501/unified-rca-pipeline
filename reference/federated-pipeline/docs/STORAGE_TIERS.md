# Federated storage tiers (design vision)

**ObserveOps note:** Lean is the primary evaluation engine for ObserveOps ([ADR-001](../../docs/ADR-001-lean-primary-engine.md); not a finalized product commitment). This document describes the **federated** dual-tier storage model (PoC approximations + production vision). Shipping ObserveOps diagnose path does not require this stack — see lean [`ARCHITECTURE.md`](../../lean-pipeline/docs/ARCHITECTURE.md). Federated implementation status: [`ARCHITECTURE.md`](./ARCHITECTURE.md) · limits: [`LIMITATIONS_AND_FUTURE.md`](./LIMITATIONS_AND_FUTURE.md).

## Overview

The federated design uses **two storage tiers** and a **three-step pipeline**, connected by an **orchestrator** that is not part of either storage tier.

```
┌─────────────────────────────────────────────────────────────────┐
|                     ORCHESTRATOR (coordination)                   |
|   trigger routing · schema translation · narrowing · fusion     |
└────────────┬──────────────────────────────────────┬─────────────┘
             | query path                           |
   ┌─────────▼──────────┐              ┌───────────▼────────────┐
   |  STRUCTURAL TIER    |             |      SPEED TIER        |
   |  (Knowledge Graph)  |             |    (Event Graph)       |
   |                     |             |                        |
   |  Vortex/Arrow CSR   |             |   DragonflyDB          |
   |  + DashMap LSM      |             |   ZSETs + HSETs + Lua  |
   |                     |             |                        |
   |  Panorama (Step 1)  |             |   Nezha (Step 3)       |
   |  Murphy   (Step 2)  |             |                        |
   └─────────▲──────────┘              └───────────▲────────────┘
             | write path B                          | write path A
             └──────────────┬────────────────────────┘
                    NATS → Rust normalizer (aspirational)
```

**PoC today:** in-memory structural store + optional Redis/Dragonfly speed tier (`poc/stores/`, `IngestNormalizer`). Vortex/DashMap/NATS Rust path is deferred (Phase C/E).

## Speed tier — Event Graph (Dragonfly / Nezha)

**Role:** Ingest high-velocity traces, logs, and metrics. Build temporal execution graphs per request.

| Property | Value |
|----------|-------|
| Storage | DragonflyDB (shared-nothing, multi-threaded in-memory) |
| Question answered | *What happened, when, along which execution path?* |
| Algorithm | Nezha — expected vs. actual pattern scoring |

**Data model:**

| Key pattern | Type | Contents |
|-------------|------|----------|
| `tg:{tenant}:{trace_id}:{minute}` | ZSET | Temporal event ordering per trace |
| `pc:{phase}:{tenant}:{hash(pattern) % 256}` | HSET | Pattern counts; `phase` = `fault-free` or `fault-suffering` |

Sharding by `hash(pattern) % 256` prevents hot-key bottlenecks. Server-side Lua can compute Nezha scores (`Score = S_C / (S_C + S_P)`).

## Structural tier — Knowledge Graph (Vortex/Arrow + DashMap)

**Role:** Persistent topology, health observations, metric time series.

| Property | Value |
|----------|-------|
| Graph storage | Vortex/Arrow CSR (vectorized BFS) |
| Property storage | DashMap lock-free LSM |
| Question answered | *Who is unhealthy, and why across the dependency graph?* |
| Algorithms | Panorama (Step 1), Murphy (Step 2) |

- **Panorama** — DashMap LOS observer→subject evidence; bounded-look-back majority voting.  
- **Murphy** — CSR dependency edges + metric series; MRF + Gibbs macro localization.

> **PoC note:** Reference path uses in-process / simulated stores. Production Vortex replaces Arrow at scale.

## Pipeline steps vs storage tiers

Do not conflate:

| Scheme | Labels | Question |
|--------|--------|----------|
| **Pipeline steps** | Step 1→2→3 (Panorama→Murphy→Nezha) | What runs during an incident |
| **Storage tiers** | Speed / Structural | Where data lives |

| Step | Algorithm | Storage tier | Question |
|------|-----------|--------------|----------|
| 1 | Panorama | Structural | Who is unhealthy right now? |
| 2 | Murphy | Structural | Which upstream entity caused this symptom? |
| 3 | Nezha | Speed | Which code-path event patterns shifted? |

## Write path (continuous) — design

Raw telemetry splits into **two parallel streams**. They do not merge at the storage layer.

### Stream A → Speed tier (Nezha)

`NATS → Rust normalizer → Dragonfly` — events into `tg:` / `pc:` keys.

### Stream B → Structural tier (Panorama + Murphy)

`NATS → Rust normalizer → DashMap LOS + metrics + Vortex CSR`.

**Separation invariant:** Speed tier never sees health verdicts. Structural tier never sees individual trace spans. Only the orchestrator holds cross-tier context.

## Query path (per incident) — design

| Hop | Component | Output |
|-----|-----------|--------|
| 1 | Panorama | Gray-failure flag |
| 2–3 | Orchestrator + Murphy | Posterior over entities |
| 4–5 | Orchestrator + Nezha | Ranked pattern pairs |
| 6 | Orchestrator | Fused RCA verdict |

Hop schemas: [`ORCHESTRATOR.md`](./ORCHESTRATOR.md). Capacity / EPS: [`CAPACITY.md`](./CAPACITY.md).

## Technology stack

| Layer | PoC (today) | Production vision |
|-------|-------------|-------------------|
| Ingest | Python `IngestNormalizer` + optional Redis | NATS + Rust normalizer |
| Speed tier | Dragonfly/Redis 1 node | Dragonfly fleet |
| Structural tier | In-memory / simulated | DashMap LSM + Vortex |
| Orchestrator | Python `UnifiedRCAOrchestrator` | Rust HA service |
| ObserveOps API | **Lean** `:8780` | Federated API only if microservice track funded |
