/**
 * CTFd LOKI — Challenge Update JS
 *
 * Pre-populates Loki-specific fields when the update modal loads,
 * and handles the flag template toggle.
 */

if (window.$ === undefined && window.CTFd && window.CTFd.lib) {
  window.$ = window.CTFd.lib.$;
}

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

if (window.$) {
  $("#desc-edit").on("shown.bs.tab", function (event) {
    if (event.target.hash === "#desc-preview" && window.challenge && window.challenge.render) {
      var editorValue = $("#desc-editor").val();
      $(event.target.hash).html(window.challenge.render(editorValue));
    }
  });

  $("#new-desc-edit").on("shown.bs.tab", function (event) {
    if (event.target.hash === "#new-desc-preview" && window.challenge && window.challenge.render) {
      var editorValue = $("#new-desc-editor").val();
      $(event.target.hash).html(window.challenge.render(editorValue));
    }
  });
}
