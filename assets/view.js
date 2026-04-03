CTFd._internal.challenge.data = undefined;

CTFd._internal.challenge.preRender = function () {};
CTFd._internal.challenge.postRender = function () {
  lokiLoadInfo();
};
CTFd._internal.challenge.render = CTFd.lib.markdown();

if (window.$ === undefined) {
  window.$ = CTFd.lib.$;
}

var lokiTimer = null;

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
}

function lokiSetStartedState(responseData) {
  var renewCount = responseData.renew_count || 0;
  var remaining = parseInt(responseData.remaining_time || 0);

  $("#loki-challenge-user-access").text(responseData.user_access || "");
  $("#loki-renew-count").text(renewCount);
  $("#loki-challenge-count-down").text(remaining);

  $("#loki-panel-stopped").hide();
  $("#loki-panel-started").show();

  lokiClearTimer();
  lokiTimer = setInterval(function () {
    var current = parseInt($("#loki-challenge-count-down").text() || "0");
    var next = current - 1;
    if (next <= 0) {
      lokiLoadInfo();
      return;
    }
    $("#loki-challenge-count-down").text(next);
  }, 1000);
}

function lokiSetStoppedState() {
  lokiClearTimer();
  $("#loki-panel-started").hide();
  $("#loki-panel-stopped").show();
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
      lokiSetStoppedState();
    });
}

CTFd._internal.challenge.boot = function () {
  var button = $("#loki-button-boot");
  button.text("Starting...");
  button.prop("disabled", true);

  lokiRequest("POST")
    .then(function (response) {
      if (response.success) {
        lokiLoadInfo();
      } else {
        lokiAlert("Spawn Failed", response.message || "Failed to start instance");
      }
    })
    .catch(function () {
      lokiAlert("Spawn Failed", "Failed to start instance");
    })
    .finally(function () {
      button.text("Start Instance");
      button.prop("disabled", false);
    });
};

CTFd._internal.challenge.destroy = function () {
  var button = $("#loki-button-destroy");
  button.text("Stopping...");
  button.prop("disabled", true);

  lokiRequest("DELETE")
    .then(function (response) {
      if (response.success) {
        lokiLoadInfo();
      } else {
        lokiAlert("Stop Failed", response.message || "Failed to stop instance");
      }
    })
    .catch(function () {
      lokiAlert("Stop Failed", "Failed to stop instance");
    })
    .finally(function () {
      button.text("Stop Instance");
      button.prop("disabled", false);
    });
};

CTFd._internal.challenge.renew = function () {
  var button = $("#loki-button-renew");
  button.text("Renewing...");
  button.prop("disabled", true);

  lokiRequest("PATCH")
    .then(function (response) {
      if (response.success) {
        lokiLoadInfo();
      } else {
        lokiAlert("Renew Failed", response.message || "Failed to renew instance");
      }
    })
    .catch(function () {
      lokiAlert("Renew Failed", "Failed to renew instance");
    })
    .finally(function () {
      button.text("Renew Instance");
      button.prop("disabled", false);
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
