# Reference canvases (Cursor)

These `.canvas.tsx` files were authored for Cursor’s Canvas panel. They are **reference copies** in git; Cursor also keeps a live copy under the project `canvases/` folder for Open Canvas.

**Problems panel noise:** opening a file under this `reference/canvases/` folder in the editor may show TypeScript errors (`Cannot find module 'cursor/canvas'`, missing JSX types). That is expected — the workspace TypeScript server does not load Cursor’s canvas SDK here. The managed copy under the project `canvases/` folder (Open Canvas) is the typed, rendered surface; these reference files carry `// @ts-nocheck` so the Problems list stays quiet.

## Docs hub door (use this on `:8765`)

**Do not click `.canvas.tsx` from the docs hub.** Those paths do not render in the browser and often 404 or open raw source.

| Need | Open |
|------|------|
| Pillar B PoC framing + all canvas → hub mappings | [`:8765/pillar-b-poc-hub.html`](http://127.0.0.1:8765/pillar-b-poc-hub.html) (source: [`docs/fabric/pillar-b-poc-hub.html`](../../../../docs/fabric/pillar-b-poc-hub.html)) |
| GraphWriter admit / I/O teaching | [`Our HLD → GraphWriter`](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter) |
| `map/` vs `history/` rooms | [`map-history-storage-blocks.html`](http://127.0.0.1:8765/map-history-storage-blocks.html) |

Catalog of other former canvases: [`docs/CANVASES.md`](../../../../docs/CANVASES.md).

## Optional: Open Canvas in Cursor (interactive panel)

1. **Command Palette** → **Open Canvas** → pick `pillar-b-poc-navigator` (live rendered view).
2. In the IDE file tree: open the managed copy under the project `canvases/` folder (not only this `reference/` path).
3. From chat: ask the agent to open the Pillar B PoC Navigator via Open Canvas.

## Files in this folder

| File | Hub replacement |
|------|-----------------|
| `pillar-b-poc-navigator.canvas.tsx` | [`pillar-b-poc-hub.html`](http://127.0.0.1:8765/pillar-b-poc-hub.html) |
| `graphwriter-io-walkthrough.canvas.tsx` | [Our HLD → GraphWriter](http://127.0.0.1:8765/observeops-pipeline-hld.html#graphwriter) |
| `map-history-storage-blocks.canvas.tsx` | [`map-history-storage-blocks.html`](http://127.0.0.1:8765/map-history-storage-blocks.html) |
