# Unified-RCA — repository audit

**Status:** Phase A complete (2026-10-07). Living document — regenerate stats with [`../scripts/repo_inventory.py`](../scripts/repo_inventory.py).  
**Machine inventory:** [`REPO_INVENTORY.yaml`](./REPO_INVENTORY.yaml)  
**Docs hub portal:** [`HUB_PORTAL_AUDIT.md`](./HUB_PORTAL_AUDIT.md) · [`HUB_CATALOG.yaml`](./HUB_CATALOG.yaml)

## Decisions already locked

| Decision | Choice |
|----------|--------|
| Repo shape | Stay **one git monorepo**; reorganize into clear top-level **zones** with path shims |
| Lean + Federated | **Reference / archive** — Motadata Pillar A/B is the only active product track |
| Live edit roots | `docs/` + `pillar-ab-implementation/` only (see [`REPO_HYGIENE.md`](./REPO_HYGIENE.md)) |
| Cold SoT for map writers | [`WRITER_REGULATOR.md`](../pillar-ab-implementation/contracts/WRITER_REGULATOR.md) (`writer_stream.v1`, no `fact_kind`) |

## Executive summary

The tree mixes four eras of work:

1. **Active Motadata product** — Pillar A/B contracts + PoC code under `pillar-ab-implementation/`, fabric teaching under `docs/fabric/`, ObserveOps HLD under `docs/observeops/`.
2. **Docs hub portal clutter** — `:8765/docs.html` still surfaces vendor lab grids, agent-task prompts, Lean/Federated bakeoff, and a long fabric bullet list on one scroll (Phase E).
3. **Evaluation history** — `lean-pipeline/`, `federated-pipeline/`, bakeoff results — keep runnable, demote in navigation.
4. **Local bulk** — gitignored Motadata JSONL (~4G), Nezha trees (~3G), Rust `map-vortex/target` (~5G). Not in git; inflate `du` only.

**Consistency drift (measured at audit):** ~54 files still mention `fact_kind`; ~69 mention `ingest.v1`. Treat `ingest.v1` as the **ObserveOps / ingestion-poc bridge**; Motadata writers use `writer_stream.v1`.

## Worksheet sign-off (W1–W12)

| ID | Scope | Verdict | Action |
|----|-------|---------|--------|
| W1 | Docs flat symlinks | ~150 flat `docs/<name>` → topic folders — intentional for `:8765` | Keep; do not create orphan flat-only articles |
| W2 | contracts vs discussion | `contracts/` = normative; `discussion/` = pre-lock debate | Banner discussion as non-normative (C1) |
| W3 | pillar-b/docs vs fabric | Package walkthroughs stay; hub owns visuals | Link hub ← package; no second Hub copy |
| W4 | Dashboard | 91 symlinks, ~10 real host files — healthy host | Never fork articles under dashboard |
| W5 | Engines | Lean/Fed still callable from bakeoff scripts | Reference README banners; freeze feature work |
| W6 | Datasets | ObserveOps UC scoreboard-active; Motadata dumps local-only | Document in inventory; no delete |
| W7 | `_archive/` | Frozen hub export + old combined PoC | Keep one export; no day-edits |
| W8 | Bulk / CI | `target/`, `.venv`, JSONL gitignored | Document clone vs git size in root README |
| W9 | Hub portal pages | 144 pages crawled from seeds | See HUB_CATALOG — demote Tier 3 from index |
| W10 | Entry points | Competing: docs.html, Our HLD, NAVIGATION, hld-archive, PoC `/` | **Door = Our HLD**; slim docs.html |
| W11 | Past-task clutter | `docs/agent-tasks/`, learning decode notes, print PDFs | Move agent-tasks to archive; print stays Tier 3 |
| W12 | Tier 1 lock | [`OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md) under-enforced on index | Enforce in Phase E2 slim |

## Top-level action column

See full table in [`REPO_INVENTORY.yaml`](./REPO_INVENTORY.yaml). Highlights:

| Path | status | action |
|------|--------|--------|
| `docs/` | active | keep (portal slim) → future `knowledge/` shim |
| `pillar-ab-implementation/` | active | keep → future `product/` shim |
| `lean-pipeline/`, `federated-pipeline/` | reference | move under `reference/` with shim |
| `_archive/` | archive | keep → rename `archive/` with shim |
| `E6-E11-mapping.md`, `Vortex-unit-check.md`, root GIF | archive | move into `_archive/root-scratch/` |
| `ingestion-poc/` | active | keep — bridge, not writer SoT |

## Bridge vs SoT (ingest)

| Surface | Role |
|---------|------|
| [`INGEST_DATA_FORMAT.md`](./INGEST_DATA_FORMAT.md) + `ingestion-poc/` | ObserveOps corpus / Vector **`ingest.v1`** bridge |
| [`WRITER_REGULATOR.md`](../pillar-ab-implementation/contracts/WRITER_REGULATOR.md) | Motadata post-E2 **`writer_stream.v1`** SoT for Graph/Sketch writers |

## Regenerating stats

```bash
python3 scripts/repo_inventory.py --write
python3 scripts/repo_inventory.py --hub-write
```

## Change log

| Date | Note |
|------|------|
| 2026-10-07 | Initial Phase A + E0 inventory and hub crawl |
| 2026-10-07 | Phase E2 slim `docs.html`; agent-tasks → archive; C1 park; C2 zones (`knowledge`/`product`/`eval`/`reference`/`archive`) + root shims |
