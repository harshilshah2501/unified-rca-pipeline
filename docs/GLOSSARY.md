# Glossary — disambiguation

Terms reused across lean, federated, and benchmarking docs.

## Tier (three namespaces)

| Namespace | Where | Meaning |
|-----------|-------|---------|
| **Lean evidentiary tier** | Lean verdict / SRE report | **Tier 1** = main path, temporal + rules, no causal claim. **Tier 2** = CARE correlational ranking when Δt is ambiguous. **Tier 3** = CARE + scoped causal check. See [`POC_BRIEFING.md`](./POC_BRIEFING.md) §15. |
| **Federated pipeline step** | Panorama → Murphy → Nezha orchestration | Hop order in the federated stack — **not** the same as lean Tier 1/2/3. |
| **Storage tier** | [`federated-pipeline/docs/STORAGE_TIERS.md`](../federated-pipeline/docs/STORAGE_TIERS.md) | Speed vs structural persistence design (Dragonfly / graph store) — unrelated to lean evidentiary tiers. |

When a doc says “Tier 3” without qualification, assume **lean evidentiary tier** unless the path is under `federated-pipeline/docs/STORAGE_TIERS.md`.

## Ingest profiles (L0 / F1)

| Tag | Plain meaning | Not |
|-----|---------------|-----|
| **L0** | Write stores **only for Lean** (cheaper baseline) | — |
| **F1** | Write for Lean **and** Federated (dual-sink; L0 + Federated feeds) | **Not** “Federated only” — there is no F0 in this PoC |
| **F2** | Heavier Federated path (more traces/logs) | Optional / stretch |

Cost compare asks: same input bytes, how much **extra** does dual-sink cost? See [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) §6.

## Shared Detect / symptom seed

| Term | Plain meaning |
|------|----------------|
| **parity-shared-detect** | Both engines get the same alerts from one threshold detector; score Localize only. |
| **symptom seed** | CI/signal where pain showed — **start** of the search, usually **not** the root. |
| **Panorama (fair bakeoff)** | Off the ObserveOps UC scoreboard; Federated Hop-1 consumes shared Detect. |

## Fault buckets (Samples / coverage)

Dashboard labels (ids stay `1_symptom` … in data):

| Id | Label | Meaning |
|----|-------|---------|
| `1_symptom` | Symptom-layer | What users notice first; root may still be elsewhere |
| `2_infra` | Infrastructure | Host / network / storage / OS |
| `3_application` | Application | App / service dependency |
| `4_external` | External / change | Deploy / outside organic ops |

See [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md).

## Corpus names

| Name | Path | Role |
|------|------|------|
| **ObserveOps UC / Corpus B** | `datasets/observeops/` v1.1.0 | Frozen synthetic classic-infra UCs; shared GT; primary lean vs federated bakeoff (`adr001-rerun-20260723`). |
| **Corpus A** | Deferred | Microservice / DeathStarBench-style track in Lean PRD — not the ObserveOps bakeoff. |
| **OpenObserve incidents** | `datasets/openobserve_incidents/v1/` | Real incident packs; different GT contract — **do not merge** with ObserveOps 5/5 scoreboard. |
| **ObserveOps replay (`ingest.v1`)** | `datasets/ingest_samples/observeops-replay/` | Normalized JSONL from frozen UCs for Vector / writers — not a second bakeoff corpus. |
| **Motadata resolved dump** | `datasets/ingest_samples/jsonl_resolved/` | Local ClickHouse export (gitignored large files); product-shaped ingest source. |
| **Motadata ingest stream** | `datasets/ingest_samples/motadata-ingest/` | Derived `ingest.v1` + L1 incident packs (`incidents/motadata-*`) with human GT — shown on console `#incident` + `#samples`. |

## Verifiability vs main-path %

**Lean Tier 1/2/3** is lean-only (evidentiary depth). Federated does not use that ladder.

The bakeoff’s shared **main-path %** is a different, coarser metric: % of verdicts with `fallback_fired: false`.

| Engine | `fallback_fired: false` | `fallback_fired: true` |
|--------|-------------------------|------------------------|
| Lean | CARE did not fire (Tier 1) | CARE fired (Tier 2/3) |
| Federated | Fusion path (no lean-rule rescue) | Fell back to lean helpers after weak Murphy |

Lean may score **lower** main-path % when CARE fires (UC-1, UC-3) while still winning **Verifiability** for SRE audit: explicit tier labels, CARE flags, causal logs, and evidence citations. Federated’s higher no-fallback % is **not** “more Tier 1.” See [`benchmarking/results/comparison/COMPARISON.md`](../benchmarking/results/comparison/COMPARISON.md).

## Evaluation verdict (standard phrase)

**Bakeoff evaluation finding:** lean is the primary evaluation engine for the ObserveOps UC corpus ([ADR-001](./ADR-001-lean-primary-engine.md)); **not a finalized GTM or product commitment.**
