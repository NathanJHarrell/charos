(function() {
  var NEST = "https://tc-nest.tailb8d6bc.ts.net";
  var CC_SELECTORS = [
    ".ClosedCaption",                    // Hulu
    ".cc-container",                     // older Hulu
    ".ytp-caption-window-container",     // YouTube
    ".caption-window",                   // YouTube fallback
    ".captions-renderer",                // Netflix
    ".player-timedtext",                 // Netflix alt
    "[class*='Caption']",                // nuclear fallback
  ];
  var lastSent = "";
  var observer = null;

  function findRoot() {
    for (var i = 0; i < CC_SELECTORS.length; i++) {
      var el = document.querySelector(CC_SELECTORS[i]);
      if (el) return el;
    }
    return null;
  }

  function extract(root) {
    return (root.innerText || root.textContent || "").trim();
  }

  function send(text) {
    if (!text || text === lastSent) return;
    lastSent = text;
    var v = document.querySelector("video");
    fetch(NEST + "/subtitle", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text, ts: v ? v.currentTime : null}),
      mode: "cors"
    }).catch(function(e) {
      console.warn("drawercast send failed:", e.message);
    });
  }

  function start() {
    var root = findRoot();
    if (!root) {
      console.warn("DrawerCast: no CC container yet. Turn on CC, re-run.");
      setTimeout(start, 1500);
      return;
    }
    send(extract(root));
    observer = new MutationObserver(function() { send(extract(root)); });
    observer.observe(root, {childList: true, subtree: true, characterData: true});
    console.log("DrawerCast armed. Streaming from " + (root.className || root.tagName) + " to " + NEST);
  }

  window.drawerCastStop = function() {
    if (observer) observer.disconnect();
    console.log("DrawerCast stopped.");
  };

  start();
})();
