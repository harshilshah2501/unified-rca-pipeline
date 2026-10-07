/**
 * Datadog Detect-category registry + switcher for docs hub (:8765).
 *
 * Thesis is category-neutral (shared fabric). Breakdown / Three-rail stay one
 * copy each; ?cat=<id> frames Detect there and on Hub. Timeline is per-category.
 *
 * Include: <script src="/dd-detect-categories.js" defer></script>
 * Sticky slots:
 *   Engineering: Hub → Thesis → Breakdown → Three-rail → Timeline
 *   Interpret (run workbook, not BTS): MTL workbook · Bits
 * Breakdown = screenshot-grounded lean 8-stage IPO (Metrics∥Logs∥Traces).
 * MTL/Bits are Layer I (interpret one Observed run) — see OBSERVEOPS_PIPELINE_HLD.md.
 *
 * Datadog-native vocabulary: Agent, Unified Service Tags, Service Map,
 * Metrics/APM/Logs, Monitors, Watchdog, Related, flamegraph, Insights/Incident.
 */
(function (global) {
  "use strict";

  var CATS = [
    {
      id: "error",
      name: "ERROR",
      title: "ERROR · Failure rate",
      blurb:
        "Code-level KeyError (missing WIDGET-1). env:rca-lab-e3 · version:keyerror-20260810T072333Z. Door A Flask Alert after sustain · Door B APM Watchdog 0 · logs Watchdog stories yes. Clean telemetry (no fault.injected).",
      detect: "Door A Alert (sustain) · APM KeyError · logs Watchdog",
      status: "observed",
      evidence: "MCP KeyError · rca-lab-e3 · 2026-08-10",
      lab: "/dd-lab-timeline-error.html",
      mtlDoc: "/dd-error-mtl-dissection.html",
      bitsDoc: "/dd-bits-error-review.html",
      btsDoc: "/dd-behind-the-scenes-error.html",
      signal: "error_rate"
    },
    {
      id: "slowdown",
      name: "SLOWDOWN",
      title: "SLOWDOWN · Latency / response time",
      blurb:
        "Response-time degradation (ledger-scan CPU → slow HTTP 200). Stage 03 Write had long spans; stage 05 Detect stayed empty (error Door A OK · no latency monitor · Watchdog 0). Leaf found because the lab opened APM — Write ≠ Detect ≠ Localize.",
      detect: "05 empty · 03 Write strong · 07 operator Localize",
      status: "observed",
      evidence: "MCP + Bits ledger-scan · rca-lab-e3 · 2026-08-11",
      lab: "/dd-lab-timeline-slowdown.html",
      mtlDoc: "/dd-slowdown-mtl-dissection.html",
      bitsDoc: "/dd-bits-slowdown-review.html",
      signal: "response_time"
    },
    {
      id: "resource_contention",
      name: "RESOURCE_CONTENTION",
      title: "RESOURCE_CONTENTION · CPU / memory (semantic)",
      blurb:
        "Background CPU burn on inventory; HTTP stays fast 200. No Davis stamp — Host pack load Alert fired; Flask/APM-error doors stayed quiet.",
      detect: "Door A Host pack load Alert (310484611) · no category stamp",
      status: "observed",
      evidence: "MCP 2026-08-14 · rc-20260813t065225z · load Triggered 06:56:31Z / Recovered 07:07:31Z",
      lab: "/dd-lab-timeline-resource-contention.html",
      signal: "resource",
      agentTask: "/docs/agent-tasks/dd-resource-contention.md"
    },
    {
      id: "availability",
      name: "AVAILABILITY",
      title: "AVAILABILITY · Process down (semantic)",
      blurb:
        "Code-only inventory process exit; callers 502. Native Detect = absent inventory APM + caller errors + docker DIE — not a Datadog AVAILABILITY enum.",
      detect: "Caller APM 502 cascade · inventory DIE · no category stamp",
      status: "observed",
      evidence: "MCP 2026-08-14 · avail-20260813t070424z · FE/product error · inventory 0 spans · DIE ~07:05:35Z",
      lab: "/dd-lab-timeline-availability.html",
      signal: "availability",
      agentTask: "/docs/agent-tasks/dd-availability.md"
    },
    {
      id: "monitoring_unavailable",
      name: "MONITORING_UNAVAILABLE",
      title: "MONITORING_UNAVAILABLE · Visibility dark (semantic)",
      blurb:
        "MONITORING_DARK: HTTP 200; inventory APM 0 while FE/product still write. Logs continued (partial dark). No Datadog twin category.",
      detect: "Inventory APM gap · logs still present · no twin Alert",
      status: "observed",
      evidence: "MCP 2026-08-14 · mu-20260813t071758z · inventory APM 0 · logs 1564 · HTTP 200",
      lab: "/dd-lab-timeline-monitoring-unavailable.html",
      signal: "monitoring",
      agentTask: "/docs/agent-tasks/dd-monitoring-unavailable.md"
    }
  ];

  var TEACH = {
    mechanisms: "/datadog-subsystem-mechanisms.html",
    pipeline: "/datadog-production-pipeline.html",
    e2e: "/dd-e2e-metrics-traces-logs.html",
    hub: "/dd-detect-category-hub.html"
  };

  /**
   * Shared pipeline teaching — Method, backend stores, Door vs rails, stage IPO, tab jobs.
   * Mount: <div id="urca-dd-pipeline-guide" data-variant="full|compact"></div>
   * Official: Metrics timeseries ≠ Husky event store (logs/traces/NPM/RUM/…).
   * Refs: https://www.datadoghq.com/blog/engineering/introducing-husky/
   *       https://www.datadoghq.com/blog/engineering/husky-query-architecture/
   */
  var PIPELINE = {
    method:
      "Finish independent Datadog end-to-end dissection for ERROR-rate and SLOWDOWN first " +
      "(Detect → leaf → packaging limits). Dynatrace ↔ Datadog building-block parallels come only " +
      "after both categories have that insight — not mid-pipeline.",
    methodMap: [
      { phrase: "Write (continuous)", stages: "03 · M ∥ APM ∥ Logs (not Detect)" },
      { phrase: "Detect", stages: "05 · Monitors · Watchdog (Door A ∥ Door B)" },
      { phrase: "leaf", stages: "07 · Flamegraph leaf · tag join" },
      { phrase: "packaging limits", stages: "08 · Bits Investigation ∥ Incident (often absent)" }
    ],
    stores: {
      title: "Backend reality (official engineering) — not three equal peer DBs",
      product:
        "Operator UI still has three rails: Metrics ∥ APM (Traces) ∥ Logs, joined by Unified Service Tags.",
      metrics:
        "Metrics = classic timeseries store (<timeseries_id, timestamp, float64>). Pre-aggregated; bounded tag cardinality. Separate from Husky.",
      husky:
        "Husky = Datadog’s 3rd-gen event store on the Event Platform. Holds high-cardinality events: Logs, Traces/APM spans, plus NPM / RUM / Continuous Profiler events. Kafka → Writers → object storage + FoundationDB metadata → Compactors → Readers.",
      join:
        "Teaching join is still tags (+ trace_id for log↔span). Product explorers stay separate even when Traces and Logs share the Husky event-family backend.",
      cite:
        "Datadog eng: Introducing Husky · Husky query architecture (logs, traces, network data, and more)."
    },
    doors: {
      myth: "Both Doors do not equally consume Metrics ∥ Traces ∥ Logs for Detect.",
      fabric:
        "Stage 03 writes all three product rails continuously (Metrics timeseries + Husky events for traces/logs) — includes live baseline / warm discovery. Stage 05 Detect reads a narrower primary input per Door. Logs re-enter as equal evidence at stage 07 (tag join). There is no Maintain stage — Write is 03.",
      doorA:
        "Door A · Monitors — explicit query + threshold (pack- or user-authored). Lab ERROR: APM/Metrics errors÷hits > 0.1 with min(last_15m) (monitor 310925690). Short windows often OK; sustained ≈15m near-100% errors → Alert (e3 Observed). Lab SLOWDOWN: that same error Door stays OK on HTTP 200; a latency/p95 Door A was never scoped → no Alert.",
      doorB:
        "Door B · Watchdog — anomaly stories → source:watchdog events → optional APM bridge (310485027). Lab e3 ERROR screenshots: Watchdog Insights Logs Error Outliers (~⅓ each). Lab SLOWDOWN: 0 APM Watchdog stories (deployment version story ≠ latency RCA).",
      bits:
        "Bits = peer hub tab (Bits AI Investigation) after Detect — same sticky chrome as Thesis/MTL. ERROR: Metrics (neg. host) + Logs KeyError + Traces 500/502 → Hypothesis Tree. SLOWDOWN: APM self-time leaf + host CPU (error Door A OK). Incident = optional. Detect does not start Bits — you (or a prompt) seed the Investigation.",
      independence:
        "∥ = parallel, not merged. Same fault can light both doors with different verdicts — Observed ERROR e3: Door A Alert after sustain, Door B APM quiet, logs Watchdog Insights present.",
      emptyDetect:
        "SLOWDOWN Observed trap: stage 03 Write can be loud (p95 ~9–22s, hundreds of ok spans >5s) while stage 05 Detect is silent (no latency monitor · error Door OK · Watchdog 0). Slow charts in explorers are Write, not Detect. The lab found the leaf by opening APM for a known fault window — operator Localize (07), not a Door foghorn. Slow data ≠ Detected incident. Detail: Timeline §2 Write ≠ Detect ≠ Localize."
    },
    stages: [
      {
        n: "01",
        name: "Agent",
        input: "Host/app telemetry (ddtrace, DogStatsD, log tails, containers)",
        process: "Collect, buffer, export",
        output: "Payloads toward intake",
        consumer: "02–03"
      },
      {
        n: "02",
        name: "Tagging",
        input: "Untagged / partial records",
        process: "Stamp service·env·version·host/container",
        output: "Join-ready identity (env:rca-lab-e3 filter works)",
        consumer: "03–04, later pivots"
      },
      {
        n: "03",
        name: "M ∥ APM ∥ Logs",
        input: "Tagged stream",
        process: "∥ write: Metrics timeseries + Husky events (spans/logs); continuous fabric + baseline",
        output: "Three product explorers (screenshot inputs)",
        consumer: "04–05, explorers"
      },
      {
        n: "04",
        name: "Service Map",
        input: "APM peers",
        process: "Materialize service nodes + call edges",
        output: "Dependency view (can lag traces)",
        consumer: "Operator triage"
      },
      {
        n: "05",
        name: "Monitors · Watchdog",
        input: "Door A queries · Door B anomaly features · Logs for Insights",
        process: "Threshold eval ∥ stories ∥ Insights outliers — or stay quiet if no matching Door",
        output: "Monitor status · Watchdog/Insights cards · ALERT or OK (or empty foghorn)",
        consumer: "06 (optional Bits click) — SLOWDOWN Observed: empty → operator still may open APM"
      },
      {
        n: "06",
        name: "Triage · Related",
        input: "Hot Door A/B / Insights cards — or operator-chosen latency window when Detect is empty",
        process: "Pick primary symptom · lock env/version/time",
        output: "Scoped seed (inventory 500 direction, or inventory @duration for SLOWDOWN)",
        consumer: "07"
      },
      {
        n: "07",
        name: "Leaf · tag join",
        input: "Scoped traces + logs (+ metrics)",
        process: "ERROR: deepest error span · SLOWDOWN: longest self-time span · same trace_id corroboration",
        output: "Leaf claim (inventory KeyError/500 · or inventory.stock long HTTP 200)",
        consumer: "08 / write-up"
      },
      {
        n: "08",
        name: "Bits ∥ Incident",
        input: "Alert + leaf + MTL",
        process: "Optional Bits narrative ∥ Incident declare",
        output: "Package (Incident often absent)",
        consumer: "Humans / postmortem"
      }
    ],
    tabs: [
      {
        tab: "Thesis",
        job: "Mental model + evidence map",
        why:
          "What Datadog is: Agent → tags → product rails → Detect doors → leaf → thin packaging. Where Metrics timeseries vs Husky events fit. One lab walkthrough; Detect classes are examples, not Thesis modes.",
        not: "Not the animated stage walk; not the ERROR query workbook; not a category switcher."
      },
      {
        tab: "Breakdown",
        job: "8 mechanisms · screenshot IPO",
        why:
          "Lean stages with Input→Process→Output. ERROR embeds Host Metrics · Log Explorer · Trace Explorer and drives Detect→leaf→Bits. Method maps onto 05 / 07 / 08.",
        not: "Not clocked break/heal; not MCP count tables."
      },
      {
        tab: "Three-rail journey",
        job: "Animated write path across stages",
        why:
          "Play how Metrics ∥ APM ∥ Logs appear at each stage for the active ?cat=. Teaches continuous write + tag join. Backend note: Metrics store ∥ Husky events (traces+logs).",
        not: "Not copy-paste queries or Observed scalars — that is MTL workbook."
      },
      {
        tab: "Timeline",
        job: "Clocked Observed lab narrative",
        why:
          "Break / load / heal / Detect surfaces for one category (ERROR or SLOWDOWN). Chronological teaching evidence.",
        not: "Not the pipeline animation; not the full query cookbook."
      },
      {
        tab: "MTL workbook",
        job: "Interpret · operator workbook (Layer I)",
        why:
          "Emit · explorer queries · MCP counts · Detect doors for one Observed run. Not a behind-the-scenes fabric stage.",
        not: "Not Collect/Detect/Localize engineering; not a second Three-rail journey."
      },
      {
        tab: "Bits",
        job: "Interpret · optional packaging walk (Layer I)",
        why:
          "Hypothesis loop for one investigation. ERROR: 500 vs 502. SLOWDOWN: self-time leaf. Maps to optional E11 narrator — not a separate fabric block.",
        not: "Not MTL query cookbook; not required to name the leaf from flamegraph alone."
      }
    ]
  };

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderPipelineGuide(el, opts) {
    if (!el) return;
    opts = opts || {};
    var variant = opts.variant || el.getAttribute("data-variant") || "full";
    var compact = variant === "compact";
    var html = [];
    html.push('<div class="urca-dd-pg">');
    html.push('<p class="urca-dd-pg-method"><strong>Method · </strong>' + escapeHtml(PIPELINE.method) + "</p>");
    html.push("<table class=\"urca-dd-pg-map\"><thead><tr><th>Method phrase</th><th>Breakdown stages</th></tr></thead><tbody>");
    PIPELINE.methodMap.forEach(function (row) {
      html.push(
        "<tr><td><strong>" +
          escapeHtml(row.phrase) +
          "</strong></td><td>" +
          escapeHtml(row.stages) +
          "</td></tr>"
      );
    });
    html.push("</tbody></table>");

    html.push('<h3 class="urca-dd-pg-h">' + escapeHtml(PIPELINE.stores.title) + "</h3>");
    html.push("<ul class=\"urca-dd-pg-door-list\">");
    html.push("<li><strong>Product rails · </strong>" + escapeHtml(PIPELINE.stores.product) + "</li>");
    html.push("<li><strong>Metrics · </strong>" + escapeHtml(PIPELINE.stores.metrics) + "</li>");
    html.push("<li><strong>Husky · </strong>" + escapeHtml(PIPELINE.stores.husky) + "</li>");
    html.push("<li><strong>Join · </strong>" + escapeHtml(PIPELINE.stores.join) + "</li>");
    html.push("<li><strong>Cite · </strong>" + escapeHtml(PIPELINE.stores.cite) + "</li>");
    html.push("</ul>");

    html.push('<p class="urca-dd-pg-doors"><strong>Doors vs rails · </strong>' + escapeHtml(PIPELINE.doors.myth) + " ");
    html.push(escapeHtml(PIPELINE.doors.fabric) + "</p>");
    html.push("<ul class=\"urca-dd-pg-door-list\">");
    html.push("<li>" + escapeHtml(PIPELINE.doors.doorA) + "</li>");
    html.push("<li>" + escapeHtml(PIPELINE.doors.doorB) + "</li>");
    html.push("<li>" + escapeHtml(PIPELINE.doors.independence) + "</li>");
    html.push("<li>" + escapeHtml(PIPELINE.doors.bits) + "</li>");
    html.push("</ul>");
    var catId =
      window.URCA_DD_CATS && typeof window.URCA_DD_CATS.current === "function"
        ? (window.URCA_DD_CATS.current() || {}).id
        : "";
    if (catId === "slowdown" || !compact) {
      html.push(
        '<p class="urca-dd-pg-empty"><strong>SLOWDOWN · empty Detect · </strong>' +
          escapeHtml(PIPELINE.doors.emptyDetect) +
          ' <a href="/dd-lab-timeline-slowdown.html?cat=slowdown#insight">Timeline §2</a>.</p>'
      );
    }
    if (!compact) {
      html.push("<h3 class=\"urca-dd-pg-h\">8-stage IPO (Input → Process → Output → Consumer)</h3>");
      html.push(
        "<table class=\"urca-dd-pg-ipo\"><thead><tr><th>#</th><th>Stage</th><th>Input</th><th>Processing</th><th>Output</th><th>Consumed by</th></tr></thead><tbody>"
      );
      PIPELINE.stages.forEach(function (s) {
        html.push(
          "<tr><td>" +
            escapeHtml(s.n) +
            "</td><td><strong>" +
            escapeHtml(s.name) +
            "</strong></td><td>" +
            escapeHtml(s.input) +
            "</td><td>" +
            escapeHtml(s.process) +
            "</td><td>" +
            escapeHtml(s.output) +
            "</td><td>" +
            escapeHtml(s.consumer) +
            "</td></tr>"
        );
      });
      html.push("</tbody></table>");
      html.push("<h3 class=\"urca-dd-pg-h\">Hub tabs — same spine, different zoom</h3>");
      html.push(
        "<table class=\"urca-dd-pg-tabs\"><thead><tr><th>Tab</th><th>Job</th><th>Use for</th><th>Not for</th></tr></thead><tbody>"
      );
      PIPELINE.tabs.forEach(function (t) {
        html.push(
          "<tr><td><strong>" +
            escapeHtml(t.tab) +
            "</strong></td><td>" +
            escapeHtml(t.job) +
            "</td><td>" +
            escapeHtml(t.why) +
            "</td><td>" +
            escapeHtml(t.not) +
            "</td></tr>"
        );
      });
      html.push("</tbody></table>");
    } else {
      html.push(
        '<p class="urca-dd-pg-tabs-short"><strong>Tabs · </strong>' +
          "Engineering: Thesis · Breakdown · Three-rail · Timeline. " +
          "Interpret (run): MTL · Bits. " +
          "Backend: Metrics timeseries ∥ Husky events (traces+logs). " +
          'Our HLD: <a href="/observeops-pipeline-hld.html">ObserveOps pipeline</a> · ' +
          '<a href="/dd-detect-category-hub.html">Hub</a>.</p>'
      );
    }
    html.push("</div>");
    el.innerHTML = html.join("");

    if (!document.getElementById("urca-dd-pg-style")) {
      var st = document.createElement("style");
      st.id = "urca-dd-pg-style";
      st.textContent = [
        ".urca-dd-pg{margin:1rem 0 1.25rem;padding:1rem 1.1rem;border-radius:8px;",
        "background:rgba(79,209,160,.07);border:1px solid rgba(79,209,160,.32);color:#d8e0e8;font-size:15px;line-height:1.55;}",
        ".urca-dd-pg-method{margin:0 0 .75rem;}",
        ".urca-dd-pg-method strong,.urca-dd-pg-doors strong,.urca-dd-pg-tabs-short strong,.urca-dd-pg-h{color:#7aecc4;}",
        ".urca-dd-pg-h{font-size:1rem;font-weight:650;margin:1rem 0 .5rem;color:#f2f5f8;}",
        ".urca-dd-pg-doors{margin:.5rem 0;}",
        ".urca-dd-pg-empty{margin:.75rem 0 0;padding:.75rem .85rem;border-radius:6px;",
        "background:rgba(240,179,90,.12);border-left:3px solid #F0B35A;color:#d8e0e8;}",
        ".urca-dd-pg-empty strong{color:#F0B35A;}",
        ".urca-dd-pg-door-list{margin:.35rem 0 .75rem 1.1rem;}",
        ".urca-dd-pg-door-list li{margin:.35rem 0;}",
        ".urca-dd-pg table{width:100%;border-collapse:collapse;font-size:14px;margin:.4rem 0 .8rem;}",
        ".urca-dd-pg th,.urca-dd-pg td{text-align:left;vertical-align:top;padding:.4rem .45rem;border-bottom:1px solid #2a3441;color:#d8e0e8;}",
        ".urca-dd-pg th{color:#b0bac6;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;}",
        ".urca-dd-pg td strong{color:#f2f5f8;}",
        ".urca-dd-pg a{color:#7BA8F5;}",
        ".urca-dd-pg code{font-family:ui-monospace,monospace;font-size:.9em;background:#1c2430;padding:.05rem .3rem;border-radius:3px;color:#b8d4ff;}"
      ].join("");
      document.head.appendChild(st);
    }
  }

  function fillPipelineGuides() {
    var nodes = document.querySelectorAll("#urca-dd-pipeline-guide, [data-urca-dd-pipeline]");
    Array.prototype.forEach.call(nodes, function (el) {
      renderPipelineGuide(el);
    });
  }

  /**
   * Teaching payloads — drive Three-rail (M∥T∥L) and Breakdown tips.
   * Thesis is category-neutral (both ERROR and SLOWDOWN as examples).
   * Datadog-native: monitors · Watchdog · tags · flamegraph · Incident-absent honesty.
   */
  var LAB = {
    error: {
      id: "error",
      evidence: "2026-08-10 MCP KeyError · env:rca-lab-e3",
      leaf: "inventory GET /api/stock → 500 KeyError",
      cascade: "product/frontend → 502",
      clocks: ["baseline (pre-07:24Z)", "fault W1", "healed", "fault W2"],
      faultWindow: "Baseline before 07:24:50Z · W1 07:24–07:31Z · W2 07:45–07:56Z (e3)",
      detectSignal: "error_rate",
      detectThr: 0.1,
      detectUnit: "ratio",
      detectTitles: [
        "① Watch — flask.request errors/hits by {env,service}",
        "② Door A — Flask High Error Rate → Alert after sustain (min 15m)",
        "③ Door B APM — 0 story_category:apm · bridge OK",
        "④ Cascade — FE/product 502; leaf remains inventory KeyError"
      ],
      detectSeries: [
        { id: "inventory", signal: "err%", healthy: 0.02, fault: 1.0, order: 0 },
        { id: "product", signal: "err%", healthy: 0.01, fault: 1.0, order: 1 },
        { id: "frontend", signal: "err%", healthy: 0.01, fault: 1.0, order: 2 }
      ],
      events: [
        { type: "APM span error", e: "inventory", ts: "fault+", v: "500 KeyError · ~2427", role: "leaf" },
        { type: "APM span error", e: "product", ts: "fault+", v: "502 · ~2421", role: "caller" },
        { type: "APM span error", e: "frontend", ts: "fault+", v: "502 · ~2421", role: "edge" },
        { type: "monitor", e: "flask High Error Rate", ts: "after sustain", v: "Alert · 310925690", role: "detect" },
        { type: "Watchdog APM", e: "story_category:apm", ts: "window", v: "0 · bridge OK", noise: true },
        { type: "Watchdog Logs", e: "logs_pattern_anomaly", ts: "~07:51Z+", v: "inventory/product/FE", role: "detect" }
      ],
      packageLines: [
        ["Incident", "0 (until Declare)"],
        ["Door A Flask monitor", "Alert after sustain · 310925690"],
        ["Door B APM bridge", "OK · 0 APM stories · 310485027"],
        ["Watchdog Logs stories", "present · env:rca-lab-e3"],
        ["Bits Investigation", "optional — see Bits review steps"],
        ["flamegraph leaf", "deepest KeyError · inventory 500"]
      ],
      packageNote:
        "No fault.injected. Filter env:rca-lab-e3 · version:keyerror-20260810T072333Z. Bits: /dd-bits-error-review.html",
      mtl: {
        metrics:
          "MCP e3: rca.inventory.stock.errors≈2403 · flask.errors inv 2403 · FE/product 2397. version:keyerror-20260810T072333Z.",
        traces:
          "MCP: KeyError/500≈2427 · Upstream*/502≈2421 each. Sample 6a79840f…. Reload container 3f0f94af…. No fault.injected.",
        logs:
          "MCP: @event:inventory.stock.error KeyError≈2486 · product≈2481 · frontend≈2480 · log↔trace via trace_id"
      },
      journey: [
        {
          key: "agent",
          title: "Agent",
          m: "host + container tags ready",
          a: "ddtrace → Agent :8126",
          l: "rca_lab_logs.d file tail",
          teach: "Agent Collect: host/container sources ∥ app sources (ddtrace, DogStatsD, logs). Intake only — Detect later."
        },
        {
          key: "tagging",
          title: "Tagging",
          m: "env:rca-lab-e3 · version:keyerror-…",
          a: "same tags on spans + container_id/image_id",
          l: "same join keys",
          teach: "App DD_* ∥ Agent Docker tags. e3 isolates prior rca-lab / e2 history."
        },
        {
          key: "service_map",
          title: "Service Map",
          m: "catalog names appear",
          a: "peers FE→product→inventory",
          l: "host/container context",
          teach: "Catalog nodes ∥ peer edges from spans. Topology only — not leaf. Leaf = deepest error / flamegraph later."
        },
        {
          key: "stores",
          title: "M ∥ T ∥ L",
          m: "hits/errors + rca.* write",
          a: "KeyError spans write",
          l: "inventory.stock.error lines",
          teach: "Three-rail ∥ write: Metrics · Traces · Logs under the same env/version."
        },
        {
          key: "intake",
          title: "Always-on fabric",
          m: "→ timeseries store",
          a: "→ Husky events",
          l: "→ Husky events",
          teach: "Pre-Detect writes: Metrics→timeseries · APM+Logs→Husky. Baseline = before 07:24:50Z. W1/W2 are fault windows. Not an alert."
        },
        {
          key: "monitors_watchdog",
          title: "Monitors · Watchdog",
          m: "Door A Alert after sustain",
          a: "Door B APM 0 stories",
          l: "logs Watchdog stories",
          teach: "Door = Detect entry only. Door A metric/APM ratio · Door B APM bridge ≠ logs stories. ∥ independent. Detect ≠ Bits ≠ Incident."
        },
        {
          key: "triage",
          title: "Alert triage",
          m: "three hot services",
          a: "typed KeyError vs Upstream*",
          l: "stock.error lines",
          teach: "Cascade cards ∥ leaf pick — choose inventory KeyError, not checkout 502."
        },
        {
          key: "related",
          title: "Related scope",
          m: "scope env:rca-lab-e3 + time",
          a: "fault W1 or W2 (not baseline)",
          l: "host filter",
          teach: "Baseline = before 07:24:50Z. Fault scopes: W1 07:24–07:31Z · W2 07:45–07:56Z. Isolate e3 from retired envs."
        },
        {
          key: "flamegraph",
          title: "Flamegraph leaf",
          m: "error-rate explorer",
          a: "deepest KeyError / 500",
          l: "log corroboration",
          teach: "Symptom 502 ∥ leaf KeyError — operator deepest-error judgment."
        },
        {
          key: "tag_join",
          title: "Tag join",
          m: "same tags on series",
          a: "same tags + container_id",
          l: "same tags on logs",
          teach: "Metrics check ∥ Trace check ∥ Log check on one env/version."
        },
        {
          key: "insights",
          title: "Insights · Incident",
          m: "no auto Incident",
          a: "Bits optional · Door A Alert",
          l: "logs stories optional path",
          teach: "Bits path ∥ Incident path. Infra IDs match fault-time; heal/reload changes container_id."
        }
      ],
      thesisDetect:
        "Detect tip = Door A (Flask High Error Rate <code>310925690</code>, thr &gt; 0.1, <code>min(last_15m)</code> → <strong>Alert</strong> after sustain) ∥ Door B APM (0 stories · bridge <code>310485027</code> OK) ∥ Watchdog logs_pattern_anomaly under <code>env:rca-lab-e3</code>. Detect ≠ Bits ≠ Incident.",
      thesisLab:
        "Fault: <code>break_inventory_code.sh</code> → inventory <strong>500 KeyError</strong>, checkout <strong>502</strong>. Isolate: <code>env:rca-lab-e3</code> · <code>version:keyerror-20260810T072333Z</code>. Read deepest KeyError on inventory."
    },
    slowdown: {
      id: "slowdown",
      evidence: "2026-08-11 MCP ledger-scan · env:rca-lab-e3",
      leaf: "inventory lookup_stock_in_warehouse → 200 · ~9–22s",
      cascade: "product/frontend wait on inventory (still 200)",
      clocks: ["healthy", "slow on", "sustained", "healed"],
      faultWindow: "~12 min slow 200s under load (04:58–05:10Z)",
      detectSignal: "latency / p95",
      detectThr: 2.0,
      detectUnit: "seconds",
      detectTitles: [
        "① Write — flask.request duration / p95 by {env,service} (stage 03)",
        "② Symptom — inventory leaf p50 ~10.9 s / p95 ~17.6 s (HTTP still 200)",
        "③ Cascade — product/frontend wall time rises while waiting",
        "④ Detect — often empty in lab (no latency Door A · Watchdog 0); operator opens APM"
      ],
      detectSeries: [
        { id: "inventory", signal: "p95_s", healthy: 0.005, fault: 17.6, order: 0 },
        { id: "product", signal: "p95_s", healthy: 0.008, fault: 17.6, order: 1 },
        { id: "frontend", signal: "p95_s", healthy: 0.02, fault: 17.6, order: 2 }
      ],
      events: [
        { type: "APM slow span", e: "inventory", ts: "fault+", v: "~11s", role: "leaf" },
        { type: "APM slow span", e: "product", ts: "fault+", v: "~11s", role: "caller" },
        { type: "APM slow span", e: "frontend", ts: "fault+", v: "~11s", role: "edge" },
        { type: "Watchdog", e: "(none observed)", ts: "window", v: "0", noise: true }
      ],
      packageLines: [
        ["Incident", "0"],
        ["Watchdog story", "0"],
        ["Bits Investigation", "observed write-up — inventory.stock self-time"],
        ["flamegraph leaf", "longest self-time · inventory.stock CPU"]
      ],
      packageNote:
        "Strong duration telemetry; Watchdog/Incident absent. Bits: /dd-bits-slowdown-review.html (e3 2026-08-11)",
      mtl: {
        metrics:
          "p95:trace.flask.request ↑ (~9–22 s) on inventory; host CPU user% ~52–57% during fault (DESKTOP-MBPAQK1)",
        traces:
          "status:ok · HTTP 200 · inventory.stock self-time avg~11.8s / p95~17.6s · callers wait · sample 6a7aabea…",
        logs: "inventory.stock.ok · http_status:200 · 0 KeyError (contrast ERROR run)"
      },
      journey: [
        {
          key: "agent",
          title: "Agent",
          m: "host + container tags ready",
          a: "ddtrace → Agent :8126",
          l: "optional shippers",
          teach: "Agent Collect: two source families in parallel — host/container probes ∥ app (ddtrace, DogStatsD, logs). Intake only; Detect is later."
        },
        {
          key: "tagging",
          title: "Tagging",
          m: "env:rca-lab-e3 · service:*",
          a: "same tags on spans",
          l: "same join keys",
          teach: "Unified Service Tags: service / env / version / host. Observed SLOWDOWN uses env:rca-lab-e3 + version:slowdown-…. Tags join Metrics ∥ APM ∥ Logs."
        },
        {
          key: "service_map",
          title: "Service Map",
          m: "catalog names appear",
          a: "peers FE→product→inventory",
          l: "host/container context",
          teach: "Service Map = APM-derived peers (who calls whom). Not leaf localization — that is longest duration span later."
        },
        {
          key: "stores",
          title: "M ∥ T ∥ L",
          m: "latency series write",
          a: "spans write continuously",
          l: "lines if enabled",
          teach: "One tagged stream writes into three Datadog products: Metrics, APM, and Logs."
        },
        {
          key: "intake",
          title: "Always-on fabric",
          m: "p95 series keep updating",
          a: "map edges stay warm",
          l: "index retention",
          teach: "Pre-Detect fabric: latency series + spans keep writing before any latency Door fires. Not Detect itself."
        },
        {
          key: "monitors_watchdog",
          title: "Monitors · Watchdog",
          m: "p95 → ~11 s (no Alert)",
          a: "200 · ~9s leaf (no 5xx)",
          l: "optional",
          teach: "05 Detect empty: error Door A OK · latency Door A absent · Watchdog 0. Loud Write ≠ foghorn. Lab opened APM to Localize — Timeline §2."
        },
        {
          key: "triage",
          title: "Alert triage",
          m: "many hot latency series",
          a: "many ok slow spans",
          l: "optional noise",
          teach: "No Alert to triage — operator still locks env/version/time from known fault window (or optional Bits seed)."
        },
        {
          key: "related",
          title: "Related scope",
          m: "env:rca-lab-e3 · 04:58–05:10Z",
          a: "status:ok @duration:>5s",
          l: "host filter",
          teach: "Lock Observed fault window 04:58:07Z–05:10:34Z (not baseline ~04:56Z). Filter ok slow spans — not status:error."
        },
        {
          key: "flamegraph",
          title: "Flamegraph leaf",
          m: "latency explorer",
          a: "flamegraph longest leaf",
          l: "optional corroboration",
          teach: "Read the longest inventory span — HTTP stays 200; there is no status:error."
        },
        {
          key: "tag_join",
          title: "Tag join",
          m: "same tags on series",
          a: "same tags on spans",
          l: "same tags on logs",
          teach: "Pivot Metrics ∥ APM ∥ Logs with the same service/env/host tags."
        },
        {
          key: "insights",
          title: "Insights · Incident",
          m: "no auto Incident",
          a: "Bits optional · no Watchdog RC",
          l: "ok corroboration",
          teach: "Bits packages longest-leaf self-time; Watchdog/Incident packaging was absent. Detect ≠ Bits ≠ Incident."
        }
      ],
      thesisDetect:
        "Observed: stage <strong>05 Detect empty</strong> (error Door A <code>310925690</code> OK · latency Door A <em>absent</em> · Watchdog 0 · Incident 0) while stage <strong>03 Write</strong> had p95 ~9–22s. Leaf via operator APM open — Write ≠ Detect ≠ Localize. Optional next: define latency Door A. Detect ≠ Bits ≠ Incident.",
      thesisLab:
        "Fault: <code>break_inventory_slow_code.sh</code> → inventory <strong>200 · ~9–22s</strong> (ledger scan). Isolate: <code>env:rca-lab-e3</code> · <code>version:slowdown-20260811T045553Z</code>. Read longest <em>self-time</em> leaf (<code>inventory.stock</code>), not status:error. Detail: Timeline §2."
    }
  };

  var STORAGE_KEY = "urca.dd.detect.cat";

  function byId(id) {
    for (var i = 0; i < CATS.length; i++) if (CATS[i].id === id) return CATS[i];
    return CATS[0];
  }

  function fromQuery() {
    try {
      var q = new URLSearchParams(location.search || "");
      var c = q.get("cat");
      if (c) return byId(String(c).toLowerCase());
    } catch (e) {}
    return null;
  }

  function fromPath() {
    var p = (location.pathname || "").toLowerCase();
    if (p.indexOf("slowdown") >= 0) return byId("slowdown");
    if (p.indexOf("dd-lab-timeline-error") >= 0) return byId("error");
    return null;
  }

  function fromStorage() {
    try {
      var s = localStorage.getItem(STORAGE_KEY);
      if (s) return byId(s);
    } catch (e) {}
    return null;
  }

  function current() {
    return fromQuery() || fromPath() || fromStorage() || CATS[0];
  }

  function persist(cat) {
    try {
      localStorage.setItem(STORAGE_KEY, cat.id);
    } catch (e) {}
  }

  function withCat(url, cat) {
    var u = url;
    u = u.replace(/([?&])cat=[^&]*/g, "$1").replace(/[?&]$/, "").replace(/\?&/, "?");
    if (!u.includes("?")) return u + "?cat=" + encodeURIComponent(cat.id);
    return u + "&cat=" + encodeURIComponent(cat.id);
  }

  function statusLabel(s) {
    if (s === "observed") return "Observed";
    if (s === "planned") return "Planned lab";
    return s;
  }

  function labScenario() {
    var cat = current();
    return LAB[cat.id] || LAB.error;
  }

  function isThesisPage(path) {
    path = (path || location.pathname || "").toLowerCase();
    return path.indexOf("datadog-production-pipeline") >= 0;
  }

  function stripCatFromLocation() {
    try {
      var u = new URL(location.href);
      if (!u.searchParams.has("cat")) return;
      u.searchParams.delete("cat");
      var q = u.searchParams.toString();
      history.replaceState(null, "", u.pathname + (q ? "?" + q : "") + u.hash);
    } catch (e) {}
  }

  function mountSwitcher(opts) {
    opts = opts || {};
    if (document.getElementById("urca-dd-cat-bar")) return;
    var cat = current();
    persist(cat);
    var thesis = isThesisPage();
    if (thesis) stripCatFromLocation();

    var bar = document.createElement("div");
    bar.id = "urca-dd-cat-bar";
    bar.setAttribute("role", "navigation");
    bar.setAttribute("aria-label", "Datadog teaching");
    if (thesis) bar.classList.add("thesis-neutral");

    var rowCat = document.createElement("div");
    rowCat.className = "urca-teach-row cat";
    var kCat = document.createElement("span");
    kCat.className = "urca-k";
    kCat.textContent = "Category";
    rowCat.appendChild(kCat);

    var labEl = document.createElement("label");
    labEl.htmlFor = "urca-dd-cat-select";
    labEl.textContent = "Detect category";
    rowCat.appendChild(labEl);

    var sel = document.createElement("select");
    sel.id = "urca-dd-cat-select";
    CATS.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c.id;
      o.textContent = c.title + (c.status === "planned" ? "  · planned" : "");
      if (c.id === cat.id) o.selected = true;
      sel.appendChild(o);
    });
    rowCat.appendChild(sel);
    if (!thesis) bar.appendChild(rowCat);

    var rowViews = document.createElement("div");
    rowViews.className = "urca-teach-row views";
    var kViews = document.createElement("span");
    kViews.className = "urca-k";
    kViews.textContent = "Views";
    rowViews.appendChild(kViews);

    var slots = document.createElement("div");
    slots.className = "slots";
    function addSlot(parent, href, label, kind, interp) {
      var a = document.createElement("a");
      a.href = kind === "pipeline" ? href : withCat(href, cat);
      a.textContent = label;
      a.dataset.kind = kind;
      if (interp) a.classList.add("interp");
      var path = (location.pathname || "").replace(/\/+$/, "") || "/";
      var target = href.replace(/\/+$/, "");
      if (path === target || path.endsWith(target)) a.classList.add("here");
      parent.appendChild(a);
    }
    addSlot(slots, TEACH.hub, "Hub", "hub", false);
    addSlot(slots, TEACH.pipeline, "Thesis", "pipeline", false);
    addSlot(slots, TEACH.mechanisms, "Breakdown", "mechanisms", false);
    addSlot(slots, TEACH.e2e, "Three-rail", "e2e", false);
    addSlot(slots, cat.lab, "Timeline", "lab", false);
    rowViews.appendChild(slots);

    if (!thesis && (cat.mtlDoc || cat.bitsDoc)) {
      var spacer = document.createElement("span");
      spacer.className = "urca-teach-spacer";
      spacer.setAttribute("aria-hidden", "true");
      rowViews.appendChild(spacer);

      var kInterp = document.createElement("span");
      kInterp.className = "urca-k interp";
      kInterp.textContent = "Interpret";
      rowViews.appendChild(kInterp);

      var interpSlots = document.createElement("div");
      interpSlots.className = "slots";
      if (cat.mtlDoc) addSlot(interpSlots, cat.mtlDoc, "MTL workbook", "mtl", true);
      if (cat.bitsDoc) addSlot(interpSlots, cat.bitsDoc, "Bits", "bits", true);
      rowViews.appendChild(interpSlots);
    }
    bar.appendChild(rowViews);

    sel.addEventListener("change", function () {
      var next = byId(sel.value);
      persist(next);
      var path = (location.pathname || "").toLowerCase();
      if (/datadog-subsystem-mechanisms|dd-e2e-metrics-traces/.test(path)) {
        location.href = withCat(location.pathname, next);
        return;
      }
      location.href = withCat(TEACH.hub, next);
    });

    function place() {
      var body = document.body;
      if (!body || document.getElementById("urca-dd-cat-bar")) return;
      var nav = document.getElementById("urca-doc-nav");
      if (nav && nav.parentNode) nav.parentNode.insertBefore(bar, nav.nextSibling);
      else body.insertBefore(bar, body.firstChild);

      if (!thesis && opts.banner !== false && !document.getElementById("urca-dd-cat-banner")) {
        var ban = document.createElement("div");
        ban.id = "urca-dd-cat-banner";
        ban.innerHTML =
          "<b>" +
          cat.name +
          "</b> — " +
          cat.blurb +
          " · Detect: <code>" +
          cat.detect +
          "</code>" +
          (cat.evidence ? " · Evidence <code>" + cat.evidence + "</code>" : "") +
          " · " +
          statusLabel(cat.status);
        bar.parentNode.insertBefore(ban, bar.nextSibling);
      }
    }
    if (document.body) place();
    else document.addEventListener("DOMContentLoaded", place);
  }

  global.URCA_DD_CATS = {
    list: CATS,
    teach: TEACH,
    lab: LAB,
    pipeline: PIPELINE,
    current: current,
    byId: byId,
    withCat: withCat,
    persist: persist,
    mountSwitcher: mountSwitcher,
    statusLabel: statusLabel,
    labScenario: labScenario,
    renderPipelineGuide: renderPipelineGuide,
    fillPipelineGuides: fillPipelineGuides
  };

  var path = (location.pathname || "").toLowerCase();
  var auto =
    path.indexOf("datadog-subsystem-mechanisms") >= 0 ||
    path.indexOf("datadog-production-pipeline") >= 0 ||
    path.indexOf("dd-e2e-metrics-traces") >= 0 ||
    path.indexOf("dd-error-mtl") >= 0 ||
    path.indexOf("dd-slowdown-mtl") >= 0 ||
    path.indexOf("dd-lab-timeline") >= 0 ||
    path.indexOf("dd-detect-category") >= 0 ||
    path.indexOf("dd-bits-") >= 0 ||
    path.indexOf("dd-behind-the-scenes") >= 0 ||
    path.indexOf("datadog-lab-evidence-mtl") >= 0;
  if (auto) {
    document.addEventListener("DOMContentLoaded", function () {
      setTimeout(function () {
        mountSwitcher({ banner: true });
        fillPipelineGuides();
      }, 0);
    });
  }
})(typeof window !== "undefined" ? window : this);
