# Murphy — Performance Diagnosis for Distributed Cloud Applications

Python implementation of **Murphy** (SIGCOMM 2023): performance root-cause analysis via Markov Random Fields and counterfactual Gibbs sampling.

Paper: Vipul Harsh et al., *"Murphy: Performance Diagnosis of Distributed Cloud Applications"*, ACM SIGCOMM 2023. DOI: [10.1145/3603269.3604877](https://doi.org/10.1145/3603269.3604877)

## Overview

Murphy is **Tier 2 (Knowledge Graph)** of the Unified RCA platform:

```
Panorama (symptom) → Murphy.diagnose() → ranked root causes + explanations → Nezha
```

This implementation targets a **fully synthetic/simulated environment** — no real infrastructure. Metric time-series and topology are generated to validate algorithm correctness against the paper's methodology.

Three components:

1. **RelationshipGraph** — cyclic directed infrastructure topology
2. **MRFDiagnosisEngine** — online Ridge regression + counterfactual Gibbs sampling
3. **ExplanationGenerator** — state-machine causal chain narratives

## Requirements

- Python 3.11+
- See [requirements.txt](requirements.txt)

## Install

```bash
cd murphy
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export PYTHONPATH="$(pwd)/..:${PYTHONPATH}"
```

## Usage — SimulatedMetricStore

```python
from datetime import datetime
from murphy import Murphy, Symptom, SimulatedMetricStore
from murphy.tests.fixtures.crawler_incident import build_crawler_incident_store, build_crawler_symptom

store = build_crawler_incident_store()
symptom = build_crawler_symptom()

murphy = Murphy(monitoring_db=store)
result = murphy.diagnose(symptom)

for rc in result.root_causes:
    print(rc.entity_id, rc.metric_name, rc.anomaly_score, rc.p_value)
```

### Custom fault injection

```python
from datetime import datetime
from murphy import SimulatedMetricStore
from murphy.types import Entity

incident = datetime(2024, 6, 15, 12, 0, 0)
store = SimulatedMetricStore(seed=0)
store.add_entity(Entity("vm_a", "vm", "app1", metadata={"neighbors": ["vm_b"]}))
store.add_entity(Entity("vm_b", "vm", "app1", metadata={"neighbors": ["vm_a"]}))
store.define_metric("vm_a", "load", mean=10.0, noise_std=1.0)
store.define_metric("vm_b", "cpu_usage", mean=0.3, noise_std=0.02)
store.add_causal_rule("vm_a", "load", "vm_b", "cpu_usage", coefficient=0.01, intercept=0.2)
store.inject_fault("vm_a", "load", fault_type="spike", multiplier=10.0)
store.simulate(incident_time=incident)
```

## MetricStore implementations

| Store | Purpose |
|-------|---------|
| [`SimulatedMetricStore`](adapters/simulated_store.py) | Primary — synthetic time-series with fault injection and causal propagation |
| [`CsvMetricStore`](adapters/csv_store.py) | Load DeathStarBench CSV/Parquet traces for accuracy validation |
| `DictMetricStore` | Low-level dict-backed store for unit tests |

## Paper Constants (defaults)

| Parameter | Default |
|-----------|---------|
| Gibbs iterations (W) | 4 |
| Samples per T-test | 5000 |
| Counterfactual σ | 2.0 |
| Top-B neighbors | 10 |
| Training window | 7 days |

## Tests

```bash
cd murphy
PYTHONPATH=.. .venv/bin/pytest tests/ -v
```

Integration test [`tests/fixtures/crawler_incident.py`](tests/fixtures/crawler_incident.py) reproduces paper Figure 1 (Crawler → Frontend → Backend) with Host/NIC/ToR infrastructure entities.

## DeathStarBench validation

To validate against the paper's ~86% top-1 accuracy, export DeathStarBench traces to the schema documented in [`adapters/csv_store.py`](adapters/csv_store.py) and implement the CSV parser.

## Out of Scope

- Symptom detection (Panorama)
- Event-graph RCA (Nezha)
- Persistent model storage (Murphy trains online every invocation)
