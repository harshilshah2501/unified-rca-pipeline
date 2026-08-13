/**
 * Shared vendor-hub launchpad: documentation ladder + E-block engineering map.
 * Mount: <div id="urca-hub-launchpad" data-vendor="dt|dd"></div>
 */
(function () {
  "use strict";

  var BLOCKS = [
    { id: "E1", phase: "P1 · F", stage: "Collect", x: "Edge bytes", y: "TelemetryEnvelope", lld: "LLD-E1" },
    { id: "E2", phase: "P1 · F", stage: "Identity", x: "TelemetryEnvelope", y: "IdentifiedRecord (join keys)", lld: "LLD-E2" },
    { id: "E3", phase: "P1 · F", stage: "Topology", x: "IdentifiedRecord + discovery cues", y: "GraphSnapshot (topology)", lld: "LLD-E3" },
    { id: "E4", phase: "P1 · F", stage: "Stores", x: "IdentifiedRecord", y: "Evidence stores (history)", lld: "LLD-E4" },
    { id: "E5", phase: "P1 · F", stage: "Maintain", x: "Stores + topology", y: "Freshness baseline (Detect-ready estate)", lld: "LLD-E5" },
    { id: "E6", phase: "P2 · T", stage: "Detect", x: "Detect-ready estate", y: "Signal (fault signals)", lld: "LLD-E6" },
    { id: "E7", phase: "P2 · T", stage: "Curate", x: "Signal storm", y: "CaseSeed", lld: "LLD-E7" },
    { id: "E8", phase: "P2 · T", stage: "Scope", x: "CaseSeed", y: "WorkingSet (seed + time + candidate CIs)", lld: "LLD-E8" },
    { id: "E9", phase: "P3 · D", stage: "Localize", x: "WorkingSet", y: "LeafClaim", lld: "LLD-E9" },
    { id: "E10", phase: "P3 · D", stage: "Identify", x: "LeafClaim + scoped evidence", y: "EvidenceBundle (corroboration)", lld: "LLD-E10" },
    { id: "E11", phase: "P3 · D", stage: "Package", x: "LeafClaim + corroboration", y: "VerdictCard (operator handoff)", lld: "LLD-E11" }
  ];

  var ANCHORS = {
    dt: {
      E1: "OneAgent / OTLP intake",
      E2: "Enrichment → entityId + failure cues",
      E3: "Smartscape nodes/edges",
      E4: "Grail evidence ∥ Smartscape upserts",
      E5: "Grail lifecycle + Smartscape freshness",
      E6: "Detectors → Event objects",
      E7: "Davis Event merge",
      E8: "Smartscape neighborhood + Grail DQL cut",
      E9: "Smartscape walk · rootCauseEntity",
      E10: "rootCauseRelevant ranking on Grail",
      E11: "Problem (default packaging)"
    },
    dd: {
      E1: "Agent · ddtrace · DogStatsD · log tails",
      E2: "Unified Service Tags + span status",
      E3: "Service Catalog · APM Service Map",
      E4: "Metrics store ∥ Husky (APM + Logs)",
      E5: "Continuous 03 Write + retention/indexing",
      E6: "Door A Monitors ∥ Door B Watchdog",
      E7: "Thin auto-merge · operator/Bits seed",
      E8: "Related · env/version/time scope",
      E9: "Flamegraph / deepest error or self-time",
      E10: "Tag join across M/T/L rails",
      E11: "Bits optional · Incident often 0"
    }
  };

  var LADDER = [
    {
      level: "L0",
      title: "Vendor unveil",
      here: true,
      href: null,
      blurb: "Native product reading for one Detect category — thesis, breakdown, journey, timeline."
    },
    {
      level: "L1",
      title: "Abstract compare lens",
      here: false,
      href: "/comparable-pipeline-dt-dd.html#optional-pattern-lens-clock-a-after-native-reading",
      blurb: "F → T → D distillation: phase outputs, stage I/O spine, DT vs DD gaps — after reading both vendors natively."
    },
    {
      level: "L2",
      title: "ObserveOps HLD",
      here: false,
      href: "/observeops-pipeline-hld.html",
      blurb: "Canonical E1–E11 engineering contracts, ADRs, and information objects we will implement."
    },
    {
      level: "L3",
      title: "Block LLDs",
      here: false,
      href: "/observeops-pipeline-hld.html#contracts",
      blurb: "Per-block low-level designs (LLD-E1 … LLD-E11) — same template as HLD stage catalog; backlog until each block is specced."
    }
  ];

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function hldAnchor(id) {
    var n = parseInt(id.slice(1), 10);
    if (n <= 5) return "/observeops-pipeline-hld.html#p1";
    if (n <= 8) return "/observeops-pipeline-hld.html#p2";
    return "/observeops-pipeline-hld.html#p3";
  }

  function renderLaunchpad(vendor) {
    var anchors = ANCHORS[vendor] || ANCHORS.dt;
    var vendorName = vendor === "dd" ? "Datadog" : "Dynatrace";

    var ladderRows = LADDER.map(function (step) {
      var titleCell = step.href
        ? '<a href="' + esc(step.href) + '"><strong>' + esc(step.title) + "</strong></a>"
        : "<strong>" + esc(step.title) + "</strong>";
      var where = step.here ? vendorName + " hub (you are here)" : "Open next →";
      return (
        "<tr><td><code>" +
        esc(step.level) +
        "</code></td><td>" +
        titleCell +
        "</td><td>" +
        esc(where) +
        "</td><td>" +
        esc(step.blurb) +
        "</td></tr>"
      );
    }).join("");

    var blockRows = BLOCKS.map(function (b) {
      return (
        "<tr><td><code>" +
        esc(b.id) +
        "</code></td><td>" +
        esc(b.phase) +
        "</td><td>" +
        esc(b.stage) +
        "</td><td>" +
        esc(b.x) +
        "</td><td>" +
        esc(b.y) +
        "</td><td>" +
        esc(anchors[b.id] || "") +
        '</td><td><a href="' +
        esc(hldAnchor(b.id)) +
        '">HLD</a> · <span style="color:var(--faint)">' +
        esc(b.lld) +
        " (planned)</span></td></tr>"
      );
    }).join("");

    return (
      '<section class="launchpad">' +
      '<h2 id="launchpad">Documentation ladder</h2>' +
      "<p class=\"launchpad-lead\">Read top-down: vendor-native unveil → abstract engineering pipeline → our HLD → per-block LLDs. " +
      "Vendor terms stay in L0; L1+ use compare-lens and E-block vocabulary only.</p>" +
      "<table><thead><tr><th>Layer</th><th>Artifact</th><th>Where</th><th>Job</th></tr></thead><tbody>" +
      ladderRows +
      "</tbody></table>" +
      '<h2 id="e-blocks">Engineering block map (E1–E11)</h2>' +
      "<p class=\"launchpad-lead\">Same abstract I/O at every row — " +
      vendorName +
      " column shows where this category run anchors in product. LLD column links to HLD contract until dedicated LLD pages land.</p>" +
      "<table><thead><tr><th>Block</th><th>Phase</th><th>Stage</th><th>X (input)</th><th>Y (output)</th><th>" +
      esc(vendorName) +
      " anchor</th><th>Spec</th></tr></thead><tbody>" +
      blockRows +
      "</tbody></table>" +
      '<p class="launchpad-note">Phase handoffs: <strong>P1 → estate</strong> · <strong>P2 → working set</strong> · <strong>P3 → verdict card</strong>. ' +
      'Layer I (Timeline deep-dive, MTL, Bits) retells evidence — it does not replace E-blocks. See <a href="/observeops-pipeline-hld.html#overview">HLD Layer E vs I</a>.</p>' +
      "</section>"
    );
  }

  function mountAll() {
    document.querySelectorAll("#urca-hub-launchpad,[data-urca-hub-launchpad]").forEach(function (el) {
      var vendor = (el.getAttribute("data-vendor") || "dt").toLowerCase();
      el.innerHTML = renderLaunchpad(vendor);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountAll);
  } else {
    mountAll();
  }

  window.URCA_HUB_LAUNCHPAD = { mountAll: mountAll, renderLaunchpad: renderLaunchpad };
})();
