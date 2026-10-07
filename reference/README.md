# Reference engines (evaluation history)

**Not on the Motadata Pillar A/B critical path.**

| Path | Role |
|------|------|
| [`lean-pipeline/`](./lean-pipeline/) | ADR-001 ObserveOps Lean diagnose engine |
| [`federated-pipeline/`](./federated-pipeline/) | Panorama → Murphy → Nezha bakeoff comparator |

Root shims `lean-pipeline/` and `federated-pipeline/` still point here so existing scripts keep working.

**Portal:** [`../docs/reference/eval-reference.html`](../docs/reference/eval-reference.html) (`:8765/eval-reference.html`).  
**Product SoT:** [`../product/`](../product/) (shim [`../pillar-ab-implementation/`](../pillar-ab-implementation/)).
