# Contributing to Digital Wellbeing

First off, thank you for considering contributing to **Digital Wellbeing for Windows**! Open-source contributions from developers, designers, and testers are what make this software reliable, delightful, and privacy-respecting for everyone.

Please take a moment to review this guide before submitting issues or pull requests.

---

## Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it to understand our community standards and expectations.

---

## How Can I Contribute?

There are many ways to contribute to Digital Wellbeing:

- 🐛 **Reporting Bugs:** Uncover edge cases, UI scaling bugs, or process detection glitches.
- 💡 **Suggesting Features:** Propose productivity features, UI refinements, or blocking mechanisms.
- 💻 **Writing Code:** Implement new capabilities, fix bugs, optimize performance, or add test coverage.
- 📖 **Improving Documentation:** Clarify user guides, architecture docs, or API references.
- 🎨 **Design & Assets:** Help improve icons, theme palettes, and UI micro-interactions.

---

## Development Environment Setup

### 1. Prerequisites
- **Operating System:** Windows 10 (version 1809 or higher) or Windows 11 (64-bit).
- **Python:** Python 3.11, 3.12, or 3.13 (64-bit).
- **Git:** Git for Windows.
- *(Optional for building installer)* **Inno Setup 6:** Required only if compiling the Windows installer binary.

### 2. Clone the Repository
```powershell
git clone https://github.com/princechouhan19/Digital-Wellbeing-PC.git
cd digital-wellbeing
```

### 3. Set Up a Virtual Environment
We strongly recommend developing within an isolated Python virtual environment:

```powershell
# Create virtual environment
python -m venv venv

# Activate on PowerShell
.\venv\Scripts\Activate.ps1

# (If running into PowerShell ExecutionPolicy restrictions, run:)
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Codebase Architecture

Digital Wellbeing is organized into modular Python packages with strict separation of concerns:

```
digital-wellbeing/
├── main.py                      # Application entry point (GUI, service, UAC helper)
├── core/                        # Global constants, versioning, logger
│   ├── constants.py             # Enums (AppCategory, EventType), colors, defaults
│   ├── logger.py                # Rotating file & console logger
│   └── version.py               # Version helper reading version.json
├── database/                    # SQLite local persistence engine
│   ├── schema.py                # Table schemas and DDL migrations
│   ├── models.py                # Dataclasses and object models
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

## Running in Development

### Run the Interactive GUI
```powershell
python main.py
```

### Launch Minimized to System Tray
```powershell
python main.py --background
```

### Run the Headless Tracking Engine
Runs the background tracker with zero Qt/GUI memory footprint:
```powershell
python main.py --service
```

### Test Privileged Elevated Actions
```powershell
python main.py --elevated-helper --action safebrowse-apply --domains adultsite.com
```

---

## Testing

Digital Wellbeing includes extensive automated test suites covering tracking, domain normalization, app locker security, timers, and database operations.

Run all tests via `pytest`:
```powershell
pytest
```

Or execute targeted test scripts:
```powershell
python test_all.py
python test_app_locker.py
python test_domain_normalization.py
python test_features.py
python test_tracking.py
python test_updater_flow.py
```

---

## Coding Standards & Guidelines

### 1. Python Style & Quality
- Follow **PEP 8** style conventions.
- Use explicit type hints for function arguments and return types.
- Include docstrings on all public classes, methods, and modules.
- Always include `from __future__ import annotations` at the top of new files for forward-compatible type evaluation.

### 2. Qt / PySide6 Thread Safety
- **Never block the Qt GUI thread.** Long-running tasks (network requests, blocklist parsing, heavy file I/O) must execute on background threads (`threading.Thread` or `QThread`).
- **Never touch GUI elements directly from worker threads.** Communicate between threads exclusively using Qt Signals and Slots (`Signal`, `Slot`).

### 3. Windows API Conventions
- When using Win32 API functions via `pywin32` or `ctypes`, ensure handles (e.g., process handles, token handles) are cleanly released using `try...finally` and `CloseHandle`.
- Be mindful of clock wraparound when dealing with `GetTickCount64` and `GetLastInputInfo`.

### 4. Privacy & Security Invariants
- Never persist plaintext passwords or PINs.
- Never hardcode personal API tokens, telemetry URLs, or developer secrets.
- Always validate and sanitize user inputs before passing them to the elevated helper or writing to the hosts file.

---

## Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new user-facing or technical feature
- `fix:` A bug fix
- `docs:` Documentation updates or additions
- `style:` Formatting, missing semi-colons, no code change
- `refactor:` Code refactoring with no functional change
- `perf:` Performance improvements
- `test:` Adding or correcting tests
- `chore:` Maintenance tasks, dependency updates, build tooling

**Example:**
```text
feat(safebrowse): add weekly automatic blocklist refresh

- Check blocklist timestamp on app launch
- Sync in background if cache is older than 7 days
- Notify user via toast on successful update
```

---

## Submitting Pull Requests

1. **Fork the repository** on GitHub.
2. **Create a branch** for your work:
   ```powershell
   git checkout -b feat/custom-blocklist-support
   ```
3. **Make your changes** cleanly, following our coding conventions.
4. **Run the test suite** to ensure no regressions:
   ```powershell
   pytest
   ```
5. **Commit your changes** with a meaningful conventional commit message.
6. **Push to your fork:**
   ```powershell
   git push origin feat/custom-blocklist-support
   ```
7. **Open a Pull Request** against the `main` branch of the repository.
8. Complete the PR template checklist and await code review from the maintainers.

Thank you for helping make Digital Wellbeing the best productivity tool on Windows!
