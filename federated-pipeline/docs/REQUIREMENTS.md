# Requirements — Federated RCA PoC

**Scope:** Federated pipeline only (Panorama → Murphy → Nezha). For Motadata ObserveOps UC-1..UC-5, **lean is the primary engine** — see [`../../docs/ADR-001-lean-primary-engine.md`](../../docs/ADR-001-lean-primary-engine.md) and [`../../docs/ROADMAP.md`](../../docs/ROADMAP.md). This document tracks the federated PoC and optional microservice/code-path track (Phase C deferred).

## Problem statement

Production systems need root-cause analysis that spans three granularities:

1. **Detection** — catch gray failures that evade threshold-based alerting (Panorama)
2. **Macro localization** — identify which service/entity in the dependency graph caused a symptom (Murphy)
3. **Micro localization** — pinpoint the exact execution-path shift within a service (Nezha)

No existing deployment combines all three. This PoC validates the synthesis and the coordination layer that connects them.

## Goals

| # | Goal | Success signal |
|---|------|----------------|
| G1 | Run the full pipeline end-to-end on a benchmark workload | Panorama flag → Murphy posterior → Nezha pattern rank → fused verdict | **Done** — `crawler` + `hipster` |
| G2 | Prove the orchestrator contract | Hop payloads validated between components (see [ORCHESTRATOR.md](./ORCHESTRATOR.md)) | **Done** — hop logs + typed payloads in both scenarios |
| G3 | Validate storage-tier separation | Speed tier holds events only; structural tier holds topology + LOS + metrics | **Done** (PoC) — `IngestNormalizer` dual-stream + Redis speed / in-memory structural |
| G4 | Reproduce paper-level accuracy on reference datasets | Results within published tolerance on ZooKeeper/TrainTicket/Online Boutique | Partial — hipster topology + Nezha scorer; full `rca_data` eval via `--live-nezha` |

## Non-goals (PoC scope)

- Sustained **1B events/sec** production ingest (see [CAPACITY.md](./CAPACITY.md) for the scaling story)
- Multi-region, multi-tenant isolation guarantees
- Automated remediation or runbook execution
- Replacing existing APM/observability platforms

## PoC target environment

| Dimension | PoC target | Production vision |
|-----------|------------|-------------------|
| Event rate | ~100K EPS sustained | 1B EPS |
| Service topology | 10–50 microservices | 100K+ entities |
| Benchmarks | TrainTicket, Online Boutique, ZooKeeper logs | Hyperscaler telemetry backbone |
| Ingest | NATS → Rust normalizer (single cluster) | Tbps-class shard router |
| Speed-tier store | DragonflyDB (single node → small cluster) | 1,250–5,000 nodes |
| Structural-tier store | In-process DashMap + Arrow CSR (PoC); Vortex at scale | Tens–low hundreds of nodes |

## Functional requirements

### FR-1: Continuous ingestion (write path)

- **FR-1a** — Raw telemetry (traces, logs, metrics) enters via NATS.
- **FR-1b** — Rust normalizer emits Nezha `Event` records to the speed tier (Dragonfly).
- **FR-1c** — Observer reports flow to Panorama LOS in the structural tier (DashMap).
- **FR-1d** — Per-entity metric time series and dependency edges flow to Murphy stores (DashMap + CSR graph).

### FR-2: Incident RCA (query path)

- **FR-2a** — Panorama flags gray failures from accumulated LOS evidence.
- **FR-2b** — Orchestrator routes the flag to Murphy with a constructed symptom payload.
- **FR-2c** — Murphy returns a posterior distribution over candidate root-cause entities.
- **FR-2d** — Orchestrator narrows Murphy output to a service + time window for Nezha.
- **FR-2e** — Nezha returns ranked pattern pairs with scores.
- **FR-2f** — Orchestrator fuses all three outputs into a single RCA verdict.

### FR-3: Orchestrator

- **FR-3a** — Trigger arbitration when Panorama and Murphy both fire independently.
- **FR-3b** — Schema translation between hop boundaries (see [ORCHESTRATOR.md](./ORCHESTRATOR.md)).
- **FR-3c** — Baseline lifecycle management for Nezha fault-free vs. fault-suffering phases.
- **FR-3d** — Confidence fusion across incompatible output semantics.

### FR-4: Observability of the pipeline itself

- **FR-4a** — Each hop emits structured logs with incident ID, latency, and input/output hashes.
- **FR-4b** — Fused verdict is exposed via API for SRE UI or CLI.

## Implementation status

| Component | Reference impl | PoC target | Status |
|-----------|----------------|------------|--------|
| Panorama algorithm | `federated-pipeline/panorama/` (Go) | DashMap LOS | **Integrated** — Python InferView/InferPano in `panorama_majority.py` |
| Murphy algorithm | `federated-pipeline/murphy/` (Python) | Arrow CSR + DashMap | **Integrated** via `poc/adapters/murphy.py` |
| Nezha algorithm | `federated-pipeline/Nezha/` (Python) | Dragonfly + Lua | **Integrated** scorer; dataset path via `--live-nezha` (falls back if Drain3/data fail) |
| Orchestrator | `poc/orchestrator.py` | Python (Rust at scale) | **Done** — 6-hop pipeline with hop logging |
| Rust ingest normalizer | `poc/ingest.py` | NATS consumer | **Python stub done** — dual-stream split; Rust/NATS still future |
| Dragonfly Lua scripts | `poc/benchmarks/phase0_dragonfly.py` | Pattern scoring | **Done** — Lua ingest path exercised on Redis |
| Hop payload schemas | `poc/types.py` | JSON dataclasses | **Done** |
| Dragonfly throughput benchmark | `poc/benchmarks/phase0_dragonfly.py` | `CAPACITY.md` harness | **Measured** — Dragonfly **20.9K EPS** (2 thr, host-net, w=4, pipe=128, p99 0.35ms); Redis ~20K |
| End-to-end demo | `crawler` + `hipster` + `ingest` | Murphy Fig.1 + Online Boutique | **Done** |
| Speed-tier Nezha | `poc/adapters/nezha_speed.py` | Score from `pc:` keys | **Done** — `--with-speed-tier` |

## Open decisions

| ID | Question | Options | Blocking |
|----|----------|---------|----------|
| OD-1 | Primary Murphy trigger | Panorama-only / Murphy self-scan / both with arbitration | Orchestrator routing rules |
| OD-2 | Nezha baseline collection | Rolling window / deploy-gated snapshot / manual mark | FR-3c lifecycle |
| OD-3 | Fusion strategy | Weighted vote / Bayesian combine / rule-based precedence | FR-3d verdict format |
| OD-4 | PoC benchmark priority | TrainTicket first / Online Boutique first | G4 validation order |
