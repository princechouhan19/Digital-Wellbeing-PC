"""
app_locker.py — Persistent App Locker engine for Digital Wellbeing.

App Locker is SEPARATE from Focus Mode:
  - Focus Mode:  temporary session-scoped productivity restrictions.
  - App Locker:  permanent, per-app protection requiring authentication.

Architecture:
  - AppLockerManager is a singleton QObject.
  - A 1-second QTimer polls the foreground window.
  - When a locked app is foregrounded without a valid grant, ``lock_triggered``
    is emitted so the UI layer can show the authentication dialog.
  - Temporary grants are in-memory only (session-scoped by default, which is
    the safest behaviour; grants are cleared on app restart/crash).
  - Locked app configuration persists in the SQLite ``app_locker_apps`` table.

System-safety policy:
  SYSTEM_SAFE processes are NEVER lockable and NEVER handled by App Locker.
  This prevents accidental breakage of Windows system processes.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger
from database.repository import Repository


# ── Safety constants ──────────────────────────────────────────────────────────

#: Processes that can never be added to the lock list.
#: The app itself is also protected — locking it would prevent authentication.
SYSTEM_SAFE: frozenset[str] = frozenset({
    "explorer.exe",
    "dwm.exe",
    "csrss.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "wininit.exe",
    "smss.exe",
    "taskmgr.exe",
    "systemsettings.exe",
    "searchapp.exe",
    "searchhost.exe",
    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
    "applicationframehost.exe",
    "textinputhost.exe",
    "ctfmon.exe",
    "sihost.exe",
    "runtimebroker.exe",
    "smartscreen.exe",
    "lockapp.exe",
    "securityhealthsystray.exe",
    # Windows screenshot and capture utilities (never blockable)
    "snippingtool.exe",
    "screenclippinghost.exe",
    # Digital Wellbeing & IDE runtime safety (never terminate the development environment)
    "digitalwellbeing.exe",   # the app itself
    "antigravity.exe",        # Antigravity IDE runtime
    "antigravity ide.exe",    # Antigravity IDE runner
    "python.exe",             # Python runtime (development/runner safety)
    "pythonw.exe",            # Python windowed runtime
    "py.exe",                 # Python launcher
    "pytest.exe",             # Test runner
    "registry",               # Windows registry pseudo-process
})


# ── Auth enums ────────────────────────────────────────────────────────────────

class AuthMethod(str, Enum):
    WINDOWS_HELLO  = "hello"        # Windows Hello (PIN, Face, Fingerprint)
    PIN            = "pin"          # Local PIN only
    HELLO_THEN_PIN = "hello_pin"    # Hello first, local PIN fallback
    NYW_PIN        = "pin"          # Backwards-compatibility alias


class AuthDuration(str, Enum):
    EVERY_LAUNCH   = "every_launch" # Re-authenticate on every foreground event
    FIVE_MIN       = "5_min"        # Grant lasts 5 minutes
    FIFTEEN_MIN    = "15_min"       # Grant lasts 15 minutes (default)
    UNTIL_CLOSE    = "until_close"  # Grant lasts until process exits


# ── Manager ───────────────────────────────────────────────────────────────────

class AppLockerManager(QObject):
    """Persistent App Locker engine — singleton.

    Signals:
        lock_triggered(process_name):  Emitted when a locked app is foregrounded
                                       without a valid grant.  The UI should show
                                       the authentication dialog and call
                                       ``grant_temporary_access()`` on success.
        state_changed():               Emitted when locked-app list or settings change.
    """

    lock_triggered = Signal(str)   # process_name
    state_changed  = Signal()

    _instance: Optional["AppLockerManager"] = None
    _lock = threading.Lock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls, repo: Optional[Repository] = None) -> "AppLockerManager":
        with cls._lock:
            if cls._instance is None:
                if repo is None:
                    repo = Repository()
                cls._instance = AppLockerManager(repo)
            return cls._instance

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def __init__(self, repo: Repository, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._grants: Dict[str, Optional[datetime]] = {}  # process_name -> expiry (None = until_close)
        self._pending_lock: Optional[str] = None          # process triggering auth; prevents re-entrant prompts
        self._dialog_open = False

        # Load config from DB
        self._enabled        = self._repo.get_setting("app_locker_enabled") == "true"
        self._auth_method    = AuthMethod(self._repo.get_setting("app_locker_auth_method") or "hello_pin")
        self._auth_duration  = AuthDuration(self._repo.get_setting("app_locker_auth_duration") or "15_min")

        # 1-second foreground-poll timer (separate from FocusManager timer)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        if self._enabled:
            self._timer.start()

        logger.info(
            "AppLockerManager initialised. enabled=%s method=%s duration=%s locked_apps=%d",
            self._enabled, self._auth_method.value, self._auth_duration.value,
            len(self._repo.get_locked_apps()),
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def auth_method(self) -> AuthMethod:
        return self._auth_method

    @property
    def auth_duration(self) -> AuthDuration:
        return self._auth_duration

    # ------------------------------------------------------------------
    # Enable / Disable
    # ------------------------------------------------------------------

    def enable(self) -> None:
        """Enable App Locker. No auth required to enable."""
        self._enabled = True
        self._repo.set_setting("app_locker_enabled", "true")
        self._timer.start()
        self.state_changed.emit()
        logger.info("App Locker enabled.")

    def disable(self) -> None:
        """Disable App Locker.  Caller is responsible for requiring auth BEFORE calling this."""
        self._enabled = False
        self._repo.set_setting("app_locker_enabled", "false")
        self._timer.stop()
        self._grants.clear()
        self._dialog_open = False
        self._pending_lock = None
        self.state_changed.emit()
        logger.info("App Locker disabled.")

    # ------------------------------------------------------------------
    # Locked app management
    # ------------------------------------------------------------------

    def get_locked_apps(self) -> List[dict]:
        """Return list of locked app dicts from the DB."""
        return self._repo.get_locked_apps()

    def is_locked(self, process_name: str) -> bool:
        """Return True if process_name is in the locked list."""
        p = process_name.lower()
        return any(row["process_name"] == p for row in self._repo.get_locked_apps())

    def add_locked_app(self, process_name: str, display_name: str,
                       exe_path: str = "", icon_path: Optional[str] = None) -> bool:
        """Add an app to the locked list.

        Returns False if process_name is in SYSTEM_SAFE or already locked.
        Caller is responsible for requiring auth before calling this from the UI.
        """
        p = process_name.lower()
        if p in SYSTEM_SAFE:
            logger.warning("Cannot lock system-safe process: %s", p)
            return False
            
        if exe_path:
            from utils.win_utils import is_safe_lock_target
            if not is_safe_lock_target(exe_path, p):
                logger.warning("Attempted to lock invalid application: %s (%s)", p, exe_path)
                return False
                
        ok = self._repo.add_locked_app(p, display_name, exe_path, icon_path)
        if ok:
            self.state_changed.emit()
            logger.info("Locked app added: %s (%s)", p, display_name)
        return ok

    def remove_locked_app(self, process_name: str) -> bool:
        """Remove an app from the locked list.
        Caller is responsible for requiring auth before calling this from the UI.
        """
        p = process_name.lower()
        ok = self._repo.remove_locked_app(p)
        if ok:
            self._grants.pop(p, None)
            self.state_changed.emit()
            logger.info("Locked app removed: %s", p)
        return ok

    def clear_all_locked_apps(self) -> bool:
        """Remove ALL locked apps.  Caller must require auth first."""
        ok = self._repo.clear_locked_apps()
        if ok:
            self._grants.clear()
            self.state_changed.emit()
            logger.info("All locked apps cleared.")
        return ok

    # ------------------------------------------------------------------
    # Temporary access grants
    # ------------------------------------------------------------------

    def grant_temporary_access(self, process_name: str) -> None:
        """Grant temporary access after successful authentication.

        Duration is determined by self._auth_duration setting.
        Grants are in-memory only — cleared when the app restarts.
        """
        p = process_name.lower()
        if self._auth_duration == AuthDuration.EVERY_LAUNCH:
            # Grant only for the current foreground event (expires immediately)
            self._grants[p] = datetime.now(timezone.utc) + timedelta(seconds=5)
        elif self._auth_duration == AuthDuration.FIVE_MIN:
            self._grants[p] = datetime.now(timezone.utc) + timedelta(minutes=5)
        elif self._auth_duration == AuthDuration.FIFTEEN_MIN:
            self._grants[p] = datetime.now(timezone.utc) + timedelta(minutes=15)
        elif self._auth_duration == AuthDuration.UNTIL_CLOSE:
            # None sentinel = grant lasts until process exits or the app restarts
            self._grants[p] = None

        self._dialog_open = False
        self._pending_lock = None
        
        # Restore the minimized/hidden window if we have it
        if hasattr(self, '_minimized_hwnds') and p in self._minimized_hwnds:
            hwnd = self._minimized_hwnds.pop(p)
            try:
                import win32gui
                import win32con
                win32gui.EnableWindow(hwnd, True)
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
            except Exception as e:
                logger.warning(f"Failed to restore window for {p}: {e}")

        logger.info("Access granted to %s. duration=%s", p, self._auth_duration.value)

    def revoke_access(self, process_name: str) -> None:
        """Manually revoke a temporary grant."""
        self._grants.pop(process_name.lower(), None)

    def is_access_granted(self, process_name: str) -> bool:
        """Return True if a valid temporary grant exists for process_name."""
        p = process_name.lower()
        if p not in self._grants:
            return False
        expiry = self._grants[p]
        if expiry is None:
            # UNTIL_CLOSE: check whether process is still running
            return self._is_process_running(p)
        if datetime.now(timezone.utc) < expiry:
            return True
        # Grant expired
        del self._grants[p]
        return False

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def set_auth_method(self, method: AuthMethod) -> None:
        self._auth_method = method
        self._repo.set_setting("app_locker_auth_method", method.value)
        self.state_changed.emit()

    def set_auth_duration(self, duration: AuthDuration) -> None:
        self._auth_duration = duration
        self._repo.set_setting("app_locker_auth_duration", duration.value)
        self.state_changed.emit()

    # ------------------------------------------------------------------
    # Internal tick
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        """Poll foreground window; emit lock_triggered if needed."""
        if not self._enabled:
            return

        try:
            import win32gui
            from tracker.foreground import _get_real_window_pid
            import psutil

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return

            pid = _get_real_window_pid(hwnd)
            if not pid:
                return

            p = psutil.Process(pid)
            p_name = p.name().lower()

            if p_name in SYSTEM_SAFE:
                return

            if not self.is_locked(p_name):
                return
                
            try:
                exe_path = p.exe()
            except Exception:
                exe_path = ""
                
            if exe_path:
                from utils.win_utils import is_safe_lock_target
                if not is_safe_lock_target(exe_path, p_name):
                    return

            if self.is_access_granted(p_name):
                return

            # Real Blocking: Disable window input entirely and hide it
            import win32con
            if not hasattr(self, '_minimized_hwnds'):
                self._minimized_hwnds = {}
            self._minimized_hwnds[p_name] = hwnd
            win32gui.EnableWindow(hwnd, False)
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            
            if self._dialog_open:
                return  # Auth dialog already visible, but we still hid the app

            # App is locked and no valid grant — trigger auth
            self._dialog_open = True
            self._pending_lock = p_name
            self.lock_triggered.emit(p_name)

        except Exception as exc:
            logger.debug("AppLockerManager tick error: %s", exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_process_running(process_name: str) -> bool:
        """Check if any process with the given name is currently running."""
        try:
            import psutil
            p_lower = process_name.lower()
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and proc.info["name"].lower() == p_lower:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        return False

    def on_auth_canceled(self) -> None:
        """Call when the user cancels the auth dialog without authenticating."""
        self._dialog_open = False
        self._pending_lock = None
