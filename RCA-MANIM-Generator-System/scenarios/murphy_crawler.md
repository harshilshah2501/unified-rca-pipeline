---
system: murphy
seed: 42
app_id: web_app
incident_time: "2024-06-15T12:00:00"
simulation:
  inner_sweeps: 4
  outer_samples: 5000
  model: "ridge + gibbs"
visualization:
  style: wave
  show_counterfactual: true
  show_drift: false
---
## Nodes
- id: crawler_vm, entity_type: vm, metrics: [session_count, throughput], mean: {session_count: 12.0, throughput: 120.0}, noise_std: {session_count: 1.0, throughput: 10.0}
- id: frontend_ms, entity_type: microservice, metrics: [latency_p90], mean: {latency_p90: 45.0}, noise_std: {latency_p90: 3.0}
- id: backend_vm_1, entity_type: vm, metrics: [cpu_usage], mean: {cpu_usage: 0.25}, noise_std: {cpu_usage: 0.01}
- id: normal_vm, entity_type: vm, metrics: [cpu_usage], mean: {cpu_usage: 0.2}, noise_std: {cpu_usage: 0.006}

## Edges
- from: crawler_vm, to: frontend_ms, src_metric: session_count, dst_metric: latency_p90, weight: 0.8, intercept: 45.0, bidirectional: false
- from: frontend_ms, to: backend_vm_1, src_metric: latency_p90, dst_metric: cpu_usage, weight: 0.004, intercept: 0.25, bidirectional: false

## Fault
type: spike
target: crawler_vm
metrics: [session_count, throughput]
multiplier: 8.0

## Symptom
entity: backend_vm_1
metric: cpu_usage
