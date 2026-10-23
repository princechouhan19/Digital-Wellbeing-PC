"""Digital Wellbeing Uninstaller — matching professional dark UI."""
import os, sys, subprocess, shutil, winreg
from pathlib import Path

# Add installer dir to sys.path for branding helper
_installer_dir = Path(__file__).resolve().parent
if str(_installer_dir) not in sys.path:
    sys.path.insert(0, str(_installer_dir))

from PySide6.QtCore import Qt, QThread, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QProgressBar, QCheckBox, QStackedWidget)

from branding import get_logo_pixmap, get_app_icon

APP, EXE = "Digital Wellbeing", "DigitalWellbeing.exe"
ACCENT, BG, CARD, LINE = "#3E8BFF", "#0B0B0E", "#17171D", "#26262D"
TXT, SUB, DANGER, SUCCESS = "#F3F3F6", "#9B9BA6", "#FF6B6B", "#4CAF50"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\DigitalWellbeing"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
DATA_DIRS = [Path(os.environ.get("APPDATA", "")) / APP,
             Path(os.environ.get("LOCALAPPDATA", "")) / APP,
             Path(os.environ.get("APPDATA", "")) / "DigitalWellbeing",
             Path(os.environ.get("LOCALAPPDATA", "")) / "DigitalWellbeing",
             Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / APP]


def install_dir():
    d = Path(sys.executable).resolve().parent
    if (d / EXE).exists() or d.name.lower() == APP.lower():
        return d
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        loc, _ = winreg.QueryValueEx(k, "InstallLocation"); winreg.CloseKey(k)
        if loc and Path(loc).is_dir(): return Path(loc)
    except OSError:
        pass
    return d


class UninstallWorker(QThread):
    step = Signal(str, int); detail = Signal(str); done_ok = Signal()
    def __init__(self, target, keep):
        super().__init__(); self.target, self.keep = Path(target), keep
    def run(self):
        try: self._run()
        except Exception as e: self.step.emit("Error: %s" % e, 100)
    def _run(self):
        self.step.emit("Closing active " + APP + " instances…", 5)
        for exe in (EXE, "DigitalWellbeing.exe"):
            subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True)
            
        self.step.emit("Removing desktop and start menu shortcuts…", 25)
        for lnk in (Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Digital Wellbeing.lnk",
                    Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "Digital Wellbeing.lnk"):
            try: lnk.unlink()
            except OSError: pass
            
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(k, "DigitalWellbeing"); winreg.CloseKey(k)
        except OSError: pass
        
        self.step.emit("Unregistering application…", 45)
        try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        except OSError: pass
        try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\AppUserModelId\PrinceChouhan.DigitalWellbeing.App")
        except OSError: pass
        
        if not self.keep:
            self.step.emit("Removing local database and profile settings…", 60)
            for d in DATA_DIRS:
                if d.is_dir(): shutil.rmtree(d, ignore_errors=True)
                
        self.step.emit("Removing installed files…", 75)
        me = Path(sys.executable).resolve(); d = self.target
        if d.is_dir():
            for p in sorted(d.rglob("*"), reverse=True):
                try:
                    if p.is_file() and p.resolve() != me: p.unlink()
                    elif p.is_dir():
                        try: p.rmdir()
                        except OSError: pass
                except OSError: pass
                
        self.step.emit("Uninstall complete", 100); self.done_ok.emit()


class TitleBar(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedHeight(40)
        lay = QHBoxLayout(self); lay.setContentsMargins(20, 0, 10, 0)
        t = QLabel("Uninstall " + APP); t.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % SUB)
        lay.addWidget(t); lay.addStretch()
        b = QPushButton("✕"); b.setFixedSize(34, 26); b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("QPushButton{background:transparent;color:%s;border:none;border-radius:6px;}"
                        "QPushButton:hover{background:#1E1E24;color:%s;}" % (SUB, TXT))
        b.clicked.connect(self.window().close); lay.addWidget(b)
    def mousePressEvent(self, e):
        try: self.window().windowHandle().startSystemMove()
        except Exception: pass


class Uninstaller(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Uninstall " + APP)
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.setFixedSize(560, 420)
        self.worker = None; self.target = install_dir()
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(TitleBar())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_confirm()); self.stack.addWidget(self._page_progress())
        self.stack.addWidget(self._page_done())
        root.addWidget(self.stack, 1)
        bar = QWidget(); bar.setFixedHeight(70)
        lay = QHBoxLayout(bar); lay.setContentsMargins(28, 0, 28, 0)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setObjectName("ghost")
        self.cancel_btn.clicked.connect(self.close)
        self.go_btn = QPushButton("Uninstall"); self.go_btn.setObjectName("danger")
        self.go_btn.clicked.connect(self._go)
        lay.addWidget(self.cancel_btn); lay.addStretch(); lay.addWidget(self.go_btn)
        root.addWidget(bar)
        self.stack.setCurrentIndex(0); self.setStyleSheet(self._qss())

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

    def _logo(self, sym, color):
        lb = QLabel()
        lb.setFixedSize(54, 54)
        lb.setAlignment(Qt.AlignCenter)
        if sym != "✓":
            pix = get_logo_pixmap(54)
            if pix and not pix.isNull():
                lb.setPixmap(pix)
                return lb
        lb.setText(sym)
        lb.setStyleSheet(f"background:{color};color:white;font-size:26px;font-weight:700;border-radius:27px;")
        return lb

    def _page_confirm(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(32, 14, 32, 0); lay.setSpacing(10)
        lay.addWidget(self._logo("DW", ACCENT))
        t = QLabel("Uninstall " + APP); t.setStyleSheet("color:%s;font-size:24px;font-weight:700;" % TXT)
        lay.addWidget(t)
        s = QLabel(APP + " will be completely removed from this computer.\n\n" + str(self.target))
        s.setWordWrap(True); s.setStyleSheet("color:%s;font-size:13px;line-height:1.4;" % SUB); lay.addWidget(s)
        self.keep_cb = QCheckBox("Keep my activity history and local settings (recommended)")
        self.keep_cb.setChecked(True); lay.addWidget(self.keep_cb)
        note = QLabel("If unchecked, all historical screen-time records in AppData will be permanently deleted.")
        note.setWordWrap(True); note.setStyleSheet("color:%s;font-size:11px;" % DANGER)
        lay.addWidget(note); lay.addStretch()
        return w

    def _page_progress(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(32, 14, 32, 0); lay.setSpacing(14)
        lay.addStretch()
        t = QLabel("Uninstalling " + APP + "…")
        t.setStyleSheet("color:%s;font-size:20px;font-weight:700;" % TXT); lay.addWidget(t)
        self.bar = QProgressBar(); self.bar.setFixedHeight(6); self.bar.setRange(0, 100)
        self.bar.setTextVisible(False); lay.addWidget(self.bar)
        self.p_step = QLabel("Preparing…"); self.p_step.setStyleSheet("color:%s;font-size:13px;" % SUB)
        lay.addWidget(self.p_step); lay.addStretch()
        return w

    def _page_done(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(32, 14, 32, 0); lay.setSpacing(10)
        lay.addStretch()
        row = QHBoxLayout(); row.addStretch(); row.addWidget(self._logo("✓", SUCCESS)); row.addStretch()
        lay.addLayout(row)
        t = QLabel(APP + " was successfully uninstalled"); t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("color:%s;font-size:21px;font-weight:700;" % TXT); lay.addWidget(t)
        self.done_note = QLabel(""); self.done_note.setAlignment(Qt.AlignCenter)
        self.done_note.setStyleSheet("color:%s;font-size:12px;" % SUB); lay.addWidget(self.done_note)
        lay.addStretch()
        return w

    def _qss(self):
        return ("QPushButton#danger{background:%s;color:white;border:none;border-radius:8px;"
                "padding:11px 28px;font-weight:600;font-size:14px;}"
                "QPushButton#danger:hover{background:#FF8585;}"
                "QPushButton#danger:disabled{background:#23232B;color:#66666F;}"
                "QPushButton#ghost{background:transparent;color:%s;border:1px solid %s;"
                "border-radius:8px;padding:10px 24px;font-size:13px;}"
                "QPushButton#ghost:hover{color:%s;border-color:#3A3A46;}"
                "QCheckBox{color:%s;font-size:13px;spacing:10px;}"
                "QCheckBox::indicator{width:18px;height:18px;border-radius:5px;"
                "border:1px solid %s;background:%s;}"
                "QCheckBox::indicator:checked{background:%s;border-color:%s;}"
                "QProgressBar{background:#1D1D24;border:none;border-radius:3px;}"
                "QProgressBar::chunk{background:%s;border-radius:3px;}"
                % (DANGER, SUB, LINE, TXT, TXT, LINE, CARD, ACCENT, ACCENT, ACCENT))

    def _go(self):
        self.stack.setCurrentIndex(1)
        self.cancel_btn.setVisible(False); self.go_btn.setVisible(False)
        self.worker = UninstallWorker(self.target, self.keep_cb.isChecked())
        self.worker.step.connect(lambda s, p: (self.p_step.setText(s), self.bar.setValue(p)))
        self.worker.done_ok.connect(self._finished)
        self.worker.start()

    def _finished(self):
        kept = self.keep_cb.isChecked()
        self.done_note.setText("Your local activity history and settings were kept on this PC." if kept
                               else "All application data and database records were removed from this PC.")
        self.stack.setCurrentIndex(2)
        self.go_btn.setText("Close"); self.go_btn.setVisible(True)
        try: self.go_btn.clicked.disconnect()
        except Exception: pass
        self.go_btn.clicked.connect(self._bye)

    def _bye(self):
        try:
            cmd = 'timeout /t 2 /nobreak >nul & rmdir /s /q "%s"' % self.target
            subprocess.Popen(["cmd", "/c", cmd],
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
        self.close()

    def closeEvent(self, e):
        if self.worker is not None and self.worker.isRunning(): e.ignore()
        else: e.accept()


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PrinceChouhan.DigitalWellbeing.Uninstaller.4.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    from branding import get_app_icon
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    win = Uninstaller()
    if not app_icon.isNull():
        win.setWindowIcon(app_icon)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
