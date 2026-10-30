const params = new URLSearchParams(location.search);
const reason = params.get("reason") || "Blocked by Focus rules";
const url = params.get("url") || "";

document.getElementById("reason").textContent = reason;
document.getElementById("url").textContent = url;

document.getElementById("close").addEventListener("click", async () => {
  try {
    const tab = await chrome.tabs.getCurrent();
    if (tab && tab.id != null) {
      await chrome.tabs.remove(tab.id);
      return;
    }
  } catch (error) {
    /* fall through */
  }
  window.close();
});

document.getElementById("back").addEventListener("click", () => {
  history.length > 1 ? history.back() : window.close();
});

// 60-Second Mindfulness Breather
let breatherInterval = null;
document.getElementById("breatheBtn").addEventListener("click", () => {
  const timerBox = document.getElementById("breatherTimer");
  const countEl = document.getElementById("countdown");
  const breatheBtn = document.getElementById("breatheBtn");

  breatheBtn.style.display = "none";
  timerBox.style.display = "block";

  let remaining = 60;
  countEl.textContent = remaining;

  if (breatherInterval) clearInterval(breatherInterval);
  breatherInterval = setInterval(() => {
    remaining -= 1;
    countEl.textContent = remaining;
    if (remaining <= 0) {
      clearInterval(breatherInterval);
      timerBox.textContent = "Mindful pause complete. Ready to return to focus?";
    }
  }, 1000);
});
