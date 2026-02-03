// Apply rounded corners to mermaid nodes after render
(function () {
  function applyRoundedCorners() {
    document.querySelectorAll(".mermaid svg").forEach(function (svg) {
      // Apply to all rect elements except clusters and edge labels
      svg.querySelectorAll("rect").forEach(function (rect) {
        const isCluster = rect.closest(".cluster");
        const isEdgeLabel = rect.closest(".edgeLabel");

        if (isEdgeLabel) {
          rect.style.fill = "transparent";
          rect.setAttribute("fill", "transparent");
          return;
        }

        if (!isCluster) {
          rect.setAttribute("rx", "8");
          rect.setAttribute("ry", "8");
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function init() {
    const observer = new MutationObserver(function () {
      applyRoundedCorners();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    applyRoundedCorners();
    setTimeout(applyRoundedCorners, 100);
    setTimeout(applyRoundedCorners, 500);
    setTimeout(applyRoundedCorners, 1000);
  }
})();
