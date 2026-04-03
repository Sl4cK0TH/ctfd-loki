/**
 * CTFd LOKI — Challenge Creation JS
 *
 * Handles form submission for creating a new Loki challenge.
 * Reuses CTFd's standard challenge creation JS for most behaviour;
 * this file adds Loki-specific field handling.
 */

// Toggle flag template visibility on page load
document.addEventListener("DOMContentLoaded", function () {
  var flagMode = document.getElementById("flag_mode");
  if (flagMode) {
    flagMode.addEventListener("change", function () {
      var group = document.getElementById("flag-template-group");
      if (group) {
        group.style.display = flagMode.value === "dynamic" ? "" : "none";
      }
    });
  }
});
