/* Shared site nav for hosted HTML on :8765 — include as <script src="/doc-nav.js"></script>
 *
 * Also injects urca-docs.css + IBM Plex fonts for consistent hub typography/layout.
 * One global sticky bar only. Do NOT add a second horizontal site menu on pages.
 *
 * Optional: <script src="/theme-init.js"></script> in <head> avoids a flash before defer load.
 *
 * Top bar uses flat links plus dropdown groups:
 *   Vendor survey — DT / DD / ED hubs, Obs 1.0/2.0/3.0, DT vs DD vs ED
 *   Bakeoff — Fed vs DT, Lean/Federated eval reference
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

  /** Flat top links and dropdown groups (order = left → right). */
  var navItems = [
    { type: "link", href: "/docs.html", label: "Docs index" },
    { type: "link", href: "/urca-glossary.html", label: "Glossary" },
    { type: "link", href: "/observeops-pipeline-hld.html", label: "Our HLD" },
    {
      type: "group",
      id: "vendor-survey",
      label: "Vendor survey",
      items: [
        { href: "/dt-davis-category-hub.html", label: "DT hub" },
        { href: "/dd-detect-category-hub.html", label: "DD hub" },
        { href: "/ed-ai-team-hub.html", label: "ED hub" },
        { href: "/observability-generations-dt-dd.html", label: "Obs 1.0 / 2.0 / 3.0" },
        { href: "/comparable-pipeline-dt-dd.html", label: "DT vs DD vs ED" }
      ]
    },
    {
      type: "group",
      id: "bakeoff",
      label: "Bakeoff",
      items: [
        { href: "/federated-vs-dt-pipeline-gaps.html", label: "Fed vs DT" },
        { href: "/eval-reference.html", label: "Lean · Federated eval" }
      ]
    },
    { type: "link", href: "/multi-telemetry-rca-fac.html", label: "Motadata FR/AC" },
    { type: "link", href: "/", label: "PoC console" }
  ];

  var path = (location.pathname || "").replace(/\/+$/, "") || "/";

  var nav = document.createElement("nav");
  nav.id = "urca-doc-nav";
  nav.setAttribute("aria-label", "Site");

  var label = document.createElement("span");
  label.className = "urca-nav-label";
  label.textContent = "Site";
  nav.appendChild(label);

  function linkIsHere(item) {
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
      /observeops-pipeline-hld|OBSERVEOPS_PIPELINE_HLD|OBSERVEOPS_HLD_OPERATIONAL_GRAPH|OBSERVEOPS_USE_CASES|observeops-fusion-guide|observeops-ci-graph|observeops-pipeline-diagram|observeops-shift-left|hld-archive|motadata-3pillars|lld-e\d|motadata-unified-pipeline-workflow|graphwriter-io-walkthrough|checkout-diagnose-walkthrough/i.test(path)
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
      /ed-ai-team-hub|edgedelta-production-pipeline|EDGEDELTA_PRODUCTION_PIPELINE|edgedelta-subsystem-mechanisms|ed-e2e-pipelines-team|ed-portal-walkthrough|ed-lab-timeline|edgedelta-tenant-evidence|edgedelta-lab-run|edgedelta-uc9|ed-lab-setup|EDGEDELTA_LAB_SETUP|ed-supported-scenarios|edgedelta-to-motadata-mapping/.test(
        path
      )
    ) {
      return true;
    }
    if (
      item.href === "/comparable-pipeline-dt-dd.html" &&
      /comparable-pipeline-dt-dd/.test(path)
    ) {
      return true;
    }
    if (
      item.href === "/observability-generations-dt-dd.html" &&
      /observability-generations-dt-dd/.test(path)
    ) {
      return true;
    }
    if (
      item.href === "/federated-vs-dt-pipeline-gaps.html" &&
      /federated-vs-dt|FEDERATED_VS_DT/.test(path)
    ) {
      return true;
    }
    if (
      item.href === "/eval-reference.html" &&
      /eval-reference|rca-workflow-sim|ECOM_CHECKOUT|PIPELINE_PARITY|ADR-001/i.test(path)
    ) {
      return true;
    }
    return false;
  }

  function groupHasHere(group) {
    return group.items.some(linkIsHere);
  }

  function makeLink(item) {
    var a = document.createElement("a");
    a.href = item.href;
    a.textContent = item.label;
    if (linkIsHere(item)) a.className = "here";
    return a;
  }

  function closeAllMenus(except) {
    nav.querySelectorAll(".urca-nav-group.open").forEach(function (g) {
      if (g !== except) {
        g.classList.remove("open");
        var btn = g.querySelector(".urca-nav-group-btn");
        if (btn) btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function makeGroup(group) {
    var wrap = document.createElement("div");
    wrap.className = "urca-nav-group";
    wrap.dataset.group = group.id;
    if (groupHasHere(group)) wrap.classList.add("here");

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "urca-nav-group-btn";
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-haspopup", "true");
    btn.setAttribute("aria-controls", "urca-nav-menu-" + group.id);
    btn.textContent = group.label;

    var menu = document.createElement("div");
    menu.className = "urca-nav-menu";
    menu.id = "urca-nav-menu-" + group.id;
    menu.setAttribute("role", "menu");

    group.items.forEach(function (item) {
      var a = makeLink(item);
      a.setAttribute("role", "menuitem");
      menu.appendChild(a);
    });

    btn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      var open = !wrap.classList.contains("open");
      closeAllMenus(wrap);
      wrap.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });

    wrap.appendChild(btn);
    wrap.appendChild(menu);
    return wrap;
  }

  navItems.forEach(function (item) {
    if (item.type === "group") nav.appendChild(makeGroup(item));
    else nav.appendChild(makeLink(item));
  });

  document.addEventListener("click", function () {
    closeAllMenus(null);
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") closeAllMenus(null);
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
