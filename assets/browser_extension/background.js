/**
 * Digital Wellbeing — local Web Rules bridge client.
 *
 * Sends only the current tab URL to 127.0.0.1 when the tab changes or is
 * activated. If the app says "block", the tab is redirected to a local
 * blocked.html page. Everything fails open: if the app is closed, browsing is
 * never interrupted.
 */
const DEFAULT_PORT = 47823;
const BLOCKED_PAGE = "blocked.html";

let cachedConfig = null;
let lastChecked = new Map();

async function getConfig() {
  if (cachedConfig) return cachedConfig;
  const stored = await chrome.storage.local.get([
    "dwPort",
    "dwToken",
    "dwEnabled",
  ]);
  cachedConfig = {
    port: Number(stored.dwPort) || DEFAULT_PORT,
    token: String(stored.dwToken || ""),
    enabled: stored.dwEnabled !== false,
  };
  return cachedConfig;
}

// Invalidate the cache when the options page saves new credentials.
chrome.storage.onChanged.addListener((changes) => {
  if (changes.dwPort || changes.dwToken || changes.dwEnabled) {
    cachedConfig = null;
  }
});

function isWebUrl(url) {
  return /^https?:\/\//i.test(url || "");
}

function isExtensionPage(url) {
  return (url || "").startsWith(chrome.runtime.getURL(""));
}

function browserExecutable() {
  const ua = navigator.userAgent || "";
  if (/Edg\//.test(ua)) return "msedge.exe";
  if (/OPR\//.test(ua)) return "opera.exe";
  if (/Vivaldi\//.test(ua)) return "vivaldi.exe";
  if (/Firefox\//.test(ua)) return "firefox.exe";
  return "chrome.exe";
}

async function checkUrl(url, title) {
  const cfg = await getConfig();
  if (!cfg.enabled || !cfg.token || !isWebUrl(url)) return null;

  // Debounce repeated events for the same URL (onUpdated can fire several
  // times for one navigation).
  const previous = lastChecked.get(url);
  if (previous && Date.now() - previous < 1200) return null;
  lastChecked.set(url, Date.now());
  if (lastChecked.size > 50) lastChecked.clear();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1500);
  try {
    const response = await fetch(`http://127.0.0.1:${cfg.port}/v1/check`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-DW-Token": cfg.token,
      },
      body: JSON.stringify({
        url,
        title: title || "",
        browser: browserExecutable(),
      }),
      signal: controller.signal,
    });
    if (!response.ok) return null;
    return await response.json();
  } catch (error) {
    // App closed / bridge down: fail open silently.
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

async function enforce(tabId, url, title) {
  if (!isWebUrl(url) || isExtensionPage(url)) return;
  const decision = await checkUrl(url, title);
  if (!decision || decision.action !== "block") return;

  // Re-check the tab still points at the same URL before redirecting (the
  // user may have navigated away while the request was in flight).
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab || tab.url !== url) return;
  } catch (error) {
    return;
  }

  const params = new URLSearchParams({
    reason: decision.reason || "Blocked by Focus rules",
    url,
  });
  await chrome.tabs.update(tabId, {
    url: chrome.runtime.getURL(`${BLOCKED_PAGE}?${params.toString()}`),
  });
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!tab.active) return;
  const url = changeInfo.url || (changeInfo.status === "complete" ? tab.url : "");
  if (!url) return;
  enforce(tabId, url, tab.title || "");
});

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (tab && tab.url) enforce(tabId, tab.url, tab.title || "");
  } catch (error) {
    /* tab gone */
  }
});

// Periodic recheck catches rule edits while a page stays open.
chrome.alarms.create("dw-recheck", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "dw-recheck") return;
  try {
    const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (tabs[0] && tabs[0].url) {
      enforce(tabs[0].id, tabs[0].url, tabs[0].title || "");
    }
  } catch (error) {
    /* ignore */
  }
});

chrome.runtime.onInstalled.addListener(async () => {
  const cfg = await getConfig();
  if (!cfg.token) {
    chrome.runtime.openOptionsPage();
  }
});
