# Digital Wellbeing — Developer Guide

This guide covers everything necessary to build, develop, extend, and package **Digital Wellbeing for Windows**.

---

## 1. Development Prerequisites

- **OS:** Windows 10 (Build 17763+) or Windows 11 (64-bit).
- **Python:** Python 3.11, 3.12, or 3.13 (64-bit).
- **Git:** Installed and available in your PowerShell PATH.
- **Inno Setup 6 (Optional):** Required only if building the Windows setup installer (`ISCC.exe`).

---

## 2. Setting Up the Development Environment

### Step 1: Virtual Environment
In your PowerShell terminal:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Required Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Install Development & Linting Tools (Recommended)
```powershell
pip install pytest black flake8 mypy
```

---

## 3. Running & Debugging the Application

### Running with Full GUI
```powershell
python main.py
```

### Running Minimized to System Tray
```powershell
python main.py --background
```

### Running as Headless Tracking Service
Runs the tracker loop with no Qt GUI instantiated (useful for testing tracking in low-resource environments):
```powershell
python main.py --service
```

### Developer Mode in GUI
While the application is running, press `Ctrl + Shift + D` inside the window to reveal the internal **Developer / Diagnostics page**. This displays:
- Active foreground window handles and process metadata.
- Last input tick counts and idle calculation state.
- Database transaction counters and WAL size.
- Live browser domain extraction telemetry.

### Inspecting Local Data & Logs
All application runtime files are located in your user profile:
- **Database:** `%LOCALAPPDATA%\DigitalWellbeing\digital_wellbeing.db`
- **Application Logs:** `%LOCALAPPDATA%\DigitalWellbeing\digital_wellbeing.log`
- **Startup Diagnostics:** `%LOCALAPPDATA%\DigitalWellbeing\startup_diagnostic.txt`
- **SafeBrowse Blocklist Cache:** `%LOCALAPPDATA%\DigitalWellbeing\blocklist\`

To inspect the SQLite database:
```powershell
sqlite3 "$env:LOCALAPPDATA\DigitalWellbeing\digital_wellbeing.db"
```

---

## 4. UI Development with the Aurora Design System

Digital Wellbeing uses the **Aurora Design System** (`ui/design_system.py`), which centralizes all styling tokens:

### Token Usage Example
```python
from ui.design_system import (
    COLOR_SYSTEM_BLUE,
    COLOR_CARD_DARK,
    COLOR_CARD_LIGHT,
    RADIUS_CARD,
    SPACING_MD,
    get_font,
)
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

class CustomStatCard(QFrame):
    def __init__(self, parent=None, dark: bool = True):
        super().__init__(parent)
        self.setObjectName("CustomStatCard")
        
        # Apply token metrics
        bg = COLOR_CARD_DARK if dark else COLOR_CARD_LIGHT
        self.setStyleSheet(f"""
            QFrame#CustomStatCard {{
                background-color: {bg};
                border-radius: {RADIUS_CARD}px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                padding: {SPACING_MD}px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        label = QLabel("Focus Score")
        label.setFont(get_font(size=14, weight=600))
        layout.addWidget(label)
```

### Page Addition Checklist
To add a new page to the application:
1. Create your page widget inside `ui/pages/my_new_page.py`.
2. Inherit from `QWidget` and implement `on_theme_changed(dark: bool)`.
3. Register the page widget in `ui/main_window.py` in `_setup_pages()`.
4. Add a navigation button in the sidebar in `ui/main_window.py` in `_setup_sidebar()`.

---

## 5. Adding Browser Support to Domain Tracking

Active browser tab tracking is managed by `tracker/browser_domain.py`:

```python
# 1. Register browser process name
BROWSER_PROCESSES = frozenset({
    "chrome.exe",
    "msedge.exe",
    "brave.exe",
    "firefox.exe",
    "my_new_browser.exe",
})

# 2. Add UIA address bar identifier pattern if non-standard
```
Domain extraction uses Windows UI Automation to locate the address bar edit control without injecting into browser process memory.

---

## 6. Extending the Elevated Helper

Operations that modify Windows protected system files (e.g. `hosts`) must use the isolated elevated helper:

1. Never run the main application executable elevated.
2. In `protection/elevated_helper.py`, define the action in `VALID_ACTIONS`:
   ```python
   VALID_ACTIONS = {
       "focus-apply",
       "focus-remove",
       "safebrowse-apply",
       "safebrowse-remove",
       "my-new-action",
   }
   ```
3. Implement strict input validation on all arguments.
4. Call the elevated helper using `utils/elevation.py`:
   ```python
   from utils.elevation import run_as_admin
   success = run_as_admin(["--elevated-helper", "--action", "my-new-action"])
   ```

---

## 7. Running Automated Tests

Run the full automated test suite with pytest:
```powershell
pytest -v
```

Execute specific test modules:
```powershell
# Test App Locker logic and biometric fallback
python test_app_locker.py

# Test domain normalization and browser tab parsing
python test_domain_normalization.py

# Test foreground window and idle tracking logic
python test_tracking.py

# Test focus PIN and regression guards
python test_focus_pin_regression.py
```

---

## 8. Building the Standalone Executable & Installer

Digital Wellbeing includes a unified build pipeline in `build.py`.

### 1. Build Standalone PyInstaller Executable
```powershell
python build.py
```
This performs the following steps:
1. Reads `version.json` and updates `file_version_info.txt` and `app.manifest`.
2. Executes PyInstaller using `digital_wellbeing.spec`.
3. Signs binaries if a code-signing certificate (`cert.pfx`) is present.
4. Invokes Inno Setup (`installer/DigitalWellbeing.iss`) to compile the Windows installer executable into `dist/DigitalWellbeingSetup-<version>.exe`.

### 2. Manual PyInstaller Invocation
```powershell
pyinstaller digital_wellbeing.spec --clean --noconfirm
```
The output directory will be placed at `dist/DigitalWellbeing/`.
