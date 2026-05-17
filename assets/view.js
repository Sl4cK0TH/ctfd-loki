CTFd._internal.challenge = CTFd._internal.challenge || {};

var lokiChallenge = CTFd._internal.challenge;
if (window.challenge && window.challenge !== lokiChallenge) {
  lokiChallenge = window.challenge;
  CTFd._internal.challenge = lokiChallenge;
} else if (!window.challenge) {
  window.challenge = lokiChallenge;
}

lokiChallenge.data = undefined;

// TODO: Remove in CTFd v4.0
lokiChallenge.renderer = null;

lokiChallenge.preRender = function () {};

function lokiRenderText(text) {
  return text;
}

if (CTFd.lib && typeof CTFd.lib.markdown === "function") {
  try {
    var md = CTFd.lib.markdown();
    if (typeof md === "function") {
      lokiRenderText = md;
    } else if (md && typeof md.render === "function") {
      lokiRenderText = function (text) {
        return md.render(text);
      };
    }
  } catch (e) {
    lokiRenderText = function (text) {
      return text;
    };
  }
}

// TODO: Remove in CTFd v4.0
lokiChallenge.render = lokiRenderText;

lokiChallenge.postRender = function () {
  lokiLoadInfo();
};

if (window.$ === undefined && CTFd.lib && CTFd.lib.$) {
  window.$ = CTFd.lib.$;
}

var lokiTimer = null;
var lokiPendingTimer = null;

function lokiFormatDuration(totalSeconds) {
  var seconds = parseInt(totalSeconds || 0);
  if (Number.isNaN(seconds) || seconds < 0) {
    seconds = 0;
  }
  var mins = Math.floor(seconds / 60);
  var secs = seconds % 60;
  var padded = secs < 10 ? "0" + secs : String(secs);
  return mins + "m " + padded + "s";
}

function lokiChallengeId() {
  return CTFd._internal.challenge.data.id;
}

function lokiContainerUrl() {
  return "/api/v1/plugins/ctfd-loki/container?challenge_id=" + lokiChallengeId();
}

function lokiClearTimer() {
  if (lokiTimer !== null) {
    clearInterval(lokiTimer);
    lokiTimer = null;
  }

  if (lokiPendingTimer !== null) {
    clearTimeout(lokiPendingTimer);
    lokiPendingTimer = null;
  }
}

function lokiSetActionButtonsDisabled(disabled) {
  $("#loki-button-boot").prop("disabled", disabled);
  $("#loki-button-destroy").prop("disabled", disabled);
  $("#loki-button-renew").prop("disabled", disabled);
}

function lokiSetButtonLoading(buttonId, spinnerId, isLoading) {
  var button = $(buttonId);
  var spinner = $(spinnerId);
  if (isLoading) {
    button.hide();
    spinner.show();
  } else {
    spinner.hide();
    button.show();
  }
}

function lokiSetStartedActionLoading(isLoading) {
  if (isLoading) {
    $("#loki-button-destroy").hide();
    $("#loki-button-renew").hide();
    $("#loki-started-action-loading").show();
  } else {
    $("#loki-started-action-loading").hide();
    $("#loki-button-destroy").show();
    $("#loki-button-renew").show();
  }
}

function lokiScheduleReload(seconds) {
  var delay = parseInt(seconds || 0);
  if (Number.isNaN(delay) || delay < 0) {
    delay = 0;
  }
  lokiPendingTimer = setTimeout(function () {
    lokiPendingTimer = null;
    lokiLoadInfo();
  }, delay * 1000);
}

function lokiSetStartedState(responseData) {
  var renewCount = responseData.renew_count || 0;
  var remaining = parseInt(responseData.remaining_time || 0);
  var parsed = lokiParseAccessInfo(responseData.user_access || "");

  $("#loki-connection-command").val(parsed.command);
  $("#loki-connection-text").text(parsed.command);
  if (parsed.password) {
    $("#loki-connection-password").val(parsed.password);
    $("#loki-password-group").show();
  } else {
    $("#loki-connection-password").val("");
    $("#loki-password-group").hide();
  }
  $("#loki-renew-count").text(renewCount);
  $("#loki-challenge-count-down").text(lokiFormatDuration(remaining));

  $("#loki-status-active").css("display", "flex");
  $("#loki-connection-inline").css("display", "flex");
  $("#loki-button-boot-loading").hide();
  $("#loki-panel-stopped").hide();
  $("#loki-panel-started").show();
  lokiSetActionButtonsDisabled(false);

  lokiClearTimer();
  lokiTimer = setInterval(function () {
    var current = parseInt(responseData.remaining_time || 0);
    current = current - 1;
    responseData.remaining_time = current;
    var next = current;
    if (next <= 0) {
      lokiLoadInfo();
      return;
    }
    $("#loki-challenge-count-down").text(lokiFormatDuration(next));
  }, 1000);
}

function lokiSetStoppedState() {
  lokiClearTimer();
  $("#loki-status-active").hide();
  $("#loki-connection-inline").hide();
  $("#loki-panel-started").hide();
  $("#loki-panel-stopped").show();
  $("#loki-button-boot").text("Start Challenge");
  $("#loki-spinner").removeClass("text-danger").addClass("text-primary");
  $("#loki-starting-text").text("Challenge is spawning. Please stand by...");
  lokiSetButtonLoading("#loki-button-boot", "#loki-button-boot-loading", false);
  lokiSetStartedActionLoading(false);
  lokiSetActionButtonsDisabled(false);
}

function lokiAlert(title, message) {
  CTFd._functions.events.eventAlert({
    title: title,
    html: message,
    button: "OK",
  });
}

function lokiRequest(method) {
  return CTFd.fetch(lokiContainerUrl(), {
    method: method,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  }).then(function (response) {
    return response.json();
  });
}

function lokiLoadInfo() {
  if (!CTFd._internal.challenge.data || !CTFd._internal.challenge.data.id) {
    return;
  }

  CTFd.fetch(lokiContainerUrl(), {
    method: "GET",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
  })
    .then(function (response) {
      return response.json();
    })
    .then(function (response) {
      var data = response.success ? response.data : null;
      if (data && data.user_access) {
        lokiSetStartedState(data);
      } else {
        lokiSetStoppedState();
      }
    })
    .catch(function () {
      // Keep current state on transient errors to avoid hiding active instances.
    });
}

function lokiCopyAccessInfo() {
  var text = $("#loki-connection-command").val() || "";
  if (!text.trim()) {
    return;
  }

  lokiCopyText(text, null);
  lokiFlashInlineCopy();
}

function lokiCopyPasswordInfo() {
  var text = $("#loki-connection-password").val() || "";
  if (!text.trim()) {
    return;
  }

  lokiCopyText(text, "#loki-copy-password");
}

function lokiShowCopySuccess(buttonSelector) {
  var button = $(buttonSelector);
  if (!button.length) {
    return;
  }

  button.data("original-html", button.html());
  button.prop("disabled", true);
  button.html('<i class="fas fa-check text-success" aria-hidden="true"></i>');

  setTimeout(function () {
    var original = button.data("original-html") || "Copy";
    button.html(original);
    button.prop("disabled", false);
  }, 900);
}

function lokiFlashInlineCopy() {
  var inline = $("#loki-connection-inline");
  if (!inline.length) {
    return;
  }
  inline.find(".loki-copy-hint").text("Copied");
  inline.addClass("loki-copied");
  setTimeout(function () {
    inline.removeClass("loki-copied");
    inline.find(".loki-copy-hint").text("Copy");
  }, 900);
}

function lokiCopyText(text, buttonSelector) {
  if (!text.trim()) {
    return;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function () {
      if (buttonSelector) {
        lokiShowCopySuccess(buttonSelector);
      }
    });
    return;
  }

  var ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
  if (buttonSelector) {
    lokiShowCopySuccess(buttonSelector);
  }
}

function lokiParseAccessInfo(raw) {
  var output = {
    command: "",
    password: "",
  };

  var text = String(raw || "").trim();
  if (!text) {
    return output;
  }

  var lines = text.split(/\r?\n/).map(function (line) {
    return line.trim();
  });
  var commandLines = [];

  lines.forEach(function (line) {
    if (/^password\s*:/i.test(line)) {
      output.password = line.replace(/^password\s*:/i, "").trim();
    } else if (line) {
      commandLines.push(line);
    }
  });

  output.command = commandLines.join(" ");
  return output;
}

$(document).off("click", "#loki-copy-connection");
$(document).on("click", "#loki-copy-connection", function () {
  lokiCopyAccessInfo();
});

$(document).off("click", "#loki-connection-inline");
$(document).on("click", "#loki-connection-inline", function () {
  lokiCopyAccessInfo();
});

$(document).off("click", "#loki-connection-text");
$(document).on("click", "#loki-connection-text", function () {
  lokiCopyAccessInfo();
});

$(document).off("click", "#loki-copy-password");
$(document).on("click", "#loki-copy-password", function () {
  lokiCopyPasswordInfo();
});

lokiChallenge.boot = function () {
  var button = $("#loki-button-boot");
  button.text("Start Challenge");
  lokiSetActionButtonsDisabled(true);
  lokiSetButtonLoading("#loki-button-boot", "#loki-button-boot-loading", true);

  lokiRequest("POST")
    .then(function (response) {
      if (response.success) {
        var delay =
          response.data && response.data.start_delay_seconds
            ? response.data.start_delay_seconds
            : 0;
        button.text("Start Challenge");
        lokiScheduleReload(delay);
      } else {
        lokiAlert("Spawn Failed", response.message || "Failed to start instance");
        lokiSetActionButtonsDisabled(false);
        lokiSetButtonLoading(
          "#loki-button-boot",
          "#loki-button-boot-loading",
          false,
        );
      }
    })
    .catch(function () {
      lokiAlert("Spawn Failed", "Failed to start instance");
      lokiSetActionButtonsDisabled(false);
      lokiSetButtonLoading(
        "#loki-button-boot",
        "#loki-button-boot-loading",
        false,
      );
    })
    .finally(function () {
      if (lokiPendingTimer === null) {
        button.text("Start Challenge");
        lokiSetButtonLoading(
          "#loki-button-boot",
          "#loki-button-boot-loading",
          false,
        );
      }
    });
};

lokiChallenge.destroy = function () {
  lokiSetActionButtonsDisabled(true);
  lokiSetStartedActionLoading(true);
  $("#loki-panel-started").hide();
  $("#loki-status-active").hide();
  $("#loki-connection-inline").hide();
  $("#loki-panel-stopped").hide();
  $("#loki-button-boot").hide();
  $("#loki-spinner").removeClass("text-primary").addClass("text-danger");
  $("#loki-starting-text").text("Stopping challenge, please wait...");
  $("#loki-button-boot-loading").show();

  lokiRequest("DELETE")
    .then(function (response) {
      if (response.success) {
        var delay =
          response.data && response.data.stop_delay_seconds
            ? response.data.stop_delay_seconds
            : 0;
        lokiScheduleReload(delay);
      } else {
        lokiAlert("Stop Failed", response.message || "Failed to stop instance");
        lokiSetActionButtonsDisabled(false);
        lokiSetStartedActionLoading(false);
        $("#loki-button-boot-loading").hide();
      }
    })
    .catch(function () {
      lokiAlert("Stop Failed", "Failed to stop instance");
      lokiSetActionButtonsDisabled(false);
      lokiSetStartedActionLoading(false);
      $("#loki-button-boot-loading").hide();
    })
    .finally(function () {
      if (lokiPendingTimer === null) {
        lokiSetStartedActionLoading(false);
      }
    });
};

lokiChallenge.renew = function () {
  var proceed = window.confirm("Renew this instance timer?");
  if (!proceed) {
    return;
  }

  lokiSetActionButtonsDisabled(true);
  lokiSetStartedActionLoading(true);

  lokiRequest("PATCH")
    .then(function (response) {
      if (response.success) {
        lokiLoadInfo();
      } else {
        lokiAlert("Renew Failed", response.message || "Failed to renew instance");
        lokiSetActionButtonsDisabled(false);
        lokiSetStartedActionLoading(false);
      }
    })
    .catch(function () {
      lokiAlert("Renew Failed", "Failed to renew instance");
      lokiSetActionButtonsDisabled(false);
      lokiSetStartedActionLoading(false);
    })
    .finally(function () {
      if (lokiPendingTimer === null) {
        lokiSetActionButtonsDisabled(false);
        lokiSetStartedActionLoading(false);
      }
    });
};

CTFd._internal.challenge.submit = function (preview) {
  var challengeId = lokiChallengeId();
  var submission = $("#challenge-input").val();
  var body = {
    challenge_id: challengeId,
    submission: submission,
  };
  var params = {};
  if (preview) {
    params.preview = true;
  }
  return CTFd.api.post_challenge_attempt(params, body);
};
