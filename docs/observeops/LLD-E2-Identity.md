# LLD-E2 — Identity (Normalize)

**Status:** Done
**Version:** v1.1
**Owner:** ObserveOps RCA engineering
**Parent:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §8 (E2 Identity contract), §5 rule 4 (Fabric **Normalize = E2**), §11.1 (identity namespace)
**Gate checklist (per HLD §18):** stage ID/purpose referenced ✓ · concrete schema/API defined ✓ (§2–§3) · acceptance test from corpus/lab replay ✓ (§6) · evidence-maturity tag stated ✓ (§6, §7)

This document **is** the Normalize LLD. Do not look for a separate `LLD-Normalize.md`.

---

## 1. Purpose and boundary (from HLD §8)

E2 Identity stamps join keys so `TelemetryEnvelope` records (E1's output) become `IdentifiedRecord`s — joinable with the topology graph (E3), the stores (E4), and a **future ServiceOps CI / ticket** under a common `tenant`+`ci_id`. E2 owns **identity resolution**:

- It maps whatever raw host/monitor/service identifier a source asserts onto the stable `ci_id` used elsewhere in the pipeline.
- It does **not** decide whether that CI exists in the topology graph — that check (and the ambiguity it creates for localize) belongs to E3/E9.
- It does **not** evaluate thresholds or detect anomalies — that is E6.
- It does **not** create ServiceOps incidents — that is E11 (FR-J1). It only guarantees the `ci_id` E11 would hand off is the same key CMDB/ServiceOps can join later.

**Trigger:** continuous, per record.
**Inputs:** `TelemetryEnvelope` (from E1).
**Outputs:** `IdentifiedRecord` — this pass, the same `ingest.v1` line after the identity overlay (§3), not a second on-wire format.
**Preconditions:** an identity strategy (bind table, or self-describing source) is configured.
**Postconditions:** each record is joinable with topology and store keys; `identity.status` is present so downstream can tell resolved from synthesized.
**Failure if missing:** cross-modal joins collapse — E4/E10 cannot correlate metrics/traces/logs for the same entity.
**Degradation:** unresolved records move to an unattributed queue (query surface over `identity.status != resolved`, FR-B1). They are never silently dropped. They are **not** localize or ServiceOps-ticket targets (D-E2-1).

---

## 2. Two identity-resolution mechanisms in this repo (both real, different maturity)

E2 is not one algorithm — it is two different resolution paths depending on how "clean" the source already is.

### 2.1 ObserveOps corpus path — topology-lookup only (no bind table needed)

The ObserveOps corpus is synthetic and already ships `ci_id`s that exist in `topology.json`. E2's entire job here is a `ci_type` lookup, not identity discovery:

```python
def _ci_type(topology: dict, ci_id: str) -> str:
    for node in topology.get("nodes") or []:
        if node.get("id") == ci_id:
            return str(node.get("type") or "Unknown")
    return "Unknown"
```

Reference: [`ingestion-poc/replay/observeops_to_ingest_v1.py`](../../ingestion-poc/replay/observeops_to_ingest_v1.py) (`_ci_type`, called from `metric_rows`/`event_rows`/the `topo_updates.jsonl` writer). That lookup currently runs inside the E1 replay converter; the LLD still attributes it to E2 ([`LLD-E1-Collect.md`](./LLD-E1-Collect.md) §1.1).

Real `ci_type` values seen in the corpus (from `datasets/observeops/UC-1/topology.json`): `NetworkPort`, `HypervisorHost`, `Datastore`, `VirtualMachine`, `GuestOS`, `Service`. Edge relations seen: `runs_on`, `hosted_by`, `uplink_to`, `stored_on`. Fallback when a `ci_id` isn't found in the topology: `"Unknown"` → overlay `identity.status = "unattributed"` (or `"synthesized"` if a placeholder id was invented).

**This path has effectively 100% resolution on the frozen corpus** — it doesn't exercise the miss/fallback case in any interesting way, because the corpus was built pre-bound. Treat §2.2 as the real test of E2's resolution logic.

**Overlay mapping for this path (contract; emission is a follow-up):**

| After lookup | `identity.status` | `identity.bind_source` | `identity.aliases` |
|---|---|---|---|
| Node found | `resolved` | `topology_lookup` | source `ci_id` if it differed (usually empty) |
| Node missing, `ci_type = "Unknown"` | `unattributed` | `topology_lookup` | source-asserted id |

Until converters emit `identity.*`, Motadata `labels.bound` and ObserveOps `"Unknown"` `ci_type` are the **implemented proxies**. Downstream E6/E9/E11 must treat those proxies as equivalent to `identity.status != resolved`.

### 2.2 Motadata export path — CI bind table with plugin-based fallback

Real, messy monitor data does not arrive with a stable `ci_id`. E2 here is a two-stage bind:

**Stage A — build the bind table** (offline, once per export):

```bash
python3 ingestion-poc/adapters/build_motadata_ci_bind.py
# reads:  datasets/ingest_samples/jsonl_resolved/metric_string.jsonl
# writes: datasets/ingest_samples/motadata-ingest/ci_bind.json
```

Resolution order per monitor, from [`build_motadata_ci_bind.py`](../../ingestion-poc/adapters/build_motadata_ci_bind.py):

1. Prefer field `object.name`, else `system.name`, `host.name`, `hostname`, `device.name`, `target.name` (`_pick_name`).
2. Last resort: any `*.name` string field that looks like a hostname (no spaces, < 128 chars).
3. If none of the above exist for a monitor id ever seen: synthesize `"{plugin_prefix}-{monitor_id}"` using a small fixed table (`_PLUGIN_FALLBACK_PREFIX`: `426→proxmox-ve`, `88→linux-host`, `157→network-device`, `181→windows-host`, `199→ping-target`), or `"monitor-{monitor_id}"` if the plugin id isn't in that table. `ci_type` for every fallback entry is `"Host"`. `bind_source` is recorded as `"object.name"`, `"string_name"`, or `"plugin_fallback"` per entry — this is an audit trail, not just a value.

**Stage B — apply the bind table at conversion time:**

```python
def resolve_monitor_ci(monitor_id, bind) -> tuple[str, str]:
    entry = bind.get(str(monitor_id))
    if entry and entry.get("ci_id"):
        return str(entry["ci_id"]), str(entry.get("ci_type") or "Host")
    return f"monitor-{monitor_id}", "Monitor"
```

Reference: [`ingestion-poc/adapters/motadata_to_ingest_v1.py`](../../ingestion-poc/adapters/motadata_to_ingest_v1.py) (`resolve_monitor_ci`, called from `convert_metric_numeric`/`convert_metric_string`). This currently runs inside the E1 Motadata converter; LLD attributes it to E2.

**Note the two different fallback layers are not the same value:** if `build_motadata_ci_bind.py` never saw a monitor id at all (Stage A never wrote an entry), Stage B's own fallback fires with `ci_type = "Monitor"` and `ci_id = "monitor-{id}"` — distinct from Stage A's own `"Host"`-typed fallback for monitors it did see but couldn't name. Every emitted record carries `labels.bound: bool` (`ci_id != f"monitor-{obj_id}"`) so a downstream consumer can tell resolved from synthesized without re-deriving it.

**Overlay mapping for this path:**

| Bind outcome | `identity.status` | `identity.bind_source` | Implemented proxy today |
|---|---|---|---|
| Named CI from bind table | `resolved` | `object.name` / `string_name` | `labels.bound = true` |
| Plugin fallback `"{prefix}-{id}"` | `synthesized` | `plugin_fallback` | `labels.bound` may still be true if id ≠ `monitor-{id}` — **treat `plugin_fallback` as synthesized for E9/E11** |
| Never in bind table: `monitor-{id}` | `synthesized` | `unbound` | `labels.bound = false` |

`identity.aliases` should retain the source-native keys (monitor id, `object.name`, hostname, IP) so a later CMDB/ServiceOps record can match without competing as a primary key.

---

## 3. `IdentifiedRecord` contract (overlay on `ingest.v1`)

This repo does **not** define `IdentifiedRecord` as a second on-wire schema. Identity resolution happens **in place**: the same `ingest.v1` envelope is emitted, with resolved `ci_id`/`ci_type` plus the overlay below.

HLD object `IdentifiedRecord` = `ingest.v1` + `identity` object.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T10:00:01Z",
  "tenant": "default",
  "ci_id": "esxi-host-01",
  "ci_type": "HypervisorHost",
  "signal_class": "metric_sample",
  "name": "cpu.ready",
  "value": 12.4,
  "identity": {
    "status": "resolved",
    "bind_source": "object.name",
    "aliases": ["monitor-88", "esxi-host-01.lab.local"]
  },
  "labels": {
    "bound": true,
    "service": "optional",
    "env": "optional",
    "version": "optional"
  }
}
```

| Field | Source (E1) | After E2 |
|---|---|---|
| `tenant` + `ci_id` | Source-native identifier (may be a raw monitor id, hostname, IP) | **Primary join key** for E3, E4, E9, E11, and a future ServiceOps ticket/CI |
| `ci_type` | Often absent/generic | Resolved from topology or bind table. Extensible taxonomy: corpus six + `Host` / `Monitor` / `Unknown`. New types are additive |
| `identity.status` | n/a | `resolved` \| `unattributed` \| `synthesized` (required on E2 output once emitters land; Motadata `labels.bound` is the proxy until then) |
| `identity.bind_source` | n/a | e.g. `topology_lookup`, `object.name`, `plugin_fallback`, `unbound` |
| `identity.aliases` | n/a | Source-native keys later CMDB/ServiceOps can match. Not competing primary keys |
| `labels.bound` | n/a | Motadata path today: `true`/`false`. Kept until `identity.status` is emitted |
| `labels.service` / `labels.env` / `labels.version` | optional, free-form | **Stay in `labels`** (D-E2-2). Not required top-level. Recommended when the source has Unified-Service-Tags-style identity; they do not replace `ci_id` |

`ci_type` values that are legal after E2: `NetworkPort`, `HypervisorHost`, `Datastore`, `VirtualMachine`, `GuestOS`, `Service`, `Host`, `Monitor`, `Unknown`. Additional types may appear without an `ingest.v1` version bump.

---

## 4. D-E2-1 — bind-miss policy (Signed)

[`INGESTION_PIPELINE_VECTOR.md`](../INGESTION_PIPELINE_VECTOR.md) §5.2 described a Vector CI bind transform with "CI bind failure → dead-letter sink (do not invent roots in RCA)". No Vector transform in [`ingestion-poc/vector/`](../../ingestion-poc/vector/) implements that, and both converters **synthesize** placeholders. v1.1 signs the reconciliation:

**Signed default (HLD D-E2-1):**

1. **Keep synthesis** for observability of misses — every record stays visible; nothing is silently dropped (FR-B1).
2. **`identity.status != resolved` is not a localize target and not a ServiceOps-ticket target.** E9 must not pick a synthesized/unattributed CI as `LeafClaim`. E11 must not open a ServiceOps incident on one.
3. **Unattributed queue** is the query surface over those records (`identity.status` in `{unattributed, synthesized}`, or today's proxies), not a second pipeline.
4. **True poison** (malformed JSON, `schema_version` mismatch, unknown `signal_class`) is **E1 dead-letter**, not E2 synthesis. That DLQ is deferred to Vector D5 ([`LLD-E1-Collect.md`](./LLD-E1-Collect.md) §5).

Vector live CI-bind remains Design-level until D3/D5 land. When it lands, it must implement this policy, not the old "dead-letter on bind miss" sentence.

---

## 5. Failure modes and degradation

| Condition | Behavior today | Overlay | Status |
|---|---|---|---|
| ObserveOps `ci_id` not found in `topology.json` | `ci_type = "Unknown"`, record still emitted | `unattributed` | Grounded (implemented) |
| Motadata monitor id has a named bind-table entry | Resolved `ci_id`/`ci_type`, `labels.bound = true` | `resolved` | Grounded (implemented) |
| Motadata monitor id known to bind-builder but unnameable | Synthesized `"{prefix-or-monitor}-{id}"`, `ci_type = "Host"` | `synthesized` | Grounded (implemented) |
| Motadata monitor id never reaches the bind table at all | Synthesized `"monitor-{id}"`, `ci_type = "Monitor"`, `labels.bound = false` | `synthesized` | Grounded (implemented) |
| Vector live CI-bind miss | Documented historically as dead-letter; **superseded by D-E2-1** | `synthesized` or `unattributed`, never poison-DLQ | **Design-level — not implemented** |
| Schema-invalid envelope | E1 reject / DLQ (deferred D5) | n/a | See LLD-E1 |

---

## 6. Acceptance test (evidence maturity: Grounded)

**ObserveOps path:**

```bash
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all
```

Pass criteria:

1. Every `ci_type` value in every `stream.jsonl` line is one of `{NetworkPort, HypervisorHost, Datastore, VirtualMachine, GuestOS, Service, Unknown}`.
2. `"Unknown"` count is 0 across UC-1..UC-5 (the corpus is pre-bound — a non-zero count means topology/metric CI ids drifted apart and is a regression).
3. None of the UC `ground_truth.json` `root_ci` values are synthesized placeholders (`Unknown`, `monitor-*`, or plugin-fallback ids).

**Motadata path:**

```bash
python3 ingestion-poc/adapters/build_motadata_ci_bind.py
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
```

Pass criteria: the conversion summary's `ci_bind_miss_monitors` count is reported (not silently swallowed) and every emitted line has `labels.bound` present. Per [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md) §11 depth note (2026-07-21): CI-bind + threshold catalog + span-derived `http.error_rate` already feeds a Localize smoke (`motadata-apm-001`) — that downstream success is indirect evidence the bind table is good enough to be useful, not just structurally valid.

**Overlay emission (follow-up, not blocking Done):** when converters emit `identity.*`, add: every E2 output line carries `identity.status`; synthesized ids are countable; the same GT `root_ci` check holds against `identity.status == resolved`.

**Evidence maturity: Grounded** for both paths — both are repo-executable against real (ObserveOps) or real-exported (Motadata) data. Overlay emission is Design-level until the follow-up lands; proxies (`labels.bound`, `"Unknown"`) are Grounded.

---

## 7. Traceability and NFR measurement

Per HLD §16: E2 maps to **FR-B (entity resolution)**. NFR target from HLD §15 / FR/AC §6: entity-resolution accuracy ≥ 95% of resolvable signals.

**Definition (the bar to hit, not a result claimed):**

```
accuracy = resolved / resolvable
```

- **resolved:** `identity.status == resolved` (or Motadata `labels.bound == true` **and** `bind_source` is not `plugin_fallback`).
- **resolvable:** signals whose source keys map to a CI in the labeled bind/topology set. Unnameable monitors are in the denominator only when a human/CMDB label exists for them.
- Unresolved records stay in the unattributed queue; they are not dropped and do not count as resolved.

This repo reports `ci_bind_miss_monitors` / `ci_bind_miss_sample` per Motadata run but does **not** yet trend `accuracy` against 95%. That metric is the E2 follow-up, not a claim that FR-B1 is met.

---

## 8. Industry context — entity extraction vs CMDB “CI definition”

Cold readers often ask whether E2 “defines configuration items the way ServiceNow does.” **No — and that is intentional.** ServiceNow and peer CMDBs answer **organizational** questions (CI class, owner, lifecycle, allowed relationship types). E2 answers an **operational** question: **which stable `tenant`+`ci_id` should this telemetry line carry so E3/E4/E6+ can join it?**

### 8.1 Two questions — do not merge them

| Question | Typical owner | ObserveOps |
|----------|---------------|------------|
| What is a CI in our estate? (schema, policy) | CMDB / ITSM (ServiceNow, …) | Keys frozen for future ServiceOps join; **no ticket/CMDB Collect in E1 this pass** (§1) |
| Which thing does this sample refer to? | Identity / entity resolution | **E2** — LUT or topology lookup → `identity.status` |
| Who is connected to whom? | Discovery + catalog + telemetry | **E3** — graph nodes/edges; `evidence_type` = authoritative / declared / corroborating |

E2 **does not** decide whether the CI “exists on the map” for localize — that ambiguity is E3/E9 (§1). E2 **does** guarantee the same key CMDB/ServiceOps can use later when integration lands.

### 8.2 How the industry usually populates entities

There is no single “extract CI from log line” algorithm. Stacks combine **layers**:

```text
TelemetryEnvelope labels
        │
        ├─ Inventory / agent scan     authoritative   (process/cgroup, K8s, hypervisor APIs)
        ├─ CMDB / catalog sync        declared        (ServiceNow, Terraform, service catalog)
        └─ Spans / logs / peers       corroborating   (suggested call edges until confirmed)
        │
        ▼
   Stable entity id  +  relationships (separate concern)
```

| Vendor / product | Primary join key | Typical population |
|------------------|------------------|--------------------|
| **ServiceNow CMDB** | `sys_id` + CI class | Discovery, import, manual; IRE reconciliation |
| **Dynatrace** | Smartscape `entityId` | OneAgent + observed traffic; CMDB enrich optional |
| **Datadog** | Host / service / APM tags | Agent + APM Service Map; optional catalog |
| **ObserveOps** | `tenant` + `ci_id` | §2 paths (topology lookup vs Motadata bind table); E3 for edges |

**Ephemeral workloads:** observability discovery often sees short-lived pods/services **live**; CMDB may lag unless sync is tight. That asymmetry drives quarantine / miss-policy discussion — see [`../discussion/04-raw-data-identity-lut-open-questions.md`](../../pillar-ab-implementation/discussion/04-raw-data-identity-lut-open-questions.md) §3.3, §3.6, Q1–Q3.

### 8.3 Mechanism glossary (maps to this LLD)

| Industry term | Meaning | This repo |
|---------------|---------|-----------|
| **Bind / LUT** | Raw label → stable id | E2 bind table; `_pick_name` + plugin fallback (§2.2) |
| **Discovery** | Create/update entities from inventory | Authoritative edges on E3; not the same as “Auto-create as resolved” |
| **Auto-create / Orphan / Soft-match** | LUT miss policy | §4 D-E2-1: synthesize + unattributed; Pillar A/B **resolved only** |
| **Reconciliation** | Match discovered entity to CMDB row | Future ServiceOps; not E2 Collect |
| **Service map / Smartscape edge** | Telemetry-suggested relationship | Graph `corroborating` until inventory/catalog upgrades |

**Do not confuse** LUT miss policy (node bind) with graph `evidence_type` (edge ownership). Same vocabulary family, different axis — [`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G10–G11.

### 8.4 Practical takeaway for implementers

- **Entity extraction from data ≈ E2** (bind messy labels → `ci_id`).
- **CMDB CI definition ≈ organizational schema** — align keys and classes when integrating; do not expect the sketch writer or bind script to replace ServiceNow’s class model.
- **Relationships ≈ E3**, fed by the three evidence classes above; traces alone rarely justify `resolved` production joins without authoritative or declared backing (discussion doc §3.3).

---

## 9. Closed decisions

| ID | Decision | Status |
|---|---|---|
| D-E2-1 | Synthesize flagged placeholders; `identity.status != resolved` is not a localize/ServiceOps-ticket target; poison is E1 DLQ | **Signed** (HLD §13) |
| D-E2-2 | `service` / `env` / `version` stay optional `labels`; primary join key is `tenant`+`ci_id` | **Signed** (HLD §13) |
| Overlay vs new schema | `IdentifiedRecord` is an overlay on `ingest.v1`, not a second on-wire format this pass | **Signed** |
| ServiceOps in E2 | Identity-ready only: freeze keys/aliases. No ticket/CMDB Collect sources | **Signed** (HLD §4, §11.1) |

**Follow-ups (implementation, not remaining design):**

- Emit `identity.status` / `bind_source` / `aliases` from both converters (replace Motadata-only `labels.bound` as the load-bearing flag).
- Split Motadata admit vs bind so E1/E2 are separately invocable ([`LLD-E1-Collect.md`](./LLD-E1-Collect.md) §1.1).
- Trend `resolved / resolvable` against ≥95% on a labeled Motadata bind set.
- Vector CI-bind transform implements D-E2-1 (not dead-letter-on-miss).

---

*Part of the LLD backlog defined in [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §18. Sibling: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md).*
