# Stage exit gates

## Stage 0

- [x] SLO worksheet, trace schema, run manifest schema, oracle, factor registry published under `design-v3/`.

## Stage 1

- [x] Reproduce Report 02 / follow-up **2×2** (order × builder) at 500k edges, uniform + hubby, spine, process_cold, N=20.
- [x] Manifests under `map-vortex-bench/out/design-v3/stage1/`.
- [x] Report 04 records main effects + interaction; no confounded natural+naive vs clustered+sort_aware-only comparison.

## Stage 2

- [x] Screening ranks material factors (order, builder×order, shape×query tails, load decode share).
- [x] Report 05 names which interactions deserve Stage 3 depth.
- [x] Per-query JSONL written for screened cells.

## Stage 3

- [x] All four layouts measured at 250k / 500k / 1M × uniform+hubby with correctness_ok.
- [x] Pareto of build_ms × query p95 × peak RSS documented in Report 06.
- [x] Explicit gate call: adopt clustered+sort_aware **hash** vs prototype CSR/CSC vs hybrid — synthetic-only caveat required.

## Stage 3.5 (critical-review remediation)

- [x] Bidirectional hash (`hash_bi`) measured against hash / CSR / CSR+CSC / hybrid.
- [x] Same reverse query mix for **every** layout; reverse algorithm documented per layout.
- [x] Per-class latency (forward / reverse / dependency_chain) in results + Report 07.
- [x] Hybrid occurrence-count delete semantics documented (not edge_id).
- [ ] Disk-cold / remote-cold (deferred — labels clarified only).

## Stage 4.0–4.2 (workload-informed synthetic)

- [x] 4.0 contracts + six estate generators + property validators + query-trace emitter.
- [x] 4.1 property reports for all families at 500k/1M/5M (Report 08).
- [x] 4.2 layout screen ≤5M with identical traces; Report 09 crossover candidates (not production lock). Full factorial at 500k/1M; thin 5M ladder (uniform+hubby × balanced).
- [x] Explicitly deferred: concurrency, mutation economics, 10M+, confirmation batches (4.6).
