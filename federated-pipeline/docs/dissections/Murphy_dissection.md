---
title: "Murphy — Performance Root-Cause Diagnosis via Counterfactual MRF"
subtitle: "Unified RCA Tier 2 · Learning Dissection"
papersize: a4
geometry: margin=18mm
---

# Murphy: Performance Root-Cause Diagnosis via Counterfactual MRF

> **Unified RCA — Tier 2 (Knowledge Graph / Infra RCA)**
> Murphy's core trick is **not** to mine event patterns (Nezha) or reconcile observer votes (Panorama). It builds a **relationship graph** over infrastructure entities, learns **how metrics propagate** along edges with Ridge regression, then asks a counterfactual question: *if we had fixed entity A's metrics to normal, would the symptom metric at entity B still look anomalous?* Gibbs sampling propagates that hypothetical through the graph; a **t-test** on sampled symptom values separates true root causes from correlated bystanders.

| | |
|:---|:---|
| **Document** | Murphy learning dissection |
| **Tier** | 2 — Infra performance RCA (MRF + counterfactual) |
| **Code** | `murphy/` · `graph.py` · `mrf.py` |
| **Simulator** | [127.0.0.1:8770/#murphy](http://127.0.0.1:8770/#murphy) |
| **Related** | [Panorama (Tier 1)](Panorama_dissection.md) · [Nezha (Tier 3)](Nezha-dissection.md) |
| **Print (A4)** | `./federated-pipeline/scripts/build-dissection-pdf.sh Murphy_dissection.md` |

---

## Contents

1. [How to Read This Document](#how-to-read-this-document)
2. [Groundwork: Why Panorama and Nezha Are Not Sufficient](#groundwork-why-panorama-and-nezha-are-not-sufficient)
3. [What Murphy Adds](#what-murphy-adds-the-missing-middle-tier)
4. [The Big Picture (30-Second Version)](#the-big-picture-30-second-version)
5. [Core Data Types](#core-data-types)
6. [Relationship Graph](#relationship-graph-graphpy)
7. [MRF Engine: Ridge + Counterfactual Gibbs](#mrf-engine-ridge--counterfactual-gibbs-mrfpy)
8. [Ranking](#ranking-rankerpy)
9. [Explanations](#explanations-explainerpy)
10. [Worked Example — Paper Figure 1](#worked-example--paper-figure-1-crawler-incident)
11. [Panorama vs Nezha vs Murphy](#panorama-vs-nezha-vs-murphy)
12. [Key Files](#key-files)
13. [Guided Walkthrough (Simulator)](#guided-walkthrough-simulator)
14. [Cheat Sheet](#cheat-sheet)
15. [Simulation](#simulation)

---

## How to Read This Document

Work through sections **in order** the first time.

> **why Panorama & Nezha are not enough → the gap Murphy fills → unified RCA tiers → pipeline → relationship graph → prune → Ridge → counterfactual Gibbs → t-test → explanations → worked example → three-way comparison**

For reference, jump to the [Cheat Sheet](#cheat-sheet).

### Where Murphy sits in Unified RCA

| Tier | Tool | Question |
|:----:|:-----|:---------|
| 1 | [Panorama](Panorama_dissection.md) | Who is unhealthy right now? |
| 2 | **Murphy** (this doc) | Which upstream entity caused this performance symptom? |
| 3 | [Nezha](Nezha-dissection.md) | Which code-path event patterns shifted? |

### μ ± 1σ in plain English

- **μ (mu)** — the usual average for that metric over the last **7 days** of history.
- **σ (sigma)** — how much that metric normally wiggles day to day (standard deviation).
- **μ ± 1σ** — the “typical healthy band” (roughly the middle **68%** of readings).

Murphy uses this band like a speed limit during **prune**: if **any** metric on an entity is **outside** μ ± 1σ, that entity stays a **candidate**. If all metrics stay inside (e.g. `normal_vm` CPU at 0.201 vs μ≈0.20), the entity is **pruned** and **never reaches Gibbs**.

**Counterfactual clamping** uses **μ ± 2σ** — a stricter “clearly back to normal” target when simulating “what if we fixed entity A?”

---


<div class="pagebreak"></div>
## Groundwork: Why Panorama and Nezha Are Not Sufficient

The Unified RCA platform stacks three tools because **each solves a different class of question**. Panorama and Nezha are powerful — but they leave a large hole in **performance diagnosis for distributed cloud applications**.

### What Panorama answers (and what it cannot)

Panorama answers: **"Who is unhealthy right now, according to independent observers?"**


| Panorama strength                               | Limit for performance RCA                                                                                                                                                                 |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Real-time, baseline-free fault detection        | Discrete status enums (`HEALTHY`, `PENDING`, `MAYBE_UNHEALTHY`, `UNHEALTHY`, `DEAD`) — not continuous latency/CPU time series                                                             |
| Observer convergence on logs                    | **Filter tree** (`zoo_filter.json` + `FieldFilterTree.Eval`) maps each log line → `(observer, subject, metric, status, score)` — not a flat event list, but still **classification only** |
| Works on ZooKeeper ensemble partitions          | Needs multiple observers of the same subject; weak on cloud metric topology (host/NIC/ToR/flow)                                                                                           |
| Tells you **peer@9 is UNHEALTHY on SyncThread** | Does **not** tell you **why backend CPU spiked** or **which upstream VM started it**                                                                                                      |


Panorama is **Tier 1 — symptom detection**. Its filter tree is there for **accurate symptom identification** — regex/chain rules pick the right metric, subject, and severity from noisy logs. That is richer than tallying raw events, but it still answers *what looks unhealthy on whom*, not *what caused it*. `InferView` / `InferPano` reconcile **observer disagreement** (majority vote); they do not rank upstream entities by causal responsibility for a performance regression.

### What Nezha answers (and what it cannot)

Nezha answers: **"Which event-pair patterns drifted between fault-free and fault windows?"**


| Nezha strength                                                       | Limit for performance RCA                                                                                                                                                      |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Unifies metrics, logs, traces into one event graph per request       | **Per-trace, offline** — not a system-wide metric propagation model                                                                                                            |
| Finds code-region patterns (`charge_start → charge_ok` support drop) | Points to **pods/spans/templates** (e.g. `checkoutservice` PlaceOrder logs), not Murphy-style **infra entities** (paper Fig. 1: `crawler_vm` → `frontend_ms` → `backend_vm_1`) |
| Homogeneous `Event` + Drain3 cluster IDs                             | Needs `construct_data` fault-free baseline before any signal                                                                                                                   |
| Great for "what changed in request behavior?"                        | Poor for "which VM sent abnormal load that propagated?"                                                                                                                        |


Nezha is **Tier 3 — code-level RCA**. It explains *what the software did differently* on each request — which log-template pairs gained or lost support, on which pod, at what call depth.

#### Why Murphy talks about “cyclic infrastructure graphs” (and Nezha doesn’t)

These are **two different graph types** for **two different questions**:


|           | **Nezha EventGraph**                                                  | **Murphy RelationshipGraph**                                  |
| --------- | --------------------------------------------------------------------- | ------------------------------------------------------------- |
| **Node**  | One event on one trace (Drain template, span start/end, metric alarm) | A persistent entity (VM, microservice, host, NIC, ToR switch) |
| **Edge**  | “happened before” or “parent called child” on a **single request**    | “runs on / connected to / shares” in **deployment topology**  |
| **Scope** | One minute of traces, many separate graphs                            | One standing infra graph per application                      |
| **Shape** | **DAG per trace** — time moves forward                                | **Often cyclic** — mutual wiring (VM ↔ host ↔ ToR)            |


**Nezha — acyclic by construction.** Events in a span are sorted by timestamp; edges link consecutive events (pillar) and parent spans to children (slice). On one checkout trace:

```
PlaceOrder start → Start charge card → Failed to connect payment service → PlaceOrder end
```

There is no edge from `end` back to `start` on the same trace. Nezha then **counts directed pairs across thousands of traces** (e.g. `charge_start→charge_fail` support rises). It does not keep a persistent “who is wired to whom” graph.

**Murphy — cycles are normal.** Infrastructure relationships are mutual: a VM runs on a host, a NIC serves a VM, two VMs share a ToR switch. Murphy wires many edges **bidirectionally** (`graph.py`: `add_edge(..., bidirectional=True)`), so paths can loop. Paper Figure 1 example:

```
crawler_vm → frontend_ms → backend_vm_1     (app load path)
crawler_vm ↔ host_crawler ↔ tor_switch_1 ↔ host_backend ↔ backend_vm_1   (shared network)
```

A ToR bottleneck can correlate metrics on **both** VMs; Murphy’s Ridge models and Gibbs counterfactuals propagate through that mesh. That is what “cyclic infrastructure graph” means — not that Nezha events form cycles, but that **Murphy models shared infra feedback** that a per-trace event DAG never represents.

Nezha neither builds that topology nor runs counterfactual metric intervention on it.

### The gap in one sentence

> **Panorama tells you something broke. Nezha tells you which request-level patterns shifted. Neither tells you which upstream entity in a metric topology *caused* a performance symptom to move — with statistical confidence and a human-readable propagation chain.**

That gap is exactly what Murphy (SIGCOMM 2023) targets.

---


<div class="pagebreak"></div>
## What Murphy Adds: The Missing Middle Tier

Murphy is **Tier 2 — knowledge-graph performance diagnosis**:

```
Panorama (symptom)  →  Murphy.diagnose()  →  ranked root causes + explanations  →  Nezha (code RCA)
```


| Question                                                          | Tool         |
| ----------------------------------------------------------------- | ------------ |
| Is anything unhealthy?                                            | **Panorama** |
| **Which entity/metric upstream caused this performance symptom?** | **Murphy**   |
| Which code path / event pattern explains the fault?               | **Nezha**    |


### Murphy's bet

1. **Model the system as a graph** — VMs, microservices, hosts, NICs, ToR switches, flows — with typed edges (not just trace parent/child).
2. **Learn normal propagation** — Ridge regression per `(entity, metric)` predicts a metric from its in-neighbors' historical time series (top-B correlated features). See [Ridge, propagation & Gibbs — mini walkthrough](#ridge-propagation--gibbs--mini-walkthrough-fig-1) below.

3. **Counterfactual intervention** — For candidate root cause A, set A's metrics to *normal* (mean ± 2σ flip). Sample the symptom metric at B via **Gibbs sampling** along the path. Compare to samples with A's *true* anomalous values.
4. **Statistical test** — If fixing A shifts the symptom distribution significantly (one-sided t-test, p < 0.05), A is a root cause.
5. **Explain** — Walk the shortest path A → symptom with a state machine (`heavy_hitter` → `degraded_performance` → …).

#### Ridge, propagation & Gibbs — mini walkthrough (Fig. 1)

Murphy’s pipeline has **three phases**. Ridge is **not** normalization or pre-processing — it is **training** (learning how the system usually behaves). Gibbs + counterfactual is **diagnosis** (testing “what if we fixed entity A?”).

```
Phase A — TRAIN (7 days history)     Ridge learns "normal propagation"
Phase B — PIN candidate A            counterfactual (normal) vs true (anomalous)
Phase C — PROPAGATE + SAMPLE         Gibbs walks the graph using Ridge models → symptom metric
Phase D — COMPARE                    t-test on 5000 symptom samples → root cause?
```

**Setup (paper Figure 1):**

```
crawler_vm  ──→  frontend_ms  ──→  backend_vm_1
 (throughput↑)     (latency↑)        (cpu_usage↑)  ← SYMPTOM
```

**Candidate A → B → C (entity roles on the Ridge path):**

| Role | Entity | Metric on path | What happens |
|------|--------|----------------|--------------|
| **A** (candidate, clamped) | `crawler_vm` | `throughput` (also `session_count` clamped) | Root-cause under test; **all hot metrics** on A are fixed during Gibbs |
| **B** (middle hop) | `frontend_ms` | `latency_p90` | Re-sampled from Ridge given upstream (A’s clamped values) |
| **C** (symptom) | `backend_vm_1` | `cpu_usage` | Where the alert fired; Murphy **reads** this metric after propagation |

Full trained path: **`crawler_vm:throughput` → `frontend_ms:latency_p90` → `backend_vm_1:cpu_usage`**.

A is whichever entity Murphy tests (`focus_candidate`); B is whatever sits on the shortest path between A and C; C is the symptom entity (`symptom.entity`), which may differ from A when the alert lands downstream (here: backend CPU, root cause upstream at crawler).

At incident time everything is hot. SRE alert: `backend_vm_1.cpu_usage = 0.77` (historical mean ≈ 0.25).

---

##### Is Ridge “pre-work” like normalizing?

**No.** Normalizing would rescale numbers (e.g. divide by mean). **Ridge is supervised ML training:**

| | Normalization | Ridge (Murphy) |
|--|---------------|----------------|
| **Purpose** | Put metrics on comparable scale | Learn **prediction rules** from history |
| **Output** | Transformed numbers | A **model**: `backend_cpu ≈ w0 + w1×frontend_latency + w2×…` |
| **When** | Optional preprocessing | **Once per diagnosis** on 7-day history |
| **Used for** | Display / some ML pipelines | **Gibbs sampling** — “given neighbors, what should this metric be?” |

Murphy trains **one Ridge model per (entity, metric)** on the path. Example models learned from healthy weeks:

- `frontend_ms:latency_p90` ← predicted from `crawler_vm:throughput`, …
- `backend_vm_1:cpu_usage` ← predicted from `frontend_ms:latency_p90`, …

Each model returns a **predicted value + noise** (`model.sample()` uses prediction ± residual σ). That is the engine for propagation.

---

##### What does “propagation” mean?

**Propagation** = filling in metric values **along the graph**, one entity at a time, using Ridge models: *“my neighbors currently look like X, so my metric is probably Y (± noise).”*

Think of a **domino chain of predictions**:

1. You **clamp** (fix) the candidate entity’s metrics — either **true** (still broken) or **counterfactual** (forced normal).
2. For the next entity on the path, Ridge reads its **in-neighbors’ current values** and **samples** its own metric.
3. Repeat for each entity until you reach the **symptom** entity and read `cpu_usage`.

That one pass along A → B → C is **one inner Gibbs sweep** (Murphy runs **W = 4** such sweeps per outer sample). One symptom reading at C = one **sample**. Murphy repeats **5000 samples** to get a **distribution** of “what the symptom metric would look like under this clamp.”

**Propagation is not** sending network packets — it is **simulating how metrics would flow through the dependency graph** if upstream values were X.

---

##### What is Gibbs sampling? (one sample, step by step)

Forget abstract “people in a line.” Think of **one Monte Carlo roll** of a **small simulator** Murphy already trained with Ridge.

**Path:** `crawler_vm` → `frontend_ms` → `backend_vm_1`
**Question:** If we **clamp** crawler throughput, what backend CPU do we **simulate**?

Murphy runs **two experiments** (same path, same randomness pattern, different clamp):

---

**Experiment D2 — clamp crawler at TRUE (broken) throughput ≈ 976**

| Step | What happens | Concrete values (illustrative) |
|------|----------------|--------------------------------|
| 0. **Clamp** | **All hot metrics** on `crawler_vm` are **locked** — Gibbs cannot change them | e.g. `throughput = 976`, `session_count = 96` (fixed) |
| 1. **Sample frontend** | Ridge model for `frontend_ms:latency_p90` reads clamped crawler + adds noise | `latency_p90 ≈ 124ms` (high) |
| 2. **Sample backend** | Ridge model for `backend_vm_1:cpu_usage` reads frontend + adds noise | `cpu_usage ≈ 0.74` |
| 3. **Re-sweep** (×4) | Frontend and backend are **re-sampled** from Ridge again; crawler **stays 976** | `cpu_usage ≈ 0.76` after last sweep |
| 4. **Record** | That final `cpu_usage` is **one sample** | sample #1 = **0.76** |

Repeat steps 0–4 **5000 times** (new noise each time) → distribution **D2**: backend CPU clustered around **~0.75** (matches the real alert 0.77).

---

**Experiment D1 — clamp crawler at COUNTERFACTUAL (normal) throughput ≈ 99**

Same simulator, but step 0 clamps crawler metrics to healthy μ±2σ (e.g. throughput ≈ 99) instead of broken values.

| Step | Change | Result |
|------|--------|--------|
| 0. Clamp | all crawler metrics at healthy μ±2σ | crawler “fixed as if healthy” |
| 1–3. Propagate | Ridge + noise down the chain | `latency_p90 ≈ 52ms`, `cpu_usage ≈ 0.27` |
| 4. Record | One sample | sample #1 = **0.27** |

5000 repeats → distribution **D1**: backend CPU clustered around **~0.28** (healthy band).

---

**What “Gibbs” adds beyond one forward pass**

A single forward pass (A → B → C once) would already give one number. Murphy runs **W = 4 inner sweeps** per outer sample:

1. **Clamp A** (counterfactual normal for D1, or true broken values for D2).
2. For each sweep **1…W**: walk entities on the path **except A**; for each free entity/metric, `model.sample()` = Ridge **predict(neighbors) + Gaussian noise(residual σ)**.
3. **Read C** (symptom metric) → one value in the distribution.

So **W is not “multiply the path W times”** in a chain-rule sense — it is **W re-sweeps** where B and C get **re-sampled** from Ridge given the latest upstream assignments, while A stays clamped. That lets the path settle before recording the symptom.

Repeat the whole procedure **5000 times** (new noise each time) → distributions **D1** and **D2** for the t-test.

**One sentence:** Gibbs sampling = *run the trained “metric physics” simulator 5000 times with A clamped normal vs broken, and see if C’s metric distributions separate.*

---

##### Full counterfactual example — is `crawler_vm` the root cause?

**Candidate:** `crawler_vm` (both `session_count` and `throughput` were far above μ±1σ).

> **Clamp `session_count` or `throughput`?** **Both.** `_counterfactual_values_for_entity()` clamps **every metric** on entity A at incident time. The prototype labels the tested root-cause pair separately (e.g. `crawler_vm:session_count` in the t-test line when the symptom is frontend latency).

| Run | Clamp on `crawler_vm` | Gibbs propagates → | 5000 samples of **symptom** metric |
|-----|----------------------|--------------------|-------------------------------------|
| **D2 (true)** | Keep **broken** values (~96 sessions, ~976 throughput) | frontend stays high → backend stays high | e.g. `backend_vm_1:cpu_usage` mean ≈ **0.75** (near observed 0.77) |
| **D1 (counterfactual)** | Force **normal** (μ ± 2σ flip on each metric) | frontend drops → backend drops | e.g. `backend_vm_1:cpu_usage` mean ≈ **0.28** (healthy band) |

When the **symptom** is `frontend_ms:latency_p90`, D1/D2 are means of **latency** samples (≈55 vs ≈126), not backend CPU — same logic, different symptom metric.

**μ in D1/D2 lines** = **mean of the 5000 Gibbs samples** of the symptom metric, not the single live alert value (though D2 should be close to it).

If candidate were a **bystander** (correlated but not causal), clamping it to normal would **not** move the symptom distribution much — D1 and D2 would look similar → **reject** as root cause.

**Why not just compare raw metrics?** A NIC or ToR might also look hot. Counterfactual + propagation tests whether **this specific entity’s state is necessary** for the symptom, along the causal path.

---

##### How the three pieces fit together

| Piece | One-line role |
|-------|----------------|
| **Ridge** | Learned **normal physics** of the graph: neighbor metrics → this metric |
| **Propagation** | Apply that physics along the path with current/clamped neighbor values |
| **Gibbs** | Repeat stochastic propagation many times → distribution at symptom |
| **Counterfactual** | Compare clamp-broken vs clamp-normal → causal necessity test |
| **t-test** | Statistical verdict on root cause |

Ridge alone only says “backend CPU is high given frontend latency” — **correlation**. Murphy’s contribution is **counterfactual Gibbs**: “if we had normalized **crawler** only, would backend CPU still be high?” — **causal screening**.


### What Murphy deliberately does *not* do

- **Symptom detection** — you pass in a `Symptom` (entity, metric, observed value, incident time). Panorama or an SLO alert can supply this.
- **Code-level RCA** — output is `crawler_vm:throughput`, not `PlaceOrder → charge_ok` pair drift.
- **Persistent models** — trains Ridge models online each invocation (7-day lookback by default).

---


## The Big Picture (30-Second Version)

```
MetricStore (time series + entity metadata)
        ↓
  Symptom  →  entity_id, metric_name, incident_time
        ↓
  RelationshipGraph.build_from_monitoring_db()  →  cyclic infra topology
        ↓
  prune_candidates()  →  BFS from symptom; keep entities with metric > μ ± 1σ
        ↓
  train_all_models()  →  per (entity, metric): Ridge on in-neighbor features
        ↓
  For each candidate (entity, metric):
        counterfactual values on A  vs  true values on A
        ↓
  Gibbs sample symptom metric W times (paper: W=4 inner, 5000 outer samples)
        ↓
  t-test(D1 counterfactual, D2 true)  →  p-value, is_significant
        ↓
  RootCauseRanker  →  sort by anomaly score (max |z| over metrics)
        ↓
  ExplanationGenerator  →  causal chain along shortest path
        ↓
  DiagnosisResult  →  { symptom, root_causes[], explanation_chains{} }
```

---


<div class="pagebreak"></div>
## Core Data Types


| Type              | Fields                                                                  | Role                                                                   |
| ----------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `Entity`          | `id`, `entity_type`, `app_id`, `metadata`                               | Node in relationship graph (vm, microservice, host, nic, router, flow) |
| `MetricSample`    | `entity_id`, `metric_name`, `timestamp`, `value`                        | One point in monitoring DB                                             |
| `Symptom`         | `entity_id`, `metric_name`, `observed_value`, `incident_time`           | **Input** — where SRE noticed pain                                     |
| `RootCause`       | `entity_id`, `metric_name`, `anomaly_score`, `p_value`, `d1/d2_samples` | **Output** — statistically significant upstream cause                  |
| `ExplanationStep` | `from_entity`, `to_entity`, `from_state`, `to_state`, `edge_label`      | One hop in narrative chain                                             |


Composite model key: `entity_id:metric_name` (e.g. `crawler_vm:session_count`).

---


<div class="pagebreak"></div>
## Relationship Graph (`graph.py`)

Murphy's graph is **not** a trace DAG. It is a **cyclic directed infrastructure topology**:

```
crawler_vm ──→ frontend_ms ──→ backend_vm_1
     │              │                │
 host_crawler   (upstream/      host_backend
 nic_crawler     downstream)     nic_backend
     │                              │
     └──────── tor_switch_1 ────────┘
```


### How edges are wired

1. **Explicit** — `metadata.neighbors`, `upstream`, `downstream`, `directed_edges`
2. **Type-based** — `vm` ↔ `host`, `vm` ↔ `nic`, `microservice` ↔ `container`, `host` ↔ `tor_switch`, `flow` ↔ source/dest VM


### Key graph operations


| Method                         | Purpose                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| `bfs_from(symptom_entity)`     | Reachable entities within `max_hops` (default 5)                   |
| `prune_candidates()`           | Keep entities with **any** metric beyond μ ± 1σ from 7-day history |
| `shortest_path_subgraph(A, B)` | Nodes on shortest path(s) for Gibbs propagation                    |
| `shortest_path_hops(A, B)`     | Single path for explanation text                                   |


**Pruning is conservative** — it drops obviously normal entities (e.g. `normal_vm` with stable CPU) before expensive Gibbs runs.

#### How metrics are chosen for `crawler_vm`, `frontend_ms`, `backend_vm_1`

**Prune does not assign one metric per candidate.** It keeps **entities** if **any** monitored metric is beyond μ ± 1σ:

| Entity | Why it survives prune | Hot metrics at incident (Figure 1) |
|--------|----------------------|-------------------------------------|
| `backend_vm_1` | Symptom entity (always kept) | `cpu_usage` 0.771 vs μ≈0.25 |
| `frontend_ms` | On BFS path; latency anomalous | `latency_p90` 126.3 vs μ≈54.8 |
| `crawler_vm` | Upstream; crawler metrics hot | `session_count` 95.7 vs μ≈12; `throughput` 975.8 vs μ≈119 |
| `normal_vm` | **Pruned** — connected but CPU within band | `cpu_usage` 0.201 vs μ≈0.20 |

The **Ridge path** (`train_models`) is separate: one trained model per **(entity, metric)** hop on the **shortest path** from candidate **A** → symptom **C** — e.g. `crawler_vm:throughput → frontend_ms:latency_p90 → backend_vm_1:cpu_usage` when the alert is backend CPU (A=`crawler_vm`, B=`frontend_ms`, C=`backend_vm_1`).

---


<div class="pagebreak"></div>
## MRF Engine: Ridge + Counterfactual Gibbs (`mrf.py`)


### Step 1 — Train `EntityModel` (Ridge)

For each `(entity_id, metric_name)` on paths to the symptom:

- Collect **7-day historical** target series from `MetricStore`
- For each **in-neighbor**, align neighbor metric series to same timestamps
- Pick **top-B** (default 10) features by correlation with target
- Fit `Ridge(α=1.0)`; track residual σ for sampling

```python
# Simplified mental model
predict(cpu_backend) = f(cpu_frontend, latency_frontend, …)
```


### Step 2 — Counterfactual on candidate A

For **all metrics** on entity A at incident time:

- If `current > mean` → set to `mean - 2σ`
- If `current < mean` → set to `mean + 2σ`

This is the "what if A were normal?" intervention (paper Figure 2).

### Step 3 — Gibbs sampling along path

Fix candidate entity **A**'s values (counterfactual or true). For **W** inner iterations (default **4**), walk entities on shortest path **A → … → C** (symptom):

- Skip **A** (clamped); for each other entity on the path, sample each metric from its Ridge model given current in-neighbor assignments (`predict + N(0, residual σ)`).
- After W sweeps, read symptom entity **C**'s target metric → **one sample**.

Repeat the full procedure **5000 times** → distributions `D1` (counterfactual A) and `D2` (true A).

```python
# mrf.py mental model — one outer sample
for _ in range(5000):
    assignment = copy(current_metrics)
  # clamp A (counterfactual or true)
    for _ in range(W):  # default W=4 inner sweeps
        for entity in path_entities:
            if entity == A: continue
            assignment[entity][metric] = model.sample(neighbor_values)
    D.append(assignment[C][symptom_metric])
```

### Step 4 — t-test

```python
stats.ttest_ind(D1, D2, alternative="less")
```

If fixing A **reduces** the symptom metric significantly → A is a root cause (`p < 0.05`).

> **Intuition:** Correlated bystanders (e.g. a NIC that spiked because it carried traffic) won't pass the counterfactual test. Only entities whose *abnormal state is necessary* for the symptom distribution shift survive.

---


<div class="pagebreak"></div>
## Ranking (`ranker.py`)

Among significant candidates, rank by **anomaly score**:

```
score(entity) = max over metrics of |current - μ| / σ
```

Higher z-score → more abnormal → listed first. Paper reports ~86% top-1 accuracy on DeathStarBench traces.

---


<div class="pagebreak"></div>
## Explanations (`explainer.py`)

State machine labels (threshold-based on current vs historical):


| State                  | Typical trigger                                   |
| ---------------------- | ------------------------------------------------- |
| `heavy_hitter`         | **Source** of excessive load (`session_count` or `throughput` ≥ 2× historical mean) — the aggressor, not the victim |
| `degraded_performance` | High `latency_p90` or elevated `cpu_usage`        |
| `high_drop_rate`       | `drop_rate` above threshold                       |
| `nonfunctional`        | `availability` ≈ 0                                |


Walk shortest path root → symptom; emit templated sentences:

> Entity **crawler_vm** (heavy hitter) **sent high load to** Entity **frontend_ms** (degraded performance). Entity **frontend_ms** (degraded performance) **propagated load to** Entity **backend_vm_1** (degraded performance).

---


<div class="pagebreak"></div>
## Worked Example — Paper Figure 1 (Crawler Incident)

**Fixture:** `murphy/tests/fixtures/crawler_incident.py`

### Topology


| Entity                            | Type         | Role                                |
| --------------------------------- | ------------ | ----------------------------------- |
| `crawler_vm`                      | vm           | Misbehaving crawler (heavy hitter)  |
| `frontend_ms`                     | microservice | Front-end service                   |
| `backend_vm_1`                    | vm           | Back-end VM (symptom location)      |
| `normal_vm`                       | vm           | Idle worker (should **not** rank)   |
| `host_*`, `nic_*`, `tor_switch_1` | infra        | Cyclic graph for realistic topology |


### Injected fault

```python
store.inject_fault("crawler_vm", "session_count", fault_type="spike", multiplier=8.0)
store.inject_fault("crawler_vm", "throughput", fault_type="spike", multiplier=8.0)
```

Causal rules in simulator:

- `crawler_vm.session_count` → `frontend_ms.latency_p90`
- `frontend_ms.latency_p90` → `backend_vm_1.cpu_usage`


### Symptom (what the operator sees)

```python
Symptom(
    entity_id="backend_vm_1",
    metric_name="cpu_usage",
    observed_value≈0.77,   # vs historical μ≈0.25
    incident_time=2024-06-15 12:00:00,
)
```


### Typical diagnosis output


| Rank | Root cause                | p-value | Chain                        |
| ---- | ------------------------- | ------- | ---------------------------- |
| 1    | `crawler_vm:throughput`   | ≈ 0     | A → B → C: crawler → frontend → backend |
| 2    | `frontend_ms:latency_p90` | ≈ 0     | B → C: frontend → backend           |


**A / B / C for this fixture:** A = `crawler_vm` (clamped), B = `frontend_ms`, C = `backend_vm_1` (symptom `cpu_usage`).

`normal_vm` pruned — CPU stayed within 1σ. Infrastructure hosts/NICs may appear in graph but fail t-test if counterfactual doesn't fix backend CPU.

### What Panorama would say here

If logs existed: maybe `backend_vm_1` UNHEALTHY on `cpu_usage`. No upstream ranking, no "crawler sent high load."

### What Nezha would say here

If traces existed: event-pair drift on hot spans in checkout path. No `crawler_vm` entity — different abstraction layer.

---


<div class="pagebreak"></div>
## Panorama vs Nezha vs Murphy


| Dimension            | Panorama                           | Murphy                                     | Nezha                       |
| -------------------- | ---------------------------------- | ------------------------------------------ | --------------------------- |
| **Primary signal**   | Observer log consensus             | Metric propagation + counterfactual        | Event-pair support drift    |
| **Input**            | ZooKeeper logs                     | Metric time series + entity graph          | Metrics + logs + traces CSV |
| **Baseline needed?** | No                                 | Yes (7-day μ, σ per metric)                | Yes (`construct_data`)      |
| **Real-time?**       | Yes                                | Near-real-time (online train per incident) | Offline batch               |
| **Output**           | `{subject, metric, status, score}` | `{entity, metric, p_value, chain}`         | Pattern / pod / region rank |
| **Graph type**       | Observer → subject views           | Infrastructure relationship graph          | Per-trace event DAG         |
| **Causal model**     | Majority vote                      | MRF + Ridge + Gibbs intervention           | Pattern frequency contrast  |
| **Best question**    | Who is unhealthy?                  | Who caused this performance symptom?       | What code path changed?     |
| **Tier**             | 1 — Symptom                        | 2 — Infra RCA                              | 3 — Code RCA                |


---


<div class="pagebreak"></div>
## Key Files


| File                                        | Role                                          |
| ------------------------------------------- | --------------------------------------------- |
| `murphy/murphy.py`                          | Top-level `Murphy.diagnose()` orchestrator    |
| `murphy/graph.py`                           | `RelationshipGraph` — build, prune, paths     |
| `murphy/mrf.py`                             | `MRFDiagnosisEngine` — Ridge, Gibbs, t-test   |
| `murphy/ranker.py`                          | `RootCauseRanker` — anomaly z-score sort      |
| `murphy/explainer.py`                       | `ExplanationGenerator` — state machine chains |
| `murphy/adapters/simulated_store.py`        | Synthetic metrics + fault injection           |
| `murphy/tests/fixtures/crawler_incident.py` | Paper Figure 1 reproducible incident          |


---


<div class="pagebreak"></div>
## Guided Walkthrough (Simulator)

**Unified UI (recommended):** [http://127.0.0.1:8770/#murphy](http://127.0.0.1:8770/#murphy) — tabbed Panorama / Murphy / Nezha (`index.html` + `federated-pipeline/deploy/systemd/unified-rca-learning-prototype.service` on port **8770**).

**Standalone:** `murphy/murphy-learning-prototype.html` (same content; serve from repo root).

### Prototype sidebar

| Panel | Purpose |
|-------|---------|
| **Scenario legend** | Numbered **1–9** cheat sheet (symptom → prune → Ridge → clamp → D1/D2 → t-test). During **guided walkthrough**, the row matching the current step is **highlighted** (orange); completed rows turn green; future rows dim. Includes μ ± 1σ plain-English blurb. |
| **Learning focus** | Scenario-level insight only (e.g. “symptom is backend CPU but root cause is crawler”) — **hidden during walkthrough** so it does not duplicate the step bar at the top. |
| **Gibbs detail** | Full counterfactual panel (clamp list, Ridge path, D1/D2, t-test) — readable HTML, not clipped SVG |
| **Root causes** | Ranked list + explanation chain (`heavy_hitter` → `degraded` → …) |

The main diagram shows **compact** summaries (Gibbs, gap banner, etc.); use the sidebar for full text. Hard-refresh the unified UI if you see stale layout (`index.html` cache param). Start **guided walkthrough** for prune BFS, Ridge, and Gibbs animations.

**Legend step map (walkthrough):**

| Legend # | Walkthrough step | Highlights |
|----------|------------------|------------|
| 1 | Step 1 — Symptom | Alert input |
| 2–4 | Step 3 — Prune | Candidates, hot metrics, pruned examples |
| 5 | Step 4 — Train | Ridge path |
| 6–7 | Step 5 — Counter | Clamp on A, RC test metric |
| 8 | Steps 6–7 — Gibbs / t-test | D1 vs D2 sample means |
| 9 | Step 7 — t-test | t-test result |

### Steps

1. **Symptom** — SRE alert: `backend_vm_1.cpu_usage` elevated at incident time
2. **Build graph** — wire VMs, microservices, hosts, NICs, ToR from entity metadata
3. **Prune candidates** — BFS ripple from symptom; drop entities within μ±1σ (e.g. `normal_vm` never reaches Gibbs)
4. **Train Ridge** — learn how neighbor metrics predict each entity's metrics
5. **Counterfactual** — clamp **all metrics** on candidate A to normal (μ ± 2σ flip per metric)
6. **Gibbs sample** — propagate through path; sample symptom metric 5000×
7. **t-test** — compare counterfactual vs true distributions
8. **Rank** — sort significant causes by anomaly score
9. **Explain** — render heavy_hitter → degraded_performance chain


### Scenarios to try


| Scenario                    | Symptom                   | Ridge path (trained) | D1 vs D2 (symptom sample means) | Expected top root cause |
| --------------------------- | ------------------------- | -------------------- | ------------------------------- | ----------------------- |
| Crawler incident (Figure 1) | `backend_vm_1:cpu_usage`  | throughput → latency → cpu | ≈0.25 vs ≈0.77 | `crawler_vm:throughput` |
| Frontend latency symptom    | `frontend_ms:latency_p90` | session_count → latency → cpu | ≈55 vs ≈126 | `crawler_vm:session_count` |
| Idle bystander              | same backend symptom      | (prune demo) | N/A — Gibbs skipped for `normal_vm` | `normal_vm` **not** in candidates |


---


<div class="pagebreak"></div>
## Cheat Sheet


| Term                   | Meaning                                         |
| ---------------------- | ----------------------------------------------- |
| **Symptom**            | Where pain is observed (input to Murphy) — entity **C** |
| **Candidate A**        | Upstream entity under root-cause test (clamped during Gibbs) |
| **B**                  | Middle hop on shortest path A → C (re-sampled from Ridge) |
| **Candidate**          | Upstream entity with some metric beyond 1σ      |
| **Counterfactual**     | Hypothetical "A is normal" metric assignment    |
| **Gibbs**              | W inner re-sweeps of Ridge sampling along A→C, ×5000 outer samples |
| **W**                  | Inner Gibbs iterations per sample (default 4) — re-sample B,C while A stays clamped |
| **D1 / D2**            | Distributions of **symptom metric** at C (counterfactual vs true clamp on A); μ ≈ mean of 5000 samples |
| **Clamp / CLAMPED**    | Lock candidate entity metrics during Gibbs (UI badge); all hot metrics on A, not just one |
| **heavy_hitter**       | Explanation state: entity **sending** abnormal load (source), not the degraded victim |
| **Anomaly score** | max \|z\| over metrics on entity (ranker sort key) |
| **Relationship graph** | Infra topology — cyclic, typed edges            |
| **EntityModel**        | Ridge predictor for one entity-metric pair      |


### Mnemonic: **S → G → P → T → C → G → t → R → E**

**S**ymptom → **G**raph → **P**rune → **T**rain → **C**ounterfactual → **G**ibbs → **t**-test → **R**ank → **E**xplain

---


<div class="pagebreak"></div>
## Simulation

- **Doc:** this file
- **Related:** [Panorama_dissection.md](Panorama_dissection.md) (Tier 1) · [Nezha-dissection.md](Nezha-dissection.md) (Tier 3)
- **Code:** `murphy/` Python package
- **Prototype:** [http://127.0.0.1:8770/#murphy](http://127.0.0.1:8770/#murphy) (unified tabs) or `murphy/murphy-learning-prototype.html` from repo root
- **Service:** `federated-pipeline/deploy/systemd/unified-rca-learning-prototype.service` (port **8770**; legacy per-tool ports 8771/8772 deprecated)
- **Run tests:** `cd murphy && PYTHONPATH=.. .venv/bin/pytest tests/ -v`
- **Run diagnosis:**

```bash
cd /root/Harshil-PoCs/Unified-RCA
PYTHONPATH=. murphy/.venv/bin/python -c "
from murphy import Murphy
from murphy.tests.fixtures.crawler_incident import *
store = build_crawler_incident_store()
murphy = Murphy(monitoring_db=store, parallel=False, n_samples=800)
print(murphy.diagnose(build_crawler_symptom()))
"
```
