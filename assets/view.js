/**
 * CTFd LOKI — Player View JS
 *
 * Handles container lifecycle (start / stop / renew) and displays
 * connection info with a live countdown timer.
 */

/* ── Globals ─────────────────────────────────────────────── */

var LOKI_CHALLENGE_ID = parseInt(
  (document.getElementById("challenge-id") || {}).value ||
    (document.querySelector("[data-challenge-id]") || {}).dataset
      ?.challengeId ||
    0
);
var _lokiTimer = null;
var _lokiRemaining = 0;

/* ── UI Helpers ──────────────────────────────────────────── */

function _show(id) {
  document.getElementById(id).style.display = "";
}
function _hide(id) {
  document.getElementById(id).style.display = "none";
}

function lokiCopy(el) {
  navigator.clipboard.writeText(el.innerText).then(function () {
    var orig = el.title;
    el.title = "Copied!";
    setTimeout(function () {
      el.title = orig;
    }, 1500);
  });
}

function _showRunning(data) {
  document.getElementById("loki-access").innerText = data.user_access || "";
  document.getElementById("loki-renew-count").innerText =
    data.renew_count || 0;

  _lokiRemaining = data.remaining_time || 0;
  _startCountdown();

  _show("loki-connection");
  _show("loki-stop-btn");
  _show("loki-renew-btn");
  _hide("loki-start-btn");
  _hide("loki-spinner");
  _hide("loki-error");
}

function _showStopped() {
  _stopCountdown();
  _hide("loki-connection");
  _hide("loki-stop-btn");
  _hide("loki-renew-btn");
  _show("loki-start-btn");
  _hide("loki-spinner");
}

function _showError(msg) {
  var el = document.getElementById("loki-error");
  el.innerText = msg;
  _show("loki-error");
  _hide("loki-spinner");
  _show("loki-start-btn");
}

function _showLoading() {
  _hide("loki-start-btn");
  _hide("loki-stop-btn");
  _hide("loki-renew-btn");
  _hide("loki-error");
  _show("loki-spinner");
}

/* ── Countdown Timer ─────────────────────────────────────── */

function _formatTime(secs) {
  if (secs <= 0) return "00:00";
  var m = Math.floor(secs / 60);
  var s = secs % 60;
  return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
}

function _startCountdown() {
  _stopCountdown();
  _updateTimerDisplay();
  _lokiTimer = setInterval(function () {
    _lokiRemaining--;
    _updateTimerDisplay();
    if (_lokiRemaining <= 0) {
      _stopCountdown();
      _showStopped();
    }
  }, 1000);
}

function _updateTimerDisplay() {
  var el = document.getElementById("loki-timer");
  if (el) el.innerText = _formatTime(_lokiRemaining);
}

function _stopCountdown() {
  if (_lokiTimer) {
    clearInterval(_lokiTimer);
    _lokiTimer = null;
  }
}

/* ── API Calls ───────────────────────────────────────────── */

function _apiCall(method, callback) {
  var xhr = new XMLHttpRequest();
  var url =
    "/api/v1/plugins/ctfd-loki/container?challenge_id=" + LOKI_CHALLENGE_ID;
  xhr.open(method, url, true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", init.csrfNonce);

  xhr.onload = function () {
    var resp;
    try {
      resp = JSON.parse(xhr.responseText);
    } catch (e) {
      callback({ success: false, message: "Invalid server response" });
      return;
    }
    callback(resp, xhr.status);
  };

  xhr.onerror = function () {
    callback({ success: false, message: "Network error" });
  };

  xhr.send();
}

function lokiStart() {
  _showLoading();
  var xhr = new XMLHttpRequest();
  var url =
    "/api/v1/plugins/ctfd-loki/container?challenge_id=" + LOKI_CHALLENGE_ID;
  xhr.open("POST", url, true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", init.csrfNonce);

  xhr.onload = function () {
    var resp;
    try {
      resp = JSON.parse(xhr.responseText);
    } catch (e) {
      _showError("Invalid server response");
      return;
    }
    if (xhr.status === 200 && resp.success) {
      // Re-fetch to get connection info
      lokiCheckStatus();
    } else {
      _showError(resp.message || "Failed to start instance");
    }
  };
  xhr.onerror = function () {
    _showError("Network error");
  };
  xhr.send();
}

function lokiStop() {
  _showLoading();
  var xhr = new XMLHttpRequest();
  var url =
    "/api/v1/plugins/ctfd-loki/container?challenge_id=" + LOKI_CHALLENGE_ID;
  xhr.open("DELETE", url, true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", init.csrfNonce);

  xhr.onload = function () {
    _showStopped();
  };
  xhr.onerror = function () {
    _showError("Network error");
  };
  xhr.send();
}

function lokiRenew() {
  _showLoading();
  var xhr = new XMLHttpRequest();
  var url =
    "/api/v1/plugins/ctfd-loki/container?challenge_id=" + LOKI_CHALLENGE_ID;
  xhr.open("PATCH", url, true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", init.csrfNonce);

  xhr.onload = function () {
    var resp;
    try {
      resp = JSON.parse(xhr.responseText);
    } catch (e) {
      _showError("Invalid server response");
      return;
    }
    if (resp.success) {
      lokiCheckStatus();
    } else {
      _showError(resp.message || "Failed to renew");
      _show("loki-stop-btn");
      _show("loki-renew-btn");
    }
  };
  xhr.onerror = function () {
    _showError("Network error");
  };
  xhr.send();
}

function lokiCheckStatus() {
  _apiCall("GET", function (resp, status) {
    if (resp.success && resp.data && resp.data.user_access) {
      _showRunning(resp.data);
    } else {
      _showStopped();
    }
  });
}

/* ── On Page Load ────────────────────────────────────────── */

(function () {
  lokiCheckStatus();
})();
