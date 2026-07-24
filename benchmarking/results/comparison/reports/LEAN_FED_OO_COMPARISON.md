# Lean × Federated × OpenObserve — ObserveOps UC comparison

**Corpus:** ObserveOps UC-1..UC-5 (same synthetic classic-infra stories)  
**Lean / Federated cite:** run `adr001-rerun-20260723` · reports under [`lean/`](./lean/) · [`federated/`](./federated/) · scoreboard [`../COMPARISON.md`](../COMPARISON.md)  
**OpenObserve cite:** operator-collected incident analyses under [`OO/`](./OO/) (synthetic data pushed into OO; alerts → incidents → RCA write-ups)  
**Date indexed:** 2026-07-24  

**Do not merge** this three-way surface with Motadata L1, ecom-numa gold, or prior OpenObserve peer % scoreboards.

---

## 0. Fairness contract (read first)

| Engine | How the case starts | What we score |
|--------|---------------------|---------------|
| **Lean / Federated** | Frozen pack (topology + anomalies + seed + GT); shared threshold Detect in bakeoff | Machine `root_ci` / signature vs GT; N=20 repro; latency; comprehensive report 15/15 |
| **OpenObserve** | **Alert required** to form an incident; no automatic RCA without alerts. Past-data incident creation was disabled for ~14‑day‑old telemetry, so the operator **forced past-window incident trigger** after preparing alerts | Human-readable OO incident analysis (executive “Potential Cause”) vs same GT |

### Operator notes (OO run — authoritative caveats)

1. **Automatic RCA is not available in OpenObserve** — alert creation is compulsory before any incident/RCA exists.  
2. Alerts were not present initially → no incidents until alerts were prepared.  
3. Incident creation from past data was disabled → changed so **past** synthetic windows could be triggered (data was ~14 days old).  

These steps are **part of the OO cost of entry**, not a Lean/Fed step. Treat OO results as **alert-gated, operator-assisted** analysis on the same synthetic story — not a drop-in same-API bakeoff.

### Contamination flag (UC-1)

OO UC-1 analysis quotes alert text that embeds GT literally:

`root_ci_gt=esxi-host-01, signature_gt=cpu_contention`

So UC-1 OO “correctness” is **weak evidence** for independent Localize; the alert may have handed the answer. Prefer UC-2..UC-5 for OO accuracy claims unless alerts are rewritten without GT strings.

---

## 1. Ground truth (ObserveOps)

| UC | Root CI | Signature | Trap |
|----|---------|-----------|------|
| UC-1 | `esxi-host-01` | `cpu_contention` | Blame `orders-api` / guest |
| UC-2 | `switch-core-01:GigE0/2` | `link_failure` | Blame app / host |
| UC-3 | `datastore-01` | `storage_contention` | Blame DB / app only |
| UC-4 | `guest-os-vm-app-01` | `os_resource_exhaustion` | Blame app code / ESXi |
| UC-5 | `orders-api` | `app_resource_exhaustion` | **False-blame healthy infra** |

---

## 2. Root / Identify scoreboard

| UC | GT root | Lean | Federated | OpenObserve (from executive / potential cause) | OO notes |
|----|---------|------|-----------|------------------------------------------------|----------|
| UC-1 | `esxi-host-01` | ✓ | ✓ | ✓ names `esxi-host-01` / CPU contention | **GT string in alert** — discount |
| UC-2 | `switch-core-01:GigE0/2` | ✓ | ✓ | ✓ core switch GigE0/2 link-down | Metric/log query gaps; still correct narrative |
| UC-3 | `datastore-01` | ✓ | ✓ | ✓ datastore queue + `vm-neighbor-01` noisy neighbor | Strong multimodal reasoning in prose |
| UC-4 | `guest-os-vm-app-01` | ✓ | ✓ | ✓ guest FS full → OOM → app | Correct layer; hypervisors ruled out |
| UC-5 | `orders-api` | ✓ | ✓ | ✓ app heap + pool; infra healthy | **Anti-FP pass** (critical) |

**Headline accuracy (root story):**

| Engine | Root vs GT | Caveat |
|--------|------------|--------|
| Lean | **5/5** | Machine-scored vs pack GT |
| Federated | **5/5** | Machine-scored vs pack GT |
| OpenObserve | **5/5 narrative** (operator judgment) | UC-1 contaminated; process not automatic |

Signatures: Lean/Fed machine-match GT on this rerun. OO uses prose (“CPU contention”, “link-down”, “datastore contention”, “guest OS exhaustion”, “JVM/pool exhaustion”) — aligned in meaning, not the same enum field.

---

## 3. Four-axis + ops axes (UC corpus)

| Axis | Lean | Federated | OpenObserve |
|------|------|-----------|-------------|
| **Accuracy (root)** | 5/5 | 5/5 | 5/5 narrative (see §0 UC-1) |
| **UC-5 anti-FP** | Pass | Pass | Pass (infra ruled healthy) |
| **Reproducibility** | **100%** N=20 bit-identical | **40%** packs bit-identical | Not on this contract (LLM/operator write-up) |
| **Verifiability** | High — tier / CARE / causal_log + structured report | Medium — fusion/posterior; report assembled | High **prose** audit; weaker **machine** replay of Localize path |
| **Efficiency (diagnose)** | ~**1–5 ms** RCA | ~**0.003–10 s** RCA | Human + platform (alerts, past trigger, investigation) — **minutes**, not ms |
| **Report completeness** | 15/15 `comprehensive_rca.v1` | 15/15 | Rich OO sections; some **tool gaps** (traces/logs/changes empty on UC-2/3/5) |
| **Front-door cost** | Pack / Detect in bakeoff | Same | **Must author alerts** + enable past incident path |

Sources: Lean/Fed — [`../COMPARISON.md`](../COMPARISON.md). OO — [`OO/`](./OO/) + operator notes above.

---

## 4. Per-UC qualitative (what each got right / struggled)

### UC-1 — ESXi CPU contention
- **Lean / Fed:** Correct root; Lean Tier 3 + CARE on this rerun path.  
- **OO:** Correct story (hypervisor contention → guest ready → app latency) **but** alert embeds GT — do not cite as independent discovery.

### UC-2 — Core switch link failure
- **Lean / Fed:** Correct root port.  
- **OO:** Correct root port + cascade (discards → vmnic → retransmits → timeouts). Live queries often **0 hits** / “Not connected”; analysis leaned on **alert context**. Shows OO strength when alert text is rich, and fragility when streams don’t query.

### UC-3 — Datastore noisy neighbor
- **Lean / Fed:** Correct `datastore-01`.  
- **OO:** Excellent explanation of **gavg ≫ davg** and `vm-neighbor-01` — matches GT teaching intent. Topology tool empty; still recovered chain from alert/metrics.

### UC-4 — Guest OS exhaustion
- **Lean / Fed:** Correct guest OS root.  
- **OO:** Correct FS full → OOM kill → 5xx; correctly keeps ESXi out of blame.

### UC-5 — App resource exhaustion (anti-FP)
- **Lean / Fed:** Correct `orders-api`; no infra false blame.  
- **OO:** Correct app heap + DB pool; explicitly marks infra layers NORMAL — **same anti-FP win**.

---

## 5. Where each engine has leverage

| If you care about… | Prefer |
|--------------------|--------|
| Bit-stable, ms Localize on classic infra packs | **Lean** |
| Structured GT bakeoff + SRE tier labels | **Lean** (Fed as comparator) |
| Heavy causal sampling / future micro path-diff | **Federated** (not winning this UC ops profile) |
| Rich incident narrative inside an observability product | **OpenObserve** (after alerts exist) |
| Zero-alert automatic RCA from frozen pack | **Lean / Fed** — OO **cannot** start without alerts |
| Independent Localize without GT in alert text | **Lean / Fed**; scrub OO alerts before claiming OO accuracy |

---

## 6. Verdict (this three-way only)

1. **All three can tell the correct UC story** on this synthetic push — including UC-5 anti-FP.  
2. **Lean remains the stronger *engine* for ObserveOps UC ops profile:** reproducibility, latency, machine GT scoring, no alert prerequisite.  
3. **OO’s leverage is productized multimodal prose** once incidents exist — not automatic RCA, and not a fair ms bakeoff opponent.  
4. **Do not overclaim OO Localize wins** until alerts are free of `root_ci_gt` / `signature_gt` coaching (especially UC-1). See [`OO_UC_FAIRNESS_CHECKLIST.md`](../../../docs/OO_UC_FAIRNESS_CHECKLIST.md).  
5. Federated ties accuracy here but loses Lean on cost/repro; OO does not change ADR-001 for classic infra.

---

## 7. Artifact index

| Path | Role |
|------|------|
| [`OO/uc1_esxi_cpu_contention`](./OO/uc1_esxi_cpu_contention) … [`uc5_…`](./OO/uc5_orders_api_resource_exhaustion) | OO write-ups |
| [`lean/UC-N/incident_report.md`](./lean/UC-1/incident_report.md) | Lean comprehensive reports |
| [`federated/UC-N/incident_report.md`](./federated/UC-1/incident_report.md) | Federated comprehensive reports |
| [`../COMPARISON.md`](../COMPARISON.md) | Lean vs Fed machine scoreboard |
| [`../../../docs/ADR-001-lean-primary-engine.md`](../../../docs/ADR-001-lean-primary-engine.md) | Lean-primary evaluation finding (UC-scoped) |

*Last updated: 2026-07-24 — first Lean/Fed/OO UC three-way with OO process caveats.*
