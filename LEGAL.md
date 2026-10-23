# Legal Notices and Disclaimers

This document contains legal notices, third-party software licenses, intellectual property acknowledgments, and operational disclaimers for **Digital Wellbeing for Windows**.

---

## 1. Application License

Digital Wellbeing for Windows is free and open-source software distributed under the terms of the **MIT License**.

> Copyright (c) 2026 Prince Chouhan and Digital Wellbeing Contributors.
> 
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the conditions detailed in the [LICENSE](LICENSE) file.

---

## 2. Disclaimer of Warranties and Limitation of Liability

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

IN NO EVENT SHALL THE AUTHORS, COPYRIGHT HOLDERS, OR CONTRIBUTORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE, INCLUDING BUT NOT LIMITED TO:
- System downtime, data corruption, or operating system instability.
- Unintentional blocking or closure of applications, websites, or background tasks during Focus Mode or App Locker sessions.
- Incompatibilities with third-party software, anti-cheat mechanisms, antivirus engines, or Windows security updates.
- Accuracy or completeness of third-party DNS blocklists used by SafeBrowse.

---

## 3. System Modifications & Privileged Actions Notice

Certain features of Digital Wellbeing interact directly with core Windows operating system components:

1. **Hosts File Modification (`SafeBrowse` and `Focus Mode`):**
   - SafeBrowse and Focus Mode DNS blocking operate by appending loopback redirections (`127.0.0.1` and `::1`) into the Windows hosts file located at `C:\Windows\System32\drivers\etc\hosts`.
   - Modifying this file requires elevated administrative privileges (User Account Control / UAC prompt).
   - Digital Wellbeing isolates all hosts file writes into atomic operations, creates an automatic backup at `C:\Windows\System32\drivers\etc\hosts.dw.bak`, and encapsulates its entries inside dedicated `# DIGITAL WELLBEING BLOCK` and `# DW-SAFEBROWSE` markers.
   - When disabling these features or uninstalling the software, the managed sections are cleanly deleted and DNS caches are flushed via `ipconfig /flushdns`.

2. **Process Management & Termination:**
   - Focus Mode and App Locker monitor running processes and may terminate unauthorized processes or close unauthorized browser tabs according to user-configured profiles.
   - Core Windows system processes (e.g., `explorer.exe`, `dwm.exe`, `csrss.exe`, `lsass.exe`, `services.exe`) are strictly protected by an immutable allowlist and will never be closed or manipulated.

---

## 4. Third-Party Software and Open-Source Acknowledgments

Digital Wellbeing relies upon several exceptional open-source libraries, frameworks, and datasets. We gratefully acknowledge their authors and maintainers:

### PySide6 (Qt for Python)
- **Copyright:** (C) 2026 The Qt Company Ltd. and other contributors.
- **License:** GNU Lesser General Public License (LGPL) v3 / Commercial.
- **Notice:** PySide6 and Qt libraries are dynamically linked as shared libraries (`.pyd` / `.dll`). In compliance with the LGPL v3, users have the freedom to replace the bundled Qt shared libraries with compatible versions. The source code of Qt and PySide6 is available at [qt.io](https://www.qt.io) and [code.qt.io](https://code.qt.io).

### pywin32
- **Copyright:** (C) Mark Hammond and contributors.
- **License:** Python Software Foundation (PSF) License.
- **Usage:** Windows API access, process token inspection, shell notifications, and event loops.

### psutil
- **Copyright:** (C) 2009, Jay Loden, Dave Daeschler, Giampaolo Rodola.
- **License:** BSD 3-Clause License.
- **Usage:** Process table queries, memory usage, CPU monitoring, and execution paths.

### pyqtgraph
- **Copyright:** (C) 2020 Luke Campagnola and PyQtGraph developers.
- **License:** MIT License.
- **Usage:** Real-time data visualization, interactive chart foundations, and analytics curves.

### StevenBlack/hosts
- **Copyright:** (C) 2026 Steven Black and contributors.
- **License:** MIT License.
- **Usage:** Community-curated DNS blocklists utilized by the SafeBrowse adult content shield.

### Inter Font Family
- **Copyright:** (C) 2016-2024 Rasmus Andersson.
- **License:** SIL Open Font License 1.1 (OFL).
- **Usage:** Bundled typography for the Aurora Apple-grade interface.

### Inno Setup
- **Copyright:** (C) 1997-2024 Jordan Russell and Martijn Laan.
- **License:** Inno Setup License.
- **Usage:** Packaging and generating the Windows installer binary (`DigitalWellbeingSetup.exe`).

---

## 5. Trademark Disclaimers

- **Microsoft, Windows, Windows Hello, and Segoe UI** are registered trademarks of Microsoft Corporation in the United States and other countries.
- **Apple, macOS, and Sequoia** are registered trademarks of Apple Inc. in the United States and other countries. References to "Apple-grade" or "macOS Sequoia inspired" describe the visual styling and aesthetic design principles of the interface and do not imply any affiliation, sponsorship, or endorsement by Apple Inc.
- **GitHub** is a registered trademark of GitHub, Inc.
- All other trademarks, registered trademarks, product names, and company names or logos mentioned in this software are the property of their respective owners.
