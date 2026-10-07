(function () {
  if (window.self === window.top) return;
  document.documentElement.classList.add("embedded");

  function notifyHeight() {
    const h = Math.max(
      document.documentElement.scrollHeight,
      document.body ? document.body.scrollHeight : 0,
      document.documentElement.offsetHeight
    );
    window.parent.postMessage({ type: "unified-rca-embed-height", height: h }, "*");
  }

  notifyHeight();
  window.addEventListener("load", notifyHeight);
  if (typeof ResizeObserver !== "undefined" && document.body) {
    new ResizeObserver(notifyHeight).observe(document.body);
  }
  window.addEventListener("resize", notifyHeight);
})();
