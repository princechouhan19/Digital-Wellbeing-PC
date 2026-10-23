# REBRAND NOTES

## Brand Changes (v4.1.0)
- **Retired brands:** all legacy product names used by earlier releases (v2 "NYW", v3 display name)
- **Final Product Brand:** Digital Wellbeing (visual wordmark: "DIGITAL / WELLBEING" overline pair)
- **Product Descriptor:** Digital Wellbeing for Windows
- **Version:** 4.1.0

## What User-Facing Surfaces Changed
1. **Desktop Application UI:**
   - Sidebar brand header now displays "DIGITAL / WELLBEING".
   - Window title displays "Digital Wellbeing v4.1.0".
   - Settings page descriptions reflect "Digital Wellbeing".
   - Update dialog copy: "Digital Wellbeing X is available" / "Downloading Digital Wellbeing X…".
   - Tray menu action renamed to "Open Digital Wellbeing".
   - All protection and authentication dialogs updated (e.g. "This app is protected by Digital Wellbeing", "Enter your PIN", "App Blocked by Focus").
2. **Installer Metadata:**
   - Inno Setup wizard dialogs and titles display "Digital Wellbeing".
   - Shortcuts in Start Menu, Startup, and Desktop use "Digital Wellbeing".
   - Output installer named `DigitalWellbeingSetup-4.1.0.exe`.
   - Windows Registry Apps & Features metadata lists "Digital Wellbeing".
3. **Executable Metadata:**
   - Embedded `ProductName` updated to "Digital Wellbeing".
   - `FileDescription` set to "Digital Wellbeing for Windows".
4. **Website:**
   - Site title: "Digital Wellbeing for Windows".
   - Navbar/footer brand: "DIGITAL WELLBEING".
   - Canonical logo asset: `/logo.png` (legacy brand-named assets removed).
   - All hero, capability, philosophy, privacy, and download copy updated.
   - Legacy `nyw-*` design tokens renamed to neutral `dw-*` tokens.
5. **Documentation:**
   - README updated with "# Digital Wellbeing — Apple-grade digital wellbeing for Windows".

## Technical Identifiers (unchanged by design)
To prevent breaking existing configurations, user data, or update mechanisms:
- **Executable Name:** `DigitalWellbeing.exe` (registry paths, shortcut targets, startup tasks, updater hooks)
- **GitHub Repository:** `digital-wellbeing/digital-wellbeing`
- **App Data Directory/DB:** `digital_wellbeing.db` inside user AppData (`DigitalWellbeing`)
- **Python Module Imports:** internal module structure unchanged
- **Windows Toast AppID:** `PrinceChouhan.DigitalWellbeing.App` retained for notification grouping
- **Updater back-compat:** the release-asset matcher accepts any `*Setup-<version>.exe` naming, so
  clients updating from older releases continue to find installers published with the legacy name.
- **Hosts-file back-compat:** the website blocker strips managed blocks written by any previous
  release format (matched generically), then writes the current `# DIGITAL WELLBEING BLOCK` section.
- **CHANGELOG:** historical entries use the current product name for readability.
