# Privacy Policy

**Last Updated:** October 2026  
**Applicable Version:** Digital Wellbeing v4.2.0 and later

Digital Wellbeing is engineered around an uncompromising principle: **your digital life is nobody's business but your own**. 

Unlike many commercial productivity or monitoring suites, Digital Wellbeing is **strictly local-first**. It runs locally on your PC, stores all records locally on your device, and transmits nothing to external servers.

---

## Core Privacy Principles

1. **Local-First Architecture:** All tracking data, application logs, category classifications, and usage metrics are stored solely on your physical drive in an embedded SQLite database.
2. **Zero Telemetry by Default:** Out of the box, Digital Wellbeing sends zero analytics, zero telemetry, and zero behavioral telemetry to the developer or any third party.
3. **No Account Required:** You do not need to register, log in, or provide an email address, name, or payment details to use any feature of the application.
4. **No Keylogging or Content Inspection:** Digital Wellbeing records process names, active window titles, and browser domain names. It **never** intercepts keystrokes, clipboard data, webcam, microphone, screen content, or form inputs.
5. **Full User Sovereignty:** You have complete ownership of your data. You can inspect the SQLite database, export your activity to standard CSV files, or permanently wipe your records at any time.

---

## What Data is Collected and Where

### 1. Foreground Window & Application Usage
- **What is recorded:** The process executable name (e.g., `code.exe`), full executable path (used to display the application icon), the window title bar text (e.g., `README.md - Digital Wellbeing`), and the timestamps when the window gained and lost focus.
- **Why it is recorded:** To calculate accurate daily, weekly, and monthly screen time statistics, group usage by categories, and enforce user-configured app limits.
- **Storage Location:** `%LOCALAPPDATA%\DigitalWellbeing\digital_wellbeing.db` (Table: `sessions`, `window_events`).

### 2. Idle and System State Detection
- **What is recorded:** Inactivity duration based on `GetLastInputInfo` (time elapsed since the last user keystroke or mouse movement), as well as system Lock, Unlock, Sleep, and Resume events.
- **What is NOT recorded:** Mouse cursor coordinates, mouse clicks, keystroke contents, or typed text. The system only reads the hardware timestamp of the most recent user interaction.
- **Why it is recorded:** To pause screen time counters when you step away from your computer and calculate active vs. idle periods.
- **Storage Location:** `%LOCALAPPDATA%\DigitalWellbeing\digital_wellbeing.db`.

### 3. Browser Domains (Website Tracking)
- **What is recorded:** The root domain of the currently active browser tab (e.g., `github.com` or `youtube.com`).
- **What is NOT recorded:** Full query parameters, passwords, form fields, page content, cookies, or browser search queries.
- **How it works:** Digital Wellbeing uses native Windows UI Automation (UIA) to read the address bar of supported foreground browsers (Edge, Chrome, Brave, Firefox, Opera, Vivaldi). If UI Automation is unavailable, it extracts the domain from the window title bar.
- **Storage Location:** `%LOCALAPPDATA%\DigitalWellbeing\digital_wellbeing.db` (Table: `website_sessions`).

### 4. Biometric Data & PIN Protection
- **Windows Hello:** Digital Wellbeing utilizes the Windows Runtime `Windows.Security.Credentials.UI.UserConsentVerifier` API. The authentication prompt, fingerprint analysis, facial recognition, and Windows PIN verification are executed entirely within the protected Windows security boundary. Digital Wellbeing **never receives, processes, or stores your biometric credentials**.
- **Local Fallback PIN:** If you configure a custom PIN within Digital Wellbeing, it is securely hashed with a cryptographically random salt using **PBKDF2 / SHA-256**. The raw PIN is never saved to disk.

---

## Network Communications

Digital Wellbeing does not require an internet connection for normal operation. The only network activities possible in the software are:

### 1. SafeBrowse Blocklist Downloads
When you enable the SafeBrowse Content Shield, the application downloads community blocklists over HTTPS from trusted open-source sources (by default, `https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn/hosts` or a custom user-defined URL). Blocklists are cached locally in `%LOCALAPPDATA%\DigitalWellbeing\blocklist\`. No usage data is transmitted during list synchronization.

### 2. Opt-in Anonymous Heartbeat Telemetry (Default: Disabled)
A minimal, anonymous heartbeat metric exists for opt-in quality verification. It is **disabled by default**. When explicitly enabled in Settings:
- It transmits an anonymous system ping (OS version, app version, runtime state) to a user-configured endpoint.
- It **never** contains window titles, domain history, personal files, user names, or machine MAC addresses.

---

## Data Retention and Management

- **Data Export:** You can export your full activity log to CSV format at any time via **Settings → Data Management → Export Data**.
- **Database Backup & Restore:** You can create standalone `.bak` snapshots of your database or restore from a previous backup directly in Settings.
- **Data Deletion:** You can delete individual session records or execute a complete factory reset via **Settings → Data Management → Reset Database**, which completely wipes the local SQLite database.
- **Uninstallation:** Removing Digital Wellbeing via Windows Apps & Features removes the application files and unregisters shortcuts. To delete your historical database, delete the directory `%LOCALAPPDATA%\DigitalWellbeing`.

---

## Children's Online Privacy

Digital Wellbeing does not collect personal data from any user, including children under the age of 13. The application is designed to help parents and individuals protect attention, establish healthy computing habits, and filter adult web content locally without cloud profiling.

---

## Changes to this Policy

If changes are made to our privacy architecture or policy, they will be documented in this repository alongside corresponding version releases in `CHANGELOG.md`.

---

## Contact & Questions

If you have questions, concerns, or feedback regarding privacy in Digital Wellbeing, please contact **privacy@digitalwellbeing.app** or open an issue on the repository.
