const $ = (id) => document.getElementById(id);

function formatTime(totalSeconds) {
  if (totalSeconds <= 0) return "00:00";
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function updateUI(data) {
  if (!data) return;
  const { cfg, ruleCache, currentUrl, evaluation } = data;

  // 1. Connection status
  const isOnline = ruleCache && ruleCache.connected && cfg && Boolean(cfg.token);
  const connPill = $("connectionPill");
  const connText = $("connectionText");
  if (isOnline) {
    connPill.className = "status-pill online";
    connText.textContent = "Connected";
  } else {
    connPill.className = "status-pill offline";
    connText.textContent = cfg && cfg.token ? "App Offline" : "Not Paired";
  }

  // 2. Focus state
  const focusCard = $("focusCard");
  const focusTitle = $("focusStatusTitle");
  const focusTimer = $("focusTimer");
  const focusSubtext = $("focusSubtext");
  const focusTag = $("focusModeTag");

  if (ruleCache && ruleCache.focus_active) {
    focusCard.className = "card focus-card active";
    focusTag.textContent = ruleCache.mode || "Focus";
    focusTitle.textContent = "Focus Mode Active";
    focusTimer.textContent = formatTime(ruleCache.seconds_remaining);
    focusSubtext.textContent = "Sub-path rules & distraction limits actively enforced.";
  } else {
    focusCard.className = "card focus-card";
    focusTag.textContent = ruleCache ? ruleCache.mode || "Standard" : "Standard";
    focusTitle.textContent = "No Active Session";
    focusTimer.textContent = "--:--";
    focusSubtext.textContent = "Start a session in the desktop app to lock distracting feeds.";
  }

  // 3. Tab state
  const tabDomain = $("tabDomain");
  const tabReason = $("tabReason");
  const tabBadge = $("tabDecisionBadge");

  if (!currentUrl) {
    tabDomain.textContent = "New Tab";
    tabReason.textContent = "Browser home screen";
    tabBadge.textContent = "Normal";
    tabBadge.className = "badge badge-neutral";
  } else {
    try {
      const u = new URL(currentUrl);
      let host = u.hostname.replace(/^www\./, "");
      tabDomain.textContent = `${host}${u.pathname !== "/" ? u.pathname : ""}`;
    } catch (e) {
      tabDomain.textContent = currentUrl.slice(0, 32);
    }

    if (evaluation) {
      if (evaluation.action === "block") {
        tabBadge.textContent = "Blocked";
        tabBadge.className = "badge badge-block";
        tabReason.textContent = evaluation.reason || "Distraction rule applies";
      } else {
        tabBadge.textContent = evaluation.focus_active ? "Protected" : "Allowed";
        tabBadge.className = "badge badge-allow";
        tabReason.textContent = evaluation.reason || "No blocking rules apply";
      }
    } else {
      tabBadge.textContent = "Allowed";
      tabBadge.className = "badge badge-allow";
      tabReason.textContent = "Normal browsing";
    }
  }
}

function refresh() {
  chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
    if (chrome.runtime.lastError) return;
    updateUI(response);
  });
}

$("syncBtn").addEventListener("click", () => {
  const icon = $("syncIcon");
  icon.style.transform = "rotate(360deg)";
  icon.style.transition = "transform 0.4s ease";
  setTimeout(() => {
    icon.style.transform = "none";
    icon.style.transition = "none";
  }, 400);

  chrome.runtime.sendMessage({ type: "SYNC_RULES" }, (response) => {
    refresh();
  });
});

$("optionsBtn").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

refresh();
// Update timer every second locally if focus is active
setInterval(refresh, 2000);
