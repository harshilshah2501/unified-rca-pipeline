# Federated Justification Report (template)

**Purpose:** Decide with **PoC data** whether Federated should be promoted beyond optional on microservice workloads.  
**Policy:** [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md) §3b · [`POC_BRIEFING.md`](./POC_BRIEFING.md) §7  
**Status:** Template — fill after microservice validation runs

---

## 1. Run metadata

| Field | Value |
|-------|-------|
| Report ID | `fed-justification-YYYYMMDD` |
| Dataset | e.g. `datasets/ingest_samples/microservice-suite/` |
| Incident count | |
| Input mode | frozen replay / live capture |
| Hardware | e.g. pro6000-server 16c / 125GiB |
| Ingest profile | F1 dual-sink + shared detect |
| Run IDs (Lean / Federated) | |
| Authors / date | |

---

## 2. Hypothesis under test

> On a **microservice-heavy** incident set, Federated (Panorama + Murphy + Nezha on ingested stores) delivers materially better diagnosis outcomes than Lean on the **same ingest stream**, without unacceptable cost/repro/FP regression.

---

## 3. Promotion gates (pass/fail)

| Gate | Metric | Threshold (promote Federated) | Lean value | Federated value | Pass? |
|------|--------|-------------------------------|------------|-----------------|-------|
| **G1** | Root-CI accuracy | Fed − Lean ≥ **8 pp** | | | |
| **G2** | Gray-failure capture rate | Fed − Lean ≥ **20 pp** | | | |
| **G3** | False-positive rate | Fed − Lean ≤ **+3 pp** | | | |
| **G4** | Reproducibility (N=20) | Fed ≥ **85%** | | | |
| **G5** | Cost per correct diagnosis | Within budget cap: $____ | | | |
| **G6** | System p95 latency (detect+RCA) | ≤ ____ ms @ ____ EPS | | | |

**Overall promotion:** Pass **G1 or G2** plus **G3, G4, G5, G6** (all four).

---

## 4. Per-incident scoreboard

| Incident ID | Class | GT root | Lean root | Fed root | Lean ✓ | Fed ✓ | Gray-failure? | Lean miss reason | Fed advantage? |
|-------------|-------|---------|-----------|----------|--------|-------|---------------|------------------|----------------|
| MS-001 | retry_storm | | | | | | | | |
| MS-002 | path_regression | | | | | | | | |
| MS-003 | deploy_churn | | | | | | | | |
| MS-004 | cross_svc_contention | | | | | | | | |

**Incident classes required:** retry_storm, path_regression, deploy_churn, cross_svc_contention (minimum 4; target ≥12 incidents).

---

## 5. Accuracy summary

| Engine | Root-CI pass | Signature pass | Gray-failure capture | FP (infra blame / wrong svc) |
|--------|--------------|----------------|----------------------|------------------------------|
| Lean | /N | /N | /N gray | /N |
| Federated | /N | /N | /N gray | /N |

Formulas:

- `accuracy = root_ci_pass / N`
- `gray_capture = gray_incidents_correct / gray_incidents_total`
- `fp_rate = false_positives / N`

---

## 6. Reproducibility (N=20)

| Incident | Lean stable hashes | Fed stable hashes | Lean % | Fed % |
|----------|-------------------|-------------------|--------|-------|
| MS-001 | /20 | /20 | | |
| … | | | | |
| **Overall** | | | | |

---

## 7. Cost & latency (same EPS profile)

| Bucket | Lean | Federated | Notes |
|--------|------|-----------|-------|
| C_detect | | | shared vs panorama |
| C_collect + normalize | | | Vector |
| C_store | | | L0 vs F1 |
| C_rca_runtime | | | |
| **System total** | | | detect + ingest + RCA |
| p95 system latency | | | ms |
| EPS sustained | | | |

Cost per correct diagnosis:

```
cost_per_correct = system_total_cost / correct_diagnoses
```

---

## 8. Federated hop attribution (sample incident)

| Hop | Component | latency_ms | Notes |
|-----|-----------|------------|-------|
| 1 | shared_detect / panorama | | |
| 3 | murphy | | |
| 5 | nezha | | |

---

## 9. Decision

| Outcome | Criteria met | Recommendation |
|---------|--------------|----------------|
| ☐ Promote Federated for microservice track | G1/G2 + G3–G6 | Build M3 ingest + product path |
| ☐ Hybrid | Fed wins subset only | Domain-scoped Federated; Lean default elsewhere |
| ☐ Keep Lean-primary | Gates failed | Federated remains optional comparator |

**Decision:**  
**Rationale (data cites):**  

---

## 10. Artifacts to attach

- [ ] `comparison.json` / COMPARISON.md for microservice run id
- [x] `cost_report.md` (L0 vs F1) — [`cost-pro6000-20260721Tfinal`](../benchmarking/results/costing/cost-pro6000-20260721Tfinal/)
- [ ] `hop_logs.json` per incident (Federated)
- [ ] `run_meta.json` (detect + RCA timings both engines)
- [ ] Ingest manifest: [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) compliance checklist

---

## 11. References

- Ingest format: [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md)
- Pipeline plan: [`INGESTION_POC_PLAN.md`](./INGESTION_POC_PLAN.md)
- Parity: [`PIPELINE_PARITY.md`](./PIPELINE_PARITY.md)
