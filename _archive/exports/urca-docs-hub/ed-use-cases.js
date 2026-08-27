/**
 * Edge Delta AI Team use-case registry + sticky teaching chrome for docs hub (:8765).
 *
 * Not a Detect-category twin. DT/DD switch ERROR/SLOWDOWN; ED switches the 10
 * published investigation jobs. Thesis is use-case-neutral (shared fabric).
 * Breakdown / Dual-layer / Portal / Timeline take ?uc=<id>.
 *
 * Sticky slots: Hub → Thesis → Breakdown → Dual-layer → Portal → Timeline
 */
(function (global) {
  "use strict";

  var UCS = [
    {
      id: "uc9",
      n: 9,
      name: "UC9",
      title: "UC9 · GitHub development workflow",
      blurb:
        "Scheduled Daily GitHub Engineering Risk Report — not a @edge-delta PR comment. SaaS-only; no cluster required.",
      detect: "Workflow · Daily Report - github (not GitHub Event Thresholds)",
      status: "observed",
      evidence: "Resolved · #code-issues · 391.1 K tokens · 2026-08-17",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/ai/overview",
      door: "Cloud ingest + GitHub connector",
      honesty: "Observed (UI). Thread ≠ Issue. Issues still 0."
    },
    {
      id: "uc8",
      n: 8,
      name: "UC8",
      title: "UC8 · Kubernetes troubleshooting",
      blurb:
        "Pod Crash Monitor → OnCall thread in #alerts. kubectl leaf: inventory-api missing INVENTORY_DSN. SaaS log search 500 this session.",
      detect: "Pod Crash Monitor (Event) → OnCall → SRE",
      status: "team_recipe",
      evidence: "Completed · Team recipe · no Issue card · CrashLoopBackOff",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/monitors/list",
      door: "Node · K8s events / pod logs",
      honesty: "Completed at team-recipe scope. Do not Test UC8 again. Thread ≠ Issue (Issues 0)."
    },
    {
      id: "uc4",
      n: 4,
      name: "UC4",
      title: "UC4 · Database performance",
      blurb:
        "Frontend → API → Postgres path. Node eBPF traces landed without Gateway. No DB OnCall. No OTLP Gateway.",
      detect: "Traces / Service Map (no DB monitor wired)",
      status: "partial",
      evidence: "checkout-api-db → checkout-db eBPF traces",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/traces",
      door: "Node eBPF (Gateway still open for OTLP)",
      honesty: "Signals Observed. Diagnose recipe not run."
    },
    {
      id: "uc1",
      n: 1,
      name: "UC1",
      title: "UC1 · Anomaly-triggered investigation",
      blurb:
        "Parked. Negative patterns indexed; live Pattern Anomaly stayed No Data (empty lookback). 18 Aug ingest 402; noisy-logger scaled to 0. Test ≠ ALERT.",
      detect: "Pattern Anomaly · Default Service Anomaly (live No Data)",
      status: "parked",
      evidence: "Patterns + tuned monitor; event.type:pattern_anomaly = 0; 402 on 18 Aug",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/monitors/edit/3HtsPcoX2ZN8CG9rpfKBOXN65mL",
      door: "Org Monitor · Pattern Anomaly",
      honesty: "Parked on lookback then ingest 402. Firehose scaled to 0. Do not Test unless asked."
    },
    {
      id: "uc6",
      n: 6,
      name: "UC6",
      title: "UC6 · Ingest failure",
      blurb:
        "Lite only — fake kafka produce timeout patterns on ingest-api. No Kafka cluster. No OnCall thread.",
      detect: "Log patterns (no Pattern Anomaly event)",
      status: "lite",
      evidence: "ingest-api kafka produce timeout patterns; scaled to 0 on 18 Aug",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/logs/search",
      door: "Node log tail",
      honesty: "Lite patterns only. Not an investigation recipe."
    },
    {
      id: "uc10",
      n: 10,
      name: "UC10",
      title: "UC10 · Data locality for AI investigations",
      blurb:
        "Why telemetry routed through Edge Delta makes MCP native. Demoed from Cursor MCP, not a portal alert path.",
      detect: "Edge Delta MCP connector (no monitor)",
      status: "mcp_demo",
      evidence: "MCP saw events + patterns + traces on this org",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/ai/connectors",
      door: "Platform index → MCP",
      honesty: "Native MCP demo. Not a Detect door."
    },
    {
      id: "uc2",
      n: 2,
      name: "UC2",
      title: "UC2 · Security-related degradation",
      blurb: "Security Engineer joins SRE when a perf/infra change might be compromise. AWS connector not connected.",
      detect: "Needs AWS + ED MCP + GitHub",
      status: "blocked",
      evidence: "Connectors Observed: GitHub · ED MCP · ED Docs only",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/ai/connectors",
      door: "Blocked — AWS",
      honesty: "Blocked. Do not invent a security scenario."
    },
    {
      id: "uc3",
      n: 3,
      name: "UC3",
      title: "UC3 · Cross-platform telemetry",
      blurb: "Correlate Edge Delta with another lake (Elasticsearch MCP). Elastic not connected.",
      detect: "Needs Elastic MCP",
      status: "blocked",
      evidence: "No Elastic connector",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/ai/connectors",
      door: "Blocked — Elastic",
      honesty: "Blocked."
    },
    {
      id: "uc5",
      n: 5,
      name: "UC5",
      title: "UC5 · CI/CD pipeline failure",
      blurb: "CircleCI + GitHub to separate regression vs flake vs environment. CircleCI not connected.",
      detect: "Needs CircleCI connector",
      status: "blocked",
      evidence: "GitHub Event Thresholds exist; often No Data. CircleCI absent.",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/ai/connectors",
      door: "Blocked — CircleCI",
      honesty: "Blocked."
    },
    {
      id: "uc7",
      n: 7,
      name: "UC7",
      title: "UC7 · PagerDuty incident automation",
      blurb: "PagerDuty webhook in; confidence-gated actions; human approval. PagerDuty not connected.",
      detect: "Needs PagerDuty connector",
      status: "blocked",
      evidence: "No PagerDuty connector",
      lab: "/ed-lab-timeline.html",
      portal: "/ed-portal-walkthrough.html",
      app: "https://app.edgedelta.com/ai/connectors",
      door: "Blocked — PagerDuty",
      honesty: "Blocked."
    }
  ];

  var TEACH = {
    hub: "/ed-ai-team-hub.html",
    pipeline: "/edgedelta-production-pipeline.html",
    mechanisms: "/edgedelta-subsystem-mechanisms.html",
    e2e: "/ed-e2e-pipelines-team.html",
    portal: "/ed-portal-walkthrough.html",
    lab: "/ed-lab-timeline.html"
  };

  var STORAGE_KEY = "urca.ed.uc";

  function byId(id) {
    var key = String(id || "").toLowerCase();
    if (/^\d+$/.test(key)) key = "uc" + key;
    for (var i = 0; i < UCS.length; i++) if (UCS[i].id === key) return UCS[i];
    return UCS[0];
  }

  function fromQuery() {
    try {
      var q = new URLSearchParams(location.search || "");
      var c = q.get("uc") || q.get("cat");
      if (c) return byId(c);
    } catch (e) {}
    return null;
  }

  function fromPath() {
    var p = (location.pathname || "").toLowerCase();
    if (p.indexOf("uc9") >= 0 || p.indexOf("github") >= 0 && p.indexOf("edgedelta") >= 0)
      return byId("uc9");
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
    return fromQuery() || fromPath() || fromStorage() || UCS[0];
  }

  function persist(uc) {
    try {
      localStorage.setItem(STORAGE_KEY, uc.id);
    } catch (e) {}
  }

  function withUc(url, uc) {
    var u = url;
    u = u.replace(/([?&])(uc|cat)=[^&]*/g, "$1").replace(/[?&]$/, "").replace(/\?&/, "?");
    var join = u.indexOf("?") >= 0 ? "&" : "?";
    if (!u.includes("?")) return u + "?uc=" + encodeURIComponent(uc.id);
    return u + "&uc=" + encodeURIComponent(uc.id);
  }

  function statusLabel(s) {
    if (s === "observed") return "Observed";
    if (s === "team_recipe") return "Completed — team recipe, no Issue card";
    if (s === "partial") return "Partial";
    if (s === "parked") return "Parked";
    if (s === "lite") return "Lite";
    if (s === "mcp_demo") return "MCP demo";
    if (s === "blocked") return "Blocked";
    return s;
  }

  function statusPill(s) {
    if (s === "observed") return "ok";
    if (s === "team_recipe" || s === "partial" || s === "mcp_demo") return "task";
    if (s === "parked") return "park";
    if (s === "blocked") return "block";
    return "plan";
  }

  function isThesisPage(path) {
    path = (path || location.pathname || "").toLowerCase();
    return path.indexOf("edgedelta-production-pipeline") >= 0;
  }

  function stripUcFromLocation() {
    try {
      var u = new URL(location.href);
      if (!u.searchParams.has("uc") && !u.searchParams.has("cat")) return;
      u.searchParams.delete("uc");
      u.searchParams.delete("cat");
      var q = u.searchParams.toString();
      history.replaceState(null, "", u.pathname + (q ? "?" + q : "") + u.hash);
    } catch (e) {}
  }

  function mountSwitcher(opts) {
    opts = opts || {};
    if (document.getElementById("urca-ed-cat-bar")) return;
    var uc = current();
    persist(uc);
    var thesis = isThesisPage();
    if (thesis) stripUcFromLocation();

    var bar = document.createElement("div");
    bar.id = "urca-ed-cat-bar";
    bar.setAttribute("role", "navigation");
    bar.setAttribute("aria-label", "Edge Delta teaching");
    if (thesis) bar.classList.add("thesis-neutral");

    var rowUc = document.createElement("div");
    rowUc.className = "urca-teach-row cat";
    var kUc = document.createElement("span");
    kUc.className = "urca-k";
    kUc.textContent = "Use case";
    rowUc.appendChild(kUc);

    var labEl = document.createElement("label");
    labEl.htmlFor = "urca-ed-uc-select";
    labEl.textContent = "AI Team use case";
    rowUc.appendChild(labEl);

    var sel = document.createElement("select");
    sel.id = "urca-ed-uc-select";
    UCS.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c.id;
      o.textContent = c.title + "  · " + statusLabel(c.status);
      if (c.id === uc.id) o.selected = true;
      o.dataset.status = c.status;
      sel.appendChild(o);
    });
    rowUc.appendChild(sel);
    if (!thesis) bar.appendChild(rowUc);

    var rowViews = document.createElement("div");
    rowViews.className = "urca-teach-row views";
    var kViews = document.createElement("span");
    kViews.className = "urca-k";
    kViews.textContent = "Views";
    rowViews.appendChild(kViews);

    var slots = document.createElement("div");
    slots.className = "slots";
    function addSlot(href, label, kind, extraClass) {
      var a = document.createElement("a");
      a.href = kind === "pipeline" ? href : withUc(href, uc);
      a.textContent = label;
      a.dataset.kind = kind;
      var path = (location.pathname || "").replace(/\/+$/, "") || "/";
      var target = href.replace(/\/+$/, "");
      if (path === target || path.endsWith(target)) a.classList.add("here");
      if (extraClass) a.classList.add(extraClass);
      if (kind === "lab" && uc.status === "blocked") a.classList.add("muted");
      slots.appendChild(a);
    }
    addSlot(TEACH.hub, "Hub", "hub");
    addSlot(TEACH.pipeline, "Thesis", "pipeline");
    addSlot(TEACH.mechanisms, "Breakdown", "mechanisms");
    addSlot(TEACH.e2e, "Dual-layer", "e2e");
    addSlot(TEACH.portal, "Portal", "portal", "interp");
    addSlot(TEACH.lab, "Timeline", "lab");
    rowViews.appendChild(slots);
    bar.appendChild(rowViews);

    sel.addEventListener("change", function () {
      var next = byId(sel.value);
      persist(next);
      var path = (location.pathname || "").toLowerCase();
      if (
        /edgedelta-subsystem-mechanisms|ed-e2e-pipelines-team|ed-portal-walkthrough|ed-lab-timeline/.test(
          path
        )
      ) {
        location.href = withUc(location.pathname, next);
        return;
      }
      location.href = withUc(TEACH.hub, next);
    });

    function place() {
      var body = document.body;
      if (!body || document.getElementById("urca-ed-cat-bar")) return;
      var nav = document.getElementById("urca-doc-nav");
      if (nav && nav.parentNode) nav.parentNode.insertBefore(bar, nav.nextSibling);
      else body.insertBefore(bar, body.firstChild);

      if (!thesis && opts.banner !== false && !document.getElementById("urca-ed-cat-banner")) {
        var ban = document.createElement("div");
        ban.id = "urca-ed-cat-banner";
        ban.innerHTML =
          "<b>" +
          uc.name +
          "</b> — " +
          uc.blurb +
          " · Door: <code>" +
          uc.door +
          "</code> · " +
          statusLabel(uc.status) +
          (uc.evidence ? " · " + uc.evidence : "");
        bar.parentNode.insertBefore(ban, bar.nextSibling);
      }
    }
    if (document.body) place();
    else document.addEventListener("DOMContentLoaded", place);
  }

  global.URCA_ED_UCS = {
    list: UCS,
    teach: TEACH,
    current: current,
    byId: byId,
    withUc: withUc,
    persist: persist,
    mountSwitcher: mountSwitcher,
    statusLabel: statusLabel,
    statusPill: statusPill
  };

  var path = (location.pathname || "").toLowerCase();
  var auto =
    path.indexOf("ed-ai-team-hub") >= 0 ||
    path.indexOf("edgedelta-production-pipeline") >= 0 ||
    path.indexOf("edgedelta-subsystem-mechanisms") >= 0 ||
    path.indexOf("ed-e2e-pipelines-team") >= 0 ||
    path.indexOf("ed-portal-walkthrough") >= 0 ||
    path.indexOf("ed-lab-timeline") >= 0 ||
    path.indexOf("ed-lab-setup") >= 0 ||
    path.indexOf("ed-supported-scenarios") >= 0;
  if (auto) {
    document.addEventListener("DOMContentLoaded", function () {
      setTimeout(function () {
        mountSwitcher({ banner: true });
      }, 0);
    });
  }
})(typeof window !== "undefined" ? window : this);
