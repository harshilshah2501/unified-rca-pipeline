/* Shared site nav for hosted HTML on :8765 — include as <script src="/doc-nav.js"></script>
 *
 * One global sticky bar only. Do NOT add a second horizontal .doc-bar / .bar of
 * cross-doc links on pages — left TOC (if any) is for in-page sections only.
 */
(function () {
  if (window.__URCA_DOC_NAV__) return;
  window.__URCA_DOC_NAV__ = true;

  var links = [
    { href: "/docs.html", label: "Docs index" },
    { href: "/urca-glossary.html", label: "Glossary" },
    { href: "/observeops-pipeline-hld.html", label: "Our HLD" },
    { href: "/dt-davis-category-hub.html", label: "DT hub" },
    { href: "/dd-detect-category-hub.html", label: "DD hub" },
    { href: "/comparable-pipeline-dt-dd.html", label: "DT vs DD" },
    { href: "/observability-generations-dt-dd.html", label: "Obs 1.0 / 2.0 / 3.0" },
    { href: "/federated-vs-dt-pipeline-gaps.html", label: "Fed vs DT" },
    { href: "/multi-telemetry-rca-fac.html", label: "Motadata FR/AC" },
    { href: "/", label: "PoC console" }
  ];

  var path = (location.pathname || "").replace(/\/+$/, "") || "/";
  var style = document.createElement("style");
  style.textContent = [
    "#urca-doc-nav{position:sticky;top:0;z-index:9999;display:flex;flex-wrap:wrap;gap:6px;align-items:center;",
    "padding:8px 12px;background:rgba(15,20,25,.96);border-bottom:1px solid #2a3441;",
    "backdrop-filter:blur(8px);font-family:system-ui,-apple-system,sans-serif;}",
    "#urca-doc-nav .urca-nav-label{font-size:10px;font-weight:650;letter-spacing:.06em;text-transform:uppercase;",
    "color:#8a96a4;margin-right:6px;white-space:nowrap;}",
    "#urca-dt-cat-bar,#urca-dd-cat-bar{position:sticky;top:42px;z-index:9998;}",
    "#urca-doc-nav a{font-size:12px;padding:5px 9px;border-radius:4px;border:1px solid #2a3441;",
    "background:#1c2430;color:#b8c4d0;text-decoration:none;white-space:nowrap;}",
    "#urca-doc-nav a:hover{color:#e8eef4;border-color:#3d9a8b;}",
    "#urca-doc-nav a.here{color:#7ec8b8;border-color:rgba(61,154,139,.55);background:rgba(61,154,139,.14);}",
    /* Page left TOC sits under the site bar; in-page only — no second site menu */
    ".shell>nav.toc{top:42px;height:calc(100vh - 42px);}",
    /* Hide legacy duplicate site menus if any remain in markup */
    "main>.doc-bar,.wrap>.bar.site-dup{display:none!important;}"
  ].join("");
  document.head.appendChild(style);

  var nav = document.createElement("nav");
  nav.id = "urca-doc-nav";
  nav.setAttribute("aria-label", "Site");

  var label = document.createElement("span");
  label.className = "urca-nav-label";
  label.textContent = "Site";
  nav.appendChild(label);

  function isHere(item) {
    var target = item.href.replace(/\/+$/, "") || "/";
    if (path === target || path.endsWith(target)) return true;
    if (
      item.href === "/urca-glossary.html" &&
      /urca-glossary|GLOSSARY\.md/i.test(path)
    ) {
      return true;
    }
    if (
      item.href === "/observeops-pipeline-hld.html" &&
      /observeops-pipeline-hld|OBSERVEOPS_PIPELINE_HLD|lld-e\d/i.test(path)
    ) {
      return true;
    }
    if (
      item.href === "/dt-davis-category-hub.html" &&
      /dt-lab-timeline|dt-cat-|eleven-subsystem-mechanisms|dynatrace-production-pipeline|dt-e2e-smartscape|dt-davis-category/.test(
        path
      )
    ) {
      return true;
    }
    if (
      item.href === "/dd-detect-category-hub.html" &&
      /dd-lab-timeline|dd-e2e-metrics|datadog-subsystem-mechanisms|datadog-production-pipeline|dd-detect-category|dd-bits-|dd-error-mtl|dd-slowdown-mtl|dd-behind-the-scenes/.test(
        path
      )
    ) {
      return true;
    }
    if (
      item.href === "/comparable-pipeline-dt-dd.html" &&
      /comparable-pipeline-dt-dd|observability-generations-dt-dd/.test(path)
    ) {
      /* Obs page gets its own highlight; DT vs DD only when on compare */
      return /comparable-pipeline-dt-dd/.test(path);
    }
    return false;
  }

  links.forEach(function (item) {
    var a = document.createElement("a");
    a.href = item.href;
    a.textContent = item.label;
    if (isHere(item)) a.className = "here";
    nav.appendChild(a);
  });

  function mount() {
    if (document.getElementById("urca-doc-nav")) return;
    var body = document.body;
    if (!body) return;
    body.insertBefore(nav, body.firstChild);
  }
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
