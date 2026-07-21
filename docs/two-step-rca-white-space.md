# The Two-Step RCA Process — Where the Market Stops, and Where We Could Go Further

## The Two Steps, Simplified

Every RCA system — ours and every vendor we've checked — is really doing two very different jobs, even though people often talk about "root cause analysis" as if it's one single thing.

**Step 1 — "Which service is broken?" (Localization)**
Zoom in from the whole system down to one specific component. Think of this like a triage nurse: they don't diagnose your illness, they just tell you "the problem is in your stomach, not your head" — pointing you to the right department fast.

**Step 2 — "Why is it broken, at the code / execution-path level?" (Diagnosis)**
Once you know *which* service, you still need to know *what specifically* went wrong inside it. Which function misbehaved? Which call to another service timed out instead of succeeding? This is the actual specialist doctor's job — running tests, reading scans, forming a real diagnosis — not just pointing at an organ.

**The one-sentence version:** Step 1 tells you *where*. Step 2 tells you *what happened there, specifically*.

**How this maps to our full workflow** (see [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md)):

`Ingest → Detect → Localize → Identify → Verify`

- Step 1 ≈ **Localize** (+ Detect that starts the case).
- Step 2 ≈ **Identify** at execution-path depth (signature / expected-vs-actual), then **Verify** when we claim causal depth.

---

## How Vendors Handle Step 1 — Automated, and Genuinely Good

All three vendors we checked (Dynatrace, Datadog, BigPanda) automate Step 1 well, each in their own way:

- **Dynatrace** walks a continuously-updated map of how services depend on each other, using fixed logical rules, to point at one exact component.
- **Datadog** learns what "normal" looks like from history, and flags whichever component's behavior deviates most, labeling it the likely cause.
- **BigPanda** correlates alerts from many different tools into one incident and points at the most likely culprit.

All three genuinely automate: *"the problem is in payment-svc, not orders-api."* That's real, useful, automated Step 1.

## Where They All Stop — Step 2 Automation Gap

Here's the gap we care about: **none of them ship Nezha-style expected-vs-actual execution-path comparison as one continuous automated verdict.**

Vendors *do* help humans with “why” after localization — method hotspots, error spans, log/trace pivots, AI summaries. Dynatrace’s own community guidance describes this plainly as a two-part workflow: let the automated system find the service first, *then* manually dig into method-level detail. That is useful, but it is still **operator-driven Step 2**, not an automatic expected-vs-actual pattern diff fused into the root-cause answer.

**The raw material for automated Step 2 often exists** (Dynatrace’s method-level tracing is genuinely deep, for example) — but the **automatic comparison against a healthy execution-path baseline, emitted as part of the RCA verdict**, is what we could not verify as a shipped product feature.

**Scoped claim (use this wording in decks):** white space = *automated expected-vs-actual execution-pattern diff fused into the RCA verdict* — not “vendors never help explain why.”

## What Nezha Actually Did Differently

Nezha's real contribution was automating that specific Step 2 mechanism. Instead of stopping at "payment-svc is the problem" and leaving a human to dig further, it:

1. Learns what a **normal, healthy** request path through a service looks like (e.g., *Auth → DB_Query, completes in 200ms*)
2. Compares that against what **actually happened** in the current incident (e.g., *Auth → DB_Timeout, 5 seconds, failed*)
3. Surfaces that exact difference automatically — no human required to go find it

That specific mechanism — automatic expected-vs-actual comparison, at the execution-path level — is the piece nobody in the commercial market has copied into a continuous automated verdict, as far as we could verify.

---

## The White-Space Opportunity

This is worth taking seriously precisely *because* that scoped capability still looks unclaimed. If we build automated Step 2 carefully, we are not merely catching up to Dynatrace or Datadog on localization — we would differentiate on **path-level Identify** after Localize.

### How to actually build it, without breaking our own design principles

The temptation is to say "let's do what Nezha did, everywhere, all the time." That would be a mistake — it reintroduces exactly the cost problem our whole design has been built to avoid (the same reason we don't run the expensive causal check on every incident, only the ambiguous ones). The fix is to apply the same discipline we already use elsewhere: **only run the expensive thing on the narrow slice that actually needs it.**

**Proposed mechanism — call it Automated Execution-Pattern Diff:**

1. **Trigger:** runs automatically only on the *one* candidate our pipeline has already localized to — whether that came from Tier 1 alone, or after CARE resolved an ambiguous case. Never on the whole graph, never on every service.
2. **What it needs:** a continuously maintained **healthy execution-path baseline** per service (Nezha-class).  
   **Honest note:** today’s ObserveOps CARE PoC is **severity ranking under Δt ambiguity**, not a continuous healthy-path baseline. Pattern-diff baselines are a **new (or future shared) baseline store** — they can later share infrastructure with an enriched CARE, but they are **not** something CARE already collects in the current PoC.
3. **What it does:** pulls recent traces for that one already-localized service and diffs them against its expected pattern.
4. **What it outputs:** becomes part of the *same automated verdict*, not a separate manual step — e.g.:

   ```
   Root cause: payment-svc
   Expected:   Auth → DB_Query (≈200ms)
   Actual:     Auth → DB_Timeout (≈5000ms, failed)
   ```

### Why this fits our design instead of fighting it

| Design principle already in place | How this new piece follows the same rule |
|---|---|
| CARE only runs when Tier 1 is ambiguous, not on every incident | Execution-pattern diffing only runs on the one already-localized candidate, not the whole graph |
| The causal check (Tier 3) is scoped to a small candidate set, never the full topology | Same scoping logic — expensive Identify depth only after Localize |
| Every mechanism must stay reproducible — same input, same output | A pattern diff against a **fixed, versioned** expected baseline is deterministic; moving baselines must be versioned for replay |
| Federated promotion needs PoC data gates | Ship Step-2 only after [`FEDERATED_JUSTIFICATION_REPORT.md`](./FEDERATED_JUSTIFICATION_REPORT.md) gates pass on microservice incidents |

### The honest cost this adds

This isn't free — it needs a healthy-traffic **path** baseline maintained per service (and usually a speed-tier / trace store). Cost stays controlled **because** we scope the diff to one localized candidate, not because CARE already bought us the baseline for free. Nezha’s original design paid for fleet-wide path materialization; our proposal pays for **scoped** path diff after Localize.

**Promotion rule:** treat Automated Execution-Pattern Diff as a **stretch / Federated-track** capability. Prove it with measured gates before calling it a product differentiator.

---

## Bottom Line

Every vendor we checked automates “which service is broken” well; deeper “why, at the execution-path level” usually stays a **manual or assisted** follow-up. Nezha proved that *specific* second step can be automated as expected-vs-actual path comparison — we could not verify that exact fused automation as a commercial product feature. Building a **scoped**, narrow version of it — applied only after Localize, with an honest new baseline cost, and only after data-backed gates — would close a real gap **without** abandoning the cost discipline the rest of our design is built around.
