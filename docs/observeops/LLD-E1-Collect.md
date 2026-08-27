# LLD-E1 — Collect

**Status:** Done
**Version:** v1.1
**Owner:** ObserveOps RCA engineering
**Parent:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §8 (E1 Collect contract), §5 (crosswalk: E1 is part of the 5-stage "Ingest" phase), §11.1 (identity namespace — E1 carries keys, does not resolve them)
**Gate checklist (per HLD §18):** stage ID/purpose referenced ✓ · concrete schema/API defined ✓ (§2–§3) · acceptance test from corpus/lab replay ✓ (§7) · evidence-maturity tag stated ✓ (§6, §7)

---

## 1. Purpose and boundary (from HLD §8)

E1 Collect ingests edge telemetry payloads from agents/OTLP/log streams and admits them into the pipeline as `TelemetryEnvelope` records. E1 owns **wire-format admission** only:

- It does **not** decide what a signal means (that starts at E6 Detect).
- It does **not** resolve identity. Source-asserted `ci_id` / `ci_type` are carried as-is, including empty or placeholder values. Identity *resolution* — CI bind against topology or a bind table — is E2's job; see [`LLD-E2-Identity.md`](./LLD-E2-Identity.md).
- It does **not** interpret `topo_update` lines semantically — it only carries them; E3 Topology is the consumer that turns them into a `GraphSnapshot`.
- It does **not** admit CMDB / change / ticket sources this pass (HLD v1.1: telemetry only). Those envelope classes are **reserved** (§2.2) so they can join later without colliding with today's enum.

**Trigger:** continuous (live sources) or batch replay (corpus/lab converters).
**Preconditions:** source auth/config available.
**Postconditions:** incoming events are accepted into the ingestion path as well-formed `ingest.v1` lines.
**Failure if missing:** no data enters the pipeline — everything downstream stalls.
**Degradation:** partial source loss still allows scoped RCA on the sources that remain.

### 1.1 E1 vs E2 in today's converters (load-bearing)

There is no long-running E1 service yet. Two converters emit `ingest.v1`, but they are **not** equal on the E1/E2 split:

| Path | What E1 owns in the LLD | What actually runs in one script today |
|---|---|---|
| ObserveOps replay | Admit corpus metrics/events/topo_update as `ingest.v1` | [`observeops_to_ingest_v1.py`](../ingestion-poc/replay/observeops_to_ingest_v1.py) also looks up `ci_type` from `topology.json` — that lookup is **E2**, documented here so it is not mistaken for Collect |
| Motadata export | Admit ClickHouse JSONL as `ingest.v1` with source-native ids | [`motadata_to_ingest_v1.py`](../ingestion-poc/adapters/motadata_to_ingest_v1.py) applies [`build_motadata_ci_bind.py`](../ingestion-poc/adapters/build_motadata_ci_bind.py) **in the same process** — that bind is **E2** |

**Follow-up (not required to call this LLD Done):** split Motadata admit vs bind into separately invocable steps so the code matches the stage boundary. Until then, treat the Motadata script as E1 admit + E2 bind in one process, and score identity work against [`LLD-E2-Identity.md`](./LLD-E2-Identity.md).

---

## 2. Output schema — `ingest.v1` (this is the HLD's `TelemetryEnvelope`)

One JSON object per line, time-ordered, UTF-8, newline-delimited (JSONL). Canonical field list also lives in [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md).

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:01Z",
  "tenant": "default",
  "ci_id": "orders-api",
  "ci_type": "Service",
  "signal_class": "metric_sample",
  "name": "request.p95_latency_ms",
  "value": 1450.0,
  "threshold": 1000.0,
  "severity": 1.45,
  "labels": {
    "source": "replay",
    "trace_id": "abc123",
    "span_id": "span-7",
    "parent_span_id": "span-2",
    "route": "POST /checkout"
  },
  "raw_ref": "optional/path/to/original.line"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | Yes | Always `"ingest.v1"` — contract version gate. A consumer that sees a different value **must reject or dead-letter**, not guess. Policy is in this LLD; implementation is deferred to Vector D5 (§5) |
| `ts` | ISO-8601 UTC | Yes | Event time (not admission time) |
| `tenant` | string | Yes | `"default"` in every current corpus/lab path — multi-tenant is not exercised yet. Part of the future ServiceOps join key (`tenant`+`ci_id`) |
| `ci_id` | string | Yes at E2; at E1 may be source-asserted placeholder | E1 does **not** validate this against topology. An unresolvable `ci_id` is legal at E1 and becomes E2's problem |
| `ci_type` | string | Yes at E2; at E1 may be `"Unknown"` / source class | ObserveOps corpus types: `NetworkPort`, `HypervisorHost`, `Datastore`, `VirtualMachine`, `GuestOS`, `Service`. Additive taxonomy — new types do not require an `ingest.v1` bump |
| `signal_class` | enum | Yes | Admitted now: §2.1. Reserved unused: §2.2. Unknown → reject / dead-letter |
| `name` | string | Yes | Metric name, log/event type, span operation, or edge relation (for `topo_update`) |
| `value` | number | Usually | Numeric value; `1.0` for boolean/event occurrences. Not required for every future reserved class |
| `threshold` | number \| null | If known | Carried through for E6 Detect; E1 does not evaluate it |
| `severity` | number | Optional | Normalized severity or `value/threshold` ratio when computable |
| `labels` | object | Optional | Free-form: trace/span ids, route, host, `uc_id`, `source`. `service` / `env` / `version` stay here (HLD D-E2-2) |
| `raw_ref` | string | Optional | Pointer back to the original record, for audit |

E1 does **not** emit `identity.*`. That overlay is E2 ([`LLD-E2-Identity.md`](./LLD-E2-Identity.md) §3).

### 2.1 `signal_class` values admitted now

| Class | Emitted by | Primary downstream consumer |
|---|---|---|
| `metric_sample` | Metric series replay, Prometheus scrape, OTLP metrics | E6 Detect (anomaly evaluation), E4 Stores |
| `anomaly` | Pre-marked threshold crossings (replay converter can pre-tag these; live path defers to E6) | E6 Detect, E7 Curate |
| `event` | Log lines, structured events, syslog | E4 Stores, E10 Identify (evidence) |
| `trace_span` | OTLP/Jaeger/Zipkin traces, ddtrace-style spans | E9 Localize, E10 Identify (self-time/error leaf) |
| `topo_update` | Topology crawler audit fan-out (sibling path, not the primary A-TOPO writer) | E3 Topology only — E1 does not act on these |

### 2.2 Reserved `signal_class` values (unused this pass)

Named so later ServiceOps/CMDB sources do not collide with today's enum. **Do not emit these from E1 now. Do not implement collectors for them in this LLD.**

| Class | Future producer | Why reserved |
|---|---|---|
| `change_event` | Change / deploy feed | HLD E5 Maintain + ServiceOps change correlation |
| `cmdb_sync` | CMDB / discovery snapshot or delta | Optional CMDB enrichment of P1; identity join, not a second Collect plane |
| `ticket` | ServiceOps incident / ITSM record | Future join onto the same `ci_id`; E11 is still the RCA→ServiceOps egress |

**Extension policy:** a line whose `signal_class` is not in §2.1 and not in §2.2, or whose `schema_version != "ingest.v1"`, is **poison**. Policy is reject or dead-letter. Do not coerce it into `event` or invent a class.

---

## 3. Interface — how E1 is actually invoked today

There is no long-running E1 service in this repo yet; E1 exists as three concrete code paths that all emit the same `ingest.v1` contract.

### 3.1 Corpus replay (primary path for the ObserveOps bakeoff)

```bash
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all
# per-UC: --uc UC-1
# flags: --no-anomaly-rows | --incident-day-only | --out-root PATH | --corpus PATH
```

Reads `datasets/observeops/UC-{1..5}/{metrics/*.json, events.json, topology.json}`, writes `datasets/ingest_samples/observeops-replay/UC-N/{stream.jsonl, manifest.json, topo_updates.jsonl}` plus copies of `topology.json`, `ground_truth.json`, `symptom_seed.json`, `anomalies.json` for downstream stages.

Reference: [`ingestion-poc/replay/observeops_to_ingest_v1.py`](../ingestion-poc/replay/observeops_to_ingest_v1.py).

### 3.2 Motadata export path (product-shaped, real-export path)

```bash
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
```

Reads `datasets/ingest_samples/jsonl_resolved/*.jsonl` (local, gitignored ClickHouse export), applies CI bind (E2 — see [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) §2.2) and the threshold catalog, writes `motadata-ingest/stream.jsonl`.

Reference: [`ingestion-poc/adapters/motadata_to_ingest_v1.py`](../ingestion-poc/adapters/motadata_to_ingest_v1.py).

### 3.3 Live / Vector path (lab-validated, not the fairness baseline)

Vector source → transform → sink configs already exist as skeletons:

| Config | Role |
|---|---|
| [`vector.l0-smoke.toml`](../ingestion-poc/vector/vector.l0-smoke.toml) | Lean-only sink smoke |
| [`vector.f1-smoke.toml`](../ingestion-poc/vector/vector.f1-smoke.toml) | Dual-sink (Lean + structural + speed) smoke |
| [`vector.dual-sink.toml`](../ingestion-poc/vector/vector.dual-sink.toml) | Dual-sink production-shaped |
| [`vector.live-syslog.toml`](../ingestion-poc/vector/vector.live-syslog.toml) | Live syslog source |
| [`vector.live-prometheus.toml`](../ingestion-poc/vector/vector.live-prometheus.toml) | Live Prometheus scrape |

Dev/smoke stand-in for the Vector box (same three-sink output shape) is the Python fan-out runner:

```bash
python3 ingestion-poc/pipeline/f1_run.py
```

Reference: [`ingestion-poc/pipeline/f1_run.py`](../ingestion-poc/pipeline/f1_run.py) — **per [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) §D0–D2, this is Done as a smoke path; D3–D5 (topology crawler stub, Federated speed-tier builder from Vector's own Redis/Kafka sink, product hardening including DLQ) remain Planned.**

---

## 4. `topo_update` boundary note

`observeops_to_ingest_v1.py` also emits `topo_updates.jsonl` — one `topo_update` line per topology edge, timestamped at `incident_start`. This is the **audit fan-out** described in `INGESTION_PIPELINE_VECTOR.md` §4 ("optional: emit topo_update events into Vector for audit fan-out"), not the primary `A-TOPO` writer. The primary topology snapshot is `topology.json` itself, copied through unchanged and consumed directly by E3. Do not read `topo_updates.jsonl` as the topology source of truth.

---

## 5. Failure modes and degradation

| Condition | Behavior today | Status |
|---|---|---|
| Source unreachable / auth missing | No data enters pipeline for that source; other sources unaffected | Grounded — this is just "the script/config for that source doesn't run" |
| `ci_type` unresolvable from topology (replay path) | Falls back to `"Unknown"` (`_ci_type()` in the replay converter). That fallback is **E2** behavior running inside the replay script | Grounded — implemented, see `observeops_to_ingest_v1.py` |
| Malformed / schema-violating line, unknown `signal_class`, or `schema_version != "ingest.v1"` | **Policy:** dead-letter / reject. Do not coerce. | **Design-level — not yet implemented.** Deferred to [`INGESTION_POC_PLAN.md`](../INGESTION_POC_PLAN.md) design phase **D5** (HA / auth / DLQ product hardening, Post-PoC) and [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) §D5. `f1_run.py` has no dead-letter path today. This LLD is Done with that scope note — DLQ is not a remaining E1 design question |
| CI bind failure | **Not an E1 failure.** E2 D-E2-1 (synthesize + `identity.status`) applies. Vector docs that said "CI bind failure → dead-letter" are superseded by HLD D-E2-1 for identity misses; E1 DLQ is for **poison envelopes**, not unresolved CIs | Signed in HLD §13 |

Live (non-replay) throughput SLA: inherit [`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) §6.0 — saved replay is the fairness baseline; live is secondary. This LLD does **not** invent a live EPS number.

---

## 6. NFR baseline and measured evidence

The HLD (§15) sets "sustained ingest throughput ≥ platform peak (soak-validated)" as the P1 target. Measured numbers exist from one pro6000 run:

| Path | Measured | Run |
|---|---|---|
| L0 (Lean-only sinks), Python fan-out | 153,417 EPS, 6.51 CPU-s/1M events | `cost-pro6000-20260721Tfinal` |
| F1 (dual-sink), Python fan-out | 144,201 EPS, 6.92 CPU-s/1M events (−6.0% EPS vs L0, 2.32× sink bytes) | same run |
| L0, Vector (Docker) | 31,163 EPS (includes container startup — conservative) | same run |
| F1, Vector (Docker) | 66,541 EPS | same run |
| Dragonfly soak (store-path headline gate, not this stage directly but the sink E1 feeds) | **67,084.8 EPS sustained**, p99 write 0.379 ms, 120 s duration | `cost-pro6000-20260721Tsoak` |

**Evidence maturity: Grounded** — these are measured (not extrapolated) numbers from [`benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md`](../benchmarking/results/costing/cost-pro6000-20260721Tfinal/cost_report.md), except GB/day figures in that report which are explicitly extrapolated (flagged there, not here). Per that report's own notes: **the headline ≥50K EPS gate is the Dragonfly soak (store path), not raw Vector/Python fan-out** — do not cite the 153K Python fan-out number as if it were the product throughput SLA; it's an upper-bound smoke number on a 16-CPU host, not a soak-validated target.

---

## 7. Acceptance test (evidence maturity: Grounded)

```bash
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all
```

**Pass criteria:**

1. `datasets/ingest_samples/observeops-replay/UC-N/stream.jsonl` exists for `N = 1..5`.
2. Every line parses as JSON with `schema_version == "ingest.v1"`, a parseable ISO-8601 `ts`, and `signal_class` in the §2.1 enum (not a reserved §2.2 class).
3. `manifest.json` per UC reports `stream_lines`, `metric_series_files`, `event_lines` matching the corpus's `metrics/*.json` file count and `events.json` line count.
4. `ground_truth_root_ci` in the manifest matches `datasets/observeops/UC-N/ground_truth.json`'s `root_ci` (sanity check that the copy-through didn't corrupt the eval-only artifact).

This exercises the corpus/lab replay path end-to-end and is reproducible byte-for-byte from the frozen corpus (Reproducibility principle, HLD §3).

Motadata converter: documented as E1 admit + E2 bind in one process (§1.1). Identity pass criteria live in [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) §6.

---

## 8. Traceability

Per HLD §16: E1 maps to **FR-A (ingest/normalize)** — the ingest half; normalize/identity is E2 / FR-B. Primary FR/AC reference: [`multi-telemetry-rca-functional-and-acceptance-criteria.md`](./multi-telemetry-rca-functional-and-acceptance-criteria.md).

---

## 9. Closed decisions / follow-ups that are not E1 design

| Item | Disposition |
|---|---|
| Dead-letter sink in `f1_run.py` / Vector | **Deferred** to Vector / PoC plan D5. Policy is specified here. Not blocking Done |
| Schema-version reject in converters | Same D5 bucket. Policy: reject / dead-letter |
| Live throughput SLA | Inherit Vector §6.0 (replay primary) |
| Motadata E1/E2 code split | Follow-up implementation; LLD boundary is signed |
| CMDB / change / ticket Collect | Out of this pass. Reserved classes in §2.2 |

---

*Part of the LLD backlog defined in [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §18. Sibling: [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) (Normalize).*
