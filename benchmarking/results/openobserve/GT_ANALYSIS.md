# OpenObserve Option B — Results analysis

Companion to [`GT_SCOREBOARD.md`](./GT_SCOREBOARD.md) (numbers) and `gt_scoreboard.json` (machine-readable).

**Updated after full-corpus labeling:** 29 incidents labeled (solo dual-pass), **24 accuracy-eligible**, **5 excluded** (3× starter stub, 1× empty-payload db_primary_down, 1× SLO-only checkout).

## Deep insights

### 1. The headline: layer tie tightens, root gap widens

On the full 24-incident eligible set:

| | Lean | Federated | OpenObserve |
|--|------|-----------|-------------|
| Layer accuracy | **88% (21/24)** | **88% (21/24)** | **79% (19/24)** |
| Root-alert (Top‑1 entity) | **92% (22/24)** | 62% (15/24) | 58% (14/24) |
| Layer **and** root | **88%** | 58% | 50% |

**Insight:** Adding 14 mostly straightforward single-trigger database incidents lifts everyone's layer score and makes the three-way layer tie look even closer. The **root-alert gap is unchanged in direction** — Lean still dominates entity naming — and OpenObserve falls slightly behind on layer once the full corpus is included.

### 2. Multi-trigger decoys remain the real discriminator

On the **11 eligible multi-trigger** incidents:

| | Lean | Federated | OpenObserve |
|--|------|-----------|-------------|
| Layer | 82% | 82% | 73% |
| Root | **82%** | **18%** | **9%** |
| Crowns incident title | 36% | **100%** | 64% |

Federated principle-fusion still **always** picks the title on multi-trigger eligible cases. Lean resists decoys; OpenObserve sometimes follows narrative upstream but often lands on symptom alerts (`checkout_db_timeouts`, `pgw_esxi_443_no_return`, SLO titles).

**New cases that reinforce the pattern:**

| Incident | Baseline root | Who got the entity right? |
|----------|---------------|---------------------------|
| `sd_notif_slo` | `sd_tls_fail` | **Nobody** — all three crown SLO title / miss TLS layer |
| `pgw_checkout_tps_drop` (twin) | `pgw_fw_443_denies` | **Lean only** (Fed → TPS title; OO → ESXi symptom) |
| `net_link_saturation` (twin) | `net_link_saturation` | Lean + Fed; OO picked `checkout_db_timeouts` on one twin |
| `ecom_checkout_slo_breach` (3-trigger) | `ecom_dns_aaaa_numa` | **Lean only** (Fed/OO → SLO title) |

**Database singles (6 variants + 4 with narrative):** All three methods score **100% layer and root** — these are easy agreement cases that inflate headline layer accuracy without testing decoy resistance.

### 3. OpenObserve as method #3 — not the answer key

Against the full convention baseline:

- Layer: **79%** (slightly behind Lean/Fed at 88%)
- Root: **58%** (vs Lean 92%, Fed 62%)
- On multi-trigger decoys: **9% root** (1/11) — still symptom/title biased
- New miss: **`sd_notif_slo`** — OO, Lean, and Fed all fail to prefer `sd_tls_fail` over the SLO title (TLS layer taxonomy gap across methods)

**Insight:** Platform narrative helps on some firewall/network tickets but does not fix title bias on SLO-fronted chains.

### 4. Shared blind spots (all methods)

1. **`orders_service_surge`** — layer taxonomy gap (Lean/Fed → `unknown`; OO → `database`).
2. **`sc_latency_slo` / redis-node-3** — CI id root with no matching alert name; root match nearly impossible.
3. **`sd_notif_slo`** — new shared blind spot: expired cert / TLS failure upstream of SLO; all methods crown the notification SLO title.
4. **Excluded (5):** 3× `starter_high_cpu` stubs, empty-payload `db_primary_down`, single-trigger `ecom_checkout_slo_breach on checkout-service` (SLO-only, no upstream in triggers).

### 5. How this lines up with papers (language, not ego)

| Paper idea | What we did |
|------------|-------------|
| Murphy *true root cause entity* / Top‑1 | Root-alert accuracy column |
| Murphy *operator-decided ground truth* | Solo convention labels (weaker than dual-human, same *kind*) |
| Nezha *known injected service* | **Not** this track — we did not inject |
| Panorama *reproduced known failure* | **Not** this track |

UC-1..UC-5 remains the **designed** bakeoff. This corpus is now the **full 29-incident convention** bakeoff for OpenObserve-shaped incidents.

### 6. UC bakeoff echo

On ObserveOps UC-1..UC-5, both engines were 5/5 root-CI; Lean won on **reproducibility** and observation tie-breaks. On the full OpenObserve convention set, Lean wins the entity/decoy bar while layer looks like a near-tie — consistent with “prefer stable, checkable upstream walk over title-fusion” for classic multi-symptom tickets.

---

## Conclusion (simple words)

We compared Lean, Federated, and OpenObserve to an **agreed baseline** across all **29** OpenObserve incidents (**24 scored**, **5 excluded**).

**Short score card (24 scored incidents):**

- Lean and Federated find the **right area** equally often (**88%**); OpenObserve is slightly behind (**79%**).
- Lean names the **right root alert** far more often (**92%** vs Federated **62%** vs OpenObserve **58%**).
- On messy multi-alert tickets, Federated still almost always trusts the **incident title**; Lean usually looks past the decoy.

**So what?** The extra 17 labels mostly added easy database singles — they confirm baseline agreement on simple cases but do not change the decoy story. **Lean still wins on the metric SREs care about (the actual root)**, especially when SLO/CPU/TPS titles hide DNS, TLS, filesystem, or firewall causes.

**What not to overclaim:** Labels were solo dual-pass (not two independent people). Engines are principle stand-ins. Re-label with two humans before any product decision.

**Bottom line:** Full corpus labeled. **Lean wins this round on root-alert accuracy (92%)** even when layer accuracy looks like a two-way tie at 88%.
