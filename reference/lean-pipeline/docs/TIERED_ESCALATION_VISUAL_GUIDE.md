# Lean Tiered Escalation — Sub-step Guide for Visual Simulation

**Purpose:** Explain every Lean diagnosis sub-step clearly enough that you can build a **frame-by-frame visual simulation** for one scenario (e.g. UC-1), without running that simulation here.

**Sibling doc (Federated, same UC-1 scenario):** [`../../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md`](../../federated-pipeline/docs/FEDERATED_PIPELINE_VISUAL_GUIDE.md)  
**Code source of truth:** [`core_engine/observeops/engine.py`](../core_engine/observeops/engine.py) `diagnose()`.  
**Related:** [ARCHITECTURE.md](./ARCHITECTURE.md) · ObserveOps engine [README](../core_engine/observeops/README.md) · product framing [Lean_RCA_PRD.md](../../docs/Lean_RCA_PRD.md).

**Policy (matches the Tiered Escalation poster):**  
*Ration Causal Validity. Do not make it the expensive heartbeat for every simple failure.*

---

## 0. Correct mental model (and one terminology fix)

### Three evidentiary tiers (what the verdict claims)

| Tier | Name | When | Claim strength |
|------|------|------|----------------|
| **1** | Fast / temporal (main path) | Clear onset + rules; CARE did **not** need to rescue | Solid timing / reachability guess. **No causal claim.** Solves most classic incidents. |
| **2** | CARE / ambiguity | Onset Δt is ambiguous → CARE ranks suspects | Stronger **statistical** guess. Still correlational. |
| **3** | Scoped causal check | Only after Tier‑2 path; lean `verify_care_root` passes | **Proven cause-and-effect** *within scoped checks* (topology + onset). |

### Sub-steps vs tiers (important)

Your proposed chain is almost right, with one correction:

```
Tier-1 ingredients:  Best-First (info-gain)  +  Temporal order  +  ObserveOps rules
         │
         ▼  (only if Δt ambiguous)
Tier-2:  CARE severity ranking
         │
         ▼  (only if CARE path ran)
Tier-3:  Lean scoped causal check   ←── NOT Murphy / Gibbs / fleet counterfactuals
```

| You said | Shipping Lean |
|----------|---------------|
| Tier‑3 = “Murphy-like Causal” | **No.** Murphy (MRF + Gibbs) is **Federated**. Lean Tier‑3 is **`verify_care_root`**: topology reachability + onset precedence on the CARE-selected (or shared-upstream) suspect. |

Best-first + info-gain **always run** (walk order, efficiency metrics, candidate list). They do **not** always decide the final `root_ci` — rules (`shared_upstream`) often win on Tier 1 / CARE path.

---

## 1. Scenario inputs (what every visual needs on stage)

Freeze one UC pack as the simulation “set.” Example: **UC-1**.

| Asset | File | Role on stage |
|-------|------|---------------|
| Typed CI graph | `topology.json` | Nodes + **effect→cause** edges (walk **upstream**) |
| Crossed anomalies | `anomalies.json` | Per-CI signals with value, threshold, timestamp |
| Symptom seed | `symptom_seed.json` | Where the search starts (customer-facing CI) |
| Signal registry | `signals.yaml` | Decisive signals + rule thresholds |
| (Eval only) GT | `ground_truth.json` | Scoreboard target — **not** used to pick root |

### UC-1 cast (concrete)

**Seed:** `orders-api` @ `10:00:25Z` (p95 1450 > 1000).

| Time | CI | Signal | Value / thr |
|------|-----|--------|-------------|
| 10:00:05 | `esxi-host-01` | cpu.usage, cpu.ready | 92/85, 12/5 |
| 10:00:12 | `vm-app-01`, `vm-db-01` | cpu.ready | 11/5, 10/5 |
| 10:00:18 | `guest-os-vm-app-01` | load.avg | 8/4 |
| 10:00:25 | `orders-api` | request.p95_latency_ms | 1450/1000 |

**Upstream chain (effect → cause):**  
`orders-api` → `guest-os-vm-app-01` → `vm-app-01` → `esxi-host-01`  
(+ `vm-db-01` also hosted by `esxi-host-01`).

Use this cast for storyboards below; other UCs swap topology + anomalies.

---

## 2. End-to-end flow (one page)

```mermaid
flowchart TD
  load[Load bundle + registry]
  graph[Build InvocationGraph]
  score[Info-gain score_fn per CI]
  bfs[Best-first upstream walk]
  onset[Onset map + rank_by_onset]
  amb{Delta_t ambiguous? window 10s}
  shared[shared_upstream rule]
  t1[Tier 1: root via shared or earliest onset]
  care[Tier 2: CARE severity ranking]
  pick[Pick root: prefer shared else CARE top]
  caus[Tier 3: verify_care_root]
  gate[upstream_healthy gate]
  out[Verdict + SRE report]

  load --> graph --> score --> bfs
  load --> onset
  bfs --> shared
  onset --> amb
  amb -->|no| t1
  amb -->|yes| care --> pick --> caus
  shared --> t1
  shared --> pick
  t1 --> gate
  caus --> gate
  gate --> out
```

**Simulation tip:** Treat each box as a **keyframe**. Do not collapse “search” and “tier claim” into one animation — search can complete while the **claim** stays Tier 1, 2, or 3.

---

## 3. Sub-step A — Invocation graph (stage setup)

**Module:** `lean/invocation_graph.py`  
**Not a tier by itself** — it is the board every later step moves pieces on.

### What it is

Directed graph: edge `from` → `to` means **effect → cause**. Search walks **upstream** (symptom toward infra).

### Inputs / outputs

| In | Out |
|----|-----|
| `topology.nodes`, `topology.edges` | `upstream[ci] = [causes…]`, `node_types` |
| Seed CI | `collect_upstream(seed)` = reachable infra candidates |

### Visual frames

1. Draw all CIs.  
2. Animate arrow direction **app → host** (upstream).  
3. Highlight seed with a “START” badge.  
4. Optional: ghost-draw full upstream closure before search starts.

### Pseudocode

```
for edge in topology.edges:
    upstream[edge.from].append(edge.to)   # effect walks to cause
```

---

## 4. Sub-step B — Information-gain scoring

**Module:** `lean/info_gain.py` · `score_candidate(ci, crossed, onset_times, decisive_signals)`

### What it is

A **priority number** per CI: “how worth expanding is this node?”  
Higher = expand sooner in best-first search. It is **not** the final root by itself.

### Formula (shipping)

```
if CI has no crossed anomalies:  score = −1e12   (almost never expand)

score = 0
if CI has an onset time:
    score += 1000 − (onset.timestamp % 1e6)     # earlier onset → higher
for each crossed anomaly on CI:
    if signal is decisive:  score += 50
    if crossed:             score += min(value/threshold, 10) × 5
```

| Term | Intuition for the visual |
|------|---------------------------|
| Onset bonus (~1000-scale) | “Who broke first?” dominates |
| Decisive +50 | Registry marks this signal as RCA-useful |
| Severity ×5 | How hard the threshold is crossed (capped) |

### Inputs / outputs

| In | Out |
|----|-----|
| Crossed anomalies, onset map, decisive set from `signals.yaml` | `score_fn(ci) → float` consumed by search |

### Visual frames

1. Timeline of onsets under the graph.  
2. For each anomalous CI, stack three chips: **onset**, **decisive**, **severity**.  
3. Show total score badge on the node (e.g. esxi large, seed smaller).  
4. Callout: “Scores rank the **walk**, not yet the verdict.”

### UC-1 intuition (approximate)

- `esxi-host-01` earliest (05s) + two strong signals → **highest**.  
- VMs at 12s medium.  
- Guest / app later → lower onset bonus.

---

## 5. Sub-step C — Best-first traversal

**Module:** `lean/search.py` · `best_first_walk(graph, start, score_fn, max_expansions=50)`

### What it is

**Priority search upstream** from the seed: always expand the **highest-scoring** frontier node next (max-heap), not FIFO BFS.

Also compute:

| Metric | Meaning |
|--------|---------|
| `expansion_order` | Visit sequence for animation |
| `obs_to_convergence` | How many expansions until root appears in the walk |
| `naive_bfs_expansions` | Same root via FIFO BFS (baseline) |
| `efficiency_ratio` | `naive / max(obs, 1)` |

### Inputs / outputs

| In | Out |
|----|-----|
| Graph, seed, `score_fn` | `ranked` candidates (sorted by score), `expansion_order` |

### Algorithm (visual)

```
frontier = max-heap of (score, node); start from seed's upstream neighbors
while frontier and expansions < 50:
    pop highest-scoring node
    record in expansion_order
    push its unscored upstream parents with their scores
finally sort all seen nodes by score descending → ranked
```

### Visual frames

1. Seed pulsing.  
2. Frontier list HUD (heap of CIs + scores).  
3. Each tick: pop top → paint node “expanded” → add parents to frontier.  
4. Sidebar counter: `expansions` vs naive BFS ghost path.  
5. End card: ranked list (esxi first on UC-1).

### Caveat for the script

On UC-1, root is often **chosen by `shared_upstream`**, while best-first still runs for **ordering + efficiency**. Animate both: “search thinks…” vs “rules decide…”.

---

## 6. Sub-step D — Temporal order

**Module:** `lean/temporal.py`

| Function | Role |
|----------|------|
| `onset_by_ci(crossed)` | Earliest timestamp per CI |
| `rank_by_onset(crossed)` | Anomalies sorted earliest → latest |
| `delta_t_ambiguous(onset_times, candidates, window_seconds=10.0)` | **CARE gate** |

### Δt ambiguity gate (exact shipping rule)

```
Take onsets of candidate CIs that have a time.
Need ≥ 2 such CIs.
Sort times ascending.
If (time[1] − time[0]) ≤ 10 seconds  →  AMBIGUOUS = True  → enter CARE path
```

**Nuance:** Only the **two earliest** onsets matter, not “any pair within 10s.”

### Inputs / outputs

| In | Out |
|----|-----|
| Crossed timestamps | Onset map; ambiguity boolean; ordered anomaly list |

### Visual frames

1. Horizontal time ruler with CI dots.  
2. Bracket from earliest to second-earliest; label Δt.  
3. If Δt ≤ 10s: strobe **“AMBIGUOUS → escalate to CARE”**.  
4. If Δt > 10s: green **“CLEAR → Tier‑1 temporal / rules”**.

### UC-1 numbers

- Earliest: `esxi` @ 05s  
- Second: VMs @ 12s  
- **Δt = 7s ≤ 10s → CARE fires** (`fallback_fired=true`).

### Tier‑1 use of temporal (when not ambiguous)

Among search ∩ crossed (or all crossed), pick **earliest onset** CI as root (unless `shared_upstream` already returned a shared infra CI on the clear path).

---

## 7. Sub-step E — ObserveOps rules (Tier‑1 helpers)

Rules sit **beside** search/temporal; they encode classic infra patterns.

### E1 — `shared_upstream` (`rules/shared_upstream.py`)

**Idea:** If ≥2 VMs show the same contention signal, blame the **shared host** (or datastore for storage signals).

| Pattern | Shipping config (`signals.yaml`) |
|---------|----------------------------------|
| CPU | ≥2 `vm-*` with `cpu.ready` → first `esxi-*` in candidates |
| Storage | crossed latency / iowait → `datastore-*` |

**UC-1:** `vm-app-01` + `vm-db-01` both `cpu.ready` → **`esxi-host-01`**.

**Visual:** Two VM nodes flash same signal → magnet pull to host.

### E2 — `upstream_healthy` (`rules/upstream_healthy.py`)

**Idea (UC-5):** If infra is clean and the seed is app-layer, **do not** walk blame upstream to host — keep root at app.

**Visual:** Host stays grey (no crossed infra) → root badge sticks on `orders-*`.

### E3 — Signature / contributors (post-root)

`infer_signature(crossed)`, datastore contributor — enrich the report; not the tier ladder itself.

---

## 8. Sub-step F — CARE (Tier 2)

**Module:** `lean/care.py` · `care_fallback_candidates(crossed, candidates, window_seconds=10.0)`

### When it runs

Only if `delta_t_ambiguous` is **True**. Sets `fallback_fired=True`, `evidentiary_tier=2` (until Tier‑3 upgrades it).

### What it computes (PoC)

**Not** full PRD spectrum + PageRank. Shipping PoC:

```
if not ambiguous: return None
for each CI:
    severity[CI] = Σ (value / threshold) over that CI's crossed anomalies
return CIs sorted by severity descending
```

### Root pick on CARE path (`diagnose`)

```
prefer shared_upstream CI if it is in crossed
else CARE ranked[0]
else best-first #0 / earliest onset
```

So CARE is the **ambiguity resolver**, but shared-upstream can still override the severity winner.

### Visual frames

1. Ambiguity banner from §6.  
2. Bar chart of severity per CI (UC-1: esxi highest ≈ 92/85 + 12/5).  
3. Crown temporary “CARE suspect”.  
4. If shared-upstream agrees, morph crown to host with label **“rule + CARE path”**.  
5. Caption: **“Stronger statistical guess — not yet proven cause.”**

---

## 9. Sub-step G — Scoped causal check (Tier 3)

**Module:** `lean/causal.py` · `verify_care_root(graph, seed_ci, root_ci, crossed)`

### When it runs

**Only** on the CARE path (Tier 2). Never on a clean Tier‑1 exit.

### What it is / is not

| Is | Is not |
|----|--------|
| Lean **scoped** check after CARE | Murphy Gibbs / MRF |
| Topology + onset **plausibility** | Fleet-wide do-calculus |
| Raises claim to Tier **3** if all checks pass | Automatic for every ticket |

Poster question (*“If suspect were healthy, would the problem go away?”*) is the **design intent**; the PoC implements a **lightweight stand-in**: “Is this suspect anomalous, upstream of the seed, and temporally before connected symptoms?”

### Checks (all must support a pass)

1. **`root_anomalous`** — root has an onset (it is actually sick).  
2. **`topology_upstream_of_seed`** — walking upstream from seed **reaches** root.  
3. **`onset_precedes_connected_symptoms`** — for every other anomalous CI that can reach this root upstream, `root_onset ≤ that_ci.onset`.  
4. Pass requires **at least one connected downstream symptom** *and* temporal OK. If nothing downstream is anomalous, verification **fails** → stay Tier 2.

### Inputs / outputs

| In | Out |
|----|-----|
| Graph, seed, proposed root, crossed | `(causal_verified: bool, causal_log: list[dict])` |
| If verified | `evidentiary_tier = 3` |

### Visual frames

1. Dim whole graph; spotlight seed → … → suspect path.  
2. Checklist ticks for the three checks (animate each).  
3. Downstream symptom nodes light up in onset order.  
4. Final stamp: **Tier 3 — proven C&E (scoped)** or **Tier 2 — CARE only**.

### UC-1 outcome (current engine)

CARE fires (Δt=7s) → root `esxi-host-01` via shared_upstream → `verify_care_root` passes → **`evidentiary_tier=3`**, `causal_verified=true`.

---

## 10. How tiers compose (decision table for animators)

| Condition | Path | Typical root picker | Final tier |
|-----------|------|---------------------|------------|
| No crossed anomalies | Degenerate | Seed | 1 |
| Clear Δt **and** shared_upstream hits | Main | shared_upstream | **1** |
| Clear Δt, no shared | Main | Earliest onset ∩ search | **1** |
| Ambiguous Δt | CARE | shared if present else CARE severity | **2**, then **3** if verify passes |
| After any root | Gate | `upstream_healthy` may force app seed (UC-5) | Unchanged tier number unless you re-label in UI |

```
            ┌─────────────────────────────┐
            │ Tier 1  Fast / temporal     │  ← default; no causal claim
            └──────────────┬──────────────┘
                           │ only if Δt ≤ 10s (ambiguous)
                           ▼
            ┌─────────────────────────────┐
            │ Tier 2  CARE                │  ← statistical
            └──────────────┬──────────────┘
                           │ only if CARE path ran
                           ▼
            ┌─────────────────────────────┐
            │ Tier 3  Scoped causal check │  ← claim causal validity
            └─────────────────────────────┘
```

---

## 11. Recommended simulation chapter list (one scenario)

Use these as **slides / scenes**. Each scene = one HUD + one graph state.

| # | Scene title | Sub-steps on screen | Succeeds when viewer sees… |
|---|-------------|---------------------|----------------------------|
| 0 | Freeze the incident | Graph + seed + anomaly table | “This is the corpus pack” |
| 1 | Orient upstream | Graph edges effect→cause | Walk direction toward infra |
| 2 | Score the nodes | Info-gain breakdown | Why esxi outranks app |
| 3 | Walk best-first | Heap + expansion_order | Search ≠ verdict (optional callout) |
| 4 | Lay the timeline | Temporal ruler | Δt vs 10s window |
| 5a | **Clear path** (alt UC) | Tier 1 banner | Rules / earliest root, stop |
| 5b | **Ambiguous** (UC-1) | CARE bars | Severity ranking |
| 6 | Shared-upstream magnet | Rule overlay | Two VMs → one host |
| 7 | Causal checklist | Tier 3 stamps | Pass → Tier 3 / fail → Tier 2 |
| 8 | Healthy-upstream gate | UC-5 cutscene | App kept when infra clean |
| 9 | Verdict card | tier, root, fallback, efficiency | Matches bakeoff fields |

**Efficiency epilogue (optional scene):** Ghost naive BFS vs best-first expansion counts (`obs_to_convergence`, `efficiency_ratio`).

---

## 12. Data contract for a visual tool

Minimum state object to drive UI (mirrors verdict + intermediates):

```json
{
  "uc_id": "UC-1",
  "seed_ci": "orders-api",
  "nodes": [{"id": "...", "type": "..."}],
  "edges": [{"from": "...", "to": "...", "relation": "..."}],
  "anomalies": [{"ci": "...", "signal": "...", "value": 0, "threshold": 0, "timestamp": "...", "crossed": true}],
  "onset_by_ci": {"esxi-host-01": "2026-07-10T10:00:05Z"},
  "scores": {"esxi-host-01": 1234.5},
  "expansion_order": ["guest-os-vm-app-01", "vm-app-01", "esxi-host-01"],
  "delta_t_seconds": 7.0,
  "ambiguous": true,
  "shared_upstream": "esxi-host-01",
  "care_ranked": ["esxi-host-01", "vm-app-01", "..."],
  "root_ci": "esxi-host-01",
  "evidentiary_tier": 3,
  "fallback_fired": true,
  "causal_verified": true,
  "causal_log": [{"check": "root_anomalous", "passed": true}],
  "obs_to_convergence": 3,
  "naive_bfs_expansions": 3,
  "efficiency_ratio": 1.0
}
```

Hook: run `diagnose(uc_id, corpus)` and/or unit-test the pure functions (`score_candidate`, `best_first_walk`, `delta_t_ambiguous`, `care_fallback_candidates`, `verify_care_root`) to fill this JSON per frame — **outside** this document’s scope.

---

## 13. One-line cheat sheet

| Sub-step | One line |
|----------|----------|
| **Graph** | Effect→cause board; walk upstream from seed. |
| **Info-gain** | Score = onset primacy + decisive + severity. |
| **Best-first** | Expand highest score next; records search cost. |
| **Temporal** | Who broke first; Δt≤10s opens CARE. |
| **shared_upstream** | Many VMs same signal → shared host/datastore. |
| **CARE** | Ambiguity → severity-ranked statistical suspect. |
| **Causal (Tier 3)** | Lean scoped verify (topology+onset), **not** Murphy. |
| **upstream_healthy** | Clean infra → keep app root (anti-FP). |

---

## 14. Pointers in code

| Concern | Path |
|---------|------|
| Orchestration / tier assignment | `lean-pipeline/core_engine/observeops/engine.py` |
| Best-first + BFS baseline | `lean-pipeline/core_engine/lean/search.py` |
| Info-gain | `lean-pipeline/core_engine/lean/info_gain.py` |
| Temporal / Δt | `lean-pipeline/core_engine/lean/temporal.py` |
| CARE | `lean-pipeline/core_engine/lean/care.py` |
| Tier‑3 verify | `lean-pipeline/core_engine/lean/causal.py` |
| Graph | `lean-pipeline/core_engine/lean/invocation_graph.py` |
| Rules | `lean-pipeline/core_engine/observeops/rules/` |
| Registry / decisive | `lean-pipeline/core_engine/observeops/signals.yaml` |
| Example pack | `datasets/observeops/UC-1/` |
