# Unified RCA — complete docs hub (portable)

Standalone copy of the browser documentation hub (`:8765/docs.html`).
Snapshot: **2026-08-17** (ED hub matches DT/DD chronology: Thesis · Breakdown · Dual-layer · Timeline · Portal walkthrough).

## How to open (required)

Pages use absolute paths (`/docs.html`, `/doc-nav.js`, `/urca-docs.css`, …).
**Do not open via `file://`.**

```bash
cd urca-docs-hub
python3 -m http.server 8765
```

Then open:

- Home / docs index: http://127.0.0.1:8765/  or  http://127.0.0.1:8765/docs.html
- Glossary: http://127.0.0.1:8765/urca-glossary.html
- Our HLD: http://127.0.0.1:8765/observeops-pipeline-hld.html
- Dynatrace hub: http://127.0.0.1:8765/dt-davis-category-hub.html
- Datadog hub: http://127.0.0.1:8765/dd-detect-category-hub.html
- Edge Delta hub: http://127.0.0.1:8765/ed-ai-team-hub.html
- DT vs DD vs ED: http://127.0.0.1:8765/comparable-pipeline-dt-dd.html

Suggested path: Our HLD (skim) → DT hub ERROR + SLOWDOWN → DD hub ERROR + SLOWDOWN → ED hub → DT vs DD vs ED → Motadata FR/AC.

## What’s inside

Full L0–L3 hub: vendor launchpads (DT · DD · **ED**), compare pages, HLD/LLDs, glossary,
lab timelines, MTL/Bits reviews, vendor JSON/screenshots (including Edge Delta tenant
and UC9 GitHub thread), agent-task notes, and linked markdown under `/docs/`.

## Omitted on purpose

- Live **PoC console** job API (`/api/status`, bakeoff runners). The Site bar “PoC console”
  link goes to this pack’s home. Workflow sim is at `/rca-workflow-sim.html`.
- Lab Docker/code trees (only RCA reference markdown files are included).

## Notes

- IBM Plex fonts load from Google when online; offline falls back to system fonts.
- External Datadog / Dynatrace / Edge Delta product URLs still need internet if you click them.
- Markdown files (LLDs, NAVIGATION.md, ED evidence notes) are served as raw text by `http.server`.
