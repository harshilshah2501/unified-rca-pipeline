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
      blurb: "OneAgent / ingest dark — meta outage of visibility, not app fault.",
      detect: "agent / ingest availability",
      status: "planned",
      problem: null,
      lab: "/dt-cat-monitoring-unavailable-lab.html",
      signal: "monitoring"
    },
    {
      id: "availability",
      name: "AVAILABILITY",
      title: "AVAILABILITY · Host / process down",
      blurb: "Hard outage, crash, process unavailable. Detect often from hard signals, not soft % thresholds.",
      detect: "availability / process / host down",
      status: "planned",
      problem: null,
      lab: "/dt-cat-availability-lab.html",
      signal: "availability"
    },
    {
      id: "resource_contention",
      name: "RESOURCE_CONTENTION",
      title: "RESOURCE_CONTENTION · CPU / memory",
      blurb: "Saturation on host/process. Smartscape runsOn walk matters more for seed tip.",
      detect: "CPU / memory / resource saturation",
      status: "planned",
      problem: null,
      lab: "/dt-cat-resource-contention-lab.html",
      signal: "resource"
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
        "Clock = Observed dual-lab UTC (<code>P-26084</code>: fault ≈05:54 → Problem ≈06:04). ERROR path: 5xx / error_rate."
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
        { e: "SERVICE-INV", ts: "15:05", w: "response_time ~9s", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "15:05", w: "RT cascade (waits INV)", tone: "muted", from: 1 },
        { e: "SERVICE-FE", ts: "15:05", w: "RT cascade (waits INV)", tone: "muted", from: 1 },
        { e: "SERVICE-INV", ts: "15:20", w: "/inventory 200 · ~50ms", tone: "ok", from: 3 }
      ],
      detectSignal: "resp_time_s",
      detectThr: 2.0,
      detectMax: 10.0,
      detectTitles: [
        "① Watch — each service’s response_time vs fixed threshold (lab 2s)",
        "② Breach — INV crosses threshold → first SERVICE_SLOWDOWN Event",
        "③ Cascade — API then FE each open their own SLOWDOWN Event",
        "④ Storm — raw Event list; still no Problem card"
      ],
      detectSeries: [
        { id: "SERVICE-INV", signal: "resp_s", y: 110, healthy: 0.05, fault: 9.0, order: 0 },
        { id: "SERVICE-API", signal: "resp_s", y: 170, healthy: 0.08, fault: 9.1, order: 1 },
        { id: "SERVICE-FE", signal: "resp_s", y: 230, healthy: 0.1, fault: 9.2, order: 2 }
      ],
      events: [
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-INV", ts: "15:05", v: "~9s", from: 1 },
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-API", ts: "15:05", v: "~9s", from: 2 },
        { type: "SERVICE_SLOWDOWN", e: "SERVICE-FE", ts: "15:05", v: "~9s", from: 3 },
        { type: "PROCESS_CPU_HIGH", e: "SERVICE-BATCH", ts: "15:06", v: "0.81", from: 3, noise: true }
      ],
      packageLines: [
        ["rootCauseEntity", "null"],
        ["impact", "frontend · ~159 calls"],
        ["events", "3× SERVICE_SLOWDOWN"]
      ],
      identifyRows: ["long INV span ~9s", "RT FE→product→INV", "CPU HOST-B", "BATCH noise"],
      clearMetric: "response_time",
      clockIntro:
        "Clock = Observed SLOWDOWN lab UTC (<code>P-260820</code>: Events ≈15:05 → Problem ≈15:10). HTTP <b>200</b> slow path — not 5xx."
    },
    monitoring_unavailable: {
      id: "monitoring_unavailable",
      problem: "(planned)",
      problemNote: "illustrative — lab not run",
      rcEntity: "HOST-B / OneAgent",
      rcLabel: "seed tip = monitoring / agent dark (illustrative)",
      clocks: ["t0", "t0+gap", "Problem", "restored"],
      faultWindow: "agent dark window",
      problemAt: "Problem",
      seenFault: "dark",
      maintainTitles: [
        "① Healthy — agents reporting · Grail receiving",
        "② Agent/ingest dark on INV host — map stale · Grail gaps",
        "③ Problem for MONITORING_UNAVAILABLE (illustrative)",
        "④ Agent restored — Grail fills again"
      ],
      grailRows: [
        { e: "SERVICE-INV", ts: "t0", w: "spans/metrics OK", tone: "ok", from: 0 },
        { e: "HOST-B", ts: "t1", w: "OneAgent unreachable", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "t1", w: "no new telemetry", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "t1", w: "calls INV · incomplete traces", tone: "muted", from: 1 },
        { e: "HOST-B", ts: "t2", w: "agent still dark", tone: "seed", from: 1 },
        { e: "HOST-B", ts: "t3", w: "agent back", tone: "ok", from: 3 }
      ],
      detectSignal: "agent_up",
      detectThr: 0.5,
      detectMax: 1.0,
      detectTitles: [
        "① Watch — agent / ingest heartbeats",
        "② Breach — INV host monitoring unavailable Event",
        "③ Related — dependent services may warn",
        "④ Storm — raw Events; not yet Problem"
      ],
      detectSeries: [
        { id: "HOST-B", signal: "agent_up", y: 110, healthy: 1.0, fault: 0.0, order: 0 },
        { id: "SERVICE-INV", signal: "ingest", y: 170, healthy: 1.0, fault: 0.0, order: 1 },
        { id: "SERVICE-API", signal: "ingest", y: 230, healthy: 1.0, fault: 0.85, order: 2 }
      ],
      events: [
        { type: "MONITORING_UNAVAILABLE", e: "HOST-B", ts: "t1", v: "agent", from: 1 },
        { type: "MONITORING_UNAVAILABLE", e: "SERVICE-INV", ts: "t1", v: "dark", from: 2 },
        { type: "CONNECTION_FAILED", e: "SERVICE-API", ts: "t2", v: "partial", from: 3 }
      ],
      packageLines: [
        ["category", "MONITORING_UNAVAILABLE"],
        ["seed tip", "HOST-B / agent"],
        ["note", "lab planned"]
      ],
      identifyRows: ["agent heartbeat miss", "ingest gap INV", "trace breaks", "noise"],
      clearMetric: "agent_up",
      clockIntro:
        "Illustrative MONITORING_UNAVAILABLE path (lab planned). Detect tip = agent/ingest dark — not app 5xx."
    },
    availability: {
      id: "availability",
      problem: "(planned)",
      problemNote: "illustrative — lab not run",
      rcEntity: "SERVICE-INV",
      rcLabel: "seed tip = process/host down (illustrative)",
      clocks: ["t0", "crash window", "Problem", "restarted"],
      faultWindow: "process down",
      problemAt: "Problem",
      seenFault: "down",
      maintainTitles: [
        "① Healthy — INV process up",
        "② INV process/host down — map marks unavailable · Grail availability Events",
        "③ AVAILABILITY Problem (illustrative)",
        "④ Process back — availability clear"
      ],
      grailRows: [
        { e: "SERVICE-INV", ts: "t0", w: "process UP", tone: "ok", from: 0 },
        { e: "SERVICE-INV", ts: "t1", w: "process DOWN", tone: "seed", from: 1 },
        { e: "SERVICE-API", ts: "t1", w: "connection refused", tone: "seed", from: 1 },
        { e: "SERVICE-FE", ts: "t1", w: "upstream fail", tone: "muted", from: 1 },
        { e: "SERVICE-INV", ts: "t2", w: "still DOWN", tone: "seed", from: 1 },
        { e: "SERVICE-INV", ts: "t3", w: "process UP", tone: "ok", from: 3 }
      ],
      detectSignal: "availability",
      detectThr: 0.5,
      detectMax: 1.0,
      detectTitles: [
        "① Watch — process / host availability",
        "② Breach — INV availability Event",
        "③ Cascade — API/FE connection failures",
        "④ Storm — raw Events"
      ],
      detectSeries: [
        { id: "SERVICE-INV", signal: "available", y: 110, healthy: 1.0, fault: 0.0, order: 0 },
        { id: "SERVICE-API", signal: "available", y: 170, healthy: 1.0, fault: 0.4, order: 1 },
        { id: "SERVICE-FE", signal: "available", y: 230, healthy: 1.0, fault: 0.5, order: 2 }
      ],
      events: [
        { type: "SERVICE_UNAVAILABLE", e: "SERVICE-INV", ts: "t1", v: "down", from: 1 },
        { type: "CONNECTION_LOST", e: "SERVICE-API", ts: "t1", v: "refused", from: 2 },
        { type: "REQUEST_FAILED", e: "SERVICE-FE", ts: "t2", v: "5xx/timeout", from: 3 }
      ],
      packageLines: [
        ["category", "AVAILABILITY"],
        ["seed tip", "SERVICE-INV"],
        ["note", "lab planned"]
      ],
      identifyRows: ["process down INV", "conn refused API", "FE errors", "noise"],
      clearMetric: "availability",
      clockIntro:
        "Illustrative AVAILABILITY path (lab planned). Hard down — not soft error_rate or latency-only."
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
        "Illustrative RESOURCE_CONTENTION path (lab planned). Detect tip = CPU/mem; Smartscape runsOn matters."
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
    if (s === "planned") return "Planned lab";
    return s;
  }

  /** Inject sticky category bar under #urca-doc-nav (or at top). */
  function mountSwitcher(opts) {
    opts = opts || {};
    if (document.getElementById("urca-dt-cat-bar")) return;
    var cat = current();
    persist(cat);

    var style = document.createElement("style");
    style.textContent = [
      "#urca-dt-cat-bar{position:sticky;top:0;z-index:9998;display:flex;flex-wrap:wrap;gap:10px;align-items:center;",
      "padding:8px 12px;background:rgba(12,16,22,.96);border-bottom:1px solid #2a3441;",
      "font-family:system-ui,-apple-system,sans-serif;font-size:13px;color:#c5d0da;}",
      "#urca-doc-nav + #urca-dt-cat-bar,#urca-doc-nav ~ #urca-dt-cat-bar{top:42px;}",
      "#urca-dt-cat-bar label{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#8a96a4;}",
      "#urca-dt-cat-bar select{font:inherit;padding:5px 8px;border-radius:4px;border:1px solid #2a3441;",
      "background:#1c2430;color:#e8eef4;min-width:16rem;}",
      "#urca-dt-cat-bar .slots{display:flex;flex-wrap:wrap;gap:6px;margin-left:auto;}",
      "#urca-dt-cat-bar .slots a{font-size:12px;padding:4px 9px;border-radius:4px;border:1px solid #2a3441;",
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
    bar.setAttribute("aria-label", "Davis event category");

    var labEl = document.createElement("label");
    labEl.htmlFor = "urca-dt-cat-select";
    labEl.textContent = "Davis category";
    bar.appendChild(labEl);

    var sel = document.createElement("select");
    sel.id = "urca-dt-cat-select";
    CATS.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c.id;
      o.textContent = c.title + (c.status === "planned" ? "  · planned" : "");
      if (c.id === cat.id) o.selected = true;
      sel.appendChild(o);
    });
    bar.appendChild(sel);

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
      slots.appendChild(a);
    }
    addSlot(TEACH.hub, "Hub", "hub");
    addSlot(TEACH.pipeline, "Thesis", "pipeline");
    addSlot(TEACH.mechanisms, "Breakdown", "mechanisms");
    addSlot(TEACH.e2e, "Dual-track", "e2e");
    addSlot(cat.lab, cat.status === "observed" ? "Timeline" : "Timeline (planned)", "lab");
    bar.appendChild(slots);

    sel.addEventListener("change", function () {
      var next = byId(sel.value);
      persist(next);
      var path = (location.pathname || "").toLowerCase();
      // Stay on teaching canvases so Maintain/Detect data reloads for the new category
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
