# Lab SLO worksheet (Design v3 Stages 0–3)

Synthetic lab only. Thresholds below are **tracking targets** for experiment reporting — not Motadata production SLOs until real estates exist.

## Use cases

| ID | Use case | Success definition |
| -- | -------- | ------------------ |
| U1 | Cold → walk rebuild | Decode + build out-adjacency + first forward BFS (hops=2) completes; index ready |
| U2 | Forward Scope walk | Forward BFS from seed on hot index; hops ∈ {1,2,3}; no Vortex I/O |
| U3 | Reverse blast | Incoming-neighbor BFS (needs CSC or scan); hops=2 |
| U4 | Hybrid mutate+query | After N inserts/deletes on delta, forward BFS matches oracle effective graph |

## Metrics tracked

| Metric | Where | Percentiles |
| ------ | ----- | ----------- |
| `total_cold_to_walk_ms` | U1 | p50, p95 across timed repeats (N≥20 for Stage 1) |
| `build_ms` | U1 | p50, p95 |
| `query_ms` | U2/U3/U4 | p50, p95 over **per-query** events (≥200/cell in Stage 3) |
| `peak_rss_bytes` | process | high-water mark (VmHWM) |
| Correctness | all | reachable-set checksum match vs hash reference |

**Do not claim robust p99** from twenty run-level observations. Prefer high-volume query JSONL for tails.

## Readiness

**Ready** = out-adjacency (or CSR/CSC/hybrid effective view) built and first correctness check passed for the contracted query class.

## Lab budgets (aspirational)

| Scale | U1 p95 cold→walk (clustered + sort_aware hash) | Peak RSS |
| ----- | ---------------------------------------------- | -------- |
| 500k edges | track vs Report 02 baseline (~80–150 ms class) | measure |
| 1M edges | track vs Report 02 (~175 ms clustered full) | measure |

Owner for production thresholds: deferred until Stage 0 real-estate instrumentation.
