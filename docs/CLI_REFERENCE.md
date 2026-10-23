# Digital Wellbeing — Command Line Interface Reference

Digital Wellbeing provides command-line flags allowing it to operate in standard desktop mode, background system-tray mode, as a headless tracking daemon, or as a privileged UAC helper.

---

## Command Syntax

```powershell
DigitalWellbeing.exe [OPTIONS]
# Or when running from source:
python main.py [OPTIONS]
```

---

## Options & Flags

| Flag | Argument | Description |
| :--- | :--- | :--- |
| *(None)* | — | Launches the full graphical user interface (Aurora UI). |
| `--background` | — | Launches the application minimized directly into the Windows system notification area (system tray). Used primarily for Windows autostart. |
| `--service` | — | Runs the tracking engine in headless service mode. No Qt GUI or windowing libraries are instantiated, resulting in minimal CPU and memory consumption (~15–25 MB). |
| `--elevated-helper` | — | Runs the process as a privileged helper to perform administrative actions. Requires elevated UAC privileges. |
| `--action` | `<string>` | Specifies the action for the elevated helper to perform (e.g. `safebrowse-apply`, `focus-apply`). Must be accompanied by `--elevated-helper`. |
| `--domains` | `<string>` | Comma-separated list of domain names to block when performing `focus-apply`. |
| `-h`, `--help` | — | Displays the command-line help message and exits. |

---

## Usage Examples

### 1. Launch Interactive GUI
```powershell
python main.py
```

### 2. Launch Minimized to System Tray
Ideal for Windows Task Scheduler or the Registry `Run` key:
```powershell
python main.py --background
```

### 3. Run Headless Tracking Service
Runs tracking continuously in the terminal or background service without any GUI:
```powershell
python main.py --service
```

### 4. Elevated Helper (UAC Actions)
These commands are normally spawned internally by Digital Wellbeing via `ShellExecuteEx` (`runas`), but can be executed directly from an elevated PowerShell terminal:

#### Apply Focus Website Blocking:
```powershell
python main.py --elevated-helper --action focus-apply --domains "reddit.com,twitter.com,youtube.com"
```

#### Remove Focus Website Blocking:
```powershell
python main.py --elevated-helper --action focus-remove
```

#### Apply SafeBrowse Content Filter:
```powershell
python main.py --elevated-helper --action safebrowse-apply
```

#### Remove SafeBrowse Content Filter:
```powershell
python main.py --elevated-helper --action safebrowse-remove
```

---

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GITHUB_API_BASE` | `https://api.github.com` | Custom endpoint for checking application updates. Useful for local mocking or enterprise mirrors. |
| `SIGN_PASSWORD` | `""` | Code-signing certificate password consumed by `build.py` during release compilation. |

---

## Process Exit Codes

| Exit Code | Meaning |
| :--- | :--- |
| `0` | Success / normal termination. |
| `1` | Fatal error during initialization, failed elevated helper action, or uncaught exception. |
