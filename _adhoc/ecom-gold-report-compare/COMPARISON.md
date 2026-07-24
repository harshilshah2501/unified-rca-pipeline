# E-com checkout — Lean vs Federated (ecom-numa-001)

**run_id (accuracy cite):** `ecom-20260722T110736Z`  
**repro prefix:** `ecom-repro-v1` (N=20)

**Full analysis:** [`docs/ECOM_CHECKOUT_RCA_ANALYSIS.md`](../../docs/ECOM_CHECKOUT_RCA_ANALYSIS.md)

## Ground truth
- root_ci: `np17-irq-affinity`
- signature: `cross_numa_irq_affinity`

## Results (accuracy cite)

| Engine | Status | Root | Signature | Latency ms | Fallback |
|--------|--------|------|-----------|------------|----------|
| Lean | **pass** | `np17-irq-affinity` ✓ | `cross_numa_irq_affinity` ✓ | 6.5794 | True |
| Federated | **pass** | `np17-irq-affinity` ✓ | `cross_numa_irq_affinity` ✓ | 17603.5953 | True |

## Reproducibility (N=20, bit-identical `verdict.json`)

| Engine | Bit-identical packs | Unique hashes | Notes |
|--------|---------------------|---------------|-------|
| Lean | **100%** (1/1) | 1 / 20 | Deterministic walk |
| Federated | **0%** (0/1) | 2 / 20 | Root always GT; posterior/path noise (17× vs 3×) |

Reports: `reproducibility_lean_ecom_ecom-repro-v1.json`, `reproducibility_federated_ecom_ecom-repro-v1.json`

## Notes
- Scenario: `datasets/scenario.md` (cross-NUMA IRQ affinity on NP-17).
- Data path: Postgres → JSON → engine pack.
- False lead on path: `payment-provider`.
- Federated stamps GT signature; Lean infers it.
- Federated first fuses to mid-chain CI, then overrides via `earliest_onset_upstream`.
