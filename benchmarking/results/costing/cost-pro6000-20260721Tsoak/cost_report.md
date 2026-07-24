# Cost report — L0 vs F1

**Run:** `cost-pro6000-20260721Tsoak`  
**Captured:** 2026-07-21T12:14:44Z  
**Host:** pro6000-server · 16 CPU · 125.79 GiB · tier B+

## Fairness contract

- Identical replay JSONL for L0 and F1.
- Only sink fan-out differs (L0 = lean; F1 = lean + structural + speed).
- GB/day is **extrapolated** from sink write rate (not retention-backed).
- Vector EPS includes container startup (conservative).

## Profile comparison

| Profile | Engine | Events | EPS | CPU-s / 1M evt | Sink bytes | GB/day (extrapolated) | Mean ingest ms |
|---------|--------|--------|-----|----------------|------------|----------------------|----------------|
| L0 | python_fanout | 500000 | 157273.34 | 6.36 | 116849997 | 3175.613 | 0.0064 |
| F1 | python_fanout | 500000 | 147517.83 | 6.78 | 271650069 | 6924.6541 | 0.0068 |
| L0 | vector_docker | 500000 | 4166.23 | — | 116849997 | 84.1231 | 0.2400 |
| F1 | vector_docker | 500000 | 4166.24 | — | 271650069 | 195.568 | 0.2400 |

## Dragonfly soak (C_store speed-tier proxy)

- Sustained EPS: **67084.8**
- p99 write: **0.379 ms**
- Duration: 120s · workers=16 · proactor=8
- Artifact: `benchmarking/results/costing/cost-pro6000-20260721Tsoak/phase0_soak.json`

## L0 → F1 delta (Python fan-out)

- EPS change: **-6.2%**
- Sink byte multiplier: **2.32×**
- Extra sinks: structural={'metric_sample', 'trace_span', 'anomaly', 'event'}, speed={'trace_span', 'anomaly', 'event'}

## Notes

- Headline ≥50K EPS gate is the **Dragonfly soak** (store path), not Vector/Python fan-out.
- RCA accuracy is measured separately (UC / Motadata bakeoff); this report is ingest cost only.
- Confidence: Python metrics = measured; GB/day = extrapolated; Vector EPS = measured wall incl. startup.
