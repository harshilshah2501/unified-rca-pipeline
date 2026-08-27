# ObserveOps Use-Cases — Learning & Brainstorm Guide

**Purpose:** Reframe UC-1..UC-5 and UC-3b for learning and brainstorming — not a bakeoff contract.  
**Canonical eval / GT:** [`rca-use-cases-only.md`](../rca-use-cases-only.md). Prefer that file for Accuracy scoring and corpus freeze.

**Stack (shared):** Network → ESXi Host → VM → Guest OS → App (+ shared Datastore).  
**CI** = Configuration Item (inventory id: host, switch port, datastore, VM, OS, app).

### How to read each UC (deduction loop)

1. **Problem** — What hurt the user, and what wrong blame is tempting?  
2. **Fault & injection** — What actually broke, and how would you inject it?  
3. **Telemetry** — Which counters / thresholds light up where?  
4. **Events** — Which log/trap lines reinforce metrics (when events channel ships)?  
5. **Symptoms per layer** — What each owner sees vs reality.  
6. **Correlation logic** — Deduction: why shared upstream / signature wins.  
7. **Auto RCA output** — Root, signature, contributor, chain, blast radius, fix hints.  
8. **Lean approach** — How ObserveOps’ primary evaluation engine (lean) would get there.  
9. **Federated approach** — How Panorama → Murphy → Nezha (+ ObserveOps bakeoff adapters) would get there.

---

## Two engines, same story — mental model

Both engines get the **same frozen UC bundles** in the ObserveOps bakeoff. They answer the same question (“what is `root_ci` / `signature`?”) with different brains.

| | **Lean** (primary evaluation engine) | **Federated** (optional / bakeoff comparator) |
|--|------------------------------|-----------------------------------------------|
| Core idea | One typed CI graph *is* the reasoner | Three papers glued by an orchestrator |
| Typical path | Best-first upstream walk → temporal / ObserveOps rules → optional CARE → signature | Simulated detection flag → Murphy MRF/Gibbs posterior → optional Nezha → fusion |
| ObserveOps “secret sauce” | `shared_upstream`, signatures, contributors, `upstream_healthy`, structured events | Same ObserveOps helpers used in fusion / **fallback** when Murphy is weak |
| Natural strength | Classic infra tickets; bit-stable; auditable tiers | Microservice gray-failure + code-path (Nezha); Murphy CV when funded |
| On this corpus | Usually Tier 1, or CARE→Tier 3 when onsets clump | Often accurate; less reproducible (~40% vs lean 100% in matched bakeoffs) |

### Typed CI graph

**CI** = Configuration Item — a durable inventory object ObserveOps monitors (host, switch port, datastore, VM, guest OS, app).

A **typed CI graph** is a map of those objects as nodes, with **typed** meaning:

1. Every node has a **kind** — e.g. `HypervisorHost`, `Datastore`, `VirtualMachine`, `NetworkPort`, `GuestOS`, `Service`  
2. Every edge has a **relation** — e.g. `runs_on`, `hosted_by`, `stored_on`, `uplink_to`  

So it’s not a free-form call graph or “blob of metrics.” It’s:

```text
orders-api  --runs_on-->  guest-os  --hosted_by-->  vm-app
                                              |
                                    hosted_by / stored_on
                                              |
                                         esxi-host / datastore
                                              |
                                         switch port
```

**Why “typed” matters for RCA**

- Rules can say: “≥2 VMs with CPU Ready → blame the **HypervisorHost**,” or “storage latency → blame the **Datastore**.”  
- Walks know which direction is **upstream** (toward shared infra) vs symptom.  
- Different from a microservice “who called whom” graph (pods/services); ObserveOps ObserveOps uses long-lived inventory CIs.

Edges mean “related in inventory / dependency,” **not** “proven cause.” Causation is claimed separately (rules / Tier 3), not by the edge alone.

---

### Best-first upstream walk vs Breadth-first search (BFS)

Both start at the **symptom** (e.g. `orders-api`) and walk **upstream** along the typed edges (effect → cause). They differ in **which neighbor to expand next**.

| | **Breadth-first (BFS)** | **Best-first (info-gain walk)** |
|--|------------------------|----------------------------------|
| Queue style | FIFO — expand in discovery order | Priority — expand highest-scoring CI first |
| Order | “Nearby” layers first, equally | “Most informative” CI first |
| Score | None (or weak) | Info-gain: crossed anomaly? earlier onset? decisive signal? severity? |
| Purpose | Discover all reachable upstream CIs fairly | Reach a likely root with **fewer observations** |
| In this PoC | `collect_upstream` / `naive_bfs_expansions` (baseline) | `best_first_walk` (lean main search) |

**BFS intuition:**  
Check apartment → floor → building → street in even rings. Methodical; may inspect many low-value nodes before the real fire.

**Best-first intuition:**  
Same building map, but first open the door that’s already smoke-filled and highly scored. Still explores the graph; order follows **score**, not “next in line.”

In lean’s PRD language: the frontier is still a BFS-style discovery of neighbors — but once you rank the frontier by expected information gain, the traversal becomes **best-first over that frontier**, not strict FIFO BFS.

**Concrete toy**

Symptoms at App. Upstream candidates: GuestOS (quiet), VM (quiet), Host (high Ready), Switch (quiet).

- **BFS:** might expand GuestOS → VM → Host in layer order.  
- **Best-first:** may expand **Host** first because `cpu.ready` / decisive signals score highest.

Both can still find the same root; best-first aims to get there with a shorter expansion path (efficiency), while ObserveOps **rules** (shared-upstream, etc.) still decide the final `root_ci` when signatures apply.

```text
Symptom seed (usually orders-api)
        │
        ├────────────── lean ──────────────► walk typed graph + rules + CARE?
        │
        └────────── federated ─────────────► flag → Murphy posterior → Nezha?
                                              └─ ObserveOps fusion / lean-rule fallback if needed
```

**Honest ObserveOps note:** On classic infra UC-1..UC-5 both engines often land the **same correct root**. The teaching value is *how* they get there — and where each can still go wrong without ObserveOps rules (especially UC-3b).

Deeper architecture: [`../lean-pipeline/docs/ARCHITECTURE.md`](../lean-pipeline/docs/ARCHITECTURE.md) · [`../federated-pipeline/docs/ARCHITECTURE.md`](../federated-pipeline/docs/ARCHITECTURE.md).

---

## Map at a glance

| UC | Root layer | Tempting wrong answer | Correct root (CI) | Signature | Lean feel | Federated feel |
|----|------------|----------------------|-------------------|-----------|-----------|----------------|
| UC-1 | Host CPU | Blame app / one VM | `esxi-host-01` | `cpu_contention` | Shared-upstream + often CARE→Tier 3 | Murphy tends to host; stable in bakeoff |
| UC-2 | Network | Blame app / server | `switch-core-01:GigE0/2` | `link_failure` | Clear link / events; usually Tier 1 | Can be accurate but repro weaker |
| UC-3 | Storage | Blame slow DB/app | `datastore-01` | `storage_contention` | Shared-upstream + contributor; CARE→Tier 3 | Murphy + fusion; sometimes fewer obs |
| UC-3b | Storage + early noise | Blame earliest CI (switch) | still `datastore-01` | `storage_contention` | CARE fires; **shared beats earliest** | Needs ObserveOps fusion — naïve earliest fails |
| UC-4 | Guest OS | Blame app code | `guest-os-vm-app-01` | `os_resource_exhaustion` | Stop at OS + events; Tier 1 | Posterior / heuristics land OS |
| UC-5 | Application | Blame healthy infra | `orders-api` | `app_resource_exhaustion` | `upstream_healthy` gate | Must not invent infra; gate / fusion |

---

## UC-1 — Host CPU contention

### Problem
Orders API is slow. Guest CPU looks busy, but work is stalling. Easy to blame the app or “my VM is at 100%.”

### Fault & injection
`esxi-host-01` is overcommitted: more vCPU demand than physical cores.  
*Inject:* `stress-ng --cpu` on several co-located VMs, or power on extra CPU-heavy VMs.

### Telemetry signals & thresholds

| Layer | CI | Signal | Rough fire |
|-------|-----|--------|------------|
| Host | `esxi-host-01` | `cpu.usage` | > ~85–90% sustained |
| Host / VMs | host or `vm-*` | `cpu.ready` | > ~5% per vCPU (10%+ severe) |
| VMs | `vm-*` | `cpu.costop` (SMP) | > ~3–5% |
| OS | guest | load / run-queue | > #vCPU |
| App | `orders-api` | p95 latency | SLO breach |

### Events
Optional (metrics-dominant). None required for primary bakeoff thinking.

### Symptoms per layer

| Who | Sees |
|-----|------|
| App owner | Slow API; VM CPU ~100% but low throughput |
| Reality | VMs waiting for a core (high CPU Ready). Guest CPU% is misleading |

### Correlation logic (deduction)
Several VMs hurt the same way → look for **shared upstream** → host.  
Host high `cpu.usage` **and** high `cpu.ready` across ≥2 VMs → host is starving them → **`cpu_contention`**.  
Do not stop at the app CI.

### Auto RCA output
- **Root:** `esxi-host-01`  
- **Signature:** `cpu_contention`  
- **Contributor:** none  
- **Chain:** host → VMs → OS → apps  
- **Blast radius:** every VM/app on that host  
- **Remediation hints:** vMotion / rebalance, check DRS, find runaway VM, right-size vCPUs  

### How lean approaches UC-1

1. Seed from symptom (`orders-api`); build typed graph; collect upstream CIs.  
2. Best-first walk scores candidates that crossed (host Ready/usage, VM Ready, app latency).  
3. **`shared_upstream`**: ≥2 VMs with `cpu.ready` → prefer `esxi-host-01`.  
4. Onsets often clump within Δt → **CARE** (Tier 2); scoped causal check can promote **Tier 3**.  
5. `infer_signature` → `cpu_contention`.  
6. SRE report: chain / blast radius / remediations from signature table.

**Without ObserveOps shared-upstream:** might crown an early VM or the app if you only followed “earliest/most severe symptom.” Shared rule is the teaching point.

### How federated approaches UC-1

1. Bundle → **SimulatedMetricStore** with CPU propagation (host usage elevates VM Ready, etc.).  
2. Build a **DetectionFlag** from the symptom seed (Panorama adapter in “simulated” mode for ObserveOps — not live multi-observer LOS).  
3. Orchestrator → **Murphy** Gibbs: entities with high Ready/usage around the host bubble up in the posterior.  
4. Nezha may be invoked if posterior is confident, but **root CI for ObserveOps** is mainly Murphy fusion (code-path mining does little on classic host CPU).  
5. If posterior is weak: bakeoff **`resolve_root_ci`** can fall back to lean-style shared-upstream / temporal heuristics.

**Teaching contrast:** Federated *reasons* via metric dependency / MRF; lean *walks* inventory and applies ObserveOps host rules. Bakeoff often: both pick `esxi-host-01`; lean more often labels Tier 3 when CARE fires.

---

## UC-2 — Network uplink / link failure

### Problem
App looks flaky — timeouts, latency, failed requests. Easy to blame the app or the server OS.

### Fault & injection
Uplink between host and `switch-core-01` is down or saturated.  
*Inject:* admin-down the port, iperf flood, or disable one NIC so redundancy collapses.

### Telemetry signals & thresholds

| Layer | CI | Signal | Rough fire |
|-------|-----|--------|------------|
| Network | switch port | linkDown / `ifOperStatus=down` | immediate |
| Network | switch port | errors / discards | > 0 rising |
| Network | switch port | utilization | > ~90% sustained |
| Host | `esxi-host-01` | vmnic drops / link state | drops or down |
| OS / App | VMs, app | TCP retransmits, timeouts | rising |

### Events (required once events channel ships)

| CI | event_type | Example |
|----|------------|---------|
| `switch-core-01:GigE0/2` | `snmp.linkDown` | SNMP trap: GigE0/2 operStatus down |
| `switch-core-01:GigE0/2` | `snmp.ifOutDiscards` (optional) | discards rising |

Cite event **message** in evidence when present.

### Symptoms per layer

| Who | Sees |
|-----|------|
| App owner | Intermittent timeouts — “app is flaky” |
| Reality | Packet loss / saturation on the shared uplink; many VMs hurt alike |

### Correlation logic (deduction)
Hard fault on the **port** that feeds the host.  
Topology: port → host → all VMs/apps. Shared network upstream explains identical multi-VM symptoms.  
`linkDown` **or** (util >90% **and** discards) → **`link_failure`**.

### Auto RCA output
- **Root:** `switch-core-01:GigE0/2`  
- **Signature:** `link_failure`  
- **Contributor:** none  
- **Chain:** port → host uplink → VMs → apps  
- **Blast radius:** all VMs/apps behind that uplink  
- **Remediation hints:** restore/replace link, check NIC teaming / redundant uplink, find traffic spike  

### How lean approaches UC-2

1. Walk from app toward network along `uplink_to`.  
2. Decisive crossed signals (linkDown / util∩discards) on the port — often a **clear Tier 1** winner (shared-upstream CPU/storage rules may not fire).  
3. Signature `link_failure`; merge **`events.json`** (SNMP trap text) into evidence.  
4. Remediations from `link_failure` table.

**Teaching point:** Events strengthen verifiability (“here is the trap line”), not a second root channel.

### How federated approaches UC-2

1. Propagation rules inject network→host drops→TCP→app latency into the simulated store.  
2. Murphy posterior should favor the switch port / NIC entity once cross-layer metrics align.  
3. Classic Panorama strength (observer gray failure) is only lightly simulated here — ObserveOps path is not “full OSDI Panorama on switches.”  
4. Nezha does not mine SNMP free text; ObserveOps uses lean’s structured events for traps on the lean side.  
5. Bakeoff history: accuracy can match GT, but **reproducibility** is weaker (Gibbs / path variance) than lean’s bit-stable Walk.

**Teaching contrast:** Lean treats linkDown as a hard inventory + signal rule. Federated must rediscover the same story through sampled causal posteriors — powerful in theory, noisier as a ObserveOps default.

---

## UC-3 — Shared datastore / noisy neighbor

### Problem
Database and Orders API feel slow. Easy to blame the DB or the app.

### Fault & injection
Shared `datastore-01` is latency-bound because another VM floods I/O.  
*Inject:* heavy `fio` / `dd` inside `vm-neighbor-01` on the same datastore as `vm-db-01`.

### Telemetry signals & thresholds

| Layer | CI | Signal | Rough fire |
|-------|-----|--------|------------|
| Storage | `datastore-01` | **GAVG** (`gavg_latency_ms`) — total/guest path latency | > ~20–30 ms (severe >50) |
| Storage | `datastore-01` | **DAVG** (`davg_latency_ms`) — device/array side | > ~20 ms |
| VM | `vm-db-01` | `virtualDisk.totalLatency` | > ~20–30 ms |
| OS | DB guest | await / iowait | high |
| App | DB / Orders | query time, p95 | SLO breach |
| Neighbor | `vm-neighbor-01` | high IOPS (contributor clue) | elevated |

**GAVG** ≈ how slow disk feels to guests. **DAVG** ≈ latency on the backing device.

### Events
Optional for primary UC-3 (neighbor IOPS can stay metric-only).

### Symptoms per layer

| Who | Sees |
|-----|------|
| App / DB owner | “DB is slow / timing out” |
| Reality | Shared datastore congested; DB VM is a **victim**; neighbor is the **load source** |

### Correlation logic (deduction)
App + DB disk pain → walk to shared storage.  
Datastore GAVG/DAVG high **and** sibling VM driving IOPS →  
- **root** = datastore (shared bottleneck)  
- **contributor** = noisy-neighbor VM  
Signature: **`storage_contention`**. Do not crown the DB app.

### Auto RCA output
- **Root:** `datastore-01`  
- **Signature:** `storage_contention`  
- **Contributor:** `vm-neighbor-01`  
- **Chain:** datastore → DB VM disk → OS iowait → queries → app  
- **Blast radius:** VMs on that datastore  
- **Remediation hints:** Storage vMotion noisy VM or DB; SIOC / I/O limits; check backing array  

### How lean approaches UC-3

1. Shared-storage pain across VMs → **`shared_upstream`** targets `datastore-`.  
2. `datastore_contributor` lists `vm-neighbor-01` from neighbor IOPS signal.  
3. Onsets often ambiguous → CARE + prefer shared datastore → often **Tier 3**.  
4. Signature `storage_contention`. Explicitly **not** “Batch VM started I/O first ⇒ Batch is root.”

**Teaching point:** Lean separates **root (shared bottle)** from **contributor (who pushed load)**.

### How federated approaches UC-3

1. Simulated store includes **noisy-neighbor rules**: neighbor IOPS elevates datastore GAVG/DAVG, which elevates victim VM disk latency → app.  
2. Murphy’s MRF is a good fit *in spirit* (shared storage + cyclic-ish effects) — posterior can peak on `datastore-01`.  
3. Fusion may prefer upstream among high-posterior candidates (ObserveOps-aware).  
4. Bakeoff: sometimes federated uses **fewer raw observations** while accuracy still matches lean — Murphy can “short-cut,” while lean may spend budget reaching Tier 3.  
5. Contributor naming is a ObserveOps/lean-native field; federated bakeoff maps to the same GT via ObserveOps scoring helpers.

**Teaching contrast:** Federated can *discover* shared-storage causality statistically; lean *encodes* the ObserveOps pattern as inventory rules + contributor. On this corpus both can be correct; lean remains preferable for reproducible SRE reports.

---

## UC-3b — Same storage story + early unrelated switch noise

### Problem
Same user pain as UC-3. An **earlier** switch blip tempts “who got sick first wins.”

### Fault & injection
Same as UC-3 **plus** a brief, **non-causal** switch anomaly a few seconds earlier (e.g. high util — **not** a real linkDown that should be root).

### Telemetry signals & thresholds
All UC-3 crossed storage signals **plus** early network noise on `switch-core-01:GigE0/2` within a short Δt window.

### Events
Optional early switch util / syslog noise — must **not** override storage root.

### Symptoms per layer

| Who | Sees |
|-----|------|
| App owner | Same as UC-3 (DB/app slow) |
| Reality | Storage still causal; network noise is concurrent **confound** |

### Correlation logic (deduction)
Naïve rule: earliest abnormal CI → switch. **Wrong.**  
Correct: shared-upstream + storage signature still pick **`datastore-01`**; neighbor still contributor.  
Switch may appear in evidence as noise, not root.  
*Lesson:* onset timing is a **clue**, not the verdict.

### Auto RCA output
Same as UC-3. Report should note concurrent network anomaly, non-causal for this incident.

### How lean approaches UC-3b

1. Δt ambiguity **fires CARE** because switch and storage onsets are close.  
2. Critical ObserveOps policy: under ambiguity, **prefer `shared_upstream` datastore** over CARE severity / earliest CI.  
3. Root stays `datastore-01`; contributor stays neighbor; switch stays in evidence as concurrent noise.  
4. Often Tier 3 after `verify_care_root`.

**This is the flagship lean ObserveOps lesson.** Temporal-only lean *would fail*; ObserveOps rules salvage it.

### How federated approaches UC-3b

1. Synthetic store still has storage causality; switch noise is an extra early metric.  
2. Pure “earliest entity” or a weak posterior can drift to the switch.  
3. ObserveOps bakeoff path needs **fusion / shared-upstream preference / resolve_root_ci** to stay on datastore — same ObserveOps idea, bolted after Murphy.  
4. Nezha does not resolve this classic-infra confound (no helpful code-path pattern).

**Teaching contrast:** UC-3b punishes “earliest abnormal” engines. Lean fails closed into ObserveOps shared-upstream; federated must not trust Gibbs alone without ObserveOps post-fusion. Primary bakeoff is still UC-1..UC-5; UC-3b is the adversarial teaching / lean-regression fixture.

---

## UC-4 — Guest OS resource exhaustion

### Problem
App throws write errors, crashes, or 500s. Easy to blame application code.

### Fault & injection
Break the **OS**, not the app.  
*Inject:* fill filesystem (`fallocate` / `dd`), runaway process, or force OOM-killer.

### Telemetry signals & thresholds

| Layer | CI | Signal | Rough fire |
|-------|-----|--------|------------|
| OS | guest OS | filesystem used % | > ~90% (critical ~95–100%) |
| OS | guest OS | low memory / swap | scarcity |
| OS | guest OS | OOM / runaway process | present |
| OS | guest OS | service state | down |
| App | app | health / 5xx / down | failing |
| Below OS | VM / host / net | — | **healthy** |

### Events (required once events channel ships)

At least one of:

| CI | event_type | Example |
|----|------------|---------|
| `guest-os-vm-app-01` | `syslog.oom_killer` | OOM killed orders-api |
| `guest-os-vm-app-01` | `syslog.filesystem_full` | No space left on device |
| `guest-os-vm-app-01` | `process.runaway` (optional) | top offender stress-ng |

Cite **message** in evidence.

### Symptoms per layer

| Who | Sees |
|-----|------|
| App owner | Write errors / crash / 500s |
| Reality | Disk full, OOM, or runaway process on the guest OS |

### Correlation logic (deduction)
App failing → immediate upstream OS shows decisive resource fault → stop at OS.  
Infra below OS healthy → not host/network.  
Signature: app errors **and** (fs full **or** OOM **or** runaway) → **`os_resource_exhaustion`**.

### Auto RCA output
- **Root:** `guest-os-vm-app-01`  
- **Signature:** `os_resource_exhaustion`  
- **Contributor:** none  
- **Blast radius:** app(s) on **this** OS only (narrower than UC-1 host blast)  
- **Remediation hints:** free/extend disk; kill/limit runaway; add memory / fix leak; restart service  

### How lean approaches UC-4

1. Seed at app; walk one hop to guest OS; OS metrics/events decisive.  
2. Layers below marked healthy → walk **stops** (narrow blast radius vs UC-1).  
3. Usually **Tier 1** (no CARE needed).  
4. Evidence must cite **event message** when present (OOM / fs full).  
5. Signature `os_resource_exhaustion`.

**Teaching point:** Same app symptoms as UC-5, but OS layer has a hard fault — localization stops one layer up.

### How federated approaches UC-4

1. Simulated store keeps host/datastore/network healthy; OS/resource metrics on the guest / container-mapped entity are abnormal.  
2. Murphy posterior should peak near the guest-OS entity (ObserveOps maps GuestOS into Murphy’s type map).  
3. Nezha *could* shine on free-text OS logs in a microservice track; ObserveOps PoC uses **structured events** instead — lean cites them; federated ObserveOps root still mainly Murphy/fusion.  
4. Bakeoff: lean often wins observation-efficiency on this simple stop-at-OS path.

**Teaching contrast:** Federated’s Nezha paper strength (log/event patterns) is underused on ObserveOps UC-4; lean covers the gap with `events.json` without Drain mining.

---

## UC-5 — Application exhaustion (do not blame healthy infra)

### Problem
Latency and errors climb. Temptation: finger-point host, storage, or network “just in case.”

### Fault & injection
Real **app-tier** fault; everything below is fine.  
*Inject:* exhaust JVM heap / GC thrash, saturate DB connection pool, or exhaust thread pool.

### Telemetry signals & thresholds

| Layer | CI | Signal | Rough fire |
|-------|-----|--------|------------|
| App | `orders-api` | heap % / GC | heap > ~90%, bad GC |
| App | `orders-api` | pool active/max | ≈ 100% |
| App | `orders-api` | p95 / 5xx | SLO breach |
| OS / Host / Net / Storage | upstream | — | **normal** (decisive) |

### Events
Optional (e.g. GC log line). Not required for primary thinking.

### Symptoms per layer

| Who | Sees |
|-----|------|
| App owner | Latency + errors |
| Reality | App itself (heap / pool); infra clean |

### Correlation logic (deduction)
App pain → walk upstream → **no causal infra anomaly** → terminate at app.  
Signature: app latency/errors **and** (heap/pool bad) **and** upstream healthy → **`app_resource_exhaustion`**.  
Anti-false-positive: do not invent infra blame.

### Auto RCA output
- **Root:** `orders-api`  
- **Signature:** `app_resource_exhaustion`  
- **Contributor:** none  
- **Evidence note:** upstream infra verified healthy  
- **Blast radius:** this service (+ consumers), not the whole host  
- **Remediation hints:** raise heap / fix leak; tune pools; autoscale; check slow downstream deps  

### How lean approaches UC-5

1. Crossed anomalies mostly/only on app.  
2. **`upstream_healthy.gate`**: if infra not crossed (or GT `upstream_healthy`), keep root at symptom/app seed.  
3. Signature `app_resource_exhaustion`. Tier 1. Blast radius restricted to Service-style root.  
4. Fail condition for bakeoff: any infra root when upstream is healthy.

**Teaching point:** Lean must know when **not** to roll up.

### How federated approaches UC-5

1. Simulated store keeps infra metrics healthy; app heap/pool anomalies present.  
2. Murphy should *not* invent a strong infra cause — posterior should stay on the app / microservice entity.  
3. Same ObserveOps **`upstream_healthy`** helper can force / check the anti-FP outcome in bakeoff resolution.  
4. Historical bakeoff: accuracy can match, reproducibility weaker than lean.

**Teaching contrast:** Both need an explicit “infra is clean → stay at app” gate. Federated’s hunger for *some* causal entity is the risk mode; ObserveOps fusion must refuse false infra blame.

---

## Side-by-side cheat sheet (brainstorm)

| UC | Lean “winning move” | Federated “winning move” | Shared ObserveOps trap if skipped |
|----|---------------------|--------------------------|----------------------------------|
| UC-1 | Shared-upstream host + Ready | Murphy links host Ready ↔ VM Ready | Blame one VM |
| UC-2 | Port linkDown / util+discards + events | Posterior on network entity | Blame app for timeouts |
| UC-3 | Shared datastore + **contributor** | Propagation noisy-neighbor → datastore | Blame DB |
| UC-3b | CARE **but prefer shared** over earliest | Fusion must ignore early switch | Earliest = switch |
| UC-4 | Stop at OS + event message | Posterior on guest OS; don’t roll to host | Blame app code |
| UC-5 | `upstream_healthy` gate | Don’t invent infra posterior | Blame host/store |

---

## Live-incident comparative track (29 OpenObserve incidents)

Beyond UC-1..UC-5, a frozen snapshot of **29** platform incidents is evaluated with
lean- vs federated-**principle** analyzers (alert topology substrate — not the
VMware typed CI freeze):

- Corpus: [`../datasets/openobserve_incidents/`](../datasets/openobserve_incidents/)
- Report: [`../benchmarking/results/openobserve/COMPARISON.md`](../benchmarking/results/openobserve/COMPARISON.md)
- Runner: `python3 benchmarking/benchmark/compare_openobserve.py`

Use that report for directional insight on decoys, multi-alert correlation, and
reproducibility; keep the 5 UC bakeoff for classic typed-CI Accuracy.

## Brainstorm prompts (use freely)

1. Swap layers — what if UC-1 host Ready is missing but two VMs still scream? What evidence do you need (lean vs Murphy)?  
2. UC-3 without neighbor IOPS — can GAVG alone + multi-VM disk latency still justify storage root?  
3. UC-3b with *real* linkDown — when **should** network win, and how do lean/federated avoid teaching the wrong lesson?  
4. UC-4 filesystem-full vs OOM — same signature, different remediation: subtypes? Who owns that — signature table or events?  
5. UC-5 with one slightly crossed host metric (noise) — same trap as UC-3b; which ObserveOps rule holds the line for each engine?  
6. Where should **contributor_cis** expand (UC-1 runaway VM as contributor, not root)? Does Murphy posterior express “contributor” or only “root”?  
7. If ObserveOps funded a microservice corpus next year, which UCs would *flip* (federated Nezha suddenly relevant)?  
8. Draw the evidence trail an SRE must see for Tier 1 vs Tier 3 on UC-1 — what is missing from a Murphy-only PDF dump?

---

## Quick glossary

| Term | Meaning |
|------|---------|
| **CI** | Configuration Item — inventory node id |
| **root_ci** | Blamed primary fault object |
| **contributor_cis** | Who overloaded a shared root (e.g. noisy neighbor); not the root |
| **signature** | Fault class label (`cpu_contention`, …) |
| **GAVG / DAVG** | Datastore guest/total vs device latency |
| **Blast radius** | Downstream dependents of root |
| **Remediation** | Advisor hints keyed by signature (not auto-execute) |
| **CARE / Tier 2–3** | Lean ambiguity path; Tier 3 = scoped causal claim |
| **Murphy posterior** | Federated distribution over candidate root entities |
| **Fusion / resolve_root_ci** | ObserveOps bakeoff glue after Murphy (may use lean rules) |

---

*Learning / brainstorm only. Spec + GT authority: [`rca-use-cases-only.md`](../rca-use-cases-only.md). Engine docs: lean / federated `ARCHITECTURE.md`.*
