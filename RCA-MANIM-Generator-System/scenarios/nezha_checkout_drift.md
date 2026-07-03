---
system: nezha
seed: 42
simulation:
  inner_sweeps: 1
  outer_samples: 1
  model: event_graph
visualization:
  style: graph
  show_counterfactual: false
  show_drift: true
---
## Nodes
- id: evt_1, role: event, cluster_id: 12, template: "PlaceOrder start", pod: checkoutservice, span: place_order, path: both
- id: evt_2, role: event, cluster_id: 45, template: "Start charge card", pod: checkoutservice, span: place_order, path: both
- id: evt_3_ok, role: event, cluster_id: 46, template: "Charge successfully", pod: paymentservice, span: charge, path: expected
- id: evt_3_fail, role: event, cluster_id: 47, template: "Failed to connect payment service", pod: paymentservice, span: charge, path: actual
- id: evt_4, role: event, cluster_id: 13, template: "PlaceOrder end", pod: checkoutservice, span: place_order, path: both
- id: evt_fe, role: event, cluster_id: 20, template: "Frontend Recv start", pod: frontend, span: frontend_recv, path: both

## Edges
- from: evt_fe, to: evt_1, rule: B
- from: evt_1, to: evt_2, rule: A
- from: evt_2, to: evt_3_ok, rule: B
- from: evt_2, to: evt_3_fail, rule: B
- from: evt_3_ok, to: evt_4, rule: A
- from: evt_3_fail, to: evt_4, rule: A

## Fault
type: network
target: evt_3_fail
metrics: []
diverge_at: evt_2
