# LLD-E5 — Maintain

**Status:** Design-level draft (stub) — **no dedicated lab**
**Version:** v0.1
**Owner:** ObserveOps RCA engineering
**Parent:** [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §8 (E5 Maintain), §18 backlog
**Related:** [`OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md`](./OBSERVEOPS_HLD_OPERATIONAL_GRAPH.md) §4 E5 · [`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G16, G32 · Pillar B [`maintain.py`](../../pillar-ab-implementation/pillar-b/poc/graph/maintain.py) · [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) §10 · [`LLD-E4-Stores.md`](./LLD-E4-Stores.md) §8

---

## 1. Purpose and boundary (from HLD §8)

E5 Maintain keeps the always-on fabric **detect-ready**: retention, indexing, discovery freshness, and edge/sketch lifecycle. It is a running property of the fabric, not a per-case stage.

| E5 does | E5 does not |
|---------|-------------|
| Update validity / staleness / baselines on existing fabric | **Create** topology edges (that is E3) |
| Refresh seasonal baselines into `history/` (Pillar A job) | Filter Detect `Signal`s after fire (that is E6/E7 — G32) |
| Expire or downgrade stale `declared` / weak corroborating edges | Merge `map/` and `history/` into one room |
| Bump fabric version readers should prefer | Rewrite case objects (WorkingSet / VerdictCard) |

**Trigger:** scheduled / continuous maintenance.
**Inputs:** store/index metadata, discovery updates, change feeds (reserved `change_event` — not Collect this pass), per-edge `refresh` cadences.
**Outputs:** freshness baseline; maintain state; updated snapshot / sketch versions.
**Preconditions:** E3 and E4 operating (or stubs thereof).
**Postconditions:** Detect can read latest fabric without silent drift.
**Failure if missing:** data drift/staleness silently degrades RCA quality.
**Degradation:** larger correlation windows needed; confidence drops.
**Evidence maturity:** **Design-level** overall (Pipeline HLD §9.1 / op-graph §4). Unit stub on Pillar B is Grounded as *code exists*; product decay windows are not lab-validated.

---

## 2. Two rooms, two maintain jobs (do not merge)

| Room | Writer | Maintain job |
|------|--------|--------------|
| **`map/`** (Pillar B) | GraphWriter (E3) | Validity: `valid_to` expiry; drop or downgrade stale corroborating; **declared** soft-stale / hard-downgrade (below) |
| **`history/`** (Pillar A) | SketchWriter (E4) | Seasonal baseline refresh into sketch rows; retention of sketch blobs |

No continuous sync between rooms ([`GRAPH_QNA.md`](../../pillar-ab-implementation/contracts/GRAPH_QNA.md) G16). Diagnose prefers the **latest** version of each.

---

## 3. Declared-edge freshness (product default — Design numeric)

From operational-graph decision log #4 (also cited in [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) §6):

| Clock | Behavior |
|-------|----------|
| **7 days** without corroborating signal or CMDB re-sync | Soft-flag `declared` edge as stale |
| **30 days** | Hard-downgrade — exclude from confidence-bearing localization paths |
| CMDB pull that still includes the edge | Resets the clock |

Bakeoff Lean/Federated graphs still lack freshness markers. Pillar B PoC: expire `valid_to`, drop stale corroborating, and apply declared soft-stale (7d) / hard-downgrade (30d) markers via fixture `as_of` on [`maintain.py`](../../pillar-ab-implementation/pillar-b/poc/graph/maintain.py) (Design-numeric; see [`MAP_P1_FABRIC_EVAL.md`](../../pillar-ab-implementation/pillar-b/docs/MAP_P1_FABRIC_EVAL.md)).

---

## 4. Acceptance (stub)

**Pillar B (map validity):**

```bash
cd pillar-ab-implementation/pillar-b/poc && make test-graph
# includes graph/tests/unit/test_maintain.py
```

Pass criteria: maintain does not create edges; post-maintain snapshot still loads; version bumps on re-flush when CLI requests maintain.

**Pillar A (baselines):** Sketch baseline refresh path — TBD in this stub; see Pillar A deep dive. Not required to call this LLD Done.

**Non-goals this draft:** OpAMP fleet control plane; live discovery re-derive at per-edge `refresh` cadence; E11 operator feedback → E3 trust score (op-graph §3.5 — separate Design item).

---

## 5. Traceability

Per HLD §16: E5 maps (jointly with E3–E4) to **FR-C** and **FR-I/J (operability/freshness)**.

---

## 6. Open decisions

- Vendor-lab validate 7d/30d declared rules beyond fixture-clock unit proofs.
- Define Pillar A baseline-refresh acceptance without requiring raw rescan.
- Whether `change_event` reserved class becomes an E5 input feed in a later Collect pass.

---

*Part of the LLD backlog defined in [`OBSERVEOPS_PIPELINE_HLD.md`](./OBSERVEOPS_PIPELINE_HLD.md) §18. Siblings: [`LLD-E1-Collect.md`](./LLD-E1-Collect.md) · [`LLD-E2-Identity.md`](./LLD-E2-Identity.md) · [`LLD-E3-Topology.md`](./LLD-E3-Topology.md) · [`LLD-E4-Stores.md`](./LLD-E4-Stores.md).*
