/**
 * CTFd LOKI — Challenge Update JS
 *
 * Pre-populates Loki-specific fields when the update modal loads,
 * and handles the flag template toggle.
 */

document.addEventListener("DOMContentLoaded", function () {
  // Toggle flag template visibility
  var flagMode = document.getElementById("flag_mode");
  if (flagMode) {
    toggleFlagTemplate();
    flagMode.addEventListener("change", toggleFlagTemplate);
  }
});

function toggleFlagTemplate() {
  var mode = document.getElementById("flag_mode").value;
  var group = document.getElementById("flag-template-group");
  if (group) {
    group.style.display = mode === "dynamic" ? "" : "none";
  }
}
