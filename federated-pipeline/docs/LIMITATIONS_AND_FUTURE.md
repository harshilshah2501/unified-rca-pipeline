# Federated RCA — Limitations & Future Work

Companion to [`ARCHITECTURE.md`](./ARCHITECTURE.md). Motadata decision: **lean is primary** for classic ObserveOps ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)). Federated remains a PoC, bakeoff comparator, and optional microservice / code-path hybrid.

---

## 1. Limitations (current federated tree)

### 1.1 Not Motadata’s shipping primary engine

Phase D packaging (CLI / HTTP API / systemd RCA service) landed on **lean**, not federated. This tree has no Motadata-equivalent production diagnose API on `:8780`. Learning UI on `:8770` is teaching HTML only.

### 1.2 Reproducibility

Matched ObserveOps bakeoffs: federated **~40%** bit-stable across N=20 vs lean **100%**. Gibbs sampling and synthetic-store path variance show multi-hash runs on some UCs (notably UC-2/3/5). Bad fit when Motadata needs incident compare/diff and change control.

### 1.3 Classic-infra underuses federated strengths

Motadata corpus is Network → Host → VM → OS → App. Panorama gray-failure observers and Nezha code-path pairs shine on microservice workloads (hipster / TrainTicket). On UC-1..UC-5, root selection is dominated by Murphy + Motadata-aware fusion / lean-rule fallbacks — paying three-algorithm cost without a clear Accuracy premium (both engines **5/5**).

### 1.4 Complexity and Roadblock 5

Three heterogeneous algorithms + dual storage tiers + orchestrator translation. Lean solves the same Motadata tickets with one coherent walk. Fleet-wide Murphy CV as the default brain violates Motadata’s cost posture.

### 1.5 PoC ingest vs production vision

`IngestNormalizer` is a Python dual-stream stub. Rust/NATS shard router, Vortex CSR, DashMap LSM fleet, and HA Rust orchestrator are **design targets**, not Motadata deliverables. See [`STORAGE_TIERS.md`](./STORAGE_TIERS.md).

### 1.6 Open orchestrator decisions

[`ORCHESTRATOR.md`](./ORCHESTRATOR.md) still lists draft items (OD-1..OD-3): trigger arbitration, Nezha baseline lifecycle, fusion strategy. Fine for research; not Motadata-blocking while lean is primary.

### 1.7 Live Nezha / paper datasets

`--live-nezha` and full `rca_data` eval are partial; Drain3 / dataset gaps fall back. Paper accuracy claims are not Motadata bakeoff acceptance criteria.

### 1.8 Capacity numbers are host-bound

Phase 0 measured ~21K EPS Dragonfly on **2-core WSL** — a local floor, not a fleet sizing input. Do not extrapolate 1B EPS node counts from laptop measurements ([`CAPACITY.md`](./CAPACITY.md)).

### 1.9 Motadata fusion may lean on lean rules

When Murphy posterior is weak, `resolve_root_ci` can fall back to lean `shared_upstream` / `upstream_healthy`. That is honest Motadata scoring hygiene — it also means “federated win” narratives must not ignore shared Motadata rules.

### 1.10 Roadblock honesty

| Roadblock | Federated Motadata stance |
|-----------|---------------------------|
| **1a** | Panorama helps where interaction exists; true black boxes still detect-and-flag |
| **1b** | Org silos unsolved; Motadata joined graph does not require federated to prove 1b |
| **2** | Murphy live reconstruction strength — underused on frozen Motadata bundles |
| **3** | Workload keying still research/Corpus A; Motadata VMs out of scope |
| **4** | Corpus GT Mandatory by convention (shared with lean bakeoff) |
| **5** | Federated stack is the expensive choice; lean honors this by design |

---

## 2. When to choose federated vs lean

| Choose **lean** (default Motadata) | Choose **federated** (optional) |
|------------------------------------|----------------------------------|
| Classic infra typed CI tickets | Microservice gray failure + code-path / pair mining |
| Bit-stable, auditable answers | Will pay for Murphy CV + Nezha depth |
| Hard signals + rules + temporal enough | Dedicated microservice evaluation corpus in scope |
| Roadblock 5 tight | Research / Boutique / TrainTicket-style workloads |

Hybrid product posture: **lean primary + federated optional** ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)).

---

## 3. Future work (deferred)

Aligned with [`../../docs/ROADMAP.md`](../../docs/ROADMAP.md). Motadata critical path A/B/D is **complete** on lean.

### 3.1 Phase C — Federated ingest / microservice track (optional)

| ID | Item |
|----|------|
| C1 | NATS → normalizer dual-stream (Rust or hardened Python) |
| C2 | Stable Nezha `rca_data` / reliable `--live-nezha` |
| C3 | Resolve OD-1..OD-3 in ORCHESTRATOR.md |
| C4–C5 | Server-class Phase 0 EPS; ~100K EPS PoC target |

### 3.2 Phase E — Scale vision (explicitly later)

1B EPS fleet math, Vortex/DashMap production structural tier, event-size validation. **Not** Motadata-blocking.

### 3.3 Microservice evaluation corpus

If Motadata funds code-path RCA: freeze a Boutique/TrainTicket-style corpus with GT, then re-run lean vs federated on **that** contract — do not reuse classic-infra UC-1..UC-5 as the sole federated win claim.

### 3.4 Explicitly out of Motadata primary path

- Replacing lean as default classic-infra engine without new evidence  
- Learning UI as production RCA API  
- Claiming federated Accuracy superiority on ObserveOps UC-1..UC-5 (bakeoff: tied)  
- Sizing hyperscale fleets from 2-core WSL Phase 0  

---

## 4. What “done” means for federated (honest)

| Capability | Status |
|------------|--------|
| Orchestrator 6-hop demo (crawler / hipster) | **Done** |
| Dual-stream PoC ingest stub + optional Redis speed tier | **Done** (PoC) |
| ObserveOps bakeoff adapter + matched compare | **Done** |
| Motadata primary packaging | **N/A — lean** |
| Phase C production ingest / OD resolution | **Deferred** |
| Phase E 1B EPS | **Deferred** |

---

## 5. Related documents

| Document | Role |
|----------|------|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Components and workflows |
| [`REQUIREMENTS.md`](./REQUIREMENTS.md) | Federated PoC goals |
| [`../../benchmarking/results/comparison/DECISION.md`](../../benchmarking/results/comparison/DECISION.md) | Bakeoff decision memo |
| [`../../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md`](../../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md) | Lean limits (primary path) |

---

*Limitations & future work for federated-pipeline. Motadata-aligned (2026-07-13).*
