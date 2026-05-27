(function () {
  "use strict";

  var STEALTH_ENDPOINT = "/api/stealth/report";
  var REPORTED = false;

  function report(type, details) {
    if (REPORTED) return;
    REPORTED = true;
    var pid = typeof PARTICIPANT_ID !== "undefined" ? PARTICIPANT_ID : "";
    var payload = JSON.stringify({
      type: type,
      details: details || {},
      participant_id: pid,
      url: window.location.href,
      timestamp: new Date().toISOString(),
    });
    fetch(STEALTH_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
    }).catch(function () {});
  }

  // ── 1. DevTools docked detection ──
  function checkDevToolsSize() {
    var wd = window.outerWidth - window.innerWidth;
    var hd = window.outerHeight - window.innerHeight;
    if (wd > 160 || hd > 160) {
      report("devtools_docked", { widthDelta: wd, heightDelta: hd });
    }
  }

  // ── 2. DevTools console detection ──
  (function consoleTrap() {
    var trap = /./;
    trap.toString = function () {
      report("devtools_console", {});
      return " ";
    };
    setInterval(function () { console.log(trap); }, 3000);
  })();

  // ── 3. Headless browser detection ──
  function checkHeadless() {
    var flags = [];
    if (navigator.webdriver) flags.push("webdriver");
    if (!navigator.plugins || navigator.plugins.length === 0)
      flags.push("no_plugins");
    if (
      navigator.languages !== undefined &&
      navigator.languages.length === 0
    )
      flags.push("no_languages");
    if (
      navigator.mimeTypes !== undefined &&
      navigator.mimeTypes.length === 0
    )
      flags.push("no_mimeTypes");
    if (navigator.plugins && navigator.plugins.length === 0) {
      if (navigator.mimeTypes && navigator.mimeTypes.length === 0) {
        flags.push("headless_chrome");
      }
    }
    if (window.chrome && chrome.runtime === undefined) {
      flags.push("chrome_no_runtime");
    }
    if (flags.length >= 2) {
      report("headless", flags.join(","));
    }
  }

  // ── 4. Block F12 & dev shortcuts ──
  document.addEventListener(
    "keydown",
    function (e) {
      var blocked = false;
      if (e.key === "F12") blocked = true;
      if (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "J" || e.key === "C"))
        blocked = true;
      if (e.ctrlKey && e.key === "U") blocked = true;
      if (e.ctrlKey && e.shiftKey && e.key === "i") blocked = true;
      if (blocked) {
        e.preventDefault();
        e.stopPropagation();
        report("devtools_shortcut", {
          key: e.key,
          ctrl: e.ctrlKey,
          shift: e.shiftKey,
        });
        return false;
      }
    },
    true
  );

  // ── 5. Block right-click ──
  document.addEventListener(
    "contextmenu",
    function (e) {
      e.preventDefault();
      report("context_menu", {});
      return false;
    },
    true
  );

  // ── 6. Debugger timing trap ──
  (function debuggerTrap() {
    var start = performance.now();
    (function debug() {})();
    var end = performance.now();
    if (end - start > 50) {
      report("devtools_stepped", { delay: Math.round(end - start) });
    }
  })();

  // ── Init ──
  checkDevToolsSize();
  checkHeadless();
  setInterval(checkDevToolsSize, 3000);
  setInterval(checkHeadless, 5000);
})();
