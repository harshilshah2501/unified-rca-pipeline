# OpenObserve Option B — Results analysis

Companion to [`GT_SCOREBOARD.md`](./GT_SCOREBOARD.md) (numbers) and `gt_scoreboard.json` (machine-readable).

## Deep insights

### 1. The headline: same layer score, very different root score

All three methods are **tied at 80% layer accuracy** (8/10). That can fool a shallow readout into “they’re equal.”

They are **not** equal on naming the agreed root alert:

| | Lean | Federated | OpenObserve |
|--|------|-----------|-------------|
| Root-alert (Top‑1 entity) | **90% (9/10)** | 40% (4/10) | 30% (3/10) |
| Layer **and** root | **80%** | 30% | 20% |

**Insight:** On this corpus, “which domain?” is relatively easy once alerts are layered; “which alert is the root?” is where methods diverge. That is exactly the Murphy *true root cause entity* bar.

### 2. Multi-trigger decoys are the real discriminator

On the **7 eligible multi-trigger** incidents:

| | Lean | Federated | OpenObserve |
|--|------|-----------|-------------|
| Layer | 86% | 86% | 86% |
| Root | **86%** | **14%** | **0%** |
| Crowns incident title | 29% | **100%** | 57% |

Federated principle-fusion (title + earliest bias) **always** picked the title on this multi set. Lean only did when the title *was* the agreed root (`net_link_saturation`). OpenObserve often stayed on the symptom title or a nearby symptom alert.

**Patterns:**

| Incident | Baseline root | Who got the entity right? |
|----------|---------------|---------------------------|
| `cio_host_cpu_high` | `cio_disk_io_stall` | **Lean only** (Fed → CPU title; OO → load avg) |
| `ecom_checkout_slo_breach` (×2) | `ecom_dns_aaaa_numa` | **Lean only** (Fed/OO → SLO title; one OO also wrong layer) |
| `sa_upload_slo` | `sa_inode_high` | **Lean only** (Fed/OO → SLO title) |
| `pgw_checkout_tps_drop` | `pgw_fw_443_denies` | **Lean only** (Fed → TPS title; OO → ESXi symptom) |
| `net_link_saturation` | title = root | Lean + Fed; OO picked `checkout_db_timeouts` |
| `sc_latency_slo` | CI `redis-node-3` | **Nobody** on root; OO alone got application layer |

**Insight:** When the freeze *embeds* the causal chain in alert text (CPU iowait decoy, DNS→payment→SLO, inode→ENOSPC, ACL ROOT), Lean’s upstream preference recovers it. Federated/OO match the **loud title**.

### 3. OpenObserve as method #3 — not the answer key

Against convention baseline, OpenObserve:

- Matches layer as often as the others (**80%**)
- Rarely names the adjudicated root on decoy tickets (**0% root on multi**)
- On `orders_service_surge`, wrongly prefers **database** layer (surge “driving DB load” wording trap)
- On one ecom case, stays at **application** while baseline + Lean say **dns**

**Insight:** Platform narrative is useful as a *third opinion*, and dangerous as *GT*. Peer “agree with OO” earlier would have overstated OO and understated Lean’s decoy wins.

### 4. Shared blind spots (all methods)

1. **`orders_service_surge`** — everyone got the alert name right; nobody got `application` layer (Lean/Fed → `unknown`; OO → `database`). Keyword taxonomy gap, not a decoy fight.
2. **`sc_latency_slo` / redis-node-3** — baseline root is a **CI id** called out in alert prose, with **no redis alert** in the freeze. Root match is nearly impossible for alert-pickers; OO’s layer hit is the best partial credit. **Corpus packaging limit.**
3. **Ambiguous exclusions** (`starter_high_cpu`, empty `db_primary_down`) — correct decision; scoring them would invent accuracy out of thin air.

### 5. How this lines up with papers (language, not ego)

| Paper idea | What we did |
|------------|-------------|
| Murphy *true root cause entity* / Top‑1 | Root-alert accuracy column |
| Murphy *operator-decided ground truth* | Solo convention labels (weaker than dual-human, same *kind*) |
| Nezha *known injected service* | **Not** this track — we did not inject |
| Panorama *reproduced known failure* | **Not** this track |

UC-1..UC-5 remains the **designed** bakeoff. This sample is the **convention** bakeoff for OpenObserve-shaped incidents.

### 6. UC bakeoff echo

On ObserveOps UC-1..UC-5, both engines were 5/5 root-CI; Lean won on **reproducibility** and observation tie-breaks. Here Lean does not win layer (tie) but **does** win the entity/decoy bar — consistent with “prefer stable, checkable upstream walk over title-fusion” for classic multi-symptom tickets.

---

## Conclusion (simple words)

We finally compared Lean, Federated, and OpenObserve to an **agreed baseline** (who we say the root is), not to each other.

**Short score card (10 scored incidents):**

- All three find the **right area** about equally often (**8/10**).
- Lean names the **right root alert** far more often (**9/10** vs Federated **4/10** vs OpenObserve **3/10**).
- On messy multi-alert tickets, Federated almost always trusts the **incident title**; Lean usually looks past the decoy.

**So what?** For these kinds of incidents — especially CPU/SLO/TPS titles that hide storage, DNS, filesystem, or firewall causes — a **lean, decoy-aware walk** matched our baseline better than fusion/title bias or the platform’s own narrative.

**What not to overclaim:** Labels were done solo (not two independent people). Engines are principle stand-ins, not full Murphy/lean on a VMware graph. Sample is small (10). Re-label with two humans and grow the set before any product decision.

**Bottom line:** With a Murphy-style baseline in place, **Lean wins this round on the metric that matters to SREs (the actual root)**, even when the “which layer?” score looks like a three-way tie.

