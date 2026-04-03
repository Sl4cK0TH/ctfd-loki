/**
 * CTFd LOKI — Challenge Creation JS
 */

if (window.$ === undefined && window.CTFd && window.CTFd.lib) {
  window.$ = window.CTFd.lib.$;
}

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
