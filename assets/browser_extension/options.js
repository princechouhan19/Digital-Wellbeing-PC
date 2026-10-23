const $ = (id) => document.getElementById(id);

async function load() {
  const stored = await chrome.storage.local.get([
    "dwPort",
    "dwToken",
    "dwEnabled",
  ]);
  $("port").value = stored.dwPort || 47823;
  $("token").value = stored.dwToken || "";
  $("enabled").checked = stored.dwEnabled !== false;
}

function setStatus(text, kind) {
  const el = $("status");
  el.textContent = text;
  el.className = `status ${kind || ""}`;
}

async function save() {
  const port = Number($("port").value) || 47823;
  const token = $("token").value.trim();
  const enabled = $("enabled").checked;
  await chrome.storage.local.set({ dwPort: port, dwToken: token, dwEnabled: enabled });
  setStatus("Saved. Tab checks will use the new credentials.", "ok");
}

async function test() {
  const port = Number($("port").value) || 47823;
  try {
    const response = await fetch(`http://127.0.0.1:${port}/v1/health`, {
      signal: AbortSignal.timeout(1500),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    setStatus(`Connected to ${data.service} bridge on port ${data.port}.`, "ok");
  } catch (error) {
    setStatus("Could not reach the Digital Wellbeing app. Is it running?", "err");
  }
}

$("save").addEventListener("click", save);
$("test").addEventListener("click", test);
load();
