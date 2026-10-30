const $ = (id) => document.getElementById(id);

async function load() {
  const stored = await chrome.storage.local.get([
    "dwPort",
    "dwToken",
    "dwEnabled",
    "dwFeedShield",
  ]);
  $("port").value = stored.dwPort || 47823;
  $("token").value = stored.dwToken || "";
  $("enabled").checked = stored.dwEnabled !== false;
  $("feedShield").checked = stored.dwFeedShield !== false;
}

function setStatus(elId, text, kind) {
  const el = $(elId);
  el.textContent = text;
  el.className = `status ${kind || ""}`;
}

// Smart multi-line paste parser
$("token").addEventListener("paste", (e) => {
  const pasteData = (e.clipboardData || window.clipboardData).getData("text") || "";
  if (pasteData.includes("port=") || pasteData.includes("token=")) {
    e.preventDefault();
    const lines = pasteData.split("\n");
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("port=")) {
        $("port").value = trimmed.replace("port=", "").trim();
      } else if (trimmed.startsWith("token=")) {
        $("token").value = trimmed.replace("token=", "").trim();
      } else if (trimmed.startsWith("code=")) {
        $("pairCode").value = trimmed.replace("code=", "").trim();
      }
    }
    setStatus("status", "Pasted port and token from clipboard.", "ok");
  }
});

async function save() {
  const port = Number($("port").value) || 47823;
  const token = $("token").value.trim();
  const enabled = $("enabled").checked;
  const feedShield = $("feedShield").checked;

  await chrome.storage.local.set({
    dwPort: port,
    dwToken: token,
    dwEnabled: enabled,
    dwFeedShield: feedShield,
  });
  setStatus("status", "Settings saved successfully.", "ok");

  // Trigger sync in background service worker
  chrome.runtime.sendMessage({ type: "SYNC_RULES" });
}

async function test() {
  const port = Number($("port").value) || 47823;
  const token = $("token").value.trim();
  setStatus("status", "Connecting to 127.0.0.1...", "pending");

  try {
    // 1. Check health
    const healthRes = await fetch(`http://127.0.0.1:${port}/v1/health`, {
      signal: AbortSignal.timeout(2000),
    });
    if (!healthRes.ok) throw new Error("Bridge not responding on loopback.");
    const health = await healthRes.json();

    // 2. Check token authentication if provided
    if (token) {
      const rulesRes = await fetch(`http://127.0.0.1:${port}/v1/rules`, {
        headers: { "X-DW-Token": token },
        signal: AbortSignal.timeout(2000),
      });
      if (rulesRes.status === 401) {
        setStatus("status", "Bridge reached, but bearer token is invalid.", "err");
        return;
      }
      if (rulesRes.ok) {
        const rulesData = await rulesRes.json();
        const ruleCount = (rulesData.rules || []).length;
        const focusState = rulesData.focus_active ? `Active (${rulesData.mode || "Focus"})` : "Inactive";
        setStatus(
          "status",
          `Connected & Authenticated! Focus: ${focusState}. Active rules: ${ruleCount}.`,
          "ok"
        );
        return;
      }
    }

    setStatus("status", `Connected to bridge on port ${port}. Enter token to complete pairing.`, "pending");
  } catch (error) {
    setStatus("status", "Could not reach Digital Wellbeing. Is the desktop app open?", "err");
  }
}

async function autoPair() {
  const port = Number($("port").value) || 47823;
  const code = $("pairCode").value.trim();
  setStatus("pairStatus", "Pairing with desktop app...", "pending");

  chrome.runtime.sendMessage(
    {
      type: "AUTO_PAIR",
      port,
      code,
      auto: !code,
    },
    (res) => {
      if (chrome.runtime.lastError) {
        setStatus("pairStatus", "Background worker error. Please try again.", "err");
        return;
      }
      if (res && res.ok) {
        $("port").value = res.port;
        $("token").value = res.token;
        setStatus("pairStatus", "Paired successfully with Digital Wellbeing!", "ok");
        save();
      } else {
        setStatus(
          "pairStatus",
          res && res.error
            ? res.error
            : "Pairing not approved. Open Focus → Web Rules in the app and click Generate Code.",
          "err"
        );
      }
    }
  );
}

$("save").addEventListener("click", save);
$("test").addEventListener("click", test);
$("autoPairBtn").addEventListener("click", autoPair);
$("enabled").addEventListener("change", save);
$("feedShield").addEventListener("change", save);

load();
