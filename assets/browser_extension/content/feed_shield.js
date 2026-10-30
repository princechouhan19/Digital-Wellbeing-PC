/**
 * feed_shield.js — In-page distraction mitigation content script.
 *
 * Removes algorithmic feeds and shorts shelves without blocking useful educational
 * and search functionality.
 */
(function () {
  "use strict";

  const YOUTUBE_SHIELD_CSS = `
    /* YouTube Home Feed distracting recommendations */
    ytd-browse[page-subtype="home"] #contents,
    ytd-browse[page-subtype="home"] #feed-filter-chip-bar-container,
    /* Shorts buttons in left navigation sidebar */
    ytd-guide-entry-renderer:has(a[title*="Shorts"]),
    ytd-mini-guide-entry-renderer[aria-label*="Shorts"],
    /* Shorts shelves injected in search results and watch next */
    ytd-reel-shelf-renderer,
    ytd-rich-shelf-renderer[is-shorts],
    ytd-rich-section-renderer:has(ytd-reel-shelf-renderer),
    /* Compact shorts on mobile / small screen views */
    ytm-reel-shelf-renderer {
      display: none !important;
    }
  `;

  const REDDIT_SHIELD_CSS = `
    /* Reddit infinite all/popular feeds and promoted distraction banners */
    shreddit-feed[feed-type="all"],
    shreddit-feed[feed-type="popular"],
    aside:has(#trending-posts) {
      display: none !important;
    }
  `;

  let styleTag = null;

  function applyStyles(cssText) {
    if (!styleTag) {
      styleTag = document.createElement("style");
      styleTag.id = "dw-feed-shield-style";
      (document.head || document.documentElement).appendChild(styleTag);
    }
    styleTag.textContent = cssText;
  }

  function removeStyles() {
    if (styleTag) {
      styleTag.remove();
      styleTag = null;
    }
  }

  function updateShield() {
    chrome.storage.local.get(["dwFeedShield", "dwEnabled"], (res) => {
      const enabled = res.dwEnabled !== false && res.dwFeedShield !== false;
      if (!enabled) {
        removeStyles();
        return;
      }

      const host = window.location.hostname.toLowerCase();
      if (host.includes("youtube.com")) {
        applyStyles(YOUTUBE_SHIELD_CSS);
      } else if (host.includes("reddit.com")) {
        applyStyles(REDDIT_SHIELD_CSS);
      }
    });
  }

  // Initial check
  updateShield();

  // Listen for setting changes
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && (changes.dwFeedShield || changes.dwEnabled)) {
      updateShield();
    }
  });
})();
