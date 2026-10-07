# sketch-vortex-bench

Physical Vortex layout experiment for Motadata **sketch.v2**-shaped rows.

This crate answers: for staged RCA reads (locate → distribution → exemplar), which
physical column shape minimizes **decode cost** under Vortex’s zone / flat-chunk /
buffered-run layout strategy?

It does **not** lock a product sketch schema. Map cold parts stay in
[`../../pillar-b/map-vortex/`](../../pillar-b/map-vortex/).

Program hub (sketch + map benches, detailed reports, comparative analysis):
[`../README.md`](../README.md) · [`../reports/01-sketch-physical-layout.md`](../reports/01-sketch-physical-layout.md)

## Layouts

| Id | Shape |
|----|--------|
| `A_nested` | Logical nested structs (`tdigest`, `buckets`, `exemplars`) |
| `B_flat_wide` | Fully flat; Stage‑1 queries deliberately project `*` (anti-pattern) |
| `C_spine_nested_cold` | Flat hot spine + one nested `cold_evidence` struct |
| `D_spine_flat_evidence` | Flat spine + flat distribution/exemplar columns; staged projections |
| `E_split_tables` | Separate `spine.vortex` / `distribution.vortex` / `exemplars.vortex` |

Row sort orders: `natural` (interleaved) vs `clustered` (`tenant → entity_id → metric_id → window_start`).

## Queries (Q1–Q8)

Staged projections matching [`Vortex-unit-check.md`](../../../Vortex-unit-check.md):

- **Stage 1:** Q1, Q2, Q3, Q7, Q8 — identity / anomaly / percentiles / baseline
- **Stage 2:** Q4 — bucket counts (+ schema id)
- **Stage 3:** Q5, Q6 — exemplar pointers / trace ids

Metrics recorded: file bytes, write ms, projected columns, decode ms (median),
rows decoded, post-decode filter matches. Zone pushdown filters are a follow-up.

## Run

```bash
cd pillar-ab-implementation/vortex-bench/sketch-vortex-bench
cargo build --bin sketch_vortex_bench

# Smoke
cargo run --bin sketch_vortex_bench -- \
  --rows 5000 --entities 64 --out out/smoke --warmup 0 --repeats 1

# Larger (still lab-scale)
cargo run --release --bin sketch_vortex_bench -- \
  --rows 100000 --entities 256 --sort clustered \
  --out out/run-100k-clustered --warmup 1 --repeats 3

# Target scale from the design note
cargo run --release --bin sketch_vortex_bench -- \
  --rows 1000000 --entities 1024 --sort clustered \
  --out out/run-1m-clustered --warmup 1 --repeats 3
```

Compare sort locality:

```bash
cargo run --release --bin sketch_vortex_bench -- \
  --rows 100000 --sort natural --out out/run-100k-natural
cargo run --release --bin sketch_vortex_bench -- \
  --rows 100000 --sort clustered --out out/run-100k-clustered
```

Results: `<out>/results.json` plus a Stage‑1 summary on stdout.

## Reading results

Prefer **Stage‑1 decode_ms** (Q1/Q2/Q7) and total bytes:

- `B_flat_wide` with `*` should be worst on Stage‑1 (decodes T‑Digest + exemplars early).
- `D_spine_flat_evidence` / `C_spine_nested_cold` / `E_split_tables` should be closer on Stage‑1.
- Stage‑2/3 show whether nesting (`cold_evidence` / `exemplars` struct) over-fetches vs flat exemplar columns.

Hypothesis to confirm at 1M rows: **hot spine + progressive cold columns** (D or E), not nested-as-default and not naive wide `*`.
