> **Study notes — not a scoreboard.** Canonical numbers: `benchmarking/results/comparison/` and `docs/`.

# RCA Learning Cheatsheet + Ingestion Cost PoC Plan

**Doc map:** [`docs/NAVIGATION.md`](docs/NAVIGATION.md)

## 1) Lean vs Federated (quick revision)

| Dimension | Lean pipeline | Federated pipeline |
|---|---|---|
| Primary role in this repo | Primary evaluation engine on ObserveOps corpus (ADR-001; not finalized commitment) | Comparator / optional hybrid track |
| Reasoning shape | Single coherent walk: typed graph + temporal + info-gain + CARE + scoped Tier-3 check | Multi-stage orchestration: Panorama -> Murphy -> optional Nezha -> fusion |
| Reproducibility posture | Strong / deterministic-oriented on current corpus | More variance-prone depending on sampling/fusion path |
| Verifiability style | Explicit evidentiary tiers + CARE flags + clear trail | Rich, but can be harder to narrate under pressure |
| Ingestion dependency (default path) | Lower for classic infra use-cases | Higher in full vision (dual-tier + orchestration + optional micro path) |
| Best-fit workload | Classic infra tickets needing stable/auditable RCA | Cases where deeper microservice/path/causal depth is worth complexity |
| Current PoC ingestion | Frozen bundles for bakeoff; **`ingest.v1`** replay + Motadata smoke for ingest track | Same shared streams when Vector wired; Federated still adapterized on ObserveOps eval |

Tag reminder for learning notes:
- `[Implemented]` repo-verified behavior
- `[Simulated]` PoC adapter/bundle stand-in
- `[Aspirational]` production-scale vision

---

## 1b) Data structures & algorithms (side-by-side)

### Algorithms

| Concern | Lean | Federated |
|---------|------|-----------|
| Detection / trigger | Symptom seed + crossed anomalies (from bundle) | **Panorama** — observer / majority-style unhealthy flag `[Simulated]` on ObserveOps |
| Macro localization | Best-first upstream walk + temporal + **ObserveOps rules** | **Murphy** — MRF + Gibbs posteriors over entities `[Implemented]` |
| Micro / path refinement | Structured `events.json` cite-in-evidence (not Drain mining) | **Nezha** — pattern / path drift scoring `[Implemented]` (light on classic infra) |
| Ambiguity handling | **CARE** when onsets within Δt (~10s) | θ_murphy gate; weak posterior → lean-rule / earliest-onset fallback |
| Causal claim | Scoped `verify_care_root` → Tier 3 only | Murphy partial CV (costly if global) |
| Fusion / resolve | Single engine + rule registry + signature | Orchestrator `fuse_verdict` (weights e.g. 0.2/0.4/0.4) |
| Search shape | **Best-first** (not FIFO BFS); naive BFS = efficiency baseline | Orchestrated hops 1→6, not one graph walk |
| Determinism | Designed bit-stable | Gibbs / path variance → ~40% repro on corpus |

### Data structures / schemas

| Structure | Lean | Federated |
|-----------|------|-----------|
| Topology | Typed **InvocationGraph** from `topology.json` (NetworkPort, HypervisorHost, Datastore, VM, GuestOS, Service) | Structural / knowledge-graph style edges + LOS/metrics in PoC store; production Vortex/DashMap `[Aspirational]` |
| Anomalies / metrics | `anomalies.json` crossings + onset times | SimulatedMetricStore / metric edges for Murphy `[Simulated]` on bakeoff |
| Events | Optional `events.json` (UC-2/4/3b) | Speed-tier event graph (`tg:` / `pc:` keys) for Nezha `[Simulated]` / `[Aspirational]` at scale |
| Hop payloads | Internal engine state (not multi-hop schemas) | `DetectionFlag` → `MurphyRequest` → Nezha request → fused verdict `[Implemented]` in orchestrator |
| Verdict | `root_ci`, `signature`, `evidentiary_tier` 1/2/3, `fallback_fired`, evidence trail, CARE/causal fields | `root_ci` / fusion fields, hop logs; `fallback_fired` = lean-rule rescue (≠ lean Tier ladder) |
| Signal / rules registry | `signals.yaml` + shared_upstream / upstream_healthy / contributors | Fusion + ObserveOps helpers on weak Murphy |
| Evidence narration | Lean Tier 1/2/3 (lean-only) | Fusion path vs fallback path |

### PoC input files (both engines on ObserveOps)

| File | Lean | Federated bakeoff |
|------|------|-------------------|
| `topology.json` | Required | Required (via adapter) |
| `anomalies.json` | Required | Required |
| `symptom_seed.json` | Required | Required |
| `events.json` | Required on UC-2/4/3b | Used where adapter maps it |
| `ground_truth.json` | Eval only | Eval only |
| Live collectors / NATS / Dragonfly fleet | Not required for bakeoff | Stub / optional Phase 0; production ingest deferred |

---

## 1c) Ingestion pipeline cost breakdown

**Remember:** bakeoff RCA still uses **frozen** ObserveOps bundles. Ingest PoC has **normalized `ingest.v1`** (UC replay + Motadata smoke); Vector → writers still ahead — [`docs/INGESTION_POC_PLAN.md`](docs/INGESTION_POC_PLAN.md). Numbers below are a **cost structure** for planning — not measured production invoices.

### Cost equation

```
Total ops cost ≈ C_collect + C_detect + C_normalize + C_store + C_query_feed + C_ops
                 + C_rca_runtime   (separate — already bakeoff-comparable)
```

**Detection (`C_detect`) is mandatory in product** — Lean does not include Panorama. Fair bakeoff now runs a **shared threshold detector** before both engines ([`docs/PIPELINE_PARITY.md`](docs/PIPELINE_PARITY.md)). Continuous detection often costs more than sparse RCA calls; real ingest + real Panorama come later. See also [`docs/INGESTION_PIPELINE_VECTOR.md`](docs/INGESTION_PIPELINE_VECTOR.md) §1b.

| Cost bucket | What it pays for | Lean (classic infra default) | Federated (full vision) |
|-------------|------------------|------------------------------|-------------------------|
| **C_collect** | Agents, SNMP/vCenter/APM/trace exporters | Inventory + metric/event collectors for typed CIs — **moderate** | Same **plus** high-velocity traces/logs for Nezha — **high** |
| **C_detect** | Mark crossed anomalies + raise symptom seeds | Thresholds / alerts / Vector detect — **moderate** (required) | Panorama-class observers **or** shared front door — **moderate → high** |
| **C_normalize** | Schema mapping, identity joins, clock skew | One CI inventory + anomaly/event schema — **lower** | Multi-schema hop translation (Panorama/Murphy/Nezha) — **higher** |
| **C_store** | Retention, hot/cold, indexing | Snapshot/graph + short anomaly windows — **lower** | Dual tier: structural KG + speed event store — **much higher** |
| **C_query_feed** | Serving RCA-ready windows to the engine | Load bundle / incident slice — **cheap per ticket** | Slice KG + open event windows; Gibbs sampling load — **expensive per ticket** |
| **C_ops** | On-call, upgrades, backpressure, TTL, HA | Fewer moving parts — **lower** | Orchestrator + 3 algos + 2 stores — **higher** |
| **C_rca_runtime** | Diagnose CPU after data is ready | Best-first walk + rules (+ rare CARE/Tier3) — **low** | Murphy Gibbs + optional Nezha + fusion — **medium–high** |

### Relative cost sketch (classic infra vs microservice-heavy)

| Workload | Lean ingest burden | Federated ingest burden | Notes |
|----------|--------------------|-------------------------|-------|
| Classic infra steady (ObserveOps-like) | ★★☆ | ★★★★★ | Federated dual-tier mostly unused value |
| Burst incident windows | ★★☆ | ★★★★ | Speed tier spikes dominate federated |
| Microservice gray-failure + code-path | ★★★ (may be underpowered) | ★★★★★ | Federated may justify cost |
| This PoC (frozen bundles) | ★ (simulated) | ★ (simulated) | **Not** a real ingest cost bakeoff yet |

### What we already know vs what we still need to measure

| Already known (RCA bakeoff) | Still needed (ingestion cost PoC) |
|-----------------------------|-----------------------------------|
| Lean ≈ federated accuracy (5/5) on UC corpus | $/1M events, GB/day, p99 ingest latency |
| Lean wins repro / verifiability / fewer obs | Collector and store ops headcount proxy |
| Federated CV edge didn’t buy top-1 here | Break-even: when does Nezha-tier ingest pay for itself? |

Full experiment plan: §3 below.  
**Vector ingest design (artifact contracts + L0/F1 sinks):** [`docs/INGESTION_PIPELINE_VECTOR.md`](docs/INGESTION_PIPELINE_VECTOR.md) · skeleton [`ingestion-poc/vector/`](ingestion-poc/vector/).  
**Data format / converters:** [`docs/INGEST_DATA_FORMAT.md`](docs/INGEST_DATA_FORMAT.md) · Motadata adapter [`ingestion-poc/adapters/`](ingestion-poc/adapters/).  
**Fair pipeline parity (shared detect):** [`docs/PIPELINE_PARITY.md`](docs/PIPELINE_PARITY.md) · [`ingestion-poc/detect/`](ingestion-poc/detect/).  
**Next actions:** [`docs/RCA_WORKFLOW_AND_NEXT.md`](docs/RCA_WORKFLOW_AND_NEXT.md).

---

## 1d) Learning links (algorithms & data structures)

Use these as background reading. Prefer **primers** first, then **source papers**. Repo PDFs under [`federated-pipeline/docs/papers/`](federated-pipeline/docs/papers/README.md) when available offline.

### Shared foundations (both engines)

| Topic | Why it matters here | Start here |
|-------|---------------------|------------|
| Graphs & adjacency / traversal | Typed CI / dependency topology | [Graph (Wikipedia)](https://en.wikipedia.org/wiki/Graph_(discrete_mathematics)) · [Graph traversal](https://en.wikipedia.org/wiki/Graph_traversal) |
| Breadth-first search (BFS) | Lean’s **efficiency baseline** (naive expansions), not the main search | [BFS (Wikipedia)](https://en.wikipedia.org/wiki/Breadth-first_search) · [VisuAlgo BFS](https://visualgo.net/en/dfsbfs) |
| Best-first / priority search | Lean’s actual walk order (score-guided frontier) | [Best-first search](https://en.wikipedia.org/wiki/Best-first_search) · [A\* overview](https://en.wikipedia.org/wiki/A*_search_algorithm) (related family) |
| Information gain | Lean candidate prioritization intuition | [Information gain](https://en.wikipedia.org/wiki/Information_gain_(decision_tree)) · [Entropy](https://en.wikipedia.org/wiki/Entropy_(information_theory)) |
| Temporal / onset ordering | “Who failed first” clue (necessary, not sufficient) | [Temporal logic (overview)](https://en.wikipedia.org/wiki/Temporal_logic) · practical: clock skew / Δt windows in ops |
| Configuration Item (CMDB) | ObserveOps inventory CI model | [CMDB](https://en.wikipedia.org/wiki/Configuration_management_database) · [ITIL CI](https://en.wikipedia.org/wiki/Configuration_item) |

### Lean-specific

| Topic | Why it matters here | Start here |
|-------|---------------------|------------|
| Heuristic / rule-based diagnosis | `shared_upstream`, signatures, `upstream_healthy` | Pattern: expert systems + production runbooks (concept) · repo: [`lean-pipeline/docs/ARCHITECTURE.md`](lean-pipeline/docs/ARCHITECTURE.md) |
| Spectrum / correlational ranking | CARE PoC ranks by severity under Δt ambiguity | CARE in papers is spectrum-based; our PoC is a **lighter** ranking — see [`LIMITATIONS_AND_FUTURE.md`](lean-pipeline/docs/LIMITATIONS_AND_FUTURE.md) |
| Lightweight causal checks | Tier-3 `verify_care_root` (not full Pearl do-calculus) | [Causal inference (intro)](https://en.wikipedia.org/wiki/Causal_inference) · [Pearl’s ladder (gentle)](https://ftp.cs.ucla.edu/pub/stat_ser/r481.pdf) (advanced) |
| Visual walkthrough | Sub-step Tier 1→2→3 | [`TIERED_ESCALATION_VISUAL_GUIDE.md`](lean-pipeline/docs/TIERED_ESCALATION_VISUAL_GUIDE.md) |

### Federated-specific (papers + primers)

| Topic | Why it matters here | Start here |
|-------|---------------------|------------|
| **Panorama** (gray failure / observers) | Detection hop | Paper PDF (local): [`Panorama_OSDI2018.pdf`](federated-pipeline/docs/papers/Panorama_OSDI2018.pdf) · [Author pubs](https://www.cs.jhu.edu/~huang/pubs.html) · USENIX: [OSDI ’18 open access](https://www.usenix.org/conference/osdi18/presentation/huang) · Primer: [Gray failure (HotOS)](https://www.cs.jhu.edu/~huang/paper/grayfailure-hotos17.pdf) |
| **Murphy** (MRF + Gibbs) | Macro localization | Open PDF: [Illinois copy](https://sachin.cs.illinois.edu/papers/murphy-harsh-sigcomm23.pdf) · Alt: [Godfrey lab](https://pbg.cs.illinois.edu/papers/harsh23murphy.pdf) · Local: [`Murphy_SIGCOMM2023.pdf`](federated-pipeline/docs/papers/Murphy_SIGCOMM2023.pdf) |
| Markov Random Field | Murphy dependency model | [MRF (Wikipedia)](https://en.wikipedia.org/wiki/Markov_random_field) · [Graphical models survey (Koller/Friedman book site)](https://ermongroup.github.io/cs228-notes/) |
| Gibbs sampling | Murphy inference; source of repro variance | [Gibbs sampling](https://en.wikipedia.org/wiki/Gibbs_sampling) · [MCMC intro (Princeton)](https://www.cs.princeton.edu/courses/archive/fall11/cos513/docs/lec7.pdf) |
| **Nezha** (event graphs / pattern drift) | Micro hop | ACM: [doi:10.1145/3611643.3616249](https://doi.org/10.1145/3611643.3616249) · Code: [IntelligentDDS/Nezha](https://github.com/IntelligentDDS/Nezha) · Local: [`Nezha_FSE2023.pdf`](federated-pipeline/docs/papers/Nezha_FSE2023.pdf) |
| Event / execution graphs | Speed-tier substrate for Nezha | [Event graph (overview)](https://en.wikipedia.org/wiki/Event_graph) · distributed tracing primer: [OpenTelemetry Concepts](https://opentelemetry.io/docs/concepts/) |
| Orchestration / fusion | Multi-engine hop contracts | Repo: [`ORCHESTRATOR.md`](federated-pipeline/docs/ORCHESTRATOR.md) · [`FEDERATED_PIPELINE_VISUAL_GUIDE.md`](federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md) |
| Paper dissections (internal) | Guided reading | [`dissections/`](federated-pipeline/docs/dissections/) |

### Ingestion & storage (cost PoC background)

| Topic | Why it matters here | Start here |
|-------|---------------------|------------|
| Lambda / dual-path analytics | Speed vs structural tier intuition | [Lambda architecture](https://en.wikipedia.org/wiki/Lambda_architecture) |
| Stream processing | High-velocity ingest | [Stream processing](https://en.wikipedia.org/wiki/Stream_processing) · [Kafka intro (Confluent)](https://developer.confluent.io/what-is-apache-kafka/) |
| Time-series / hot retention | Metric windows, TTL | [Time series database](https://en.wikipedia.org/wiki/Time_series_database) · Redis/Dragonfly sorted sets as hot windows (ops blogs vary) |
| Knowledge / property graphs | Structural tier vision | [Knowledge graph](https://en.wikipedia.org/wiki/Knowledge_graph) · [Property graph model](https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph) |
| Observability pillars | Metrics / logs / traces | [Observability](https://en.wikipedia.org/wiki/Observability) · [OpenTelemetry](https://opentelemetry.io/docs/) |
| Repo storage vision | Federated dual-tier design | [`STORAGE_TIERS.md`](federated-pipeline/docs/STORAGE_TIERS.md) · [`CAPACITY.md`](federated-pipeline/docs/CAPACITY.md) |

### Suggested reading order (1–2 evenings)

1. BFS + best-first + info-gain primers (Lean walk).  
2. Lean architecture + Tier visual guide (map primers → this repo).  
3. MRF + Gibbs primers → Murphy PDF (macro hop).  
4. Gray failure / Panorama abstract → Nezha abstract (detect + micro).  
5. Lambda architecture + OpenTelemetry (ingestion cost PoC vocabulary).

### Study notes in this repo

| Note | Focus |
|------|--------|
| [`Lean-decoded.md`](Lean-decoded.md) | Lean tagged study (corrected coach notes) |
| [`Federated-decoded.md`](Federated-decoded.md) | Federated tagged study |
| [`docs/UC_LEARNING_BRAINSTORM.md`](docs/UC_LEARNING_BRAINSTORM.md) | UC walkthroughs (not bakeoff GT) |

---

## 2) Why we need a dedicated ingestion-cost PoC

Current bakeoffs compare RCA reasoning on shared frozen inputs, which is correct for fairness.  
But real deployment cost = **ingestion + storage + RCA + ops overhead**.

So the next fair comparison is:

`Total Cost to Diagnose = Ingestion Cost + RCA Runtime Cost + Platform/Ops Cost`

without mixing product claims.

---

## 3) Ingestion Pipeline Cost PoC (proposal)

**Canonical plan:** [`docs/INGESTION_POC_PLAN.md`](docs/INGESTION_POC_PLAN.md) — milestones M1–M3, hardware tiers A–C, week-by-week checklist, sign-off gates.

### 3.0 Vector as the shared ingest fabric

Design (not full implementation): [`docs/INGESTION_PIPELINE_VECTOR.md`](docs/INGESTION_PIPELINE_VECTOR.md).

- **One** Vector collect/normalize path; **Lean-only (L0)** vs **dual-sink (F1)** profiles for cost compare.  
- Topology crawler stays **beside** Vector; post-Vector builders materialize Lean bundles and Federated speed-tier keys.  
- Skeleton: [`ingestion-poc/vector/`](ingestion-poc/vector/).

### 3.1 Objective

Estimate and compare ingestion + serving cost envelope for Lean vs Federated under the same synthetic/recorded workload profiles.

### 3.2 Scope boundaries

In scope:
- Telemetry ingest path to RCA-ready normalized payloads
- Storage footprint and retention behavior
- Throughput/latency under controlled load
- Infra/runtime costs and ops complexity indicators

Out of scope (for this PoC pass):
- Final RCA accuracy debate (already covered by existing bakeoff)
- Full production HA hardening
- Vendor-specific contract pricing nuances

### 3.3 Comparison surfaces

Measure three surfaces separately:

1. **Ingestion-only**  
   Cost to ingest, normalize, and store RCA-ready telemetry.

2. **RCA-only**  
   Cost to run diagnosis using prebuilt normalized snapshots.

3. **End-to-end**  
   Cost from incoming telemetry to final verdict.

This avoids confusion where one side is blamed for another side's bottleneck.

### 3.4 Workload profiles

Define fixed profiles (same for both pipelines):

- **P1 Low steady:** baseline operations
- **P2 Bursty incident:** short spikes (5x-20x)
- **P3 Multi-tenant mixed:** heterogeneous load
- **P4 Retention stress:** long-running storage pressure

Input dimensions:
- events/sec
- topology updates/sec
- trace/span-like payload rate
- % incidents requiring deep path analysis
- retention window (hot/cold)

### 3.5 Metrics (must-have)

Performance:
- ingest throughput (events/sec)
- p50/p95/p99 ingest latency
- queue/backlog growth
- drop/retry rate

Resource:
- CPU-seconds / 1M events
- RAM peak + steady-state
- storage GB/day by tier
- network egress/ingress per incident window

Economics:
- infra $/hour by component
- $/1M events ingested
- $/diagnosis (end-to-end)
- monthly projected run-rate by workload profile

Operability:
- moving parts count
- on-call burden proxy (alerts/day, failure modes)
- reprocessing complexity

### 3.6 Data collection approach

- Instrument every stage with uniform telemetry schema (`cost_trace_id`, timestamps, bytes, retries).
- Emit per-stage accounting logs to a shared cost ledger table/file.
- Produce a run summary artifact:
  - `cost_report.json`
  - `cost_report.md`
  - profile-wise comparison table.

### 3.7 Fairness rules

- Same machine class / quota for both runs.
- Same input payload replay and timeline.
- Same retention policy assumptions per profile.
- Explicitly document what is simulated vs fully implemented.
- Report confidence level per metric (measured vs extrapolated).

### 3.8 Deliverables

1. `ingestion-cost-poc/PLAN.md` (experiment contract)
2. `ingestion-cost-poc/profiles/*.json` (workload profiles)
3. `ingestion-cost-poc/scripts/` (replay + measurement harness)
4. `benchmarking/results/costing/`:
   - `LEAN_COST_REPORT.md/json`
   - `FEDERATED_COST_REPORT.md/json`
   - `COMPARATIVE_COST_REPORT.md/json`

### 3.9 Decision output format

Final output should not be "which is better" in absolute terms.

Use:
- **Cost envelope by scenario**
- **Break-even zones**
- **Recommended default per workload class**

Example:
- Classic infra steady-state: lean cheaper and simpler
- Microservice drift-heavy hot paths: federated may justify incremental ingest/RCA cost

---

## 4) Execution plan (2-week draft)

Week 1:
- Freeze profiles + metric schema
- Build replay harness + instrumentation hooks
- Dry runs on P1/P2

Week 2:
- Run all profiles for both pipelines
- Generate comparative cost reports
- Review assumptions + sensitivity analysis

---

## 5) Risks and controls

Risks:
- Simulated ingest may underestimate real operational complexity
- Capacity numbers may be host-bound and non-transferable
- Incomplete parity between pipeline implementations

Controls:
- Mark each metric as measured / simulated / extrapolated
- Include confidence bands
- Keep scenario-specific recommendations instead of global claims
