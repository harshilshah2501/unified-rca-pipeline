# ObserveOps Benchmark Contract

**Corpus:** `datasets/observeops/` (UC-1..UC-5 primary; **UC-3b** + `events.json` frozen in corpus v1.1.0)  
**Source:** [rca-use-cases-only.md](../../docs/rca-use-cases-only.md)  
**Comparison output:** `benchmarking/results/comparison/COMPARISON.md`

## Ground truth

This contract is how Motadata ObserveOps addresses **Roadblock 4** (no field-wide standardized GT): we do not invent an industry benchmark, but we **require** a corpus-local shared GT so Accuracy and federated-vs-lean comparison are defined. See [`docs/README.md`](../../docs/README.md) and the Eval contract in the use-case spec.

| UC | Root CI | Signature | Pass | Fail |
|----|---------|-----------|------|------|
| UC-1 | `esxi-host-01` | `cpu_contention` | Root = host | Blame app/VM only |
| UC-2 | `switch-core-01:GigE0/2` | `link_failure` | Root = switch port | Blame app/server |
| UC-3 | `datastore-01` | `storage_contention` | Root = datastore; contributor includes noisy neighbor when present | Blame DB app only |
| UC-3b | `datastore-01` | `storage_contention` | Same as UC-3 **despite** earlier unrelated switch anomaly | Root = switch due to earliest onset |
| UC-4 | `guest-os-vm-app-01` | `os_resource_exhaustion` | Root = guest OS; cite events when present | Blame app or infra below |
| UC-5 | `orders-api` | `app_resource_exhaustion` | Root = app; upstream healthy | False-blame infra |

## Metrics (scored identically for federated and lean)

| Metric | Definition |
|--------|------------|
| `top1_root_ci_correct` | `verdict.root_ci == ground_truth.root_ci` |
| `signature_match` | `verdict.signature == ground_truth.signature` |
| `contributor_match` | UC-3/UC-3b: noisy-neighbor id ∈ `verdict.contributor_cis` when GT lists one |
| `false_infra_blame` | UC-5 only: root in host/switch/datastore when GT is app |
| `observations_to_verdict` | Count of CI checks / graph expansions |
| `reproducibility_pct` | % of N=20 runs with bit-identical `verdict.json` |
| `verifiability_pass` | Evidence cites decisive signals from use-case table (b) and events from (b2) when present |

## Four-axis scoring

| Axis | Federated | Lean |
|------|-----------|------|
| Reproducibility | Same bundle → same verdict | Same |
| Verifiability | Inspectable evidence trail | Same + `evidentiary_tier` |
| Accuracy | top-1 vs ground truth (Mandatory KPI with a declared floor; 5/5 on this tiny corpus is smoke, not a forever-100% rule) | Same |
| Causal Validity | Murphy partial (if claimed; costly if global) | Tier 3 only (CARE + scoped causal check) — Recommended, not Mandatory on every UC |

## Lean-only fields

- `evidentiary_tier`: 1 (main path), 2 (CARE), 3 (CARE + causal check)
- `fallback_fired`: boolean
- **Never blend Tier 1/2/3 accuracy in reports**

## UC-5 anti-false-positive rule

When `ground_truth.upstream_healthy == true`, a verdict blaming `esxi-host-01`, `switch-core-01:GigE0/2`, or `datastore-01` is an automatic **fail**.

## Run parameters

- `N_REPRODUCIBILITY_RUNS = 20`
- `DELTA_T_SECONDS = 10` (CARE trigger window; 2× clock-skew bound for PoC)
