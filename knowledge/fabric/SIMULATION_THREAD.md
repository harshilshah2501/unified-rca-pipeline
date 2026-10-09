# Simulation thread — unified film locks

This page records what the fabric film is allowed to show. Do not invent new names.

**Canonical film:** [`edge-platform-detect-simulation.html`](./edge-platform-detect-simulation.html) · `:8765/edge-platform-detect-simulation.html`

Former separate case and capture URLs redirect to the same page.

## Layout locks

1. **Two zones only.** Zone 1 = **Ingestion** (Edge devices · Node · optional Collector). Zone 2 = **SaaS platform · processing** (Ingest API → rooms → Maintain → Detect → triage → localize).
2. **Every handoff is labeled** on the wire with the contract that crosses it (`raw MELT`, `writer_stream.v1`, `GraphSnapshot`, `sketch.v1`, `Signal`, `CaseSeed`, `WorkingSet`, `LeafClaim`, `event cite`, …). Labels brighten when that beat is live.
3. **Split screen.** Left pane = end-to-end film. Clicking a processing block opens that block’s low-level admit / write flow on the right (especially E3 Pillar B GraphWriter and E4 Pillar A SketchWriter). The film keeps looping; detail is independent.

## Architecture locks (confirmed)

1. **Ingest API fans out to both rooms.** After E2 Identity, SaaS ingest offers **`writer_stream.v1`** to GraphRegulator (E3 → `map/`) and SketchRegulator (E4 → `history/`) **in parallel**. The rooms do not sync.
2. **E5 Maintain is shared.** Two outputs (no sync): **validity → E3 `map/` edges**, and **baselines → E4 `history/` sketches**. It does not create edges and does not merge rooms ([HLD E5](../observeops/OBSERVEOPS_PIPELINE_HLD.md)).
3. **Two SaaS ingest doors only:** Node (straight or via Collector) and optional Collector-direct (SNMP / flows / APM). Coordinator is not a data path.
4. **Normalize = E2 Identity** (not E10 Identify).
5. **Detect = E6 → `Signal`.** Door C (platform on sketches) is primary in the film. Door A on Node is shown unfired. An `anomaly` block also becomes a Signal. An `event` block (including logs) is evidence — correlates / Identify cites — not a second root-cause engine.
6. **Case path through Localize:** Curate → `CaseSeed` → Scope `WorkingSet` (read-join) → Localize `LeafClaim`. Identify cite is shown lightly; Package stays muted.
7. **No `fact_kind`.** Post-E2 wire is [`WRITER_REGULATOR.md`](../../pillar-ab-implementation/contracts/WRITER_REGULATOR.md): optional blocks `metric` · `topology` · `anomaly` · `event` · `span`. Regulators admit by **presence**, not a router enum. Logs use the `event` block (example `name: log.error`). Sketch p95 vs baseline is a Door C **read**, not a stream block.

## Film beats (one loop)

Emit → Collect → Normalize → Two doors → **Fan-out (writer_stream → map/ ∥ history/)** → **Maintain (E5 → both rooms)** → Capture (optional blocks) → Detect storm → Curate → Scope → Localize.

## Illustrative names

Checkout / orders teaching (`checkout-api`, `orders-api`, `payments-db`). Not a live lab replay.

## Deferred

Collector on/off as a control, Door A vs Door C side-by-side timing, Coordinator overlay, named use-case pack as the packet script, full Identify → Package film beats (Pillar B PoC Increment 3 covers code path).
