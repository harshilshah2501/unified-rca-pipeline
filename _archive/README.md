# Archive (not the live hub)

Parked snapshots and one-offs. **Do not edit these for live `:8765` docs.**

| Path | What it was |
|------|-------------|
| `exports/` | Frozen Aug 2026 portable docs-hub copy (+ zip). **Do not edit** — live hub is `../docs/`. Regenerate on demand later; do not treat as canonical. |
| `pillar-ab-combined-poc-2026-08/` | Pre-split combined A+B PoC (archived 2026-08-27). Live: `pillar-a/` / `pillar-b/` / `integration/`. |
| `_adhoc/` | One-off e-com gold compare and similar scratch |
| `notes/` | Off-record notes |
| `Pratik-docs/` | Parallel HLD/diagram copies formerly under `docs/` |
| `linux-server-ci-telemetry 2.*` | Root orphans; live copy is `docs/linux-server-ci-telemetry.json` |

Canonical hub content: `../docs/` and `../pillar-ab-implementation/`.  
Management binaries: `../KR Plan/`.

**Follow-up (not done this pass):** add `scripts/export-docs-hub.sh` to rsync live `docs/` + needed assets into a disposable folder when a portable snapshot is needed — instead of maintaining a permanent tree under `exports/`.
