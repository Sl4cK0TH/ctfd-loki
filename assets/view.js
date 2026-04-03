CTFd._internal.challenge.data = undefined;

CTFd._internal.challenge.preRender = function () {};
CTFd._internal.challenge.postRender = function () {
  lokiLoadInfo();
};

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

CTFd._internal.challenge.render = lokiRenderText;

if (window.$ === undefined) {
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
  if (parsed.password) {
    $("#loki-connection-password").val(parsed.password);
    $("#loki-password-group").show();
  } else {
    $("#loki-connection-password").val("");
    $("#loki-password-group").hide();
  }
  $("#loki-renew-count").text(renewCount);
  $("#loki-challenge-count-down").text(lokiFormatDuration(remaining));

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
  $("#loki-panel-started").hide();
  $("#loki-panel-stopped").show();
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

  lokiCopyText(text, "Connection copied to clipboard.");
}

function lokiCopyPasswordInfo() {
  var text = $("#loki-connection-password").val() || "";
  if (!text.trim()) {
    return;
  }

  lokiCopyText(text, "Password copied to clipboard.");
}

function lokiCopyText(text, successMessage) {
  if (!text.trim()) {
    return;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function () {
      CTFd._functions.events.eventAlert({
        title: "Copied",
        html: successMessage,
        button: "OK",
      });
    });
    return;
  }

  var ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
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

$(document).off("click", "#loki-copy-password");
$(document).on("click", "#loki-copy-password", function () {
  lokiCopyPasswordInfo();
});

CTFd._internal.challenge.boot = function () {
  var button = $("#loki-button-boot");
  button.text("Starting...");
  lokiSetActionButtonsDisabled(true);

  lokiRequest("POST")
    .then(function (response) {
      if (response.success) {
        var delay =
          response.data && response.data.start_delay_seconds
            ? response.data.start_delay_seconds
            : 0;
        button.text(delay > 0 ? "Starting..." : "Start Instance");
        lokiScheduleReload(delay);
      } else {
        lokiAlert("Spawn Failed", response.message || "Failed to start instance");
        lokiSetActionButtonsDisabled(false);
      }
    })
    .catch(function () {
      lokiAlert("Spawn Failed", "Failed to start instance");
      lokiSetActionButtonsDisabled(false);
    })
    .finally(function () {
      if (lokiPendingTimer === null) {
        button.text("Start Instance");
      }
    });
};

CTFd._internal.challenge.destroy = function () {
  var button = $("#loki-button-destroy");
  button.text("Stopping...");
  lokiSetActionButtonsDisabled(true);

  lokiRequest("DELETE")
    .then(function (response) {
      if (response.success) {
        var delay =
          response.data && response.data.stop_delay_seconds
            ? response.data.stop_delay_seconds
            : 0;
        button.text(delay > 0 ? "Stopping..." : "Stop Instance");
        lokiScheduleReload(delay);
      } else {
        lokiAlert("Stop Failed", response.message || "Failed to stop instance");
        lokiSetActionButtonsDisabled(false);
      }
    })
    .catch(function () {
      lokiAlert("Stop Failed", "Failed to stop instance");
      lokiSetActionButtonsDisabled(false);
    })
    .finally(function () {
      if (lokiPendingTimer === null) {
        button.text("Stop Instance");
      }
    });
};

CTFd._internal.challenge.renew = function () {
  var button = $("#loki-button-renew");
  button.text("Renewing...");
  lokiSetActionButtonsDisabled(true);

  lokiRequest("PATCH")
    .then(function (response) {
      if (response.success) {
        lokiLoadInfo();
      } else {
        lokiAlert("Renew Failed", response.message || "Failed to renew instance");
        lokiSetActionButtonsDisabled(false);
      }
    })
    .catch(function () {
      lokiAlert("Renew Failed", "Failed to renew instance");
      lokiSetActionButtonsDisabled(false);
    })
    .finally(function () {
      button.text("Renew Instance");
      if (lokiPendingTimer === null) {
        lokiSetActionButtonsDisabled(false);
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
  return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
    return response;
  });
};
