# Digital Wellbeing — Companion Browser Extension

Companion extension for the **Digital Wellbeing** desktop application for Windows.

Enforces granular **sub-path** web rules, shields addictive algorithmic feeds, and synchronizes active tab analytics without heavy Windows UI Automation (COM) overhead.

---

## Why Use the Companion Extension?

| Without Extension (OS Only) | With Companion Extension |
| :--- | :--- |
| **All-or-Nothing Hosts Blocking**: Blocking `youtube.com` kills educational video lectures and tutorials. | **Granular Sub-Path Control**: Blocks `youtube.com/shorts` while keeping `youtube.com/watch` available; blocks `reddit.com/r/all` while permitting `reddit.com/r/programming`. |
| **Heavy UI Automation (COM)**: Traverses browser address bars via accessibility tree, causing 50–200ms stutter. | **Zero Overhead Native Events**: Event-driven `chrome.tabs` detection with `<0.1ms` local rule evaluation. |
| **Jarring Tab Kill (`Ctrl+W`)**: Forcefully kills tabs without explanation. | **Mindful Pause UI**: Serene breathing pause screen with 60-second mindfulness breather. |
| **Addictive Feeds Visible**: Algorithmic recommendations stay visible on work tabs. | **Feed Shield**: Hides YouTube Shorts shelves, recommendations, and Reddit infinite feeds. |
| **Blind to In-Browser Quota**: No countdown or focus state in the browser. | **Toolbar Badge & Popup**: Real-time Focus countdown timer and live policy indicator. |

---

## 100% Local & Private

* **Loopback Only**: Communicates exclusively with `127.0.0.1` on your local computer.
* **Zero Telemetry**: No browsing data, history, or URLs are logged or sent to any remote server.
* **Fail-Open Reliability**: If the desktop app is closed or restarting, web browsing continues uninterrupted without false blocking.

---

## Installation (Chrome, Edge, Brave, Opera, Vivaldi)

1. Open `chrome://extensions` (or `edge://extensions` / `brave://extensions`).
2. Toggle on **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select this `assets/browser_extension` folder.
4. Open the extension icon in your browser toolbar or its **Options** page.
5. In Digital Wellbeing, open **Focus → Web Rules**:
   - Click **1-Click Auto Connect** in the extension options, or
   - Enter the 6-digit pairing code shown in the desktop app.

---

## File Structure

```
assets/browser_extension/
├── manifest.json         # Manifest V3 configuration & content script rules
├── background.js        # Service worker: sub-millisecond local rule caching & heartbeat
├── popup.html / .js / .css  # Toolbar popup: focus state, countdown timer & tab policy
├── options.html / .js   # Easy pairing, Feed Shield toggle & connection manager
├── blocked.html / .js   # Mindful pause screen with calming breathing ring & 60s breather
├── content/
│   └── feed_shield.js   # Content script hiding YouTube Shorts shelves & Reddit infinite feeds
└── icons/               # 16px, 48px, 128px extension icons
```
