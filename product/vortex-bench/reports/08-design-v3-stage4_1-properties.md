# Report 08 — Design v3 Stage 4.1 graph properties

Post-generation structural metrics for six synthetic estate families.
These are **modeling assumptions**, not Motadata production claims.

Source cells: `out/design-v3/stage4/characterize`

## Summary table

| Cell | Family | Nodes | Edges | Mean out | Out max | Out p99 | Top1% share | Reciprocity | Components | Validation |
| ---- | ------ | ----: | ----: | -------: | ------: | ------: | ----------: | ----------: | ---------: | ---------- |
| 1M-community | community | 200000 | 1000000 | 5.00 | 17 | 11 | 0.024 | 0.001 | 30 | OK |
| 1M-hierarchical | hierarchical | 199893 | 1000000 | 5.00 | 23 | 14 | 0.032 | 0.000 | 1 | OK |
| 1M-hubby | hubby | 200000 | 1000000 | 5.00 | 350 | 187 | 0.472 | 0.000 | 116 | OK |
| 1M-layered | layered | 200000 | 1000000 | 5.00 | 28 | 18 | 0.022 | 0.000 | 1519 | OK |
| 1M-power-law | power_law | 200000 | 1000000 | 5.00 | 3788 | 1537 | 0.118 | 0.000 | 1301 | OK |
| 1M-uniform | uniform | 200000 | 1000000 | 5.00 | 18 | 11 | 0.024 | 0.000 | 14 | OK |
| 500k-community | community | 100000 | 500000 | 5.00 | 17 | 11 | 0.023 | 0.001 | 8 | OK |
| 500k-hierarchical | hierarchical | 99948 | 500000 | 5.00 | 22 | 14 | 0.031 | 0.000 | 1 | OK |
| 500k-hubby | hubby | 100000 | 500000 | 5.00 | 295 | 227 | 0.466 | 0.000 | 49 | OK |
| 500k-layered | layered | 100000 | 500000 | 5.00 | 28 | 18 | 0.022 | 0.000 | 749 | OK |
| 500k-power-law | power_law | 100000 | 500000 | 5.00 | 3253 | 1577 | 0.121 | 0.000 | 649 | OK |
| 500k-uniform | uniform | 100000 | 500000 | 5.00 | 19 | 11 | 0.024 | 0.000 | 6 | OK |
| 5M-community | community | 1000000 | 5000000 | 5.00 | 19 | 11 | 0.024 | 0.000 | 126 | OK |
| 5M-hierarchical | hierarchical | 999465 | 5000000 | 5.00 | 25 | 14 | 0.031 | 0.000 | 1 | OK |
| 5M-hubby | hubby | 1000000 | 5000000 | 5.00 | 590 | 8 | 0.507 | 0.000 | 570 | OK |
| 5M-layered | layered | 1000000 | 5000000 | 5.00 | 29 | 18 | 0.022 | 0.000 | 7526 | OK |
| 5M-power-law | power_law | 1000000 | 5000000 | 5.00 | 3795 | 1559 | 0.120 | 0.000 | 6544 | OK |
| 5M-uniform | uniform | 1000000 | 5000000 | 5.00 | 19 | 11 | 0.024 | 0.000 | 45 | OK |

## Validation failures

None — all characterized cells passed family gates.

## Notes

- Mean out-degree target **5** for uniform / hubby / power_law / community; hierarchical / layered record realized means.
- Intra-community share recorded for `community` family when available.
- Stage 4.2 layout screening consumes only families that passed validation.
