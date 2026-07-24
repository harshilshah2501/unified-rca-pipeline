# Cost report — L0 vs F1

**Run:** `cost-pro6000-20260721Tfinal`  
**Captured:** 2026-07-21T12:26:25Z  
**Host:** pro6000-server · 16 CPU · 125.79 GiB · tier B+

## Fairness contract

- Identical replay JSONL for L0 and F1.
- Only sink fan-out differs (L0 = lean; F1 = lean + structural + speed).
- GB/day is **extrapolated** from sink write rate (not retention-backed).
- Vector EPS includes container startup (conservative).

## Profile comparison

| Profile | Engine | Events | EPS | CPU-s / 1M evt | Sink bytes | GB/day (extrapolated) | Mean ingest ms |
|---------|--------|--------|-----|----------------|------------|----------------------|----------------|
| L0 | python_fanout | 500000 | 153417.26 | 6.51 | 116849997 | 3097.7522 | 0.0065 |
| F1 | python_fanout | 500000 | 144201.32 | 6.92 | 271650069 | 6768.9732 | 0.0069 |
| L0 | vector_docker | 500000 | 31163.24 | — | 113222736 | 629.2381 | 0.0321 |
| F1 | vector_docker | 500000 | 66541.14 | — | 266557077 | 3123.5153 | 0.0150 |

## Dragonfly soak (C_store speed-tier proxy)

- Sustained EPS: **67084.8**
- p99 write: **0.379 ms**
- Duration: 120.0s · workers=16 · proactor=8
- Artifact: `benchmarking/results/costing/cost-pro6000-20260721Tsoak/phase0_soak.json`

## L0 → F1 delta (Python fan-out)

- EPS change: **-6.0%**
- Sink byte multiplier: **2.32×**
- Extra sinks: structural={'trace_span', 'anomaly', 'event', 'metric_sample'}, speed={'trace_span', 'anomaly', 'event'}

## Notes

- Headline ≥50K EPS gate is the **Dragonfly soak** (store path), not Vector/Python fan-out.
- RCA accuracy is measured separately (UC / Motadata bakeoff); this report is ingest cost only.
- Confidence: Python metrics = measured; GB/day = extrapolated; Vector EPS = measured wall incl. startup.
- Vector F1 wall can look faster than L0 on a warm second run (page cache); treat Vector as order-of-magnitude, Python fan-out for L0↔F1 delta.
