/**
 * CTFd LOKI — Challenge Creation JS
 */

function lokiToggleFlagTemplate() {
  var flagMode = document.getElementById("flag_mode");
  var group = document.getElementById("flag-template-group");
  if (!flagMode || !group) {
    return;
  }
  group.style.display = flagMode.value === "dynamic" ? "" : "none";
}

(function () {
  var flagMode = document.getElementById("flag_mode");
  if (!flagMode) {
    return;
  }
  flagMode.addEventListener("change", lokiToggleFlagTemplate);
  lokiToggleFlagTemplate();
})();
