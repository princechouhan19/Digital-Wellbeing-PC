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
