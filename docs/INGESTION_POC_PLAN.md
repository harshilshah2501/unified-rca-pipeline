# Ingestion PoC Plan — Near Product-Match

**Status:** Active plan (RCA eval path closed; ingestion is the critical path)  
**Progress (2026-07-24):** ObserveOps ingest + Motadata L1 (+ Bucket-3 `motadata-deps-001`) + F1/N4/N5 + cost_report + Samples. **LIVE prep Done** — [`LIVE_INGEST_RUNBOOK.md`](./LIVE_INGEST_RUNBOOK.md); **execute** collector smoke next week → then `CHANGE`.
**Owner audience:** engineering + infra provisioning  
**Related:** [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) · [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) · [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) · [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) · [`ROADMAP.md`](./ROADMAP.md) · [`CAPACITY.md`](../federated-pipeline/docs/CAPACITY.md)

---

## 1. Executive summary

**RCA is eval-complete** for ObserveOps classic infra (Lean primary per ADR-001; fair shared-detect bakeoff `bakeoff-parity-001`). The next work is **ingestion**: replace frozen/synthetic bundles with a real collect → detect → artifact pipeline, then point Lean (and optionally Federated) at **live-produced** `A-TOPO` / `A-ANOM` / `A-SEED`.

This plan defines three milestones (M1–M3), hardware tiers (A–C), week-by-week checklist, and exit gates. It does **not** target 1B EPS or full hyperscaler sizing.

```
Collect → Detect → Artifacts → RCA (Lean primary)
                ↑
         Vector + builders (this PoC)
```

---

## 2. What “closed” means for RCA vs ingestion

| Layer | Closed? | Evidence |
|-------|---------|----------|
| Lean vs Federated accuracy (UC-1..5) | Yes | 5/5 both; `bakeoff-parity-001` |
| Fair pipeline (shared detect) | Yes | [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md) |
| Lean packaging (CLI / HTTP / systemd) | Yes | ROADMAP **Ship** complete |
| **Normalized `ingest.v1` streams** | **Partial** | UC replay + Motadata smoke + F1 sinks + N4/N5 writers **Done**; live collectors still open |
| **Real ingested front door** (Vector → detect → bundles/stores) | **Partial** | N3–N5 smoke **Done** on replay; **LIVE prep Done** ([`LIVE_INGEST_RUNBOOK.md`](./LIVE_INGEST_RUNBOOK.md)); execute lab smoke next week; real Panorama (D4) still open |
| **Real Panorama detect** | **No** | Needs gray-failure corpus (D4); M2 |
| Federated repro 40% | Open | Not blocking Lean-primary track |

**Handoff rule:** No further RCA algorithm work unless ingested artifacts regress accuracy or a new corpus is added.

---

## 3. Milestones

### M1 — Lab ingest MVP (must-have)

**Goal:** One shared Vector path produces Lean-shaped bundles from **replay**, not hand-edited JSON.

| Deliverable | Maps to design |
|-------------|----------------|
| UC JSONL → Vector (`vector.lean-only.toml`) | INGESTION §D1 |
| `ingest.v1` + CI bind | INGESTION §5.2 |
| `lean_bundle_writer` (post-Vector) | INGESTION §5.3 |
| Stream-fed shared threshold detect | [`ingestion-poc/detect/`](../ingestion-poc/detect/) |
| Lean `diagnose` on writer output | Parity harness |
| UC-1..5 ingested PASS vs GT | New gate |

**Exit gate:** All five UCs root-CI match when RCA reads **ingested** bundles only (frozen files not copied for anomalies/seed).

**Hardware:** Tier A.

**Duration:** ~4–6 weeks.

---

### M2 — Product-shaped ingest (headline PoC)

**Goal:** Live collectors, real topology refresh, **real Panorama** on Federated detect profile, measured cost envelope.

| Deliverable | Exit criteria |
|-------------|---------------|
| Topology crawler stub → `A-TOPO` | Fresh topo snapshot ≤ 15 min stale in lab |
| Live smoke (syslog / Prometheus / OT) | ≥1 non-replay source into Vector |
| Real Panorama (`federated-pipeline/panorama/`) | `detect_source=panorama`; observer reports in lab |
| Cost harness L0 vs F1 | `cost_report.md`: EPS, CPU, GB/day, p99 ingest |
| End-to-end fault drill | Inject → detect → Lean RCA → correct root |

**Exit gate:** Documented **Total Cost to Diagnose** = `C_detect + C_collect + C_store + C_rca` on Tier B hardware at **≥50K EPS sustained** (stretch **100K EPS**).

**Hardware:** Tier B.

**Duration:** ~6–8 weeks after M1.

---

### M3 — Federated ingest track (optional)

**Goal:** F1 dual-sink, Dragonfly speed tier, Nezha key materialization; Federated RCA on ingested stores (not simulated).

Only pursue if product needs Murphy/Nezha on live streams or microservice track is prioritized.

**Hardware:** Tier C.

**Duration:** ~8+ weeks after M2.

---

## 3b. When Federated is justified over Lean

For **high-volume microservice architectures**, Federated is generally more justified **when the problem requires continuous path-level reasoning**, not just incident-local topology walkbacks.

| Environment / need | Prefer Lean | Prefer Federated |
|--------------------|------------|------------------|
| Classic infra chain (host/VM/network/storage) | Yes | Rarely needed |
| High-cardinality traces + noisy retries + gray failures | Limited | Yes |
| Need request-path pattern drift scoring (Nezha-style) | No | Yes |
| Need observer-majority anomaly detect (Panorama-style LOS) | No | Yes |
| Requirement is deterministic, low-ops, cheaper RCA | Yes | Usually no |
| Requirement is deeper microservice causality despite higher ops/cost | Sometimes | Yes |

### Practical decision rule

Choose **Federated** for product path if most of these are true:

1. Sustained service graph churn (frequent deploys, topology changes, ephemeral pods).
2. Trace-heavy workload where symptoms depend on execution-path variants.
3. Frequent gray failures where threshold alerts are insufficient.
4. You can accept higher `C_detect + C_store + C_ops` for better microservice depth.

Otherwise choose **Lean-first** with a lighter ingest front door and escalate to Federated only for scoped domains.

### Data-backed promotion gate (no heuristics-only claims)

Federated is promoted from optional to justified only if the PoC produces **measured** wins on a microservice-focused validation set.

| Gate | Metric | Promote Federated when… |
|------|--------|--------------------------|
| G1 | Root-CI / signature accuracy | Federated exceeds Lean by **>= 8 percentage points** on microservice incidents |
| G2 | Gray-failure capture | Federated catches **>= 20%** more gray-failure incidents than Lean |
| G3 | False positives | Federated does not exceed Lean FP rate by more than **+3 points** |
| G4 | Reproducibility floor | Federated reproducibility reaches **>= 85%** on N=20 reruns |
| G5 | Cost efficiency | Incremental cost per correctly diagnosed incident is within approved budget cap |
| G6 | Latency SLO | System p95 diagnose latency stays within product SLO under target EPS |

All six gates are evaluated on the **same incidents and same input stream**; if G1/G2 fail, keep Lean-primary and Federated remains optional.

### Required PoC dataset for this claim

To avoid “classic infra bias,” M2/M3 must include a microservice-heavy suite (replay or live-captured) containing at least:

1. Retry storms / partial dependency gray failures.
2. Path-specific regressions (same service, different route behavior).
3. High-churn deploy windows (pod/service identity churn).
4. Cross-service contention where earliest-alert heuristics are misleading.

Deliverable: `federated_justification_report.md` with per-incident scoreboard and aggregate pass/fail on G1–G6.  
Template: [`FEDERATED_JUSTIFICATION_REPORT.md`](./FEDERATED_JUSTIFICATION_REPORT.md).  
Sample ingest contract: [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md).

### This PoC’s policy

- **M1/M2 default:** Lean-primary path is the release gate.
- **M3 trigger:** start Federated-heavy ingest only if M2 data shows Lean misses required microservice cases or product requirements explicitly demand Nezha/Panorama depth.

---

## 4. Hardware tiers

### Tier A — Start now (M1)

| Resource | Spec | Rationale |
|----------|------|-----------|
| Host | **8 vCPU, 32 GB RAM, 500 GB SSD** | Vector + builders + Lean RCA + replay at 10K–50K EPS |
| OS | Linux 22.04+ (WSL OK for dev only) | |
| Network | 1 Gbps | Non-issue |
| Stack | Docker Compose: Vector, artifact volume, optional Redis | No cluster |

**Not for headline EPS claims** — correctness and pipeline wiring only.

---

### Tier B — Cost PoC target (M2)

Aligns with [`CAPACITY.md`](../federated-pipeline/docs/CAPACITY.md) PoC row (~100K EPS).

| Resource | Spec | Rationale |
|----------|------|-----------|
| Benchmark host | **16–32 vCPU, 64 GB RAM, 1 TB NVMe** | Vector @ 100K EPS + detect + writers |
| Dragonfly | **8 vCPU, 32 GB** (co-located or dedicated) | Hot window ~6 GB @ 100K×200B×300s |
| Structural / topo | **8 GB** Postgres or in-process | `A-TOPO` + anomaly index |
| Panorama service | **4 vCPU, 8 GB** | Real multi-observer detect |
| Network | 1 Gbps | |

**Re-benchmark:** Run `phase0_dragonfly.py` on Tier B; replace laptop ~21K EPS floor.

**Success metrics:**

| Metric | Target |
|--------|--------|
| Sustained ingest EPS | ≥50K (stretch 100K) |
| p99 Vector → artifact | < 500 ms |
| CI-bind miss rate | < 1% |
| Ingest cost table | $/1M events, GB/day documented |

---

### Tier C — Federated-heavy (M3 only)

| Resource | Spec |
|----------|------|
| 2–3 nodes × (16 vCPU, 64 GB) | Vector fan-out + Dragonfly cluster + orchestrator |
| Target | 100K–200K EPS with F1 dual-sink |

**Explicit non-goal:** 1B EPS fleet sizing (ROADMAP **Later · Scale**).

---

### Tier B+ — Your `pro6000-server` (recommended lab host)

**Validated profile (2026-07-20):**

| Resource | Measured | Tier B requirement | Verdict |
|----------|----------|-------------------|---------|
| CPU | **16 cores** | 16–32 | Meets minimum |
| RAM | **125 GiB** (~121 GiB available) | 64 GiB | **Exceeds** — Dragonfly co-located OK |
| GPU | RTX PRO 6000 96 GiB | Not required M1–M2 | Idle for ingest PoC |
| Swap | **0** | Optional safety | Consider 8–16 GiB swap for OOM spikes |

Use **`pro6000-server` as a single-box lab for M1 + M2** — no separate cloud VM or second Dragonfly host needed.

**Recommended process layout (one machine):**

```
pro6000-server
├── Vector          (4–6 cores effective)
├── lean_bundle_writer + threshold_detect  (1–2 cores)
├── Dragonfly       (4–8 cores, ~8–16 GiB RAM cap for PoC)
├── Panorama        (M2, 2–4 cores)
├── Lean RCA        (on demand, negligible)
└── load generator  (replay JSONL for EPS tests)
```

**Capacity expectation on this host:** **50K–100K EPS** ingest replay is realistic; run [`ingestion-poc/lab/run_lab_eps.py`](../ingestion-poc/lab/run_lab_eps.py) here to set the measured ceiling (expect well above laptop ~24K EPS).

```bash
# On pro6000-server
DF_PROACTOR_THREADS=8 python3 ingestion-poc/lab/run_lab_eps.py --seconds 30 --workers 16
# → benchmarking/capacity/lab/<run_id>/LAB_REPORT.md — paste phase0 into CAPACITY.md
```

If **`pro6000-server`** has **≥16 CPU cores and ≥64 GB system RAM** (typical for an RTX PRO 6000 workstation), use it as **both Tier A and Tier B** — no separate cloud VM required for M1–M2.

| Component | Role on pro6000 | Notes |
|-----------|-----------------|-------|
| **CPU + RAM** | Vector, detect, Murphy, Dragonfly, Lean RCA | **Primary constraint** for M1–M2 |
| **NVMe / SSD** | Replay JSONL, artifact bundles, Dragonfly persistence | Ensure ≥500 GB free |
| **NVIDIA RTX PRO 6000 (96 GB)** | **Not required** for M1–M2 as designed | See GPU section below |

Run headline EPS benchmarks **on this host**, not WSL laptop (~21K EPS floor).

#### GPU (RTX PRO 6000) — when it helps vs when it does not

**Current repo has no CUDA/GPU code paths** (Vector, threshold detect, Panorama, Murphy Gibbs, Lean walk are all CPU).

| Milestone | GPU useful? | Why |
|-----------|-------------|-----|
| **M1** (Vector → bundle writer) | **No** | Stream parse, CI bind, file I/O — CPU |
| **M2** (live ingest + Panorama + cost PoC) | **No** for planned scope | Threshold + observer voting + Dragonfly Lua |
| **M3** (F1 dual-sink / Nezha at scale) | **Maybe later** | Graph/pattern ops at high EPS *if* we add GPU kernels — **not implemented** |
| **Post-PoC / product** | **Yes, optional** | ML anomaly detect, log embeddings, very large MRF inference |

**Practical guidance:**

- **Do not block M1/M2 on GPU setup** — install NVIDIA driver (you have 590.48 ✓); skip CUDA/toolkit until a concrete GPU workload exists.
- **Use the GPU box for CPU/RAM headroom** — one machine runs Vector + Dragonfly + Panorama + RCA for end-to-end drills.
- **Re-run** `phase0_dragonfly.py` and M2 cost harness **on pro6000** to replace laptop numbers.
- **Optional experiment (M3+ only):** GPU-accelerated Murphy Gibbs or Nezha pattern scoring on large event graphs — research spike, not PoC gate.

```bash
# Quick host check on pro6000-server (run once)
nproc && free -h && df -h && nvidia-smi
```

---

## 5. Week-by-week checklist

### Weeks 1–2 — Foundation (M1 start)

| Week | Tasks | Owner output |
|------|-------|--------------|
| W1 | Provision Tier A; Docker Compose for Vector | `ingestion-poc/compose/` |
| W1 | Corpus metrics → JSONL replay generator (UC-1..5) | **Done** — `ingestion-poc/replay/` → `datasets/ingest_samples/observeops-replay/` |
| W1 | Motadata → `ingest.v1` adapter (smoke) | **Done** — `ingestion-poc/adapters/motadata_to_ingest_v1.py` → `motadata-ingest/` (local dumps gitignored) |
| W2 | Vector F1/L0: file source → remap / detect / sink | **Done (smoke)** — `ingestion-poc/pipeline/f1_run.py` + `vector.f1-smoke.toml` (Python fan-out default; `--vector` Docker) |
| W2 | CI bind lookup from frozen `topology.json` (UC); Motadata bind | **Done** — UC topology in F1 out; Motadata `ci_bind.json` + inventory topology |

### Weeks 3–4 — Bundle writer + detect (M1 core)

| Week | Tasks | Owner output |
|------|-------|--------------|
| W3 | `lean_bundle_writer`: stream → `anomalies.json`, `symptom_seed.json` | **Done** — `ingestion-poc/builders/lean_bundle_writer.py` |
| W3 | Integrate `threshold_detect` on writer path OR inline in Vector | **Done** — F1 + `detect_meta.json` |
| W4 | UC-1 end-to-end: replay → Vector → writer → Lean diagnose | **Done** — `n45_chain.py` UC-1..5 root match |
| W4 | `--ingested-corpus` flag in bakeoff runners | Still open (harness) |

### Weeks 5–6 — M1 exit (all UCs)

| Week | Tasks | Owner output |
|------|-------|--------------|
| W5 | Replay JSONL for UC-2..UC-5; extend writer | 5/5 ingested bundles |
| W5 | Ingested vs frozen diff report | `ingested_parity_report.md` |
| W6 | M1 demo + sign-off | RCA reads ingested only; GT 5/5 |

### Weeks 7–10 — M2 product shape

| Week | Tasks | Owner output |
|------|-------|--------------|
| W7 | Topology crawler stub (static export / cron) | `A-TOPO` refresh job |
| W8 | Live collector smoke (choose one: syslog or Prometheus) | non-replay events in Vector |
| W9 | Panorama service wired; Federated profile with real detect | hop-1 `panorama` on lab |
| W10 | Cost harness: L0 vs F1 replay; Tier B benchmark | **Done (pro6000)** — `benchmarking/results/costing/cost-pro6000-20260721Tfinal/` |

### Weeks 11+ — M3 (if approved)

| Week | Tasks |
|------|-------|
| W11–12 | F1 dual-sink; speed-tier builder → Dragonfly |
| W13–14 | Federated RCA on ingested stores; optional Nezha keys |

---

## 6. Repository mapping

**Build order (frozen corpus):** Federated ingest path **first** (F1: Vector → Dragonfly speed tier + structural feed), then Lean `lean_bundle_writer` from the **same** `ingest.v1` stream. See [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md).

| Path | Role |
|------|------|
| [`ingestion-poc/vector/`](../ingestion-poc/vector/) | Vector configs (L0 / F1 skeleton) |
| [`ingestion-poc/detect/`](../ingestion-poc/detect/) | Shared threshold detect (M1); Panorama later (M2) |
| [`ingestion-poc/replay/`](../ingestion-poc/replay/) | **Done** — ObserveOps → `ingest.v1` |
| [`ingestion-poc/pipeline/`](../ingestion-poc/pipeline/) | **Done (N3)** — F1 smoke runner |
| [`ingestion-poc/builders/`](../ingestion-poc/builders/) | **Done (N4–N5)** — Federated store + Lean bundle writers + `n45_chain.py` |
| [`ingestion-poc/adapters/`](../ingestion-poc/adapters/) | **Done (smoke)** — Motadata → `ingest.v1` |
| [`ingestion-poc/compose/`](../ingestion-poc/compose/) | **Partial** — `docker-compose.f1.yml` |
| [`benchmarking/benchmark/parity.py`](../benchmarking/benchmark/parity.py) | Shared detect helpers; extend for ingested corpus |
| [`datasets/observeops/`](../datasets/observeops/) | GT + reference bundles (eval only after M1) |
| [`datasets/ingest_samples/`](../datasets/ingest_samples/) | Normalized streams: `observeops-replay/`, `motadata-ingest/`; raw Motadata in `jsonl_resolved/` (local) |

Design phases D1–D5 from [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md):

| Design phase | This plan |
|--------------|-----------|
| D1 JSONL replay → lean bundle writer | M1 W2–W4 |
| D2 Cost harness L0 vs F1 | M2 W10 |
| D3 Topology crawler + CI bind | M1 W2 + M2 W7 |
| D4 Federated speed-tier builder | M3 |
| D5 HA / auth / DLQ product hardening | Post-PoC |

---

## 7. Cost model (what we will measure)

```
Total ≈ C_collect + C_detect + C_normalize + C_store + C_query_feed + C_ops + C_rca_runtime
```

| Bucket | M1 | M2 |
|--------|----|----|
| C_collect | Replay only | + live smoke |
| C_detect | Shared threshold (timed) | + real Panorama (Federated profile) |
| C_store | File artifacts | + hot index / Dragonfly window |
| C_rca_runtime | Already measured (`bakeoff-parity-001`) | Same |

Headline compare: **L0 (Lean-only sinks)** vs **F1 (dual-sink)** on **identical replay bytes**.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Ingested anomalies ≠ frozen GT | Golden UC-1 first; diff tool; freeze expected detect outputs per UC |
| Laptop EPS misleading | Tier B re-benchmark before publishing cost tables |
| Scope creep (1B EPS, full HA) | Explicit non-goals in §9 |
| Panorama lab complexity | M2 only; Lean path stays threshold detect |
| Federated store adapter drift | M3 optional; Lean-primary PoC does not require Nezha tier |

---

## 9. Non-goals (this PoC)

- 1B EPS production sizing
- DeathStarBench / microservice corpus as ObserveOps gate
- Full HA multi-region Vector
- Automated remediation / runbook execution
- Replacing RCA accuracy bakeoff (already done)

---

## 10. Immediate next three actions

Already done: ObserveOps replay; Motadata adapter; F1 + N4/N5; D1–D3; Motadata L1 (+ Bucket-3 `motadata-deps-001` authored); inventory; pro6000 cost/soak; Samples; **LIVE runbook + live Vector configs**.

1. **LIVE — execute** syslog or Prometheus → Vector → F1 ([`LIVE_INGEST_RUNBOOK.md`](./LIVE_INGEST_RUNBOOK.md)) — scheduled next week.  
2. **CHANGE — real change feed** into D2 `change_near_onset`.  
3. **Samples confirm** `motadata-deps-001` (+ optional OO alert scrub per [`OO_UC_FAIRNESS_CHECKLIST.md`](./OO_UC_FAIRNESS_CHECKLIST.md)).

Park D4/I2 until gray-failure / path-baseline data exists. See [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3.

---

## 11. Sign-off criteria (PoC complete)

| Criterion | Milestone |
|-----------|-----------|
| Lean 5/5 on ingested bundles (no frozen anomalies/seed) | M1 |
| Detect + ingest latency recorded in `run_meta` | M1 |
| Live source + real Panorama in lab | M2 |
| `cost_report.md` on Tier B at ≥50K EPS | M2 |
| F1 dual-sink + Federated on ingested stores | M3 (optional) |

---

## 12. References

- Workflow + next actions: [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md)
- Vector design: [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md)
- Data format / converters: [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md)
- Fair RCA compare: [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md)
- Cost structure: [`RCA-learning-cheatsheet.md`](../RCA-learning-cheatsheet.md) §1c–§3
- Capacity: [`federated-pipeline/docs/CAPACITY.md`](../federated-pipeline/docs/CAPACITY.md)
- Canonical RCA scoreboard: [`benchmarking/results/comparison/RUN_IDS.md`](../benchmarking/results/comparison/RUN_IDS.md)
