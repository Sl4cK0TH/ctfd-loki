/**
 * CTFd LOKI — Challenge Update JS
 *
 * Pre-populates Loki-specific fields when the update modal loads,
 * and handles the flag template toggle.
 */

function toggleFlagTemplate() {
  var modeEl = document.getElementById("flag_mode");
  if (!modeEl) {
    return;
  }
  var mode = modeEl.value;
  var group = document.getElementById("flag-template-group");
  if (group) {
    group.style.display = mode === "dynamic" ? "" : "none";
  }
}

(function () {
  var flagMode = document.getElementById("flag_mode");
  if (!flagMode) {
    return;
  }
  flagMode.addEventListener("change", toggleFlagTemplate);
  toggleFlagTemplate();
})();
