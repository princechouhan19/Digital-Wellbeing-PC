# Digital Wellbeing — Troubleshooting Guide

This guide helps resolve common configuration, permission, and operating system issues with **Digital Wellbeing for Windows**.

---

## 1. Hosts File & SafeBrowse Issues

### Issue: "Access Denied" or UAC prompt fails when enabling SafeBrowse or Focus Mode
- **Cause:** Modifying `C:\Windows\System32\drivers\etc\hosts` requires administrator privileges. If the UAC prompt was dismissed or an antivirus software has locked the hosts file, the modification will fail.
- **Solution:**
  1. Ensure you accept the Windows User Account Control (UAC) prompt when enabling SafeBrowse or Focus website blocking.
  2. Check if third-party antivirus suites (e.g., Bitdefender, Kaspersky, Norton) have a "Hosts file protection" toggle enabled. If so, add an exclusion for `DigitalWellbeing.exe`.
  3. Verify permissions on `C:\Windows\System32\drivers\etc\hosts`: Right-click the file → **Properties** → **Security** → Ensure the `Administrators` group has Full Control.

### Issue: The hosts file seems corrupted or blocked sites remain blocked after exiting
- **Recovery:** Digital Wellbeing maintains an automatic backup before any write at:  
  `C:\Windows\System32\drivers\etc\hosts.dw.bak`
- **Manual Restoration:**
  1. Open an elevated PowerShell terminal (Run as Administrator).
  2. Run:
     ```powershell
     Copy-Item "C:\Windows\System32\drivers\etc\hosts.dw.bak" "C:\Windows\System32\drivers\etc\hosts" -Force
     ipconfig /flushdns
     ```

---

## 2. Windows Hello & Biometric Authentication

### Issue: "Windows Hello unavailable on this device" badge is shown
- **Cause:** Your computer either lacks Windows Hello biometric hardware (IR facial camera, fingerprint sensor) or Windows Hello PIN has not been set up in Windows Settings.
- **Solution:**
  1. Go to **Windows Settings → Accounts → Sign-in options**.
  2. Configure a PIN or biometric sign-in under **Windows Hello**.
  3. If your PC does not support Windows Hello hardware, simply use the **Digital Wellbeing PIN** option inside the app (Settings → Privacy & Security → PIN).

### Issue: Windows Hello prompt does not appear when running over Remote Desktop (RDP)
- **Cause:** Microsoft Windows disables biometric verification APIs when connected via standard Remote Desktop sessions.
- **Solution:** Use your local Digital Wellbeing fallback PIN while connected over Remote Desktop.

---

## 3. Browser Domain Tracking

### Issue: Browser usage is tracked, but domain names (e.g. github.com) are not appearing
- **Cause:** Domain extraction utilizes Windows UI Automation (UIA) to read the browser address bar. If accessibility hooks are disabled in the browser, domain inspection may fall back to the window title.
- **Solution:**
  1. Ensure you are using a supported Chromium or Gecko-based browser: Google Chrome, Microsoft Edge, Brave, Mozilla Firefox, Opera, or Vivaldi.
  2. If using Brave or Chrome with strict sandboxing flags, verify that the browser window title displays the page title.

---

## 4. Antivirus False Positives with PyInstaller

### Issue: Antivirus flags `DigitalWellbeing.exe` as generic malware (Heur/Trojan)
- **Cause:** Digital Wellbeing is bundled as a standalone Windows executable using PyInstaller. Heuristic scanners frequently flag unfamiliar, newly packaged PyInstaller binaries until community reputation is established.
- **Solution:**
  1. Verify the binary's integrity: Compare the SHA-256 hash of your downloaded installer against the published release checksums.
  2. Add an exception in Windows Defender / your antivirus suite for `DigitalWellbeing.exe` or the installation directory `%LOCALAPPDATA%\Programs\DigitalWellbeing`.

---

## 5. Corrupted Database or Crash on Startup

### Issue: Digital Wellbeing crashes immediately upon launch
- **Inspection:** Check the startup diagnostic log:
  ```powershell
  Get-Content "$env:LOCALAPPDATA\DigitalWellbeing\startup_diagnostic.txt" -Tail 50
  Get-Content "$env:LOCALAPPDATA\DigitalWellbeing\digital_wellbeing.log" -Tail 50
  ```
- **Recovery:** If the SQLite database became corrupted due to an abrupt system shutdown:
  1. Close any running Digital Wellbeing processes.
  2. Rename the database file:
     ```powershell
     Rename-Item "$env:LOCALAPPDATA\DigitalWellbeing\digital_wellbeing.db" "digital_wellbeing.db.corrupt"
     ```
  3. Relaunch Digital Wellbeing. The application will automatically create a fresh SQLite database.

---

## 6. High DPI & Display Scaling

### Issue: Text appears slightly blurry or oversized on high-resolution displays
- **Solution:**
  1. Digital Wellbeing automatically enables Per-Monitor DPI Aware v2 scaling (`Qt::AA_EnableHighDpiScaling`).
  2. If scaling issues persist, right-click `DigitalWellbeing.exe` → **Properties** → **Compatibility** → **Change high DPI settings** → Check "Override high DPI scaling behavior" and select **Application**.
