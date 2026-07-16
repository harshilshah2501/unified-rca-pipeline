# Unified RCA — End-to-End Roadmap

**Evaluation corpus (only):** [`rca-use-cases-only.md`](./rca-use-cases-only.md) → frozen bundles in `../datasets/observeops/` (UC-1..UC-5).

**Goal:** decide which pipeline (federated vs lean) wins on ObserveOps layers, then harden the winner toward production readiness.

**ObserveOps critical path status:** **Complete** (Phases A → B → D). Lean is the primary evaluation engine (ADR-001; not a finalized product commitment); packaged as CLI/HTTP API. Optional later: B5 / C* / E*.

```
                    ┌─────────────────────────────────────┐
   Spec             │  docs/rca-use-cases-only.md         │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
   Corpus           │  datasets/observeops/  (frozen)      │
                    └─────────────────┬───────────────────┘
                                      ▼
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   ┌─────────────────────┐                         ┌─────────────────────┐
   │ federated-pipeline  │                         │   lean-pipeline     │
   │ Pano→Murphy→Nezha   │                         │ BFS+temporal+CARE   │
   │ (optional / hybrid) │                         │ + Tier3 causal ✅   │
   └──────────┬──────────┘                         └──────────┬──────────┘
              └───────────────────────┬───────────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
   Bakeoff          │  benchmarking/results/comparison/   │
   Decision         │  primary evaluation engine (ADR-001) ✅ │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
   Production PoC   │  lean_rca CLI + HTTP :8780 ✅        │
                    └─────────────────────────────────────┘
```

Shared objective docs: [`README.md`](./README.md) (`docs/`). Pipeline-specific docs stay under `federated-pipeline/docs/` and `lean-pipeline/docs/`.

---

## Where we are (done)

| Milestone | Status | Evidence |
|-----------|--------|----------|
| M0 Repo layout | **Done** | `federated-pipeline/`, `lean-pipeline/`, `datasets/`, `benchmarking/`; algos + deploy/scripts under federated; **common docs in `docs/`** |
| M1 Corpus B frozen | **Done** | UC-1..UC-5 from `rca-use-cases-only.md`; schema + manifest validation |
| M2 Federated PoC | **Done** | Orchestrator 6-hop; crawler + hipster demos; ObserveOps adapter |
| M3 Lean ObserveOps engine | **Done** | BFS + info-gain + temporal + CARE; Tier 3 causal on UC-1/UC-3; hardened signatures |
| M4 Same-corpus bakeoff | **Done** | Both engines 5/5 accuracy on ObserveOps; comparison artifacts exist |
| M5 Phase 0 EPS (laptop) | **Partial** | ~21K EPS on 2-core WSL Dragonfly; **not** 64-core production estimate |
| **M6 Phase A bakeoff close** | **Done** | A1 fusion fix; A2 four-axis compare; `bakeoff-phase-a-001`; **primary evaluation engine (ADR-001)** — [`DECISION.md`](../benchmarking/results/comparison/DECISION.md) |
| **M7 Phase B lean PRD depth** | **Done** | Tiers 1/2/3 + CARE→causal; signatures; search vs BFS efficiency; `bakeoff-phase-b-002` (latest) |
| **M8 Phase D packaging** | **Done** | ADR-001; `lean_rca` CLI/HTTP; SRE report fields; systemd `lean-rca.service` |
| **M9 Docs consolidation** | **Done** | Common objective docs in [`docs/`](./README.md) (use-cases, roadmap, ADR, Lean PRD + Simple Guide); pipeline-specific docs remain in-tree |

---

## Next action items → roadmap phases

### Phase A — Close the ObserveOps bakeoff (Corpus B) — *COMPLETE*

| # | Action item | Status | Exit criteria |
|---|-------------|--------|---------------|
| A1 | Fix federated fusion gaps (UC-2/UC-3 Murphy posterior) | **Done** | Murphy posteriors high; lean-heuristic fallback gone |
| A2 | Enrich compare.py with four-axis + reproducibility | **Done** | Four-axis scoreboard in COMPARISON.md / comparison.json |
| A3 | Re-run matched bakeoff after A1–A2 | **Done** | `bakeoff-phase-a-001` |
| A4 | Document verdict: federated vs lean on ObserveOps | **Done** | [`DECISION.md`](../benchmarking/results/comparison/DECISION.md) — **primary evaluation engine (ADR-001)** |

---

### Phase B — Lean to PRD depth (still on ObserveOps) — *COMPLETE*

| # | Action item | Status | Exit criteria |
|---|-------------|--------|---------------|
| B1 | Correct evidentiary tier labeling (1 / 2 / 3) | **Done** | UC-1/UC-3 → Tier 3; UC-2/4/5 → Tier 1 |
| B2 | Tier 3 scoped causal check (only when CARE fires) | **Done** | `lean/causal.py`; `causal_verified` + `causal_log` |
| B3 | Harden signatures vs `rca-use-cases-only.md` | **Done** | AND-condition matchers + negative tests |
| B4 | Observation-efficiency vs naive BFS | **Done** | `obs_to_convergence` / `naive_bfs_expansions` / ratio in verdict + compare |
| B5 | Continuous causal memory (§2.8) | Deferred | Optional; after ObserveOps packaging |

**Bakeoff:** `bakeoff-phase-b-002` — [`COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md).

**Out of scope for classic ObserveOps path:** DeathStarBench / TrainTicket Corpus A — optional only if paper-style algorithm proof beyond ObserveOps is needed.

---

### Phase C — Federated production path (ingest + stores) — *optional / deferred*

Only if a microservice / code-path eval track is prioritized (not ObserveOps).

| # | Action item | Maps to | Exit criteria |
|---|-------------|---------|---------------|
| C1 | NATS → Rust (or retained Python) normalizer dual-stream | FR-1a–d | Live write path: events → speed tier; metrics/topology → structural |
| C2 | Real Nezha `rca_data` path stable (`--live-nezha`) | G4 / FR-2e | No silent Drain3 fallback on hipster reference |
| C3 | Resolve OD-1..OD-3 (trigger, baseline, fusion) | Open decisions | Written choices in ORCHESTRATOR.md |
| C4 | Phase 0 on server-class host (64+ cores) | CAPACITY.md | Replace 200K–800K estimate with measured E_node |
| C5 | PoC 100K EPS sustained target | CAPACITY PoC | Single/small Dragonfly cluster meets p99 SLO |

---

### Phase D — Decision & packaging — *COMPLETE*

| # | Action item | Status | Exit criteria |
|---|-------------|--------|---------------|
| D1 | Choose primary engine / hybrid | **Done** | [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) |
| D2 | Single RCA API + CLI | **Done** | `python -m lean_rca diagnose\|serve` |
| D3 | SRE report (chain, blast radius, remediation) | **Done** | UC (e) fields on every verdict |
| D4 | Deployable service unit | **Done** | `lean-pipeline/deploy/systemd/lean-rca.service` |

**Try it** (from repo root):
```bash
PYTHONPATH=lean-pipeline:. .venv/bin/python -m lean_rca diagnose UC-1 --format report
./lean-pipeline/scripts/serve-rca.sh   # :8780  → GET /health, /v1/diagnose/UC-1
```
See [`../lean-pipeline/deploy/README.md`](../lean-pipeline/deploy/README.md).

---

### Phase E — Scale vision — *explicitly later / not PoC-blocking*

| # | Action item | Maps to | Exit criteria |
|---|-------------|---------|---------------|
| E1 | Validate event size (~200B) + encoding | CAPACITY production | Measured bytes/event |
| E2 | Structural tier at Vortex/DashMap scale | Architecture Tier 2 | Capacity model with real entity counts |
| E3 | 1B EPS fleet sizing from measured E_node only | CAPACITY production | Node-count formula with measured inputs |

---

## Suggested sequence (critical path)

```
A1–A4 ObserveOps bakeoff close          ✅ DONE → primary evaluation engine per ADR-001
B1–B4 Lean PRD depth on same corpus     ✅ DONE
D1–D4 Package lean RCA API/report       ✅ DONE
M9  Common docs/ consolidation          ✅ DONE
        │
        └─► optional next:
              B5 causal memory
              C* federated ingest (microservice track only)
              E* capacity / 1B EPS vision
```

---

## Non-goals (keep out of the ObserveOps PoC path)

- Replacing ObserveOps eval with Nezha Online Boutique / TrainTicket accuracy claims
- DeathStarBench harness as an ObserveOps gate
- 1B EPS deployment work before server-class Phase 0 measurement
- Automated remediation / runbook execution

---

## Quick pointers

| Need | Where |
|------|-------|
| Docs home | [`README.md`](./README.md) |
| End-to-end PoC briefing | [`POC_BRIEFING.md`](./POC_BRIEFING.md) |
| Use-case definitions | [`rca-use-cases-only.md`](./rca-use-cases-only.md) |
| Lean PRD | [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) (**canonical**) · [`.pdf`](./Lean_RCA_PRD.pdf) |
| Lean Simple Guide | [`Lean_RCA_Simple_Guide.md`](./Lean_RCA_Simple_Guide.md) (**canonical**) · [`.pdf`](./Lean_RCA_Simple_Guide.pdf) |
| Lean pipeline architecture | [`../lean-pipeline/docs/ARCHITECTURE.md`](../lean-pipeline/docs/ARCHITECTURE.md) · [limitations](../lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md) |
| Primary-engine ADR | [`ADR-001-lean-primary-engine.md`](./ADR-001-lean-primary-engine.md) |
| Federated architecture | [`../federated-pipeline/docs/ARCHITECTURE.md`](../federated-pipeline/docs/ARCHITECTURE.md) · [limitations](../federated-pipeline/docs/LIMITATIONS_AND_FUTURE.md) |
| Federated status | [`../federated-pipeline/docs/REQUIREMENTS.md`](../federated-pipeline/docs/REQUIREMENTS.md) |
| Capacity | [`../federated-pipeline/docs/CAPACITY.md`](../federated-pipeline/docs/CAPACITY.md) |
| Bakeoff how-to | [`../benchmarking/README.md`](../benchmarking/README.md) |
| Path helper | [`../repo_paths.py`](../repo_paths.py) |
