/**
 * Digital Wellbeing — Companion Extension Service Worker (Manifest V3)
 *
 * Provides ultra-fast local sub-path rule evaluation, badge countdowns,
 * active tab reporting to 127.0.0.1, and zero-config loopback pairing.
 * Completely local, fail-open design: browsing is never interrupted if
 * the desktop app is offline.
 */

const DEFAULT_PORT = 47823;
const BLOCKED_PAGE = "blocked.html";

let cachedConfig = null;
let ruleCache = {
  focus_active: false,
  mode: "custom",
  seconds_remaining: 0,
  rules: [],
  blocked_domains: [],
  revision: 0,
  lastSync: 0,
  connected: false,
};
let lastHeartbeat = 0;
let lastEvaluatedUrl = "";

// ── Configuration & Storage ────────────────────────────────────────────────

async function getConfig() {
  if (cachedConfig) return cachedConfig;
  const stored = await chrome.storage.local.get([
    "dwPort",
    "dwToken",
    "dwEnabled",
    "dwFeedShield",
    "dwRuleCache",
  ]);
  cachedConfig = {
    port: Number(stored.dwPort) || DEFAULT_PORT,
    token: String(stored.dwToken || ""),
    enabled: stored.dwEnabled !== false,
    feedShield: stored.dwFeedShield !== false,
  };
  if (stored.dwRuleCache) {
    ruleCache = { ...ruleCache, ...stored.dwRuleCache };
  }
  return cachedConfig;
}

chrome.storage.onChanged.addListener((changes) => {
  if (changes.dwPort || changes.dwToken || changes.dwEnabled || changes.dwFeedShield) {
    cachedConfig = null;
    syncRules(true);
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
  if (/Brave/i.test(ua)) return "brave.exe";
  return "chrome.exe";
}

function parseHostAndPath(urlString) {
  try {
    const parsed = new URL(urlString);
    let host = (parsed.hostname || "").toLowerCase().trim();
    if (host.startsWith("www.")) {
      host = host.slice(4);
    }
    const path = (parsed.pathname || "/").toLowerCase();
    return { host, path };
  } catch (err) {
    return { host: "", path: "" };
  }
}

// ── Fast In-Memory Rule Evaluation (<0.1ms) ────────────────────────────────

function evaluateUrlLocally(urlString) {
  if (!isWebUrl(urlString) || isExtensionPage(urlString)) {
    return { action: "allow", reason: "Internal or non-web page" };
  }

  const { host, path } = parseHostAndPath(urlString);
  if (!host) {
    return { action: "allow", reason: "Invalid host" };
  }

  // Sub-path and domain rules apply while a Focus session is active
  if (!ruleCache.focus_active) {
    return { action: "allow", reason: "Focus session inactive", focus_active: false };
  }

  // 1. Most-specific sub-path rule evaluation
  // Rules are sorted by pattern length descending
  const rules = (ruleCache.rules || []).slice().sort((a, b) => (b.pattern || "").length - (a.pattern || "").length);
  for (const rule of rules) {
    if (!rule.enabled && rule.enabled !== undefined) continue;
    let pat = (rule.pattern || "").toLowerCase().trim();
    if (pat.startsWith("http://") || pat.startsWith("https://")) {
      try {
        const u = new URL(pat);
        pat = (u.hostname || "") + (u.pathname || "");
      } catch (e) {}
    }
    if (pat.startsWith("www.")) {
      pat = pat.slice(4);
    }
    const slashIdx = pat.indexOf("/");
    const ruleHost = slashIdx >= 0 ? pat.slice(0, slashIdx) : pat;
    const rulePath = slashIdx >= 0 ? pat.slice(slashIdx) : "";

    // Host must match exact or be a subdomain
    const hostMatch = host === ruleHost || host.endsWith("." + ruleHost);
    if (!hostMatch) continue;

    // Path prefix match
    if (rulePath) {
      if (path === rulePath || path.startsWith(rulePath + "/") || path.startsWith(rulePath)) {
        return {
          action: rule.action === "allow" ? "allow" : "block",
          reason: rule.label || (rule.action === "block" ? `Rule: ${rule.pattern}` : "Allowed by rule"),
          rule: rule.pattern,
          domain: host,
          focus_active: true,
        };
      }
    } else {
      // Entire host rule
      return {
        action: rule.action === "allow" ? "allow" : "block",
        reason: rule.label || (rule.action === "block" ? `Rule: ${rule.pattern}` : "Allowed by rule"),
        rule: rule.pattern,
        domain: host,
        focus_active: true,
      };
    }
  }

  // 2. Focus mode blocked domains check
  const blocked = ruleCache.blocked_domains || [];
  for (const b of blocked) {
    let bNorm = (b || "").toLowerCase().trim();
    if (bNorm.startsWith("www.")) bNorm = bNorm.slice(4);
    if (bNorm && (host === bNorm || host.endsWith("." + bNorm))) {
      return {
        action: "block",
        reason: `Blocked during ${ruleCache.mode || "Focus"} mode`,
        rule: bNorm,
        domain: host,
        focus_active: true,
      };
    }
  }

  return { action: "allow", reason: "Allowed", domain: host, focus_active: true };
}

// ── Bridge Communication & Sync ─────────────────────────────────────────────

async function syncRules(force = false) {
  const cfg = await getConfig();
  if (!cfg.enabled || !cfg.token) {
    updateBadge(false);
    return false;
  }

  const now = Date.now();
  if (!force && now - ruleCache.lastSync < 8000) {
    return true;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2000);
  try {
    const res = await fetch(`http://127.0.0.1:${cfg.port}/v1/rules`, {
      headers: { "X-DW-Token": cfg.token },
      signal: controller.signal,
    });
    if (!res.ok) {
      ruleCache.connected = false;
      return false;
    }
    const data = await res.json();
    ruleCache = {
      ...ruleCache,
      focus_active: Boolean(data.focus_active),
      mode: data.mode || "custom",
      seconds_remaining: Number(data.seconds_remaining) || 0,
      session_total_seconds: Number(data.session_total_seconds) || 0,
      rules: Array.isArray(data.rules) ? data.rules : [],
      blocked_domains: Array.isArray(data.blocked_domains) ? data.blocked_domains : [],
      revision: data.revision || 0,
      lastSync: now,
      connected: true,
    };
    await chrome.storage.local.set({ dwRuleCache: ruleCache });
    updateBadge(ruleCache.focus_active, ruleCache.seconds_remaining);
    return true;
  } catch (err) {
    ruleCache.connected = false;
    return false;
  } finally {
    clearTimeout(timer);
  }
}

async function sendHeartbeat(url, title) {
  const cfg = await getConfig();
  if (!cfg.enabled || !cfg.token || !isWebUrl(url)) return;

  const now = Date.now();
  if (now - lastHeartbeat < 1500 && lastEvaluatedUrl === url) return;
  lastHeartbeat = now;
  lastEvaluatedUrl = url;

  try {
    const res = await fetch(`http://127.0.0.1:${cfg.port}/v1/heartbeat`, {
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
      signal: AbortSignal.timeout(1500),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.revision !== undefined && data.revision !== ruleCache.revision) {
        syncRules(true);
      }
    }
  } catch (err) {
    // Fail-open
  }
}

function updateBadge(focusActive, secondsRemaining = 0) {
  if (!focusActive) {
    chrome.action.setBadgeText({ text: "" });
    return;
  }
  const mins = Math.max(1, Math.ceil(secondsRemaining / 60));
  const text = secondsRemaining > 0 ? `${mins}m` : "ON";
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color: "#10b981" }); // Emerald green
}

// ── Tab Enforcement ────────────────────────────────────────────────────────

async function enforce(tabId, url, title) {
  if (!isWebUrl(url) || isExtensionPage(url)) return;

  const cfg = await getConfig();
  if (!cfg.enabled) return;

  // 1. Fast local evaluation (sub-millisecond)
  const decision = evaluateUrlLocally(url);

  if (decision.action === "block") {
    try {
      const tab = await chrome.tabs.get(tabId);
      if (!tab || tab.url !== url) return;
    } catch (e) {
      return;
    }
    const params = new URLSearchParams({
      reason: decision.reason || "Blocked by Focus rules",
      url,
      rule: decision.rule || "",
    });
    chrome.tabs.update(tabId, {
      url: chrome.runtime.getURL(`${BLOCKED_PAGE}?${params.toString()}`),
    });
    return;
  }

  // 2. Send lightweight tab heartbeat for desktop activity tracking
  sendHeartbeat(url, title);
}

// Tab navigation listeners
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!tab.active) return;
  const url = changeInfo.url || (changeInfo.status === "complete" ? tab.url : "");
  if (!url) return;
  enforce(tabId, url, tab.title || "");
});

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (tab && tab.url) {
      enforce(tabId, tab.url, tab.title || "");
    }
  } catch (e) {}
});

// Periodic background sync and badge update
chrome.alarms.create("dw-sync-alarm", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "dw-sync-alarm") {
    syncRules();
  }
});

// ── Messaging for Popup & Options ──────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "GET_STATUS") {
    getConfig().then((cfg) => {
      chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
        const currentTab = tabs && tabs[0] ? tabs[0] : null;
        const currentUrl = currentTab ? currentTab.url : "";
        const evaluation = currentUrl ? evaluateUrlLocally(currentUrl) : null;
        sendResponse({
          cfg,
          ruleCache,
          currentUrl,
          currentTitle: currentTab ? currentTab.title : "",
          evaluation,
        });
      });
    });
    return true; // async
  }

  if (msg.type === "SYNC_RULES") {
    syncRules(true).then((ok) => {
      sendResponse({ ok, ruleCache });
    });
    return true;
  }

  if (msg.type === "AUTO_PAIR") {
    const port = Number(msg.port) || DEFAULT_PORT;
    const code = String(msg.code || "").trim();
    const auto = Boolean(msg.auto);

    fetch(`http://127.0.0.1:${port}/v1/pair`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, auto }),
      signal: AbortSignal.timeout(3000),
    })
      .then((res) => res.json())
      .then(async (data) => {
        if (data.ok && data.token) {
          await chrome.storage.local.set({
            dwPort: Number(data.port) || port,
            dwToken: data.token,
            dwEnabled: true,
          });
          cachedConfig = null;
          await syncRules(true);
          sendResponse({ ok: true, port: data.port, token: data.token });
        } else {
          sendResponse({ ok: false, error: data.error || "Pairing failed" });
        }
      })
      .catch((err) => {
        sendResponse({ ok: false, error: "Could not reach desktop app on loopback." });
      });
    return true;
  }
});

// Initial startup sync
chrome.runtime.onInstalled.addListener(() => {
  syncRules(true);
});

syncRules(true);
