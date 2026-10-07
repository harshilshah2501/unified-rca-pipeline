# Documentation search (Docs Ask)

**Audience:** You on iPhone or Mac when the WSL laptop and local docs hub (`http://127.0.0.1:8765`) are off.

## Live URL

**[https://unified-rca-docs-ask.harshilshah25.workers.dev](https://unified-rca-docs-ask.harshilshah25.workers.dev)** — bookmark or Add to Home Screen on iPhone.

## What you get

- Natural-language **questions** with **answers grounded in repo docs**
- **Citations** as GitHub links (`knowledge/…`, `product/contracts/…`, etc.)
- Same content family as the docs hub, rebuilt automatically when you **push to GitHub**

## Why GitHub + Cloudflare (not only GitHub)

| Need | GitHub alone | This design |
|------|------------|-------------|
| Docs stay versioned | Yes | Repo is source of truth |
| Laptop off at 6:30pm | No local server | **Cloudflare Worker** is always on |
| “Answer my question” + cites | Code search ≠ Q&A | Retrieval + **Workers AI** synthesis |
| Private doc content | Public Pages expose files | Optional **access token** on the Worker |

GitHub **Actions** rebuild the index on push; Cloudflare **hosts** the search UI and API.

## Setup (once)

Full steps: [`../tools/docs-ask/README.md`](../tools/docs-ask/README.md)

1. Add GitHub Actions secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
2. Run workflow **docs-ask deploy** (or push doc changes)
3. Bookmark the Worker URL (e.g. `https://unified-rca-docs-ask.<subdomain>.workers.dev`)
4. Optional: set `DOCS_ASK_TOKEN` via Wrangler; enter it once on your phone

## Local-only preview (laptop on)

```bash
python3 tools/docs-ask/index/build_index.py   # needs PyYAML: pip install pyyaml
cd tools/docs-ask/worker && npm install && npx wrangler dev
```

## Related

- Docs hub door: [Our HLD](./observeops/observeops-pipeline-hld.html)
- Portal audit: [HUB_PORTAL_AUDIT.md](./HUB_PORTAL_AUDIT.md)
