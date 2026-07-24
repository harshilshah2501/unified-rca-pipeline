# E-com gold report compare (AD-HOC / INDEPENDENT)

**This folder is not part of the Unified-RCA product path or main corpus.**

Default compare of:

1. **Gold** — human OpenObserve-style incident analysis for `3GAWT8nVjUE2rA95CZmtyiQcVri`
2. **Lean** — `comprehensive_rca.v1` report for pack `ecom-numa-001`
3. **Federated** — same schema report for the same pack

Do **not** merge these scores into ObserveOps UC, Motadata L1, OpenObserve peer, or ADR-001 scoreboards.

## Status

Provenance-aware default dashboard (~99% Lean / ~99% Federated after closing structural gaps):

- Impact counts/rates: `source=derived_from_telemetry`
- App WARN evidence packed; alert.fire on timeline
- `causal_chain.topology_path` + `narrative_steps`
- Fed localizes via fusion without gateway onset override

Machine-readable: [`COMPARE.json`](./COMPARE.json)

## Open

- Browser: open [`index.html`](./index.html) locally
- Cursor canvas: `ecom-gold-report-compare.canvas.tsx` (search canvases)

## Reports (quarantined here)

| Engine | Path |
|--------|------|
| Gold | [`reports/gold/incident_report.md`](./reports/gold/incident_report.md) |
| Lean | [`reports/lean/incident_report.md`](./reports/lean/incident_report.md) |
| Federated | [`reports/federated/incident_report.md`](./reports/federated/incident_report.md) |

Engine verdicts used to build Lean/Fed still live under `benchmarking/results/{lean,federated}/ecom/…` (normal run artifacts). These **comprehensive report** snapshots are ad-hoc only.
