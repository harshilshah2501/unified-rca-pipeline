# Edge Delta use case 9 — GitHub workflow execute (2026-08-17)

**Honesty:** Observed (UI) after login. Not a Node/Gateway lab.  
**Org:** `gmailcom_d4486595` · user `harshilshah25@gmail.com`  
**Hub:** [`ed-lab-setup.html`](./ed-lab-setup.html) · **Use case docs:** [GitHub Development Workflow Automation](https://docs.edgedelta.com/ai-team-github-development-workflows/)

Screenshot: [`vendor-source/edgedelta/ed-uc9-github-thread-2026-08-17.png`](../vendor-source/edgedelta/ed-uc9-github-thread-2026-08-17.png)

---

## What fired

Use case 9 on this tenant is the scheduled workflow **Daily Report - github**, not a `@edge-delta` PR comment (no open PRs).

| Field | Value |
|-------|--------|
| Thread | Daily GitHub Engineering Risk Report |
| Thread id | `01M06G98NBQG2ADXK10P58NFXD` |
| Channel | `#code-issues` (`01KZZR1S5EDCADAPTKAJ563KSM`) |
| Source | Workflow |
| Status | **Resolved** · Human actions: No action required |
| Started | 2026-08-17 ~05:30 AM (UI) |
| Duration shown | ~3 minutes |
| Tokens | **391.1 K** |
| Teammate | Software Engineer (37 reasoning steps) |
| Linked issue | standalone (Issues **0**) |
| GitHub connector | `github-1786699123842` (`ed.connector.type` = github) |

Four Resolved GitHub-report threads exist (14 Aug 15:00, 15 Aug 05:33, 16 Aug 05:35, 17 Aug 05:34). Combined tokens this week: ~1.75 M. Pipeline `AI-Connector-Telemetry-Pipeline` has **two** GitHub HTTP inputs (`github-1786698950398`, `github-1786699123842`).

---

## Report (Observed UI, truncated)

Repo visible through the connector: **Unified RCA Pipeline**. Window 2026-08-16 00:00Z → 2026-08-17 00:00Z.

**Summary (5 bullets from the teammate):**

1. No engineering activity: zero human or bot PRs, issues, or default-branch commits in 24h; six-day baseline also zero.
2. CI visibility is the primary delivery risk: no workflow ran; only Dependabot dependency-graph processing is visible — not build/test/lint/deploy.
3. `main` remains unprotected (no required PRs, reviews, checks, or force-push restrictions).
4. No review backlog (no open or historical PRs).
5. Security telemetry incomplete: Dependabot-alert, secret-scanning, and audit-log APIs were unavailable.

**Ranked actions:** High — protect `main`; High — add `.github/workflows` application CI; Medium — grant alert/audit visibility; Low — reconcile zero connector events vs repo activity.

**Mode:** read-only investigation. No active failure; delivery-governance and observability risks only. Memory: same gaps as prior days.

Current `main` tip cited: `3a4bb3b` (predates the 7-day window). Newest visible Actions run: Dependabot graph `30908862009` on 4 Aug.

---

## What this is / is not

| Is | Is not |
|----|--------|
| UC9 GitHub development-workflow automation **Observed executing** | UC1 Pattern Anomaly (still No Data — no app logs) |
| E7–E11 analogue on the standing Team (thread + verdict, no Issue card) | Shift-left Node/Gateway fabric |
| GitHub as input **and** analysis target | `@edge-delta` PR review (no PR to tag) |

Cluster / Kubernetes connector still **blocked** until the Linux VM is ready.
