# Glossary — engine and bakeoff terms

Short definitions for lean, federated, ingest, and corpus docs.

Hub terms (HLD, Dynatrace, Datadog, flamegraph, Detect class, …) live in the browser glossary:

[`urca-glossary.html`](../urca-glossary.html) (`:8765/urca-glossary.html`).

---

## A–Z

**CARE** — Lean correlational ranking when several onsets sit in the same Δt window. Not a causal claim by itself.

**Corpus A** — Deferred microservice / DeathStarBench-style track in the Lean PRD. Not the ObserveOps bakeoff.

**Corpus B / ObserveOps UC** — Frozen synthetic classic-infra use cases in `datasets/observeops/` (v1.1.0). Shared ground truth; primary lean vs federated bakeoff.

**F1** — Ingest profile: write for Lean **and** Federated (dual-sink). Not “Federated only.” There is no F0 in this PoC.

**F2** — Heavier Federated ingest (more traces/logs). Optional / stretch.

**fallback_fired** — Bakeoff flag. `false` = main path; `true` = engine used a rescue path. Coarser than lean Tier 1/2/3.

**Federated hop** — Orchestrator step order Panorama → Murphy → Nezha. Not the same numbering as lean evidentiary tiers.

**L0** — Ingest profile: write stores only for Lean (cheaper baseline).

**main-path %** — Share of verdicts with `fallback_fired: false`. Not “more Tier 1.” Lean can fire CARE (Tier 2/3) and still be more verifiable.

**Motadata ingest stream** — `datasets/ingest_samples/motadata-ingest/` — derived `ingest.v1` plus L1 incident packs with human GT.

**Motadata resolved dump** — `datasets/ingest_samples/jsonl_resolved/` — local ClickHouse export (large files gitignored).

**Murphy** — Federated hop: which upstream entity best explains the symptom (MRF / Gibbs).

**Nezha** — Federated hop: which execution-path or event patterns shifted inside that entity.

**ObserveOps replay (`ingest.v1`)** — `datasets/ingest_samples/observeops-replay/` — normalized JSONL from frozen UCs for Vector / writers. Not a second bakeoff corpus.

**OpenObserve incidents** — `datasets/openobserve_incidents/v1/` — real incident packs; different GT contract. Do not merge with the ObserveOps 5/5 scoreboard.

**Panorama (fair bakeoff)** — Off the ObserveOps UC scoreboard; Federated Hop-1 consumes shared Detect.

**parity-shared-detect** — Both engines get the same alerts from one threshold detector; score Localize only.

**Seed (teaching)** — Curate tip `(entityId, t0)` for Tailor. Not `rootCauseEntity`.

**Storage tier** — Federated **storage Tier** 1/2: speed vs structural persistence (Dragonfly / graph store) in [`federated-pipeline/docs/STORAGE_TIERS.md`](../../federated-pipeline/docs/STORAGE_TIERS.md). Unrelated to lean evidentiary tiers and unrelated to **hub Tier** (Our HLD reading depth).

**Storm (teaching)** — Pile of raw Events before Curate merge.

**symptom seed** — CI/signal where pain showed. Start of the search; usually not the root.

**Tier (hub)** — Our HLD / Motadata **docs reading depth**: hub Tier 1 = must-read above the fold; hub Tier 2 = depth (LLDs, fabric, I/O chain); hub Tier 3 = archive / evaluation history. Locked list: [`OUR_HLD_TIER1.md`](../observeops/OUR_HLD_TIER1.md). Not evidentiary Tier and not storage Tier.

**Tier (lean evidentiary)** — Lean verdict depth. **Tier 1** = main path, temporal + rules, no causal claim. **Tier 2** = CARE ranking when Δt is ambiguous. **Tier 3** = CARE + scoped causal check. Default reading of bare “Tier 3” in bakeoff docs unless the page says **hub Tier** or **storage Tier**.

**Teaching threshold 0.30** — ERROR Detect chalk line on the storyboard. Not a fitted Dynatrace SKU. SLOWDOWN Observed used 2 s / 3 s, not 0.30.

---

## Fault-bucket labels (dashboard)

| Id | Label | Meaning |
|----|-------|---------|
| `1_symptom` | Symptom-layer | What users notice first; root may still be elsewhere |
| `2_infra` | Infrastructure | Host / network / storage / OS |
| `3_application` | Application | App / service dependency |
| `4_external` | External / change | Deploy / outside organic ops |

See [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md).

---

## Evaluation phrase

**Bakeoff evaluation finding:** lean is the primary evaluation engine for the ObserveOps UC corpus ([ADR-001](./ADR-001-lean-primary-engine.md)); **not a finalized GTM or product commitment.**
