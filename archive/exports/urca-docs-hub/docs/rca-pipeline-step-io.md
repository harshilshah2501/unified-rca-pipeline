# RCA Pipeline — Step I/O (§3.2b)

Full step I/O reference. Tailor guess confirmed — details below.

## Pipeline shape (important)

Topology is a **sibling**, not strictly "after all metrics." Case sequencing is **Detect → Curate → Tailor**. Tailor is **case-triggered** Clock A.

```
Collect → Normalize ─┬─► Fan-out → Maintain
                      │
Topology (CI graph) ──┘

Detect → raw alerts
Curate → one honest seed
Tailor(seed) → working set → Clock B
```

## Each step

| Step | Input | Process | Output |
|------|--------|---------|--------|
| **Collect** | Agents, scrapes, OTel, traps, APIs… | Receive/pull raw telemetry | Raw streams (vendor-shaped) |
| **Normalize** | Raw streams | Map to joinable envelope: `ci_id`, signal, `ts`, value… | Normalized stream |
| **Topology bind** | Discovery / CMDB / service map | Build **CI relationship/dependency graph** (nodes + typed edges) + bind LUT (hostname→`ci_id`) | Graph + bind table |
| **Fan-out** | Normalized envelopes | **Route same stream** to cheap and/or rich sinks (L0 vs F1) — **not** a second Detect | Populated stores/bundles |
| **Maintain** | Sinks + graph | Retention, sampling, topo freshness, clock sync (fair compare: matched TTL; L0/F1 differ by payload) | Usable hot/warm lake |
| **Detect** | Streams/stores | Thresholds / anomalies — noisy by design | Raw alert storm |
| **Curate** | Detect’s raw alerts + humans | Storm→one seed, GT, quality flags, no coaching | **One honest seed** `(CI, signal, t0)` |
| **Tailor** | Seed + graph + stores | Cut space/time/modality | **Working set → Clock B** |

## Topology = dependency graph?

**Yes.** Typed **CI graph**: nodes (service, VM, datastore…) + edges (`calls`, `hosted_on`, `uses_datastore`…). That is the relationship/dependency map Localize walks — **not** a request trace.

## Topology bind — two independent inputs, not a conversion

Discovery/CMDB/service map and Normalized stream are **separate systems**, not one feeding the other:

- **CMDB/Discovery/service map** — a system of record (ServiceNow CMDB, service mesh registry, cloud inventory, discovery scanner) that already knows the CIs and their relationships, independent of any telemetry.
- **Normalized stream** — telemetry carrying raw identifiers (hostname, pod name, IP, service name) that don't natively match CMDB's `ci_id`.

Topology bind produces two distinct artifacts from these:

```
CMDB/Discovery ──────► CI Graph (nodes + edges)
                            │
Normalized stream ──► bind LUT (hostname→ci_id) ──► attaches ci_id to each envelope
```

1. **CI Graph** — built only from CMDB/discovery. Nodes + typed edges. What Tailor walks for k-hop neighborhoods.
2. **Bind LUT** — an **identity resolution index**, not a slice or view of the graph. A flat lookup: `hostname/pod/IP/service-name → ci_id`. Its job is to resolve a raw string from telemetry to the canonical node identity that already exists in the graph — the address-lookup table that tells you which pin on the map corresponds to the address written on an envelope.

| | CI Graph | Bind LUT |
|---|---|---|
| Shape | Nodes + typed edges | Flat key→value |
| Purpose | Relationship traversal (Tailor's k-hop) | Identity resolution (tagging each telemetry record) |
| Access pattern | Graph queries (neighbors, paths) | Point lookups, one per incoming record — needs to be fast |
| Store | Graph DB (Neo4j) or edge-list table | KV store (Redis) or in-memory hash |

Both are derived from the same CMDB/discovery source (via a periodic reconciliation job) but serve different consumers. The LUT is applied at ingest time to tag each normalized record with its `ci_id` before it hits the graph-aware steps downstream.

## Fan-out means?

**Cost/consumer routing:** one normalized feed → multiple sinks (Lean-cheap vs Fed-rich). Same Detect; different how much you store for later hops.

**Correction:** L0/F1 is a **storage cost profile**, not the definition of Lean vs Federated. It's enabling infrastructure — Federated's sinks may keep richer modalities / speed-tier keys because Murphy and Nezha need them — but that's a consequence of which algorithms run downstream, not the thing that makes Federated "Federated." See the dedicated section below on what actually distinguishes them.

## Fan-out vs Tailor — different time domains

These do **not** feed each other directly. Fan-out receives the normalized stream directly, continuously, for all traffic — incident or not. Tailor only runs later, per-incident, and **reads back** from whatever fan-out already wrote:

```
Fan-out writes continuously → Lean-cheap store / Fed-rich store
                                        │
                          (later, only on incident)
                                        │
Detect → seed → Tailor reads FROM those stores → working set → Clock B
```

- **Fan-out (step 4)** = always-on ingest routing. Writes every normalized record to Lean and/or Fed sinks as it arrives, regardless of whether any seed will ever fire.
- **Tailor** = query-time operation. Given a seed `(CI, signal, t0)`, it walks the CI graph for the k-hop neighborhood and cuts the time corridor + modalities **out of** whichever stores fan-out already populated. It does not decide what's *in* the sinks — that's fan-out/Maintain's job (retention, sampling policy).

**Note on retention as a general risk, not the Lean/Fed story:** in principle, if a store's retention is shorter than what a query wants to look back, the query can only retrieve what's still there — that's just how any TTL'd store behaves, for either engine. But on the fair ObserveOps UC packs both engines usually see the **same incident kit/corridor**, so retention length is *not* what separates Lean's and Federated's results in the bakeoff. What actually separates them is the algorithm each runs in Clock B — see below.

## Maintain vs Curate?

- **Maintain** = lifecycle (TTL, sample, keep topo fresh).
- **Curate** = quality (dedupe storms, GT, flag gaps, no GT in alerts).

## Detect → Curate → Tailor — real sequencing

What each one does after Maintain:

- **Maintain** — pure housekeeping on the stores (retention/TTL, sampling, topology resync, clock sync). No incident awareness at all; it has no opinion about whether anything is broken. Fair compare: matched TTL; L0/F1 differ by payload richness, not “Fed keeps more history.”
- **Detect** — the actual analytical trigger. Watches maintained streams/stores, scores against thresholds/anomaly baselines. Fires when something breaks — but usually **more than once per real incident**, since one root cause (e.g. a DB pool exhausting) can trip several correlated metrics (latency, error rate, queue depth, CPU…) simultaneously. Each is a separate raw alert. Detect is noisy by design — better to over-fire than miss something.
- **Curate** — sits *on Detect's raw output* (plus historical incidents and human labels), not on the streams directly. Dedupes the correlated storm into **one** honest seed candidate, attaches ground truth for scoring only (never leaked into the live alert), and flags data-quality gaps.
- **Tailor** — case-triggered Clock A: seed + graph + stores → working set for Clock B.

Corrected flow:

```
Maintain: housekeeping on stores, always running, no incident awareness

Detect: watches (maintained) streams/stores → fires raw alerts,
        potentially several per real incident (correlated symptoms)

Curate: takes Detect's raw alerts (+ history + human labels)
        → dedupes storm → ONE honest seed

Tailor: seed → neighborhood + corridor + modalities → working set → Clock B
```

Curate produces the honest seed; Tailor is the bridge into Clock B.

## Tailor cut (your formula)

```
working set =
  seed
+ neighborhood (k-hop / shared-upstream on CI graph)
+ time corridor [t0 − pre, t0 + post]
+ modalities (metrics; +logs/traces per class A–D)
```

That pack is **the** input to Clock B.

## Clock B forks after Tailor — Lean vs Federated

**Shared front half (fair compare):** same Collect, same topology kit, same Detect → same seed → same Tailor cut. Both engines start from an identical working set.

**Different back half:** *how each finds the root* (and optionally the path) diverges completely — this is a different algorithm stack, not a cost variant of the same one.

| | **Lean** | **Federated** |
|---|---|---|
| Role | Primary on classic infra (ADR-001) | Optional comparator / hybrid for gray-failure + path depth |
| Localize | Typed **CI graph walk**: best-first/info-gain + onset + ObserveOps rules (shared-upstream, signatures); **CARE** escalates only if onsets clump in Δt | **Murphy** — MRF + Gibbs sampling over a dependency/structural graph → posterior over entities |
| Identify / path | Signatures / fault class, light structured events — **not** path mining as the main mechanism | **Nezha** — expected vs actual execution **patterns** (speed-tier `tg:`/`pc:` when enabled) |
| **Verify** | Evidentiary Tier 1/2/3 + CARE → scoped causal | Orchestrator **fusion** of Murphy + Nezha (confidence / overrides; not Lean tiers) |
| Detect (Fed-specific) | Shared thresholds/alerts (on the fair board) | Can use **Panorama** (LOS/gray-failure) — **not** on the fair scoreboard |
| Storage vision | One coherent graph + incident kits | Dual tier: structural (Murphy/Panorama) + speed Event Graph (Nezha `tg:`/`pc:`) — richer Fan-out, not “longer TTL = Federated” |
| Why Lean preferred on UC bakeoff | Bit-stable, clear tier trail, same 5/5 accuracy, lower cost | Repro weaker (~40% Gibbs variance); CV story stronger on paper, not needed for classic UC top-1 |

**One sentence:** Federated is a **different algorithm stack** (Panorama → Murphy → Nezha + orchestrator), not "Lean with a bigger window."

Corrected diagram:

```
Collect → Normalize → Topology bind → Fan-out → Maintain → Detect (shared) → Curate → seed
                                                                                      │
                                                                                   Tailor (shared cut, Clock A)
                                                                                      │
                          ┌───────────────────────────────────────────────────────────┴───────────────────────────────────────────┐
                          │ LEAN branch                                                                    FEDERATED branch        │
                          │ Localize: CI graph walk (best-first/info-gain + onset + ObserveOps rules;      Localize: Murphy         │
                          │           CARE escalates only if onsets clump in Δt)                            (MRF + Gibbs sampling)  │
                          │ Identify: signatures / fault class                                              Identify: Nezha         │
                          │           (light structured events, not path mining)                            (execution pattern      │
                          │                                                                                  mining)                │
                          │ Verify:   tier verification                                                     Verify: fusion          │
                          │                                                                                  (orchestrator;          │
                          │                                                                                  Panorama = optional     │
                          │                                                                                  Detect, off fair board) │
                          └────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Canonical references: `docs/PIPELINE_PARITY.md`, Lean/Fed `ARCHITECTURE.md`, Lean PRD §5 (Federated as prior/optional work).

---

*Detail lives in `docs/RCA_DATA_LAKE_AND_MODALITY_BRAINSTORM.md` §3.2b.*
