/**
 * Highlight the left TOC entry for the heading currently in view.
 * Include after the article: <script src="/toc-spy.js" defer></script>
 */
(function () {
  "use strict";

  function spy() {
    var toc = document.querySelector(".shell > nav.toc") || document.querySelector("nav.toc");
    if (!toc) return;
    var links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
    var sections = [];
    links.forEach(function (a) {
      var id = decodeURIComponent((a.getAttribute("href") || "").replace(/^#/, ""));
      if (!id) return;
      var el = document.getElementById(id);
      if (el) sections.push({ el: el, a: a });
    });
    if (!sections.length) return;

    function navOffset() {
      var n = parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue("--urca-nav-h")
      );
      return (isNaN(n) ? 48 : n) + 18;
    }

    function setHere(active) {
      links.forEach(function (a) {
        a.classList.toggle("here", active && a === active.a);
      });
      if (!active) return;
      var r = active.a.getBoundingClientRect();
      var box = toc.getBoundingClientRect();
      if (r.top < box.top + 8 || r.bottom > box.bottom - 8) {
        active.a.scrollIntoView({ block: "nearest" });
      }
    }

    function update() {
      var y = navOffset();
      var current = sections[0];
      for (var i = 0; i < sections.length; i++) {
        if (sections[i].el.getBoundingClientRect().top <= y) current = sections[i];
      }
      setHere(current);
    }

    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", spy);
  else spy();
})();
