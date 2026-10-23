<div align="center">

<img src="assets/icons/app_logo.png" alt="Digital Wellbeing Logo" width="120" style="border-radius: 24px;" />

# Digital Wellbeing for Windows

### A calmer relationship with your PC.

Digital Wellbeing tracks your screen time, protects your attention, and filters the web — all locally, with an Apple-grade interface inspired by macOS Sequoia.

[![Release](https://img.shields.io/badge/Release-v4.1.0--Aurora-0A84FF.svg?style=flat-square)](https://github.com/digital-wellbeing/digital-wellbeing/releases)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-30D158.svg?style=flat-square)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20%28Qt%29-BF5AF2.svg?style=flat-square)](https://www.qt.io/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20x64-007AFF.svg?style=flat-square)](https://www.microsoft.com/windows)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local--First-30D158.svg?style=flat-square)](PRIVACY.md)
[![License](https://img.shields.io/badge/License-MIT-FF9F0A.svg?style=flat-square)](LICENSE)

[**Download Installer (v4.1.0)**](https://digitalwellbeing.vercel.app) • [**User Guide**](docs/USER_GUIDE.md) • [**Architecture**](docs/ARCHITECTURE.md) • [**Roadmap**](ROADMAP.md) • [**Contributing**](CONTRIBUTING.md) • [**Website**](https://digitalwellbeing.vercel.app)

</div>

---

## Overview

Digital Wellbeing helps you understand and reclaim your computer time. It monitors active windows, user idle periods, and daily/weekly/monthly application usage — transforming raw data into actionable boundaries: **Focus sessions**, **daily app limits**, **website blocking**, and **system-wide adult content filtering**.

Tracking runs quietly in the background with negligible CPU footprint; the **Aurora interface** is ready whenever you need insight or focus.

> **100% Local-First:** No user account, no cloud telemetry, no analytics tracking. All data is persisted strictly to a local SQLite database on your machine.

---

## Screenshots & Interface Showcase

### Dashboard — Activity Rings & Real-time Trends

| Dark Mode Dashboard | Light Mode Dashboard |
| :---: | :---: |
| <img src="docs/screenshots/dark_dashboard.png" alt="Dark Mode Dashboard" width="100%" /> | <img src="docs/screenshots/light_dashboard.png" alt="Light Mode Dashboard" width="100%" /> |
| *Real-time category donut ring, top metrics, hourly curve & timeline* | *Light theme appearance with crisp typography and Apple HIG palette* |

---

### Attention Protection & Security

| Focus Mode & Distraction Blocker | App Locker & Windows Hello |
| :---: | :---: |
| <img src="docs/screenshots/dark_focus.png" alt="Focus Mode" width="100%" /> | <img src="docs/screenshots/dark_app_locker.png" alt="App Locker" width="100%" /> |
| *Preset allowlists (Study, Work, Deep Focus) with tab-level URL closing* | *Biometric face/fingerprint authentication via native Windows Hello* |

---

### Boundaries & Content Filtering

| Unified App & Website Timers | SafeBrowse Content Shield |
| :---: | :---: |
| <img src="docs/screenshots/dark_app_timer.png" alt="App Timers" width="100%" /> | <img src="docs/screenshots/safebrowse_dark.png" alt="SafeBrowse Shield" width="100%" /> |
| *Per-application & per-domain daily quotas with gentle 80% warnings* | *DNS-level adult content filter powered by StevenBlack open-source hosts* |

---

### Deep Analytics & SleepGuard

| Activity Trends & Hourly Breakdown | Insights & Productivity Analytics |
| :---: | :---: |
| <img src="docs/screenshots/dark_activity.png" alt="Activity Trends" width="100%" /> | <img src="docs/screenshots/dark_insights.png" alt="Insights" width="100%" /> |
| *Granular hourly application logs and category distributions* | *Weekly habit trends, productivity scoring, and focus metrics* |

---

### Wellbeing & Onboarding

| SleepGuard Bedtime Protection | 5-Step First-Run Onboarding |
| :---: | :---: |
| <img src="docs/screenshots/dark_sleepguard.png" alt="SleepGuard" width="100%" /> | <img src="docs/screenshots/onboarding_dark.png" alt="Onboarding Wizard" width="100%" /> |
| *Detects late-night inactivity and safely locks or sleeps the PC* | *Interactive first-run welcome personalizing goals and theme in 60s* |

---

## Key Features

### 1. Aurora Design System
- Built to Apple Human Interface Guidelines (HIG) standards: SF-metric typography (bundled Inter & Inter Display), refined materials, fluid spring animations, and Apple system color tokens (`#0A84FF` / `#007AFF`).
- Seamless support for Dark Mode, Light Mode, and automatic Windows System appearance matching.
- Haptics-lite sound feedback utilizing native Windows system audio cues.

### 2. Intelligent Screen Time Tracking
- Real-time foreground application tracking (process binary, path, and window title).
- Wraparound-safe idle detection via `GetLastInputInfo`.
- UI Automation tree traversal for active browser tab domain extraction across **Chrome**, **Edge**, **Brave**, **Firefox**, **Opera**, and **Vivaldi**.
- Crash-safe 30-second heartbeat database synchronization ensuring zero data loss.
- Detection of native Win32 power management events (Lock, Unlock, Sleep, Resume, Shutdown).

### 3. SafeBrowse Content Shield
- System-wide adult content filter blocking over 100,000+ adult and malicious domains at the DNS resolution layer.
- Powered by open-source, community-curated blocklists (**StevenBlack/hosts**, MIT License).
- Ships with an offline seed list enabling immediate filtering from first launch.
- Automatic weekly background synchronization with dedicated, atomic hosts-file management (`# DW-SAFEBROWSE`).
- **Zero packet sniffing or local VPNs:** Functions safely in every browser, normal and private/incognito windows alike.

### 4. Focus Mode & Distraction Blocker
- Curated presets: *Study*, *Work*, *Movie*, *Deep Focus*, and *Custom*.
- Strict **Allowlist Mode** (only approved applications run) or **Blocklist Mode** (restricts distracting apps).
- Browser tab URL enforcement: automatically closes unauthorized browser tabs during active focus.
- Temporary DNS domain blocking via an isolated hosts section (`# DIGITAL WELLBEING BLOCK`).

### 5. App Locker with Windows Hello
- Protect sensitive applications (communication suites, banking, private browsers) behind biometric authentication.
- Direct integration with native Windows Hello via WinRT (`UserConsentVerifier`) for instant facial or fingerprint unlock.
- Salted PBKDF2 / SHA-256 local PIN fallback when biometric hardware is unavailable.
- Configurable authentication frequencies: *Every Launch*, *5 Minutes*, *15 Minutes*, or *Until Application Closes*.

### 6. Unified App & Website Timers
- Configure daily usage quotas for specific software or web domains.
- Non-intrusive toast notifications when approaching limits (80% warning threshold).
- Graceful countdown dialogs and hard lockouts when daily time expires.

### 7. SleepGuard
- Late-night inactivity and burnout detection.
- Prompts gentle rest reminders and automatically locks the workstation or sleeps the PC if you doze off.

### 8. First-Run Onboarding
- A five-step welcome wizard introducing theme selection, daily goals, and SafeBrowse activation in under 60 seconds.

---

## Architecture Overview

Digital Wellbeing follows a clean, decoupled architecture:

```mermaid
flowchart TD
    subgraph UI ["Aurora UI Layer (PySide6)"]
        MW["MainWindow & Sidebar (12 Pages)"]
        OB["Onboarding Flow (5 Steps)"]
        DS["Aurora Design System & Theme Engine"]
        CW["Custom Widgets & PyQtGraph"]
    end

    subgraph CoreEngine ["Tracking & Protection Core"]
        TM["TrackingManager (Daemon Thread)"]
        FT["ForegroundTracker (Win32)"]
        IT["IdleTracker (GetLastInputInfo)"]
        BT["BrowserDomainTracker (UI Automation)"]
        FM["FocusManager (Session Enforcement)"]
        AL["AppLocker (Biometric / PIN Guard)"]
        CB["SafeBrowse Content Shield"]
        SG["SleepGuard (Burnout / Inactivity)"]
    end

    subgraph Security ["Security & OS Subsystems"]
        WH["Windows Hello (WinRT Biometrics)"]
        EH["Elevated Helper (One-Shot UAC Helper)"]
        HOSTS["Windows hosts File\n(C:\\Windows\\...\\hosts)"]
        NOTIF["Windows Toast Subsystem (WinRT)"]
    end

    subgraph Persistence ["Data & Local Storage"]
        REPO["Repository & Transactions"]
        DB[("SQLite Database (WAL Mode)\ndigital_wellbeing.db")]
        SETTINGS["SettingsManager (JSON Config)"]
    end

    MW --> TM
    MW --> FM
    MW --> AL
    MW --> CB
    MW --> REPO

    TM --> FT
    TM --> IT
    TM --> BT
    TM --> SG
    TM --> REPO

    FM --> EH
    CB --> EH
    EH --> HOSTS
    AL --> WH

    REPO --> DB
    TM --> NOTIF
    FM --> NOTIF
```

For full architectural details, consult the [Architecture Documentation](docs/ARCHITECTURE.md).

---

## Installation

### Standard Windows Installer (Recommended)
Download and run the installer from the [Releases page](https://digitalwellbeing.vercel.app):
```text
DigitalWellbeingSetup-4.1.0.exe
```

### Running from Source

#### Prerequisites
- Windows 10 (version 1809+) or Windows 11 (64-bit)
- Python 3.11, 3.12, or 3.13 (64-bit)
- Git for Windows

```powershell
# 1. Clone the repository
git clone https://github.com/digital-wellbeing/digital-wellbeing.git
cd digital-wellbeing

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Application

### 1. Interactive GUI
Launch the main desktop application:
```powershell
python main.py
```

### 2. Minimized to System Tray
Launch directly to the system notification area (ideal for startup / Task Scheduler):
```powershell
python main.py --background
```

### 3. Headless Tracking Service
Run tracking in the background with zero GUI memory overhead (~15–25 MB RAM):
```powershell
python main.py --service
```

### 4. Elevated Helper
Perform privileged hosts operations via User Account Control (UAC):
```powershell
python main.py --elevated-helper --action focus-apply --domains "reddit.com,youtube.com"
```

For full details on CLI flags, see the [CLI Reference](docs/CLI_REFERENCE.md).

---

## Building from Source

Digital Wellbeing provides an automated build script (`build.py`):

```powershell
# Compiles PyInstaller binary and generates Inno Setup installer
python build.py
```

To build standalone binaries manually with PyInstaller:
```powershell
pyinstaller digital_wellbeing.spec --clean --noconfirm
```
The output will be generated at `dist/DigitalWellbeing/DigitalWellbeing.exe`.

---

## Project Structure

```
digital-wellbeing/
├── main.py                      # Application entry point (GUI, service, UAC helper)
├── core/                        # Global constants, versioning, logger
│   ├── constants.py             # Enums, Apple system color tokens, timing constants
│   ├── logger.py                # Rotating logger
│   └── version.py               # Version accessor
├── database/                    # SQLite local persistence engine
│   ├── schema.py                # Table schemas and DDL migrations
│   ├── models.py                # Dataclasses and models
│   └── repository.py            # SQLite WAL mode repository, transactions, queries
├── tracker/                     # Screen time, foreground, and session monitoring
│   ├── foreground.py            # Win32 foreground window & process tracker
│   ├── idle.py                  # User idle detection via GetLastInputInfo
│   ├── browser_domain.py        # Active browser tab domain extraction (UI Automation)
│   ├── categorizer.py           # Process-to-category classification engine
│   ├── sleepguard.py            # Inactivity and late-night rest detector
│   └── manager.py               # Background TrackingManager coordinator thread
├── protection/                  # Focus, limits, SafeBrowse, and access control
│   ├── focus_manager.py         # Focus session management and allowlist/blocklist rules
│   ├── app_locker.py            # Biometric & PIN app protection guard
│   ├── content_blocker.py       # SafeBrowse adult content hosts manager
│   ├── windows_hello.py         # WinRT UserConsentVerifier biometric integration
│   ├── pin.py                   # Salted PBKDF2 PIN hashing and verification
│   ├── website_blocker.py       # Focus website hosts file blocker
│   └── elevated_helper.py       # One-shot privileged helper for UAC operations
├── analytics/                   # Aggregation and analytics engine
│   └── engine.py                # Screen time computation, trends, daily stats
├── ui/                          # Aurora Apple-grade PySide6 graphical interface
│   ├── app.py                   # DigitalWellbeingApp lifecycle & QApplication wrapper
│   ├── main_window.py           # Main window chrome, sidebar, and layout
│   ├── design_system.py         # Aurora design system tokens, fonts, and metrics
│   ├── theme.py                 # Dynamic dark/light QSS stylesheets
│   ├── onboarding.py            # 5-step interactive onboarding experience
│   ├── pages/                   # 12 application pages (Dashboard, Activity, Focus, etc.)
│   └── widgets/                 # Reusable Aurora widgets (Charts, Rings, Cards, Dialogs)
├── notifications/               # Native Windows toast notifications
│   └── notifier.py              # WinRT / Windows toast notification dispatcher
└── utils/                       # System helpers, autostart, updater, elevation
    ├── elevation.py             # UAC elevation launcher (ShellExecuteEx)
    ├── autostart.py             # Windows Registry Run key manager
    ├── updater.py               # GitHub Releases auto-update checker & SHA-256 verifier
    └── csv_exporter.py          # CSV activity history export
```

---

## Documentation Index

- 📘 [**User Guide**](docs/USER_GUIDE.md): Complete end-user manual for all features and settings.
- 📐 [**Architecture Guide**](docs/ARCHITECTURE.md): Deep dive into subsystems, threading, and data models.
- 🛠️ [**Developer Guide**](docs/DEVELOPER_GUIDE.md): Development setup, coding guidelines, and testing.
- 💻 [**CLI Reference**](docs/CLI_REFERENCE.md): Command line flags and headless service documentation.
- 🔍 [**Troubleshooting**](docs/TROUBLESHOOTING.md): Solutions for permissions, antivirus false positives, and Windows Hello.
- 🔒 [**Security Policy**](SECURITY.md): Vulnerability reporting, threat modeling, and defense-in-depth principles.
- 🛡️ [**Privacy Policy**](PRIVACY.md): Detailed local-first data guarantees and privacy architecture.
- ⚖️ [**Legal Notices**](LEGAL.md): Third-party software licenses, trademarks, and disclaimers.
- 🤝 [**Contributing Guidelines**](CONTRIBUTING.md): How to contribute, report bugs, and propose features.
- 📜 [**Code of Conduct**](CODE_OF_CONDUCT.md): Community standards and enforcement pledge.
- 🗺️ [**Product Roadmap**](ROADMAP.md): Upcoming features, Connect with Phone, and engine optimizations.

---

## Security & Privacy Guarantee

- **Zero Cloud Storage:** Everything is stored locally in `%LOCALAPPDATA%\DigitalWellbeing\digital_wellbeing.db`.
- **Zero Telemetry by Default:** Telemetry is strictly opt-in and disabled by default.
- **Biometric Security:** Biometric credentials are authenticated entirely by the Windows OS; no biometric data ever touches application memory.
- **Atomic Hosts Updates:** All hosts updates create an atomic backup (`hosts.dw.bak`) before modification and are restored cleanly upon exit or uninstallation.

---

## License

Digital Wellbeing for Windows is open-source software licensed under the **[MIT License](LICENSE)**.

```
Copyright (c) 2026 Prince Chouhan and Digital Wellbeing Contributors
```
