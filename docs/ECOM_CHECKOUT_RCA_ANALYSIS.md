# E-com checkout RCA — analysis & north star

**One-stop doc** for the cross-NUMA checkout scenario.

| | |
|--|--|
| **Pack** | `ecom-numa-001` |
| **Gold incident report** | OpenObserve-style analysis for `3GAWT8nVjUE2rA95CZmtyiQcVri` (same story; fuller multimodal write-up) |
| **Scenario design** | [`../datasets/scenario.md`](../datasets/scenario.md) |
| **Ground truth** | [`../datasets/ecom_checkout/incidents/ecom-numa-001/ground_truth.json`](../datasets/ecom_checkout/incidents/ecom-numa-001/ground_truth.json) |
| **Engine cite** | run `ecom-20260722T110736Z` · repro `ecom-repro-v1` |
| **Scoreboard (parked)** | [`../_adhoc/ecom-gold-report-compare/COMPARISON.md`](../_adhoc/ecom-gold-report-compare/COMPARISON.md) — Lean vs Fed compare is **secondary** |

---

## 0. Current objective (park engine bakeoff)

**Goal:** produce an incident RCA that is **correct and as comprehensive** as the gold analysis report — for **both** Lean and Federated.

We are **not** optimizing “which engine wins” right now. Bakeoff metrics (latency, N=20 bit-identical, signature stamp quirks) stay documented below for later; they do not drive the next build.

### What “correct + comprehensive” means (gold report checklist)

An acceptable RCA for this incident must cover, in substance:

| Section | Must get right |
|---------|----------------|
| **Incident summary** | SLO drop, dimension slice (~2.8%), services, severity/window |
| **Impact** | Who/what failed; SLA breach; not “whole platform down” |
| **Service dependencies** | Critical path; isolate payment path; rule out healthy siblings |
| **Distributed traces** | Slow span ~17s on provider call; argue latency is *before*/around DNS/conn — provider itself not guilty |
| **Log patterns** | Kernel RX-7 cross-NUMA; infra node-image + IRQ affinity WARN |
| **Metrics** | Checkout p99, AAAA DNS, pool acquire, RX queue, success rate — with baselines |
| **Recent changes** | Node image `2026.06.18` on NP-17 as root-cause change |
| **Causal chain** | Image → IRQ/NUMA → RX → AAAA DNS → pool → payment tail → checkout SLO (+ amplifier) |
| **Contributing factors** | Primary misconfig + payment-risk DNS amplification |
| **Timeline** | Change → kernel onset → symptom → alert |
| **Actions** | Immediate rollback to `2026.05.30` + verify; future NUMA validation / staged rollout |

**Correctness bar:** root = NP-17 IRQ / node-image misconfig (not `payment-provider`).  
**Completeness bar:** multimodal evidence + chain + fix — not only `root_ci` + signature.

### Gap vs engines today → status

| Gold need | Status |
|-----------|--------|
| Trace-backed false-lead rebuttal | **Addressed** — report analyzes `raw/spans.json` (slow provider spans + sibling isolation) |
| Log patterns as first-class proof | **Addressed** — pack events + key findings in report (Fed no longer depends on loading events into Murphy) |
| Full narrative (summary → actions) | **Addressed** — shared `comprehensive_rca.v1` markdown/JSON |
| Shared report shape | **Addressed** — same schema for Lean and Federated |
| Federated full causal chain | **Addressed** — assembler builds root→seed topology path (not root-only) |
| Quantified impact + api-gateway | **Addressed** — ~186/387, ~48% path error, gateway on topology/critical path |
| Canonical alert identity / Jul-7 clock | **Addressed** — `source_incident_id` + `canonical_clock` remap in report |
| Fed signature without GT stamp | **Addressed** — `infer_signature(crossed)` in `run_federated.py` |

**Schema:** [`schemas/comprehensive_incident_report.v1.json`](./schemas/comprehensive_incident_report.v1.json)  
**Builder:** `benchmarking/benchmark/comprehensive_rca_report.py`  
**Sample outputs (15/15 completeness, ad-hoc quarantine):**  
[`../_adhoc/ecom-gold-report-compare/reports/lean/incident_report.md`](../_adhoc/ecom-gold-report-compare/reports/lean/incident_report.md) ·  
[`../_adhoc/ecom-gold-report-compare/reports/federated/incident_report.md`](../_adhoc/ecom-gold-report-compare/reports/federated/incident_report.md) ·  
[`../_adhoc/ecom-gold-report-compare/reports/gold/incident_report.md`](../_adhoc/ecom-gold-report-compare/reports/gold/incident_report.md)

Reports include **RCA Summary**, **Remediation** guidance (`signature_template`, LLM-replaceable), and service error rates (`checkout_error_rate_pct`, `payment_service_error_rate_pct`, gateway path error).

```bash
python3 benchmarking/benchmark/comprehensive_rca_report.py \
  --pack datasets/ecom_checkout/incidents/ecom-numa-001 \
  --raw datasets/ecom_checkout/raw \
  --verdict benchmarking/results/lean/ecom/ecom-numa-001/run-*/verdict.json \
  --out-dir _adhoc/ecom-gold-report-compare/reports/lean
```

Localization still comes from each engine’s verdict; multimodal sections are assembled from pack + raw so **both** engines can emit a gold-shaped correct report when root is right.

**Gaps closed (2026-07-23):** topology-derived `causal_chain` for Federated; Fed `infer_signature` (no GT stamp); `api-gateway` + quantified impact; canonical Jul-7 clock + OO `source_incident_id`; RCA summary + remediation section; checkout/payment service error rates.

**Gaps closed (2026-07-24):** payment/checkout WARN (+ ERROR) logs folded into pack `events.json` via `build_ecom_scenario_pack.py` (raw streams `payment_service_logs` / `checkout_service_logs` → 182 WARN + 66 ERROR; pack matches raw 1:1). Builder asserts non-zero app WARN count on rebuild.

Still open later: live Detect (not frozen anomalies); wire LLM for remediation prose (template today).

---

## 1. Problem context

### 1.1 What on-call sees

Customers on a multi-region e-commerce platform report **checkout spinning 10–20s** and occasional failures. Only **~2.8%** of checkouts are hit — not a full outage.

| Symptom | Isolation |
|---------|-----------|
| Checkout success **99.97% → ~97.2%** | `region=Region-B`, `payment_method=CARD`, `device_type=MOBILE` |
| Checkout p99 **~18s** | `checkout_version=v4.18.7`, `currency=INR`, `cart_items > 12` |
| Slowest span | `payment-service` → external `payments.provider.com` (~17s) |

**Platform:** OpenObserve Enterprise · org `default` · cluster `prod-use1` · affected region **Region-B**.

### 1.2 Why it is hard

Traces and provider latency make the **external payment provider** look guilty. Other apps calling the same provider are fine — so “blame the vendor” is a **false lead**.

A good RCA must use **correlation** (what moved together) *and* **causal links** (what caused what), not the highest anomaly score alone. The scenario plants decoys: provider latency, jumbo MTU on NP-17, healthy checkout CPU/mem/GC/RPS.

### 1.3 Correlation vs causal links

| Kind | In this scenario |
|------|------------------|
| **Correlation** | SLO drop, p99 spike, pool exhaustion, AAAA DNS latency, RX-queue latency, and IRQ mismatch all co-occur on shared dims (`cluster` / `region` → `node_pool=NP-17` / bad pods / `RX-7`). Slice `CARD+INR+cart>12` correlates hardest (risk-feature amplifier). |
| **Causal links** | Directed chain with temporal order: node-image / IRQ misconfig (earliest) → RX stall → AAAA DNS → pool/retries → payment/checkout → SLO. Topology edges encode effect→cause; change events anchor the root. Provider is correlated and high-magnitude but **not** causal. |

```
FALSE path (looks guilty):  checkout → payment → payment-provider

REAL path (GT):             checkout → payment → dns-aaaa-np17 → nic-rx-queue-7 → np17-irq-affinity
```

### 1.4 Ground truth (authored — we score against this)

GT status: **`scenario_authored`** in [`ground_truth.json`](../datasets/ecom_checkout/incidents/ecom-numa-001/ground_truth.json). Authoritative for this bakeoff (same role as ObserveOps UC GT).

| Field | Value |
|-------|--------|
| **root_ci** | `np17-irq-affinity` |
| **signature** | `cross_numa_irq_affinity` |
| **fault_bucket / type** | `2_infra` / `misconfiguration` |
| **fault_title** | NP-17 cross-NUMA IRQ affinity (node image `2026.06.18`) |
| **contributor_cis** | `nic-rx-queue-7`, `dns-aaaa-np17` |
| **blast_radius** | `checkout-service`, `payment-service`, payment pods `118/124/131/144` (on NP-17) |
| **false_leads** | `payment-provider`; NP-17 jumbo MTU (in raw metrics) |
| **amplifier** | `CARD+INR+cart>12` payment-risk feature (extra AAAA DNS lookups) |

**Root cause:** node-image `2026.06.18` on **NP-17** pinned RX-queue-7’s IRQ to **CPU48 (NUMA1)** while queue memory sits on **NUMA0** → cross-NUMA stall → slow AAAA DNS → payment pool exhaustion → checkout SLO breach.

**Resolution:** roll NP-17 back to node image `2026.05.30`; fix IRQ affinity so the RX interrupt runs on the same NUMA node as its memory.

**Symptom seed:** `checkout-service` / `checkout_success_rate` ([`symptom_seed.json`](../datasets/ecom_checkout/incidents/ecom-numa-001/symptom_seed.json)).

Full signal tables, traces, logs, and SQL checks: [`../datasets/scenario.md`](../datasets/scenario.md).

---

## 2. Verdict — what we compared (bakeoff — parked)

> **Parked for now.** Useful as a baseline that both engines can hit the GT root; not the current build priority. See §0.

| Parameter | What it asks | GT / target | Lean | Federated |
|-----------|--------------|-------------|------|-----------|
| **Root CI** | *Where* is the fault? (localize) | `np17-irq-affinity` | ✓ same | ✓ same |
| **Signature** | *What kind* of fault? (identify) | `cross_numa_irq_affinity` | ✓ **inferred** from signals | ✓ on scoreboard, but **copied from GT** — not a fair Identify win (see §5.2) |
| **False lead avoided** | Did the engine *not* blame the decoy? | Must not pick `payment-provider` | ✓ | ✓ only after override |
| **Latency** | How long did diagnose take? (cost, not accuracy) | — | ~**6.6 ms** | ~**17.6 s** |
| **Path** | *How* did it arrive at the root? (reasoning story) | — | CARE → causal verify (tier 3) | Murphy → wrong mid-node → onset override → IRQ |
| **Evidence trail** | How rich is the SRE-facing evidence list? | Useful citations | Anomalies + change/kernel/DNS events | Crossed anomalies mainly |
| **Verify** | How strongly does it claim “this is the cause”? | Tier / causal checks | Tier 3 + causal_log | Tier 2 + posterior + override |
| **Verifiability** | Can an SRE reconstruct *why* from the verdict alone? | Auditable trail | **High** — tier + CARE + causal_log + evidence | **Medium** — posterior + override; harder under time pressure |
| **Reproducibility** | Same pack in → same verdict out across N runs? | Bit-stable preferred | **100%** (N=20, bit-identical) | **0%** bit-identical (N=20; 2 verdict hashes) — root still always GT |

**Bottom line:** both pass **Root CI** vs GT. Lean is cheaper, fairly wins **Signature** / **Verifiability**, and is **bit-stable** on N=20. Federated always lands on the right root after override, but Murphy path noise makes full `verdict.json` hashes diverge (17× posterior 1.0 vs 3× ~0.89).

---

## 3. From Postgres to engine pack

```
dump_scenario_postgres.sh
        → Postgres (otel_metrics / otel_logs / otel_spans)
export_scenario_postgres_json.py
        → datasets/ecom_checkout/raw/{metrics,logs,spans}.json
build_ecom_scenario_pack.py
        → datasets/ecom_checkout/incidents/ecom-numa-001/
run_ecom_bakeoff.py
        → Lean + Federated + COMPARISON.md
```

| Artifact | Role |
|----------|------|
| Raw JSON | Export of the Postgres scenario (~12k metrics, ~286 logs, ~840 spans) |
| Engine pack | Frozen topology + anomalies + seed + GT for fair Lean/Fed compare |
| Pack topology | Effect→cause: checkout → payment → {provider decoy \| DNS → RX → **IRQ**} |

Earliest crossed drivers: IRQ + RX at **T₀**; DNS / pool / provider / checkout symptoms ~2 minutes later.

Reproduce: [`scenario.md`](../datasets/scenario.md) §7.3 · `python3 benchmarking/benchmark/run_ecom_bakeoff.py`

---

## 4. Lean analysis

**Result:** root `np17-irq-affinity` · signature `cross_numa_irq_affinity` · tier **3** · `fallback_fired=true` · `causal_verified=true` · ~**6.6 ms**.

### 4.1 How it reasoned

1. Seed at checkout SLO; walk upstream on `depends_on`.
2. Many crossed CIs on the path → CARE **fallback** (tier 2).
3. Causal verify: root anomalous, upstream of seed, onset precedes downstream symptoms → **tier 3**.
4. Signature inferred from `irq_affinity_numa_mismatch` / `kernel_rx_queue_latency_ms` → `cross_numa_irq_affinity`.

### 4.2 Chain Lean reported

```
np17-irq-affinity → nic-rx-queue-7 → dns-aaaa-np17 → payment-service → checkout-service
```

`payment-provider` is a sibling decoy branch: crossed and high (~17.8 s) but **later onset** than IRQ, so it does not win.

### 4.3 Evidence (high signal)

| Kind | Example |
|------|---------|
| Anomaly | `irq_affinity_numa_mismatch=1` on `np17-irq-affinity` at T₀ |
| Anomaly | `kernel_rx_queue_latency_ms≈2937` on `nic-rx-queue-7` |
| Anomaly | `dns_query_latency_p99_ms≈3359` (AAAA / NP-17) |
| Event | infra: node image `2026.06.18` + IRQ affinity WARN |
| Event | kernel: cross-NUMA RX queue 7 messages |
| Event | rare `dns.resolver` AAAA latency warnings |

Efficiency on this small graph: `obs_to_convergence=5` / naive BFS `5` (ratio 1.0).

### 4.4 Lean caveats

- Frozen pack — shared Detect over raw series was not exercised.
- Contributor list empty in verdict (GT lists RX + DNS); ObserveOps datastore contributor rules did not fire.
- Remediation text is generic; scenario fix lives in GT / `scenario.md`.

---

## 5. Federated analysis

**Result:** root `np17-irq-affinity` · signature stamped from GT · tier **2** · `fallback_fired=true` · ~**17.6 s**.

### 5.1 How it reasoned

1. Murphy store from topology + crossed anomalies; Panorama → Murphy → Nezha.
2. Murphy hop ≈ all wall time (~17.6 s); posterior **1.0**.
3. Fusion first preferred **`payment-service`** (mid-chain, closer to the symptom).
4. Override: earliest crossed anomaly **upstream** of the fused entity → `np17-irq-affinity`  
   (`fallback_reason=earliest_onset_upstream:np17-irq-affinity`).

Without that override, Federated would have failed vs GT (`payment-service`).

### 5.2 Signature fairness

Federated **copies signature from `ground_truth.json`** on this bakeoff path. Lean’s signature ✓ is the fair Identify comparison; Federated’s signature ✓ means “GT was present,” not “Federated named the fault class.”

### 5.3 Federated caveats

- Murphy propagation rules are ObserveOps/VMware-oriented; e-com signals do not map cleanly — hence mid-chain pull until onset override.
- Contributor CIs in the verdict come from GT helpers, not independent discovery.
- ~17.6 s vs Lean ~7 ms — fine for offline compare, not interactive SRE on this pack shape.

---

## 6. Head-to-head (same parameters, plain reading)

| Parameter | What the comparison is | Lean | Federated | Who “wins” |
|-----------|------------------------|------|-----------|------------|
| **Root vs GT** | Final `root_ci` == GT? | Pass | Pass | Tie |
| **Path to root** | Straight shot or corrected miss? | Walk + CARE/causal | Murphy miss → onset fix | Lean cleaner |
| **Provider false lead** | Final answer ≠ `payment-provider`? | Yes | Yes (final) | Tie (Fed was tempted at `payment-service`) |
| **Identify (signature)** | Engine *named* the fault class from data? | Yes (inferred) | No (GT stamped) | **Lean** |
| **Latency** | Wall-clock diagnose time | ~7 ms | ~17.6 s | **Lean** |
| **Evidence trail** | How rich is the SRE-facing evidence list? | Anomalies + change/kernel/DNS events | Crossed anomalies mainly | Lean richer |
| **Verify** | How strongly does the engine claim cause? | Tier 3 + causal_log | Tier 2 + posterior + override | Lean clearer |
| **Verifiability** | Human can audit *why* from emitted artifacts? | Yes (tier, CARE, causal_log, evidence) | Partial (fusion/posterior + override string) | **Lean** |
| **Reproducibility** | Identical input → identical `verdict.json` hash (N=20)? | **100%** bit-identical | **0%** bit-identical (2 hashes: 17+3); root always GT | **Lean** |

### What verifiability and reproducibility mean here

| Axis | Plain meaning | Measured on `ecom-numa-001` |
|------|---------------|-----------------------------|
| **Verifiability** | SRE can reconstruct *why* from the verdict alone (no source dive). | Lean: High (tier + CARE + causal_log + evidence). Federated: Medium (posterior + override). |
| **Reproducibility** | Same pack × N=20 → bit-identical `verdict.json` (SHA-256). | Lean **100%** (1 hash / 20). Federated **0%** (2 hashes) — Murphy posterior sometimes `1.0` (17 runs) vs ~`0.89` (3 runs); fusion also varies (`payment-service` vs `nic-rx-queue-7` before override). **Root CI stayed GT every run.** |

Prefix: `ecom-repro-v1` · reports: [`reproducibility_lean_ecom_ecom-repro-v1.json`](../benchmarking/results/reproducibility_lean_ecom_ecom-repro-v1.json) · [`reproducibility_federated_ecom_ecom-repro-v1.json`](../benchmarking/results/reproducibility_federated_ecom_ecom-repro-v1.json)

```bash
.venv/bin/python benchmarking/benchmark/run_reproducibility.py \
  --engine lean --n 20 --prefix ecom-repro-v1 \
  --corpus datasets/ecom_checkout/incidents --ids ecom-numa-001
# same for --engine federated
```

Refs: [`RCA_EVALUATION_CHECKLIST.md`](./RCA_EVALUATION_CHECKLIST.md) · [`GLOSSARY.md`](./GLOSSARY.md) · UC scoreboard [`../benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md).

**ADR-001 alignment:** root is infra misconfiguration (node image / IRQ), amplified by app dimensions. Lean’s topology + onset + CARE fits; Federated adds cost and still leans on the same temporal heuristic.

**Where Federated could still matter later:** real trace/path pattern drift (Nezha Step 2) — not exercised on this frozen pack.

---

## 7. What this run does *not* claim

- Engines did **not** discover root from raw OTEL without a pack (Detect was frozen anomalies).
- Federated did **not** independently name `cross_numa_irq_affinity`.
- Results are **not** comparable to Motadata 7/7 or ObserveOps 5/5.
- MTU decoy is in raw metrics but **not** packed as a crossed anomaly (would poison Federated’s global-earliest heuristic). Provider decoy **is** on-path and was the hard false lead.

---

## 8. Artifact index

| Path | Contents |
|------|----------|
| [`../datasets/scenario.md`](../datasets/scenario.md) | Full scenario design |
| [`../datasets/ecom_checkout/incidents/ecom-numa-001/ground_truth.json`](../datasets/ecom_checkout/incidents/ecom-numa-001/ground_truth.json) | Authored GT |
| [`../datasets/ecom_checkout/incidents/ecom-numa-001/`](../datasets/ecom_checkout/incidents/ecom-numa-001/) | Engine pack |
| [`../_adhoc/ecom-gold-report-compare/COMPARISON.md`](../_adhoc/ecom-gold-report-compare/COMPARISON.md) | Compact scoreboard (ad-hoc) |
| [`../benchmarking/results/lean/ecom/ecom-numa-001/run-ecom-20260722T110736Z/`](../benchmarking/results/lean/ecom/ecom-numa-001/run-ecom-20260722T110736Z/) | Lean verdict + meta |
| [`../benchmarking/results/federated/ecom/ecom-numa-001/run-ecom-20260722T110736Z/`](../benchmarking/results/federated/ecom/ecom-numa-001/run-ecom-20260722T110736Z/) | Federated verdict + hops |
| `ingestion-poc/adapters/export_scenario_postgres_json.py` | Postgres → JSON |
| `ingestion-poc/adapters/build_ecom_scenario_pack.py` | JSON → pack |
| `benchmarking/benchmark/run_ecom_bakeoff.py` | Dual-engine driver |
| [`../benchmarking/results/reproducibility_lean_ecom_ecom-repro-v1.json`](../benchmarking/results/reproducibility_lean_ecom_ecom-repro-v1.json) | Lean N=20 repro report |
| [`../benchmarking/results/reproducibility_federated_ecom_ecom-repro-v1.json`](../benchmarking/results/reproducibility_federated_ecom_ecom-repro-v1.json) | Federated N=20 repro report |
| [`schemas/comprehensive_incident_report.v1.json`](./schemas/comprehensive_incident_report.v1.json) | Shared comprehensive RCA schema |
| `benchmarking/benchmark/comprehensive_rca_report.py` | Pack+raw+verdict → incident_report.md/json |
| [`../_adhoc/ecom-gold-report-compare/reports/lean/incident_report.md`](../_adhoc/ecom-gold-report-compare/reports/lean/incident_report.md) | Lean comprehensive report (ad-hoc) |
| [`../_adhoc/ecom-gold-report-compare/reports/federated/incident_report.md`](../_adhoc/ecom-gold-report-compare/reports/federated/incident_report.md) | Federated comprehensive report (ad-hoc) |
| [`../_adhoc/ecom-gold-report-compare/reports/gold/incident_report.md`](../_adhoc/ecom-gold-report-compare/reports/gold/incident_report.md) | Gold OO write-up (ad-hoc) |
