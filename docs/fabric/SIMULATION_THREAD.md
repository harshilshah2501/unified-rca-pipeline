# Simulation thread — increment 1 locks

This page records what the [edge → Detect simulation](./edge-platform-detect-simulation.html) is allowed to show. Later increments append here. Do not invent new names.

**Hub:** [`edge-platform-detect-simulation.html`](./edge-platform-detect-simulation.html) · `:8765/edge-platform-detect-simulation.html`

## Increment 1 (built)

Animate through a raised Detect event. Do **not** animate Curate, Scope, Localize, Identify, or Package.

### Two SaaS ingest points only

1. **Node** — agent on the machine. E1 Collect and E2 Identity (Normalize) run here. The Node may send the shaped stream **straight to SaaS**, or **via Collector**.
2. **Collector (optional)** — two jobs in one column: aggregate / dedup what already came from Node, **or** collect network / application data itself (SNMP, flows, APM) with no Node hop.

Coordinator and a separate Gateway column are out of increment 1. Collector is the optional aggregate hop that the shift-left docs currently call Gateway.

### Vocabulary

- Normalize = E2 Identity (not E10 Identify).
- Always-on fabric = P1 = E1–E5. Writes land in SaaS `map/` (Pillar B) ∥ `history/` (Pillar A). The rooms do not sync.
- Detect = E6, output `Signal`. No root-cause claim. Door C is the primary spark (SaaS watches stores). Door A is a chip on Node only.
- Triage = E7–E8. Diagnose = E9–E11. Visible as a muted band; not played.

### Illustrative packets

Checkout / orders teaching names (`orders-api` latency vs threshold). Not a live lab replay.

## Deferred

Collector on/off as a control, Door A vs Door C timing, Coordinator as a control-only overlay, a named use-case pack as the packet script, increment 2 (storm → one seed → WorkingSet → localize).
