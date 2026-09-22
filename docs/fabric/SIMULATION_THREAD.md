# Simulation thread — increment locks

This page records what the fabric films are allowed to show. Later increments append here. Do not invent new names.

**Hub films**

| Increment | Film | Port shortcut |
|-----------|------|---------------|
| 1 | [`edge-platform-detect-simulation.html`](./edge-platform-detect-simulation.html) | `:8765/edge-platform-detect-simulation.html` |
| 2 | [`edge-platform-case-simulation.html`](./edge-platform-case-simulation.html) | `:8765/edge-platform-case-simulation.html` |

## Increment 1 (built)

A looping film on one page: packets move themselves from Emit through a raised Detect event. There are no Play / Previous / Next controls. Do **not** animate Curate, Scope, Localize, Identify, or Package on this page.

### Two SaaS ingest points only

1. **Node** — agent on the machine. E1 Collect and E2 Identity (Normalize) run here. The Node may send the shaped stream **straight to SaaS**, or **via Collector**.
2. **Collector (optional)** — two jobs in one column: aggregate / dedup what already came from Node, **or** collect network / application data itself (SNMP, flows, APM) with no Node hop.

Coordinator and a separate Gateway column are out of increment 1. Collector is the optional aggregate hop that the shift-left docs currently call Gateway.

### Vocabulary

- Normalize = E2 Identity (not E10 Identify).
- Always-on fabric = P1 = E1–E5. Writes land in SaaS `map/` (Pillar B) ∥ `history/` (Pillar A). The rooms do not sync.
- Detect = E6, output `Signal`. No root-cause claim. Door C is the primary spark (SaaS watches stores). Door A is a chip on Node only.
- Triage = E7–E8. Diagnose = E9–E11. Visible as a muted band on film 1; played on film 2 through Localize only.

### Illustrative packets

Checkout / orders teaching names (`orders-api` latency vs threshold). Not a live lab replay.

## Increment 2 (built)

A second looping film. It assumes increment 1 already warmed the rooms. There are still no step buttons.

### Beats played

1. **Warm** — `map/` and `history/` already queryable; rooms do not sync.
2. **Storm** — E6 Door C raises several correlated `Signal` objects (orders-api p95, checkout-web 5xx, payments-api latency).
3. **Curate** — E7 merges the storm into one `CaseSeed` (checkout ERROR). Default policy is one seed.
4. **Scope** — E8 read-joins neighbors from `map/` and sketches from `history/` into a `WorkingSet`.
5. **Localize** — E9 emits one `LeafClaim` (deepest error leaf → `payments-db` for this ERROR teaching story).

### Explicitly not played

E10 Identify (`EvidenceBundle`) and E11 Package (`VerdictCard`) stay muted. They wait for a later increment.

### Vocabulary carry-forward

Same join key language as the HLD: `tenant` + `ci_id`. A `Signal` is not a root cause. A `LeafClaim` is still not a packaged operator verdict.

### Deferred

Collector on/off as a control, Door A vs Door C timing, Coordinator as a control-only overlay, a named use-case pack as the packet script. **Pillar B PoC Increment 3** implements Identify/Package in code (`EvidenceBundle` → `VerdictCard`); a third fabric HTML film for those beats is optional later.
