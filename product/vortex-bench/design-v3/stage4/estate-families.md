# Estate families (Stage 4.0)

All families are **synthetic modeling assumptions**, not Motadata customer claims.

| Family | Generator intent | Validation targets (post-gen) |
| ------ | ---------------- | ----------------------------- |
| `uniform` | Near-uniform source/target | mean out-degree ≈ 5; top1% source edge share < 5% |
| `hubby` | 1% hubs emit 50% of edges | top1% source edge share ≥ 40%; max out ≫ p50 |
| `power_law` | Preferential attachment on sources | max out ≥ 50× mean; p99 out ≥ 10× mean |
| `hierarchical` | DC→cluster→host→VM→app→service tree + cross links | ≥5 node type layers; PART_OF/RUNS_ON dominate |
| `community` | 32 communities, 90% intra-community edges | intra-edge share ≥ 85% |
| `layered` | infra layer → app layer directed deps | reciprocity low (<0.15); DEPENDS_ON/USES heavy |

## Defaults

- Mean out-degree target **5** for uniform / hubby / power_law / community (`nodes = edges / 5`).
- Hierarchical / layered: structural skeleton first, then top-up random edges to reach `edges` budget; record realized mean degree.
- Seed **42** unless overridden.
- Scale ladder: 500k, 1M, 5M (cap).
