# Team Knowledge-Sharing Guide - No Technical Background Needed

> **Source of truth:** this `.md` file. [`Lean_RCA_Simple_Guide.pdf`](./Lean_RCA_Simple_Guide.pdf) is an export for slides/NotebookLM (regenerated 2026-07-16).

## Understanding the Lean RCA System

**Why we evaluate lean for classic infrastructure, how it actually decides root cause (not "who failed first"), and what remains open.**

**Status (2026-07-13):** ObserveOps PoC bakeoffs measured. On this corpus, evidence **favors lean** ([ADR-001](./ADR-001-lean-primary-engine.md)) — **not a finalized product pick**. Federated remains in scope for microservice / code-path evaluation. Full narrative: [`POC_BRIEFING.md`](./POC_BRIEFING.md).

---

## WHY THIS DOCUMENT EXISTS

The team first saw the **federated** design (three academic methods glued together). This guide explains the shift to **lean**, in plain language - including what we got wrong when we oversimplified lean as "walk the map and pick who got sick first."

This revision corrects the earlier guide against what the ObserveOps PoC actually built and measured (UC-1..UC-5 + UC-3b bakeoff).

### Contents

1. Where We Started: The Federated Design  
2. Why We Changed Direction  
3. The Four Qualities We Now Check For  
4. The Five Roadblocks We're Working Against  
5. How Lean Actually Works (including ObserveOps classic infra)  
6. A Worked Example: Datastore + Early Unrelated Switch  
7. What We Haven't Fully Solved (Said Plainly)  
8. How We're Testing All of This  
9. Old vs. New, Side by Side  
10. Questions Worth Discussing As a Team  

---

## 1. Where We Started: The Federated Design

Modern apps are built from many pieces talking to each other. When something breaks, the failure often shows up far from the real cause.

The original design combined three academic methods:

- **Method A (Panorama)** - each service watches its neighbors. Good at noticing something's wrong early.  
- **Method B (Murphy)** - statistical model of how entities affect each other. Good at tangled cause-and-effect questions.  
- **Method C (Nezha)** - compares "normal" vs "now" on fine-grained events/logs. Good at detail inside a service.  

A coordination layer ("translator") was meant to glue them together.

**Think of it like...** hiring three expert consultants who've never worked together, plus a translator so they can talk.

That idea has real strengths (especially Method B's deeper causal reasoning). It also has real costs: heavy infrastructure, harder-to-audit answers, and weaker reproducibility when sampling is involved. Our bakeoff put numbers on that tradeoff for classic ObserveOps classic infra.

---

## 2. Why We Changed Direction

The turning point wasn't "federated is wrong." It was: **do we need three specialists for ObserveOps’ everyday tickets**, or is that complexity buying us something we don't use?

### The real cost of bridging three methods

Each method thinks differently. The translator layer became a major source of cost and complexity - not a free lunch.

### A word we were using too loosely

We used to say we wanted a "deterministic" system. That one word was hiding **four** different questions (Section 3). Once we split them, we could choose honestly: ObserveOps care more about **same answer every time** and **checkable evidence** than about fleet-wide counterfactual sampling on every ticket.

### THE KEY REALIZATION

One comfortable word was covering four independent qualities. Separating them is why lean can be primary for classic ObserveOps **without** pretending it beats Murphy at structural causal inference everywhere.

---

## 3. The Four Qualities We Now Check For

We score every approach against four independent questions:

| Quality | Plain-English meaning | ObserveOps stance (ObserveOps) |
|---------|----------------------|------------------------------|
| **Reproducibility** | Same input -> same output every time? | **Mandatory** (bit-stable) |
| **Verifiability** | Can a human check the reasoning step by step? | **Mandatory** |
| **Accuracy** | Is the answer correct vs labeled test cases? | **Mandatory to measure** (threshold-gated - not "must be 100% forever") |
| **Causal Validity** | Does it prove "A caused B," or only timing/correlation? | **Recommended** - claim only on Tier 3 |

These are independent. Example: Method A can be accurate without claiming true causation. Method B can attempt causation while being harder to reproduce.

**WHY THIS MATTERS:** Lean's everyday path prioritizes Reproducibility + Verifiability + Accuracy. It only claims Causal Validity when an expensive/scoped check is justified (Tier 3).

---

## 4. The Five Roadblocks We're Working Against

| # | Roadblock | In plain terms | ObserveOps PoC |
|---|-----------|----------------|-------------------------|
| **1a** | Instrumentation blind spots | Some parts never share telemetry | Optional on this frozen corpus |
| **1b** | Cross-domain fragmentation | Net / host / storage / app silos | **Org silos:** still unsolved. **Where data is already joined** into one typed multi-domain graph: **this is what the PoC Mandatory'd and demonstrated** |
| **2** | Non-stationary topology | Dependencies change with deploys | Optional (topology frozen per bundle) |
| **3** | Ephemeral entity identity | Pods come and go | Out of scope for classic ObserveOps classic VMs/hosts |
| **4** | No standardized ground truth | Field has no universal exam | **Industry-wide:** still open. **This corpus:** solved **by convention** - shared `ground_truth.json` + same-bundle bakeoff |
| **5** | Compute / cost ceiling | Full always-on analysis is expensive | Respect by design (lean stays cheap; don't run fleet Gibbs on every ticket) |

**Honest habit:** separate *proven* / *proposed* / *out of scope*. Don't say "1b and 4 unsolved" without the ObserveOps split above.

---

## 5. How Lean Actually Works

Lean is **not** only "walk the map and pick who got sick first." Timing is a **clue**. ObserveOps classic-infra lean also uses **typed inventory**, **signal signatures**, and **shared-resource rules**.

### Two worlds (don't mix them up)

| | Microservice / pod world (original PRD story) | ObserveOps classic infra (what we shipped) |
|--|-----------------------------------------------|------------------------------------------|
| Map | Who calls whom (services/pods) | Network -> ESXi -> VM -> Guest OS -> App (+ Datastore) |
| Identity | Ephemeral pods | Long-lived CIs (hosts, ports, datastores, VMs) |
| Status | Research / optional track | **Primary ObserveOps path (ADR-001)** |

### Step 1 - Follow the trail on a typed map

Start from the broken app (symptom). Walk **upstream** on the inventory graph (who hosts / stores / uplinks to whom).

**Think of it like...** contact tracing - but on a **configuration map**, not only a call graph.

### Step 2 - Timing is a clue, not the verdict

Note when each related CI first looked unhealthy. **Earliest is a leading hint, never the final rule.**  
Unrelated problems can fire earlier. Clocks skew. "First" can be wrong.

### Step 3 - Ask high-value checks first (information gain)

Prefer checks that shrink uncertainty fastest - don't blindly FIFO every neighbor.

### Step 4 - ObserveOps rules: shared resources & signatures (the missing piece in older guides)

When several VMs show the **same class** of pain (CPU ready, disk latency), lean looks for the **shared upstream CI** (host, datastore) and names a **fault signature** (e.g. `storage_contention`, `cpu_contention`).

For storage: a **noisy-neighbor VM** is usually the **contributor** (who made the load), while the **datastore** is the **root** (shared bottleneck). Victims (DB VM, app) are not blamed as root.

This is how lean avoids the trap: "Batch VM started I/O first, so Batch VM is root" or "switch blipped first, so switch is root."

### Step 5 - Ambiguity helper (CARE) when onsets clump

If several candidates break within a short window, lean escalates: don't crown a random earliest CI. Prefer shared-upstream / signature winners when they fit; otherwise rank carefully (Tier 2).

### Step 6 - Stronger check only when needed (Tier 3)

Only after ambiguity escalation may lean claim a **scoped** causal check (topology + onset plausibility on a tiny candidate set).  
**Everyday ObserveOps tickets often stay Tier 1** (rules + timing + reachability) with **no** Causal Validity claim - and that is intentional.

### THE BIG PICTURE - three confidence levels

1. **Tier 1** - solid ObserveOps answer from map + signals + rules + timing clues; **not** "proven causation."  
2. **Tier 2** - CARE / ambiguity path; still not a full causal claim.  
3. **Tier 3** - scoped causal verification ran; only then may we claim stronger cause-and-effect language.

We never blur these into one unqualified "root cause proven."

### Map is not a cause map

Step 1's graph means "these CIs are related in inventory." It does **not** mean every edge is a proven cause. Signatures and Tier 3 exist so we don't pretend otherwise.

### Why not let an AI chatbot decide?

An LLM can explain after the fact. It must **not** be the decision-maker: it can sound sure while wrong, and it's hard to audit line by line.

### Future idea: continuous causal memory

Learning stable cause patterns in the background (PRD §2.8) is optional later - not required for lean path under evaluation packaging.

---

## 6. A Worked Example: Datastore + Early Unrelated Switch

This is the story older guides failed to explain.

**Setup:** Orders App -> Database -> Database VM; Batch VM shares **Datastore-01**.

**Real fault:** Batch VM heavy disk I/O -> datastore congested -> DB VM slow -> Orders App slow.

**Complication:** at 09:59:58 a switch port shows high utilization - **earlier**, but **unrelated**.

### What "who was first" would wrongly do

Pick the switch. That fails.

### What ObserveOps lean actually does

1. Start from Orders App; walk typed upstream (OS / VM / datastore / host / switch).  
2. See storage-class signals on datastore + DB VM (+ neighbor IOPS).  
3. **Shared-upstream + signature** -> root = `datastore-01`, signature = `storage_contention`.  
4. **Contributor** = Batch / noisy-neighbor VM.  
5. Switch may appear in evidence as concurrent noise - **not** root.  
6. If onsets clump, CARE runs; lean still **prefers shared-upstream** over "earliest CI."  

We freeze this as **UC-3** (clean) and **UC-3b** (early switch confound) in the ObserveOps corpus.

---

## 7. What We Haven't Fully Solved (Said Plainly)

### Data types

Lean's main path uses metrics/anomalies + topology. We now also ingest **structured synthetic events** (SNMP/syslog-style lines) on UC-2 / UC-4 / UC-3b for evidence - **not** full Nezha free-text log mining. Deeper multimodal log RCA remains optional (federated / Nezha track).

### Circular dependencies (A <-> B service loops)

Temporal "who first" is weaker on mutual loops. lean path under evaluation UCs are **layered classic infra**, not microservice cycles - so this is a real lean limit, **not** an ObserveOps bakeoff failure. Honest cyclic fixtures can document the limit later.

### Org silos (Roadblock 1b)

Algorithms don't fix team culture. Lean **does** help when ObserveOps already joins net/host/storage/app into one graph.

### Industry-wide ground truth (Roadblock 4)

Still no universal field exam. We **do** enforce a shared ObserveOps GT convention for fair bakeoffs.

### Cost at hyperscale (Roadblock 5)

Lean is structurally cheaper; we have not claimed measured 1B EPS ObserveOps deployment.

---

## 8. How We're Testing All of This

### ObserveOps bakeoff (primary)

Frozen bundles UC-1..UC-5 (+ UC-3b adversarial):

| UC | Layer | What it proves |
|----|-------|----------------|
| UC-1 | Host CPU | Don't blame app/VMs when host is shared upstream |
| UC-2 | Network | Link/port fault, not app flakiness |
| UC-3 | Storage | Datastore root + noisy-neighbor contributor |
| UC-3b | Storage + confound | Early unrelated switch must **not** win |
| UC-4 | Guest OS | OS resource fault (+ event evidence), not app code |
| UC-5 | App | Must **not** false-blame healthy infra |

Same bundle -> both engines -> compare (Accuracy, Reproducibility N=20, Verifiability, Efficiency). Latest matched run: `bakeoff-phase-b-002`. **Evaluation finding:** lean is the primary evaluation engine on this corpus (ADR-001); not a finalized product commitment.

### Older PRD scenarios (pod churn / blind spot)

Still useful for the microservice research track. They are **not** the ObserveOps acceptance gate.

---

## 9. Old vs. New, Side by Side

### By the four qualities (ObserveOps bakeoff)

| Quality | Federated | Lean | Edge |
|---------|-----------|------|------|
| Reproducibility | ~40% on N=20 (some UCs multi-hash) | **100%** | Lean |
| Verifiability | Fusion path + posteriors | Tiers + CARE/causal log + SRE report + events | Lean |
| Accuracy | 5/5 root+signature | 5/5 | Tie on this corpus |
| Causal Validity | Stronger via Murphy (costly if global) | Scoped Tier 3 only | Design choice |

### By the five roadblocks (honest ObserveOps framing)

| Roadblock | Federated | Lean | Verdict for classic ObserveOps |
|-----------|-----------|------|----------------------|
| 1a Blind spots | Partial (observer coverage) | Boundary honesty + UC-5 anti-FP cousin | Context-dependent |
| 1b Silos | Needs joined data too | **Demonstrated on joined typed CI graph** | Org unsolved; **joined-graph path proven** |
| 2 Topology churn | Live rebuild story | Frozen bundles in PoC | Optional here |
| 3 Pod churn | Hard | Out of ObserveOps scope | Defer to microservice track |
| 4 Ground truth | Same field problem | **Corpus GT convention done** | Industry open; **PoC convention done** |
| 5 Cost | Heavy multi-engine | Lightweight main path | Lean favored |

**Bottom line:** For ObserveOps classic infra, lean wins the cost-benefit. Federated/Murphy still matter when you need deep structural CV or microservice event/code-path RCA and will pay for it.

---

## 10. Questions Worth Discussing As a Team

**ON THE FOUR QUALITIES**  
Is "time-to-answer" a fifth quality, or part of Roadblock 5?

**ON ROADBLOCKS**  
For real ObserveOps customers, is pain mostly **1b (joined data)** or something else? Pod churn is rarely the ObserveOps headline.

**ON PRIORITIES**  
Next: larger corpus / accuracy floor, continuous causal memory (B5), or federated only when a microservice corpus is in scope?

**ON THE OLD DESIGN**  
When should we call Murphy as a paid escalation instead of the ObserveOps default brain?

**THE BIG PICTURE**  
This isn't "federated was wrong." It's "be honest about four qualities, don't equate earliest abnormal with root cause, and ship the engine that fits ObserveOps’ classic infra tickets."

---

*Companion to the Lean RCA PRD. Corrected 2026-07-13 to match ObserveOps PoC + ADR-001. Prefer [`POC_BRIEFING.md`](./POC_BRIEFING.md) for stakeholder/NotebookLM narrative.*
