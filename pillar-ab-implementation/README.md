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
| **Integration** | [`integration/`](./integration/) | After both unit suites are green |

```bash
# Pillar A
cd pillar-a/poc && make install && make test-all

# Pillar B
cd pillar-b/poc && make install && make test-all
```

## Contracts (canonical)

Shared brief, schemas, samples, and fabric Q&A: [`contracts/`](./contracts/) (`GRAPH_QNA.md` lives here; `docs/GRAPH_QNA.md` is a symlink).  
Package `docs/` folders are **symlinks** — do not replace with copies.

## Related docs (repo `docs/`)

- [`docs/GRAPH_QNA.md`](../docs/GRAPH_QNA.md)
- [`docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md`](../docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md)
- Cursor canvases: `pillar-a/reference/canvases/`

## Legacy combined PoC

Moved to [`_archive/pillar-ab-combined-poc-2026-08/`](../_archive/pillar-ab-combined-poc-2026-08/). Do not expand.
