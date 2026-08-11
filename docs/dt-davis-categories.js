/**
 * Dynatrace Davis event-category registry + switcher for docs hub (:8765).
 *
 * Shared teaching pages (Thesis / Breakdown / Dual-track) stay one copy each;
 * ?cat=<id> frames Detect signal. Timeline "Observed" pages are per-category.
 *
 * Include after or instead of plain links:
 *   <script src="/dt-davis-categories.js" defer></script>
 * Optional: data-urca-cat-page="mechanisms|pipeline|e2e|lab|hub" on <html>
 * Sticky slots (order): Hub → Thesis → Breakdown → Dual-track → Timeline
 */
(function (global) {
  "use strict";

  var CATS = [
    {
      id: "error",
      name: "ERROR",
      title: "ERROR · Failure rate",
      blurb: "Error-rate / failure increase. Detect watches failure rate; lab leaf was KeyError → 5xx.",
      detect: "error_rate · SERVICE_ERROR_RATE_INCREASED",
      status: "observed",
      problem: "P-260817",
      lab: "/dt-lab-timeline-code-level.html",
      signal: "error_rate"
    },
    {
      id: "slowdown",
      name: "SLOWDOWN",
      title: "SLOWDOWN · Latency / response time",
      blurb: "Response-time degradation. Detect watches duration; lab leaf was ledger-scan CPU → slow 200.",
      detect: "response time · SERVICE_SLOWDOWN",
      status: "observed",
      problem: "P-260820",
      lab: "/dt-lab-timeline-slowdown.html",
      signal: "response_time"
    },
    {
      id: "monitoring_unavailable",
      name: "MONITORING_UNAVAILABLE",
      title: "MONITORING_UNAVAILABLE · Visibility dark",
      blurb: "OneAgent / ingest dark — meta outage of visibility, not app fault. Inventory HTTP stayed 200.",
      detect: "agent / ingest availability",
      status: "observed",
      problem: "P-260826",
      lab: "/dt-cat-monitoring-unavailable-lab.html",
      signal: "monitoring",
      agentTask: "/docs/agent-tasks/dt-monitoring-unavailable.md"
    },
    {
      id: "availability",
      name: "AVAILABILITY",
      title: "AVAILABILITY · Host / process down",
      blurb: "Hard outage — inventory container stopped; callers fail. Severity AVAILABILITY on PG.",
      detect: "availability / process / host down",
      status: "observed",
      problem: "P-260831",
      lab: "/dt-cat-availability-lab.html",
      signal: "availability",
      agentTask: "/docs/agent-tasks/dt-availability.md"
    },
    {
      id: "resource_contention",
      name: "RESOURCE_CONTENTION",
      title: "RESOURCE_CONTENTION · CPU / memory",
      blurb: "Saturation on host/process. Agent task ready to run (background CPU burn).",
      detect: "CPU / memory / resource saturation",
      status: "agent_task",
      problem: null,
      lab: "/dt-cat-resource-contention-lab.html",
      signal: "resource",
      agentTask: "/docs/agent-tasks/dt-resource-contention.md"
    }
  ];

  var TEACH = {
    mechanisms: "/eleven-subsystem-mechanisms.html",
    pipeline: "/dynatrace-production-pipeline.html",
    e2e: "/dt-e2e-smartscape-grail.html",
    hub: "/dt-davis-category-hub.html"
  };

  /**
   * Teaching canvas payloads — Detect/Maintain/Package must match the selected category
   * (no ERROR 5xx rows when cat=slowdown).
   */
  var LAB = {
    error: {
      id: "error",
      problem: "P-26084",
      problemNote: "teaching dual-lab UTC (also see Observed P-260817)",
      rcEntity: "SERVICE-INV",
      rcLabel: "rootCauseEntity = inventory (SERVICE-INV)",
      clocks: ["05:50", "05:54→06:04", "06:04", "after clear"],
      faultWindow: "05:54–06:04",
      problemAt: "06:04",
      seenFault: "06:04",
      maintainTitles: [
        "① Healthy — same Smartscape as Topology · Grail has OK rows",
        "② Fault on — map unchanged (INV hot) · Grail fills with INV 5xx",
        "③ Davis walks THIS map + pulls Grail → Problem P-26084",
        "④ Fault cleared — same topology · recovery rows in Grail"
      ],
      grailRows: [
        { e: "SERVICE-INV", ts: "05:50", w: "/stock 200", tone: "ok", from: 0 },
        { e: "SERVICE-INV", ts: "05:54", w: "/stock 500", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "05:59", w: "error_rate 0.92", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "05:59", w: "span 500 (cascade)", tone: "muted", from: 1 },
        { e: "SERVICE-INV", ts: "06:04", w: "/stock 500 (still failing)", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "06:10", w: "/stock 200 (cleared)", tone: "ok", from: 3 }
      ],
      detectSignal: "error_rate",
      detectThr: 0.3,
      detectMax: 1.0,
      detectTitles: [
        "① Watch — each service’s error_rate series watched vs its threshold",
        "② Breach — INV crosses threshold → first Event object",
        "③ Cascade — API then FE each open their own Event (not one fused alert)",
        "④ Storm — raw Event list; still no Problem card"
      ],
      detectSeries: [
        { id: "SERVICE-INV", signal: "error_rate", y: 110, healthy: 0.02, fault: 0.92, order: 0 },
        { id: "SERVICE-API", signal: "error_rate", y: 170, healthy: 0.01, fault: 0.78, order: 1 },
        { id: "SERVICE-FE", signal: "error_rate", y: 230, healthy: 0.01, fault: 0.71, order: 2 }
      ],
      events: [
        { type: "SERVICE_ERROR_RATE_INCREASED", e: "SERVICE-INV", ts: "05:58", v: "0.92", from: 1 },
        { type: "SERVICE_ERROR_RATE_INCREASED", e: "SERVICE-API", ts: "05:59", v: "0.78", from: 2 },
        { type: "SERVICE_ERROR_RATE_INCREASED", e: "SERVICE-FE", ts: "06:00", v: "0.71", from: 3 },
        { type: "PROCESS_CPU_HIGH", e: "SERVICE-BATCH", ts: "06:00", v: "0.81", from: 3, noise: true }
      ],
      packageLines: [
        ["rootCauseEntity", "SERVICE-INV"],
        ["impact", "frontend checkout"],
        ["events merged", "3 nearby"]
      ],
      identifyRows: ["failed_call↑ INV", "latency FE→API", "CPU HOST-B", "BATCH noise"],
      clearMetric: "error_rate",
      clockIntro:
        "Clock = Observed dual-lab UTC (<code>P-26084</code>: fault ≈05:54 → Problem ≈06:04). ERROR path: 5xx / error_rate.",
      normalize: {
        fieldsLine: "fields: status · raw_ids · modality",
        outA: "OUT A · status=500",
        outAHint: "→ STEP 2 Detect",
        step2Title: "FAILURE LABEL",
        step2Sub: "Detect path · not used by LUT",
        step2In: "IN:  status=500",
        step2Rule: "RULE: 5xx → true",
        step2Out: "OUT: failed_call=true",
        step2Note: "also: PAY→false · BATCH→unset",
        detailFork:
          "One envelope, two outputs: <code>status=500</code> → STEP 2; <code>raw_ids=[inventory,c8e91a]</code> → STEP 3.",
        detailStep2:
          "<code>failed_call=true</code> for failure-rate Detect later. Not an input to STEP 3 / LUT."
      }
    },
    slowdown: {
      id: "slowdown",
      problem: "P-260820",
      problemNote: "Observed SLOWDOWN lab",
      rcEntity: null,
      rcLabel: "rootCauseEntity = null (Events same start bucket)",
      clocks: ["14:55", "15:05→15:10", "15:10", "after heal"],
      faultWindow: "15:05–15:10+",
      problemAt: "15:10",
      seenFault: "15:10",
      maintainTitles: [
        "① Healthy — same Smartscape · Grail has fast 200s",
        "② Slowdown on — map unchanged (INV hot) · Grail fills with slow 200s / RT",
        "③ Davis packages Problem P-260820 (entity RC unset)",
        "④ Healed — same topology · fast 200s again"
      ],
      grailRows: [
        { e: "SERVICE-INV", ts: "14:55", w: "/inventory 200 · ~50ms", tone: "ok", from: 0 },
        { e: "SERVICE-INV", ts: "15:05", w: "/inventory 200 · ~9s", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "15:05", w: "response_time ~9s (leaf)", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "15:06", w: "RT cascade (waits INV)", tone: "muted", from: 1 },
        { e: "SERVICE-FE", ts: "15:07", w: "RT cascade (waits API)", tone: "muted", from: 1 },
        { e: "SERVICE-INV", ts: "15:20", w: "/inventory 200 · ~50ms", tone: "ok", from: 3 }
      ],
      detectSignal: "resp_time_s",
      detectThr: 2.0,
      detectMax: 10.0,
      detectTitles: [
        "① Watch — each service’s response_time vs fixed threshold (lab 2s)",
        "② Breach — INV crosses first (leaf slows before callers notice)",
        "③ Cascade — API then FE RT rise after wait; each opens own Event",
        "④ Storm — Event *start* times still same minute bucket (Observed)"
      ],
      detectSeries: [
        { id: "SERVICE-INV", signal: "resp_s", y: 110, healthy: 0.05, fault: 9.0, order: 0 },
        { id: "SERVICE-API", signal: "resp_s", y: 170, healthy: 0.08, fault: 9.1, order: 1 },
        { id: "SERVICE-FE", signal: "resp_s", y: 230, healthy: 0.1, fault: 9.2, order: 2 }
      ],
      events: [
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-INV", ts: "15:05", v: "~9s", from: 1, role: "topo leaf" },
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-API", ts: "15:05", v: "~9s", from: 2, role: "topo caller" },
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-FE", ts: "15:05", v: "~9s", from: 3, role: "topo edge" },
        { type: "PROCESS_CPU_HIGH", e: "SERVICE-BATCH", ts: "15:06", v: "0.81", from: 3, noise: true, role: "noise" }
      ],
      packageLines: [
        ["rootCauseEntity", "null"],
        ["impact", "frontend · ~159 calls"],
        ["events", "3× SERVICE_SLOWDOWN"]
      ],
      identifyRows: ["long INV span ~9s", "RT FE→product→INV", "CPU HOST-B", "BATCH noise"],
      clearMetric: "response_time",
      clockIntro:
        "Clock = Observed SLOWDOWN <code>P-260820</code>. <b>Grail</b> cascade is staggered (INV ~15:05 → API ~15:06 → FE ~15:07). <b>Detect Event starts</b> still landed in the <b>same minute bucket</b> ≈15:05 → packaged <code>rootCauseEntity=null</code>. Soft latency ≠ hard 5xx leaf timing.",
      normalize: {
        fieldsLine: "fields: status · duration · raw_ids · modality",
        outA: "OUT A · status=200 · ~9s",
        outAHint: "→ STEP 2 Detect",
        step2Title: "LATENCY LABEL",
        step2Sub: "Detect path · not used by LUT",
        step2In: "IN:  status=200 · duration≈9s",
        step2Rule: "RULE: slow OK → RT series",
        step2Out: "OUT: slow_call=true",
        step2Note: "failed_call=false (not a 5xx path)",
        detailFork:
          "One envelope, two outputs: <code>status=200 · duration≈9s</code> → STEP 2; <code>raw_ids=[inventory,c8e91a]</code> → STEP 3.",
        detailStep2:
          "<code>slow_call=true</code> feeds response-time Detect later (SLOWDOWN). Not an input to STEP 3 / LUT. No <code>failed_call</code> from 5xx."
      }
    },
    monitoring_unavailable: {
      id: "monitoring_unavailable",
      problem: "P-260826",
      problemNote: "Observed lab UTC (CUSTOM_ALERT surface; organic platform MONITORING_UNAVAILABLE not auto-fired)",
      rcEntity: "PROCESS_GROUP inventory",
      rcLabel: "seed tip = inventory PG visibility dark (HTTP still 200)",
      clocks: ["06:20", "06:21→06:36", "06:42", "06:43"],
      faultWindow: "06:20–06:43",
      problemAt: "06:42",
      seenFault: "06:42",
      maintainTitles: [
        "① Healthy — OTLP + OneAgent Python on INV · Grail receiving",
        "② Visibility dark — OTEL off · PG MONITORING_OFF · OA stopped · HTTP 200",
        "③ Davis packages Problem P-260826 (CUSTOM_ALERT on inventory PG)",
        "④ Healed — OA + MONITORING_ON + OTEL back · Grail fills again"
      ],
      grailRows: [
        { e: "SERVICE-INV", ts: "06:15", w: "spans/metrics OK", tone: "ok", from: 0 },
        { e: "SERVICE-INV", ts: "06:22", w: "OTLP+OA deep dark", tone: "seed", from: 1 },
        { e: "HOST-B", ts: "06:31", w: "oneagent stopped", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "06:31", w: "calls INV · HTTP 200", tone: "muted", from: 1 },
        { e: "SERVICE-INV", ts: "06:42", w: "CUSTOM_ALERT → P-260826", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "06:43", w: "telemetry restored", tone: "ok", from: 3 }
      ],
      detectSignal: "agent_up",
      detectThr: 0.5,
      detectMax: 1.0,
      detectTitles: [
        "① Watch — agent / ingest heartbeats (platform MONITORING_UNAVAILABLE is majority-agent)",
        "② Breach — inventory PG goes dark while checkout HTTP stays 200",
        "③ Surface — CUSTOM_ALERT ingest (organic OSI_/MONITORING_* not in window)",
        "④ Storm — raw Event; then Problem card"
      ],
      detectSeries: [
        { id: "HOST-B", signal: "agent_up", y: 110, healthy: 1.0, fault: 0.0, order: 0 },
        { id: "SERVICE-INV", signal: "ingest", y: 170, healthy: 1.0, fault: 0.0, order: 1 },
        { id: "SERVICE-API", signal: "ingest", y: 230, healthy: 1.0, fault: 0.85, order: 2 }
      ],
      events: [
        { type: "CUSTOM_ALERT", e: "SERVICE-INV", ts: "06:42", v: "dark", from: 1 },
        { type: "MONITORING_UNAVAILABLE", e: "HOST-B", ts: "06:31", v: "agent", from: 1 },
        { type: "CONNECTION_FAILED", e: "SERVICE-API", ts: "06:35", v: "partial", from: 3 }
      ],
      packageLines: [
        ["category", "MONITORING_UNAVAILABLE"],
        ["problem", "P-260826"],
        ["seed tip", "inventory PG"],
        ["severity", "CUSTOM_ALERT"]
      ],
      identifyRows: ["ingest gap INV", "OA deep off", "HTTP 200 OK", "noise"],
      clearMetric: "agent_up",
      clockIntro:
        "Clock = Observed MONITORING_UNAVAILABLE lab UTC (<code>P-260826</code>: dark ≈06:20 → Problem 06:42). Process up · telemetry dark — not 5xx.",
      normalize: {
        fieldsLine: "fields: agent_up · ingest · raw_ids · modality",
        outA: "OUT A · agent_up=0",
        outAHint: "→ STEP 2 Detect",
        step2Title: "INGEST LABEL",
        step2Sub: "Detect path · not used by LUT",
        step2In: "IN:  agent heartbeat miss",
        step2Rule: "RULE: dark → unavailable",
        step2Out: "OUT: monitoring_gap=true",
        step2Note: "HTTP may still be 200 on callers",
        detailFork:
          "One envelope, two outputs: <code>agent_up=0</code> → STEP 2; <code>raw_ids</code> → STEP 3. Not an app 5xx path.",
        detailStep2:
          "<code>monitoring_gap=true</code> for agent/ingest Detect. Not an input to STEP 3 / LUT."
      }
    },
    availability: {
      id: "availability",
      problem: "P-260831",
      problemNote: "Observed lab UTC (AVAILABILITY_EVENT surface; organic cascade was PERFORMANCE on callers)",
      rcEntity: "PROCESS_GROUP inventory",
      rcLabel: "seed tip = inventory process/container down (hard outage)",
      clocks: ["07:00", "07:00→07:11", "07:10", "07:11"],
      faultWindow: "07:00–07:11",
      problemAt: "07:10",
      seenFault: "07:00",
      maintainTitles: [
        "① Healthy — INV container up · checkout 200",
        "② INV stopped — map marks unavailable · callers 000/500",
        "③ Davis packages Problem P-260831 (AVAILABILITY on inventory PG)",
        "④ Process back — heal · checkout 200"
      ],
      grailRows: [
        { e: "SERVICE-INV", ts: "06:55", w: "process UP", tone: "ok", from: 0 },
        { e: "SERVICE-INV", ts: "07:00", w: "container STOPPED", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "07:00", w: "connection refused", tone: "seed", from: 1 },
        { e: "SERVICE-FE", ts: "07:00", w: "upstream fail / 500", tone: "muted", from: 1 },
        { e: "SERVICE-INV", ts: "07:10", w: "AVAILABILITY_EVENT → P-260831", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "07:11", w: "process UP · healed", tone: "ok", from: 3 }
      ],
      detectSignal: "availability",
      detectThr: 0.5,
      detectMax: 1.0,
      detectTitles: [
        "① Watch — process / host availability",
        "② Breach — INV container stop (graceful stop ≠ organic PGI_UNAVAILABLE in-window)",
        "③ Cascade — FE/product PERFORMANCE P-260829 · surface AVAILABILITY_EVENT",
        "④ Storm — raw Event; then Problem card P-260831"
      ],
      detectSeries: [
        { id: "SERVICE-INV", signal: "available", y: 110, healthy: 1.0, fault: 0.0, order: 0 },
        { id: "SERVICE-API", signal: "available", y: 170, healthy: 1.0, fault: 0.35, order: 1 },
        { id: "SERVICE-FE", signal: "available", y: 230, healthy: 1.0, fault: 0.4, order: 2 }
      ],
      events: [
        { type: "AVAILABILITY_EVENT", e: "SERVICE-INV", ts: "07:10", v: "down", from: 1 },
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-API", ts: "07:02", v: "cascade", from: 2 },
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-FE", ts: "07:02", v: "cascade", from: 3 }
      ],
      packageLines: [
        ["category", "AVAILABILITY"],
        ["problem", "P-260831"],
        ["seed tip", "inventory PG"],
        ["severity", "AVAILABILITY"]
      ],
      identifyRows: ["process down INV", "conn refused API", "FE 500s", "noise"],
      clearMetric: "availability",
      clockIntro:
        "Clock = Observed AVAILABILITY lab UTC (<code>P-260831</code>: stop 07:00 → Problem 07:10). Hard down — not soft error_rate or latency-only.",
      normalize: {
        fieldsLine: "fields: available · raw_ids · modality",
        outA: "OUT A · available=false",
        outAHint: "→ STEP 2 Detect",
        step2Title: "AVAILABILITY LABEL",
        step2Sub: "Detect path · not used by LUT",
        step2In: "IN:  process/host down",
        step2Rule: "RULE: hard down → true",
        step2Out: "OUT: unavailable=true",
        step2Note: "callers → connection refused",
        detailFork:
          "One envelope, two outputs: <code>available=false</code> → STEP 2; <code>raw_ids</code> → STEP 3.",
        detailStep2:
          "<code>unavailable=true</code> for availability Detect. Not an input to STEP 3 / LUT."
      }
    },
    resource_contention: {
      id: "resource_contention",
      problem: "(planned)",
      problemNote: "illustrative — lab not run",
      rcEntity: "HOST-B",
      rcLabel: "seed tip = HOST-B CPU/mem (illustrative)",
      clocks: ["t0", "saturate", "Problem", "eased"],
      faultWindow: "CPU/mem high",
      problemAt: "Problem",
      seenFault: "hot",
      maintainTitles: [
        "① Healthy — HOST-B resources normal",
        "② INV host CPU/mem saturation — Grail resource series fill",
        "③ RESOURCE_CONTENTION Problem (illustrative)",
        "④ Pressure eased"
      ],
      grailRows: [
        { e: "HOST-B", ts: "t0", w: "cpu 0.25", tone: "ok", from: 0 },
        { e: "HOST-B", ts: "t1", w: "cpu 0.97", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "t1", w: "latency↑ under pressure", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "t1", w: "slow calls to INV", tone: "muted", from: 1 },
        { e: "HOST-B", ts: "t2", w: "mem pressure", tone: "seed", from: 1 },
        { e: "HOST-B", ts: "t3", w: "cpu 0.30", tone: "ok", from: 3 }
      ],
      detectSignal: "cpu",
      detectThr: 0.85,
      detectMax: 1.0,
      detectTitles: [
        "① Watch — host/process CPU & memory",
        "② Breach — HOST-B resource Event",
        "③ Related — INV latency may rise",
        "④ Storm — raw Events"
      ],
      detectSeries: [
        { id: "HOST-B", signal: "cpu", y: 110, healthy: 0.25, fault: 0.97, order: 0 },
        { id: "SERVICE-INV", signal: "cpu", y: 170, healthy: 0.2, fault: 0.9, order: 1 },
        { id: "SERVICE-API", signal: "cpu", y: 230, healthy: 0.15, fault: 0.35, order: 2 }
      ],
      events: [
        { type: "RESOURCE_CONTENTION", e: "HOST-B", ts: "t1", v: "cpu 0.97", from: 1 },
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-INV", ts: "t1", v: "latency", from: 2 },
        { type: "RESOURCE_CONTENTION", e: "HOST-B", ts: "t2", v: "mem", from: 3 }
      ],
      packageLines: [
        ["category", "RESOURCE_CONTENTION"],
        ["seed tip", "HOST-B"],
        ["note", "lab planned"]
      ],
      identifyRows: ["HOST-B cpu", "INV latency", "runsOn INV→HOST-B", "noise"],
      clearMetric: "cpu",
      clockIntro:
        "Illustrative RESOURCE_CONTENTION path (lab planned). Detect tip = CPU/mem; Smartscape runsOn matters.",
      normalize: {
        fieldsLine: "fields: cpu · mem · raw_ids · modality",
        outA: "OUT A · cpu=0.97",
        outAHint: "→ STEP 2 Detect",
        step2Title: "RESOURCE LABEL",
        step2Sub: "Detect path · not used by LUT",
        step2In: "IN:  host/process cpu",
        step2Rule: "RULE: cpu≥thr → true",
        step2Out: "OUT: resource_hot=true",
        step2Note: "HTTP may stay 200 (unlike SLOWDOWN leaf)",
        detailFork:
          "One envelope, two outputs: <code>cpu=0.97</code> → STEP 2; <code>raw_ids</code> → STEP 3.",
        detailStep2:
          "<code>resource_hot=true</code> for CPU/mem Detect. Not an input to STEP 3 / LUT."
      }
    }
  };

  function labScenario() {
    var cat = current();
    return LAB[cat.id] || LAB.error;
  }

  var STORAGE_KEY = "urca.dt.davis.cat";

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
    if (p.indexOf("code-level") >= 0 || p.indexOf("error") >= 0 && p.indexOf("timeline") >= 0)
      return byId("error");
    if (p.indexOf("monitoring-unavailable") >= 0) return byId("monitoring_unavailable");
    if (p.indexOf("availability") >= 0 && p.indexOf("lab") >= 0) return byId("availability");
    if (p.indexOf("resource-contention") >= 0) return byId("resource_contention");
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
    var join = url.indexOf("?") >= 0 ? "&" : "?";
    // strip existing cat=
    u = u.replace(/([?&])cat=[^&]*/g, "$1").replace(/[?&]$/, "").replace(/\?&/, "?");
    if (!u.includes("?")) return u + "?cat=" + encodeURIComponent(cat.id);
    return u + "&cat=" + encodeURIComponent(cat.id);
  }

  function statusLabel(s) {
    if (s === "observed") return "Observed";
    if (s === "agent_task") return "Agent task";
    if (s === "planned") return "Planned lab";
    return s;
  }

  /** Inject sticky teaching chrome under #urca-doc-nav (or at top). */
  function mountSwitcher(opts) {
    opts = opts || {};
    if (document.getElementById("urca-dt-cat-bar")) return;
    var cat = current();
    persist(cat);

    var style = document.createElement("style");
    style.textContent = [
      "#urca-dt-cat-bar{position:sticky;top:0;z-index:9998;display:flex;flex-direction:column;gap:8px;",
      "padding:10px 14px 12px;background:rgba(12,16,22,.98);border-bottom:1px solid #2a3441;",
      "font-family:system-ui,-apple-system,sans-serif;font-size:14px;color:#c5d0da;}",
      "#urca-doc-nav + #urca-dt-cat-bar,#urca-doc-nav ~ #urca-dt-cat-bar{top:42px;}",
      "#urca-dt-cat-bar .urca-teach-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;}",
      "#urca-dt-cat-bar .urca-teach-row.views{padding-top:8px;border-top:1px solid #2a3441;}",
      "#urca-dt-cat-bar .urca-k{font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;",
      "color:#8a96a4;min-width:4.5rem;}",
      "#urca-dt-cat-bar label{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);}",
      "#urca-dt-cat-bar select{font:inherit;font-size:14px;padding:6px 10px;border-radius:4px;border:1px solid #2a3441;",
      "background:#1c2430;color:#e8eef4;min-width:18rem;max-width:min(28rem,90vw);}",
      "#urca-dt-cat-bar .slots{display:flex;flex-wrap:wrap;gap:6px;}",
      "#urca-dt-cat-bar .slots a{font-size:13px;padding:5px 10px;border-radius:4px;border:1px solid #2a3441;",
      "background:#171d25;color:#b8c4d0;text-decoration:none;}",
      "#urca-dt-cat-bar .slots a:hover{border-color:#3d9a8b;color:#e8eef4;}",
      "#urca-dt-cat-bar .slots a.here{color:#7ec8b8;border-color:rgba(61,154,139,.55);background:rgba(61,154,139,.14);}",
      "#urca-dt-cat-bar .slots a.muted{opacity:.55;}",
      "#urca-dt-cat-banner{margin:0;padding:10px 14px;background:rgba(61,154,139,.1);border-bottom:1px solid #2a3441;",
      "font-family:system-ui,-apple-system,sans-serif;font-size:13px;color:#c5d0da;line-height:1.45;}",
      "#urca-dt-cat-banner b{color:#e8eef4;} #urca-dt-cat-banner code{font-family:ui-monospace,monospace;font-size:12px;",
      "background:#1c2430;padding:1px 5px;border-radius:3px;color:#9bc0ff;}"
    ].join("");
    document.head.appendChild(style);

    var bar = document.createElement("div");
    bar.id = "urca-dt-cat-bar";
    bar.setAttribute("role", "navigation");
    bar.setAttribute("aria-label", "Dynatrace teaching");

    var rowCat = document.createElement("div");
    rowCat.className = "urca-teach-row cat";
    var kCat = document.createElement("span");
    kCat.className = "urca-k";
    kCat.textContent = "Category";
    rowCat.appendChild(kCat);

    var labEl = document.createElement("label");
    labEl.htmlFor = "urca-dt-cat-select";
    labEl.textContent = "Davis category";
    rowCat.appendChild(labEl);

    var sel = document.createElement("select");
    sel.id = "urca-dt-cat-select";
    CATS.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c.id;
      o.textContent =
        c.title +
        (c.status === "planned" ? "  · planned" : c.status === "agent_task" ? "  · agent task" : "");
      if (c.id === cat.id) o.selected = true;
      o.dataset.status = c.status;
      sel.appendChild(o);
    });
    rowCat.appendChild(sel);
    bar.appendChild(rowCat);

    var rowViews = document.createElement("div");
    rowViews.className = "urca-teach-row views";
    var kViews = document.createElement("span");
    kViews.className = "urca-k";
    kViews.textContent = "Views";
    rowViews.appendChild(kViews);

    var slots = document.createElement("div");
    slots.className = "slots";
    function addSlot(href, label, kind) {
      var a = document.createElement("a");
      a.href = withCat(href, cat);
      a.textContent = label;
      a.dataset.kind = kind;
      var path = (location.pathname || "").replace(/\/+$/, "") || "/";
      var target = href.replace(/\/+$/, "");
      if (path === target || path.endsWith(target)) a.classList.add("here");
      if (kind === "lab" && cat.status === "planned") a.classList.add("muted");
      if (kind === "lab" && cat.status === "agent_task") a.title = "Agent task ready — not yet Observed";
      slots.appendChild(a);
    }
    addSlot(TEACH.hub, "Hub", "hub");
    addSlot(TEACH.pipeline, "Thesis", "pipeline");
    addSlot(TEACH.mechanisms, "Breakdown", "mechanisms");
    addSlot(TEACH.e2e, "Dual-track", "e2e");
    addSlot(
      cat.lab,
      cat.status === "observed"
        ? "Timeline"
        : cat.status === "agent_task"
          ? "Timeline (task)"
          : "Timeline (planned)",
      "lab"
    );
    rowViews.appendChild(slots);
    bar.appendChild(rowViews);

    sel.addEventListener("change", function () {
      var next = byId(sel.value);
      persist(next);
      var path = (location.pathname || "").toLowerCase();
      if (
        /eleven-subsystem-mechanisms|dynatrace-production-pipeline|dt-e2e-smartscape/.test(path)
      ) {
        location.href = withCat(location.pathname, next);
        return;
      }
      location.href = withCat(TEACH.hub, next);
    });

    function place() {
      var body = document.body;
      if (!body || document.getElementById("urca-dt-cat-bar")) return;
      var nav = document.getElementById("urca-doc-nav");
      if (nav && nav.parentNode) nav.parentNode.insertBefore(bar, nav.nextSibling);
      else body.insertBefore(bar, body.firstChild);

      if (opts.banner !== false && !document.getElementById("urca-dt-cat-banner")) {
        var ban = document.createElement("div");
        ban.id = "urca-dt-cat-banner";
        ban.innerHTML =
          "<b>" +
          cat.name +
          "</b> — " +
          cat.blurb +
          " · Detect: <code>" +
          cat.detect +
          "</code>" +
          (cat.problem ? " · Problem <code>" + cat.problem + "</code>" : "") +
          " · " +
          statusLabel(cat.status);
        bar.parentNode.insertBefore(ban, bar.nextSibling);
      }
    }
    if (document.body) place();
    else document.addEventListener("DOMContentLoaded", place);
  }

  global.URCA_DT_CATS = {
    list: CATS,
    teach: TEACH,
    lab: LAB,
    current: current,
    byId: byId,
    withCat: withCat,
    persist: persist,
    mountSwitcher: mountSwitcher,
    statusLabel: statusLabel,
    labScenario: labScenario
  };

  // Auto-mount on DT teaching + lab pages
  var path = (location.pathname || "").toLowerCase();
  var auto =
    path.indexOf("eleven-subsystem") >= 0 ||
    path.indexOf("dynatrace-production-pipeline") >= 0 ||
    path.indexOf("dt-e2e-smartscape") >= 0 ||
    path.indexOf("dt-lab-timeline") >= 0 ||
    path.indexOf("dt-cat-") >= 0 ||
    path.indexOf("dt-davis-category") >= 0;
  if (auto) {
    document.addEventListener("DOMContentLoaded", function () {
      // wait a tick so doc-nav can insert first
      setTimeout(function () {
        mountSwitcher({ banner: true });
      }, 0);
    });
  }
})(typeof window !== "undefined" ? window : this);
