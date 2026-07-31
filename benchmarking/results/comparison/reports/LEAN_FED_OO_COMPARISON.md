# Lean × Federated × OpenObserve — ObserveOps UC comparison

**Corpus:** ObserveOps UC-1..UC-5 (same synthetic classic-infra stories)  
**Lean / Federated cite:** run `adr001-rerun-20260723` · reports under [`lean/`](./lean/) · [`federated/`](./federated/) · scoreboard [`../COMPARISON.md`](../COMPARISON.md)  
**OpenObserve cite (fair):** Slice A 2026-07-27 — symptom-only alerts + `--fair` shift-to-now push · extracts [`OO/_fair_extracts/`](./OO/_fair_extracts/) · write-ups [`OO/fair/`](./OO/fair/)  
**Charter:** [`docs/SLICE_A_OO_UC_FAIRNESS.md`](../../../docs/SLICE_A_OO_UC_FAIRNESS.md)  
**Date indexed:** 2026-07-27  

**Do not merge** this three-way surface with Motadata L1, ecom-numa gold, or OpenObserve peer (29) scoreboards.

---

## 0. Fairness contract

| Engine | How the case starts | What we score |
|--------|---------------------|---------------|
| **Lean / Federated** | Frozen pack + shared Detect (`adr001-rerun-20260723`) | Machine `root_ci` / signature vs pack GT |
| **OpenObserve (fair)** | Symptom-only alert → incident → AI SRE Analysis; telemetry via `--fair --shift-to-now` (no `root_ci_gt` / `signature_gt` on records or alerts) | Blind map of Executive “Potential Cause” → root CI vs pack GT |

### Fair-run process notes (2026-07-27)

1. Fair push: `push_observeops_uc_to_openobserve.py --parity-run-id adr001-rerun-20260723 --fair --shift-to-now --end-offset-minutes 2`.  
2. Alerts: `orders_api_*_UC{1..5}` — symptom SQL only (`oo_slice_a_alerts.json`).  
3. **Shift required:** OO incident clock is “now”; absolute Jul-10 parity timestamps do not land in the Analysis window. Score sheet marks `shift: yes`.  
4. Old morning incidents absorbed re-fires → resolved; scoring used **new** open incidents after r3/r4 push.  
5. Prior [`OO/_historical_contaminated/`](./OO/_historical_contaminated/) write-ups (2026-07-24) are **contaminated / historical** — do not cite for accuracy.

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

## 2. Root / Identify scoreboard (fair Slice A)

| UC | GT root | Lean | Federated | OpenObserve (blind Potential Cause) | OO ✓? |
|----|---------|------|-----------|-------------------------------------|-------|
| UC-1 | `esxi-host-01` | ✓ | ✓ | `payment-db (db-01)` / checkout TCP + slow product queries | **No** |
| UC-2 | `switch-core-01:GigE0/2` | ✓ | ✓ | _(none)_ — OO API unavailable at analysis | **No** |
| UC-3 | `datastore-01` | ✓ | ✓ | unidentified shared downstream bottleneck | **No** |
| UC-4 | `guest-os-vm-app-01` | ✓ | ✓ | unidentified deploy/config/upstream | **No** |
| UC-5 | `orders-api` | ✓ | ✓ | orders-api pool saturation + JVM heap ~96% | **Yes** |

**Headline accuracy (root vs pack GT):**

| Engine | Root | Caveat |
|--------|------|--------|
| Lean | **5/5** | Machine-scored |
| Federated | **5/5** | Machine-scored |
| OpenObserve (fair) | **1/5** | UC-5 only; UC-2 = platform failure (no RCA) |

Incidents scored: UC-1 `3H538eGN…` · UC-2 `3H5422Dw…` · UC-3 `3H541z1b…` · UC-4 `3H543H5F…` · UC-5 `3H540hUY…`.

Signatures: Lean/Fed machine-match GT. OO prose — only UC-5 clearly aligns with `app_resource_exhaustion` on `orders-api`.

### Historical (contaminated) OO row — do not use for claims

| Engine | Claimed root | Why invalid |
|--------|--------------|-------------|
| OO 2026-07-24 | 5/5 narrative | UC-1 alert embedded `root_ci_gt` / `signature_gt`; other UCs not re-proven under fair alerts |

---

## 3. Four-axis + ops axes (UC corpus, fair OO)

| Axis | Lean | Federated | OpenObserve (fair) |
|------|------|-----------|---------------------|
| **Accuracy (root)** | 5/5 | 5/5 | **1/5** |
| **UC-5 anti-FP** | Pass | Pass | **Pass** (stayed on app; no healthy-infra blame) |
| **Reproducibility** | **100%** N=20 | **40%** packs | Not on contract (LLM Analysis) |
| **Verifiability** | High — structured report | Medium — fusion | Prose audit; mixed evidence (ecom stream bleed on UC-1) |
| **Efficiency (diagnose)** | ~1–5 ms RCA | ~0.003–10 s | Minutes (alerts + Analysis); hung delta jobs observed |
| **Report completeness** | 15/15 | 15/15 | Variable; UC-2 empty; UC-3/4 “unknown”; UC-5 strong app story |
| **Front-door cost** | Pack / Detect | Same | Must author alerts + shift data into “now” window |

---

## 4. Per-UC qualitative (fair run)

### UC-1 — ESXi CPU contention
- **Lean / Fed:** Correct `esxi-host-01`.  
- **OO:** Saw observeops p95=1450 but blamed **checkout / payment-db** using unrelated org streams (`api_gateway_logs`, `checkout_service_logs`). Missed `cpu_ready` / ESXi.

### UC-2 — Core switch link failure
- **Lean / Fed:** Correct switch port.  
- **OO:** Analysis failed (“OpenObserve API unavailable”). No root produced → score miss.

### UC-3 — Datastore noisy neighbor
- **Lean / Fed:** Correct `datastore-01`.  
- **OO:** Noted 400→2100 ms and co-spikes with UC-1/UC-5; could not name datastore / storage contention.

### UC-4 — Guest OS exhaustion
- **Lean / Fed:** Correct `guest-os-vm-app-01`.  
- **OO:** Saw 2%→42% 5xx; blamed vague deploy/upstream; logs stream flaky during push. Did not name guest OS / OOM path.

### UC-5 — App resource exhaustion (anti-FP)
- **Lean / Fed:** Correct `orders-api`.  
- **OO:** Correct app-layer story (pool 100% + JVM heap 96% → p95 1800 / 18% errors). **Anti-FP pass.**

---

## 5. Where each engine has leverage

| If you care about… | Prefer |
|--------------------|--------|
| Bit-stable, ms Localize on classic infra packs | **Lean** |
| Structured GT bakeoff + SRE tier labels | **Lean** (Fed as comparator) |
| Upstream infra roots (ESXi / switch / datastore / guest OS) on fair symptom alerts | **Lean / Fed** (OO 0/4 on those in this fair pass) |
| App-local resource exhaustion when symptom is on the app | Lean / Fed / **OO** (OO hit UC-5) |
| Rich productized incident narrative | **OO** (when Analysis completes) — not a substitute for fair root accuracy |
| Zero-alert automatic RCA from frozen pack | **Lean / Fed** |

---

## 6. Verdict (fair three-way)

1. **Lean and Federated remain 5/5** on pack GT for UC-1..UC-5.  
2. **Fair OO root accuracy is 1/5** — only UC-5 (app-local). Upstream-infra UCs were wrong, vague, or unscorable.  
3. Contaminated 2026-07-24 OO “5/5” is **withdrawn** for Localize claims.  
4. **ADR-001 lean-primary on ObserveOps UC is reinforced**, not weakened, by fair OO.  
5. OO still useful as a **product narrative** surface; do not treat fair UC root % as peer to Lean/Fed machine scoring without stating the 1/5 caveat.

---

## 7. Artifact index

| Path | Role |
|------|------|
| [`OO/uc1_…`](./OO/_historical_contaminated/uc1_esxi_cpu_contention.md) … [`uc5_…`](./OO/_historical_contaminated/uc5_orders_api_resource_exhaustion.md) | **Historical contaminated** (2026-07-24) |
| [`OO/fair/`](./OO/fair/) | Fair Slice A write-ups + scoreboard JSON |
| [`openobserve/UC-N/`](./openobserve/) | OO portal Analysis as `incident_report.json` (same shape as Lean/Fed) |
| [`OO/_fair_extracts/`](./OO/_fair_extracts/) | Blind extract JSON + raw Analysis markdown |
| [`lean/UC-N/incident_report.md`](./lean/UC-1/incident_report.md) | Lean comprehensive reports |
| [`federated/UC-N/incident_report.md`](./federated/UC-1/incident_report.md) | Federated comprehensive reports |
| [`../COMPARISON.md`](../COMPARISON.md) | Lean vs Fed machine scoreboard |
| [`../../../docs/SLICE_A_OO_UC_FAIRNESS.md`](../../../docs/SLICE_A_OO_UC_FAIRNESS.md) | Fairness charter + live score sheet |

*Last updated: 2026-07-27 — fair Slice A OO re-score (1/5); contaminated OO narrative retired for accuracy claims.*
