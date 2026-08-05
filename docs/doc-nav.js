/* Shared cross-doc nav for hosted HTML on :8765 — include as <script src="/doc-nav.js"></script> */
(function () {
  if (window.__URCA_DOC_NAV__) return;
  window.__URCA_DOC_NAV__ = true;

  var links = [
    { href: "/docs.html", label: "Docs index" },
    { href: "/comparable-pipeline-dt-dd.html", label: "DT vs DD" },
    { href: "/dynatrace-production-pipeline.html", label: "DT pipeline" },
    { href: "/eleven-subsystem-mechanisms.html", label: "DT mechanisms" },
    { href: "/federated-vs-dt-pipeline-gaps.html", label: "Fed vs DT gaps" },
    { href: "/datadog-production-pipeline.html", label: "DD pipeline" },
    { href: "/datadog-subsystem-mechanisms.html", label: "DD mechanisms" },
    { href: "/datadog-lab-evidence-2026-08-04.html", label: "DD lab evidence" },
    { href: "/rca-data-lake-brainstorm.html", label: "Data lake" },
    { href: "/", label: "PoC console" }
  ];

  var path = (location.pathname || "").replace(/\/+$/, "") || "/";
  var style = document.createElement("style");
  style.textContent = [
    "#urca-doc-nav{position:sticky;top:0;z-index:9999;display:flex;flex-wrap:wrap;gap:6px;align-items:center;",
    "padding:8px 12px;background:rgba(15,20,25,.94);border-bottom:1px solid #2a3441;",
    "backdrop-filter:blur(8px);font-family:system-ui,-apple-system,sans-serif;}",
    "#urca-doc-nav a{font-size:12px;padding:5px 9px;border-radius:4px;border:1px solid #2a3441;",
    "background:#1c2430;color:#b8c4d0;text-decoration:none;white-space:nowrap;}",
    "#urca-doc-nav a:hover{color:#e8eef4;border-color:#3d9a8b;}",
    "#urca-doc-nav a.here{color:#7ec8b8;border-color:rgba(61,154,139,.55);background:rgba(61,154,139,.14);}",
    "#urca-doc-nav .urca-back{margin-right:4px;border-color:rgba(91,141,239,.45);color:#9bb8f5;}"
  ].join("");
  document.head.appendChild(style);

  var nav = document.createElement("nav");
  nav.id = "urca-doc-nav";
  nav.setAttribute("aria-label", "Documentation");

  links.forEach(function (item) {
    var a = document.createElement("a");
    a.href = item.href;
    a.textContent = item.label;
    var target = item.href.replace(/\/+$/, "") || "/";
    if (path === target || path.endsWith(target)) a.className = "here";
    if (item.href === "/docs.html") a.classList.add("urca-back");
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
