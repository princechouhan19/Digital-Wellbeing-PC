# Security Policy

Digital Wellbeing is committed to ensuring the safety, privacy, and integrity of our users and their devices. Because Digital Wellbeing interacts with system-level APIs on Windows — including foreground window monitoring, hosts-file manipulation for website blocking, and Windows Hello biometric authentication — security and defensive engineering are foundational to the project.

This document outlines our security policies, supported versions, threat model, and how to responsibly disclose vulnerabilities.

---

## Supported Versions

We actively provide security updates for the current major and minor release cycle. When a new version is released, previous versions may receive critical security patches at our discretion.

| Version | Supported | Status |
| :--- | :---: | :--- |
| **4.1.x** | ✅ Yes | Current active release |
| **4.0.x** | ⚠️ Critical only | Maintenance phase |
| **3.x.x and earlier** | ❌ No | End of Life (EOL) |

---

## Reporting a Vulnerability

We take all security vulnerability reports seriously. Please do **not** report security vulnerabilities via public GitHub issues, discussions, or pull requests.

### Disclosure Channels

1. **GitHub Security Advisories (Recommended):**  
   Navigate to the repository's **Security Tab** and click **"Report a vulnerability"** to open a private advisory.

2. **Email Disclosure:**  
   Send an encrypted or standard email to:  
   📧 **security@digitalwellbeing.app**  
   *Subject Line:* `[SECURITY VULNERABILITY] Digital Wellbeing - <Short Description>`

### What to Include in Your Report

To help us triage and investigate efficiently, please include:
- A detailed description of the vulnerability and its potential impact.
- The version of Digital Wellbeing and Windows OS (e.g., Windows 11 23H2 x64) tested.
- Step-by-step reproduction steps or a minimal Proof of Concept (PoC).
- Any proposed remediation or mitigation steps if you have them.

### Response & Coordinated Disclosure Timeline

- **Acknowledgment:** Within **48 hours** of receiving your report.
- **Triage & Assessment:** Within **5 business days**, detailing findings and severity rating (CVSS).
- **Patch Development:** Within **14–30 business days**, depending on complexity.
- **Public Disclosure:** Coordinated release with patch and credit to the reporter.

---

## Security Architecture & Threat Model

Digital Wellbeing is designed with a **local-first, least-privilege, and defense-in-depth** model.

### 1. Privilege Separation & UAC Elevation Safety
- **Standard User Execution:** The main graphical user interface and tracking service run strictly under standard, non-administrator user privileges.
- **Dedicated Elevated Helper:** Operations requiring administrative privileges (modifying the Windows `hosts` file for SafeBrowse or Focus Mode) are delegated to a dedicated one-shot sub-process invoked with `--elevated-helper`.
- **Strict Input Sanitization & Action Whitelisting:** The elevated helper executes only pre-approved, whitelisted actions:
  - `focus-apply`, `focus-remove`
  - `safebrowse-apply`, `safebrowse-remove`
- Domain strings are strictly parsed, validated against RFC hostname specifications, and stripped of injection characters (newlines, carriage returns, command delimiters) prior to writing.

### 2. Hosts File Protection & Integrity
- **Marker Encapsulation:** All hosts alterations are cleanly confined between designated comment delimiters (`# DIGITAL WELLBEING BLOCK` and `# DW-SAFEBROWSE`).
- **Atomic Operations & Backups:** Before any write occurs, a pristine backup of `C:\Windows\System32\drivers\etc\hosts` is created at `hosts.dw.bak`. Writes are performed via temporary files and moved atomically to prevent file corruption during power loss or abrupt termination.
- **Clean Uninstallation & Rollback:** SafeBrowse or Focus disablement completely purges managed blocks. If uninstalled, the hosts file is restored.

### 3. Windows Hello & PIN Authentication
- **Native OS Biometrics:** Digital Wellbeing integrates directly with Windows Hello via the native WinRT `Windows.Security.Credentials.UI.UserConsentVerifier` API. Biometric verification (facial recognition, fingerprint, or system PIN) occurs entirely inside the isolated Windows security subsystem. Digital Wellbeing **never** captures, receives, or stores raw biometric data.
- **Local Fallback PIN:** When a custom PIN is configured, it is stored using **salted PBKDF2/SHA-256 cryptographic hashing** within the local SQLite database. Plaintext PINs are never persisted to disk or emitted in logs.

### 4. Auto-Updater Integrity & Transport Security
- **Secure Transport:** Release metadata and update packages are retrieved exclusively via HTTPS from the official GitHub API (`api.github.com`).
- **Cryptographic Verification:** Every downloaded installer is verified against published **SHA-256 checksums** before execution. If checksum validation fails or the binary is corrupted, the installer is immediately discarded.
- **Detached Execution:** Updates run through a verified child process only after cryptographic approval.

### 5. Local Data Sovereignty & Zero Telemetry by Default
- **Local SQLite Database:** All tracked screen time, application titles, and browser domain sessions are stored locally in `%LOCALAPPDATA%\DigitalWellbeing\digital_wellbeing.db`.
- **No Third-Party Analytics:** Digital Wellbeing contains no third-party tracking SDKs, ad networks, or telemetry agents.
- **Opt-In Telemetry:** Anonymous application heartbeat statistics are completely optional, disabled by default, and require manual user activation in Settings.

### 6. Process Monitoring & Defensive Bounds
- **System Process Exclusion:** Process termination routines (used in Focus Mode and App Locker) enforce an immutable allowlist that strictly forbids terminating core Windows system processes (such as `explorer.exe`, `csrss.exe`, `lsass.exe`, `services.exe`, `svchost.exe`, `dwm.exe`).

---

## Security Best Practices for Contributors

When writing code for Digital Wellbeing:
1. **Never block the Qt UI thread** with synchronous I/O or network requests.
2. **Never execute shell strings directly:** Always pass command vectors to `subprocess.run(["cmd", "arg"])` with `shell=False`.
3. **Always sanitize file system paths:** Use `pathlib.Path.resolve()` and ensure paths cannot escape user AppData boundaries.
4. **Log defensively:** Never log user passwords, PINs, auth tokens, or sensitive window titles in standard production logs.
5. **Handle Win32 handles cleanly:** Ensure all handles acquired via `win32api` or `ctypes` are wrapped in try/finally blocks and released with `CloseHandle`.
