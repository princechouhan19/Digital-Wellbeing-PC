"""Digital Wellbeing Setup — Professional Installer Wizard. Frameless dark UI, PySide6."""
import os, sys, subprocess, shutil, winreg
from pathlib import Path
from datetime import datetime

# Add installer dir to sys.path for branding helper
_installer_dir = Path(__file__).resolve().parent
if str(_installer_dir) not in sys.path:
    sys.path.insert(0, str(_installer_dir))

from PySide6.QtCore import Qt, QThread, Signal, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QLineEdit, QProgressBar, QCheckBox, QTextEdit, QFileDialog, QStackedWidget, QFrame)

from branding import get_logo_pixmap, get_app_icon

APP, VER, EXE = "Digital Wellbeing", "4.1.0", "DigitalWellbeing.exe"
ACCENT, BG, CARD, LINE = "#3E8BFF", "#0B0B0E", "#17171D", "#26262D"
TXT, SUB, DANGER, SUCCESS = "#F3F3F6", "#9B9BA6", "#FF6B6B", "#4CAF50"

def get_default_install_dir():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = str(Path.home() / "AppData" / "Local")
    return Path(local_app_data).resolve() / "Programs" / APP

DEFAULT_DIR = get_default_install_dir()
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\DigitalWellbeing"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUMID_KEY = r"Software\Classes\AppUserModelId\PrinceChouhan.DigitalWellbeing.App"

LICENSE_TEXT = """Digital Wellbeing for Windows
Copyright (c) 2026 Prince Chouhan. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to
the following conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

PRIVACY ARCHITECTURE:
Digital Wellbeing operates exclusively on your local machine. All activity timestamps,
window classifications, domain trackers, and statistical summaries are recorded to a
local SQLite database on your device and are never transmitted to external servers.
Telemetry is disabled by default and only activates if you explicitly choose to opt in.

DISCLAIMER:
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""


def payload_dir():
    mp = getattr(sys, "_MEIPASS", None)
    if mp:
        p1 = Path(mp) / "payload"
        if p1.is_dir():
            return p1
        if (Path(mp) / EXE).is_file():
            return Path(mp)
            
    # Check adjacent or repo folders
    candidates = [
        Path(sys.executable).resolve().parent / "payload",
        Path(__file__).resolve().parent / "payload",
        Path(__file__).resolve().parent.parent / "build" / "installer_payload",
        Path(__file__).resolve().parent.parent / "dist" / "DigitalWellbeing",
    ]
    for c in candidates:
        if c.is_dir() and (c / EXE).is_file():
            return c
    return None


class InstallWorker(QThread):
    step = Signal(str, int); detail = Signal(str); progress = Signal(int)
    failed = Signal(str); done_ok = Signal()

    def __init__(self, payload, target, opts):
        super().__init__(); self.payload, self.target, self.opts = payload, target, opts

    def run(self):
        try: self._run()
        except Exception as e: self.failed.emit(str(e))

    def _run(self):
        t, opts = Path(self.target), self.opts
        self.step.emit("Closing active instances…", 2)
        for exe in (EXE, "DigitalWellbeing.exe"):
            subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True)
            
        self.step.emit("Preparing installation directory…", 5)
        if t.exists():
            shutil.rmtree(t, ignore_errors=True)
        t.mkdir(parents=True, exist_ok=True)
        
        files = [p for p in self.payload.rglob("*") if p.is_file()]
        total = sum(p.stat().st_size for p in files) or 1; done = 0
        for i, p in enumerate(files):
            dst = t / p.relative_to(self.payload)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)
            done += p.stat().st_size
            self.detail.emit(str(p.relative_to(self.payload)))
            self.progress.emit(8 + int(70 * done / total))
            if i % 5 == 0: self.msleep(1)
            
        self.step.emit("Creating system shortcuts…", 80)
        def lnk(dest):
            dest_p = Path(dest)
            dest_p.parent.mkdir(parents=True, exist_ok=True)
            target_exe = str(t / EXE)
            # 1. Native COM shortcut
            try:
                import win32com.client
                ws = win32com.client.Dispatch("WScript.Shell")
                s = ws.CreateShortcut(str(dest_p))
                s.TargetPath = target_exe
                s.WorkingDirectory = str(t)
                s.IconLocation = f"{target_exe},0"
                s.Save()
                return
            except Exception:
                pass
            # 2. PowerShell fallback
            try:
                cmd = ("$ws=New-Object -ComObject WScript.Shell;"
                       f"$s=$ws.CreateShortcut('{dest_p}');$s.TargetPath='{target_exe}';"
                       f"$s.WorkingDirectory='{t}';$s.IconLocation='{target_exe},0';$s.Save()")
                subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True)
            except Exception:
                pass
            
        smenu = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs"
        lnk(str(smenu / "Digital Wellbeing.lnk"))
        if opts.get("desktop"):
            lnk(str(Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "Digital Wellbeing.lnk"))
            
        self.step.emit("Registering application in Windows…", 88)
        kb = int(total // 1024)
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        for name, val, typ in (
            ("DisplayName", "Digital Wellbeing", winreg.REG_SZ),
            ("DisplayVersion", VER, winreg.REG_SZ),
            ("Publisher", "Prince Chouhan", winreg.REG_SZ),
            ("InstallLocation", str(t), winreg.REG_SZ),
            ("DisplayIcon", f'"{t / EXE}",0', winreg.REG_SZ),
            ("UninstallString", f'"{t / "Uninstall Digital Wellbeing.exe"}"', winreg.REG_SZ),
            ("QuietUninstallString", f'"{t / "Uninstall Digital Wellbeing.exe"}" --silent', winreg.REG_SZ),
            ("InstallDate", datetime.now().strftime("%Y%m%d"), winreg.REG_SZ),
            ("NoModify", 1, winreg.REG_DWORD),
            ("NoRepair", 1, winreg.REG_DWORD),
            ("EstimatedSize", kb, winreg.REG_DWORD),
        ):
            winreg.SetValueEx(k, name, 0, typ, val)
        winreg.CloseKey(k)
        
        # Register AppUserModelID for Windows 10/11 Notifications and Action Center
        try:
            ak = winreg.CreateKey(winreg.HKEY_CURRENT_USER, AUMID_KEY)
            winreg.SetValueEx(ak, "DisplayName", 0, winreg.REG_SZ, APP)
            icon_path = str(t / "assets" / "icons" / "app_icon.ico")
            if not Path(icon_path).exists():
                icon_path = str(t / "_internal" / "assets" / "icons" / "app_icon.ico")
            winreg.SetValueEx(ak, "IconUri", 0, winreg.REG_SZ, icon_path)
            winreg.SetValueEx(ak, "ShowInSettings", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(ak)
        except OSError:
            pass

        if opts.get("autostart"):
            rk = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
            winreg.SetValueEx(rk, "DigitalWellbeing", 0, winreg.REG_SZ, str(t / EXE))
            winreg.CloseKey(rk)
            
        # Refresh Windows Shell notifications and cache
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, 0, 0)
        except Exception:
            pass
            
        self.progress.emit(100); self.done_ok.emit()


class TitleBar(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedHeight(44)
        lay = QHBoxLayout(self); lay.setContentsMargins(20, 0, 12, 0)
        t = QLabel(f"{APP} Setup"); t.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % SUB)
        lay.addWidget(t); lay.addStretch()
        for sym, cb in (("—", lambda: self.window().showMinimized()), ("✕", self.window().close)):
            b = QPushButton(sym); b.setFixedSize(34, 26); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:transparent;color:%s;border:none;border-radius:6px;font-size:13px;}"
                            "QPushButton:hover{background:#1E1E24;color:%s;}" % (SUB, TXT))
            b.clicked.connect(cb); lay.addWidget(b)
            
    def mousePressEvent(self, e):
        try: self.window().windowHandle().startSystemMove()
        except Exception: pass


class Installer(QWidget):
    STEPS = ["Welcome", "License", "Options", "Installing", "Complete"]

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(f"{APP} Setup")
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.setFixedSize(900, 580)
        self.worker = None; self.target = DEFAULT_DIR; self.opts = {}
        self._auto_close_timer = None; self._countdown = 2
        
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        content = QHBoxLayout(); content.setSpacing(0); root.addLayout(content)
        content.addWidget(self._brand_panel())
        
        right = QVBoxLayout(); right.setSpacing(0); content.addLayout(right, 1)
        right.addWidget(TitleBar())
        
        self.stack = QStackedWidget(); self.stack.setObjectName("stack")
        for fn in (self._page_welcome, self._page_license, self._page_location,
                   self._page_progress, self._page_done):
            self.stack.addWidget(fn())
        right.addWidget(self.stack, 1)
        right.addWidget(self._navbar())
        
        self._set_step(0); self.stack.setCurrentIndex(0); self._update_nav()
        self.setStyleSheet(self._qss())

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                LR_DEFAULTSIZE = 0x00000040
                search_paths = [
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "app_icon.ico")),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "icons", "app_icon.ico")),
                    os.path.abspath(os.path.join(getattr(sys, '_MEIPASS', ''), 'assets', 'icons', 'app_icon.ico')),
                ]
                ico_path = next((p for p in search_paths if os.path.exists(p)), None)
                if ico_path:
                    h_icon_big = user32.LoadImageW(None, ico_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
                    h_icon_sm = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    hwnd = int(self.winId())
                    if h_icon_big:
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                    if h_icon_sm:
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_sm)
            except Exception:
                pass

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        p.fillPath(path, QColor(BG)); p.setPen(QColor(LINE)); p.drawPath(path)

    def _brand_panel(self):
        panel = QFrame()
        panel.setObjectName("brandPanel")
        panel.setFixedWidth(268)
        panel.setStyleSheet(f"""
            QFrame#brandPanel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0F131D, stop:1 #0B0B0E);
                border: none;
                border-right: 1px solid {LINE};
                border-top-left-radius: 14px;
                border-bottom-left-radius: 14px;
            }}
            QFrame#brandPanel QLabel {{
                background: transparent;
                border: none;
                border-right: none;
                padding: 0px;
                margin: 0px;
            }}
        """)
        lay = QVBoxLayout(panel); lay.setContentsMargins(26, 30, 22, 24); lay.setSpacing(6)
        
        # Google Digital Wellbeing Official Logo
        logo = QLabel(); logo.setFixedSize(52, 52); logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("border: none; background: transparent;")
        pix = get_logo_pixmap(52)
        if pix and not pix.isNull():
            logo.setPixmap(pix)
        else:
            logo.setText("DW")
            logo.setStyleSheet(f"background:{ACCENT};color:white;font-size:20px;font-weight:700;border-radius:12px;border:none;")
        lay.addWidget(logo); lay.addSpacing(10)
        
        name = QLabel("Digital Wellbeing")
        name.setStyleSheet(f"color:{TXT};font-size:19px;font-weight:700;letter-spacing:-0.3px;border:none;background:transparent;")
        tag = QLabel("Intelligent screen-time & focus suite.")
        tag.setWordWrap(True)
        tag.setStyleSheet(f"color:{SUB};font-size:12px;line-height:1.4;border:none;background:transparent;")
        lay.addWidget(name); lay.addWidget(tag); lay.addSpacing(26)
        
        self.step_labels = []
        for s in self.STEPS:
            lb = QLabel(s)
            lb.setStyleSheet(f"color:{SUB};font-size:13px;padding:6px 0;border:none;background:transparent;")
            self.step_labels.append(lb); lay.addWidget(lb)
            
        lay.addStretch()
        ver = QLabel(f"v{VER}  ·  Prince Chouhan")
        ver.setStyleSheet(f"color:{SUB};font-size:11px;font-weight:500;border:none;background:transparent;")
        lay.addWidget(ver)
        return panel

    def _navbar(self):
        bar = QWidget(); bar.setFixedHeight(74)
        lay = QHBoxLayout(bar); lay.setContentsMargins(32, 0, 32, 0)
        self.back_btn = QPushButton("Back"); self.back_btn.setObjectName("ghost")
        self.back_btn.setCursor(Qt.PointingHandCursor); self.back_btn.clicked.connect(self._back)
        self.primary = QPushButton("Get started"); self.primary.setObjectName("primary")
        self.primary.setCursor(Qt.PointingHandCursor); self.primary.clicked.connect(self._primary)
        lay.addWidget(self.back_btn); lay.addStretch(); lay.addWidget(self.primary)
        return bar

    def _h1(self, text):
        lb = QLabel(text); lb.setStyleSheet("color:%s;font-size:25px;font-weight:700;letter-spacing:-0.4px;" % TXT)
        return lb
        
    def _sub(self, text):
        lb = QLabel(text); lb.setWordWrap(True)
        lb.setStyleSheet("color:%s;font-size:13px;line-height:1.5;" % SUB)
        return lb

    # ---------- pages ----------
    def _page_welcome(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(38, 24, 38, 16); lay.setSpacing(10)
        lay.addSpacing(4)
        
        # Clean, modern header without redundant double logo
        lay.addWidget(self._h1("Welcome to Digital Wellbeing"))
        lay.addWidget(self._sub("Professional digital wellness, screen-time intelligence, and focus management for Windows."))
        lay.addSpacing(12)
        
        # Professional Features Card with strict scoped styling
        feat_box = QFrame()
        feat_box.setObjectName("featBox")
        feat_box.setStyleSheet(f"""
            QFrame#featBox {{
                background: {CARD};
                border: 1px solid {LINE};
                border-radius: 12px;
            }}
            QFrame#featBox QLabel {{
                background: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        f_lay = QVBoxLayout(feat_box)
        f_lay.setContentsMargins(22, 16, 22, 16)
        f_lay.setSpacing(12)
        
        feats = [
            ("Precision Screen Analytics", "Automated tracking of foreground applications and domains with idle distinction."),
            ("Smart Focus & App Shield", "Distraction blocking, customizable focus sessions, and granular application limits."),
            ("SleepGuard & Circadian Protection", "Intelligent downtime scheduling, bedtime reminders, and screen rest protection."),
            ("Private by Design", "100% offline local SQLite database — your personal activity data never leaves this PC.")
        ]
        for title, desc in feats:
            col = QVBoxLayout()
            col.setSpacing(2)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600; border: none; background: transparent; padding: 0;")
            d_lbl = QLabel(desc)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet(f"color: {SUB}; font-size: 12px; border: none; background: transparent; padding: 0;")
            col.addWidget(t_lbl)
            col.addWidget(d_lbl)
            f_lay.addLayout(col)
            
        lay.addWidget(feat_box)
        lay.addStretch()
        
        info = QLabel("Designed for Windows 10 & 11 · User-space installation (no administrator privileges required)")
        info.setStyleSheet("color: #727280; font-size: 11px;")
        lay.addWidget(info)
        return w
        return w

    def _page_license(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(38, 20, 38, 12); lay.setSpacing(12)
        lay.addWidget(self._h1("Software License Terms"))
        lay.addWidget(self._sub("Please review the licensing and privacy conditions before continuing."))
        
        box = QTextEdit(); box.setReadOnly(True); box.setPlainText(LICENSE_TEXT)
        box.setStyleSheet("QTextEdit{background:%s;color:#C9C9D3;border:1px solid %s;"
                          "border-radius:10px;padding:12px;font-size:12px;line-height:1.5;}" % (CARD, LINE))
        lay.addWidget(box, 1)
        
        self.accept_cb = QCheckBox("I have reviewed and accept the terms of this license agreement")
        self.accept_cb.toggled.connect(lambda v: self.primary.setEnabled(v))
        lay.addWidget(self.accept_cb)
        return w

    def _page_location(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(38, 20, 38, 12); lay.setSpacing(14)
        lay.addWidget(self._h1("Installation Options"))
        lay.addWidget(self._sub("Choose the installation directory and system integration options."))
        
        row = QHBoxLayout()
        self.target_edit = QLineEdit(str(DEFAULT_DIR)); self.target_edit.setFixedHeight(38)
        browse = QPushButton("Browse…"); browse.setObjectName("ghost"); browse.setFixedHeight(38)
        browse.setCursor(Qt.PointingHandCursor); browse.clicked.connect(self._browse)
        row.addWidget(self.target_edit, 1); row.addWidget(browse)
        lay.addLayout(row)
        
        lay.addSpacing(6)
        self.desktop_cb = QCheckBox("Create Desktop shortcut icon"); self.desktop_cb.setChecked(True)
        self.autostart_cb = QCheckBox("Start Digital Wellbeing automatically when Windows boots")
        lay.addWidget(self.desktop_cb); lay.addWidget(self.autostart_cb)
        
        self.loc_info = QLabel(""); self.loc_info.setWordWrap(True)
        self.loc_info.setStyleSheet("color:%s;font-size:12px;" % SUB)
        lay.addWidget(self.loc_info); lay.addStretch()
        return w

    def _page_progress(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(38, 20, 38, 12); lay.setSpacing(14)
        lay.addStretch()
        
        head = QHBoxLayout()
        prog_logo = QLabel(); prog_logo.setFixedSize(48, 48)
        pix = get_logo_pixmap(48)
        if pix and not pix.isNull():
            prog_logo.setPixmap(pix)
        head.addWidget(prog_logo)
        
        t_col = QVBoxLayout(); t_col.setSpacing(3)
        self.p_title = QLabel("Installing Digital Wellbeing…")
        self.p_title.setStyleSheet("color:%s;font-size:22px;font-weight:700;" % TXT)
        t_col.addWidget(self.p_title)
        self.p_step = QLabel("Initializing deployment…")
        self.p_step.setStyleSheet("color:%s;font-size:13px;font-weight:500;" % SUB)
        t_col.addWidget(self.p_step)
        head.addLayout(t_col, 1)
        lay.addLayout(head)
        lay.addSpacing(10)
        
        self.bar = QProgressBar(); self.bar.setFixedHeight(8); self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        lay.addWidget(self.bar)
        
        self.p_detail = QLabel(""); self.p_detail.setStyleSheet("color:#6A6A76;font-size:11px;")
        lay.addWidget(self.p_detail); lay.addStretch()
        return w

    def _page_done(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(38, 20, 38, 16)
        lay.setSpacing(12); lay.addStretch()
        
        done_logo = QLabel(); done_logo.setFixedSize(68, 68); done_logo.setAlignment(Qt.AlignCenter)
        pix = get_logo_pixmap(68)
        if pix and not pix.isNull():
            done_logo.setPixmap(pix)
        else:
            done_logo.setText("✓")
            done_logo.setStyleSheet(f"background:{SUCCESS};color:white;font-size:32px;font-weight:700;border-radius:34px;")
            
        row = QHBoxLayout(); row.addStretch(); row.addWidget(done_logo); row.addStretch()
        lay.addLayout(row); lay.addSpacing(6)
        
        t = self._h1("Digital Wellbeing is Ready")
        t.setAlignment(Qt.AlignCenter); lay.addWidget(t)
        
        self.done_sub = self._sub(f"Successfully installed to {DEFAULT_DIR}")
        self.done_sub.setAlignment(Qt.AlignCenter); lay.addWidget(self.done_sub)
        lay.addSpacing(10)
        
        self.launch_cb = QCheckBox("Launch Digital Wellbeing when this setup closes")
        self.launch_cb.setChecked(True)
        self.launch_cb.toggled.connect(self._on_launch_toggled)
        cb_row = QHBoxLayout(); cb_row.addStretch(); cb_row.addWidget(self.launch_cb); cb_row.addStretch()
        lay.addLayout(cb_row)

        self.auto_close_lbl = QLabel("")
        self.auto_close_lbl.setAlignment(Qt.AlignCenter)
        self.auto_close_lbl.setStyleSheet("color:%s;font-size:12px;font-weight:500;" % SUB)
        lay.addWidget(self.auto_close_lbl)
        lay.addStretch()
        return w

    # ---------- styling & behavior ----------
    def _qss(self):
        return ("QWidget#stack{background:transparent;}"
                "QPushButton#primary{background:%s;color:white;border:none;border-radius:8px;"
                "padding:11px 32px;font-weight:600;font-size:14px;}"
                "QPushButton#primary:hover{background:#5C9DFF;}"
                "QPushButton#primary:disabled{background:#23232B;color:#66666F;}"
                "QPushButton#ghost{background:transparent;color:%s;border:1px solid %s;"
                "border-radius:8px;padding:10px 24px;font-size:13px;}"
                "QPushButton#ghost:hover{color:%s;border-color:#3A3A46;}"
                "QLineEdit{background:%s;color:%s;border:1px solid %s;border-radius:8px;padding:0 12px;font-size:13px;}"
                "QCheckBox{color:%s;font-size:13px;spacing:10px;}"
                "QCheckBox::indicator{width:18px;height:18px;border-radius:5px;"
                "border:1px solid %s;background:%s;}"
                "QCheckBox::indicator:checked{background:%s;border-color:%s;}"
                "QProgressBar{background:#1D1D24;border:none;border-radius:4px;}"
                "QProgressBar::chunk{background:%s;border-radius:4px;}"
                % (ACCENT, SUB, LINE, TXT, CARD, TXT, LINE, TXT, LINE, CARD, ACCENT, ACCENT, ACCENT))

    def _set_step(self, idx):
        for i, lb in enumerate(self.step_labels):
            if i < idx:
                lb.setText("✓  " + self.STEPS[i])
                lb.setStyleSheet(f"color:{ACCENT};font-size:13px;font-weight:500;padding:6px 0;border:none;background:transparent;")
            elif i == idx:
                lb.setText("●  " + self.STEPS[i])
                lb.setStyleSheet(f"color:{TXT};font-size:13px;font-weight:700;padding:6px 0;border:none;background:transparent;")
            else:
                lb.setText("○  " + self.STEPS[i])
                lb.setStyleSheet(f"color:{SUB};font-size:13px;padding:6px 0;border:none;background:transparent;")

    def _goto(self, idx):
        self.stack.setCurrentIndex(idx); self._set_step(idx); self._update_nav()
        if idx == 2: self._refresh_loc_info()

    def _back(self):
        i = self.stack.currentIndex()
        if i in (1, 2): self._goto(i - 1)

    def _primary(self):
        i = self.stack.currentIndex()
        if i == 0: self._goto(1)
        elif i == 1: self._goto(2)
        elif i == 2: self._start_install()
        elif i == 4: self._finish()

    def _update_nav(self):
        i = self.stack.currentIndex()
        self.back_btn.setVisible(i in (1, 2))
        labels = ["Get started", "Accept & continue", "Install now", "", "Finish"]
        self.primary.setText(labels[i])
        self.primary.setVisible(i != 3)
        if i == 1:
            self.primary.setEnabled(self.accept_cb.isChecked())
        else:
            self.primary.setEnabled(True)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Install Destination",
                                             self.target_edit.text() or str(DEFAULT_DIR))
        if d: self.target_edit.setText(d)
        self._refresh_loc_info()

    def _refresh_loc_info(self):
        t = Path(self.target_edit.text().strip() or str(DEFAULT_DIR)); self.target = t
        msgs = []
        if t.exists() and any(t.iterdir()):
            msgs.append(("Existing installation detected. It will be cleanly upgraded.", ACCENT))
        try:
            free = shutil.disk_usage(t.anchor).free / (1024 ** 3)
            msgs.append(("%.1f GB free storage available on drive %s" % (free, t.anchor), SUB))
        except Exception:
            pass
        self.loc_info.setText("\n".join(m for m, _ in msgs))
        self.loc_info.setStyleSheet("color:%s;font-size:12px;" % (msgs[0][1] if msgs else SUB))

    def _start_install(self):
        t = Path(self.target_edit.text().strip() or str(DEFAULT_DIR))
        if not t.name or t == Path(t.anchor):
            self.loc_info.setText("Please select a valid folder path (not a root drive).")
            self.loc_info.setStyleSheet("color:%s;font-size:12px;" % DANGER); return
        payload = payload_dir()
        if payload is None:
            self.loc_info.setText("Error: Embedded application payload not found.")
            self.loc_info.setStyleSheet("color:%s;font-size:12px;" % DANGER); return
            
        self.target = t
        self.opts = {"desktop": self.desktop_cb.isChecked(), "autostart": self.autostart_cb.isChecked()}
        self.worker = InstallWorker(payload, t, self.opts)
        self.worker.step.connect(lambda s, p: (self.p_step.setText(s), self.bar.setValue(p)))
        self.worker.detail.connect(self.p_detail.setText)
        self.worker.progress.connect(self.bar.setValue)
        self.worker.failed.connect(self._failed)
        self.worker.done_ok.connect(self._installed)
        self._goto(3); self.worker.start()

    def _failed(self, msg):
        self.p_title.setText("Installation Error"); self.p_step.setText(msg)
        self.p_step.setStyleSheet("color:%s;font-size:13px;" % DANGER)
        self.back_btn.setVisible(True); self.primary.setText("Retry"); self.primary.setVisible(True)

    def _installed(self):
        self.done_sub.setText(f"Installed to {self.target}")
        self._goto(4)
        self._start_auto_close()

    def _start_auto_close(self):
        self._countdown = 2
        self._update_auto_close_ui()
        if self._auto_close_timer is None:
            self._auto_close_timer = QTimer(self)
            self._auto_close_timer.timeout.connect(self._auto_close_tick)
        self._auto_close_timer.start(1000)

    def _auto_close_tick(self):
        self._countdown -= 1
        if self._countdown <= 0:
            if self._auto_close_timer and self._auto_close_timer.isActive():
                self._auto_close_timer.stop()
            self._finish()
        else:
            self._update_auto_close_ui()

    def _update_auto_close_ui(self):
        sec = f"{self._countdown} second" if self._countdown == 1 else f"{self._countdown} seconds"
        if hasattr(self, "launch_cb") and self.launch_cb.isChecked():
            self.auto_close_lbl.setText(f"Setup will close and launch Digital Wellbeing in {sec}…")
        else:
            self.auto_close_lbl.setText(f"Setup will close in {sec}…")
        self.primary.setText(f"Finish ({self._countdown}s)")

    def _on_launch_toggled(self, checked: bool):
        if not checked:
            if self._auto_close_timer and self._auto_close_timer.isActive():
                self._auto_close_timer.stop()
            self.auto_close_lbl.setText("Auto-close paused. Click Finish to exit.")
            self.primary.setText("Finish")
        else:
            self._start_auto_close()

    def _finish(self):
        if self._auto_close_timer and self._auto_close_timer.isActive():
            self._auto_close_timer.stop()
        if self.launch_cb.isChecked():
            try:
                subprocess.Popen([str(self.target / EXE)], cwd=str(self.target),
                                 creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            except Exception:
                pass
        self.close()

    def closeEvent(self, e):
        if self.worker is not None and self.worker.isRunning():
            e.ignore()
        else:
            if self._auto_close_timer and self._auto_close_timer.isActive():
                self._auto_close_timer.stop()
            e.accept()


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PrinceChouhan.DigitalWellbeing.Setup.4.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    from branding import get_app_icon
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    win = Installer()
    if not app_icon.isNull():
        win.setWindowIcon(app_icon)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
