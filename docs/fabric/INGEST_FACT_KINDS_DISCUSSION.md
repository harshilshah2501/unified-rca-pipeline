# Ingest fact kinds — discussion notes (team)

**Status:** Working notes from Pillar B / fabric walkthroughs (2026-09).  
**Wire field today:** JSON key remains `signal_class` on `ingest.v1`.  
**Spoken name in meetings:** **fact kind** (or **line kind**) — a router label for who should care about the line, not “Detect signal” and not MELTS letter codes.  
**Rename later:** leadership may rename the wire key to `fact_kind`; that is an I/O-1 contract change (`INGEST_DATA_FORMAT.md` + schema + fixtures), not a Pillar B–only edit.

**Normative contracts:** [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md) §2 · [`E2_INPUT_FIXTURES.md`](../../pillar-ab-implementation/E2_INPUT_FIXTURES.md) · schema [`ingest_v1.schema.json`](../../pillar-ab-implementation/contracts/schemas/ingest_v1.schema.json).  
**Pillar B team demo:** [`TEAM_WALKTHROUGH.md`](../../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md).

---

## 1. Why five fact kinds (not “one line per MELTS letter”)

Collect must land **one shared JSONL stream** that feeds:

1. Motadata ObserveOps stages after Identity (Topology, Stores, Detect, Localize, Identify, …), and  
2. Lean / Federated bakeoff consumers that already thought in metrics, anomalies, events, spans, and topology refresh.

So the enum is a **closed set of line kinds**. Each writer or stage filters by kind instead of re-parsing every raw modality. Reserved kinds (`change_event`, `cmdb_sync`, `ticket`) exist so ServiceOps / CMDB / change feeds can join later without colliding.

| Fact kind (`signal_class`) | Plain meaning | Primary consumers | Pillar A / B |
|----------------------------|---------------|-------------------|--------------|
| `metric_sample` | One numeric measurement on a CI | E4 Stores · E6 Detect | A admits · B NOOP |
| `topo_update` | Explicit CI–CI edge assertion | E3 Topology | A NOOP · B admits |
| `anomaly` | Pre-marked threshold / detect crossing | E6 Detect · E7 Curate | Both skip |
| `event` | Discrete occurrence — **including logs** | E4 evidence · E10 Identify | Both skip |
| `trace_span` | One span with duration / peer labels | E9 Localize · E10 Identify | Both skip |

Kind-specific fields: see TEAM_WALKTHROUGH §3.1 or E2_INPUT_FIXTURES field cheat.

---

## 2. Where do logs go? (MELTS “L”)

**Logs are not a sixth fact kind.** On the Motadata `ingest.v1` wire they land as **`event`**.

| Raw source (examples) | Fact kind after Collect |
|-----------------------|-------------------------|
| Application / syslog / JSONL logs | `event` |
| SNMP traps, alert-style discrete fires | `event` |
| Prometheus / OTLP metrics | `metric_sample` |
| APM / OTLP spans | `trace_span` |
| Explicit topology / catalog / inventory edge facts | `topo_update` |
| Detect-marked crossings (when emitted as their own line) | `anomaly` |

That mapping is already frozen in [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md) §5 (“Logs — acceptable raw formats” → `signal_class: "event"`). E2_INPUT_FIXTURES lists typical emitters for `event` as: log lines, SNMP traps, structured syslog, Motadata alert/export events.

**Why not a separate `log` kind?** The wire optimizes for **consumer routing**, not source file type. Logs, SNMP traps, and discrete alert fires share the same consumer path (evidence history / Identify corroboration) and the same sparse shape (`name` + often `value: 1.0` + `labels`). Splitting `log` vs `event` would duplicate routers without changing Pillar A/B admit rules.

**What logs are not:** GraphWriter does **not** admit log/`event` lines as edges. If a log implies a dependency, an upstream adapter may emit a separate `topo_update` — same pattern as spans → future edge emitters.

Example (from pillar-b sample estate):

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-07-16T09:59:58Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "event",
  "name": "log.error",
  "value": 1.0,
  "labels": { "level": "error" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" }
}
```

Pretty examples for all five kinds: [`ingest.example.json`](../../pillar-ab-implementation/pillar-b/poc/sample_estate/customer_checkout/expected/ingest.example.json).

---

## 3. Node bind vs edge provenance (discussed alongside fact kinds)

| Concern | Field | Layer |
|---------|-------|-------|
| Who bound this CI id? | `identity.bind_source` | Node / ingest line |
| How trustworthy is this relationship? | `discovered_via` (`evidence_type`, …) | Edge on `map/` |

Parallel ideas; GraphWriter may copy `bind_source` into edge `telemetry_source` when writing.

---

## 4. Open decisions (do not silently change wire)

| Topic | Current stance |
|-------|----------------|
| Wire key rename `signal_class` → `fact_kind` | Deferred — spoken alias only until Motadata I/O-1 change |
| Separate `log` fact kind | **No** — logs stay under `event` |
| Derive edges from `event` / `trace_span` inside GraphWriter | **No** in Pillar B PoC — upstream may emit `topo_update` |

---

## 5. Hub reading path

1. This page (discussion)  
2. [`INGEST_DATA_FORMAT.md`](../INGEST_DATA_FORMAT.md) §2 + §5 (logs → `event`)  
3. [`E2_INPUT_FIXTURES.md`](../../pillar-ab-implementation/E2_INPUT_FIXTURES.md) (examples per kind)  
4. [`TEAM_WALKTHROUGH.md`](../../pillar-ab-implementation/pillar-b/docs/TEAM_WALKTHROUGH.md) (Pillar B demo)  
5. [GraphWriter I/O walkthrough](http://127.0.0.1:8765/graphwriter-io-walkthrough.html) (hub visual)
