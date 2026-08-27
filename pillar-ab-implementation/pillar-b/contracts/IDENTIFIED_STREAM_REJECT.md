# Identified stream — reject contract

**Purpose:** Single list of reason codes both Pillar A (sketch writer) and Pillar B (graph writer) use when dropping an `ingest.v1` line. Writers do not invent extra drop reasons without adding them here.

**Applies after:** E1 Collect + E2 Identity overlay. This workstream does not implement Collect or Identity.

---

## Reason codes

| Code | Who applies it | When |
|------|----------------|------|
| `identity_unresolved` | Identity gate (both writers) | `identity.status` is missing or `unattributed` |
| `identity_synthesized` | Identity gate (both writers) | `identity.status` is `synthesized` — not a localize or ticket target |
| `never_ci_vertex` | Graph builder | `ci_type` (or Motadata name) is Change, Alert, Incident, ITSMTicket, Metric, LogPattern, or Trace |
| `unknown_relation` | Graph builder | `relation` is not in the fifteen-name catalog |
| `unknown_metric_id` | Sketch admit | `metric_id` / `name` is outside the wave-1 allowlist |

Wave-1 metric allowlist: `request.latency_ms`, `cpu.utilization_pct`.

Wave-1 graph emit allowlist (schema still lists all fifteen): `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`.

Relations that are in the catalog but not wave-1 are **not** `unknown_relation`. They are skipped by the phased emitter, not rejected as illegal ingest.

---

## Identity gate (shared stub)

Pass only `identity.status = resolved`.

Drop:

- missing `identity` block → `identity_unresolved`
- `unattributed` → `identity_unresolved`
- `synthesized` → `identity_synthesized`

---

## On-disk rooms (Gate B file dest)

```text
poc/out/<tenant>/
  map/graph_snapshot.json
  map/edges.jsonl
  map/nodes.jsonl
  history/sketches.jsonl
  history/change_facts.jsonl
```

Logical rooms stay separate: map vs history. Same `tenant` + `ci_id` / `entity_id` namespace.
