# Pillar A + Pillar B — implementation slice

**Location:** project root `pillar-ab-implementation/`  
**Status:** Split into owner packages (2026-08-27)  
**Owners:** Pillar A (statistics + sketch) — teammate · Pillar B (entities + edges) — Harshil  
**D5:** stays Review  
**Hygiene:** [`docs/REPO_HYGIENE.md`](../docs/REPO_HYGIENE.md)

## Start here (split packages)

| Package | Path | Zip for teammate? |
|---------|------|-------------------|
| **Pillar A** | [`pillar-a/`](./pillar-a/) | **Yes** — [`pillar-a-handoff-2026-08-27.zip`](./pillar-a-handoff-2026-08-27.zip) |
| **Pillar B** | [`pillar-b/`](./pillar-b/) | Owner local |
| **Integration** | [`integration/`](./integration/) | Optional **read-join harness** after both unit suites are green (not an A∪B merge) |

```bash
# Pillar A
cd pillar-a/poc && make install && make test-all

# Pillar B
cd pillar-b/poc && make install && make test-all
```

## Contracts (canonical)

Shared brief, schemas, samples, fabric Q&A, and **map write/read JSON record**: [`contracts/`](./contracts/) (`GRAPH_QNA.md` lives here; `docs/GRAPH_QNA.md` is a symlink).  
Map dest keys/encoding: [`contracts/MAP_WRITE_READ_RECORD.md`](./contracts/MAP_WRITE_READ_RECORD.md).  
Package `docs/` folders are **symlinks** — do not replace with copies.

## Team discussion

| Note | Topic |
|------|--------|
| [`discussion/04-raw-data-identity-lut-open-questions.md`](./discussion/04-raw-data-identity-lut-open-questions.md) | Raw data + Identity look-up table (LUT) open questions — vote card |
| [`Raw_Data_Handling.pdf`](./Raw_Data_Handling.pdf) | Source synthesis for discussion 04 |

## Related docs (repo `docs/`)

- [`docs/GRAPH_QNA.md`](../docs/GRAPH_QNA.md)
- [`docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md)
- Cursor canvases: `pillar-a/reference/canvases/`

## Legacy combined PoC

Moved to [`_archive/pillar-ab-combined-poc-2026-08/`](../_archive/pillar-ab-combined-poc-2026-08/). Do not expand.
