---
system: panorama
seed: 42
simulation:
  inner_sweeps: 1
  outer_samples: 1
  model: voting
visualization:
  style: vote
  show_counterfactual: false
  show_drift: false
---
## Nodes
- id: peer@1, role: observer
- id: peer@3, role: observer
- id: peer@5, role: observer
- id: peer@7, role: observer
- id: peer@9, role: subject
- id: leader, role: observer

## Edges

## Fault
type: partition
target: peer@9
metrics: [SyncThread]

## Reports
- observer: peer@1, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 20, tick: 1
- observer: peer@3, subject: peer@9, metric: SyncThread, status: MAYBE_UNHEALTHY, score: 40, tick: 1
- observer: peer@5, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 25, tick: 2
- observer: peer@7, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 30, tick: 2
- observer: leader, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 35, tick: 3
- observer: peer@1, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 22, tick: 3
- observer: peer@3, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 45, tick: 4
- observer: peer@5, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 28, tick: 4
- observer: peer@7, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 32, tick: 5
- observer: leader, subject: peer@9, metric: SyncThread, status: UNHEALTHY, score: 40, tick: 5
