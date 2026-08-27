# Slice A — ObserveOps UC fairness (Lean × Federated × OO)

**Status:** Complete (fair extracts + scoreboard) — 2026-07-27  
**Corpus:** ObserveOps UC-1..UC-5 only — **not** the portal-native 29  
**Related:** [`OO_UC_FAIRNESS_CHECKLIST.md`](./OO_UC_FAIRNESS_CHECKLIST.md) · [`../ingestion-poc/adapters/OO_UC_PUSH.md`](../ingestion-poc/adapters/OO_UC_PUSH.md) · [`../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) · fair write-ups [`../benchmarking/results/comparison/reports/OO/fair/`](../benchmarking/results/comparison/reports/OO/fair/)


---

## 1. Declared contract (frozen)

| Clause | Slice A rule |
|--------|----------------|
| **IDs** | UC-1, UC-2, UC-3, UC-4, UC-5 only |
| **GT** | Pack `datasets/observeops/UC-*/ground_truth.json` — never OO narrative |
| **Lean / Fed start** | Frozen pack (+ shared Detect); cite run `adr001-rerun-20260723` |
| **OO start** | Symptom-only alert → incident → RCA. Past-window trigger **allowed** if recorded |
| **Contamination ban** | No `root_ci_gt`, `signature_gt`, or “root is X” coaching in alert title/body |
| **OO extract** | One line written **before** reading Lean/Fed reports |
| **Score axes** | Accuracy (root) · anti-FP (UC-5) · Lean/Fed repro · OO process notes — separate from report richness |
| **Do not merge** | Original OO portal 29 / Motadata L1 / ecom |

---

## 2. Frozen inventory

| UC | Pack GT root / signature | Symptom seed | OO write-up (fair) | Contaminated historical? |
|----|--------------------------|--------------|---------------------|--------------------------|
| UC-1 | `esxi-host-01` / `cpu_contention` | `orders-api` / `request.p95_latency_ms` | [`fair/UC-1`](../benchmarking/results/comparison/reports/OO/fair/UC-1.md) ✗ | [`_historical_contaminated/uc1_…`](../benchmarking/results/comparison/reports/OO/_historical_contaminated/uc1_esxi_cpu_contention.md) |
| UC-2 | `switch-core-01:GigE0/2` / `link_failure` | `orders-api` / `tcp.timeouts` | [`fair/UC-2`](../benchmarking/results/comparison/reports/OO/fair/UC-2.md) ✗ | [`uc2_…`](../benchmarking/results/comparison/reports/OO/_historical_contaminated/uc2_core_switch_link_failure.md) |
| UC-3 | `datastore-01` / `storage_contention` | `orders-api` / `request.p95_latency_ms` | [`fair/UC-3`](../benchmarking/results/comparison/reports/OO/fair/UC-3.md) ✗ | [`uc3_…`](../benchmarking/results/comparison/reports/OO/_historical_contaminated/uc3_datastore_storage_contention.md) |
| UC-4 | `guest-os-vm-app-01` / `os_resource_exhaustion` | `orders-api` / `error_rate_5xx` | [`fair/UC-4`](../benchmarking/results/comparison/reports/OO/fair/UC-4.md) ✗ | [`uc4_…`](../benchmarking/results/comparison/reports/OO/_historical_contaminated/uc4_guest_os_resource_exhaustion.md) |
| UC-5 | `orders-api` / `app_resource_exhaustion` | `orders-api` / `request.p95_latency_ms` | [`fair/UC-5`](../benchmarking/results/comparison/reports/OO/fair/UC-5.md) ✓ | [`uc5_…`](../benchmarking/results/comparison/reports/OO/_historical_contaminated/uc5_orders_api_resource_exhaustion.md) |

OO streams from push: `observeops_uc_uc1` … `observeops_uc_uc5` · filter `corpus=observeops` / `uc_id`.

---

## 3. Score sheet (owned by LEAN_FED)

**Do not duplicate numbers here.** Canonical fair scoreboard:

- [`LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) §2  
- [`OO/fair/scoreboard.json`](../benchmarking/results/comparison/reports/OO/fair/scoreboard.json)  
- Per-UC write-ups: [`OO/fair/`](../benchmarking/results/comparison/reports/OO/fair/)

**Headline:** Lean **5/5** · Federated **5/5** · OO fair **1/5** (UC-5 only) · run `adr001-rerun-20260723` · shift-to-now for OO.

---

## 4. Operator steps (portal) — do in order

### A. Fair re-push (strips GT tags from telemetry)

From a host that can reach OO (`172.16.14.77:5080`):

```bash
export OPENOBSERVE_URL=http://172.16.14.77:5080
export OPENOBSERVE_ORG=default
export OPENOBSERVE_USER='…'
export OPENOBSERVE_PASSWORD='…'

.venv/bin/python ingestion-poc/adapters/push_observeops_uc_to_openobserve.py \
  --parity-run-id adr001-rerun-20260723 \
  --fair \
  --purge-stale \
  --out-summary benchmarking/results/comparison/oo_push_summary_fair.json
```

`--fair` omits `root_ci_gt` / `signature_gt` and uses scenario labels like `UC-1 symptom orders-api/request.p95_latency_ms`.

Dry-run check first:

```bash
.venv/bin/python ingestion-poc/adapters/push_observeops_uc_to_openobserve.py \
  --parity-run-id adr001-rerun-20260723 --fair --preview --dry-run | head
```

### B. Replace alerts with symptom-only text

Delete or edit existing UC alerts that mention root cause / GT. Paste:

| UC | Alert title (suggested) | Alert description (paste) |
|----|-------------------------|---------------------------|
| UC-1 | `orders-api p95 latency high (UC-1)` | Symptom: `orders-api` `request.p95_latency_ms` breached SLO (threshold 1000ms). Investigate upstream of the app. Do not assume root CI. |
| UC-2 | `orders-api TCP timeouts (UC-2)` | Symptom: `orders-api` `tcp.timeouts` elevated. Investigate path to dependency. Do not assume root CI. |
| UC-3 | `orders-api p95 latency high (UC-3)` | Symptom: `orders-api` `request.p95_latency_ms` breached. Investigate storage/DB/app path. Do not assume root CI. |
| UC-4 | `orders-api 5xx error rate high (UC-4)` | Symptom: `orders-api` `error_rate_5xx` breached. Investigate guest OS / app / host. Do not assume root CI. |
| UC-5 | `orders-api p95 latency high (UC-5)` | Symptom: `orders-api` `request.p95_latency_ms` breached. Rule out healthy infra before blaming app or host. Do not assume root CI. |

Fire condition: same seed metric / threshold as pack Detect (symptom CI only).

### C. Blind extract → then RCA — **done 2026-07-27**

Canonical write-ups: [`reports/OO/fair/`](../benchmarking/results/comparison/reports/OO/fair/). Score sheet §3 filled. Contaminated = N for fair alerts (historical `OO/uc*_…` still contaminated).

### D. Publish — **done 2026-07-27**

[`LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) updated to fair OO **1/5** (contaminated 5/5 narrative withdrawn).

---

## 5. Checklist progress

| # | Item | Status |
|---|------|--------|
| 1 | Freeze UC ID set | **Done** (§2) |
| 2 | Charter written | **Done** (§1) |
| 3 | Push script `--fair` | **Done** (code) |
| 4 | Symptom alert templates | **Done** (§4B) |
| 5 | Fair re-push to OO | **Done** — parity fair push, then **2026-07-27 shift-to-now** (`oo_push_summary_fair_shifted.json`) so incident clock matches data |
| 6 | Scrub/replace alerts in OO UI | **Done** 2026-07-27 — 5 fair alerts; silence 24h; period 6h |
| 7 | Blind extracts + re-pull write-ups | **Done** 2026-07-27 — [`reports/OO/fair/`](../benchmarking/results/comparison/reports/OO/fair/) |
| 8 | Fill score sheet + update compare doc | **Done** — score sheet above + [`LEAN_FED_OO_COMPARISON.md`](../benchmarking/results/comparison/reports/LEAN_FED_OO_COMPARISON.md) |

---

*Started 2026-07-24 — fair Slice A completed 2026-07-27 (OO root 1/5). Slice B (portal 29) stays deferred.*
