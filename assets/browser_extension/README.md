# Digital Wellbeing — Web Rules browser extension

Optional companion extension for **sub-path** Focus rules such as:

- block `youtube.com/shorts` while keeping YouTube available;
- block `reddit.com/r/all` but allow `reddit.com/r/programming`.

The extension talks only to `127.0.0.1` (the Digital Wellbeing desktop app).
There is no analytics, no remote server, and no browsing history upload. If the
app is closed, every request fails open and browsing is never interrupted.

## Install (Chrome, Edge, Brave, or any Chromium browser)

1. Open `chrome://extensions` (or `edge://extensions` / `brave://extensions`).
2. Enable **Developer mode**.
3. Choose **Load unpacked** and select this `assets/browser_extension` folder.
4. In Digital Wellbeing, open **Focus → Web rules** and copy the bridge port and
   token.
5. Open the extension's **Options** page and paste both values, then click
   **Test connection**.

## How enforcement works

While a Focus session is active, the extension asks the app for a decision on
each tab change/activation. If the URL matches a block rule, the tab is
redirected to a local `blocked.html` page. Rules are configured in the app, so
the extension does not need to be updated when rules change.

## Limitations

- Browser vendors increasingly restrict extensions; loading unpacked requires
  Developer mode.
- The bridge is loopback-only and token-protected, but this is a local
  convenience boundary, not a hardened security boundary against a
  same-user administrator.
- Without the extension, the desktop app still enforces domain-level rules via
  the existing hosts-file integration.
