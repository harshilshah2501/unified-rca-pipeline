/* Shared site nav for hosted HTML on :8765 — include as <script src="/doc-nav.js"></script>
 *
 * Also injects urca-docs.css + IBM Plex fonts for consistent hub typography/layout.
 * One global sticky bar only. Do NOT add a second horizontal site menu on pages.
 *
 * Optional: <script src="/theme-init.js"></script> in <head> avoids a flash before defer load.
 */
(function applyHubThemeEarly() {
  try {
    var stored = localStorage.getItem("urca-hub-theme");
    var theme = stored === "light" || stored === "dark" ? stored : "dark";
    document.documentElement.setAttribute("data-theme", theme);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();

(function () {
  if (window.__URCA_DOC_NAV__) return;
  window.__URCA_DOC_NAV__ = true;

  var FONT_HREF =
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap";
  var THEME_KEY = "urca-hub-theme";

  function ensureHeadAsset(kind, href, id) {
    if (document.getElementById(id)) return;
    var el = document.createElement("link");
    el.id = id;
    el.rel = kind;
    el.href = href;
    if (kind === "stylesheet") el.href = href;
    document.head.appendChild(el);
  }

  function ensureTheme() {
    ensureHeadAsset("preconnect", "https://fonts.googleapis.com", "urca-font-preconnect");
    ensureHeadAsset("preconnect", "https://fonts.gstatic.com", "urca-font-preconnect-gstatic");
    var gstatic = document.getElementById("urca-font-preconnect-gstatic");
    if (gstatic) gstatic.crossOrigin = "anonymous";
    ensureHeadAsset("stylesheet", FONT_HREF, "urca-fonts");
    ensureHeadAsset("stylesheet", "/urca-docs.css", "urca-docs-css");
  }

  function getTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function setTheme(theme) {
    var next = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (e) {}
    updateThemeToggle();
  }

  function toggleTheme() {
    setTheme(getTheme() === "dark" ? "light" : "dark");
  }

  var themeToggle;

  function updateThemeToggle() {
    if (!themeToggle) return;
    var isLight = getTheme() === "light";
    themeToggle.textContent = isLight ? "Dark" : "Light";
    themeToggle.setAttribute(
      "aria-label",
      isLight ? "Switch to dark theme" : "Switch to light theme"
    );
    themeToggle.title = isLight ? "Switch to dark theme" : "Switch to light theme";
  }

  ensureTheme();

  var links = [
    { href: "/docs.html", label: "Docs index" },
    { href: "/urca-glossary.html", label: "Glossary" },
    { href: "/observeops-pipeline-hld.html", label: "Our HLD" },
    { href: "/dt-davis-category-hub.html", label: "DT hub" },
    { href: "/dd-detect-category-hub.html", label: "DD hub" },
    { href: "/ed-ai-team-hub.html", label: "ED hub" },
    { href: "/comparable-pipeline-dt-dd.html", label: "DT vs DD vs ED" },
    { href: "/observability-generations-dt-dd.html", label: "Obs 1.0 / 2.0 / 3.0" },
    { href: "/federated-vs-dt-pipeline-gaps.html", label: "Fed vs DT" },
    { href: "/multi-telemetry-rca-fac.html", label: "Motadata FR/AC" },
    { href: "/", label: "PoC console" }
  ];

  var path = (location.pathname || "").replace(/\/+$/, "") || "/";

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
    if (item.href === "/docs.html" && /\/docs\.html$|\/docs-index\.html$/.test(path)) return true;
    if (
      item.href === "/urca-glossary.html" &&
      /urca-glossary|GLOSSARY\.md/i.test(path)
    ) {
      return true;
    }
    if (
      item.href === "/observeops-pipeline-hld.html" &&
      /observeops-pipeline-hld|OBSERVEOPS_PIPELINE_HLD|OBSERVEOPS_HLD_OPERATIONAL_GRAPH|OBSERVEOPS_USE_CASES|observeops-fusion-guide|observeops-ci-graph|observeops-pipeline-diagram|observeops-shift-left|hld-archive|motadata-3pillars|lld-e\d/i.test(path)
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
      item.href === "/ed-ai-team-hub.html" &&
      /ed-ai-team-hub|edgedelta-production-pipeline|EDGEDELTA_PRODUCTION_PIPELINE|edgedelta-subsystem-mechanisms|ed-e2e-pipelines-team|ed-portal-walkthrough|ed-lab-timeline|edgedelta-tenant-evidence|edgedelta-lab-run|edgedelta-uc9|ed-lab-setup|EDGEDELTA_LAB_SETUP|ed-supported-scenarios/.test(
        path
      )
    ) {
      return true;
    }
    if (
      item.href === "/comparable-pipeline-dt-dd.html" &&
      /comparable-pipeline-dt-dd|observability-generations-dt-dd/.test(path)
    ) {
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

  themeToggle = document.createElement("button");
  themeToggle.id = "urca-theme-toggle";
  themeToggle.type = "button";
  themeToggle.addEventListener("click", toggleTheme);
  updateThemeToggle();
  nav.appendChild(themeToggle);

  function mount() {
    if (document.getElementById("urca-doc-nav")) return;
    var body = document.body;
    if (!body) return;
    body.insertBefore(nav, body.firstChild);
  }
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
